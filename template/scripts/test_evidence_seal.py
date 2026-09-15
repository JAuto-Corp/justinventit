"""Exercise the actual seal/verify CLI against disposable directories."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).with_name("evidence-seal.py")
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_TERMINAL_PROMPT="0")


class EvidenceSealTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "packet"
        self.other = Path(self.tmp.name) / "elsewhere"
        self.other.mkdir()
        self.write("REPORT.md", "report")
        self.write("codex-review/output.txt", "verdict")
        self.write("café ünïcode.log", "utf8")

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True,
                              cwd=str(cwd or self.other), env=ENV, timeout=30)

    def manifest(self):
        return (self.root / "SHA256SUMS").read_text(encoding="utf-8")

    def test_seal_is_idempotent_relative_sorted_and_coreutils_compatible(self):
        first = self.run_cli("seal", str(self.root))
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertIn("SEALED entries=3 manifest_sha256=", first.stdout)
        self.assertIn("git_head=none", first.stdout)
        self.assertNotIn("git_dirty", first.stdout)
        text = self.manifest()
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 0)
        self.assertEqual(self.manifest(), text)
        paths = [line.split("  ", 1)[1] for line in text.splitlines()]
        self.assertEqual(paths, sorted(paths, key=str.encode))
        self.assertFalse(any(p.startswith(("/", "./")) or "\\" in p for p in paths))
        self.assertNotIn("SHA256SUMS", paths)
        if not shutil.which("sha256sum"):
            self.skipTest("coreutils sha256sum unavailable")
        check = subprocess.run(["sha256sum", "-c", "--strict", "SHA256SUMS"], cwd=str(self.root),
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_verify_passes_from_another_cwd(self):
        self.run_cli("seal", str(self.root))
        result = self.run_cli("verify", str(self.root), cwd=Path(self.tmp.name))
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "OK entries=3"))

    def test_changed_and_missing_entries_exit_1_and_are_named(self):
        self.run_cli("seal", str(self.root))
        self.write("REPORT.md", "tampered")
        (self.root / "codex-review/output.txt").unlink()
        result = self.run_cli("verify", str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHANGED REPORT.md", result.stdout)
        self.assertIn("MISSING codex-review/output.txt", result.stdout)

    def test_unlisted_files_exit_3_unless_declared_ignored(self):
        self.run_cli("seal", str(self.root))
        self.write("coordination/BRIEF.md", "late")
        result = self.run_cli("verify", str(self.root))
        self.assertEqual((result.returncode, result.stdout.strip()), (3, "UNLISTED coordination/BRIEF.md"))
        self.write(".sealignore", "# declared exclusion\ncoordination/\n")
        self.assertEqual(self.run_cli("seal", str(self.root), "--reseal").returncode, 0)
        self.assertIn(".sealignore", self.manifest())
        self.assertNotIn("coordination/", self.manifest())
        self.write("coordination/MORE.txt", "still ignored")
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 0)

    def test_seal_refuses_a_failing_manifest_without_reseal_and_prints_delta_with_it(self):
        self.run_cli("seal", str(self.root))
        before = self.manifest()
        self.write("REPORT.md", "v2")
        self.write("NEW.txt", "added")
        (self.root / "café ünïcode.log").unlink()
        refused = self.run_cli("seal", str(self.root))
        self.assertEqual(refused.returncode, 1)
        self.assertIn("REFUSED", refused.stdout)
        self.assertEqual(self.manifest(), before)
        resealed = self.run_cli("seal", str(self.root), "--reseal")
        self.assertEqual(resealed.returncode, 0, resealed.stdout)
        self.assertIn("DELTA changed REPORT.md", resealed.stdout)
        self.assertIn("DELTA added NEW.txt", resealed.stdout)
        self.assertIn("DELTA removed café ünïcode.log", resealed.stdout)
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 0)

    def test_malformed_or_absolute_manifest_lines_cannot_be_evaluated(self):
        self.run_cli("seal", str(self.root))
        with open(self.root / "SHA256SUMS", "a", encoding="utf-8") as fh:
            fh.write("0" * 64 + "  " + str(self.root / "REPORT.md") + "\n")
        result = self.run_cli("verify", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("CANNOT-EVALUATE", result.stdout)
        self.assertEqual(self.run_cli("verify", str(self.other)).returncode, 2)

    def test_symlink_is_refused(self):
        os.symlink(self.root / "REPORT.md", self.root / "link.md")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink refused: link.md", result.stdout)
        self.write(".sealignore", "link.md\n")
        declared = self.run_cli("seal", str(self.root))
        self.assertEqual(declared.returncode, 0, declared.stdout)
        self.assertNotIn("link.md", self.manifest())
        (self.root / "raw").mkdir()
        os.symlink(self.root, self.root / "raw" / "latest")
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 2)
        self.write(".sealignore", "link.md\nraw/\n")
        self.assertEqual(self.run_cli("seal", str(self.root), "--reseal").returncode, 0)
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 0)

    def test_git_head_is_reported_only_inside_a_repository(self):
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), env=ENV, check=True)
        subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=T", "add", "-A"],
                       cwd=str(self.root), env=ENV, check=True)
        subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=T", "commit", "-qm", "seed"],
                       cwd=str(self.root), env=ENV, check=True)
        self.write(".sealignore", ".git/\n")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(self.root), env=ENV).decode().strip()
        self.assertIn("git_head=" + head, result.stdout)
        self.assertNotIn("git_dirty", result.stdout)

    def test_render_orders_by_bytes_regardless_of_insertion_order(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("evidence_seal", CLI)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        text = mod.render({"z.txt": "0" * 64, "a/b.txt": "1" * 64, "a.txt": "2" * 64, "é.txt": "3" * 64})
        self.assertEqual([l.split("  ", 1)[1] for l in text.splitlines()], ["a.txt", "a/b.txt", "z.txt", "é.txt"])

    def test_temporary_file_never_collides_with_packet_files(self):
        self.write("SHA256SUMS.tmp", "a real packet file with an unlucky name")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.root / "SHA256SUMS.tmp").read_text(), "a real packet file with an unlucky name")
        self.assertIn("  SHA256SUMS.tmp\n", self.manifest())
        self.assertEqual([p.name for p in self.root.glob(".SHA256SUMS.*")], [])

    def test_ignore_file_is_always_sealed_and_cannot_exclude_itself(self):
        self.write(".sealignore", ".sealignore\n")
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 0)
        self.assertIn("  .sealignore\n", self.manifest())
        self.write("late.txt", "added")
        self.write(".sealignore", ".sealignore\nlate.txt\n")
        result = self.run_cli("verify", str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHANGED .sealignore", result.stdout)

    def test_unreadable_subtree_cannot_be_evaluated(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores directory permissions")
        (self.root / "codex-review").chmod(0)
        self.addCleanup((self.root / "codex-review").chmod, 0o700)
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("CANNOT-EVALUATE", result.stdout)
        self.assertFalse((self.root / "SHA256SUMS").exists())

    def test_non_canonical_manifest_paths_cannot_be_evaluated(self):
        self.run_cli("seal", str(self.root))
        good = self.manifest()
        for bad in ("a//b", "a/./b", "a\\b", "C:\\file", "", "-", "trailing/"):
            (self.root / "SHA256SUMS").write_text(good + "0" * 64 + "  " + bad + "\n", encoding="utf-8")
            result = self.run_cli("verify", str(self.root))
            self.assertEqual(result.returncode, 2, bad)
            self.assertIn("CANNOT-EVALUATE", result.stdout)
        (self.root / "SHA256SUMS").write_text("", encoding="utf-8")
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 2)

    def test_manifest_symlink_and_ignore_symlink_are_refused(self):
        self.run_cli("seal", str(self.root))
        real = self.root / "SHA256SUMS"
        moved = self.other / "elsewhere-SHA256SUMS"
        real.rename(moved)
        os.symlink(moved, real)
        for verb in ("verify", "seal"):
            result = self.run_cli(verb, str(self.root))
            self.assertEqual(result.returncode, 2, verb)
            self.assertIn("symlink refused: SHA256SUMS", result.stdout)
        self.assertTrue(real.is_symlink())
        real.unlink()
        os.symlink(moved, self.root / ".sealignore")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink refused: .sealignore", result.stdout)

    def test_unsealable_names_and_empty_packets_are_refused(self):
        self.write("new\nline.txt", "x")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsealable name", result.stdout)
        (self.root / "new\nline.txt").unlink()
        self.write("-", "dash")
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 2)
        (self.root / "-").unlink()
        self.write("back\\slash.txt", "x")
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 2)
        (self.root / "back\\slash.txt").unlink()
        empty = self.other / "empty"
        empty.mkdir()
        result = self.run_cli("seal", str(empty))
        self.assertEqual(result.returncode, 2)
        self.assertIn("empty packet", result.stdout)
        self.assertFalse((empty / "SHA256SUMS").exists())

    def test_git_head_only_via_rev_parse_never_filters_and_none_when_absent(self):
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=T"]
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), env=ENV, check=True)
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 2)
        self.assertIn("declare '.git/'", self.run_cli("seal", str(self.root)).stdout)
        self.write(".sealignore", ".git/\n")
        subprocess.run(git + ["add", "-A"], cwd=str(self.root), env=ENV, check=True)
        subprocess.run(git + ["commit", "-qm", "seed"], cwd=str(self.root), env=ENV, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(self.root), env=ENV).decode().strip()
        marker = Path(self.tmp.name) / "filter-ran"
        self.write(".gitattributes", "* filter=probe\n")
        subprocess.run(["git", "config", "filter.probe.clean", "sh -c 'touch %s; cat'" % marker],
                       cwd=str(self.root), env=ENV, check=True)
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("git_head=" + head, result.stdout)
        self.assertNotIn("git_dirty", result.stdout)
        self.assertFalse(marker.exists(), "a repository content filter ran during seal")
        nogit = subprocess.run([sys.executable, str(CLI), "seal", str(self.root)], capture_output=True,
                               text=True, cwd=str(self.other), env=dict(ENV, PATH=""))
        self.assertIn("git_head=none", nogit.stdout)
        selected = subprocess.run([sys.executable, str(CLI), "seal", str(self.root)], capture_output=True,
                                  text=True, cwd=str(self.other), env=dict(ENV, GIT_DIR=str(self.root / ".git")))
        self.assertEqual(selected.returncode, 0, selected.stdout)
        self.assertIn("git_head=none", selected.stdout)
        self.assertFalse(marker.exists())

    def test_all_listed_files_deleted_is_missing_not_empty(self):
        self.run_cli("seal", str(self.root))
        for path in list(self.root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS":
                path.unlink()
        result = self.run_cli("verify", str(self.root))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("MISSING REPORT.md", result.stdout)

    def test_cr_separated_manifest_cannot_be_evaluated(self):
        self.run_cli("seal", str(self.root))
        raw = (self.root / "SHA256SUMS").read_bytes().replace(b"\n", b"\r")
        (self.root / "SHA256SUMS").write_bytes(raw)
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 2)
        (self.root / "SHA256SUMS").write_bytes(raw.replace(b"\r", b"\r\n"))
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 2)

    def test_ignore_rules_match_path_components_not_string_prefixes(self):
        self.write("foo/inside.txt", "x")
        self.write("foobar/outside.txt", "y")
        self.write(".sealignore", "foo\n")
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 0)
        self.assertNotIn("foo/inside.txt", self.manifest())
        self.assertIn("foobar/outside.txt", self.manifest())

    def test_dangling_and_directory_symlinks_are_refused_unless_declared(self):
        os.symlink(self.root / "does-not-exist", self.root / "dangling")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink refused: dangling", result.stdout)
        self.write(".sealignore", "dangling\n")
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 0)

    def test_duplicate_and_parent_entries_cannot_be_evaluated(self):
        self.run_cli("seal", str(self.root))
        good = self.manifest()
        first = good.splitlines()[0]
        for extra in (first, "0" * 64 + "  ../escape.txt", "0" * 64 + "  a/../b.txt"):
            (self.root / "SHA256SUMS").write_text(good + extra + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 2, extra)

    def test_special_files_are_refused_unless_declared(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs on this platform")
        self.run_cli("seal", str(self.root))
        os.mkfifo(self.root / "unlisted.fifo")
        result = self.run_cli("verify", str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("unsupported file type refused (declare it or remove it): unlisted.fifo", result.stdout)
        self.assertEqual(self.run_cli("seal", str(self.root), "--reseal").returncode, 2)
        self.write(".sealignore", "unlisted.fifo\n")
        self.assertEqual(self.run_cli("seal", str(self.root), "--reseal").returncode, 0)
        self.assertEqual(self.run_cli("verify", str(self.root)).returncode, 0)
        (self.root / "SHA256SUMS").unlink()
        os.mkfifo(self.root / "SHA256SUMS")
        for verb in (("seal",), ("seal", "--reseal"), ("verify",)):
            result = self.run_cli(*verb, str(self.root))
            self.assertEqual(result.returncode, 2, verb)
            self.assertIn("unsupported file type refused: SHA256SUMS", result.stdout)
        (self.root / "SHA256SUMS").unlink()
        (self.root / ".sealignore").unlink()
        os.mkfifo(self.root / ".sealignore")
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported file type refused: .sealignore", result.stdout)

    def test_ignore_rules_must_be_canonical(self):
        for bad in (b"foo\r\n", b"foo\r", b"a\\b\n", b"../x\n", b"foo\rbar\n"):
            (self.root / ".sealignore").write_bytes(bad)
            result = self.run_cli("seal", str(self.root))
            self.assertEqual(result.returncode, 2, bad)
            self.assertIn("non-canonical rule in .sealignore", result.stdout)
        (self.root / ".sealignore").write_bytes(b"# comment\n\n  codex-review/  \n")
        self.assertEqual(self.run_cli("seal", str(self.root)).returncode, 0)
        self.assertNotIn("codex-review/", self.manifest())

    def test_sha256_object_format_repository_head_is_reported(self):
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        init = subprocess.run(["git", "init", "-q", "--object-format=sha256"], cwd=str(self.root), env=ENV,
                              capture_output=True)
        if init.returncode != 0:
            self.skipTest("git lacks --object-format=sha256")
        git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=T"]
        self.write(".sealignore", ".git/\n")
        subprocess.run(git + ["add", "-A"], cwd=str(self.root), env=ENV, check=True)
        subprocess.run(git + ["commit", "-qm", "seed"], cwd=str(self.root), env=ENV, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(self.root), env=ENV).decode().strip()
        self.assertEqual(len(head), 64)
        result = self.run_cli("seal", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("git_head=" + head, result.stdout)

    def test_filesystem_root_is_refused(self):
        result = self.run_cli("verify", "/")
        self.assertEqual(result.returncode, 2)
        self.assertIn("filesystem root refused", result.stdout)


if __name__ == "__main__":
    unittest.main()

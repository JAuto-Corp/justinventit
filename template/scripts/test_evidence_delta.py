"""Exercise the actual read-only CLI against disposable local Git history."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).with_name("evidence-delta.py")
TEST_ENV = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
TEST_ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_TERMINAL_PROMPT="0")


class EvidenceDeltaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Local Test")
        self.write("src/café file.txt", "original")
        self.write("tests/check.txt", "oracle")
        self.write("README.md", "docs")
        self.before = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], env=TEST_ENV).decode().strip()

    def write(self, name, value):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "synthetic change")
        return self.git("rev-parse", "HEAD")

    def report(self, *inputs, before=None, code=0, env=None):
        args = [sys.executable, str(CLI), "--repo", str(self.repo)]
        for path in inputs:
            args.extend(["--input", path])
        args.extend(["--", before or self.before, "HEAD"])
        result = subprocess.run(args, capture_output=True, text=True, env=env if env is not None else TEST_ENV)
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_docs_change_is_visible_but_does_not_change_selected_inputs(self):
        self.write("README.md", "new docs")
        self.commit()
        report = self.report("src", "tests")
        self.assertEqual(report["assessment"], "committed_inputs_unchanged")
        self.assertEqual([x["path"] for x in report["all_changes"]], ["README.md"])
        self.assertEqual(report["input_changes"], [])
        self.assertEqual(Path(report["repository_git_dir"]), self.repo / ".git")
        self.assertEqual(self.report()["assessment"], "committed_inputs_changed")
        self.assertIsNone(report["worktree_has_changes"])
        self.assertEqual(report["worktree_state"], "not_inspected")

    def test_source_or_oracle_change_requires_recheck(self):
        for path in ("src/café file.txt", "tests/check.txt"):
            with self.subTest(path=path):
                self.write(path, "changed")
                self.commit()
                self.assertEqual(self.report(path)["assessment"], "committed_inputs_changed")

    def test_mode_change_is_not_hidden(self):
        self.git("update-index", "--chmod=+x", "src/café file.txt")
        self.git("commit", "-qm", "mode only")
        change = self.report("src")["input_changes"][0]
        self.assertNotEqual(change["before"]["mode"], change["after"]["mode"])
        self.assertEqual(change["before"]["object"], change["after"]["object"])

    def test_directory_add_delete_rename_and_literal_paths(self):
        self.git("mv", "src/café file.txt", "src/renamed.txt")
        self.write("src/new.txt", "new")
        self.write(":(glob)*", "literal")
        self.commit()
        changes = self.report("src")["input_changes"]
        self.assertEqual(len(changes), 3)
        self.assertIsNone(next(x for x in changes if x["path"] == "src/café file.txt")["after"])
        self.assertEqual(len(self.report(":(glob)*")["input_changes"]), 1)
        self.git("rm", "-qr", "src")
        self.commit()
        self.assertEqual(self.report("src/café file.txt")["assessment"], "committed_inputs_changed")

    def test_invalid_refs_and_unknown_or_escaping_inputs_are_unavailable(self):
        self.assertIn("error", self.report(before="--bad-option", code=2))
        for path in ("typo", "../README.md", "/README.md", "src/../README.md", "src/*"):
            with self.subTest(path=path):
                self.assertIn("error", self.report(path, code=2))

    def test_symlinks_submodules_and_type_transitions_are_unavailable(self):
        file = self.repo / "src/café file.txt"
        file.unlink()
        file.symlink_to("../README.md")
        self.commit()
        self.assertIn("error", self.report("src", code=2))
        self.git("update-index", "--add", "--cacheinfo", f"160000,{self.before},vendor")
        self.git("commit", "-qm", "synthetic gitlink")
        self.assertIn("error", self.report("vendor", code=2))

    def test_checkout_changes_do_not_become_committed_evidence(self):
        for stage in ("untracked", "staged", "unstaged"):
            with self.subTest(stage=stage):
                if stage == "untracked":
                    self.write("untracked.txt", "new")
                elif stage == "staged":
                    self.git("add", "untracked.txt")
                else:
                    self.git("reset", "-q", "--hard", "HEAD")
                    self.write("README.md", "dirty")
                report = self.report()
                self.assertIsNone(report["worktree_has_changes"])
                self.assertEqual(report["worktree_state"], "not_inspected")
                self.assertEqual(report["assessment"], "committed_inputs_unchanged")

    def test_no_external_diff_or_transport_and_missing_local_objects(self):
        marker = self.repo / "unexpected-effect"
        probe = self.repo / ".git" / "effect-probe.sh"
        probe.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\n")
        probe.chmod(0o700)
        self.write("README.md", "different")
        self.commit()
        self.git("config", "diff.external", str(probe))
        self.git("config", "core.fsmonitor", str(probe))
        self.report("src")
        self.assertFalse(marker.exists())
        self.git("config", "core.fsmonitor", "false")
        self.git("config", "remote.origin.url", f"ext::sh -c 'touch {marker}'")
        self.git("config", "remote.origin.promisor", "true")
        self.git("config", "protocol.ext.allow", "always")
        oid = self.git("rev-parse", "HEAD^{tree}")
        (self.repo / ".git" / "objects" / oid[:2] / oid[2:]).unlink()
        self.assertIn("error", self.report(code=2))
        self.assertFalse(marker.exists())

    def test_content_filters_cannot_execute(self):
        marker = self.repo / "unexpected-filter-effect"
        probe = self.repo / ".git" / "filter-probe.sh"
        probe.write_text("#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\ncat\n")
        probe.chmod(0o700)
        self.write(".gitattributes", "README.md filter=probe\n")
        self.commit()
        self.git("config", "filter.probe.clean", str(probe))
        self.write("README.md", "DIRT")
        self.report()
        self.assertFalse(marker.exists())

    def test_inherited_repository_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            subprocess.run(["git", "init", "-q", other], check=True, env=TEST_ENV)
            env = dict(TEST_ENV, GIT_DIR=other + "/.git", GIT_WORK_TREE=other)
            report = self.report(env=env, code=2)
            self.assertIn("GIT_DIR", report["error"])


if __name__ == "__main__":
    unittest.main()

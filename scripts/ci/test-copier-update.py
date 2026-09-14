#!/usr/bin/env python3
"""Real Copier answers-persistence and update-cycle tests for the main template.

Copies the template at HEAD from a local git clone, makes a framework change in that clone, runs a real
`copier update`, and checks that project-owned edits survive, the framework change arrives, and the
answers file records the resolved template commit, the original source and every answer.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MARKER = "UPDATE-MARKER: framework-managed text added after generation"
GIT_ID = ["-c", "user.name=jv-test", "-c", "user.email=jv-test@example.invalid"]


def run(args: list[str], cwd: Path, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=300,
                          stdin=subprocess.DEVNULL, **kw)


def git(cwd: Path, *args: str) -> str:
    result = run(["git", *GIT_ID, *args], cwd)
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr[-400:]}")
    return result.stdout.strip()


def answers(project: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (project / ".copier-answers.yml").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


@unittest.skipUnless(shutil.which("copier"), "copier CLI not installed")
class CopierUpdateCycle(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jv-copier-update."))
        self.template = self.tmp / "template-clone"
        git(self.tmp, "clone", "-q", str(ROOT), str(self.template))
        self.project = self.tmp / "project"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy_at_head(self) -> None:
        result = run(["copier", "copy", "--defaults", "--trust", "--vcs-ref", "HEAD",
                      "-d", "project_name=updproj", "-d", "project_description=persisted description",
                      str(self.template), str(self.project)], self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr[-800:])
        git(self.project, "init", "-q")
        git(self.project, "add", "-A")
        git(self.project, "commit", "-qm", "seed")

    def test_answers_file_records_commit_source_and_answers(self) -> None:
        self.copy_at_head()
        got = answers(self.project)
        head = git(self.template, "rev-parse", "--short", "HEAD")
        self.assertIn(head, got["_commit"], "resolved template commit must be recorded, not the requested ref")
        self.assertNotIn(got["_commit"], ("None", "HEAD"))
        self.assertEqual(got["_src_path"], str(self.template), "original source, not a temporary clone")
        for key, value in (("project_name", "updproj"), ("project_description", "persisted description"),
                           ("stack", "nextjs"), ("orchestration_tier", "solo")):
            self.assertEqual(got.get(key), value, key)

    def test_update_delivers_framework_change_and_keeps_project_edits(self) -> None:
        self.copy_at_head()
        before = answers(self.project)["_commit"]
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\n## Hand-written project section\n", encoding="utf-8")
        git(self.project, "commit", "-qam", "project edit")
        claude_jinja = self.template / "template/CLAUDE.md.jinja"
        text = claude_jinja.read_text(encoding="utf-8")
        self.assertIn("## Hooks\n", text)
        claude_jinja.write_text(text.replace("## Hooks\n", f"## Hooks\n\n{MARKER}\n", 1), encoding="utf-8")
        git(self.template, "commit", "-qam", "framework change after generation")
        new_head = git(self.template, "rev-parse", "--short", "HEAD")
        result = run(["copier", "update", "--defaults", "--trust", "--vcs-ref", "HEAD"], self.project)
        self.assertEqual(result.returncode, 0, result.stderr[-800:])
        self.assertIn(MARKER, (self.project / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("## Hand-written project section", agents.read_text(encoding="utf-8"))
        after = answers(self.project)
        self.assertNotEqual(after["_commit"], before, "answers file must advance after update")
        self.assertIn(new_head, after["_commit"])
        self.assertEqual(after["project_name"], "updproj")
        conflicts = [p for p in self.project.rglob("*") if p.is_file() and ".git" not in p.parts
                     and p.suffix in ("", ".md", ".yml", ".yaml", ".json", ".sh", ".py")
                     and "<<<<<<<" in p.read_text(encoding="utf-8", errors="ignore")]
        self.assertEqual(conflicts, [])


class SkipListDoesNotHideTheAnswersFile(unittest.TestCase):
    def test_copier_yml_does_not_skip_the_answers_file(self) -> None:
        text = (ROOT / "copier.yml").read_text(encoding="utf-8")
        skip = text[text.index("_skip_if_exists:"):text.index("_exclude:")]
        self.assertNotIn('".copier-answers.yml"', skip)

    def test_answers_template_is_canonical(self) -> None:
        text = (ROOT / "template/.copier-answers.yml.jinja").read_text(encoding="utf-8")
        self.assertIn("{{ _copier_answers|to_nice_yaml -}}", text)
        self.assertNotIn("_copier_conf.src_path", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)

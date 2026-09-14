#!/usr/bin/env python3
"""Focused tests for multi-skill projection/route selection, receipt counts and entry pointers.

Runs the real generator and route checker as subprocesses on temporary projects built from
the template, so a fail-open in either script is caught here before CI's generated matrix.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "template"
FIXTURES = ROOT / "scripts/ci/fixtures"
GENERATOR = ROOT / "scripts/generate-skill-surfaces.py"
ROUTES = ROOT / "scripts/ci/check-skill-routes.py"
sys.path.insert(0, str(ROOT / "scripts/ci"))
import skill_inventory  # noqa: E402

PINNED = skill_inventory.pinned_skill_names(FIXTURES)


def run(script: Path, project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), "--project-root", str(project), *args],
                          text=True, capture_output=True, timeout=60)


class TempProject:
    """A generated-project lookalike: both routes for every pinned skill, no scripts/ci/fixtures."""

    def __init__(self, with_fixtures: bool = False) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="jv-multiskill."))
        for name in PINNED:
            shutil.copytree(TEMPLATE / ".agents/skills" / name, self.dir / ".agents/skills" / name)
            shutil.copytree(TEMPLATE / ".claude/skills" / name, self.dir / ".claude/skills" / name)
        if with_fixtures:
            shutil.copytree(FIXTURES, self.dir / "scripts/ci/fixtures")

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class Inventory(unittest.TestCase):
    def test_pinned_names_include_frontend_design_and_new_skills(self) -> None:
        self.assertIn("frontend-design", PINNED)
        self.assertIn("ponytail", PINNED)
        self.assertIn("caveman", PINNED)

    def test_fixture_without_skill_key_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            shutil.copy(FIXTURES / "ponytail.expected.json", d / "ponytail.expected.json")
            (d / "bogus.expected.json").write_text('{"schema_version": 1, "history": []}\n')
            self.assertEqual(skill_inventory.pinned_skill_names(d), ["ponytail"])

    def test_loaded_marker_shape(self) -> None:
        self.assertEqual(
            skill_inventory.loaded_skills_marker(1),
            "Loaded 1 unique skills (1 unconditional, 0 conditional, managed: 0, user: 0, "
            "project: 1, additional: 0, legacy commands: 0)")
        self.assertIn("Loaded 3 unique skills (3 unconditional", skill_inventory.loaded_skills_marker(3))

    # Captured verbatim from Claude Code 2.1.270 --debug against a three-skill project (skills-probes-20260914).
    CAPTURED_CLAUDE_DEBUG_LINE = 'Loaded 3 unique skills (3 unconditional, 0 conditional, managed: 0, user: 0, project: 3, additional: 0, legacy commands: 0)'

    def test_loaded_total_regex_matches_a_captured_real_debug_line(self) -> None:
        self.assertEqual(skill_inventory.loaded_skills_total(self.CAPTURED_CLAUDE_DEBUG_LINE), 3)
        self.assertEqual(skill_inventory.loaded_skills_marker(3), self.CAPTURED_CLAUDE_DEBUG_LINE)

    def test_loaded_total_regex_is_self_consistent(self) -> None:
        self.assertEqual(skill_inventory.loaded_skills_total(skill_inventory.loaded_skills_marker(1)), 1)
        self.assertEqual(skill_inventory.loaded_skills_total(skill_inventory.loaded_skills_marker(3)), 3)
        self.assertEqual(skill_inventory.loaded_skills_total(
            "Loaded 3 unique skills (1 unconditional, 0 conditional, managed: 0, user: 0, project: 3, additional: 0, legacy commands: 0)"), -1)
        self.assertEqual(skill_inventory.loaded_skills_total("no marker"), -1)
        two = skill_inventory.loaded_skills_marker(1) + "\n" + skill_inventory.loaded_skills_marker(1)
        self.assertEqual(skill_inventory.loaded_skills_total(two), -1)

    def test_project_skill_count_counts_canonical_dirs_only(self) -> None:
        project = TempProject()
        try:
            self.assertEqual(skill_inventory.project_skill_count(project.dir, FIXTURES), len(PINNED))
            shutil.rmtree(project.dir / ".agents/skills/caveman")
            self.assertEqual(skill_inventory.project_skill_count(project.dir, FIXTURES), len(PINNED) - 1)
        finally:
            project.cleanup()


class Selection(unittest.TestCase):
    def setUp(self) -> None:
        self.project = TempProject()

    def tearDown(self) -> None:
        self.project.cleanup()

    def test_complete_project_passes_both_checks(self) -> None:
        self.assertEqual(run(GENERATOR, self.project.dir, "--check").returncode, 0)
        self.assertEqual(run(ROUTES, self.project.dir).returncode, 0)

    def test_canonical_deleted_projection_kept_fails_closed(self) -> None:
        shutil.rmtree(self.project.dir / ".agents/skills/ponytail")
        gen = run(GENERATOR, self.project.dir, "--check")
        self.assertNotEqual(gen.returncode, 0)
        self.assertIn("canonical skill directory missing or symlinked", gen.stderr)
        self.assertNotEqual(run(ROUTES, self.project.dir).returncode, 0)

    def test_projection_deleted_canonical_kept_fails(self) -> None:
        shutil.rmtree(self.project.dir / ".claude/skills/caveman")
        gen = run(GENERATOR, self.project.dir, "--check")
        self.assertNotEqual(gen.returncode, 0)
        self.assertIn("projection directory missing", gen.stderr)
        self.assertNotEqual(run(ROUTES, self.project.dir).returncode, 0)

    def test_dangling_symlink_route_fails(self) -> None:
        shutil.rmtree(self.project.dir / ".agents/skills/ponytail")
        (self.project.dir / ".agents/skills/ponytail").symlink_to("/nonexistent/ponytail")
        self.assertNotEqual(run(GENERATOR, self.project.dir, "--check").returncode, 0)
        self.assertNotEqual(run(ROUTES, self.project.dir).returncode, 0)

    def test_optional_skill_wholly_absent_is_out_of_scope(self) -> None:
        # A project generated before a skill was pinned carries neither route; frontend-design stays mandatory.
        shutil.rmtree(self.project.dir / ".agents/skills/caveman")
        shutil.rmtree(self.project.dir / ".claude/skills/caveman")
        self.assertEqual(run(GENERATOR, self.project.dir, "--check").returncode, 0)
        self.assertEqual(run(ROUTES, self.project.dir).returncode, 0)

    def test_mandatory_skill_absent_fails_even_when_wholly_absent(self) -> None:
        shutil.rmtree(self.project.dir / ".agents/skills/frontend-design")
        shutil.rmtree(self.project.dir / ".claude/skills/frontend-design")
        self.assertNotEqual(run(GENERATOR, self.project.dir, "--check").returncode, 0)
        self.assertNotEqual(run(ROUTES, self.project.dir).returncode, 0)

    def test_repo_root_is_strict_about_fixture_set(self) -> None:
        project = TempProject(with_fixtures=True)
        try:
            self.assertEqual(run(ROUTES, project.dir).returncode, 0)
            (project.dir / "scripts/ci/fixtures/ponytail.expected.json").unlink()
            self.assertNotEqual(run(ROUTES, project.dir).returncode, 0)
        finally:
            project.cleanup()


class EntryPointers(unittest.TestCase):
    AGENTS = (TEMPLATE / "AGENTS.md.jinja").read_text(encoding="utf-8")
    CLAUDE = (TEMPLATE / "CLAUDE.md.jinja").read_text(encoding="utf-8")

    def test_agents_md_is_the_canonical_contract(self) -> None:
        for section in ("## Before Working", "## TDD Gate", "## Work Routing", "## Skills", "## Git Workflow",
                        "read `docs/SKILL_MODES.md`", "`caveman` runs `lite`"):
            self.assertIn(section, self.AGENTS, section)
        self.assertNotRegex(self.AGENTS, r"`/[a-z]", "AGENTS.md must not use Claude slash-command syntax")

    def test_claude_md_imports_and_does_not_restate(self) -> None:
        lines = [line for line in self.CLAUDE.splitlines() if line.strip()]
        self.assertEqual(lines[1], "@AGENTS.md", "second non-empty line must be the import")
        for restated in ("## TDD Gate", "## Work Routing", "SKILL_MODES.md"):
            self.assertNotIn(restated, self.CLAUDE, restated)
        self.assertIn("/verify:complete", self.CLAUDE)

    def test_mode_policy_sets_lite_default_for_caveman(self) -> None:
        text = (TEMPLATE / "docs/SKILL_MODES.md").read_text(encoding="utf-8")
        self.assertIn("`lite` for routine status updates", text)

    @unittest.skipUnless(shutil.which("copier"), "copier CLI not installed")
    def test_copier_refuses_to_clobber_an_existing_agents_md_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            original = "# hand-authored entry contract\n"
            (target / "AGENTS.md").write_text(original, encoding="utf-8")
            result = subprocess.run(
                ["copier", "copy", "--defaults", "--vcs-ref", "HEAD", "-d", "project_name=keeptest",
                 str(ROOT), str(target)], text=True, capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), original)
            self.assertNotEqual(result.returncode, 0, "copier must refuse to overwrite without --overwrite")

    @unittest.skipUnless(shutil.which("copier"), "copier CLI not installed")
    def test_fresh_render_seeds_contract_and_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            result = subprocess.run(
                ["copier", "copy", "--defaults", "--vcs-ref", "HEAD", "-d", "project_name=freshtest",
                 str(ROOT), str(target)], text=True, capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
            self.assertEqual(result.returncode, 0, result.stderr[-800:])
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("# freshtest — Agent Entry Contract", agents)
            self.assertIn("## TDD Gate", agents)
            self.assertNotIn("{{", agents); self.assertNotIn("{%", agents)
            self.assertIn("\n@AGENTS.md\n", claude)
            self.assertNotIn("## TDD Gate", claude)


if __name__ == "__main__":
    unittest.main(verbosity=1)

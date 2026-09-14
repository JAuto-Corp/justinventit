#!/usr/bin/env python3
"""Pinned-skill inventory helpers shared by the runtime receipt producer and its tests.

The generator and the independent route checker deliberately keep their own copies of the
selection logic; this module only serves the receipt (a producer, not a checker) and tests.
"""

from __future__ import annotations

import json
from pathlib import Path
import re


def pinned_skill_names(fixtures_dir: Path) -> list[str]:
    """Names of every pinned canonical skill: one <name>.expected.json carrying a "skill" object."""
    names: list[str] = []
    for path in sorted(Path(fixtures_dir).glob("*.expected.json")):
        try:
            skill = json.loads(path.read_text(encoding="utf-8")).get("skill")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            continue
        if isinstance(skill, dict) and skill.get("name") and path.name == f"{skill['name']}.expected.json":
            names.append(skill["name"])
    return names


def route_present(path: Path) -> bool:
    """True when a runtime route exists in any form, including a dangling symlink or a stray file."""
    return path.exists() or path.is_symlink()


def project_skill_count(project_root: Path, fixtures_dir: Path) -> int:
    """How many pinned skills a project carries on its canonical route (what Claude/Codex will load)."""
    canonical_root = Path(project_root) / ".agents/skills"
    return sum(1 for name in pinned_skill_names(fixtures_dir) if (canonical_root / name).is_dir())


def loaded_skills_marker(total: int) -> str:
    """Claude Code's debug-log skill summary for a project carrying `total` project skills."""
    return (f"Loaded {total} unique skills ({total} unconditional, 0 conditional, managed: 0, user: 0, "
            f"project: {total}, additional: 0, legacy commands: 0)")


def loaded_skills_pattern(total: int) -> str:
    return re.escape(loaded_skills_marker(total))


LOADED_SKILLS_REGEX = re.compile(
    r"Loaded (?P<total>[1-9][0-9]*) unique skills \((?P=total) unconditional, 0 conditional, managed: 0, "
    r"user: 0, project: (?P=total), additional: 0, legacy commands: 0\)")


def loaded_skills_total(debug_text: str) -> int:
    """The single self-consistent project-skill total a Claude debug log reports, or -1 if absent/ambiguous."""
    matches = LOADED_SKILLS_REGEX.findall(debug_text)
    return int(matches[0]) if len(matches) == 1 else -1

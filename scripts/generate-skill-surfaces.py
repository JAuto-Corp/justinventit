#!/usr/bin/env python3
"""Materialize deterministic runtime-specific skill projections."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys


SKILL_NAME = "frontend-design"
EXPECTED_ENTRIES = ("LICENSE.txt", "PROVENANCE.json", "SKILL.md")


class ProjectionError(RuntimeError):
    """A named projection-contract failure."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"invalid JSON fixture {path}: {exc}") from exc


def expected_provenance(fixture: dict) -> dict:
    try:
        skill = fixture["skill"]
        return {
            "schema_version": 1,
            "name": skill["name"],
            "upstream": skill["upstream"],
            "equivalent_distribution": skill["equivalent_distribution"],
            "authors": skill["authors"],
            "license": skill["license"],
            "files": skill["files"],
            "runtime_routes": skill["runtime_routes"],
        }
    except KeyError as exc:
        raise ProjectionError(f"expected fixture schema missing field: {exc}") from exc


def surface_root(root: Path) -> Path:
    candidate = root / "template"
    return candidate if (candidate / ".agents").is_dir() else root


def frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProjectionError(f"skill frontmatter unreadable: {exc}") from exc
    if "{{" in text or "{%" in text:
        raise ProjectionError("unresolved Jinja syntax in canonical skill")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ProjectionError("malformed YAML frontmatter: opening delimiter missing")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ProjectionError("malformed YAML frontmatter: closing delimiter missing") from exc
    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ProjectionError(f"malformed YAML frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def regular_nonexecutable(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ProjectionError(f"{label} must be a regular file, not a symlink")
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise ProjectionError(f"{label} missing entry") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ProjectionError(f"{label} has wrong type; expected regular file")
    if stat.S_IMODE(info.st_mode) & 0o111:
        raise ProjectionError(f"{label} has executable permission mode")


def validate_canonical(root: Path) -> tuple[Path, dict]:
    fixture_path = root / "scripts/ci/fixtures/frontend-design.expected.json"
    if not fixture_path.is_file():
        fixture_path = Path(__file__).resolve().parent / "ci/fixtures/frontend-design.expected.json"
    fixture = load_json(fixture_path)
    surfaces = surface_root(root)
    source = surfaces / ".agents/skills" / SKILL_NAME
    if source.is_symlink() or not source.is_dir():
        raise ProjectionError("canonical skill directory missing or symlinked")
    actual_entries = tuple(sorted(item.name for item in source.iterdir()))
    if actual_entries != EXPECTED_ENTRIES:
        raise ProjectionError(
            f"canonical skill has unknown or missing entries: expected={EXPECTED_ENTRIES} actual={actual_entries}"
        )
    for name in EXPECTED_ENTRIES:
        regular_nonexecutable(source / name, f"canonical {name}")

    fields = frontmatter(source / "SKILL.md")
    if fields.get("name") != SKILL_NAME:
        raise ProjectionError("canonical skill frontmatter name mismatch")
    if not fields.get("description"):
        raise ProjectionError("canonical skill frontmatter description is empty")
    expected = expected_provenance(fixture)
    if fields.get("license") != expected["license"]["frontmatter"]:
        raise ProjectionError("canonical skill license frontmatter mismatch")
    license_name = expected["license"]["filename"]
    if Path(license_name).is_absolute() or len(Path(license_name).parts) != 1:
        raise ProjectionError("license filename escapes canonical containment")

    provenance = load_json(source / "PROVENANCE.json")
    if provenance != expected:
        raise ProjectionError("canonical provenance differs from expected fixture")
    for name in ("SKILL.md", "LICENSE.txt"):
        record = expected["files"][name]
        path = source / name
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise ProjectionError(f"canonical {name} byte/hash differs from expected fixture")
    return source, fixture


def paired_skills(root: Path, canonical_frontend: Path) -> list[tuple[Path, Path]]:
    surfaces = surface_root(root)
    projection_root = surfaces / ".claude/skills"
    return [(canonical_frontend, projection_root / SKILL_NAME)]


def projection_differences(source: Path, target: Path) -> list[str]:
    failures: list[str] = []
    if target.is_symlink():
        return ["projection directory is a symlink; physical copy required"]
    if not target.is_dir():
        return ["projection directory missing"]
    source_names = {item.name for item in source.iterdir()}
    target_names = {item.name for item in target.iterdir()}
    for name in sorted(source_names - target_names):
        failures.append(f"projection missing entry: {name}")
    for name in sorted(target_names - source_names):
        failures.append(f"projection extra or stale entry: {name}")
    for name in sorted(source_names & target_names):
        left, right = source / name, target / name
        if right.is_symlink():
            failures.append(f"projection {name} is a symlink, not a regular file")
            continue
        if not right.is_file():
            failures.append(f"projection {name} type mismatch: expected regular file")
            continue
        if stat.S_IMODE(right.stat().st_mode) & 0o111:
            failures.append(f"projection {name} executable permission mode drift")
        if left.read_bytes() != right.read_bytes():
            failures.append(f"projection {name} byte/hash drift")
    return failures


def remove_entry(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def materialize(source: Path, target: Path) -> None:
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        remove_entry(target)
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o755)
    source_names = {item.name for item in source.iterdir()}
    for entry in sorted(target.iterdir(), key=lambda item: item.name):
        if entry.name not in source_names:
            remove_entry(entry)
    for name in sorted(source_names):
        src, dst = source / name, target / name
        if dst.is_symlink() or (dst.exists() and not dst.is_file()):
            remove_entry(dst)
        needs_copy = not dst.exists() or src.read_bytes() != dst.read_bytes()
        if needs_copy:
            shutil.copyfile(src, dst)
        if stat.S_IMODE(dst.stat().st_mode) != 0o644:
            dst.chmod(0o644)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    try:
        source, _fixture = validate_canonical(root)
        pairs = paired_skills(root, source)
        if args.check:
            failures = [
                failure
                for pair_source, pair_target in pairs
                for failure in projection_differences(pair_source, pair_target)
            ]
            if failures:
                raise ProjectionError("; ".join(failures))
            print("skill projection check: PASS")
            return 0
        for pair_source, pair_target in pairs:
            materialize(pair_source, pair_target)
        failures = [
            failure
            for pair_source, pair_target in pairs
            for failure in projection_differences(pair_source, pair_target)
        ]
        if failures:
            raise ProjectionError("post-generation projection drift: " + "; ".join(failures))
        print("skill projection generation: PASS")
        return 0
    except ProjectionError as exc:
        print(f"skill projection error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

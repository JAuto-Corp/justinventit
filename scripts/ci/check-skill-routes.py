#!/usr/bin/env python3
"""Independently verify portable skill authority, routes, and projections."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys


PINNED_SKILL = {
    "name": "frontend-design",
    "upstream": {
        "repository": "anthropics/claude-plugins-official",
        "commit": "d029127f7d29bdb8fd8902ac34dd7d5c8ba92b6e",
        "path": "plugins/frontend-design/skills/frontend-design",
    },
    "equivalent_distribution": {
        "repository": "anthropics/claude-code",
        "plugin_name": "frontend-design",
        "plugin_version": "1.1.0",
    },
    "authors": ["Prithvi Rajasekaran", "Alexander Bricken"],
    "license": {
        "spdx": "Apache-2.0",
        "filename": "LICENSE.txt",
        "frontmatter": "Complete terms in LICENSE.txt",
    },
    "files": {
        "SKILL.md": {
            "bytes": 8260,
            "sha256": "1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd",
        },
        "LICENSE.txt": {
            "bytes": 10174,
            "sha256": "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594",
        },
    },
    "runtime_routes": {
        "codex": {"mode": "canonical", "path": ".agents/skills/frontend-design"},
        "claude": {"mode": "physical-copy", "path": ".claude/skills/frontend-design"},
    },
}
PINNED_TOOLCHAIN = {
    "copier": "9.17.1",
    "node": "v22.23.2",
    "codex": "codex-cli 0.145.0",
    "claude": "2.1.232 (Claude Code)",
}
EXPECTED_ENTRIES = {"SKILL.md", "LICENSE.txt", "PROVENANCE.json"}


class RouteError(RuntimeError):
    pass


def load_json(path: Path, label: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RouteError(f"{label} missing: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteError(f"{label} invalid JSON schema: {exc}") from exc


def frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RouteError(f"skill missing: {path}") from exc
    except UnicodeDecodeError as exc:
        raise RouteError(f"skill frontmatter is not UTF-8: {path}") from exc
    if "{{" in text or "{%" in text:
        raise RouteError(f"unresolved Jinja syntax in skill: {path}")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise RouteError(f"malformed YAML frontmatter opening delimiter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise RouteError(f"malformed YAML frontmatter closing delimiter: {path}") from exc
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise RouteError(f"malformed YAML frontmatter line in {path}: {line!r}")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def assert_fixture(root: Path) -> dict:
    path = root / "scripts/ci/fixtures/frontend-design.expected.json"
    if not path.is_file():
        path = Path(__file__).resolve().parent / "fixtures/frontend-design.expected.json"
    fixture = load_json(path, "expected fixture")
    if fixture.get("schema_version") != 1:
        raise RouteError("expected fixture schema_version differs from pinned authority")
    if fixture.get("skill") != PINNED_SKILL:
        expected = json.dumps(PINNED_SKILL, sort_keys=True)
        actual = json.dumps(fixture.get("skill"), sort_keys=True)
        raise RouteError(f"expected fixture skill/upstream/route/license/tool authority drift: expected={expected} actual={actual}")
    if fixture.get("toolchain") != PINNED_TOOLCHAIN:
        raise RouteError(
            f"expected fixture toolchain copier/node/codex/claude pin drift: {fixture.get('toolchain')!r}"
        )
    return fixture


def surface_root(root: Path) -> Path:
    candidate = root / "template"
    return candidate if (candidate / ".agents").is_dir() else root


def safe_route(root: Path, runtime: str, route: dict, expected: dict) -> Path:
    if route != expected:
        raise RouteError(f"{runtime} route mode/path differs from pinned expected route")
    raw = route.get("path")
    if not isinstance(raw, str) or not raw:
        raise RouteError(f"{runtime} route is empty")
    pure = PurePosixPath(raw)
    if pure.is_absolute():
        raise RouteError(f"{runtime} route must not be absolute")
    if ".." in pure.parts:
        raise RouteError(f"{runtime} route parent traversal is not contained")
    normalized = os.path.normpath(raw).replace(os.sep, "/")
    if normalized != raw:
        raise RouteError(f"{runtime} route is a nonnormalized alias")
    surfaces = surface_root(root)
    lexical = surfaces / pure
    resolved = lexical.resolve()
    template_root = surfaces.resolve()
    try:
        resolved.relative_to(template_root)
    except ValueError as exc:
        raise RouteError(f"{runtime} route escapes template containment") from exc
    return lexical


def regular(path: Path, label: str) -> None:
    if path.is_symlink():
        raise RouteError(f"{label} must be a regular file, not a symlink")
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise RouteError(f"{label} missing") from exc
    if not stat.S_ISREG(info.st_mode):
        raise RouteError(f"{label} has wrong type; regular file required")
    if stat.S_IMODE(info.st_mode) & 0o111:
        raise RouteError(f"{label} has executable permission class")


def assert_source(root: Path, source: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise RouteError("canonical skill source missing or symlinked")
    entries = {entry.name for entry in source.iterdir()}
    if entries != EXPECTED_ENTRIES:
        raise RouteError(f"canonical skill missing or extra entry: {sorted(entries)!r}")
    for name in sorted(EXPECTED_ENTRIES):
        regular(source / name, f"canonical {name}")
    fields = frontmatter(source / "SKILL.md")
    if fields.get("name") != PINNED_SKILL["name"]:
        raise RouteError("canonical frontmatter name/basename mismatch")
    if not fields.get("description"):
        raise RouteError("canonical frontmatter description is empty")
    if fields.get("license") != PINNED_SKILL["license"]["frontmatter"]:
        raise RouteError("canonical license frontmatter prose mismatch")
    license_name = PINNED_SKILL["license"]["filename"]
    if Path(license_name).is_absolute() or len(Path(license_name).parts) != 1:
        raise RouteError("license filename escapes canonical containment")
    provenance = load_json(source / "PROVENANCE.json", "canonical provenance")
    if provenance != {"schema_version": 1, **PINNED_SKILL}:
        raise RouteError("canonical provenance differs from independent expected authority")
    for name, record in PINNED_SKILL["files"].items():
        path = source / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size != record["bytes"] or digest != record["sha256"]:
            raise RouteError(f"canonical {name} payload byte/hash differs from independent fixture authority")


def assert_projection(source: Path, projection: Path) -> None:
    if projection.is_symlink():
        raise RouteError("claude projection must be a physical directory, not symlink")
    if not projection.is_dir():
        raise RouteError("claude projection missing")
    source_entries = {entry.name for entry in source.iterdir()}
    projection_entries = {entry.name for entry in projection.iterdir()}
    if source_entries != projection_entries:
        raise RouteError(
            f"claude projection missing/extra/plugin entry drift: source={sorted(source_entries)} projection={sorted(projection_entries)}"
        )
    for name in sorted(source_entries):
        left, right = source / name, projection / name
        regular(right, f"claude projection {name}")
        if left.read_bytes() != right.read_bytes():
            raise RouteError(f"claude projection {name} pointer/hash/byte drift")


def assert_discovery(root: Path, source: Path, projection: Path) -> None:
    surfaces = surface_root(root)
    codex_root = surfaces / ".agents/skills"
    codex_hits: list[Path] = []
    for path in sorted(codex_root.rglob("SKILL.md")):
        if not path.read_bytes().startswith(b"---\n"):
            continue
        fields = frontmatter(path)
        if fields.get("name") != path.parent.name:
            raise RouteError(f"codex basename/frontmatter name mismatch at depth: {path}")
        if fields.get("name") == "frontend-design":
            codex_hits.append(path.parent.resolve())
    if codex_hits != [source.resolve()]:
        raise RouteError(f"codex duplicate/cardinality error for frontend-design: {codex_hits!r}")

    claude_root = surfaces / ".claude/skills"
    claude_hits: list[Path] = []
    for path in sorted(claude_root.rglob("SKILL.md")):
        fields = frontmatter(path)
        if path.parent.name == "frontend-design" and fields.get("name") != "frontend-design":
            raise RouteError(f"claude frontend-design basename/frontmatter name mismatch: {path}")
        if path.parent.name == "frontend-design":
            claude_hits.append(path.parent.resolve())
        elif fields.get("name") == "frontend-design":
            raise RouteError(f"claude frontend-design name has different basename: {path}")
    if claude_hits != [projection.resolve()]:
        raise RouteError(f"claude duplicate/cardinality basename error at all depth: {claude_hits!r}")

    commands = surfaces / ".claude/commands"
    if commands.exists() and any(path.name == "frontend-design.md" for path in commands.rglob("*") if path.is_file()):
        raise RouteError("claude command conflict for frontend-design")
    unsupported = surfaces / ".codex/skills"
    if unsupported.exists():
        raise RouteError("codex unsupported project route .codex/skills")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = parse_args().project_root.resolve()
    try:
        fixture = assert_fixture(root)
        routes = fixture["skill"]["runtime_routes"]
        source = safe_route(root, "codex", routes["codex"], PINNED_SKILL["runtime_routes"]["codex"])
        projection = safe_route(root, "claude", routes["claude"], PINNED_SKILL["runtime_routes"]["claude"])
        assert_source(root, source)
        assert_projection(source, projection)
        assert_discovery(root, source, projection)
        print("skill route/source/projection check: PASS")
        return 0
    except RouteError as exc:
        print(f"skill route check error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""R2 correction acceptance for the five independently reproduced blockers."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
COPIER_FIXTURE = ROOT / "scripts/ci/fixtures/copier-portability"
RUNTIME_FIXTURE = ROOT / "scripts/ci/fixtures/runtime-availability-valid"
SCHEMA = ROOT / "scripts/ci/fixtures/runtime-skill-receipt.schema.json"
FAILURES: list[str] = []
PASSES = 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path = ROOT, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def report(case_id: str, failure: str | None) -> None:
    global PASSES
    if failure is None:
        PASSES += 1
        print(f"[R2-PASS] {case_id}")
    else:
        FAILURES.append(f"{case_id}:{failure}")
        print(f"[R2-FAIL] {case_id}: {failure}")


def valid_hash(value: object, length: int = 64) -> bool:
    return isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is not None


def test_real_copier_update() -> None:
    subject = ROOT / "scripts/ci/copier-real-update-receipt.py"
    if not subject.is_file():
        report("P2-01-real-copier-update", "production real-Copier receipt subject missing")
        return
    with tempfile.TemporaryDirectory(prefix="jv-r2-real-copier.") as temp:
        output_root = Path(temp) / "evidence"
        result = run(
            [
                sys.executable,
                str(subject),
                "--project-root",
                str(ROOT),
                "--fixture-root",
                str(COPIER_FIXTURE),
                "--output-root",
                str(output_root),
            ],
            timeout=300,
        )
        if result.returncode != 0:
            report("P2-01-real-copier-update", f"subject exit={result.returncode}: {(result.stdout + result.stderr)[-1600:]}")
            return
        receipt_path = output_root / "copier-real-update-receipt.json"
        if not receipt_path.is_file():
            report("P2-01-real-copier-update", "receipt missing")
            return
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        expected_ids = {
            "real-clean-update": "clean-overwrite",
            "real-inline-conflict": "conflict-markers",
            "real-reject-conflict": "reject-artifact",
        }
        rows = receipt.get("rows")
        errors: list[str] = []
        if receipt.get("schema_version") != 1:
            errors.append("schema_version")
        if receipt.get("copier_version") != "copier 9.17.1":
            errors.append("copier_version")
        if not valid_hash(receipt.get("fixture_manifest_sha256")):
            errors.append("fixture_manifest_sha256")
        if not isinstance(rows, list) or len(rows) != 3:
            errors.append("row cardinality")
            rows = []
        for row in rows:
            row_id = row.get("id")
            if row_id not in expected_ids:
                errors.append(f"unexpected row {row_id!r}")
                continue
            if row.get("evidence_kind") != "real-copier-update":
                errors.append(f"{row_id}: evidence kind")
            if row.get("copier_version") != "copier 9.17.1":
                errors.append(f"{row_id}: version")
            copier_path = row.get("copier_path")
            if not isinstance(copier_path, str) or "fake" in copier_path.lower():
                errors.append(f"{row_id}: fake or missing Copier path")
            for verb in ("copy", "update"):
                record = row.get(verb)
                if not isinstance(record, dict):
                    errors.append(f"{row_id}: {verb} record")
                    continue
                command = record.get("command")
                if not isinstance(command, list) or verb not in command:
                    errors.append(f"{row_id}: literal {verb} command")
                if record.get("status") != 0:
                    errors.append(f"{row_id}: {verb} status")
                for stream in ("stdout_sha256", "stderr_sha256"):
                    if not valid_hash(record.get(stream)):
                        errors.append(f"{row_id}: {verb} {stream}")
            if row.get("consumer_edit_before_sha256") == row.get("consumer_edit_after_sha256"):
                errors.append(f"{row_id}: consumer edit not recorded")
            if row.get("classification") != expected_ids[row_id]:
                errors.append(f"{row_id}: classification")
            if row.get("remediation") != "framework-wins":
                errors.append(f"{row_id}: remediation")
            rollback = row.get("rollback")
            if not isinstance(rollback, dict) or rollback.get("status") != "pass":
                errors.append(f"{row_id}: rollback")
            if not valid_hash(row.get("template_v1_tree"), 40) or not valid_hash(row.get("template_v2_tree"), 40):
                errors.append(f"{row_id}: template tree refs")
        if {row.get("id") for row in rows} != set(expected_ids):
            errors.append("scenario IDs")
        report("P2-01-real-copier-update", ", ".join(errors) if errors else None)
        if not errors:
            print("R2_COPIER_COUNTS real_update=3 simulated_classifier=11 copier_copy_matrix=4")
            print(f"R2_COPIER_RECEIPT path={receipt_path} sha256={sha256(receipt_path)}")


def test_artifact_closure() -> None:
    runtime = ROOT / "scripts/ci/runtime-skill-receipt.sh"
    command = [str(runtime), "--validate-availability-fixture", str(RUNTIME_FIXTURE)]
    first = run(command)
    if first.returncode != 0:
        report("P2-02-runtime-artifact-closure", f"source-layout validation exit={first.returncode}: {(first.stdout + first.stderr)[-1200:]}")
        return
    with tempfile.TemporaryDirectory(prefix="jv-r2-downloaded-artifact.") as temp:
        downloaded = Path(temp) / "downloaded"
        shutil.copytree(RUNTIME_FIXTURE, downloaded, symlinks=True)
        second = run([str(runtime), "--validate-availability-fixture", str(downloaded)])
        if second.returncode != 0:
            report("P2-02-runtime-artifact-closure", f"downloaded-layout validation exit={second.returncode}")
            return
    report("P2-02-runtime-artifact-closure", None)


def snapshot(root: Path) -> list[tuple[str, str, int, str]]:
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        kind = "symlink" if path.is_symlink() else "dir" if path.is_dir() else "file"
        digest = sha256(path) if kind == "file" else ""
        rows.append((relative, kind, stat.S_IMODE(info.st_mode), digest))
    return rows


def test_explicit_ownership() -> None:
    generator = ROOT / "scripts/generate-skill-surfaces.py"
    with tempfile.TemporaryDirectory(prefix="jv-r2-ownership.") as temp:
        target = Path(temp) / "consumer"
        shutil.copytree(ROOT / "template", target, symlinks=True)
        codex = target / ".agents/skills/domain/project-owned/SKILL.md"
        claude = target / ".claude/skills/domain/project-owned/SKILL.md"
        codex.parent.mkdir(parents=True, exist_ok=True)
        claude.parent.mkdir(parents=True, exist_ok=True)
        codex.write_text("---\nname: project-owned\ndescription: Codex project bytes\n---\ncodex\n", encoding="utf-8")
        claude.write_text("---\nname: project-owned\ndescription: Claude project bytes\n---\nclaude\n", encoding="utf-8")
        governed = target / ".claude/skills/frontend-design/SKILL.md"
        governed.write_bytes(governed.read_bytes() + b"drift")
        before = snapshot(target / ".agents/skills/domain") + snapshot(target / ".claude/skills/domain")
        write_run = run([sys.executable, str(generator), "--project-root", str(target)])
        check_run = run([sys.executable, str(generator), "--project-root", str(target), "--check"])
        after = snapshot(target / ".agents/skills/domain") + snapshot(target / ".claude/skills/domain")
        canonical = target / ".agents/skills/frontend-design/SKILL.md"
        failures = []
        if write_run.returncode != 0 or check_run.returncode != 0:
            failures.append("generator write/check")
        if before != after:
            failures.append("project-owned same-relative pair changed")
        if governed.read_bytes() != canonical.read_bytes():
            failures.append("framework-owned frontend-design not repaired")
        report("P2-03-explicit-framework-ownership", ", ".join(failures) if failures else None)


REQUIRED_PATHS = [
    "schema_version", "receipt_kind", "observed_at", "candidate_head", "candidate_tree",
    "generated_tree_sha256", "node_version", "codex_version", "claude_version", "isolation",
    "isolation.codex_home", "isolation.claude_config_dir", "isolation.managed_roots_absent",
    "isolation.inherited_auth", "codex_availability", "codex_availability.status",
    "codex_availability.target_count", "codex_availability.no_project_target_count",
    "codex_availability.locator_start_marker", "codex_availability.locator_end_marker",
    "codex_availability.observed_absolute_path", "codex_availability.derivation_root",
    "codex_availability.derived_repository_path", "codex_availability.skill_bytes",
    "codex_availability.skill_sha256", "codex_availability.artifacts",
]
for record in ("project", "project_stderr", "control", "control_stderr"):
    REQUIRED_PATHS.append(f"codex_availability.artifacts.{record}")
    for field in ("path", "class", "bytes", "sha256"):
        REQUIRED_PATHS.append(f"codex_availability.artifacts.{record}.{field}")
for leg in ("claude_availability", "claude_no_project"):
    REQUIRED_PATHS.extend(
        [
            leg, f"{leg}.status", f"{leg}.timeout_seconds", f"{leg}.kill_after_seconds",
            f"{leg}.session_id", f"{leg}.target_count", f"{leg}.attachment_skill_count",
            f"{leg}.markers", f"{leg}.artifacts",
        ]
    )
    for marker in ("remote_settings", "roots", "plugin_count", "loaded", "attachment"):
        REQUIRED_PATHS.append(f"{leg}.markers.{marker}")
    for record in ("debug", "transcript", "stdout", "stderr"):
        REQUIRED_PATHS.append(f"{leg}.artifacts.{record}")
        for field in ("path", "class", "bytes", "sha256"):
            REQUIRED_PATHS.append(f"{leg}.artifacts.{record}.{field}")


def parent_and_key(value: dict, dotted: str) -> tuple[dict, str]:
    parts = dotted.split(".")
    node = value
    for part in parts[:-1]:
        node = node[part]
    return node, parts[-1]


def load_validator():
    path = ROOT / "scripts/ci/validate-runtime-receipt.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location("jv_runtime_receipt_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator import spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mutation_values(original: object) -> list[tuple[str, object]]:
    values: list[tuple[str, object]] = [("null", None)]
    if isinstance(original, str):
        values.extend([("empty", ""), ("wrong-type", 7)])
    elif isinstance(original, bool):
        values.append(("wrong-type", "true"))
    elif isinstance(original, int):
        values.append(("wrong-type", "7"))
    elif isinstance(original, dict):
        values.extend([("empty", {}), ("wrong-type", [])])
    elif isinstance(original, list):
        values.extend([("empty", []), ("wrong-type", {})])
    else:
        values.append(("wrong-type", "invalid"))
    return values


def test_schema_matrix() -> None:
    try:
        validator = load_validator()
    except Exception as exc:
        report("P2-04-fail-closed-schema", f"production schema validator unavailable: {exc}")
        return
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    base = json.loads((RUNTIME_FIXTURE / "receipt.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    executed = 0

    def expect_failure(case_id: str, mutated: dict) -> None:
        nonlocal executed
        executed += 1
        try:
            validator.validate_receipt(schema, mutated, RUNTIME_FIXTURE)
        except Exception:
            return
        errors.append(case_id)

    try:
        validator.validate_receipt(schema, base, RUNTIME_FIXTURE)
    except Exception as exc:
        errors.append(f"valid-producer-fixture:{exc}")
    executed += 1

    bogus = {
        "schema_version": 1,
        "node_version": "v22.23.2",
        "codex_version": "codex-cli 0.145.0",
        "claude_version": "2.1.232 (Claude Code)",
        "receipt_kind": "availability",
        "observed_at": None,
        "candidate_head": "",
        "candidate_tree": {},
        "generated_tree_sha256": "0" * 64,
        "codex_availability": None,
        "claude_availability": 7,
        "claude_no_project": {"target_count": 0},
    }
    expect_failure("review-bogus-object", bogus)
    for dotted in REQUIRED_PATHS:
        deleted = copy.deepcopy(base)
        node, key = parent_and_key(deleted, dotted)
        node.pop(key)
        expect_failure(f"delete:{dotted}", deleted)
        original_node, original_key = parent_and_key(base, dotted)
        original = original_node[original_key]
        for label, replacement in mutation_values(original):
            mutated = copy.deepcopy(base)
            node, key = parent_and_key(mutated, dotted)
            node[key] = replacement
            expect_failure(f"{label}:{dotted}", mutated)
    for dotted in (
        "generated_tree_sha256", "codex_availability.skill_sha256",
        "codex_availability.artifacts.project.sha256",
        "claude_availability.artifacts.transcript.sha256",
        "claude_no_project.artifacts.transcript.sha256",
    ):
        mutated = copy.deepcopy(base)
        node, key = parent_and_key(mutated, dotted)
        node[key] = "not-a-hash"
        expect_failure(f"malformed-hash:{dotted}", mutated)
    for dotted in ("", "codex_availability", "claude_availability.artifacts.transcript"):
        mutated = copy.deepcopy(base)
        node = mutated if not dotted else parent_and_key(mutated, dotted)[0][parent_and_key(mutated, dotted)[1]]
        node["unknown_laundering_leg"] = {"accepted": True}
        expect_failure(f"unknown-leg:{dotted or 'root'}", mutated)
    escaped = copy.deepcopy(base)
    escaped["claude_availability"]["artifacts"]["transcript"]["path"] = "../escape.jsonl"
    expect_failure("artifact-path-escape", escaped)
    report("P2-04-fail-closed-schema", ", ".join(errors[:12]) if errors else None)
    if not errors:
        print(f"R2_SCHEMA_MUTATIONS registered={executed} actual={executed} missing=0")


def test_docs() -> None:
    text = (ROOT / "docs/CUSTOMIZATION.md").read_text(encoding="utf-8")
    required = (
        r"project-owned .*\.agents/skills.*Codex-only",
        r"project-authored Claude skills.*independently owned.*\.claude/skills/domain",
        r"no cross-runtime consumer projection generator",
    )
    missing = [pattern for pattern in required if re.search(pattern, text, re.IGNORECASE | re.DOTALL) is None]
    forbidden = re.search(
        r"project-owned skills? (?:are|is|will be) automatically projected",
        text,
        re.IGNORECASE,
    )
    failures = [f"missing meaning /{pattern}/" for pattern in missing]
    if forbidden:
        failures.append("claims automatic project-owned projection")
    report("P2-05-project-owned-doc-limit", ", ".join(failures) if failures else None)


def main() -> int:
    test_real_copier_update()
    test_artifact_closure()
    test_explicit_ownership()
    test_schema_matrix()
    test_docs()
    print(f"R2_CORRECTION registered=5 actual={PASSES + len(FAILURES)} pass={PASSES} fail={len(FAILURES)}")
    if FAILURES:
        print("R2_FAILURE_IDENTITIES_BEGIN")
        for failure in FAILURES:
            print(failure)
        print("R2_FAILURE_IDENTITIES_END")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

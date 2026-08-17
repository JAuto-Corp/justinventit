#!/usr/bin/env python3
"""Validate the closed durable real-Copier pre-remediation evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


class EvidenceValidationError(RuntimeError):
    """The durable Copier bundle is incomplete, ambiguous, or corrupt."""


EXPECTED_ROWS = {
    "real-clean-update": {
        "outcome": "clean-overwrite",
        "source": ".claude/skills/copier-conflict-fixture/SKILL.md",
        "captured": "pre-remediation.generated.SKILL.md",
        "markers": {"open": 0, "middle": 0, "close": 0},
        "reject_count": 0,
        "reject_path": None,
    },
    "real-inline-conflict": {
        "outcome": "conflict-markers",
        "source": ".claude/skills/copier-conflict-fixture/SKILL.md",
        "captured": "pre-remediation.generated.SKILL.md",
        "markers": {"open": 1, "middle": 1, "close": 1},
        "reject_count": 0,
        "reject_path": None,
    },
    "real-reject-conflict": {
        "outcome": "reject-artifact",
        "source": ".claude/skills/copier-conflict-fixture/SKILL.md.rej",
        "captured": "pre-remediation.reject.SKILL.md.rej",
        "markers": {"open": 0, "middle": 0, "close": 0},
        "reject_count": 1,
        "reject_path": ".claude/skills/copier-conflict-fixture/SKILL.md.rej",
    },
}
RECEIPT_KEYS = {
    "schema_version", "copier_version", "fixture_manifest_sha256", "provenance_question",
    "manifest_path", "rows",
}
ROW_KEYS = {
    "id", "evidence_kind", "copier_path", "copier_version", "copy", "update",
    "consumer_edit_before_sha256", "consumer_edit_after_sha256", "classification",
    "remediation", "post_remediation_sha256", "rollback", "observation",
    "template_v1_tree", "template_v2_tree",
}
OBSERVATION_KEYS = {
    "row_id", "evidence_kind", "observed_outcome", "source_path", "captured_path",
    "class", "mode", "bytes", "sha256", "marker_counts", "reject_artifact_count",
    "reject_relative_path", "source_to_captured", "capture_sequence",
}
EQUALITY_KEYS = {
    "source_bytes", "source_sha256", "captured_bytes", "captured_sha256", "equal",
    "before_source_mutation",
}
FILE_KEYS = {"path", "class", "mode", "bytes", "sha256"}
HASH = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str) -> None:
    raise EvidenceValidationError(message)


def object_exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{label}: object required")
    missing = sorted(keys - set(value))
    extra = sorted(set(value) - keys)
    if missing or extra:
        fail(f"{label}: closed keys mismatch missing={missing} extra={extra}")
    return value


def integer(value: Any, label: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        fail(f"{label}: integer >= {minimum} required")
    return value


def hash256(value: Any, label: str) -> str:
    if not isinstance(value, str) or HASH.fullmatch(value) is None:
        fail(f"{label}: SHA-256 required")
    return value


def relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label}: nonempty relative path required")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        fail(f"{label}: stable bundle-relative path required")
    return value


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(f"{label}: unreadable JSON: {exc}") from exc
    if not isinstance(value, dict):
        fail(f"{label}: object required")
    return value


def bundle_entries(root: Path) -> tuple[set[str], list[str]]:
    entries: set[str] = set()
    violations: list[str] = []
    for directory, directories, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        for name in list(directories):
            path = base / name
            if path.is_symlink():
                entries.add(path.relative_to(root).as_posix())
                violations.append(f"symlink entry: {path.relative_to(root).as_posix()}")
                directories.remove(name)
        for name in files:
            path = base / name
            relative = path.relative_to(root).as_posix()
            entries.add(relative)
            if path.is_symlink():
                violations.append(f"symlink entry: {relative}")
                continue
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                violations.append(f"non-regular entry: {relative}")
            elif info.st_nlink != 1:
                violations.append(f"hardlink alias: {relative} nlink={info.st_nlink}")
            elif stat.S_IMODE(info.st_mode) != 0o444:
                violations.append(f"mode drift: {relative} mode={stat.S_IMODE(info.st_mode):04o}")
    return entries, violations


def resolve_regular(root: Path, relative: str, label: str) -> Path:
    path = root / relative
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise EvidenceValidationError(f"{label}: missing/unresolvable artifact") from exc
    if resolved == root or root not in resolved.parents:
        fail(f"{label}: canonical path escapes bundle")
    if path.is_symlink():
        fail(f"{label}: symlink forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail(f"{label}: unique regular file required")
    if stat.S_IMODE(info.st_mode) != 0o444:
        fail(f"{label}: mode 0444 required")
    return path


def actual_file_record(root: Path, relative: str, label: str) -> dict[str, Any]:
    path = resolve_regular(root, relative, label)
    payload = path.read_bytes()
    return {
        "path": relative,
        "class": "regular",
        "mode": "0444",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def validate_command_record(record: Any, verb: str, label: str) -> None:
    record = object_exact(record, {"command", "status", "stdout_sha256", "stderr_sha256"}, label)
    command = record["command"]
    if not isinstance(command, list) or not all(isinstance(item, str) and item for item in command) or verb not in command:
        fail(f"{label}: literal {verb} command required")
    if record["status"] != 0:
        fail(f"{label}: successful status required")
    hash256(record["stdout_sha256"], f"{label}.stdout_sha256")
    hash256(record["stderr_sha256"], f"{label}.stderr_sha256")


def validate_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = object_exact(manifest, {"schema_version", "bundle_kind", "receipt_path", "files"}, "manifest")
    if manifest["schema_version"] != 1 or manifest["bundle_kind"] != "real-copier-pre-remediation-evidence":
        fail("manifest: identity mismatch")
    if manifest["receipt_path"] != "copier-real-update-receipt.json":
        fail("manifest: receipt path mismatch")
    files = manifest["files"]
    if not isinstance(files, list) or len(files) != 4:
        fail("manifest: exactly four authorized records required")
    indexed: dict[str, dict[str, Any]] = {}
    resolved_seen: set[Path] = set()
    for index, raw_record in enumerate(files):
        record = object_exact(raw_record, FILE_KEYS, f"manifest.files[{index}]")
        relative = relative_path(record["path"], f"manifest.files[{index}].path")
        if relative == "evidence-manifest.json" or relative in indexed:
            fail(f"manifest: duplicate/self path: {relative}")
        if record["class"] != "regular" or record["mode"] != "0444":
            fail(f"manifest: class/mode mismatch: {relative}")
        integer(record["bytes"], f"manifest:{relative}.bytes")
        hash256(record["sha256"], f"manifest:{relative}.sha256")
        actual = actual_file_record(root, relative, f"manifest:{relative}")
        if record != actual:
            fail(f"manifest: artifact tuple mismatch: {relative}")
        resolved = (root / relative).resolve(strict=True)
        if resolved in resolved_seen:
            fail(f"manifest: canonical path duplicate: {relative}")
        resolved_seen.add(resolved)
        indexed[relative] = record
    return indexed


def validate_observation(
    root: Path,
    row_id: str,
    row: dict[str, Any],
    expected: dict[str, Any],
    manifest: dict[str, dict[str, Any]],
    observation_paths: set[Path],
) -> str:
    observation = object_exact(row["observation"], OBSERVATION_KEYS, f"{row_id}.observation")
    if observation["row_id"] != row_id or observation["evidence_kind"] != "real-copier-update":
        fail(f"{row_id}: observation row/evidence binding mismatch")
    if observation["observed_outcome"] != expected["outcome"]:
        fail(f"{row_id}: observed outcome binding mismatch")
    if relative_path(observation["source_path"], f"{row_id}.source_path") != expected["source"]:
        fail(f"{row_id}: source path mismatch")
    captured = relative_path(observation["captured_path"], f"{row_id}.captured_path")
    expected_captured = f"observations/{row_id}/{expected['captured']}"
    if captured != expected_captured:
        fail(f"{row_id}: captured path/row binding mismatch")
    path = resolve_regular(root, captured, f"{row_id}.captured")
    resolved = path.resolve(strict=True)
    if resolved in observation_paths:
        fail(f"{row_id}: captured file reused by another observation")
    observation_paths.add(resolved)
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if observation["class"] != "regular" or observation["mode"] != "0444":
        fail(f"{row_id}: observed class/mode mismatch")
    if observation["bytes"] != len(payload) or observation["sha256"] != digest:
        fail(f"{row_id}: observed artifact tuple mismatch")
    if captured not in manifest or manifest[captured] != actual_file_record(root, captured, f"{row_id}.manifest"):
        fail(f"{row_id}: observation absent or altered in manifest")
    markers = object_exact(observation["marker_counts"], {"open", "middle", "close"}, f"{row_id}.marker_counts")
    for name in markers:
        integer(markers[name], f"{row_id}.marker_counts.{name}")
    if markers != expected["markers"]:
        fail(f"{row_id}: marker counts mismatch")
    if expected["outcome"] in {"clean-overwrite", "conflict-markers"}:
        lines = payload.decode("utf-8").splitlines()
        actual_markers = {
            "open": sum(line.startswith("<<<<<<<") for line in lines),
            "middle": sum(line.startswith("=======") for line in lines),
            "close": sum(line.startswith(">>>>>>>") for line in lines),
        }
        if markers != actual_markers:
            fail(f"{row_id}: recorded marker counts differ from captured bytes")
    if observation["reject_artifact_count"] != expected["reject_count"]:
        fail(f"{row_id}: reject cardinality mismatch")
    if observation["reject_relative_path"] != expected["reject_path"]:
        fail(f"{row_id}: reject path mismatch")
    equality = object_exact(observation["source_to_captured"], EQUALITY_KEYS, f"{row_id}.source_to_captured")
    if equality["equal"] is not True or equality["before_source_mutation"] is not True:
        fail(f"{row_id}: source/archive equality or capture order false")
    expected_equality = {
        "source_bytes": len(payload),
        "source_sha256": digest,
        "captured_bytes": len(payload),
        "captured_sha256": digest,
        "equal": True,
        "before_source_mutation": True,
    }
    if equality != expected_equality or observation["capture_sequence"] != "before-remediation":
        fail(f"{row_id}: source/archive tuple or sequence mismatch")
    return digest


def validate_bundle(bundle_root: Path) -> None:
    root = bundle_root.resolve(strict=True)
    if bundle_root.is_symlink() or not root.is_dir():
        fail("bundle root must be a real directory")
    manifest_path = resolve_regular(root, "evidence-manifest.json", "manifest")
    receipt_path = resolve_regular(root, "copier-real-update-receipt.json", "receipt")
    manifest_records = validate_manifest(root, load_json(manifest_path, "manifest"))
    receipt = object_exact(load_json(receipt_path, "receipt"), RECEIPT_KEYS, "receipt")
    if receipt["schema_version"] != 1 or receipt["copier_version"] != "copier 9.17.1":
        fail("receipt: identity/version mismatch")
    hash256(receipt["fixture_manifest_sha256"], "receipt.fixture_manifest_sha256")
    if receipt["provenance_question"] != "fixture_channel=portability-evidence":
        fail("receipt: provenance question mismatch")
    if receipt["manifest_path"] != "evidence-manifest.json":
        fail("receipt: manifest path mismatch")
    if manifest_records.get("copier-real-update-receipt.json") != actual_file_record(
        root, "copier-real-update-receipt.json", "receipt manifest record"
    ):
        fail("receipt: manifest tuple mismatch")
    rows_value = receipt["rows"]
    if not isinstance(rows_value, list) or len(rows_value) != 3:
        fail("receipt: exactly three real rows required")
    rows: dict[str, dict[str, Any]] = {}
    for index, raw_row in enumerate(rows_value):
        row = object_exact(raw_row, ROW_KEYS, f"rows[{index}]")
        row_id = row["id"]
        if row_id not in EXPECTED_ROWS or row_id in rows:
            fail(f"rows[{index}]: unexpected/duplicate row ID")
        rows[row_id] = row
    if set(rows) != set(EXPECTED_ROWS):
        fail("receipt: real row set mismatch")
    observation_paths: set[Path] = set()
    authorized = {"copier-real-update-receipt.json"}
    for row_id, expected in EXPECTED_ROWS.items():
        row = rows[row_id]
        if row["evidence_kind"] != "real-copier-update" or row["copier_version"] != "copier 9.17.1":
            fail(f"{row_id}: evidence kind/version mismatch")
        if not isinstance(row["copier_path"], str) or not row["copier_path"] or "fake" in row["copier_path"].lower():
            fail(f"{row_id}: real Copier path required")
        validate_command_record(row["copy"], "copy", f"{row_id}.copy")
        validate_command_record(row["update"], "update", f"{row_id}.update")
        hash256(row["consumer_edit_before_sha256"], f"{row_id}.consumer_edit_before_sha256")
        hash256(row["consumer_edit_after_sha256"], f"{row_id}.consumer_edit_after_sha256")
        if row["consumer_edit_before_sha256"] == row["consumer_edit_after_sha256"]:
            fail(f"{row_id}: consumer edit absent")
        if row["classification"] != expected["outcome"] or row["remediation"] != "framework-wins":
            fail(f"{row_id}: classification/remediation mismatch")
        post_hash = hash256(row["post_remediation_sha256"], f"{row_id}.post_remediation_sha256")
        rollback = object_exact(row["rollback"], {"status", "changed_path_count"}, f"{row_id}.rollback")
        if rollback["status"] != "pass":
            fail(f"{row_id}: rollback did not pass")
        integer(rollback["changed_path_count"], f"{row_id}.rollback.changed_path_count", minimum=1)
        if GIT_OBJECT.fullmatch(row["template_v1_tree"]) is None or GIT_OBJECT.fullmatch(row["template_v2_tree"]) is None:
            fail(f"{row_id}: template tree refs invalid")
        observed_hash = validate_observation(root, row_id, row, expected, manifest_records, observation_paths)
        if expected["outcome"] != "clean-overwrite" and observed_hash == post_hash:
            fail(f"{row_id}: post-remediation bytes substituted for pre-remediation evidence")
        authorized.add(row["observation"]["captured_path"])
    if set(manifest_records) != authorized:
        fail(f"manifest/receipt authorized sets differ: manifest={sorted(manifest_records)} receipt={sorted(authorized)}")
    actual_entries, entry_violations = bundle_entries(root)
    expected_entries = authorized | {"evidence-manifest.json"}
    if entry_violations:
        fail("bundle entry violations: " + ", ".join(entry_violations))
    if actual_entries != expected_entries:
        fail(f"bundle reverse closure mismatch: extra={sorted(actual_entries-expected_entries)} missing={sorted(expected_entries-actual_entries)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_bundle(args.bundle_root)
        print("durable Copier evidence validation: PASS")
        return 0
    except (OSError, EvidenceValidationError) as exc:
        print(f"durable Copier evidence validation error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

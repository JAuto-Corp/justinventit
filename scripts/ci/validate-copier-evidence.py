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
        "payload_identity": "canonical-v2-generated-skill",
        "markers": {"open": 0, "middle": 0, "close": 0},
        "reject_count": 0,
        "reject_path": None,
    },
    "real-inline-conflict": {
        "outcome": "conflict-markers",
        "source": ".claude/skills/copier-conflict-fixture/SKILL.md",
        "captured": "pre-remediation.generated.SKILL.md",
        "payload_identity": "copier-inline-conflict-v1-consumer-v2",
        "markers": {"open": 1, "middle": 1, "close": 1},
        "reject_count": 0,
        "reject_path": None,
    },
    "real-reject-conflict": {
        "outcome": "reject-artifact",
        "source": ".claude/skills/copier-conflict-fixture/SKILL.md.rej",
        "captured": "pre-remediation.reject.SKILL.md.rej",
        "payload_identity": "copier-reject-patch-v1-consumer-v2",
        "markers": {"open": 0, "middle": 0, "close": 0},
        "reject_count": 1,
        "reject_path": ".claude/skills/copier-conflict-fixture/SKILL.md.rej",
    },
}
RECEIPT_KEYS = {
    "schema_version", "copier_version", "fixture_manifest_sha256", "provenance_question",
    "manifest_path", "authority_sha256", "rows",
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
AUTHORITY_KEYS = {
    "schema_version", "authority_kind", "copier_version", "fixture_manifest",
    "template_trees", "rows",
}
AUTHORITY_FIXTURE_KEYS = {"path", "sha256"}
AUTHORITY_ROW_KEYS = {"observation", "post_remediation", "consumer_transition"}
AUTHORITY_OBSERVATION_KEYS = {
    "payload_identity", "source_path", "captured_path", "bytes", "sha256", "outcome",
    "marker_counts", "reject_artifact_count", "reject_relative_path",
}
AUTHORITY_POST_KEYS = {"path", "bytes", "sha256"}
AUTHORITY_CONSUMER_KEYS = {"before_sha256", "after_sha256"}
HASH = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT = re.compile(r"^[0-9a-f]{40}$")
SOURCE_ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = SOURCE_ROOT / "scripts/ci/fixtures/copier-portability/evidence-r4-authority.json"
FIXTURE_MANIFEST_RELATIVE = "scripts/ci/fixtures/copier-portability/manifest.json"
CANONICAL_V2_RELATIVE = (
    "scripts/ci/fixtures/copier-portability/v2/template/.claude/skills/"
    "copier-conflict-fixture/SKILL.md"
)


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


def source_regular(relative: str, label: str) -> Path:
    relative_path(relative, label)
    path = SOURCE_ROOT / relative
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise EvidenceValidationError(f"independent authority {label}: missing source artifact") from exc
    if resolved == SOURCE_ROOT or SOURCE_ROOT not in resolved.parents or path.is_symlink():
        fail(f"independent authority {label}: source path escapes or is a symlink")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail(f"independent authority {label}: unique regular source file required")
    return path


def validate_authority() -> tuple[dict[str, Any], str]:
    if AUTHORITY_PATH.is_symlink() or not AUTHORITY_PATH.is_file():
        fail("independent authority: committed authority file missing or non-regular")
    authority_info = AUTHORITY_PATH.stat()
    if not stat.S_ISREG(authority_info.st_mode) or authority_info.st_nlink != 1:
        fail("independent authority: committed authority must be a unique regular file")
    authority = object_exact(
        load_json(AUTHORITY_PATH, "independent authority"),
        AUTHORITY_KEYS,
        "independent authority",
    )
    if (
        authority["schema_version"] != 1
        or authority["authority_kind"] != "real-copier-evidence-fixture-authority"
        or authority["copier_version"] != "copier 9.17.1"
    ):
        fail("independent authority: identity/version mismatch")

    fixture = object_exact(
        authority["fixture_manifest"],
        AUTHORITY_FIXTURE_KEYS,
        "independent authority.fixture_manifest",
    )
    if fixture["path"] != FIXTURE_MANIFEST_RELATIVE:
        fail("independent authority: fixture manifest path mismatch")
    fixture_digest = hash256(fixture["sha256"], "independent authority.fixture_manifest.sha256")
    if hashlib.sha256(
        source_regular(fixture["path"], "fixture manifest").read_bytes()
    ).hexdigest() != fixture_digest:
        fail("independent authority: committed fixture manifest mismatch")

    trees = object_exact(
        authority["template_trees"],
        {"v1", "v2"},
        "independent authority.template_trees",
    )
    if (
        not isinstance(trees["v1"], str)
        or not isinstance(trees["v2"], str)
        or GIT_OBJECT.fullmatch(trees["v1"]) is None
        or GIT_OBJECT.fullmatch(trees["v2"]) is None
        or trees["v1"] == trees["v2"]
    ):
        fail("independent authority: exact distinct v1/v2 tree IDs required")

    rows = authority["rows"]
    if not isinstance(rows, dict) or set(rows) != set(EXPECTED_ROWS):
        fail("independent authority: exact row set required")
    canonical_digest: str | None = None
    for row_id, expected in EXPECTED_ROWS.items():
        row = object_exact(rows[row_id], AUTHORITY_ROW_KEYS, f"independent authority.rows.{row_id}")
        observation = object_exact(
            row["observation"],
            AUTHORITY_OBSERVATION_KEYS,
            f"independent authority.rows.{row_id}.observation",
        )
        expected_observation_identity = {
            "payload_identity": expected["payload_identity"],
            "source_path": expected["source"],
            "captured_path": f"observations/{row_id}/{expected['captured']}",
            "outcome": expected["outcome"],
            "marker_counts": expected["markers"],
            "reject_artifact_count": expected["reject_count"],
            "reject_relative_path": expected["reject_path"],
        }
        observed_identity = {
            key: observation[key]
            for key in expected_observation_identity
        }
        if observed_identity != expected_observation_identity:
            fail(f"independent authority: {row_id} observation identity mismatch")
        integer(observation["bytes"], f"independent authority.{row_id}.observation.bytes", minimum=1)
        hash256(observation["sha256"], f"independent authority.{row_id}.observation.sha256")

        post = object_exact(
            row["post_remediation"],
            AUTHORITY_POST_KEYS,
            f"independent authority.rows.{row_id}.post_remediation",
        )
        if post["path"] != CANONICAL_V2_RELATIVE:
            fail(f"independent authority: {row_id} canonical v2 path mismatch")
        post_bytes = integer(
            post["bytes"],
            f"independent authority.{row_id}.post_remediation.bytes",
            minimum=1,
        )
        post_digest = hash256(
            post["sha256"],
            f"independent authority.{row_id}.post_remediation.sha256",
        )
        canonical = source_regular(post["path"], f"{row_id} canonical v2 projection")
        canonical_payload = canonical.read_bytes()
        if len(canonical_payload) != post_bytes or hashlib.sha256(canonical_payload).hexdigest() != post_digest:
            fail(f"independent authority: {row_id} canonical v2 projection mismatch")
        if canonical_digest is None:
            canonical_digest = post_digest
        elif canonical_digest != post_digest:
            fail("independent authority: canonical post-remediation digests disagree")

        consumer = object_exact(
            row["consumer_transition"],
            AUTHORITY_CONSUMER_KEYS,
            f"independent authority.rows.{row_id}.consumer_transition",
        )
        before = hash256(
            consumer["before_sha256"],
            f"independent authority.{row_id}.consumer_transition.before_sha256",
        )
        after = hash256(
            consumer["after_sha256"],
            f"independent authority.{row_id}.consumer_transition.after_sha256",
        )
        if before == after:
            fail(f"independent authority: {row_id} consumer transition collapsed")

    return authority, hashlib.sha256(AUTHORITY_PATH.read_bytes()).hexdigest()


def bundle_entries(root: Path) -> tuple[set[str], list[str]]:
    entries: set[str] = set()
    violations: list[str] = []
    for directory, directories, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(directory)
        for name in list(directories):
            path = base / name
            entries.add(path.relative_to(root).as_posix())
            if path.is_symlink():
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


def implied_parent_directories(paths: set[str]) -> set[str]:
    directories: set[str] = set()
    for relative in paths:
        parent = Path(relative).parent
        while parent != Path("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


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
    authority: dict[str, Any],
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
    authority_projection = {
        "source_path": authority["source_path"],
        "captured_path": authority["captured_path"],
        "bytes": authority["bytes"],
        "sha256": authority["sha256"],
        "outcome": authority["outcome"],
        "marker_counts": authority["marker_counts"],
        "reject_artifact_count": authority["reject_artifact_count"],
        "reject_relative_path": authority["reject_relative_path"],
    }
    observed_projection = {
        "source_path": observation["source_path"],
        "captured_path": observation["captured_path"],
        "bytes": observation["bytes"],
        "sha256": observation["sha256"],
        "outcome": observation["observed_outcome"],
        "marker_counts": observation["marker_counts"],
        "reject_artifact_count": observation["reject_artifact_count"],
        "reject_relative_path": observation["reject_relative_path"],
    }
    if (
        observed_projection != authority_projection
        or len(payload) != authority["bytes"]
        or digest != authority["sha256"]
    ):
        fail(f"{row_id}: independent authority pre-remediation payload mismatch")
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
    authority, authority_digest = validate_authority()
    root = bundle_root.resolve(strict=True)
    if bundle_root.is_symlink() or not root.is_dir():
        fail("bundle root must be a real directory")
    manifest_path = resolve_regular(root, "evidence-manifest.json", "manifest")
    receipt_path = resolve_regular(root, "copier-real-update-receipt.json", "receipt")
    manifest_records = validate_manifest(root, load_json(manifest_path, "manifest"))
    receipt = object_exact(load_json(receipt_path, "receipt"), RECEIPT_KEYS, "receipt")
    if receipt["schema_version"] != 1 or receipt["copier_version"] != "copier 9.17.1":
        fail("receipt: identity/version mismatch")
    receipt_authority = hash256(receipt["authority_sha256"], "receipt.authority_sha256")
    if receipt_authority != authority_digest:
        fail("receipt: independent authority hash mismatch")
    fixture_manifest_sha256 = hash256(
        receipt["fixture_manifest_sha256"],
        "receipt.fixture_manifest_sha256",
    )
    if fixture_manifest_sha256 != authority["fixture_manifest"]["sha256"]:
        fail("receipt: independent authority fixture manifest mismatch")
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
        authority_row = authority["rows"][row_id]
        if row["evidence_kind"] != "real-copier-update" or row["copier_version"] != "copier 9.17.1":
            fail(f"{row_id}: evidence kind/version mismatch")
        if not isinstance(row["copier_path"], str) or not row["copier_path"] or "fake" in row["copier_path"].lower():
            fail(f"{row_id}: real Copier path required")
        validate_command_record(row["copy"], "copy", f"{row_id}.copy")
        validate_command_record(row["update"], "update", f"{row_id}.update")
        consumer_before = hash256(
            row["consumer_edit_before_sha256"],
            f"{row_id}.consumer_edit_before_sha256",
        )
        consumer_after = hash256(
            row["consumer_edit_after_sha256"],
            f"{row_id}.consumer_edit_after_sha256",
        )
        if consumer_before == consumer_after:
            fail(f"{row_id}: consumer edit absent")
        if (
            consumer_before != authority_row["consumer_transition"]["before_sha256"]
            or consumer_after != authority_row["consumer_transition"]["after_sha256"]
        ):
            fail(f"{row_id}: independent authority consumer transition mismatch")
        if row["classification"] != expected["outcome"] or row["remediation"] != "framework-wins":
            fail(f"{row_id}: classification/remediation mismatch")
        post_hash = hash256(row["post_remediation_sha256"], f"{row_id}.post_remediation_sha256")
        if post_hash != authority_row["post_remediation"]["sha256"]:
            fail(f"{row_id}: post-remediation authority mismatch")
        rollback = object_exact(row["rollback"], {"status", "changed_path_count"}, f"{row_id}.rollback")
        if rollback["status"] != "pass":
            fail(f"{row_id}: rollback did not pass")
        integer(rollback["changed_path_count"], f"{row_id}.rollback.changed_path_count", minimum=1)
        if (
            not isinstance(row["template_v1_tree"], str)
            or not isinstance(row["template_v2_tree"], str)
            or GIT_OBJECT.fullmatch(row["template_v1_tree"]) is None
            or GIT_OBJECT.fullmatch(row["template_v2_tree"]) is None
        ):
            fail(f"{row_id}: template tree refs invalid")
        if (
            row["template_v1_tree"] != authority["template_trees"]["v1"]
            or row["template_v2_tree"] != authority["template_trees"]["v2"]
        ):
            fail(f"{row_id}: independent authority template tree mismatch")
        observed_hash = validate_observation(
            root,
            row_id,
            row,
            expected,
            authority_row["observation"],
            manifest_records,
            observation_paths,
        )
        if expected["outcome"] != "clean-overwrite" and observed_hash == post_hash:
            fail(f"{row_id}: post-remediation bytes substituted for pre-remediation evidence")
        authorized.add(row["observation"]["captured_path"])
    if set(manifest_records) != authorized:
        fail(f"manifest/receipt authorized sets differ: manifest={sorted(manifest_records)} receipt={sorted(authorized)}")
    actual_entries, entry_violations = bundle_entries(root)
    expected_files = authorized | {"evidence-manifest.json"}
    expected_entries = expected_files | implied_parent_directories(expected_files)
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

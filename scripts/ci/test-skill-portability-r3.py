#!/usr/bin/env python3
"""R3 acceptance for durable real-Copier pre-remediation evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_PATH = ROOT / "scripts/ci/fixtures/copier-evidence-r3.expected.json"
COPIER_FIXTURE = ROOT / "scripts/ci/fixtures/copier-portability"
PRODUCER = ROOT / "scripts/ci/copier-real-update-receipt.py"
VALIDATOR = ROOT / "scripts/ci/validate-copier-evidence.py"
FAILURES: list[str] = []
PASSES = 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def report(case_id: str, failure: str | None) -> None:
    global PASSES
    if failure is None:
        PASSES += 1
        print(f"[R3-PASS] {case_id}")
    else:
        FAILURES.append(f"{case_id}:{failure}")
        print(f"[R3-FAIL] {case_id}: {failure}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def write_json_0444(path: Path, value: dict[str, Any]) -> None:
    if path.exists() and not path.is_symlink():
        path.chmod(0o644)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o444)


def file_record(path: Path, relative: str) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": relative,
        "class": "regular",
        "mode": "0444",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def manifest_index(bundle: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = load_json(bundle / "evidence-manifest.json")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("manifest files list missing")
    return manifest, {record["path"]: record for record in records}


def refresh_manifest_record(bundle: Path, relative: str) -> None:
    manifest_path = bundle / "evidence-manifest.json"
    manifest = load_json(manifest_path)
    records = manifest["files"]
    matches = [index for index, record in enumerate(records) if record.get("path") == relative]
    if len(matches) != 1:
        raise ValueError(f"manifest path cardinality for {relative}: {len(matches)}")
    records[matches[0]] = file_record(bundle / relative, relative)
    write_json_0444(manifest_path, manifest)


def edit_receipt(bundle: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    path = bundle / "copier-real-update-receipt.json"
    receipt = load_json(path)
    edit(receipt)
    write_json_0444(path, receipt)
    refresh_manifest_record(bundle, "copier-real-update-receipt.json")


def edit_manifest(bundle: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    path = bundle / "evidence-manifest.json"
    manifest = load_json(path)
    edit(manifest)
    write_json_0444(path, manifest)


def receipt_rows(bundle: Path) -> dict[str, dict[str, Any]]:
    receipt = load_json(bundle / "copier-real-update-receipt.json")
    return {row["id"]: row for row in receipt["rows"]}


def observation_path(bundle: Path, row_id: str) -> Path:
    return bundle / receipt_rows(bundle)[row_id]["observation"]["captured_path"]


def produce_bundle(bundle: Path) -> str | None:
    result = run(
        [
            sys.executable,
            str(PRODUCER),
            "--project-root", str(ROOT),
            "--fixture-root", str(COPIER_FIXTURE),
            "--output-root", str(bundle),
        ]
    )
    if result.returncode != 0:
        return f"real producer exit={result.returncode}: {(result.stdout + result.stderr)[-1800:]}"
    return None


def test_durable_observations(bundle: Path, expected: dict[str, Any]) -> None:
    receipt_path = bundle / "copier-real-update-receipt.json"
    manifest_path = bundle / "evidence-manifest.json"
    if not receipt_path.is_file() or not manifest_path.is_file():
        report("R3-01-durable-pre-remediation", "receipt or evidence manifest missing")
        return
    try:
        receipt = load_json(receipt_path)
        rows = {row["id"]: row for row in receipt.get("rows", [])}
        manifest, manifest_records = manifest_index(bundle)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        report("R3-01-durable-pre-remediation", f"bundle schema unreadable: {exc}")
        return
    failures: list[str] = []
    expected_rows = expected["rows"]
    if set(rows) != set(expected_rows) or len(rows) != 3:
        failures.append("real row IDs/cardinality")
    required = set(expected["observation_required"])
    authorized = {"copier-real-update-receipt.json"}
    for row_id, row_expected in expected_rows.items():
        row = rows.get(row_id, {})
        observation = row.get("observation")
        if not isinstance(observation, dict):
            failures.append(f"{row_id}: observation missing")
            continue
        if set(observation) != required:
            failures.append(f"{row_id}: observation not closed")
            continue
        captured = observation.get("captured_path")
        if not isinstance(captured, str) or captured.startswith("/") or ".." in Path(captured).parts:
            failures.append(f"{row_id}: captured path not bundle-relative")
            continue
        authorized.add(captured)
        path = bundle / captured
        if path.is_symlink() or not path.is_file():
            failures.append(f"{row_id}: captured regular file missing")
            continue
        info = path.stat()
        payload = path.read_bytes()
        if stat.S_IMODE(info.st_mode) != 0o444 or info.st_nlink != 1:
            failures.append(f"{row_id}: captured mode/link class")
        if observation.get("class") != "regular" or observation.get("mode") != "0444":
            failures.append(f"{row_id}: recorded class/mode")
        if observation.get("bytes") != len(payload) or observation.get("sha256") != hashlib.sha256(payload).hexdigest():
            failures.append(f"{row_id}: captured tuple")
        if observation.get("row_id") != row_id or observation.get("evidence_kind") != "real-copier-update":
            failures.append(f"{row_id}: row/evidence binding")
        if observation.get("observed_outcome") != row_expected["outcome"]:
            failures.append(f"{row_id}: outcome binding")
        if observation.get("marker_counts") != row_expected["marker_counts"]:
            failures.append(f"{row_id}: marker counts")
        if observation.get("reject_artifact_count") != row_expected["reject_artifact_count"]:
            failures.append(f"{row_id}: reject count")
        equality = observation.get("source_to_captured")
        if not isinstance(equality, dict) or equality.get("equal") is not True or equality.get("before_source_mutation") is not True:
            failures.append(f"{row_id}: source/archive equality/order")
        elif (
            equality.get("source_bytes") != len(payload)
            or equality.get("captured_bytes") != len(payload)
            or equality.get("source_sha256") != hashlib.sha256(payload).hexdigest()
            or equality.get("captured_sha256") != hashlib.sha256(payload).hexdigest()
        ):
            failures.append(f"{row_id}: source/archive tuple")
        if observation.get("capture_sequence") != "before-remediation":
            failures.append(f"{row_id}: capture sequence")
        if row.get("classification") != row_expected["outcome"] or row.get("remediation") != "framework-wins":
            failures.append(f"{row_id}: later classification/remediation")
        rollback = row.get("rollback")
        if not isinstance(rollback, dict) or rollback.get("status") != "pass":
            failures.append(f"{row_id}: later rollback")
        post_hash = row.get("post_remediation_sha256")
        if not isinstance(post_hash, str) or len(post_hash) != 64:
            failures.append(f"{row_id}: post-remediation hash")
        if row_expected["outcome"] != "clean-overwrite" and post_hash == observation.get("sha256"):
            failures.append(f"{row_id}: pre/post evidence collapsed")
        if captured not in manifest_records or manifest_records[captured] != file_record(path, captured):
            failures.append(f"{row_id}: manifest observation record")
    if manifest.get("bundle_kind") != expected["bundle_kind"]:
        failures.append("manifest bundle kind")
    if set(manifest_records) != authorized:
        failures.append("manifest authorized set")
    receipt_record = manifest_records.get("copier-real-update-receipt.json")
    if receipt_record != file_record(receipt_path, "copier-real-update-receipt.json"):
        failures.append("manifest receipt record")
    report("R3-01-durable-pre-remediation", ", ".join(failures[:12]) if failures else None)


def update_observation(bundle: Path, row_id: str, edit: Callable[[dict[str, Any], dict[str, Any]], None]) -> None:
    def mutate(receipt: dict[str, Any]) -> None:
        row = next(item for item in receipt["rows"] if item["id"] == row_id)
        edit(row, row["observation"])
    edit_receipt(bundle, mutate)


def mutate_bundle(case_id: str, bundle: Path) -> None:
    row_for_suffix = {
        "clean": "real-clean-update",
        "inline": "real-inline-conflict",
        "reject": "real-reject-conflict",
    }
    if case_id.startswith("remove-observation-"):
        row_id = row_for_suffix[case_id.rsplit("-", 1)[1]]
        edit_receipt(bundle, lambda receipt: next(row for row in receipt["rows"] if row["id"] == row_id).pop("observation"))
        return
    if case_id.startswith("remove-captured-file-"):
        row_id = row_for_suffix[case_id.rsplit("-", 1)[1]]
        observation_path(bundle, row_id).unlink()
        return
    if case_id == "classification-only-all":
        edit_receipt(bundle, lambda receipt: [row.pop("observation") for row in receipt["rows"]])
        return
    if case_id in {"alter-source-path", "path-outside-root"}:
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("source_path", "../outside/SKILL.md"))
        return
    if case_id == "alter-captured-path":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("captured_path", "observations/wrong/file"))
        return
    if case_id == "alter-class":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("class", "symlink"))
        return
    if case_id == "alter-recorded-mode":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("mode", "0644"))
        return
    if case_id == "alter-file-mode":
        observation_path(bundle, "real-inline-conflict").chmod(0o644)
        return
    if case_id == "alter-size":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("bytes", obs["bytes"] + 1))
        return
    if case_id == "alter-hash":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("sha256", "0" * 64))
        return
    if case_id.startswith("alter-marker-"):
        key = case_id.removeprefix("alter-marker-")
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs["marker_counts"].__setitem__(key, obs["marker_counts"][key] + 1))
        return
    if case_id == "alter-reject-count":
        update_observation(bundle, "real-reject-conflict", lambda _row, obs: obs.__setitem__("reject_artifact_count", 0))
        return
    if case_id == "alter-reject-relative-path":
        update_observation(bundle, "real-reject-conflict", lambda _row, obs: obs.__setitem__("reject_relative_path", "wrong.rej"))
        return
    if case_id == "alter-row-binding":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("row_id", "real-reject-conflict"))
        return
    if case_id == "alter-outcome-binding":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs.__setitem__("observed_outcome", "clean-overwrite"))
        return
    equality_fields = {
        "alter-source-size": "source_bytes",
        "alter-source-hash": "source_sha256",
        "alter-captured-size": "captured_bytes",
        "alter-captured-hash": "captured_sha256",
    }
    if case_id in equality_fields:
        field = equality_fields[case_id]
        def change(_row: dict[str, Any], obs: dict[str, Any]) -> None:
            current = obs["source_to_captured"][field]
            obs["source_to_captured"][field] = current + 1 if isinstance(current, int) else "0" * 64
        update_observation(bundle, "real-inline-conflict", change)
        return
    if case_id == "alter-source-captured-equality":
        update_observation(bundle, "real-inline-conflict", lambda _row, obs: obs["source_to_captured"].__setitem__("equal", False))
        return
    if case_id == "alter-capture-order":
        def order(_row: dict[str, Any], obs: dict[str, Any]) -> None:
            obs["capture_sequence"] = "after-remediation"
            obs["source_to_captured"]["before_source_mutation"] = False
        update_observation(bundle, "real-inline-conflict", order)
        return
    if case_id == "alter-remediation":
        update_observation(bundle, "real-inline-conflict", lambda row, _obs: row.__setitem__("remediation", "consumer-wins"))
        return
    if case_id == "alter-post-remediation-hash":
        update_observation(bundle, "real-inline-conflict", lambda row, obs: row.__setitem__("post_remediation_sha256", obs["sha256"]))
        return
    if case_id == "alter-rollback-result":
        update_observation(bundle, "real-inline-conflict", lambda row, _obs: row["rollback"].__setitem__("status", "fail"))
        return
    if case_id in {"symlink-artifact", "hardlink-artifact"}:
        path = observation_path(bundle, "real-inline-conflict")
        payload = path.read_bytes()
        path.unlink()
        backing = bundle.parent / f"{case_id}.backing"
        backing.write_bytes(payload)
        if case_id == "symlink-artifact":
            path.symlink_to(backing)
        else:
            os.link(backing, path)
            path.chmod(0o444)
        return
    if case_id == "duplicate-record-path":
        rows = receipt_rows(bundle)
        inline = rows["real-inline-conflict"]["observation"]
        def duplicate(_row: dict[str, Any], obs: dict[str, Any]) -> None:
            obs["captured_path"] = inline["captured_path"]
            for field in ("class", "mode", "bytes", "sha256"):
                obs[field] = inline[field]
            obs["source_to_captured"] = dict(inline["source_to_captured"])
        update_observation(bundle, "real-reject-conflict", duplicate)
        return
    if case_id == "substitute-post-remediation-bytes":
        path = observation_path(bundle, "real-inline-conflict")
        payload = (COPIER_FIXTURE / "v2/template/.claude/skills/copier-conflict-fixture/SKILL.md").read_bytes()
        path.chmod(0o644)
        path.write_bytes(payload)
        path.chmod(0o444)
        relative = path.relative_to(bundle).as_posix()
        refresh_manifest_record(bundle, relative)
        digest = hashlib.sha256(payload).hexdigest()
        def substitute(_row: dict[str, Any], obs: dict[str, Any]) -> None:
            obs["bytes"] = len(payload)
            obs["sha256"] = digest
            obs["marker_counts"] = {"open": 0, "middle": 0, "close": 0}
            obs["source_to_captured"].update({
                "source_bytes": len(payload), "source_sha256": digest,
                "captured_bytes": len(payload), "captured_sha256": digest,
            })
        update_observation(bundle, "real-inline-conflict", substitute)
        return
    if case_id == "extra-nested-receipt":
        extra = bundle / "observations/unreferenced/nested/receipt.json"
        extra.parent.mkdir(parents=True)
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o444)
        return
    if case_id == "extra-symlink-alias":
        extra = bundle / "observations/unreferenced-alias"
        extra.symlink_to(observation_path(bundle, "real-clean-update"))
        return
    if case_id == "extra-artifact":
        extra = bundle / "observations/unreferenced.bin"
        extra.write_bytes(b"unreferenced\n")
        extra.chmod(0o444)
        return
    if case_id.startswith("manifest-"):
        if case_id == "manifest-remove-receipt":
            edit_manifest(bundle, lambda manifest: manifest["files"].__setitem__(slice(None), [r for r in manifest["files"] if r["path"] != "copier-real-update-receipt.json"]))
            return
        if case_id == "manifest-remove-observation":
            target = receipt_rows(bundle)["real-inline-conflict"]["observation"]["captured_path"]
            edit_manifest(bundle, lambda manifest: manifest["files"].__setitem__(slice(None), [r for r in manifest["files"] if r["path"] != target]))
            return
        if case_id == "manifest-launder-extra-file":
            extra = bundle / "observations/laundered-extra.bin"
            extra.parent.mkdir(parents=True, exist_ok=True)
            extra.write_bytes(b"laundered\n")
            extra.chmod(0o444)
            edit_manifest(bundle, lambda manifest: manifest["files"].append(file_record(extra, extra.relative_to(bundle).as_posix())))
            return
        def alter_record(manifest: dict[str, Any]) -> None:
            record = manifest["files"][0]
            if case_id == "manifest-alter-path":
                record["path"] = "observations/wrong"
            elif case_id == "manifest-alter-class":
                record["class"] = "symlink"
            elif case_id == "manifest-alter-mode":
                record["mode"] = "0644"
            elif case_id == "manifest-alter-size":
                record["bytes"] += 1
            elif case_id == "manifest-alter-hash":
                record["sha256"] = "0" * 64
            elif case_id == "manifest-duplicate-path":
                manifest["files"][1]["path"] = record["path"]
            else:
                raise ValueError(case_id)
        edit_manifest(bundle, alter_record)
        return
    raise ValueError(f"unimplemented mutation: {case_id}")


def test_reverse_closure(bundle: Path, expected: dict[str, Any], temp_root: Path) -> None:
    if not VALIDATOR.is_file():
        report("R3-02-reverse-artifact-closure", "production Copier evidence validator missing")
        return
    control = run([sys.executable, str(VALIDATOR), "--bundle-root", str(bundle)])
    if control.returncode != 0:
        report("R3-02-reverse-artifact-closure", f"valid bundle rejected: {(control.stdout + control.stderr)[-1400:]}")
        return
    mutation_ids = expected["mutation_ids"]
    failures: list[str] = []
    actual = 0
    for case_id in mutation_ids:
        mutated = temp_root / f"mutation-{case_id}"
        shutil.copytree(bundle, mutated, symlinks=True)
        try:
            mutate_bundle(case_id, mutated)
        except Exception as exc:
            failures.append(f"{case_id}:harness:{exc}")
            continue
        result = run([sys.executable, str(VALIDATOR), "--bundle-root", str(mutated)])
        actual += 1
        if result.returncode == 0:
            failures.append(f"{case_id}:accepted")
    if actual != len(mutation_ids):
        failures.append(f"actual={actual} expected={len(mutation_ids)}")
    report("R3-02-reverse-artifact-closure", ", ".join(failures[:12]) if failures else None)
    if not failures:
        print(f"R3_EVIDENCE_MUTATIONS registered={len(mutation_ids)} actual={actual} missing=0")


def main() -> int:
    expected = load_json(EXPECTED_PATH)
    if len(expected.get("mutation_ids", [])) != 47 or len(set(expected["mutation_ids"])) != 47:
        print("R3_HARNESS_BROKEN mutation registry must contain 47 unique IDs")
        return 2
    with tempfile.TemporaryDirectory(prefix="jv-r3-copier-evidence.") as temp:
        temp_root = Path(temp)
        bundle = temp_root / "bundle"
        producer_failure = produce_bundle(bundle)
        if producer_failure:
            report("R3-01-durable-pre-remediation", producer_failure)
            report("R3-02-reverse-artifact-closure", "producer unavailable for mutation controls")
        else:
            test_durable_observations(bundle, expected)
            test_reverse_closure(bundle, expected, temp_root)
    print(f"R3_CORRECTION registered=2 actual={PASSES + len(FAILURES)} pass={PASSES} fail={len(FAILURES)}")
    if FAILURES:
        print("R3_FAILURE_IDENTITIES_BEGIN")
        for failure in FAILURES:
            print(failure)
        print("R3_FAILURE_IDENTITIES_END")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

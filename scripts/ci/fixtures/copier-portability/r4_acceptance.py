#!/usr/bin/env python3
"""R4 acceptance for independently authorized Copier evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = Path(__file__).resolve().parent
AUTHORITY = FIXTURE_ROOT / "evidence-r4-authority.json"
REGISTRY = FIXTURE_ROOT / "evidence-r4-mutations.json"
PRODUCER = ROOT / "scripts/ci/copier-real-update-receipt.py"
VALIDATOR = ROOT / "scripts/ci/validate-copier-evidence.py"
WORKFLOW = ROOT / ".github/workflows/ci.yml"
WRAPPER = FIXTURE_ROOT / "run-r4-gate.sh"
R4_GROUPS = {
    "R4-01-independent-fixture-authority",
    "R4-02-exact-remediation-result",
    "R4-03-full-entry-closure",
}
R4A_GROUP = "R4a-01-ci-reachability"
EXPECTED_GROUPS = R4_GROUPS | {R4A_GROUP}
EXPECTED_MUTATIONS = 29
EXPECTED_R4A_MUTATIONS = 6
FAILURES: list[str] = []
GROUP_FAILURES: dict[str, list[str]] = {group: [] for group in EXPECTED_GROUPS}
MUTATIONS_EXECUTED = 0
MUTATIONS_PASSED = 0
R4A_MUTATIONS_EXECUTED = 0
R4A_MUTATIONS_PASSED = 0


class HarnessError(RuntimeError):
    """The R4 assertion surface is malformed or could not execute."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HarnessError(f"object required: {path}")
    return value


def write_json_0444(path: Path, value: dict[str, Any]) -> None:
    if path.exists() and not path.is_symlink():
        path.chmod(0o644)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o444)


def run(command: list[str], *, timeout: int = 360) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def file_record(path: Path, relative: str) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": relative,
        "class": "regular",
        "mode": "0444",
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }


def refresh_manifest_record(bundle: Path, relative: str) -> None:
    manifest_path = bundle / "evidence-manifest.json"
    manifest = load_json(manifest_path)
    matches = [
        index
        for index, record in enumerate(manifest["files"])
        if record.get("path") == relative
    ]
    if len(matches) != 1:
        raise HarnessError(f"manifest path cardinality for {relative}: {len(matches)}")
    manifest["files"][matches[0]] = file_record(bundle / relative, relative)
    write_json_0444(manifest_path, manifest)


def edit_receipt(bundle: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    receipt_path = bundle / "copier-real-update-receipt.json"
    receipt = load_json(receipt_path)
    edit(receipt)
    write_json_0444(receipt_path, receipt)
    refresh_manifest_record(bundle, "copier-real-update-receipt.json")


def receipt_rows(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in receipt["rows"]}


def add_authority_hash_if_missing(bundle: Path) -> None:
    receipt = load_json(bundle / "copier-real-update-receipt.json")
    if "authority_sha256" not in receipt:
        edit_receipt(bundle, lambda value: value.__setitem__("authority_sha256", sha256(AUTHORITY)))


def replace_observation(bundle: Path, row_id: str, payload: bytes) -> None:
    receipt_path = bundle / "copier-real-update-receipt.json"
    receipt = load_json(receipt_path)
    row = receipt_rows(receipt)[row_id]
    observation = row["observation"]
    relative = observation["captured_path"]
    path = bundle / relative
    path.chmod(0o644)
    path.write_bytes(payload)
    path.chmod(0o444)
    digest = sha256_bytes(payload)
    observation["bytes"] = len(payload)
    observation["sha256"] = digest
    observation["source_to_captured"].update(
        {
            "source_bytes": len(payload),
            "source_sha256": digest,
            "captured_bytes": len(payload),
            "captured_sha256": digest,
        }
    )
    write_json_0444(receipt_path, receipt)
    refresh_manifest_record(bundle, relative)
    refresh_manifest_record(bundle, "copier-real-update-receipt.json")


def stable_wrong_hash(label: str) -> str:
    return sha256_bytes(f"R4 wrong value: {label}\n".encode())


def copy_bundle(source: Path, target: Path) -> None:
    shutil.copytree(source, target, symlinks=True)


def validate(bundle: Path, validator: Path = VALIDATOR) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(validator), "--bundle-root", str(bundle)])


def record_failure(group: str, identity: str, reason: str) -> None:
    value = f"{identity}:{reason}"
    FAILURES.append(value)
    GROUP_FAILURES[group].append(value)
    print(f"[R4-FAIL] {value}")


def record_pass(identity: str) -> None:
    print(f"[R4-PASS] {identity}")


def expect_rejection(
    group: str,
    identity: str,
    result: subprocess.CompletedProcess[str],
    diagnostic: str,
) -> None:
    global MUTATIONS_EXECUTED, MUTATIONS_PASSED
    MUTATIONS_EXECUTED += 1
    combined = output(result)
    if result.returncode == 0:
        record_failure(group, identity, "validator accepted mutation")
        return
    if re.search(diagnostic, combined, re.IGNORECASE) is None:
        tail = " ".join(combined.strip().splitlines()[-2:])[-500:]
        record_failure(group, identity, f"wrong diagnostic: {tail}")
        return
    MUTATIONS_PASSED += 1
    record_pass(identity)


def mutate_bundle(case_id: str, bundle: Path) -> None:
    if case_id.startswith("substitute-observation-"):
        suffix = case_id.removeprefix("substitute-observation-")
        row_id = {
            "clean": "real-clean-update",
            "inline": "real-inline-conflict",
            "reject": "real-reject-conflict",
        }[suffix]
        row = receipt_rows(load_json(bundle / "copier-real-update-receipt.json"))[row_id]
        path = bundle / row["observation"]["captured_path"]
        payload = path.read_bytes()
        if suffix == "clean":
            payload = (FIXTURE_ROOT / "v1/template/.claude/skills/copier-conflict-fixture/SKILL.md").read_bytes()
        else:
            needle = b"consumer local value"
            if needle not in payload:
                raise HarnessError(f"{case_id}: mutation anchor missing")
            payload = payload.replace(needle, needle + b"!", 1)
        replace_observation(bundle, row_id, payload)
        return
    if case_id == "substitute-fixture-manifest":
        edit_receipt(bundle, lambda receipt: receipt.__setitem__("fixture_manifest_sha256", "0" * 64))
        return
    if case_id in {"substitute-template-v1-tree", "substitute-template-v2-tree"}:
        key = "template_v1_tree" if "v1" in case_id else "template_v2_tree"
        edit_receipt(
            bundle,
            lambda receipt: [row.__setitem__(key, "0" * 40) for row in receipt["rows"]],
        )
        return
    if case_id == "substitute-authority-hash":
        edit_receipt(bundle, lambda receipt: receipt.__setitem__("authority_sha256", "0" * 64))
        return
    if case_id == "launder-authority-inside-bundle":
        fake = bundle / "authority.json"
        fake.write_text('{"attacker":"bundle-selected authority"}\n', encoding="utf-8")
        fake.chmod(0o444)
        edit_receipt(bundle, lambda receipt: receipt.__setitem__("authority_sha256", sha256(fake)))
        return
    if case_id == "substitute-consumer-before":
        edit_receipt(
            bundle,
            lambda receipt: [
                row.__setitem__("consumer_edit_before_sha256", stable_wrong_hash(case_id))
                for row in receipt["rows"]
            ],
        )
        return
    if case_id.startswith("substitute-consumer-after-"):
        suffix = case_id.removeprefix("substitute-consumer-after-")
        row_id = {
            "clean": "real-clean-update",
            "inline": "real-inline-conflict",
            "reject": "real-reject-conflict",
        }[suffix]
        edit_receipt(
            bundle,
            lambda receipt: receipt_rows(receipt)[row_id].__setitem__(
                "consumer_edit_after_sha256", stable_wrong_hash(case_id)
            ),
        )
        return
    if case_id.startswith("arbitrary-post-remediation-"):
        suffix = case_id.removeprefix("arbitrary-post-remediation-")
        row_id = {
            "clean": "real-clean-update",
            "inline": "real-inline-conflict",
            "reject": "real-reject-conflict",
        }[suffix]
        edit_receipt(
            bundle,
            lambda receipt: receipt_rows(receipt)[row_id].__setitem__(
                "post_remediation_sha256", stable_wrong_hash(case_id)
            ),
        )
        return
    if case_id == "extra-empty-directory":
        (bundle / "observations/unlisted-empty-artifact").mkdir()
        return
    if case_id == "extra-nonempty-directory":
        extra = bundle / "observations/unlisted-nonempty-artifact/payload.bin"
        extra.parent.mkdir()
        extra.write_bytes(b"unlisted\n")
        extra.chmod(0o444)
        return
    if case_id == "alternate-nesting-directory":
        (bundle / "observations/real-clean-update/alternate/nested").mkdir(parents=True)
        return
    if case_id == "symlinked-directory":
        backing = bundle.parent / f"{case_id}-backing"
        backing.mkdir()
        (bundle / "observations/symlinked-directory").symlink_to(backing, target_is_directory=True)
        return
    if case_id == "file-in-implied-parent":
        extra = bundle / "observations/unlisted-parent-file.txt"
        extra.write_text("unlisted\n", encoding="utf-8")
        extra.chmod(0o444)
        return
    if case_id == "hardlink-artifact":
        receipt = load_json(bundle / "copier-real-update-receipt.json")
        source = bundle / receipt_rows(receipt)["real-inline-conflict"]["observation"]["captured_path"]
        os.link(source, source.parent / "hardlink-alias")
        return
    raise HarnessError(f"unimplemented bundle mutation: {case_id}")


def prepare_validator_copy(
    temp_root: Path,
    case_id: str,
    edit: Callable[[dict[str, Any]], None] | None = None,
    *,
    include_authority: bool = True,
    malformed: bool = False,
) -> Path:
    script = temp_root / f"validator-{case_id}/scripts/ci/validate-copier-evidence.py"
    script.parent.mkdir(parents=True)
    shutil.copy2(VALIDATOR, script)
    copied_fixture_root = script.parent / "fixtures/copier-portability"
    copied_fixture_root.mkdir(parents=True)
    shutil.copy2(FIXTURE_ROOT / "manifest.json", copied_fixture_root / "manifest.json")
    canonical_relative = Path(
        "v2/template/.claude/skills/copier-conflict-fixture/SKILL.md"
    )
    copied_canonical = copied_fixture_root / canonical_relative
    copied_canonical.parent.mkdir(parents=True)
    shutil.copy2(FIXTURE_ROOT / canonical_relative, copied_canonical)
    if include_authority:
        copied = script.parent / "fixtures/copier-portability/evidence-r4-authority.json"
        if malformed:
            copied.write_text("{not-json\n", encoding="utf-8")
        else:
            authority = load_json(AUTHORITY)
            if edit is not None:
                edit(authority)
            copied.write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return script


def external_authority_validator(case_id: str, temp_root: Path) -> Path:
    if case_id == "missing-external-authority":
        return prepare_validator_copy(temp_root, case_id, include_authority=False)
    if case_id == "malformed-external-authority-json":
        return prepare_validator_copy(temp_root, case_id, malformed=True)
    if case_id == "tampered-external-authority":
        return prepare_validator_copy(
            temp_root,
            case_id,
            lambda authority: authority["fixture_manifest"].__setitem__("sha256", "0" * 64),
        )
    if case_id == "external-authority-extra-root-key":
        return prepare_validator_copy(
            temp_root,
            case_id,
            lambda authority: authority.__setitem__("bundle_selected", True),
        )
    if case_id == "external-authority-missing-row":
        return prepare_validator_copy(
            temp_root,
            case_id,
            lambda authority: authority["rows"].pop("real-reject-conflict"),
        )
    if case_id == "external-authority-extra-row":
        def extra_row(authority: dict[str, Any]) -> None:
            authority["rows"]["attacker-row"] = dict(authority["rows"]["real-clean-update"])
        return prepare_validator_copy(temp_root, case_id, extra_row)
    if case_id == "external-authority-missing-row-key":
        return prepare_validator_copy(
            temp_root,
            case_id,
            lambda authority: authority["rows"]["real-clean-update"].pop("post_remediation"),
        )
    if case_id == "external-authority-extra-row-key":
        return prepare_validator_copy(
            temp_root,
            case_id,
            lambda authority: authority["rows"]["real-clean-update"].__setitem__("bundle_override", {}),
        )
    raise HarnessError(f"unimplemented authority mutation: {case_id}")


def unquote_simple_yaml(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def portability_steps(workflow: str) -> list[dict[str, str]]:
    lines = workflow.splitlines()
    matches: list[dict[str, str]] = []
    index = 0
    while index < len(lines):
        named = re.match(r"^(?P<indent>\s*)-\s+name:\s*(?P<name>.*?)\s*$", lines[index])
        if named is None or unquote_simple_yaml(named.group("name")) != "Portable frontend-design acceptance":
            index += 1
            continue
        item_indent = len(named.group("indent"))
        end = index + 1
        while end < len(lines):
            next_item = re.match(r"^(?P<indent>\s*)-\s+", lines[end])
            if next_item is not None and len(next_item.group("indent")) <= item_indent:
                break
            end += 1
        fields = {"name": "Portable frontend-design acceptance"}
        cursor = index + 1
        while cursor < end:
            line = lines[cursor]
            if not line.strip() or line.lstrip().startswith("#"):
                cursor += 1
                continue
            field = re.match(r"^(?P<indent>\s+)(?P<key>[A-Za-z0-9_-]+):(?:\s*(?P<value>.*))?$", line)
            if field is None or len(field.group("indent")) <= item_indent:
                cursor += 1
                continue
            key = field.group("key")
            if key in fields:
                raise HarnessError(f"workflow portability step duplicates key: {key}")
            value = (field.group("value") or "").strip()
            if key == "run" and value in {"|", "|-", "|+", ">", ">-", ">+"}:
                block_indent = len(field.group("indent"))
                block: list[str] = []
                cursor += 1
                while cursor < end:
                    raw = lines[cursor]
                    if raw.strip() and len(raw) - len(raw.lstrip()) <= block_indent:
                        cursor -= 1
                        break
                    block.append(raw.strip())
                    cursor += 1
                value = (" " if value.startswith(">") else "\n").join(block).strip()
            fields[key] = unquote_simple_yaml(value)
            cursor += 1
        matches.append(fields)
        index = end
    return matches


def validate_workflow_text(workflow: str) -> str | None:
    steps = portability_steps(workflow)
    if len(steps) != 1:
        return f"exactly one executable portability step required, got {len(steps)}"
    step = steps[0]
    if set(step) != {"name", "run"}:
        return f"portability step must be unconditional and closed, got keys={sorted(step)}"
    expected = "bash scripts/ci/fixtures/copier-portability/run-r4-gate.sh"
    if step["run"] != expected:
        return f"executable portability command mismatch: {step['run']!r}"
    return None


def validate_wrapper_contract(wrapper: str) -> str | None:
    lines = [line.strip() for line in wrapper.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    retained_init = "retained_rc=0"
    r4_init = "r4_rc=0"
    retained_call = '"$ROOT/scripts/ci/test-skill-portability.sh" || retained_rc=$?'
    r4_call = 'python3 "$SCRIPT_DIR/r4_acceptance.py" || r4_rc=$?'
    failure_if = 'if [[ "$retained_rc" -ne 0 || "$r4_rc" -ne 0 ]]; then'
    required = (retained_init, r4_init, retained_call, r4_call, failure_if, "exit 1", "fi")
    missing = [line for line in required if lines.count(line) != 1]
    if missing:
        return f"wrapper exact status-preservation contract missing/duplicated: {missing}"
    if not lines.index(retained_init) < lines.index(retained_call) < lines.index(r4_call):
        return "wrapper must execute the retained gate before R4"
    if not lines.index(r4_init) < lines.index(r4_call):
        return "wrapper must initialize and preserve the R4 exit code"
    if not lines.index(failure_if) < lines.index("exit 1") < lines.index("fi"):
        return "wrapper must fail when either preserved exit code is nonzero"
    return None


def test_ci_reachability(case_ids: list[str]) -> None:
    global R4A_MUTATIONS_EXECUTED, R4A_MUTATIONS_PASSED
    actual_failures: list[str] = []
    if not WORKFLOW.is_file():
        actual_failures.append("workflow missing")
    else:
        workflow_failure = validate_workflow_text(WORKFLOW.read_text(encoding="utf-8"))
        if workflow_failure:
            actual_failures.append(workflow_failure)
    if not WRAPPER.is_file():
        actual_failures.append("R4 wrapper missing")
    else:
        wrapper_failure = validate_wrapper_contract(WRAPPER.read_text(encoding="utf-8"))
        if wrapper_failure:
            actual_failures.append(wrapper_failure)
    if actual_failures:
        record_failure(R4A_GROUP, "R4a-01-ci-reachability", ", ".join(actual_failures))
    else:
        record_pass("R4a-01-ci-reachability")

    valid = """jobs:
  generate-matrix-check:
    steps:
      - name: Portable frontend-design acceptance
        run: bash scripts/ci/fixtures/copier-portability/run-r4-gate.sh
"""
    mutations = {
        "ci-comment-only": """jobs:
  generate-matrix-check:
    steps:
      # - name: Portable frontend-design acceptance
      #   run: bash scripts/ci/fixtures/copier-portability/run-r4-gate.sh
""",
        "ci-disabled-step": valid.replace(
            "        run:",
            "        if: false\n        run:",
        ),
        "ci-wrong-wrapper-path": valid.replace("run-r4-gate.sh", "run-r4-gates.sh"),
        "ci-standalone-retained-gate": valid.replace(
            "bash scripts/ci/fixtures/copier-portability/run-r4-gate.sh",
            "bash scripts/ci/test-skill-portability.sh",
        ),
        "ci-shell-short-circuit": valid.replace(
            "bash scripts/ci/fixtures/copier-portability/run-r4-gate.sh",
            "bash scripts/ci/test-skill-portability.sh && python3 scripts/ci/fixtures/copier-portability/r4_acceptance.py",
        ),
        "ci-r4-only": valid.replace(
            "bash scripts/ci/fixtures/copier-portability/run-r4-gate.sh",
            "python3 scripts/ci/fixtures/copier-portability/r4_acceptance.py",
        ),
    }
    if set(mutations) != set(case_ids):
        raise HarnessError("R4a reachability mutations do not equal the closed registry")
    for case_id in case_ids:
        R4A_MUTATIONS_EXECUTED += 1
        reason = validate_workflow_text(mutations[case_id])
        if reason is None:
            record_failure(R4A_GROUP, case_id, "reachability mutation accepted")
        else:
            R4A_MUTATIONS_PASSED += 1
            record_pass(case_id)

    reachability_pass = 0 if GROUP_FAILURES[R4A_GROUP] else 1
    print(
        f"R4A_REACHABILITY_MUTATIONS registered={EXPECTED_R4A_MUTATIONS} "
        f"actual={R4A_MUTATIONS_EXECUTED} pass={R4A_MUTATIONS_PASSED} "
        f"fail={R4A_MUTATIONS_EXECUTED - R4A_MUTATIONS_PASSED}"
    )
    print(
        f"R4A_CORRECTION registered=1 actual=1 pass={reachability_pass} "
        f"fail={1 - reachability_pass}"
    )


def validate_registry() -> dict[str, list[str]]:
    value = load_json(REGISTRY)
    if set(value) != {"schema_version", "groups"} or value["schema_version"] != 1:
        raise HarnessError("mutation registry root must be schema-closed v1")
    groups = value["groups"]
    if not isinstance(groups, dict) or set(groups) != EXPECTED_GROUPS:
        raise HarnessError("mutation registry correction groups mismatch")
    identities: list[str] = []
    for group, cases in groups.items():
        if not isinstance(cases, list) or not cases or not all(isinstance(case, str) and case for case in cases):
            raise HarnessError(f"mutation registry malformed group: {group}")
        identities.extend(cases)
    expected_total = EXPECTED_MUTATIONS + EXPECTED_R4A_MUTATIONS
    if len(identities) != expected_total or len(set(identities)) != expected_total:
        raise HarnessError(
            f"mutation registry must contain {expected_total} unique identities, got {len(identities)}/{len(set(identities))}"
        )
    if sum(len(groups[group]) for group in R4_GROUPS) != EXPECTED_MUTATIONS:
        raise HarnessError("retained R4 mutation registry cardinality changed")
    if len(groups[R4A_GROUP]) != EXPECTED_R4A_MUTATIONS:
        raise HarnessError("R4a reachability mutation registry cardinality mismatch")
    return groups


def main() -> int:
    try:
        groups = validate_registry()
        if not AUTHORITY.is_file() or not PRODUCER.is_file() or not VALIDATOR.is_file():
            raise HarnessError("R4 authority or production subject missing")
        with tempfile.TemporaryDirectory(prefix="jv-r4-copier-evidence.") as temp:
            temp_root = Path(temp)
            produced = temp_root / "produced"
            producer = run(
                [
                    sys.executable,
                    str(PRODUCER),
                    "--project-root",
                    str(ROOT),
                    "--fixture-root",
                    str(FIXTURE_ROOT),
                    "--output-root",
                    str(produced),
                ]
            )
            if producer.returncode != 0:
                raise HarnessError(f"production producer failed: {output(producer)[-1800:]}")

            receipt = load_json(produced / "copier-real-update-receipt.json")
            authority_digest = sha256(AUTHORITY)
            positive_failures: list[str] = []
            if receipt.get("authority_sha256") != authority_digest:
                positive_failures.append("producer receipt missing exact independent authority hash")
            add_authority_hash_if_missing(produced)
            control = validate(produced)
            if control.returncode != 0:
                positive_failures.append(f"validator rejected authoritative control: {' '.join(output(control).strip().splitlines()[-2:])[-500:]}")
            if positive_failures:
                for reason in positive_failures:
                    record_failure("R4-01-independent-fixture-authority", "R4-01-authoritative-positive", reason)
            else:
                record_pass("R4-01-authoritative-positive")

            external_cases = {
                "missing-external-authority",
                "malformed-external-authority-json",
                "tampered-external-authority",
                "external-authority-extra-root-key",
                "external-authority-missing-row",
                "external-authority-extra-row",
                "external-authority-missing-row-key",
                "external-authority-extra-row-key",
            }
            for group in sorted(R4_GROUPS):
                case_ids = groups[group]
                expected_diagnostic = {
                    "R4-01-independent-fixture-authority": r"independent authority",
                    "R4-02-exact-remediation-result": r"post-remediation authority",
                    "R4-03-full-entry-closure": r"bundle (?:entry|reverse closure)|hardlink|unique regular",
                }[group]
                for case_id in case_ids:
                    mutated = temp_root / f"mutation-{case_id}"
                    copy_bundle(produced, mutated)
                    if case_id in external_cases:
                        validator = external_authority_validator(case_id, temp_root)
                    else:
                        mutate_bundle(case_id, mutated)
                        validator = VALIDATOR
                    expect_rejection(group, case_id, validate(mutated, validator), expected_diagnostic)

        correction_passes = 0
        for group in sorted(R4_GROUPS):
            if GROUP_FAILURES[group]:
                print(f"[R4-CORRECTION-FAIL] {group} failures={len(GROUP_FAILURES[group])}")
            else:
                correction_passes += 1
                print(f"[R4-CORRECTION-PASS] {group}")
        print(
            f"R4_MUTATIONS registered={EXPECTED_MUTATIONS} actual={MUTATIONS_EXECUTED} "
            f"pass={MUTATIONS_PASSED} fail={MUTATIONS_EXECUTED - MUTATIONS_PASSED}"
        )
        print(
            f"R4_CORRECTION registered=3 actual=3 pass={correction_passes} "
            f"fail={3 - correction_passes}"
        )
        test_ci_reachability(groups[R4A_GROUP])
        if FAILURES:
            print("R4_FAILURE_IDENTITIES_BEGIN")
            for failure in FAILURES:
                print(failure)
            print("R4_FAILURE_IDENTITIES_END")
            return 1
        return 0
    except (HarnessError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"R4_HARNESS_BROKEN:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

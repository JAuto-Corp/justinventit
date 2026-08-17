#!/usr/bin/env python3
"""R4 acceptance for independently authorized Copier evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable
from types import ModuleType


ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = Path(__file__).resolve().parent
AUTHORITY = FIXTURE_ROOT / "evidence-r4-authority.json"
HISTORY_AUTHORITY = FIXTURE_ROOT / "evidence-r5-history-authority.json"
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
R5_GROUP = "R5-01-fresh-checkout-determinism"
EXPECTED_GROUPS = R4_GROUPS | {R4A_GROUP, R5_GROUP}
EXPECTED_MUTATIONS = 29
EXPECTED_R4A_MUTATIONS = 6
EXPECTED_R5_MUTATIONS = 5
HISTORY_INVARIANT = "content-addressed fixture history invariant"
FAILURES: list[str] = []
GROUP_FAILURES: dict[str, list[str]] = {group: [] for group in EXPECTED_GROUPS}
MUTATIONS_EXECUTED = 0
MUTATIONS_PASSED = 0
R4A_MUTATIONS_EXECUTED = 0
R4A_MUTATIONS_PASSED = 0
R5_MUTATIONS_EXECUTED = 0
R5_MUTATIONS_PASSED = 0


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


def load_producer_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("copier_real_update_receipt_r5", PRODUCER)
    if spec is None or spec.loader is None:
        raise HarnessError("could not load production Copier history builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_at(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise HarnessError(
            f"history control git {' '.join(arguments)} exited {result.returncode}: "
            f"{(result.stdout + result.stderr)[-800:]}"
        )
    return result.stdout.strip()


def validate_history_authority() -> dict[str, Any]:
    authority = load_json(HISTORY_AUTHORITY)
    if set(authority) != {
        "schema_version",
        "authority_kind",
        "collision_mtime_ns",
        "paths",
        "template_trees",
    }:
        raise HarnessError("R5 history authority root is not closed")
    if authority["schema_version"] != 1 or authority["authority_kind"] != "copier-history-content-authority":
        raise HarnessError("R5 history authority identity mismatch")
    expected_paths = {
        "template/.agents/skills/copier-conflict-fixture/SKILL.md",
        "template/.claude/skills/copier-conflict-fixture/SKILL.md",
    }
    if set(authority["paths"]) != expected_paths:
        raise HarnessError("R5 history authority must close both conflict-fixture surfaces")
    for relative, versions in authority["paths"].items():
        if set(versions) != {"v1", "v2"}:
            raise HarnessError(f"R5 history authority versions mismatch: {relative}")
        for version, record in versions.items():
            if set(record) != {"bytes", "sha256", "git_blob"}:
                raise HarnessError(f"R5 history authority record is not closed: {version}/{relative}")
            fixture_path = FIXTURE_ROOT / version / relative
            payload = fixture_path.read_bytes()
            if len(payload) != record["bytes"] or sha256_bytes(payload) != record["sha256"]:
                raise HarnessError(f"R5 history authority payload mismatch: {version}/{relative}")
            blob = subprocess.run(
                ["git", "hash-object", "--stdin"],
                input=payload,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if blob.returncode != 0 or blob.stdout.decode().strip() != record["git_blob"]:
                raise HarnessError(f"R5 history authority blob mismatch: {version}/{relative}")
    trees = authority["template_trees"]
    if set(trees) != {"v1", "v2"} or trees["v1"] == trees["v2"]:
        raise HarnessError("R5 history authority tree identities are malformed")
    return authority


def prepare_history_fixture(target: Path, authority: dict[str, Any]) -> list[dict[str, Any]]:
    target.mkdir(parents=True)
    shutil.copy2(FIXTURE_ROOT / "copier.yml", target / "copier.yml")
    for directory in ("common", "v1", "v2"):
        shutil.copytree(FIXTURE_ROOT / directory, target / directory)
    collision_ns = authority["collision_mtime_ns"]
    receipts: list[dict[str, Any]] = []
    for version in ("v1", "v2"):
        for relative in sorted(authority["paths"]):
            path = target / version / relative
            os.utime(path, ns=(collision_ns, collision_ns))
            info = path.stat()
            receipts.append(
                {
                    "version": version,
                    "path": relative,
                    "bytes": info.st_size,
                    "mtime_ns": info.st_mtime_ns,
                    "sha256": sha256(path),
                }
            )
    if len({row["bytes"] for row in receipts}) != 1:
        raise HarnessError("R5 collision control requires equal-size v1/v2 payloads")
    if len({row["mtime_ns"] for row in receipts}) != 1:
        raise HarnessError("R5 collision control requires identical fixture mtimes")
    return receipts


def with_collision_git_config(action: Callable[[], Any]) -> Any:
    keys = (
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_CONFIG_KEY_1",
        "GIT_CONFIG_VALUE_1",
    )
    previous = {key: os.environ.get(key) for key in keys}
    os.environ.update(
        {
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "core.trustctime",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.checkStat",
            "GIT_CONFIG_VALUE_1": "minimal",
        }
    )
    try:
        return action()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def invoke_history_builder(module: ModuleType, fixture: Path, source: Path) -> tuple[str, str]:
    return with_collision_git_config(lambda: module.build_history(ROOT, fixture, source))


def mutate_history_fixture(case_id: str, fixture: Path, authority: dict[str, Any]) -> None:
    paths = sorted(authority["paths"])
    if case_id == "history-no-v2-byte-change":
        selected = paths
    elif case_id == "history-one-surface-changed":
        selected = [paths[0]]
    elif case_id in {
        "history-false-v2-success-retains-v1-tree",
        "history-metadata-only-staging",
    }:
        selected = []
    elif case_id == "history-expected-v2-blob-mismatch":
        selected = paths
        for relative in selected:
            path = fixture / "v2" / relative
            payload = path.read_bytes().replace(b"version two", b"version bad", 1)
            if len(payload) != authority["paths"][relative]["v2"]["bytes"]:
                raise HarnessError("R5 wrong-blob control changed payload size")
            path.write_bytes(payload)
    else:
        raise HarnessError(f"unimplemented R5 history mutation: {case_id}")
    if case_id != "history-expected-v2-blob-mismatch":
        for relative in selected:
            (fixture / "v2" / relative).write_bytes((fixture / "v1" / relative).read_bytes())
    collision_ns = authority["collision_mtime_ns"]
    for version in ("v1", "v2"):
        for relative in paths:
            os.utime(fixture / version / relative, ns=(collision_ns, collision_ns))


def install_history_git_control(module: ModuleType, case_id: str) -> Callable[[], None]:
    real_git = module.git
    if case_id == "history-metadata-only-staging":
        def metadata_only(repo: Path, *arguments: str) -> str:
            if arguments == ("add", "--renormalize", "."):
                return real_git(repo, "add", ".")
            return real_git(repo, *arguments)
        module.git = metadata_only
    elif case_id == "history-false-v2-success-retains-v1-tree":
        state: dict[str, str] = {}

        def false_success(repo: Path, *arguments: str) -> str:
            if arguments == ("rev-parse", "v1.0.0^{tree}"):
                state["v1_tree"] = real_git(repo, *arguments)
                return state["v1_tree"]
            if arguments == ("commit", "--quiet", "-m", "fixture v2"):
                return ""
            if arguments == ("tag", "v2.0.0"):
                return ""
            if arguments == ("rev-parse", "v2.0.0^{tree}"):
                return state["v1_tree"]
            return real_git(repo, *arguments)
        module.git = false_success

    def restore() -> None:
        module.git = real_git

    return restore


def test_history_determinism(case_ids: list[str], temp_root: Path) -> None:
    global R5_MUTATIONS_EXECUTED, R5_MUTATIONS_PASSED
    authority = validate_history_authority()
    module = load_producer_module()
    fixture = temp_root / "r5-positive-fixture"
    receipts = prepare_history_fixture(fixture, authority)
    print("R5_COLLISION_CONTROL " + json.dumps(receipts, sort_keys=True, separators=(",", ":")))
    source = temp_root / "r5-positive-source"
    positive_failures: list[str] = []
    try:
        v1_tree, v2_tree = invoke_history_builder(module, fixture, source)
    except Exception as exc:  # The production exception type is part of the RED observation.
        positive_failures.append(f"production builder rejected deterministic v2 content: {exc}")
    else:
        if v1_tree != authority["template_trees"]["v1"]:
            positive_failures.append(f"v1 tree mismatch: {v1_tree}")
        if v2_tree != authority["template_trees"]["v2"]:
            positive_failures.append(f"v2 tree mismatch: {v2_tree}")
        if v1_tree == v2_tree:
            positive_failures.append("v2 tree retained the v1 tree")
        v1_commit = git_at(source, "rev-parse", "v1.0.0^{commit}")
        v2_commit = git_at(source, "rev-parse", "v2.0.0^{commit}")
        if v1_commit == v2_commit:
            positive_failures.append("v2 tag retained the v1 commit")
        for relative, versions in sorted(authority["paths"].items()):
            for version in ("v1", "v2"):
                tag = f"{version}.0.0"
                blob = git_at(source, "rev-parse", f"{tag}:{relative}")
                payload = subprocess.run(
                    ["git", "show", f"{tag}:{relative}"],
                    cwd=source,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                if payload.returncode != 0:
                    positive_failures.append(f"missing {version} blob: {relative}")
                elif blob != versions[version]["git_blob"] or sha256_bytes(payload.stdout) != versions[version]["sha256"]:
                    positive_failures.append(f"wrong {version} blob: {relative}")
        print(
            "R5_HISTORY_IDENTITIES "
            f"v1_commit={v1_commit} v1_tree={v1_tree} "
            f"v2_commit={v2_commit} v2_tree={v2_tree}"
        )
    if positive_failures:
        for reason in positive_failures:
            record_failure(R5_GROUP, "R5-01-fresh-checkout-determinism", reason)
    else:
        record_pass("R5-01-fresh-checkout-determinism")

    if set(case_ids) != {
        "history-no-v2-byte-change",
        "history-one-surface-changed",
        "history-false-v2-success-retains-v1-tree",
        "history-expected-v2-blob-mismatch",
        "history-metadata-only-staging",
    }:
        raise HarnessError("R5 history mutations do not equal the closed registry")
    for case_id in case_ids:
        R5_MUTATIONS_EXECUTED += 1
        case_fixture = temp_root / f"r5-fixture-{case_id}"
        prepare_history_fixture(case_fixture, authority)
        mutate_history_fixture(case_id, case_fixture, authority)
        restore = install_history_git_control(module, case_id)
        try:
            try:
                invoke_history_builder(module, case_fixture, temp_root / f"r5-source-{case_id}")
            except Exception as exc:  # A named production invariant is the required outcome.
                if HISTORY_INVARIANT in str(exc):
                    R5_MUTATIONS_PASSED += 1
                    record_pass(case_id)
                else:
                    record_failure(R5_GROUP, case_id, f"wrong diagnostic: {exc}")
            else:
                record_failure(R5_GROUP, case_id, "production history builder accepted mutation")
        finally:
            restore()
    correction_pass = 0 if GROUP_FAILURES[R5_GROUP] else 1
    print(
        f"R5_HISTORY_MUTATIONS registered={EXPECTED_R5_MUTATIONS} "
        f"actual={R5_MUTATIONS_EXECUTED} pass={R5_MUTATIONS_PASSED} "
        f"fail={R5_MUTATIONS_EXECUTED - R5_MUTATIONS_PASSED}"
    )
    print(
        f"R5_CORRECTION registered=1 actual=1 pass={correction_pass} "
        f"fail={1 - correction_pass}"
    )


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
    expected_total = EXPECTED_MUTATIONS + EXPECTED_R4A_MUTATIONS + EXPECTED_R5_MUTATIONS
    if len(identities) != expected_total or len(set(identities)) != expected_total:
        raise HarnessError(
            f"mutation registry must contain {expected_total} unique identities, got {len(identities)}/{len(set(identities))}"
        )
    if sum(len(groups[group]) for group in R4_GROUPS) != EXPECTED_MUTATIONS:
        raise HarnessError("retained R4 mutation registry cardinality changed")
    if len(groups[R4A_GROUP]) != EXPECTED_R4A_MUTATIONS:
        raise HarnessError("R4a reachability mutation registry cardinality mismatch")
    if len(groups[R5_GROUP]) != EXPECTED_R5_MUTATIONS:
        raise HarnessError("R5 history mutation registry cardinality mismatch")
    return groups


def main() -> int:
    try:
        groups = validate_registry()
        if not all(path.is_file() for path in (AUTHORITY, HISTORY_AUTHORITY, PRODUCER, VALIDATOR)):
            raise HarnessError("R4/R5 authority or production subject missing")
        with tempfile.TemporaryDirectory(prefix="jv-r4-copier-evidence.") as temp:
            temp_root = Path(temp)
            test_history_determinism(groups[R5_GROUP], temp_root)
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

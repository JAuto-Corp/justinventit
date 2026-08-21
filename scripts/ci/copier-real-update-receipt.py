#!/usr/bin/env python3
"""Exercise three real Copier copy/update shapes and emit a machine receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


class CopierReceiptError(RuntimeError):
    """The real Copier integration did not satisfy its evidence contract."""


HISTORY_INVARIANT = "content-addressed fixture history invariant"
HISTORY_PATHS = {
    "template/.agents/skills/copier-conflict-fixture/SKILL.md",
    "template/.claude/skills/copier-conflict-fixture/SKILL.md",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        output = (result.stdout + result.stderr)[-2000:]
        raise CopierReceiptError(f"{label} exited {result.returncode}: {output}")


def git(repo: Path, *arguments: str) -> str:
    result = run(["git", *arguments], cwd=repo)
    require_success(result, f"git {' '.join(arguments)}")
    return result.stdout.strip()


def overlay(source: Path, target: Path) -> None:
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)


def history_error(reason: str) -> CopierReceiptError:
    return CopierReceiptError(f"{HISTORY_INVARIANT}: {reason}")


def load_history_authority(project_root: Path) -> dict[str, Any]:
    path = (
        project_root
        / "scripts/ci/fixtures/copier-portability/evidence-r5-history-authority.json"
    )
    if path.is_symlink() or not path.is_file():
        raise history_error("committed R5 authority is missing or not a regular file")
    if path.stat().st_nlink != 1:
        raise history_error("committed R5 authority must be a unique file")
    try:
        authority = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise history_error(f"committed R5 authority is unreadable: {exc}") from exc
    if not isinstance(authority, dict) or set(authority) != {
        "schema_version",
        "authority_kind",
        "collision_mtime_ns",
        "paths",
        "template_trees",
    }:
        raise history_error("committed R5 authority root is not closed")
    if authority["schema_version"] != 1 or authority["authority_kind"] != "copier-history-content-authority":
        raise history_error("committed R5 authority identity mismatch")
    paths = authority["paths"]
    if not isinstance(paths, dict) or set(paths) != HISTORY_PATHS:
        raise history_error("committed R5 authority does not close both fixture surfaces")
    for relative, versions in paths.items():
        if not isinstance(versions, dict) or set(versions) != {"v1", "v2"}:
            raise history_error(f"authority version closure mismatch: {relative}")
        for version, record in versions.items():
            if not isinstance(record, dict) or set(record) != {"bytes", "sha256", "git_blob"}:
                raise history_error(f"authority payload closure mismatch: {version}/{relative}")
            if (
                not isinstance(record["bytes"], int)
                or record["bytes"] < 0
                or not isinstance(record["sha256"], str)
                or len(record["sha256"]) != 64
                or not isinstance(record["git_blob"], str)
                or len(record["git_blob"]) != 40
            ):
                raise history_error(f"authority payload identity malformed: {version}/{relative}")
    trees = authority["template_trees"]
    if (
        not isinstance(trees, dict)
        or set(trees) != {"v1", "v2"}
        or not all(isinstance(value, str) and len(value) == 40 for value in trees.values())
        or trees["v1"] == trees["v2"]
    ):
        raise history_error("authority tree identities are malformed")
    return authority


def require_payload(payload: bytes, record: dict[str, Any], label: str) -> None:
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if len(payload) != record["bytes"] or actual_sha256 != record["sha256"]:
        raise history_error(
            f"{label} payload mismatch: bytes={len(payload)} sha256={actual_sha256}"
        )


def verify_worktree_history_payloads(
    source: Path,
    authority: dict[str, Any],
    version: str,
) -> None:
    for relative, versions in sorted(authority["paths"].items()):
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise history_error(f"{version} worktree path missing or non-regular: {relative}")
        require_payload(path.read_bytes(), versions[version], f"{version} worktree {relative}")


def staged_blob(source: Path, relative: str) -> tuple[str, bytes]:
    listing = git(source, "ls-files", "--stage", "--", relative).splitlines()
    if len(listing) != 1:
        raise history_error(f"staged path missing or ambiguous: {relative}")
    fields = listing[0].split(maxsplit=3)
    if len(fields) != 4 or fields[2] != "0" or fields[3] != relative:
        raise history_error(f"staged path entry malformed: {relative}")
    blob = fields[1]
    result = subprocess.run(
        ["git", "cat-file", "blob", blob],
        cwd=source,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise history_error(
            f"staged blob unreadable for {relative}: {result.stderr.decode(errors='replace')[-800:]}"
        )
    return blob, result.stdout


def verify_staged_v2(source: Path, authority: dict[str, Any], v1_tree: str) -> str:
    staged_tree = git(source, "write-tree")
    if staged_tree == v1_tree:
        raise history_error("v2 staged tree retained the v1 tree")
    if staged_tree != authority["template_trees"]["v2"]:
        raise history_error(f"unexpected v2 staged tree: {staged_tree}")
    for relative, versions in sorted(authority["paths"].items()):
        blob, payload = staged_blob(source, relative)
        record = versions["v2"]
        require_payload(payload, record, f"v2 staged {relative}")
        if blob != record["git_blob"]:
            raise history_error(f"v2 staged blob identity mismatch: {relative} blob={blob}")
    return staged_tree


def build_history(project_root: Path, fixture_root: Path, source: Path) -> tuple[str, str]:
    history_authority = load_history_authority(project_root)
    source.mkdir(parents=True)
    copier_config = (fixture_root / "copier.yml").read_text(encoding="utf-8")
    # Copier omits its answers file when a template has zero questions. This
    # evidence-only default makes copy persist the source/ref needed by a real
    # subsequent update; it does not alter either committed v1/v2 payload.
    copier_config += "\nfixture_channel:\n  type: str\n  default: portability-evidence\n"
    (source / "copier.yml").write_text(copier_config, encoding="utf-8")
    overlay(fixture_root / "common", source)
    (source / "template/.copier-answers.yml.jinja").write_text(
        "# Generated only for the real copy/update evidence lifecycle.\n"
        "{{ _copier_answers|to_nice_yaml -}}\n",
        encoding="utf-8",
    )
    for surface in (".agents", ".claude"):
        skill = project_root / "template" / surface / "skills/frontend-design"
        shutil.copytree(skill, source / "template" / surface / "skills/frontend-design")
    overlay(fixture_root / "v1", source)
    verify_worktree_history_payloads(source, history_authority, "v1")
    git(source, "init", "--quiet")
    git(source, "config", "user.name", "Portability Evidence")
    git(source, "config", "user.email", "portability-evidence@invalid.example")
    git(source, "add", ".")
    git(source, "commit", "--quiet", "-m", "fixture v1")
    git(source, "tag", "v1.0.0")
    v1_tree = git(source, "rev-parse", "v1.0.0^{tree}")
    if v1_tree != history_authority["template_trees"]["v1"]:
        raise history_error(f"unexpected v1 tree: {v1_tree}")
    overlay(fixture_root / "v2", source)
    verify_worktree_history_payloads(source, history_authority, "v2")
    git(source, "add", "--all")
    git(source, "add", "--renormalize", ".")
    staged_v2_tree = verify_staged_v2(source, history_authority, v1_tree)
    git(source, "commit", "--quiet", "-m", "fixture v2")
    git(source, "tag", "v2.0.0")
    v2_tree = git(source, "rev-parse", "v2.0.0^{tree}")
    if v2_tree != staged_v2_tree or v2_tree == v1_tree:
        raise history_error(
            f"committed v2 tree mismatch: v1={v1_tree} staged={staged_v2_tree} committed={v2_tree}"
        )
    return v1_tree, v2_tree


def command_record(command: list[str], result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": command,
        "status": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
    }


def bundle_file_record(bundle: Path, relative: str) -> dict[str, Any]:
    path = bundle / relative
    if path.is_symlink() or not path.is_file():
        raise CopierReceiptError(f"bundle artifact is not a regular file: {relative}")
    info = path.stat()
    if info.st_nlink != 1:
        raise CopierReceiptError(f"bundle artifact is hardlinked: {relative}")
    payload = path.read_bytes()
    return {
        "path": relative,
        "class": "regular",
        "mode": f"{info.st_mode & 0o7777:04o}",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def configure_consumer(target: Path, fixture_root: Path, edit: str) -> tuple[str, str]:
    generated = target / ".claude/skills/copier-conflict-fixture/SKILL.md"
    before = digest(generated)
    if edit == "preapply-v2":
        payload = (fixture_root / "v2/template/.claude/skills/copier-conflict-fixture/SKILL.md").read_bytes()
    elif edit == "conflicting-local":
        payload = (
            b"---\nname: copier-conflict-fixture\n"
            b"description: consumer-owned conflicting edit\n---\nconsumer local value\n"
        )
    else:
        raise CopierReceiptError(f"unknown consumer edit: {edit}")
    generated.write_bytes(payload)
    after = digest(generated)
    if before == after:
        raise CopierReceiptError(f"consumer edit did not change bytes: {edit}")
    return before, after


def initialize_consumer_history(target: Path) -> None:
    git(target, "init", "--quiet")
    git(target, "config", "user.name", "Portability Consumer")
    git(target, "config", "user.email", "portability-consumer@invalid.example")
    git(target, "add", ".")
    git(target, "commit", "--quiet", "-m", "consumer state before update")


def rollback(target: Path) -> dict[str, Any]:
    changed = [line for line in git(target, "status", "--porcelain=v1").splitlines() if line]
    if not changed:
        raise CopierReceiptError("real Copier update produced no rollback unit")
    git(target, "restore", "--source=HEAD", "--staged", "--worktree", ".")
    residual = git(target, "status", "--porcelain=v1")
    if residual:
        raise CopierReceiptError(f"rollback left residual changes: {residual}")
    return {"status": "pass", "changed_path_count": len(changed)}


def exercise(
    project_root: Path,
    fixture_root: Path,
    source: Path,
    work: Path,
    scenario: dict[str, str],
    copier: str,
    copier_version: str,
    v1_tree: str,
    v2_tree: str,
    evidence_root: Path,
) -> dict[str, Any]:
    target = work / scenario["id"]
    copy_command = [copier, "copy", "--defaults", "--trust", "--vcs-ref", "v1.0.0", str(source), str(target)]
    copied = run(copy_command, cwd=project_root)
    require_success(copied, f"{scenario['id']} Copier copy")
    before, after = configure_consumer(target, fixture_root, scenario["consumer_edit"])
    initialize_consumer_history(target)

    actor_receipt = work / f"{scenario['id']}-actor.json"
    actor_command = [
        str(project_root / "scripts/ci/copier-update-check.sh"),
        "--target", str(target),
        "--conflict", scenario["conflict_mode"],
        "--vcs-ref", "v2.0.0",
        "--receipt-out", str(actor_receipt),
        "--evidence-root", str(evidence_root),
        "--row-id", scenario["id"],
    ]
    actor_env = os.environ.copy()
    actor_env["PATH"] = f"{Path(copier).parent}:{actor_env.get('PATH', '')}"
    acted = run(actor_command, cwd=project_root, env=actor_env)
    require_success(acted, f"{scenario['id']} production update actor")
    actor = json.loads(actor_receipt.read_text(encoding="utf-8"))
    if actor.get("classification") != scenario["expected_classification"]:
        raise CopierReceiptError(
            f"{scenario['id']} expected {scenario['expected_classification']}, got {actor.get('classification')}"
        )
    canonical = target / ".agents/skills/copier-conflict-fixture/SKILL.md"
    generated = target / ".claude/skills/copier-conflict-fixture/SKILL.md"
    if canonical.read_bytes() != generated.read_bytes():
        raise CopierReceiptError(f"{scenario['id']} framework-wins remediation did not converge")
    observation = actor.get("observation")
    if not isinstance(observation, dict):
        raise CopierReceiptError(f"{scenario['id']} actor omitted pre-remediation observation")
    rollback_record = rollback(target)
    return {
        "id": scenario["id"],
        "evidence_kind": "real-copier-update",
        "copier_path": str(Path(copier).resolve()),
        "copier_version": copier_version,
        "copy": command_record(copy_command, copied),
        "update": actor["update"],
        "consumer_edit_before_sha256": before,
        "consumer_edit_after_sha256": after,
        "classification": actor["classification"],
        "remediation": actor["remediation"],
        "post_remediation_sha256": actor["post_remediation_sha256"],
        "rollback": rollback_record,
        "observation": observation,
        "template_v1_tree": v1_tree,
        "template_v2_tree": v2_tree,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    fixture_root = args.fixture_root.resolve()
    output_root = args.output_root.resolve()
    try:
        if output_root.is_symlink() or (output_root.exists() and not output_root.is_dir()):
            raise CopierReceiptError("output root must be a real directory")
        if output_root.exists() and any(output_root.iterdir()):
            raise CopierReceiptError("output root must be empty")
        output_root.mkdir(parents=True, exist_ok=True)
        copier = shutil.which("copier")
        if copier is None:
            raise CopierReceiptError("copier not found")
        version = run([copier, "--version"], cwd=project_root)
        require_success(version, "Copier version")
        copier_version = version.stdout.strip() or version.stderr.strip()
        if copier_version != "copier 9.17.1":
            raise CopierReceiptError(f"expected copier 9.17.1, got {copier_version!r}")
        manifest_path = fixture_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("copier_version") != copier_version or len(manifest.get("scenarios", [])) != 3:
            raise CopierReceiptError("committed Copier manifest is invalid")
        authority_path = (
            project_root
            / "scripts/ci/fixtures/copier-portability/evidence-r4-authority.json"
        )
        if authority_path.is_symlink() or not authority_path.is_file():
            raise CopierReceiptError("committed independent evidence authority is missing")
        authority_info = authority_path.stat()
        if authority_info.st_nlink != 1:
            raise CopierReceiptError("committed independent evidence authority must be a unique file")
        with tempfile.TemporaryDirectory(prefix="jv-real-copier.") as temp:
            work = Path(temp)
            source = work / "template-source"
            v1_tree, v2_tree = build_history(project_root, fixture_root, source)
            rows = [
                exercise(
                    project_root, fixture_root, source, work, scenario, copier,
                    copier_version, v1_tree, v2_tree, output_root,
                )
                for scenario in manifest["scenarios"]
            ]
        receipt = {
            "schema_version": 1,
            "copier_version": copier_version,
            "fixture_manifest_sha256": digest(manifest_path),
            "authority_sha256": digest(authority_path),
            "provenance_question": "fixture_channel=portability-evidence",
            "manifest_path": "evidence-manifest.json",
            "rows": rows,
        }
        receipt_path = output_root / "copier-real-update-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt_path.chmod(0o444)
        authorized_paths = [
            "copier-real-update-receipt.json",
            *(row["observation"]["captured_path"] for row in rows),
        ]
        evidence_manifest = {
            "schema_version": 1,
            "bundle_kind": "real-copier-pre-remediation-evidence",
            "receipt_path": "copier-real-update-receipt.json",
            "files": [bundle_file_record(output_root, relative) for relative in authorized_paths],
        }
        evidence_manifest_path = output_root / "evidence-manifest.json"
        evidence_manifest_path.write_text(
            json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        evidence_manifest_path.chmod(0o444)
        validated = run(
            [
                sys.executable,
                str(project_root / "scripts/ci/validate-copier-evidence.py"),
                "--bundle-root", str(output_root),
            ],
            cwd=project_root,
        )
        require_success(validated, "durable Copier evidence validation")
        print(f"real Copier update receipt: PASS {receipt_path}")
        return 0
    except (OSError, json.JSONDecodeError, CopierReceiptError) as exc:
        print(f"real Copier update receipt error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

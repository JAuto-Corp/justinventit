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
import tempfile
from typing import Any


class CopierReceiptError(RuntimeError):
    """The real Copier integration did not satisfy its evidence contract."""


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


def build_history(project_root: Path, fixture_root: Path, source: Path) -> tuple[str, str]:
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
    git(source, "init", "--quiet")
    git(source, "config", "user.name", "Portability Evidence")
    git(source, "config", "user.email", "portability-evidence@invalid.example")
    git(source, "add", ".")
    git(source, "commit", "--quiet", "-m", "fixture v1")
    git(source, "tag", "v1.0.0")
    v1_tree = git(source, "rev-parse", "v1.0.0^{tree}")
    overlay(fixture_root / "v2", source)
    git(source, "add", ".")
    git(source, "commit", "--quiet", "-m", "fixture v2")
    git(source, "tag", "v2.0.0")
    v2_tree = git(source, "rev-parse", "v2.0.0^{tree}")
    return v1_tree, v2_tree


def command_record(command: list[str], result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": command,
        "status": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
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
        "rollback": rollback_record,
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
        with tempfile.TemporaryDirectory(prefix="jv-real-copier.") as temp:
            work = Path(temp)
            source = work / "template-source"
            v1_tree, v2_tree = build_history(project_root, fixture_root, source)
            rows = [
                exercise(
                    project_root, fixture_root, source, work, scenario, copier,
                    copier_version, v1_tree, v2_tree,
                )
                for scenario in manifest["scenarios"]
            ]
        output_root.mkdir(parents=True, exist_ok=True)
        receipt = {
            "schema_version": 1,
            "copier_version": copier_version,
            "fixture_manifest_sha256": digest(manifest_path),
            "provenance_question": "fixture_channel=portability-evidence",
            "rows": rows,
        }
        receipt_path = output_root / "copier-real-update-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"real Copier update receipt: PASS {receipt_path}")
        return 0
    except (OSError, json.JSONDecodeError, CopierReceiptError) as exc:
        print(f"real Copier update receipt error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
schema_path="$source_root/scripts/ci/fixtures/runtime-skill-receipt.schema.json"

die() {
  printf 'runtime receipt error: %s\n' "$*" >&2
  exit 1
}

validate_fixture() {
  local fixture_dir="$1"
  python3 - "$fixture_dir" "$schema_path" <<'PY'
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import sys


class ValidationError(RuntimeError):
    pass


fixture = Path(sys.argv[1]).resolve()
schema_path = Path(sys.argv[2]).resolve()


def load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"{label} missing") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{label} schema invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{label} schema invalid: object required")
    return value


def artifact(path: Path, label: str, nonempty: bool) -> tuple[int, str]:
    if not path.exists():
        raise ValidationError(f"claude artifact missing: {label}")
    if path.is_symlink():
        raise ValidationError(f"claude artifact unreadable/unhashable class: {label}")
    try:
        info = path.stat()
    except OSError as exc:
        raise ValidationError(f"claude artifact unreadable/unhashable: {label}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or not path.is_file():
        raise ValidationError(f"claude artifact unreadable/unhashable class: {label}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"claude artifact unreadable/unhashable: {label}: {exc}") from exc
    if nonempty and not data:
        raise ValidationError(f"claude artifact empty: {label}")
    return len(data), hashlib.sha256(data).hexdigest()


try:
    schema = load_json(schema_path, "receipt schema")
    schema_required = schema.get("required")
    if schema.get("$id") != "https://justinventit.dev/schemas/runtime-skill-receipt-v1.json" or not isinstance(schema_required, list):
        raise ValidationError("receipt schema invalid or unsupported")

    debug_path = fixture / "claude-debug.log"
    stdout_path = fixture / "claude-stdout.txt"
    stderr_path = fixture / "claude-stderr.txt"
    receipt_path = fixture / "claude-receipt.json"
    transcript_paths = sorted((fixture / "projects").glob("*/*.jsonl"))
    if len(transcript_paths) != 1:
        raise ValidationError(f"claude transcript cardinality: expected 1, got {len(transcript_paths)}")
    transcript_path = transcript_paths[0]

    observed: dict[str, tuple[int, str]] = {}
    observed["debug"] = artifact(debug_path, "debug", True)
    observed["transcript"] = artifact(transcript_path, "transcript", True)
    observed["stdout"] = artifact(stdout_path, "stdout", True)
    observed["stderr"] = artifact(stderr_path, "stderr", False)
    observed["receipt"] = artifact(receipt_path, "receipt", True)
    if observed["stderr"][0] != 0:
        raise ValidationError(f"claude stderr nonempty: {observed['stderr'][0]}")

    receipt = load_json(receipt_path, "claude receipt")
    missing = [key for key in schema_required if key not in receipt]
    if missing:
        if "codex_version" in missing:
            raise ValidationError("codex native receipt CLI version missing")
        if "claude_version" in missing:
            raise ValidationError("claude invocation receipt CLI version missing")
        if "node_version" in missing:
            raise ValidationError("runtime node version missing")
        raise ValidationError(f"claude receipt schema missing required fields: {', '.join(missing)}")
    if receipt.get("schema_version") != 1:
        raise ValidationError("claude receipt schema_version invalid")

    exact_versions = {
        "node_version": "v22.23.2",
        "codex_version": "codex-cli 0.145.0",
        "claude_version": "2.1.232 (Claude Code)",
    }
    for key, expected in exact_versions.items():
        if receipt.get(key) != expected:
            raise ValidationError(f"runtime CLI version mismatch or missing: {key} expected {expected!r}")
    if receipt.get("timeout_seconds") != 30 or receipt.get("kill_after_seconds") != 5:
        raise ValidationError("claude timeout/signal contract mismatch")

    for name in ("debug", "transcript", "stdout", "stderr"):
        byte_count, digest = observed[name]
        if receipt.get(f"{name}_bytes") != byte_count or receipt.get(f"{name}_sha256") != digest:
            raise ValidationError(f"claude native receipt artifact hash/byte evidence tuple mismatch: {name}")

    for runtime in ("codex", "claude"):
        control = receipt.get(f"{runtime}_no_project")
        if not isinstance(control, dict) or control.get("target_count") != 0:
            raise ValidationError(f"{runtime} no-project target count must be zero")

    debug = debug_path.read_text(encoding="utf-8")
    debug_markers = (
        "Remote settings: Fetch failed (http_401) and no cached settings",
        "Loading skills from:",
        "Total plugin skills loaded: 0 (0 duplicate/user-owned entries skipped)",
        "Loaded 1 unique skills (1 unconditional, 0 conditional, managed: 0, user: 0, project: 1, additional: 0, legacy commands: 0)",
    )
    for marker in debug_markers:
        count = debug.count(marker)
        if count != 1:
            raise ValidationError(f"claude debug marker drift/cardinality: {marker!r} count={count}")
    attachment_lines = [
        line for line in debug.splitlines()
        if line.startswith("Sending ") and line.endswith(" skills via attachment (initial)")
    ]
    if len(attachment_lines) != 1:
        raise ValidationError("claude debug marker drift: skill attachment marker")
    middle = attachment_lines[0][len("Sending "):-len(" skills via attachment (initial)")]
    if not middle.isdigit():
        raise ValidationError("claude debug marker drift: attachment count is not an integer")

    try:
        transcript_rows = [
            json.loads(line)
            for line in transcript_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except json.JSONDecodeError as exc:
        raise ValidationError(f"claude transcript schema invalid: {exc}") from exc
    listings = [
        (index, row) for index, row in enumerate(transcript_rows)
        if row.get("type") == "attachment"
        and isinstance(row.get("attachment"), dict)
        and row["attachment"].get("type") == "skill_listing"
    ]
    terminals = [
        (index, row) for index, row in enumerate(transcript_rows)
        if row.get("type") == "assistant"
        and row.get("error") == "authentication_failed"
        and row.get("isApiErrorMessage") is True
        and row.get("apiErrorStatus") == 401
    ]
    if len(listings) != 1 or len(terminals) != 1:
        raise ValidationError("claude transcript skill-listing/auth schema cardinality mismatch")
    listing_index, listing = listings[0]
    terminal_index, terminal = terminals[0]
    names = listing["attachment"].get("names")
    if not isinstance(names, list) or names.count("frontend-design") != 1 or any(
        isinstance(name, str) and name.endswith(":frontend-design") for name in names
    ):
        raise ValidationError("claude transcript marker skill_listing frontend-design cardinality mismatch")
    session_id = receipt.get("session_id")
    if (
        listing_index >= terminal_index
        or listing.get("sessionId") != session_id
        or terminal.get("sessionId") != session_id
    ):
        raise ValidationError("claude transcript session/order mismatch")

    invocation = receipt.get("claude_invocation")
    if not isinstance(invocation, dict):
        raise ValidationError("claude invocation receipt missing")
    if invocation.get("marker") != "Base directory for this skill:":
        raise ValidationError("claude invocation marker drift")
    if invocation.get("loaded_body") != invocation.get("source_body"):
        raise ValidationError("claude invocation body mismatch; exact full body required")

    native = receipt.get("codex_native")
    if not isinstance(native, dict):
        raise ValidationError("codex native receipt missing")
    if native.get("raw_prompt") != "$frontend-design invoke exactly":
        raise ValidationError("codex native raw prompt contains a path or differs from exact prompt")
    records = native.get("skill_records")
    if not isinstance(records, list) or len(records) != 1:
        raise ValidationError(f"codex native skill record cardinality mismatch: {len(records) if isinstance(records, list) else 'invalid'}")
    record = records[0]
    if (
        not isinstance(record, dict)
        or record.get("source") != "runtime"
        or record.get("name") != "frontend-design"
        or record.get("path") != "/project/.agents/skills/frontend-design/SKILL.md"
    ):
        raise ValidationError("codex native runtime record/path/client provenance mismatch")
    if record.get("body") != native.get("source_body"):
        raise ValidationError("codex native injected body is not an exact full-body match")
    if native.get("fallback_used") is True and native.get("fallback_reruled") is not True:
        raise ValidationError("codex fallback used without explicit reruling")

    stdout = stdout_path.read_bytes()
    expected_stdout = "Invalid API key · Fix external API key\n".encode("utf-8")
    status = receipt.get("status")
    if status == 124 or status in (137, 143):
        raise ValidationError(f"claude timeout or signal status: {status}")
    if status == 0:
        raise ValidationError("claude unexpected authenticated success status 0")
    if status != 1:
        raise ValidationError(f"claude unexpected exit status: {status}")
    if stdout != expected_stdout:
        raise ValidationError("claude expected auth terminal missing or corrupt stdout")
    expected_stdout_sha = "d50145fd739977392cf3b0bbf1b73f863d2fcdf831ffe5605f3981f879f57c27"
    if len(stdout) != 40 or hashlib.sha256(stdout).hexdigest() != expected_stdout_sha:
        raise ValidationError("claude expected auth terminal hash/byte mismatch")

    print("runtime skill receipt fixture validation: PASS")
except ValidationError as exc:
    print(f"runtime receipt validation error: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
}

validate_availability_fixture() {
  local fixture_dir="$1" receipt_path
  [[ -d "$fixture_dir" ]] || die "availability fixture directory missing: $fixture_dir"
  if [[ -f "$fixture_dir/receipt.json" ]]; then
    receipt_path="$fixture_dir/receipt.json"
  elif [[ -f "$fixture_dir/claude-receipt.json" ]]; then
    receipt_path="$fixture_dir/claude-receipt.json"
  else
    die "availability fixture receipt missing: $fixture_dir"
  fi
  python3 "$source_root/scripts/ci/validate-runtime-receipt.py" \
    --schema "$schema_path" \
    --receipt "$receipt_path" \
    --artifact-root "$fixture_dir"
}

acquire_ci_receipt() {
  command -v node >/dev/null 2>&1 || die "node CLI missing"
  command -v codex >/dev/null 2>&1 || die "codex CLI missing"
  command -v claude >/dev/null 2>&1 || die "claude CLI missing"
  [[ "$(node --version)" == "v22.23.2" ]] || die "node version mismatch"
  [[ "$(codex --version)" == "codex-cli 0.145.0" ]] || die "codex CLI version mismatch"
  [[ "$(claude --version)" == "2.1.232 (Claude Code)" ]] || die "claude CLI version mismatch"
  [[ ! -e /etc/codex/skills ]] || die "managed Codex skill root unexpectedly present"
  [[ ! -e /etc/claude-code/.claude/skills ]] || die "managed Claude skill root unexpectedly present"
  [[ ! -e /etc/claude-code/managed-settings.json ]] || die "managed Claude settings unexpectedly present"

  local receipt_parent receipt_scratch receipt_raw project control
  receipt_parent="${RUNNER_TEMP:-/tmp}"
  receipt_scratch="$(mktemp -d "$receipt_parent/jv-runtime-skill-receipt.XXXXXX")"
  receipt_raw="$receipt_scratch/raw"
  project="$receipt_scratch/project"
  control="$receipt_scratch/no-project-control"
  mkdir -p "$receipt_raw" "$project/.agents/skills" "$project/.claude/skills" "$control" "$receipt_scratch/home" "$receipt_scratch/codex-home" "$receipt_scratch/control-home" "$receipt_scratch/control-codex-home" "$receipt_scratch/claude-config" "$receipt_scratch/control-claude-config"
  cp -R "$source_root/template/.agents/skills/frontend-design" "$project/.agents/skills/"
  cp -R "$source_root/template/.claude/skills/frontend-design" "$project/.claude/skills/"
  python3 "$source_root/scripts/generate-skill-surfaces.py" --project-root "$project" --check
  python3 "$source_root/scripts/ci/check-skill-routes.py" --project-root "$project"

  local codex_status codex_control_status claude_status claude_control_status
  set +e
  (
    cd "$project"
    env -u OPENAI_API_KEY -u CODEX_API_KEY HOME="$receipt_scratch/home" CODEX_HOME="$receipt_scratch/codex-home" codex debug prompt-input '$frontend-design availability probe only'
  ) >"$receipt_raw/codex-project.json" 2>"$receipt_raw/codex-project.stderr"
  codex_status=$?
  (
    cd "$control"
    env -u OPENAI_API_KEY -u CODEX_API_KEY HOME="$receipt_scratch/control-home" CODEX_HOME="$receipt_scratch/control-codex-home" codex debug prompt-input 'availability probe only'
  ) >"$receipt_raw/codex-control.json" 2>"$receipt_raw/codex-control.stderr"
  codex_control_status=$?

  (
    cd "$project"
    env -u ANTHROPIC_AUTH_TOKEN -u CLAUDE_CODE_OAUTH_TOKEN HOME="$receipt_scratch/home" CLAUDE_CONFIG_DIR="$receipt_scratch/claude-config" ANTHROPIC_API_KEY="invalid-availability-receipt-key" timeout --signal=TERM --kill-after=5s 30s claude --debug --debug-file "$receipt_raw/claude-debug.log" --setting-sources project -p "availability probe only"
  ) >"$receipt_raw/claude-stdout.txt" 2>"$receipt_raw/claude-stderr.txt"
  claude_status=$?
  (
    cd "$control"
    env -u ANTHROPIC_AUTH_TOKEN -u CLAUDE_CODE_OAUTH_TOKEN HOME="$receipt_scratch/control-home" CLAUDE_CONFIG_DIR="$receipt_scratch/control-claude-config" ANTHROPIC_API_KEY="invalid-availability-receipt-key" timeout --signal=TERM --kill-after=5s 30s claude --debug --debug-file "$receipt_raw/claude-control-debug.log" --setting-sources project -p "availability probe only"
  ) >"$receipt_raw/claude-control-stdout.txt" 2>"$receipt_raw/claude-control-stderr.txt"
  claude_control_status=$?
  set -e

  local -a project_transcripts control_transcripts
  mapfile -t project_transcripts < <(find "$receipt_scratch/claude-config/projects" -mindepth 2 -maxdepth 2 -type f -name '*.jsonl' -print | LC_ALL=C sort)
  mapfile -t control_transcripts < <(find "$receipt_scratch/control-claude-config/projects" -mindepth 2 -maxdepth 2 -type f -name '*.jsonl' -print | LC_ALL=C sort)
  [[ "${#project_transcripts[@]}" -eq 1 ]] || die "Claude project transcript cardinality: expected 1, got ${#project_transcripts[@]}"
  [[ "${#control_transcripts[@]}" -eq 1 ]] || die "Claude control transcript cardinality: expected 1, got ${#control_transcripts[@]}"
  cp -- "${project_transcripts[0]}" "$receipt_raw/claude-transcript.jsonl"
  cp -- "${control_transcripts[0]}" "$receipt_raw/claude-control-transcript.jsonl"
  cmp -s -- "${project_transcripts[0]}" "$receipt_raw/claude-transcript.jsonl" || die "Claude project transcript archive mismatch"
  cmp -s -- "${control_transcripts[0]}" "$receipt_raw/claude-control-transcript.jsonl" || die "Claude control transcript archive mismatch"

  python3 - "$source_root" "$receipt_scratch" "$codex_status" "$codex_control_status" "$claude_status" "$claude_control_status" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys


class ReceiptError(RuntimeError):
    pass


source_root = Path(sys.argv[1]).resolve()
scratch = Path(sys.argv[2]).resolve()
raw = scratch / "raw"
project = scratch / "project"
statuses = {
    "codex": int(sys.argv[3]),
    "codex_control": int(sys.argv[4]),
    "claude": int(sys.argv[5]),
    "claude_control": int(sys.argv[6]),
}


def file_record(path: Path, label: str, allow_empty: bool = False) -> dict:
    if not path.exists():
        raise ReceiptError(f"artifact missing: {label}")
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ReceiptError(f"artifact wrong class: {label}")
    data = path.read_bytes()
    if not allow_empty and not data:
        raise ReceiptError(f"artifact empty: {label}")
    try:
        relative = path.resolve().relative_to(raw.resolve()).as_posix()
    except ValueError as exc:
        raise ReceiptError(f"artifact outside uploaded closure: {label}") from exc
    return {
        "path": relative,
        "class": "regular",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def only_transcript(config: Path, label: str) -> Path:
    matches = sorted((config / "projects").glob("*/*.jsonl"))
    if len(matches) != 1:
        raise ReceiptError(f"{label} transcript cardinality: expected 1, got {len(matches)}")
    return matches[0]


def transcript_rows(path: Path) -> list[dict]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError as exc:
        raise ReceiptError(f"transcript JSON schema changed: {exc}") from exc


def generated_tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for base_name in (".agents", ".claude"):
        base = root / base_name
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix().encode()
            payload = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
    return digest.hexdigest()


def validate_claude(prefix: str, config_name: str, expected_project: Path, target_expected: bool) -> dict:
    debug_path = raw / f"claude-{prefix}debug.log"
    stdout_path = raw / f"claude-{prefix}stdout.txt"
    stderr_path = raw / f"claude-{prefix}stderr.txt"
    config = scratch / config_name
    source_transcript = only_transcript(config, f"claude {prefix}control")
    transcript = raw / f"claude-{prefix}transcript.jsonl"
    if source_transcript.read_bytes() != transcript.read_bytes():
        raise ReceiptError(f"claude {prefix}archived transcript differs from runtime source")
    artifacts = {
        "debug": file_record(debug_path, f"claude {prefix}debug"),
        "transcript": file_record(transcript, f"claude {prefix}transcript"),
        "stdout": file_record(stdout_path, f"claude {prefix}stdout"),
        "stderr": file_record(stderr_path, f"claude {prefix}stderr", allow_empty=True),
    }
    if artifacts["stderr"]["bytes"] != 0:
        raise ReceiptError(f"claude {prefix}stderr nonempty")
    debug = debug_path.read_text(encoding="utf-8")
    common_markers = (
        "Remote settings: Fetch failed (http_401) and no cached settings",
        "Loading skills from:",
        "Total plugin skills loaded: 0 (0 duplicate/user-owned entries skipped)",
    )
    for marker in common_markers:
        if debug.count(marker) != 1:
            raise ReceiptError(f"claude {prefix}debug marker changed: {marker}")
    loaded_pattern = (
        r"Loaded 1 unique skills \(1 unconditional, 0 conditional, managed: 0, user: 0, "
        r"project: 1, additional: 0, legacy commands: 0\)"
        if target_expected
        else r"Loaded 0 unique skills \(0 unconditional, 0 conditional, managed: 0, user: 0, "
        r"project: 0, additional: 0, legacy commands: 0\)"
    )
    if len(re.findall(loaded_pattern, debug)) != 1:
        raise ReceiptError(f"claude {prefix}loaded-skill marker changed")
    attachment_markers = re.findall(r"Sending ([0-9]+) skills via attachment \(initial\)", debug)
    if len(attachment_markers) != 1:
        raise ReceiptError(f"claude {prefix}attachment marker changed")

    rows = transcript_rows(transcript)
    listings = [
        (index, row) for index, row in enumerate(rows)
        if row.get("type") == "attachment"
        and isinstance(row.get("attachment"), dict)
        and row["attachment"].get("type") == "skill_listing"
    ]
    errors = [
        (index, row) for index, row in enumerate(rows)
        if row.get("type") == "assistant"
        and row.get("error") == "authentication_failed"
        and row.get("isApiErrorMessage") is True
        and row.get("apiErrorStatus") == 401
        and row.get("version") == "2.1.232"
        and isinstance(row.get("message"), dict)
        and row["message"].get("content") == [
            {"type": "text", "text": "Invalid API key · Fix external API key"}
        ]
    ]
    if len(listings) != 1 or len(errors) != 1:
        raise ReceiptError(f"claude {prefix}skill-listing/auth record schema changed")
    listing_index, listing = listings[0]
    error_index, error = errors[0]
    content = listing["attachment"].get("content")
    if not isinstance(content, str):
        raise ReceiptError(f"claude {prefix}skill listing content schema changed")
    target_count = sum(
        1 for line in content.splitlines()
        if line.startswith("- frontend-design:")
    )
    if target_count != (1 if target_expected else 0):
        raise ReceiptError(f"claude {prefix}frontend-design target count mismatch: {target_count}")
    if ":frontend-design:" in content:
        raise ReceiptError(f"claude {prefix}namespaced frontend-design unexpectedly present")
    session = listing.get("sessionId")
    if (
        listing_index >= error_index
        or not session
        or error.get("sessionId") != session
        or listing.get("cwd") != str(expected_project)
        or listing.get("version") != "2.1.232"
    ):
        raise ReceiptError(f"claude {prefix}session/cwd/order mismatch")
    stdout = stdout_path.read_bytes()
    expected_stdout = "Invalid API key · Fix external API key\n".encode()
    status_key = "claude_control" if prefix else "claude"
    if statuses[status_key] != 1 or stdout != expected_stdout:
        raise ReceiptError(f"claude {prefix}expected auth terminal mismatch")
    return {
        "status": statuses[status_key],
        "timeout_seconds": 30,
        "kill_after_seconds": 5,
        "session_id": session,
        "target_count": target_count,
        "attachment_skill_count": int(attachment_markers[0]),
        "markers": {
            "remote_settings": common_markers[0],
            "roots": common_markers[1],
            "plugin_count": common_markers[2],
            "loaded": loaded_pattern,
            "attachment": "Sending <integer> skills via attachment (initial)",
        },
        "artifacts": artifacts,
    }


schema = json.loads(
    (source_root / "scripts/ci/fixtures/runtime-skill-receipt.schema.json").read_text(encoding="utf-8")
)
if schema.get("$id") != "https://justinventit.dev/schemas/runtime-skill-receipt-v1.json":
    raise ReceiptError("receipt schema identity changed")
if statuses["codex"] != 0 or statuses["codex_control"] != 0:
    raise ReceiptError(f"codex debug prompt-input exit mismatch: {statuses}")

codex_project = raw / "codex-project.json"
codex_control = raw / "codex-control.json"
codex_records = {
    "project": file_record(codex_project, "codex project output"),
    "project_stderr": file_record(raw / "codex-project.stderr", "codex project stderr", allow_empty=True),
    "control": file_record(codex_control, "codex control output"),
    "control_stderr": file_record(raw / "codex-control.stderr", "codex control stderr", allow_empty=True),
}
locator_pattern = re.compile(
    r"\(file: (?P<path>/[^)]+/\.agents/skills/frontend-design/SKILL\.md)\)"
)
project_locators = locator_pattern.findall(codex_project.read_text(encoding="utf-8"))
control_locators = locator_pattern.findall(codex_control.read_text(encoding="utf-8"))
expected_skill = project / ".agents/skills/frontend-design/SKILL.md"
if project_locators != [str(expected_skill)]:
    raise ReceiptError(f"codex locator marker/cardinality changed: {project_locators!r}")
if control_locators:
    raise ReceiptError(f"codex no-project control found target: {control_locators!r}")
frontmatter_count = 0
for skill in (project / ".agents/skills").rglob("SKILL.md"):
    if re.search(r"(?m)^name: frontend-design$", skill.read_text(encoding="utf-8")):
        frontmatter_count += 1
if frontmatter_count != 1:
    raise ReceiptError(f"codex generated-tree frontmatter cardinality mismatch: {frontmatter_count}")

claude = validate_claude("", "claude-config", project, True)
claude_control = validate_claude(
    "control-", "control-claude-config", scratch / "no-project-control", False
)
skill_bytes = expected_skill.read_bytes()
head = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=source_root, text=True, capture_output=True, check=True
).stdout.strip()
tree = subprocess.run(
    ["git", "rev-parse", "HEAD^{tree}"], cwd=source_root, text=True, capture_output=True, check=True
).stdout.strip()
receipt = {
    "schema_version": 1,
    "receipt_kind": "availability",
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "candidate_head": head,
    "candidate_tree": tree,
    "generated_tree_sha256": generated_tree_digest(project),
    "node_version": "v22.23.2",
    "codex_version": "codex-cli 0.145.0",
    "claude_version": "2.1.232 (Claude Code)",
    "isolation": {
        "codex_home": "scratch",
        "claude_config_dir": "scratch",
        "managed_roots_absent": True,
        "inherited_auth": False,
    },
    "codex_availability": {
        "status": statuses["codex"],
        "target_count": frontmatter_count,
        "locator_start_marker": "(file: ",
        "locator_end_marker": ")",
        "observed_absolute_path": project_locators[0],
        "derivation_root": str(project),
        "derived_repository_path": ".agents/skills/frontend-design/SKILL.md",
        "skill_bytes": len(skill_bytes),
        "skill_sha256": hashlib.sha256(skill_bytes).hexdigest(),
        "no_project_target_count": len(control_locators),
        "artifacts": codex_records,
    },
    "claude_availability": claude,
    "claude_no_project": claude_control,
}
receipt_path = raw / "claude-receipt.json"
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
file_record(receipt_path, "machine receipt")
print(f"runtime skill availability receipt produced: {receipt_path}")
PY
  python3 "$source_root/scripts/ci/validate-runtime-receipt.py" \
    --schema "$schema_path" \
    --receipt "$receipt_raw/claude-receipt.json" \
    --artifact-root "$receipt_raw"
  printf 'runtime skill availability receipt: PASS %s\n' "$receipt_raw/claude-receipt.json"
}

case "${1:-}" in
  --validate-fixture)
    [[ "$#" -eq 2 ]] || die "usage: $0 --validate-fixture DIR"
    validate_fixture "$2"
    ;;
  --validate-availability-fixture)
    [[ "$#" -eq 2 ]] || die "usage: $0 --validate-availability-fixture DIR"
    validate_availability_fixture "$2"
    ;;
  "")
    acquire_ci_receipt
    ;;
  *)
    die "unknown argument: $1"
    ;;
esac

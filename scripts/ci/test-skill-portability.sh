#!/usr/bin/env bash
# RED acceptance runner for the portable frontend-design delivery slice.
#
# This file deliberately contains only controls. The implementation subjects it
# names are absent at the RED commit. A faithful RED therefore exits non-zero
# with MISSING_BEHAVIOR signatures, while keeping the runner itself executable
# and its independent pin fixture valid.
set -uo pipefail
umask 022

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXPECTED="$SCRIPT_DIR/fixtures/frontend-design.expected.json"

if [[ "${1:-}" == "--validate-scope" ]]; then
  [[ "$#" -eq 2 ]] || { printf 'scope gate usage: --validate-scope <json-path-list>\n' >&2; exit 2; }
  python3 - "$2" <<'PY'
import json
from pathlib import PurePosixPath
import re
import sys

paths = json.loads(open(sys.argv[1], encoding="utf-8").read())
allowed = (
    r"template/\.agents/skills/frontend-design(?:/.*)?",
    r"template/\.claude/skills/frontend-design(?:/.*)?",
    r"scripts/generate-skill-surfaces\.py",
    r"scripts/ci/(?:check-skill-routes\.py|test-skill-portability(?:-r[23]\.py|\.sh)|copier-update-check\.sh|copier-real-update-receipt\.py|validate-copier-evidence\.py|runtime-skill-receipt\.sh|validate-runtime-receipt\.py|generate-matrix-check\.sh)",
    r"scripts/ci/fixtures/(?:frontend-design\.expected\.json|runtime-skill-receipt\.schema\.json|copier-evidence-r3\.expected\.json|copier-portability/.*|runtime-availability-valid/.*)",
    r"\.github/workflows/ci\.yml",
    r"(?:CLAUDE\.md|README\.md|docs/(?:CONTEXT_CONTRACT|CUSTOMIZATION|GETTING_STARTED|MIGRATION|ROADMAP)\.md)",
)
for raw in paths:
    path = PurePosixPath(raw)
    normalized = path.as_posix()
    if raw.startswith("/") or ".." in path.parts or normalized != raw or not any(re.fullmatch(pattern, raw) for pattern in allowed):
        print(f"SCOPE_ESCAPE:{raw}", file=sys.stderr)
        raise SystemExit(1)
print(f"SCOPE_OK:{len(paths)}")
PY
  exit $?
fi

if [[ "${1:-}" == "--compare-rollback-evidence" ]]; then
  [[ "$#" -eq 3 ]] || { printf 'rollback gate usage: --compare-rollback-evidence <before.json> <after.json>\n' >&2; exit 2; }
  python3 - "$2" "$3" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    before = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    after = json.load(handle)
required = {"matrix_sets", "matrix_pass_count", "matrix_exit", "normalized_lines"}
if set(before) != required or set(after) != required:
    print("ROLLBACK_EVIDENCE_SCHEMA", file=sys.stderr)
    raise SystemExit(1)
if before != after or before["matrix_exit"] != 0:
    print("ROLLBACK_NORMALIZED_MISMATCH", file=sys.stderr)
    raise SystemExit(1)
print("ROLLBACK_EVIDENCE_EQUAL")
PY
  exit $?
fi

RUN_TMP="$(mktemp -d "${TMPDIR:-/tmp}/jv-portability-red.XXXXXX")"
EXECUTION_RECEIPT="$RUN_TMP/executed-cases.json"
CASE_REGISTRY="$RUN_TMP/case-registry.json"
cleanup() { rm -rf -- "$RUN_TMP"; }
trap cleanup EXIT INT TERM

printf '{"schema_version":2,"cases":[]}\n' > "$EXECUTION_RECEIPT"
printf '{"schema_version":2,"cases":[]}\n' > "$CASE_REGISTRY"

PASS=0
FAIL=0
declare -a FAILURES=()

pass() {
  PASS=$((PASS + 1))
  printf '[PASS] %s\n' "$1"
}

fail() {
  local cell="$1" message="$2"
  FAIL=$((FAIL + 1))
  FAILURES+=("$cell:$message")
  printf '[FAIL] %s %s\n' "$cell" "$message"
}

require_file() {
  local cell="$1" rel="$2"
  if [[ -f "$ROOT/$rel" ]]; then
    pass "$cell $rel present"
    return 0
  fi
  fail "$cell" "MISSING_BEHAVIOR:$rel"
  return 1
}

require_executable() {
  local cell="$1" rel="$2"
  if [[ -f "$ROOT/$rel" && -x "$ROOT/$rel" ]]; then
    pass "$cell $rel executable"
    return 0
  fi
  fail "$cell" "MISSING_BEHAVIOR:$rel executable"
  return 1
}

require_contains() {
  local cell="$1" rel="$2" literal="$3"
  if [[ -f "$ROOT/$rel" ]] && grep -Fq -- "$literal" "$ROOT/$rel"; then
    pass "$cell $rel contains $literal"
    return 0
  fi
  fail "$cell" "MISSING_BEHAVIOR:$rel::$literal"
  return 1
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

byte_count() {
  wc -c < "$1" | tr -d '[:space:]'
}

check_fixture_authority() {
  local cell="P01"
  if ! require_file "$cell" "scripts/ci/fixtures/frontend-design.expected.json"; then
    return
  fi
  if python3 - "$EXPECTED" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    value = json.load(handle)

expected = {
    "schema_version": 1,
    "name": "frontend-design",
    "repository": "anthropics/claude-plugins-official",
    "commit": "d029127f7d29bdb8fd8902ac34dd7d5c8ba92b6e",
    "path": "plugins/frontend-design/skills/frontend-design",
    "equivalent_repository": "anthropics/claude-code",
    "plugin_name": "frontend-design",
    "plugin_version": "1.1.0",
    "authors": ["Prithvi Rajasekaran", "Alexander Bricken"],
    "spdx": "Apache-2.0",
    "license_filename": "LICENSE.txt",
    "license_frontmatter": "Complete terms in LICENSE.txt",
    "skill_bytes": 8260,
    "skill_sha": "1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd",
    "license_bytes": 10174,
    "license_sha": "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594",
    "codex_route": {"mode": "canonical", "path": ".agents/skills/frontend-design"},
    "claude_route": {"mode": "physical-copy", "path": ".claude/skills/frontend-design"},
    "copier": "9.17.1",
    "node": "v22.23.2",
    "codex": "codex-cli 0.145.0",
    "claude": "2.1.232 (Claude Code)",
}
skill = value["skill"]
observed = {
    "schema_version": value["schema_version"],
    "name": skill["name"],
    "repository": skill["upstream"]["repository"],
    "commit": skill["upstream"]["commit"],
    "path": skill["upstream"]["path"],
    "equivalent_repository": skill["equivalent_distribution"]["repository"],
    "plugin_name": skill["equivalent_distribution"]["plugin_name"],
    "plugin_version": skill["equivalent_distribution"]["plugin_version"],
    "authors": skill["authors"],
    "spdx": skill["license"]["spdx"],
    "license_filename": skill["license"]["filename"],
    "license_frontmatter": skill["license"]["frontmatter"],
    "skill_bytes": skill["files"]["SKILL.md"]["bytes"],
    "skill_sha": skill["files"]["SKILL.md"]["sha256"],
    "license_bytes": skill["files"]["LICENSE.txt"]["bytes"],
    "license_sha": skill["files"]["LICENSE.txt"]["sha256"],
    "codex_route": skill["runtime_routes"]["codex"],
    "claude_route": skill["runtime_routes"]["claude"],
    **value["toolchain"],
}
if observed != expected:
    raise SystemExit(f"independent expected fixture mismatch: {observed!r}")
PY
  then
    pass "$cell independent pinned authority"
  else
    fail "$cell" "HARNESS_BROKEN:independent expected fixture mismatch"
  fi
}

check_canonical_source() {
  local cell="P02" base="$ROOT/template/.agents/skills/frontend-design"
  local skill="$base/SKILL.md" license="$base/LICENSE.txt" provenance="$base/PROVENANCE.json"
  local missing=0
  [[ -f "$skill" ]] || { fail "$cell" "MISSING_BEHAVIOR:template/.agents/skills/frontend-design/SKILL.md"; missing=1; }
  [[ -f "$license" ]] || { fail "$cell" "MISSING_BEHAVIOR:template/.agents/skills/frontend-design/LICENSE.txt"; missing=1; }
  [[ -f "$provenance" ]] || { fail "$cell" "MISSING_BEHAVIOR:template/.agents/skills/frontend-design/PROVENANCE.json"; missing=1; }
  [[ "$missing" -eq 0 ]] || return

  local skill_sha license_sha skill_bytes license_bytes
  skill_sha="$(sha256_file "$skill")"
  license_sha="$(sha256_file "$license")"
  skill_bytes="$(byte_count "$skill")"
  license_bytes="$(byte_count "$license")"
  if [[ "$skill_sha" == "1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd" &&
        "$skill_bytes" == "8260" &&
        "$license_sha" == "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594" &&
        "$license_bytes" == "10174" ]]; then
    pass "$cell exact pinned payload and license bytes"
  else
    fail "$cell" "SOURCE_AUTHORITY_MISMATCH:skill=$skill_sha/$skill_bytes license=$license_sha/$license_bytes"
  fi

  if grep -Fq 'name: frontend-design' "$skill" &&
     grep -Fq 'license: Complete terms in LICENSE.txt' "$skill"; then
    pass "$cell exact frontmatter identity and license prose"
  else
    fail "$cell" "FRONTMATTER_MISMATCH:frontend-design"
  fi

  if python3 - "$EXPECTED" "$provenance" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    expected = json.load(handle)["skill"]
with open(sys.argv[2], encoding="utf-8") as handle:
    provenance = json.load(handle)

required = {
    "name": expected["name"],
    "upstream": expected["upstream"],
    "equivalent_distribution": expected["equivalent_distribution"],
    "authors": expected["authors"],
    "license": expected["license"],
    "files": expected["files"],
    "runtime_routes": expected["runtime_routes"],
}
if provenance != {"schema_version": 1, **required}:
    raise SystemExit("provenance mismatch")
PY
  then
    pass "$cell provenance equals independent fixture"
  else
    fail "$cell" "PROVENANCE_MISMATCH:independent fixture"
  fi
}

check_physical_projection() {
  local cell="P03"
  local canonical="$ROOT/template/.agents/skills/frontend-design"
  local projection="$ROOT/template/.claude/skills/frontend-design"
  if [[ ! -d "$canonical" ]]; then
    fail "$cell" "MISSING_BEHAVIOR:canonical tree blocks projection control"
    return
  fi
  if [[ ! -d "$projection" ]]; then
    fail "$cell" "MISSING_BEHAVIOR:template/.claude/skills/frontend-design physical projection"
    return
  fi
  if [[ -L "$projection" ]]; then
    fail "$cell" "PROJECTION_TYPE:directory symlink"
    return
  fi
  if diff -qr --no-dereference "$canonical" "$projection" >/dev/null; then
    pass "$cell exact recursive physical projection"
  else
    fail "$cell" "PROJECTION_DRIFT:recursive entry/type/byte mismatch"
  fi
  local bad
  bad="$(find "$canonical" "$projection" \( -type l -o -type f -perm /111 \) -print)"
  if [[ -z "$bad" ]]; then
    pass "$cell portable regular non-executable file class"
  else
    fail "$cell" "PROJECTION_CLASS:$bad"
  fi
}

check_generator() {
  local cell="P04" rel="scripts/generate-skill-surfaces.py"
  if ! require_file "$cell" "$rel"; then
    return
  fi
  local before after rc
  before="$(git -C "$ROOT" status --porcelain=v1)"
  python3 "$ROOT/$rel" --project-root "$ROOT" --check >/tmp/jv-portability-generator-check.out 2>&1
  rc=$?
  after="$(git -C "$ROOT" status --porcelain=v1)"
  if [[ "$rc" -eq 0 && "$before" == "$after" ]]; then
    pass "$cell non-mutating generator check"
  else
    fail "$cell" "GENERATOR_CHECK:exit=$rc mutation=$([[ "$before" == "$after" ]] && printf no || printf yes)"
  fi
  require_contains "$cell" "$rel" "--project-root" || true
  require_contains "$cell" "$rel" "--check" || true
}

check_route_validator() {
  local cell="P05" rel="scripts/ci/check-skill-routes.py"
  if ! require_file "$cell" "$rel"; then
    return
  fi
  local rc
  python3 "$ROOT/$rel" --project-root "$ROOT" >/tmp/jv-portability-route-check.out 2>&1
  rc=$?
  if [[ "$rc" -eq 0 ]]; then
    pass "$cell positive route/source/projection control"
  else
    fail "$cell" "ROUTE_CONTROL:exit=$rc:$(tail -n 1 /tmp/jv-portability-route-check.out)"
  fi
  require_contains "$cell" "$rel" "--project-root" || true
}

# These mutation IDs are the executable acceptance inventory. The GREEN
# checker/generator must exercise each arm in disposable copies and emit the
# named class while a same-shape control passes. Their presence here prevents a
# later implementation from making RED green by silently dropping a scenario.
check_mutation_inventory() {
  local cell="P06"
  local -a mutations=(
    fixture-field-drift
    expected-upstream-repository-drift
    expected-upstream-commit-drift
    expected-upstream-path-drift
    expected-equivalent-repository-drift
    expected-plugin-name-drift
    expected-plugin-version-drift
    expected-authors-drift
    expected-spdx-drift
    expected-license-filename-drift
    expected-license-frontmatter-drift
    expected-skill-bytes-drift
    expected-skill-sha-drift
    expected-license-bytes-drift
    expected-license-sha-drift
    expected-codex-mode-drift
    expected-codex-path-drift
    expected-claude-mode-drift
    expected-claude-path-drift
    expected-copier-pin-drift
    expected-node-pin-drift
    expected-codex-pin-drift
    expected-claude-pin-drift
    canonical-skill-missing
    canonical-license-missing
    canonical-provenance-missing
    payload-plus-lock-consistent-drift
    payload-byte-drift
    license-byte-drift
    malformed-frontmatter
    missing-frontmatter-name
    wrong-frontmatter-name
    empty-description
    altered-license-prose
    escaping-license-filename
    jinja-expression-leak
    jinja-statement-leak
    projection-byte-drift
    projection-missing-entry
    projection-extra-entry
    projection-stale-entry
    projection-removed-entry
    projection-file-to-directory
    projection-permission-class
    projection-directory-symlink
    projection-payload-symlink
    projection-pointer-file
    projection-plugin-metadata
    route-parent-traversal
    route-absolute
    route-normalized-escape
    route-empty
    route-nonnormalized-alias
    codex-route-parent-traversal
    codex-route-absolute
    codex-route-normalized-escape
    codex-route-empty
    codex-route-nonnormalized-alias
    claude-route-parent-traversal
    claude-route-absolute
    claude-route-normalized-escape
    claude-route-empty
    claude-route-nonnormalized-alias
    codex-frontmatter-duplicate
    codex-basename-mismatch
    codex-different-basename-same-name
    codex-same-basename-different-name
    claude-basename-duplicate
    claude-frontmatter-mismatch
    claude-different-basename-same-name
    claude-same-basename-different-name
    nested-all-depth-duplicate
    namespaced-plugin-sighting-counted
    claude-command-conflict
    unsupported-project-codex-route
    copier-missing
    copier-wrong-version
    copier-clean-overwrite
    copier-conflict-markers
    copier-reject-artifact
    copier-unclassified-outcome
    copier-canonical-conflict
    copier-unexpected-artifact
    copier-project-owned-drift
    copier-skip-state-drift
    copier-partial-marker-set
    copier-answer-solo-go
    copier-answer-cluster-supabase
    copier-answer-cluster-postgres
    copier-answer-cluster-rust
    generator-regeneration-nondeterministic
    generator-check-mutates
    runtime-missing-cli
    runtime-wrong-cli-version
    runtime-marker-drift
    runtime-no-project-control
    runtime-missing-node
    runtime-missing-codex-cli
    runtime-missing-claude-cli
    runtime-wrong-node-version
    runtime-wrong-codex-version
    runtime-wrong-claude-version
    codex-no-project-control-present
    claude-marker-drift
    claude-mixed-evidence-tuple
    claude-missing-artifact
    claude-empty-required-artifact
    claude-missing-stderr
    claude-nonzero-stderr
    claude-transcript-cardinality
    claude-artifact-wrong-class
    claude-receipt-schema-invalid
    claude-expected-auth-missing
    claude-expected-auth-control-corrupt
    claude-unexpected-auth-success
    claude-unexpected-exit
    claude-timeout-or-signal
    claude-session-or-order-mismatch
    claude-invocation-body-truncated
    claude-invocation-body-appended
    codex-native-record-missing
    codex-native-record-duplicate
    codex-path-in-original-prompt
    codex-client-supplied-skill-item
    codex-body-truncated-or-appended
    codex-prefix-only-match
    codex-fallback-without-reruling
    rollback-partial-removal
    rollback-normalized-result-mismatch
    scope-forbidden-path
    scope-forbidden-agents
    scope-forbidden-consumer-generator
    scope-forbidden-customer-portal
    scope-forbidden-runtime-home
  )
  if [[ "${#mutations[@]}" -eq 134 ]]; then
    pass "$cell 134 named negative/mutation arms locked"
  else
    fail "$cell" "HARNESS_BROKEN:mutation inventory count=${#mutations[@]} expected=134"
  fi
  local duplicates
  duplicates="$(printf '%s\n' "${mutations[@]}" | LC_ALL=C sort | uniq -d)"
  if [[ -z "$duplicates" ]]; then
    pass "$cell mutation inventory has unique stable IDs"
  else
    fail "$cell" "HARNESS_BROKEN:duplicate mutation IDs:$duplicates"
  fi

  local declared_file="$RUN_TMP/declared-cases.txt"
  printf '%s\n' "${mutations[@]}" > "$declared_file"
  if python3 - "$declared_file" "$CASE_REGISTRY" <<'PY'
import json
from pathlib import Path
import sys

declared = [line for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line]
if len(declared) != len(set(declared)):
    raise SystemExit("declared case IDs are not unique")

def family(index):
    if index < 75:
        return "static-checker-generator"
    if index < 90:
        return "copier-update-matrix"
    if index < 92:
        return "generator-invariants"
    if index < 127:
        return "runtime-receipt"
    return "rollback-scope-gate"

registry_path = Path(sys.argv[2])
registry_path.write_text(
    json.dumps(
        {
            "schema_version": 2,
            "cases": [
                {"id": case_id, "family": family(index), "evidence": "real-subject-required"}
                for index, case_id in enumerate(declared)
            ],
        },
        indent=2,
        sort_keys=True,
    ) + "\n",
    encoding="utf-8",
)
print(f"registered={len(declared)} real-subject-required=all")
PY
  then
    pass "$cell all named arms registered as real-subject-required"
  else
    fail "$cell" "HARNESS_BROKEN:case registry construction"
  fi

  local checker="scripts/ci/check-skill-routes.py"
  local generator="scripts/generate-skill-surfaces.py"
  local subject_mode="execute"
  if [[ ! -f "$ROOT/$checker" || ! -f "$ROOT/$generator" ]]; then
    fail "$cell" "MISSING_BEHAVIOR:disposable mutation executors ($checker + $generator)"
    subject_mode="register"
  fi

  if python3 - "$ROOT" "$EXECUTION_RECEIPT" "$declared_file" "$subject_mode" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
receipt_path = Path(sys.argv[2])
declared_path = Path(sys.argv[3])
mode = sys.argv[4]
checker_rel = Path("scripts/ci/check-skill-routes.py")
generator_rel = Path("scripts/generate-skill-surfaces.py")


def run_subject(tree: Path, subject: str) -> subprocess.CompletedProcess[str]:
    if subject == "checker":
        command = [sys.executable, str(root / checker_rel), "--project-root", str(tree)]
    else:
        command = [
            sys.executable,
            str(root / generator_rel),
            "--project-root",
            str(tree),
            "--check",
        ]
    return subprocess.run(command, text=True, capture_output=True, timeout=30, check=False)


def copy_tree(parent: Path, name: str) -> Path:
    target = parent / name
    shutil.copytree(
        root,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    return target


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutation precondition missing in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def canonical(tree: Path) -> Path:
    return tree / "template/.agents/skills/frontend-design"


def projection(tree: Path) -> Path:
    return tree / "template/.claude/skills/frontend-design"


def fixture(tree: Path) -> Path:
    return tree / "scripts/ci/fixtures/frontend-design.expected.json"


def provenance(tree: Path) -> Path:
    return canonical(tree) / "PROVENANCE.json"


def mutate_fixture_field(tree: Path) -> None:
    value = load_json(fixture(tree))
    value["skill"]["equivalent_distribution"]["plugin_version"] = "9.9.9"
    save_json(fixture(tree), value)


def mutate_consistent_payload_and_locks(tree: Path) -> None:
    skill_path = canonical(tree) / "SKILL.md"
    skill_path.write_bytes(skill_path.read_bytes() + b"\nmutated\n")
    digest = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    size = skill_path.stat().st_size
    for path, nested in (
        (fixture(tree), ("skill", "files", "SKILL.md")),
        (provenance(tree), ("files", "SKILL.md")),
    ):
        value = load_json(path)
        node = value
        for key in nested:
            node = node[key]
        node["sha256"] = digest
        node["bytes"] = size
        save_json(path, value)


def mutate_payload_byte(tree: Path) -> None:
    path = canonical(tree) / "SKILL.md"
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(data)


def mutate_license_byte(tree: Path) -> None:
    path = canonical(tree) / "LICENSE.txt"
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(data)


def mutate_malformed_frontmatter(tree: Path) -> None:
    replace(canonical(tree) / "SKILL.md", "---", "--broken--")


def mutate_missing_name(tree: Path) -> None:
    path = canonical(tree) / "SKILL.md"
    path.write_text(re.sub(r"(?m)^name:.*\n", "", path.read_text(encoding="utf-8"), count=1), encoding="utf-8")


def mutate_wrong_name(tree: Path) -> None:
    replace(canonical(tree) / "SKILL.md", "name: frontend-design", "name: other-design")


def mutate_empty_description(tree: Path) -> None:
    path = canonical(tree) / "SKILL.md"
    path.write_text(re.sub(r"(?m)^description:.*$", "description:", path.read_text(encoding="utf-8"), count=1), encoding="utf-8")


def mutate_license_prose(tree: Path) -> None:
    replace(
        canonical(tree) / "SKILL.md",
        "license: Complete terms in LICENSE.txt",
        "license: Apache-2.0",
    )


def mutate_license_escape(tree: Path) -> None:
    value = load_json(provenance(tree))
    value["license"]["filename"] = "../../LICENSE"
    save_json(provenance(tree), value)


def mutate_jinja_expression(tree: Path) -> None:
    path = canonical(tree) / "SKILL.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n{{ unresolved }}\n", encoding="utf-8")


def mutate_jinja_statement(tree: Path) -> None:
    path = canonical(tree) / "SKILL.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n{% if unresolved %}\n", encoding="utf-8")


def mutate_projection_byte(tree: Path) -> None:
    path = projection(tree) / "SKILL.md"
    path.write_bytes(path.read_bytes() + b"drift")


def mutate_projection_missing(tree: Path) -> None:
    (projection(tree) / "LICENSE.txt").unlink()


def mutate_projection_extra(tree: Path) -> None:
    (projection(tree) / "EXTRA.txt").write_text("extra\n", encoding="utf-8")


def mutate_projection_type(tree: Path) -> None:
    path = projection(tree) / "LICENSE.txt"
    path.unlink()
    path.mkdir()


def mutate_projection_mode(tree: Path) -> None:
    path = projection(tree) / "SKILL.md"
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def mutate_projection_dir_symlink(tree: Path) -> None:
    path = projection(tree)
    shutil.rmtree(path)
    path.symlink_to(canonical(tree), target_is_directory=True)


def mutate_projection_payload_symlink(tree: Path) -> None:
    path = projection(tree) / "SKILL.md"
    path.unlink()
    path.symlink_to(Path("../../../.agents/skills/frontend-design/SKILL.md"))


def mutate_projection_pointer(tree: Path) -> None:
    path = projection(tree) / "SKILL.md"
    path.write_text("../../../.agents/skills/frontend-design/SKILL.md\n", encoding="utf-8")


def mutate_plugin_metadata(tree: Path) -> None:
    path = projection(tree) / ".claude-plugin"
    path.mkdir()
    (path / "plugin.json").write_text("{}\n", encoding="utf-8")


def mutate_route(tree: Path, value: str) -> None:
    for path, nested in (
        (fixture(tree), ("skill", "runtime_routes", "claude")),
        (provenance(tree), ("runtime_routes", "claude")),
    ):
        payload = load_json(path)
        node = payload
        for key in nested:
            node = node[key]
        node["path"] = value
        save_json(path, payload)


def mutate_codex_duplicate(tree: Path) -> None:
    path = tree / "template/.agents/skills/nested/other-name"
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("---\nname: frontend-design\ndescription: duplicate\n---\n", encoding="utf-8")


def mutate_claude_duplicate(tree: Path) -> None:
    path = tree / "template/.claude/skills/nested/frontend-design"
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("---\nname: other-name\ndescription: duplicate\n---\n", encoding="utf-8")


def mutate_claude_name_mismatch(tree: Path) -> None:
    replace(projection(tree) / "SKILL.md", "name: frontend-design", "name: other-name")


def mutate_command_conflict(tree: Path) -> None:
    path = tree / "template/.claude/commands"
    path.mkdir(parents=True, exist_ok=True)
    (path / "frontend-design.md").write_text("conflict\n", encoding="utf-8")


def mutate_codex_route(tree: Path) -> None:
    path = tree / "template/.codex/skills/frontend-design"
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("---\nname: frontend-design\ndescription: unsupported\n---\n", encoding="utf-8")


def set_json_path(path: Path, keys: tuple[str, ...], value) -> None:
    payload = load_json(path)
    node = payload
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    save_json(path, payload)


def mutate_expected(keys: tuple[str, ...], value):
    return lambda tree: set_json_path(fixture(tree), keys, value)


def remove_path(relative: str):
    return lambda tree: (tree / relative).unlink()


def mutate_runtime_route(tree: Path, runtime: str, value: str) -> None:
    for path, keys in (
        (fixture(tree), ("skill", "runtime_routes", runtime, "path")),
        (provenance(tree), ("runtime_routes", runtime, "path")),
    ):
        set_json_path(path, keys, value)


def mutate_projection_named_extra(tree: Path, name: str) -> None:
    (projection(tree) / name).write_text("stale projection entry\n", encoding="utf-8")


def add_skill(tree: Path, runtime: str, path_name: str, frontmatter_name: str) -> None:
    base = "template/.agents/skills" if runtime == "codex" else "template/.claude/skills"
    path = tree / base / "nested" / path_name
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {frontmatter_name}\ndescription: duplicate fixture\n---\nbody\n",
        encoding="utf-8",
    )


def mutate_namespaced_sighting(tree: Path) -> None:
    path = tree / "template/.claude/plugins/example/skills/frontend-design"
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        "---\nname: frontend-design\ndescription: namespaced plugin fixture\n---\nbody\n",
        encoding="utf-8",
    )


cases = [
    ("fixture-field-drift", "checker", r"fixture|schema|expected", mutate_expected(("schema_version",), 2), True),
    ("expected-upstream-repository-drift", "checker", r"repository|upstream|expected", mutate_expected(("skill", "upstream", "repository"), "other/repo"), True),
    ("expected-upstream-commit-drift", "checker", r"commit|upstream|expected", mutate_expected(("skill", "upstream", "commit"), "0" * 40), True),
    ("expected-upstream-path-drift", "checker", r"path|upstream|expected", mutate_expected(("skill", "upstream", "path"), "other/path"), True),
    ("expected-equivalent-repository-drift", "checker", r"equivalent|repository|expected", mutate_expected(("skill", "equivalent_distribution", "repository"), "other/repo"), True),
    ("expected-plugin-name-drift", "checker", r"plugin|name|expected", mutate_expected(("skill", "equivalent_distribution", "plugin_name"), "other"), True),
    ("expected-plugin-version-drift", "checker", r"plugin|version|expected", mutate_expected(("skill", "equivalent_distribution", "plugin_version"), "9.9.9"), True),
    ("expected-authors-drift", "checker", r"authors|expected", mutate_expected(("skill", "authors"), ["Unknown"]), True),
    ("expected-spdx-drift", "checker", r"spdx|license|expected", mutate_expected(("skill", "license", "spdx"), "MIT"), True),
    ("expected-license-filename-drift", "checker", r"license|filename|expected", mutate_expected(("skill", "license", "filename"), "OTHER.txt"), True),
    ("expected-license-frontmatter-drift", "checker", r"license|frontmatter|expected", mutate_expected(("skill", "license", "frontmatter"), "changed"), True),
    ("expected-skill-bytes-drift", "checker", r"skill|bytes|expected", mutate_expected(("skill", "files", "SKILL.md", "bytes"), 1), True),
    ("expected-skill-sha-drift", "checker", r"skill|sha|hash|expected", mutate_expected(("skill", "files", "SKILL.md", "sha256"), "0" * 64), True),
    ("expected-license-bytes-drift", "checker", r"license|bytes|expected", mutate_expected(("skill", "files", "LICENSE.txt", "bytes"), 1), True),
    ("expected-license-sha-drift", "checker", r"license|sha|hash|expected", mutate_expected(("skill", "files", "LICENSE.txt", "sha256"), "0" * 64), True),
    ("expected-codex-mode-drift", "checker", r"codex|mode|expected", mutate_expected(("skill", "runtime_routes", "codex", "mode"), "copy"), True),
    ("expected-codex-path-drift", "checker", r"codex|path|expected", mutate_expected(("skill", "runtime_routes", "codex", "path"), ".codex/skills/frontend-design"), True),
    ("expected-claude-mode-drift", "checker", r"claude|mode|expected", mutate_expected(("skill", "runtime_routes", "claude", "mode"), "symlink"), True),
    ("expected-claude-path-drift", "checker", r"claude|path|expected", mutate_expected(("skill", "runtime_routes", "claude", "path"), ".claude/skills/nested/frontend-design"), True),
    ("expected-copier-pin-drift", "checker", r"copier|toolchain|expected", mutate_expected(("toolchain", "copier"), "9.16.0"), True),
    ("expected-node-pin-drift", "checker", r"node|toolchain|expected", mutate_expected(("toolchain", "node"), "v22.16.0"), True),
    ("expected-codex-pin-drift", "checker", r"codex|toolchain|expected", mutate_expected(("toolchain", "codex"), "codex-cli 0.144.0"), True),
    ("expected-claude-pin-drift", "checker", r"claude|toolchain|expected", mutate_expected(("toolchain", "claude"), "2.1.231 (Claude Code)"), True),
    ("canonical-skill-missing", "checker", r"skill|missing", remove_path("template/.agents/skills/frontend-design/SKILL.md"), True),
    ("canonical-license-missing", "checker", r"license|missing", remove_path("template/.agents/skills/frontend-design/LICENSE.txt"), True),
    ("canonical-provenance-missing", "checker", r"provenance|missing", remove_path("template/.agents/skills/frontend-design/PROVENANCE.json"), True),
    ("payload-plus-lock-consistent-drift", "checker", r"fixture|expected|authority", mutate_consistent_payload_and_locks, True),
    ("payload-byte-drift", "checker", r"payload|hash|fixture", mutate_payload_byte, True),
    ("license-byte-drift", "checker", r"license|hash|fixture", mutate_license_byte, True),
    ("malformed-frontmatter", "checker", r"frontmatter|yaml", mutate_malformed_frontmatter, True),
    ("missing-frontmatter-name", "checker", r"frontmatter|name", mutate_missing_name, True),
    ("wrong-frontmatter-name", "checker", r"frontmatter|name|basename", mutate_wrong_name, True),
    ("empty-description", "checker", r"description|frontmatter", mutate_empty_description, True),
    ("altered-license-prose", "checker", r"license|frontmatter", mutate_license_prose, True),
    ("escaping-license-filename", "checker", r"license|contain|escape|route", mutate_license_escape, True),
    ("jinja-expression-leak", "checker", r"jinja|unresolved", mutate_jinja_expression, True),
    ("jinja-statement-leak", "checker", r"jinja|unresolved", mutate_jinja_statement, True),
    ("projection-byte-drift", "generator", r"projection|drift|byte|hash", mutate_projection_byte, True),
    ("projection-missing-entry", "generator", r"projection|missing|entry", mutate_projection_missing, True),
    ("projection-extra-entry", "generator", r"projection|extra|entry|stale", mutate_projection_extra, True),
    ("projection-stale-entry", "generator", r"projection|extra|entry|stale", lambda tree: mutate_projection_named_extra(tree, "STALE.txt"), True),
    ("projection-removed-entry", "generator", r"projection|missing|removed|entry", remove_path("template/.claude/skills/frontend-design/PROVENANCE.json"), True),
    ("projection-file-to-directory", "generator", r"projection|type|directory", mutate_projection_type, True),
    ("projection-permission-class", "generator", r"projection|permission|executable|mode", mutate_projection_mode, True),
    ("projection-directory-symlink", "checker", r"symlink|physical|projection", mutate_projection_dir_symlink, True),
    ("projection-payload-symlink", "checker", r"symlink|regular|projection", mutate_projection_payload_symlink, True),
    ("projection-pointer-file", "checker", r"pointer|hash|projection|drift", mutate_projection_pointer, True),
    ("projection-plugin-metadata", "checker", r"plugin|extra|entry", mutate_plugin_metadata, True),
    ("route-parent-traversal", "checker", r"route|contain|traversal|normalize", lambda tree: mutate_runtime_route(tree, "claude", "../../x"), True),
    ("route-absolute", "checker", r"route|absolute|contain", lambda tree: mutate_runtime_route(tree, "claude", "/tmp/x"), True),
    ("route-normalized-escape", "checker", r"route|contain|traversal|normalize", lambda tree: mutate_runtime_route(tree, "claude", ".claude/../../x"), True),
    ("route-empty", "checker", r"route|empty", lambda tree: mutate_runtime_route(tree, "claude", ""), True),
    ("route-nonnormalized-alias", "checker", r"route|normalize|alias", lambda tree: mutate_runtime_route(tree, "claude", ".claude/skills/../skills/frontend-design"), True),
    ("codex-route-parent-traversal", "checker", r"codex|route|contain|traversal", lambda tree: mutate_runtime_route(tree, "codex", "../../x"), True),
    ("codex-route-absolute", "checker", r"codex|route|absolute", lambda tree: mutate_runtime_route(tree, "codex", "/tmp/x"), True),
    ("codex-route-normalized-escape", "checker", r"codex|route|normalize|contain", lambda tree: mutate_runtime_route(tree, "codex", ".agents/../../x"), True),
    ("codex-route-empty", "checker", r"codex|route|empty", lambda tree: mutate_runtime_route(tree, "codex", ""), True),
    ("codex-route-nonnormalized-alias", "checker", r"codex|route|normalize", lambda tree: mutate_runtime_route(tree, "codex", ".agents/skills/../skills/frontend-design"), True),
    ("claude-route-parent-traversal", "checker", r"claude|route|contain|traversal", lambda tree: mutate_runtime_route(tree, "claude", "../../x"), True),
    ("claude-route-absolute", "checker", r"claude|route|absolute", lambda tree: mutate_runtime_route(tree, "claude", "/tmp/x"), True),
    ("claude-route-normalized-escape", "checker", r"claude|route|normalize|contain", lambda tree: mutate_runtime_route(tree, "claude", ".claude/../../x"), True),
    ("claude-route-empty", "checker", r"claude|route|empty", lambda tree: mutate_runtime_route(tree, "claude", ""), True),
    ("claude-route-nonnormalized-alias", "checker", r"claude|route|normalize", lambda tree: mutate_runtime_route(tree, "claude", ".claude/skills/../skills/frontend-design"), True),
    ("codex-frontmatter-duplicate", "checker", r"codex|duplicate|cardinality", mutate_codex_duplicate, True),
    ("codex-basename-mismatch", "checker", r"codex|basename|name", lambda tree: add_skill(tree, "codex", "frontend-design", "other-name"), True),
    ("codex-different-basename-same-name", "checker", r"codex|duplicate|cardinality|name", lambda tree: add_skill(tree, "codex", "other-name", "frontend-design"), True),
    ("codex-same-basename-different-name", "checker", r"codex|basename|name", lambda tree: add_skill(tree, "codex", "frontend-design", "other-name"), True),
    ("claude-basename-duplicate", "checker", r"claude|duplicate|cardinality|basename", mutate_claude_duplicate, True),
    ("claude-frontmatter-mismatch", "checker", r"claude|frontmatter|name|basename|projection", mutate_claude_name_mismatch, True),
    ("claude-different-basename-same-name", "checker", r"claude|name|basename", lambda tree: add_skill(tree, "claude", "other-name", "frontend-design"), True),
    ("claude-same-basename-different-name", "checker", r"claude|duplicate|cardinality|basename", lambda tree: add_skill(tree, "claude", "frontend-design", "other-name"), True),
    ("nested-all-depth-duplicate", "checker", r"nested|duplicate|cardinality|depth", lambda tree: add_skill(tree, "codex", "deep/other-name", "frontend-design"), True),
    ("namespaced-plugin-sighting-counted", "checker", r"", mutate_namespaced_sighting, False),
    ("claude-command-conflict", "checker", r"claude|command|conflict", mutate_command_conflict, True),
    ("unsupported-project-codex-route", "checker", r"codex|unsupported|route", mutate_codex_route, True),
]

declared = [line for line in declared_path.read_text(encoding="utf-8").splitlines() if line][:75]
if [item[0] for item in cases] != declared:
    raise SystemExit("static subject-bound case definitions do not equal the declared static prefix")
if mode == "register":
    print("reachable static subject definitions=75; execution deferred until subjects exist")
    raise SystemExit(0)

for subject in ("checker", "generator"):
    control = run_subject(root, subject)
    if control.returncode != 0:
        print(f"control failed for {subject}: rc={control.returncode}", file=sys.stderr)
        print(control.stdout + control.stderr, file=sys.stderr)
        raise SystemExit(1)

executed = []
with tempfile.TemporaryDirectory(prefix="jv-portability-mutations.") as temp:
    temp_root = Path(temp)
    for mutation_id, subject, diagnostic, mutate, expect_failure in cases:
        control = run_subject(root, subject)
        if control.returncode != 0:
            raise SystemExit(f"{mutation_id}: {subject} same-shape control failed: {control.stdout + control.stderr}")
        tree = copy_tree(temp_root, mutation_id)
        mutate(tree)
        result = run_subject(tree, subject)
        output = result.stdout + result.stderr
        if expect_failure:
            if result.returncode == 0:
                raise SystemExit(f"{mutation_id}: mutation unexpectedly passed")
            if not re.search(diagnostic, output, re.IGNORECASE):
                raise SystemExit(f"{mutation_id}: expected /{diagnostic}/; got {output!r}")
            expectation = "named-nonzero"
        else:
            if result.returncode != 0:
                raise SystemExit(f"{mutation_id}: valid namespaced control failed: {output!r}")
            expectation = "mutated-positive-control"
        executed.append({
            "id": mutation_id,
            "family": "static-checker-generator",
            "subject": str(root / (checker_rel if subject == "checker" else generator_rel)),
            "control_exit": control.returncode,
            "case_exit": result.returncode,
            "expectation": expectation,
            "diagnostic_pattern": diagnostic,
        })

receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
receipt["cases"].extend(executed)
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"actual static subject executions={len(executed)}")
PY
  then
    pass "$cell static case definitions match registry; real subjects execute when present"
  else
    fail "$cell" "MUTATION_MATRIX:control, nonzero, or named-diagnostic failure"
  fi

  if python3 - "$ROOT" "$EXECUTION_RECEIPT" "$declared_file" "$subject_mode" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
receipt_path = Path(sys.argv[2])
declared = [line for line in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines() if line][90:92]
mode = sys.argv[4]
expected_ids = ["generator-regeneration-nondeterministic", "generator-check-mutates"]
if declared != expected_ids:
    raise SystemExit("generator invariant IDs do not equal declared registry slice")
if mode == "register":
    print("reachable production-generator invariant definitions=2; execution deferred until subject exists")
    raise SystemExit(0)
generator = root / "scripts/generate-skill-surfaces.py"

def copy_root(parent, name):
    target = parent / name
    shutil.copytree(root, target, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return target

def run(target, check=False):
    command = [sys.executable, str(generator), "--project-root", str(target)]
    if check:
        command.append("--check")
    return subprocess.run(command, text=True, capture_output=True, timeout=30, check=False)

def snapshot(target, include_mtime=False):
    rows = []
    for path in sorted((target / "template/.claude/skills").rglob("*")):
        rel = path.relative_to(target).as_posix()
        info = path.lstat()
        kind = "symlink" if path.is_symlink() else "dir" if path.is_dir() else "file"
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if kind == "file" else ""
        row = [rel, kind, stat.S_IMODE(info.st_mode), digest]
        if include_mtime:
            row.append(info.st_mtime_ns)
        rows.append(row)
    return rows

executed = []
with tempfile.TemporaryDirectory(prefix="jv-portability-generator.") as temp:
    temp_root = Path(temp)
    deterministic = copy_root(temp_root, "deterministic")
    first = run(deterministic)
    snap1 = snapshot(deterministic)
    second = run(deterministic)
    snap2 = snapshot(deterministic)
    third = run(deterministic)
    snap3 = snapshot(deterministic)
    if any(result.returncode != 0 for result in (first, second, third)) or not (snap1 == snap2 == snap3):
        raise SystemExit("generator-regeneration-nondeterministic: production generator changed repeated snapshots")
    executed.append({
        "id": expected_ids[0], "family": "generator-invariants", "subject": str(generator),
        "control_exit": first.returncode, "case_exit": third.returncode,
        "expectation": "three-equal-entry-byte-type-permission-snapshots",
    })

    check_target = copy_root(temp_root, "check-no-write")
    normalize = run(check_target)
    if normalize.returncode != 0:
        raise SystemExit("generator-check-mutates: normalization control failed")
    projection = check_target / "template/.claude/skills/frontend-design/SKILL.md"
    projection.write_bytes(projection.read_bytes() + b"drift")
    before = snapshot(check_target, include_mtime=True)
    negative = run(check_target, check=True)
    after = snapshot(check_target, include_mtime=True)
    output = negative.stdout + negative.stderr
    if negative.returncode == 0 or before != after or not any(word in output.lower() for word in ("drift", "byte", "hash", "projection")):
        raise SystemExit("generator-check-mutates: production --check did not fail read-only by named projection reason")
    clean_target = copy_root(temp_root, "check-control")
    clean = run(clean_target, check=True)
    if clean.returncode != 0:
        raise SystemExit("generator-check-mutates: same-shape clean --check failed")
    executed.append({
        "id": expected_ids[1], "family": "generator-invariants", "subject": str(generator),
        "control_exit": clean.returncode, "case_exit": negative.returncode,
        "expectation": "named-nonzero-and-zero-filesystem-writes",
        "diagnostic_pattern": "drift|byte|hash|projection",
    })

receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
receipt["cases"].extend(executed)
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("actual generator invariant executions=2")
PY
  then
    pass "$cell production-generator invariant definitions match registry; execute when present"
  else
    fail "$cell" "GENERATOR_INVARIANTS:production subject failure"
  fi
}

check_copier_subject_contract() {
  local cell="P07" rel="scripts/ci/copier-update-check.sh"
  local generator="scripts/generate-skill-surfaces.py"
  local checker="scripts/ci/check-skill-routes.py"
  local subject_mode="execute"
  if [[ ! -x "$ROOT/$rel" || ! -f "$ROOT/$generator" || ! -f "$ROOT/$checker" ]]; then
    fail "$cell" "MISSING_BEHAVIOR:real Copier subject bundle ($rel + $generator + $checker)"
    subject_mode="register"
  fi

  if python3 - "$ROOT" "$RUN_TMP" "$EXECUTION_RECEIPT" "$CASE_REGISTRY" "$subject_mode" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
run_root = Path(sys.argv[2]) / "copier-real-subject"
receipt_path = Path(sys.argv[3])
registry_path = Path(sys.argv[4])
mode = sys.argv[5]
run_root.mkdir()
subject = root / "scripts/ci/copier-update-check.sh"
matrix = root / "scripts/ci/generate-matrix-check.sh"

ids = [
    "copier-missing", "copier-wrong-version", "copier-clean-overwrite",
    "copier-conflict-markers", "copier-reject-artifact", "copier-unclassified-outcome",
    "copier-canonical-conflict", "copier-unexpected-artifact", "copier-project-owned-drift",
    "copier-skip-state-drift", "copier-partial-marker-set", "copier-answer-solo-go",
    "copier-answer-cluster-supabase", "copier-answer-cluster-postgres", "copier-answer-cluster-rust",
]
registered = {
    row["id"] for row in json.loads(registry_path.read_text(encoding="utf-8"))["cases"]
    if row["family"] == "copier-update-matrix"
}
if set(ids) != registered or len(ids) != 15:
    raise SystemExit("Copier subject definitions do not equal the registered 15-case family")
if mode == "register":
    print("reachable Copier/matrix subject definitions=15; execution deferred until subjects exist")
    raise SystemExit(0)

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def make_target(name: str) -> Path:
    target = run_root / name
    shutil.copytree(root / "template", target, symlinks=True)
    canonical = target / ".agents/skills/copier-conflict-fixture/SKILL.md"
    generated = target / ".claude/skills/copier-conflict-fixture/SKILL.md"
    project = target / ".agents/skills/project-owned/SKILL.md"
    state = target / "context/WORKING.md"
    for path in (canonical, generated, project, state):
        path.parent.mkdir(parents=True, exist_ok=True)
    v1 = "---\nname: copier-conflict-fixture\ndescription: v1\n---\nframework v1\n"
    canonical.write_text(v1, encoding="utf-8")
    generated.write_text(v1, encoding="utf-8")
    project.write_text("project-owned\n", encoding="utf-8")
    state.write_text("skip-state\n", encoding="utf-8")
    return target

def write_fake(bin_dir: Path, version: str = "9.17.1") -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "copier"
    fake.write_text(
        f'''#!/usr/bin/env python3
import os
from pathlib import Path
import sys

if "--version" in sys.argv:
    print("copier {version}")
    raise SystemExit(0)

target = Path(os.environ["PORTABILITY_FAKE_TARGET"])
outcome = os.environ.get("PORTABILITY_FAKE_OUTCOME", "clean")
canonical = target / ".agents/skills/copier-conflict-fixture/SKILL.md"
generated = target / ".claude/skills/copier-conflict-fixture/SKILL.md"
reject = generated.with_name("SKILL.md.rej")
v2 = "---\\nname: copier-conflict-fixture\\ndescription: v2\\n---\\nframework v2\\n"
canonical.write_text(v2, encoding="utf-8")
if outcome == "clean":
    generated.write_text(v2, encoding="utf-8")
elif outcome == "markers":
    generated.write_text("<<<<<<< project\\nlocal\\n=======\\nframework v2\\n>>>>>>> template\\n", encoding="utf-8")
elif outcome == "reject":
    generated.write_text("local\\n", encoding="utf-8")
    reject.write_text("rejected v2\\n", encoding="utf-8")
elif outcome == "unclassified":
    generated.write_text("neither v2 nor conflict\\n", encoding="utf-8")
elif outcome == "canonical-conflict":
    canonical.write_text("<<<<<<< project\\ncanonical conflict\\n=======\\nv2\\n>>>>>>> template\\n", encoding="utf-8")
elif outcome == "unexpected-artifact":
    generated.write_text(v2, encoding="utf-8")
    (target / "unexpected.orig").write_text("unexpected\\n", encoding="utf-8")
elif outcome == "project-drift":
    generated.write_text(v2, encoding="utf-8")
    (target / ".agents/skills/project-owned/SKILL.md").write_text("changed\\n", encoding="utf-8")
elif outcome == "skip-drift":
    generated.write_text(v2, encoding="utf-8")
    (target / "context/WORKING.md").write_text("changed\\n", encoding="utf-8")
elif outcome == "partial-markers":
    generated.write_text("<<<<<<< project\\npartial\\n", encoding="utf-8")
else:
    raise SystemExit(97)
raise SystemExit(0)
''',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return fake

correct_bin = run_root / "bin-correct"
wrong_bin = run_root / "bin-wrong"
write_fake(correct_bin)
write_fake(wrong_bin, version="9.16.0")

def tool_path_without_copier() -> str:
    target = run_root / "bin-no-copier"
    target.mkdir()
    for name in ("bash", "env", "python3", "find", "grep", "sed", "awk", "sha256sum", "wc", "tr", "sort", "diff", "git", "rm", "mkdir", "cp", "chmod"):
        source = shutil.which(name)
        if source:
            (target / name).symlink_to(source)
    return str(target)

no_copier_path = tool_path_without_copier()

def invoke(target: Path, outcome: str, bin_dir: Path | None = correct_bin):
    env = os.environ.copy()
    env["PORTABILITY_FAKE_TARGET"] = str(target)
    env["PORTABILITY_FAKE_OUTCOME"] = outcome
    env["PATH"] = no_copier_path if bin_dir is None else f"{bin_dir}:{os.defpath}"
    return subprocess.run(
        [str(subject), "--target", str(target)], cwd=root, env=env,
        text=True, capture_output=True, timeout=60, check=False,
    )

executed = []
negative_shapes = {
    "copier-missing": ("clean", None, r"copier not found"),
    "copier-wrong-version": ("clean", wrong_bin, r"9\.17\.1|version"),
    "copier-unclassified-outcome": ("unclassified", correct_bin, r"unexpected Copier outcome"),
    "copier-canonical-conflict": ("canonical-conflict", correct_bin, r"canonical|ownership|unexpected Copier outcome"),
    "copier-unexpected-artifact": ("unexpected-artifact", correct_bin, r"unexpected|artifact|\.orig"),
    "copier-project-owned-drift": ("project-drift", correct_bin, r"project-owned|hash|drift"),
    "copier-skip-state-drift": ("skip-drift", correct_bin, r"skip|state|hash|drift"),
    "copier-partial-marker-set": ("partial-markers", correct_bin, r"partial|marker|unexpected Copier outcome"),
}
allowed_shapes = {
    "copier-clean-overwrite": "clean",
    "copier-conflict-markers": "markers",
    "copier-reject-artifact": "reject",
}

for case_id, outcome in allowed_shapes.items():
    target = make_target(case_id)
    result = invoke(target, outcome)
    if result.returncode != 0:
        raise SystemExit(f"{case_id}: production Copier subject rejected allowed outcome: {result.stdout + result.stderr}")
    executed.append({
        "id": case_id, "family": "copier-update-matrix", "subject": str(subject),
        "control_exit": 0, "case_exit": result.returncode,
        "expectation": f"allowed-{outcome}-classified-and-remediated",
    })

for case_id, (outcome, bin_dir, diagnostic) in negative_shapes.items():
    control = invoke(make_target(f"{case_id}-control"), "clean")
    negative = invoke(make_target(f"{case_id}-negative"), outcome, bin_dir)
    output = negative.stdout + negative.stderr
    if control.returncode != 0:
        raise SystemExit(f"{case_id}: production Copier same-shape control failed")
    import re
    if negative.returncode == 0 or not re.search(diagnostic, output, re.IGNORECASE):
        raise SystemExit(f"{case_id}: production Copier negative lacked /{diagnostic}/: {output!r}")
    executed.append({
        "id": case_id, "family": "copier-update-matrix", "subject": str(subject),
        "control_exit": control.returncode, "case_exit": negative.returncode,
        "expectation": "named-nonzero", "diagnostic_pattern": diagnostic,
    })

copier_bin = shutil.which("copier")
if copier_bin is None:
    raise SystemExit("matrix subject requires CI-installed copier==9.17.1")
version = subprocess.run([copier_bin, "--version"], text=True, capture_output=True, check=False)
if version.returncode != 0 or "9.17.1" not in version.stdout + version.stderr:
    raise SystemExit(f"matrix subject observed wrong Copier: {version.stdout + version.stderr}")
matrix_run = subprocess.run([str(matrix), copier_bin], cwd=root, text=True, capture_output=True, timeout=300, check=False)
matrix_output = matrix_run.stdout + matrix_run.stderr
matrix_cases = {
    "copier-answer-solo-go": "solo-greenfield-none",
    "copier-answer-cluster-supabase": "cluster-brownfield-supabase",
    "copier-answer-cluster-postgres": "cluster-brownfield-postgres",
    "copier-answer-cluster-rust": "cluster-greenfield-none",
}
if matrix_run.returncode != 0:
    raise SystemExit(f"production four-set matrix failed: {matrix_output[-2000:]}")
for case_id, set_name in matrix_cases.items():
    if f"[PASS] {set_name}" not in matrix_output:
        raise SystemExit(f"{case_id}: production matrix did not prove named answer set {set_name}")
    executed.append({
        "id": case_id, "family": "copier-update-matrix", "subject": str(matrix),
        "control_exit": matrix_run.returncode, "case_exit": matrix_run.returncode,
        "expectation": f"matrix-set-pass:{set_name}",
    })

if {item["id"] for item in executed} != set(ids):
    raise SystemExit("Copier actual execution IDs do not equal the declared 15-case family")
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
receipt["cases"].extend(executed)
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("actual Copier/matrix subject executions=15")
PY
  then
    pass "$cell Copier/matrix definitions match registry; real subjects execute when present"
  else
    fail "$cell" "COPIER_SUBJECT_MATRIX:real-subject failure"
  fi
}


check_runtime_subject_contract() {
  local cell="P08" runner="scripts/ci/runtime-skill-receipt.sh"
  local schema="scripts/ci/fixtures/runtime-skill-receipt.schema.json"
  local subject_mode="execute"
  if [[ ! -x "$ROOT/$runner" || ! -f "$ROOT/$schema" ]]; then
    fail "$cell" "MISSING_BEHAVIOR:real runtime fixture validator ($runner + $schema)"
    subject_mode="register"
  fi

  if python3 - "$ROOT" "$RUN_TMP" "$EXECUTION_RECEIPT" "$CASE_REGISTRY" "$subject_mode" <<'PY'
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
run_root = Path(sys.argv[2]) / "runtime-real-subject"
receipt_path = Path(sys.argv[3])
registry_path = Path(sys.argv[4])
mode = sys.argv[5]
run_root.mkdir()
subject = root / "scripts/ci/runtime-skill-receipt.sh"

ids = [
    "runtime-missing-cli", "runtime-wrong-cli-version", "runtime-marker-drift",
    "runtime-no-project-control", "runtime-missing-node", "runtime-missing-codex-cli",
    "runtime-missing-claude-cli", "runtime-wrong-node-version", "runtime-wrong-codex-version",
    "runtime-wrong-claude-version", "codex-no-project-control-present", "claude-marker-drift",
    "claude-mixed-evidence-tuple", "claude-missing-artifact", "claude-empty-required-artifact",
    "claude-missing-stderr", "claude-nonzero-stderr", "claude-transcript-cardinality",
    "claude-artifact-wrong-class", "claude-receipt-schema-invalid",
    "claude-expected-auth-missing", "claude-expected-auth-control-corrupt",
    "claude-unexpected-auth-success", "claude-unexpected-exit", "claude-timeout-or-signal",
    "claude-session-or-order-mismatch", "claude-invocation-body-truncated",
    "claude-invocation-body-appended", "codex-native-record-missing",
    "codex-native-record-duplicate", "codex-path-in-original-prompt",
    "codex-client-supplied-skill-item", "codex-body-truncated-or-appended",
    "codex-prefix-only-match", "codex-fallback-without-reruling",
]
registered = {
    row["id"] for row in json.loads(registry_path.read_text(encoding="utf-8"))["cases"]
    if row["family"] == "runtime-receipt"
}
if set(ids) != registered or len(ids) != 35:
    raise SystemExit("runtime subject definitions do not equal the registered 35-case family")
if mode == "register":
    print("reachable runtime --validate-fixture definitions=35; execution deferred until subject exists")
    raise SystemExit(0)

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def receipt_file(target: Path) -> Path:
    return target / "claude-receipt.json"

def load_receipt(target: Path):
    return json.loads(receipt_file(target).read_text(encoding="utf-8"))

def save_receipt(target: Path, value) -> None:
    receipt_file(target).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

def edit_receipt(target: Path, edit) -> None:
    value = load_receipt(target)
    edit(value)
    save_receipt(target, value)

def refresh(target: Path, artifact: str) -> None:
    value = load_receipt(target)
    paths = {
        "debug": target / "claude-debug.log",
        "stdout": target / "claude-stdout.txt",
        "stderr": target / "claude-stderr.txt",
        "transcript": target / "projects/cwd-key/session.jsonl",
    }
    path = paths[artifact]
    value[f"{artifact}_sha256"] = digest(path)
    value[f"{artifact}_bytes"] = path.stat().st_size
    save_receipt(target, value)

def write_base(target: Path) -> None:
    transcript_dir = target / "projects/cwd-key"
    transcript_dir.mkdir(parents=True)
    debug = target / "claude-debug.log"
    stdout = target / "claude-stdout.txt"
    stderr = target / "claude-stderr.txt"
    transcript = transcript_dir / "session.jsonl"
    debug.write_text(
        "Remote settings: Fetch failed (http_401) and no cached settings\n"
        "Loading skills from: managed=/etc/claude-code/.claude/skills user=/scratch/skills project=/project/.claude/skills\n"
        "Total plugin skills loaded: 0 (0 duplicate/user-owned entries skipped)\n"
        "Loaded 1 unique skills (1 unconditional, 0 conditional, managed: 0, user: 0, project: 1, additional: 0, legacy commands: 0)\n"
        "Sending 12 skills via attachment (initial)\n",
        encoding="utf-8",
    )
    stdout.write_bytes("Invalid API key · Fix external API key\n".encode())
    stderr.write_bytes(b"")
    session = "8e535220-a4ce-47f3-a825-5f2c39b48212"
    listing = {"type": "attachment", "attachment": {"type": "skill_listing", "names": ["frontend-design"]}, "sessionId": session}
    terminal = {"type": "assistant", "error": "authentication_failed", "isApiErrorMessage": True, "apiErrorStatus": 401, "sessionId": session}
    transcript.write_text(json.dumps(listing) + "\n" + json.dumps(terminal) + "\n", encoding="utf-8")
    body = "---\nname: frontend-design\ndescription: synthetic\n---\nbody\n"
    receipt = {
        "schema_version": 1,
        "node_version": "v22.23.2",
        "codex_version": "codex-cli 0.145.0",
        "claude_version": "2.1.232 (Claude Code)",
        "status": 1,
        "timeout_seconds": 30,
        "kill_after_seconds": 5,
        "session_id": session,
        "codex_no_project": {"target_count": 0},
        "claude_no_project": {"target_count": 0},
        "claude_invocation": {"marker": "Base directory for this skill:", "source_body": body, "loaded_body": body},
        "codex_native": {
            "raw_prompt": "$frontend-design invoke exactly",
            "source_body": body,
            "skill_records": [{"source": "runtime", "name": "frontend-design", "path": "/project/.agents/skills/frontend-design/SKILL.md", "body": body}],
            "fallback_used": False,
            "fallback_reruled": False,
        },
    }
    for name, path in (("debug", debug), ("stdout", stdout), ("stderr", stderr), ("transcript", transcript)):
        receipt[f"{name}_sha256"] = digest(path)
        receipt[f"{name}_bytes"] = path.stat().st_size
    save_receipt(target, receipt)

def marker_drift(target: Path) -> None:
    path = target / "claude-debug.log"
    path.write_text(path.read_text(encoding="utf-8").replace("Loading skills from:", "Loading skills changed:"), encoding="utf-8")
    refresh(target, "debug")

def no_project_present(target: Path, runtime: str) -> None:
    edit_receipt(target, lambda v: v[f"{runtime}_no_project"].__setitem__("target_count", 1))

def missing_auth(target: Path) -> None:
    (target / "claude-stdout.txt").write_text("missing auth terminal\n", encoding="utf-8")
    refresh(target, "stdout")

def nonzero_stderr(target: Path) -> None:
    (target / "claude-stderr.txt").write_bytes(b"unexpected stderr\n")
    refresh(target, "stderr")

def mutate_transcript(target: Path, edit) -> None:
    path = target / "projects/cwd-key/session.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    edit(rows)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    refresh(target, "transcript")

def wrong_class(target: Path) -> None:
    path = target / "claude-stdout.txt"
    content = path.read_bytes()
    path.unlink()
    backing = target / "stdout-backing.txt"
    backing.write_bytes(content)
    path.symlink_to(backing.name)

mutations = {
    "runtime-missing-cli": lambda t: edit_receipt(t, lambda v: (v.pop("codex_version"), v.pop("claude_version"))),
    "runtime-wrong-cli-version": lambda t: edit_receipt(t, lambda v: v.__setitem__("codex_version", "codex-cli 0.144.0")),
    "runtime-marker-drift": marker_drift,
    "runtime-no-project-control": lambda t: no_project_present(t, "claude"),
    "runtime-missing-node": lambda t: edit_receipt(t, lambda v: v.pop("node_version")),
    "runtime-missing-codex-cli": lambda t: edit_receipt(t, lambda v: v.pop("codex_version")),
    "runtime-missing-claude-cli": lambda t: edit_receipt(t, lambda v: v.pop("claude_version")),
    "runtime-wrong-node-version": lambda t: edit_receipt(t, lambda v: v.__setitem__("node_version", "v22.16.0")),
    "runtime-wrong-codex-version": lambda t: edit_receipt(t, lambda v: v.__setitem__("codex_version", "codex-cli 0.144.0")),
    "runtime-wrong-claude-version": lambda t: edit_receipt(t, lambda v: v.__setitem__("claude_version", "2.1.231 (Claude Code)")),
    "codex-no-project-control-present": lambda t: no_project_present(t, "codex"),
    "claude-marker-drift": marker_drift,
    "claude-mixed-evidence-tuple": lambda t: edit_receipt(t, lambda v: v.__setitem__("debug_bytes", v["debug_bytes"] + 1)),
    "claude-missing-artifact": lambda t: (t / "claude-debug.log").unlink(),
    "claude-empty-required-artifact": lambda t: (t / "claude-debug.log").write_bytes(b""),
    "claude-missing-stderr": lambda t: (t / "claude-stderr.txt").unlink(),
    "claude-nonzero-stderr": nonzero_stderr,
    "claude-transcript-cardinality": lambda t: shutil.copyfile(t / "projects/cwd-key/session.jsonl", t / "projects/cwd-key/duplicate.jsonl"),
    "claude-artifact-wrong-class": wrong_class,
    "claude-receipt-schema-invalid": lambda t: edit_receipt(t, lambda v: v.pop("schema_version")),
    "claude-expected-auth-missing": missing_auth,
    "claude-expected-auth-control-corrupt": lambda t: edit_receipt(t, lambda v: v.__setitem__("status", 2)),
    "claude-unexpected-auth-success": lambda t: edit_receipt(t, lambda v: v.__setitem__("status", 0)),
    "claude-unexpected-exit": lambda t: edit_receipt(t, lambda v: v.__setitem__("status", 126)),
    "claude-timeout-or-signal": lambda t: edit_receipt(t, lambda v: v.__setitem__("status", 124)),
    "claude-session-or-order-mismatch": lambda t: mutate_transcript(t, lambda rows: rows.reverse()),
    "claude-invocation-body-truncated": lambda t: edit_receipt(t, lambda v: v["claude_invocation"].__setitem__("loaded_body", "body")),
    "claude-invocation-body-appended": lambda t: edit_receipt(t, lambda v: v["claude_invocation"].__setitem__("loaded_body", v["claude_invocation"]["source_body"] + "extra")),
    "codex-native-record-missing": lambda t: edit_receipt(t, lambda v: v["codex_native"].__setitem__("skill_records", [])),
    "codex-native-record-duplicate": lambda t: edit_receipt(t, lambda v: v["codex_native"].__setitem__("skill_records", v["codex_native"]["skill_records"] * 2)),
    "codex-path-in-original-prompt": lambda t: edit_receipt(t, lambda v: v["codex_native"].__setitem__("raw_prompt", "$frontend-design /project/.agents/skills/frontend-design/SKILL.md")),
    "codex-client-supplied-skill-item": lambda t: edit_receipt(t, lambda v: v["codex_native"]["skill_records"][0].__setitem__("source", "client")),
    "codex-body-truncated-or-appended": lambda t: edit_receipt(t, lambda v: v["codex_native"]["skill_records"][0].__setitem__("body", "truncated")),
    "codex-prefix-only-match": lambda t: edit_receipt(t, lambda v: v["codex_native"]["skill_records"][0].__setitem__("body", v["codex_native"]["source_body"][:10])),
    "codex-fallback-without-reruling": lambda t: edit_receipt(t, lambda v: (v["codex_native"].__setitem__("fallback_used", True), v["codex_native"].__setitem__("fallback_reruled", False))),
}

diagnostics = {
    case_id: (
        r"version|cli|node" if "version" in case_id or "missing-cli" in case_id or "missing-node" in case_id
        else r"marker|debug" if "marker" in case_id
        else r"no-project|target|count" if "no-project" in case_id
        else r"artifact|missing|empty|stderr|cardinality|class" if any(word in case_id for word in ("artifact", "stderr", "cardinality"))
        else r"auth|status|exit|timeout|signal" if any(word in case_id for word in ("auth", "exit", "timeout"))
        else r"session|order" if "session-or-order" in case_id
        else r"schema" if "schema" in case_id
        else r"body|record|prompt|client|prefix|fallback|native|invocation"
    ) for case_id in ids
}

def invoke(target: Path):
    return subprocess.run(
        [str(subject), "--validate-fixture", str(target)], cwd=root,
        text=True, capture_output=True, timeout=20, check=False,
    )

executed = []
for case_id in ids:
    control = run_root / f"control-{case_id}"
    negative = run_root / f"negative-{case_id}"
    write_base(control)
    shutil.copytree(control, negative, symlinks=True)
    control_run = invoke(control)
    mutations[case_id](negative)
    negative_run = invoke(negative)
    output = negative_run.stdout + negative_run.stderr
    diagnostic = diagnostics[case_id]
    if control_run.returncode != 0:
        raise SystemExit(f"{case_id}: production runtime validator control failed: {control_run.stdout + control_run.stderr}")
    if negative_run.returncode == 0 or not re.search(diagnostic, output, re.IGNORECASE):
        raise SystemExit(f"{case_id}: production runtime validator lacked /{diagnostic}/: {output!r}")
    executed.append({
        "id": case_id, "family": "runtime-receipt", "subject": str(subject),
        "control_exit": control_run.returncode, "case_exit": negative_run.returncode,
        "expectation": "named-nonzero", "diagnostic_pattern": diagnostic,
    })

receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
receipt["cases"].extend(executed)
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("actual runtime fixture-validator subject executions=35")
PY
  then
    pass "$cell runtime fixture definitions match registry; real subject executes when present"
  else
    fail "$cell" "RUNTIME_SUBJECT_MATRIX:real-subject failure"
  fi
}


check_ci_and_matrix_contract() {
  local cell="P09"
  require_contains "$cell" ".github/workflows/ci.yml" 'node-version: "22.23.2"' || true
  require_contains "$cell" ".github/workflows/ci.yml" '@openai/codex@0.145.0' || true
  require_contains "$cell" ".github/workflows/ci.yml" '@anthropic-ai/claude-code@2.1.232' || true
  require_contains "$cell" ".github/workflows/ci.yml" 'copier==9.17.1' || true
  require_contains "$cell" ".github/workflows/ci.yml" 'test-skill-portability.sh' || true
  require_contains "$cell" ".github/workflows/ci.yml" 'runtime-skill-receipt.sh' || true
  require_contains "$cell" "scripts/ci/generate-matrix-check.sh" 'frontend-design.expected.json' || true
  require_contains "$cell" "scripts/ci/generate-matrix-check.sh" '.agents/skills/frontend-design' || true
  require_contains "$cell" "scripts/ci/generate-matrix-check.sh" '.claude/skills/frontend-design' || true
}

check_docs_and_scope_contract() {
  local cell="P10"
  local -a docs=(
    CLAUDE.md
    README.md
    docs/CONTEXT_CONTRACT.md
    docs/CUSTOMIZATION.md
    docs/GETTING_STARTED.md
    docs/MIGRATION.md
    docs/ROADMAP.md
  )
  local doc
  for doc in "${docs[@]}"; do
    require_contains "$cell" "$doc" "frontend-design" || true
  done
  if git -C "$ROOT" diff --name-only "dd7d2b4b500a402e52769b7c640fb791549040a5" -- \
      | grep -Eq '(^|/)(AGENTS\.md|\.codex/skills|customer-portal|R2a)(/|$)'; then
    fail "$cell" "SCOPE_ESCAPE:forbidden implementation path"
  else
    pass "$cell diff remains outside forbidden scope"
  fi
}

check_rollback_scope_subject_contract() {
  local cell="P11" gate="scripts/ci/test-skill-portability.sh"

  if python3 - "$ROOT" "$RUN_TMP" "$EXECUTION_RECEIPT" "$CASE_REGISTRY" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
run_root = Path(sys.argv[2]) / "scope-real-subject"
receipt_path = Path(sys.argv[3])
registry_path = Path(sys.argv[4])
run_root.mkdir()
subject = root / "scripts/ci/test-skill-portability.sh"
allowed = [
    "template/.agents/skills/frontend-design/SKILL.md",
    "template/.claude/skills/frontend-design/SKILL.md",
    "scripts/generate-skill-surfaces.py",
    "scripts/ci/check-skill-routes.py",
    "scripts/ci/runtime-skill-receipt.sh",
    "scripts/ci/fixtures/frontend-design.expected.json",
    ".github/workflows/ci.yml",
    "docs/CUSTOMIZATION.md",
]
cases = {
    "scope-forbidden-path": "outside-slice.txt",
    "scope-forbidden-agents": "template/AGENTS.md.jinja",
    "scope-forbidden-consumer-generator": "template/scripts/generate-skill-surfaces.py",
    "scope-forbidden-customer-portal": "customer-portal/runtime/frontend-design/SKILL.md",
    "scope-forbidden-runtime-home": "/home/runner/.codex/skills/frontend-design/SKILL.md",
}
registered = {
    row["id"] for row in json.loads(registry_path.read_text(encoding="utf-8"))["cases"]
    if row["family"] == "rollback-scope-gate"
}
defined = set(cases) | {"rollback-partial-removal", "rollback-normalized-result-mismatch"}
if defined != registered or len(defined) != 7:
    raise SystemExit("rollback/scope production-subject definitions do not equal the registered seven-case family")

def invoke(path):
    return subprocess.run([str(subject), "--validate-scope", str(path)], text=True, capture_output=True, timeout=10, check=False)

executed = []
for case_id, forbidden in cases.items():
    control_path = run_root / f"{case_id}.control.json"
    negative_path = run_root / f"{case_id}.negative.json"
    control_path.write_text(json.dumps(allowed) + "\n", encoding="utf-8")
    negative_path.write_text(json.dumps(allowed + [forbidden]) + "\n", encoding="utf-8")
    control = invoke(control_path)
    negative = invoke(negative_path)
    if control.returncode != 0:
        raise SystemExit(f"{case_id}: production scope-gate control failed: {control.stdout + control.stderr}")
    if negative.returncode == 0 or f"SCOPE_ESCAPE:{forbidden}" not in negative.stderr:
        raise SystemExit(f"{case_id}: production scope gate did not name forbidden path: {negative.stdout + negative.stderr}")
    executed.append({
        "id": case_id, "family": "rollback-scope-gate", "subject": f"{subject} --validate-scope",
        "control_exit": control.returncode, "case_exit": negative.returncode,
        "expectation": "named-nonzero", "diagnostic_pattern": f"SCOPE_ESCAPE:{forbidden}",
    })

receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
receipt["cases"].extend(executed)
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("actual production scope-gate executions=5")
PY
  then
    pass "$cell production scope gate control/escape matrix"
  else
    fail "$cell" "HARNESS_BROKEN:production scope-gate invocation"
  fi

  local checker="scripts/ci/check-skill-routes.py"
  local matrix="scripts/ci/generate-matrix-check.sh"
  if [[ ! -f "$ROOT/$checker" || ! -x "$ROOT/$matrix" || ! -d "$ROOT/template/.agents/skills/frontend-design" ]]; then
    fail "$cell" "MISSING_BEHAVIOR:real rollback bundle ($checker + $matrix + completed slice)"
    return
  fi
  if ! command -v copier >/dev/null 2>&1 || ! copier --version 2>&1 | grep -Fq '9.17.1'; then
    fail "$cell" "MISSING_BEHAVIOR:rollback matrix requires copier==9.17.1"
    return
  fi

  if python3 - "$ROOT" "$RUN_TMP" "$EXECUTION_RECEIPT" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
run_root = Path(sys.argv[2]) / "rollback-real-subject"
receipt_path = Path(sys.argv[3])
run_root.mkdir()
checker = root / "scripts/ci/check-skill-routes.py"
gate = root / "scripts/ci/test-skill-portability.sh"
base = "dd7d2b4b500a402e52769b7c640fb791549040a5"

def run(command, cwd=None, timeout=300, input_bytes=None):
    return subprocess.run(command, cwd=cwd, input=input_bytes, capture_output=True, timeout=timeout, check=False)

partial = run_root / "partial-removal"
shutil.copytree(root, partial, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
shutil.rmtree(partial / "template/.claude/skills/frontend-design")
control = run([sys.executable, str(checker), "--project-root", str(root)])
negative = run([sys.executable, str(checker), "--project-root", str(partial)])
partial_output = (negative.stdout + negative.stderr).decode(errors="replace")
if control.returncode != 0:
    raise SystemExit("rollback-partial-removal: production checker control failed")
if negative.returncode == 0 or not re.search(r"projection|missing|frontend-design", partial_output, re.IGNORECASE):
    raise SystemExit(f"rollback-partial-removal: production checker did not reject partial slice: {partial_output!r}")

repo = run_root / "repo"
cloned = run(["git", "clone", "--no-local", "--quiet", str(root), str(repo)], timeout=120)
if cloned.returncode != 0:
    raise SystemExit(f"rollback clone failed: {cloned.stderr.decode(errors='replace')}")
for key, value in (("user.name", "Portability Rollback"), ("user.email", "rollback@example.invalid")):
    configured = run(["git", "config", key, value], cwd=repo)
    if configured.returncode != 0:
        raise SystemExit("rollback git identity setup failed")
checkout = run(["git", "checkout", "--quiet", base], cwd=repo)
if checkout.returncode != 0:
    raise SystemExit("rollback base checkout failed")

copier = shutil.which("copier")
def matrix_run():
    return run([str(repo / "scripts/ci/generate-matrix-check.sh"), copier], cwd=repo, timeout=300)

before = matrix_run()
patch = run(["git", "-C", str(root), "diff", "--binary", "--full-index", f"{base}..HEAD"])
if patch.returncode != 0 or not patch.stdout:
    raise SystemExit("rollback slice patch extraction failed")
applied = run(["git", "apply", "--index", "--binary", "-"], cwd=repo, input_bytes=patch.stdout)
if applied.returncode != 0:
    raise SystemExit(f"rollback slice apply failed: {applied.stderr.decode(errors='replace')}")
committed = run(["git", "commit", "--quiet", "-m", "synthetic one-unit frontend-design slice"], cwd=repo)
if committed.returncode != 0:
    raise SystemExit("rollback synthetic slice commit failed")
slice_commit = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.decode().strip()
parent = run(["git", "rev-parse", "HEAD^"], cwd=repo).stdout.decode().strip()
if parent != base:
    raise SystemExit(f"rollback synthetic slice parent mismatch: {parent}")
slice_matrix = matrix_run()
reverted = run(["git", "revert", "--no-edit", slice_commit], cwd=repo, timeout=120)
if reverted.returncode != 0:
    raise SystemExit(f"real one-unit git revert failed: {reverted.stderr.decode(errors='replace')}")
after = matrix_run()
tree_delta = run(["git", "diff", "--exit-code", base, "HEAD"], cwd=repo)
if tree_delta.returncode != 0:
    raise SystemExit("real one-unit revert did not restore the exact base tree")
if any(result.returncode != 0 for result in (before, slice_matrix, after)):
    raise SystemExit("pre-slice, slice, or reverted production matrix was nonzero")

def evidence(result):
    text = (result.stdout + result.stderr).decode(errors="replace")
    sets = sorted(re.findall(r"^\[PASS\] ([^\n]+)$", text, re.MULTILINE))
    summary = re.search(r"matrix sets: (\d+), failed: (\d+)", text)
    if not summary:
        raise SystemExit("matrix normalized summary missing")
    normalized = sorted(line for line in text.splitlines() if line.startswith("[PASS] ") or line.startswith("matrix sets:"))
    return {"matrix_sets": sets, "matrix_pass_count": int(summary.group(1)) - int(summary.group(2)), "matrix_exit": result.returncode, "normalized_lines": normalized}

before_path = run_root / "before.json"
after_path = run_root / "after.json"
negative_path = run_root / "negative.json"
before_value = evidence(before)
after_value = evidence(after)
before_path.write_text(json.dumps(before_value, sort_keys=True) + "\n", encoding="utf-8")
after_path.write_text(json.dumps(after_value, sort_keys=True) + "\n", encoding="utf-8")
negative_value = dict(after_value)
negative_value["matrix_pass_count"] += 1
negative_path.write_text(json.dumps(negative_value, sort_keys=True) + "\n", encoding="utf-8")
compare_control = run([str(gate), "--compare-rollback-evidence", str(before_path), str(after_path)])
compare_negative = run([str(gate), "--compare-rollback-evidence", str(before_path), str(negative_path)])
negative_output = (compare_negative.stdout + compare_negative.stderr).decode(errors="replace")
if compare_control.returncode != 0:
    raise SystemExit("production rollback evidence gate rejected real revert control")
if compare_negative.returncode == 0 or "ROLLBACK_NORMALIZED_MISMATCH" not in negative_output:
    raise SystemExit("production rollback evidence gate accepted normalized mismatch")

executed = [
    {
        "id": "rollback-partial-removal", "family": "rollback-scope-gate", "subject": str(checker),
        "control_exit": control.returncode, "case_exit": negative.returncode,
        "expectation": "named-nonzero", "diagnostic_pattern": "projection|missing|frontend-design",
    },
    {
        "id": "rollback-normalized-result-mismatch", "family": "rollback-scope-gate",
        "subject": f"git revert + {repo / 'scripts/ci/generate-matrix-check.sh'} + {gate} --compare-rollback-evidence",
        "control_exit": compare_control.returncode, "case_exit": compare_negative.returncode,
        "expectation": "real-one-unit-revert-equal; mutated-evidence-named-nonzero",
        "diagnostic_pattern": "ROLLBACK_NORMALIZED_MISMATCH", "git_revert_exit": reverted.returncode,
    },
]
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
receipt["cases"].extend(executed)
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("actual rollback subject executions=2 including real one-unit git revert")
PY
  then
    pass "$cell production checker/matrix/gate real one-unit rollback"
  else
    fail "$cell" "ROLLBACK_SUBJECT_MATRIX:real-subject failure"
  fi
}


check_scenario_crosswalk() {
  local cell="P12"
  local rc output
  output="$(python3 - "$EXPECTED" "$CASE_REGISTRY" "$EXECUTION_RECEIPT" <<'PY'
import json
from pathlib import Path
import sys

expected_path = Path(sys.argv[1])
registry_path = Path(sys.argv[2])
receipt_path = Path(sys.argv[3])
expected = json.loads(expected_path.read_text(encoding="utf-8"))
registry = json.loads(registry_path.read_text(encoding="utf-8"))
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
crosswalk = expected.get("scenario_crosswalk", {})
required = {
    *(f"S{number:02d}" for number in range(1, 21)),
    *(f"R2A-S{number:02d}" for number in range(1, 7)),
    "R2B-E01", "R2B-S03", "R2B-S05", "R2B-S06", "R2B-S11",
}

if set(crosswalk) != required:
    print(f"HARNESS_BROKEN:scenario keys missing={sorted(required-set(crosswalk))} extra={sorted(set(crosswalk)-required)}")
    raise SystemExit(2)
registered_rows = registry.get("cases", [])
actual_rows = receipt.get("cases", [])
registered_ids = [case.get("id") for case in registered_rows]
actual_ids = [case.get("id") for case in actual_rows]
if registry.get("schema_version") != 2 or receipt.get("schema_version") != 2:
    print("HARNESS_BROKEN:registry/receipt schema")
    raise SystemExit(2)
if len(registered_ids) != 134 or len(set(registered_ids)) != 134:
    print(f"HARNESS_BROKEN:registered IDs count={len(registered_ids)} unique={len(set(registered_ids))}")
    raise SystemExit(2)
if len(actual_ids) != len(set(actual_ids)):
    print("HARNESS_BROKEN:duplicate actual subject-bound execution IDs")
    raise SystemExit(2)
registered = {case["id"]: case for case in registered_rows}
actual = {case["id"]: case for case in actual_rows}
extra = set(actual) - set(registered)
if extra:
    print(f"HARNESS_BROKEN:unregistered actual IDs={sorted(extra)}")
    raise SystemExit(2)
required_families = {
    "static-checker-generator", "copier-update-matrix", "generator-invariants",
    "runtime-receipt", "rollback-scope-gate",
}
if {row["family"] for row in registered_rows} != required_families:
    print("HARNESS_BROKEN:registered specialized families incomplete")
    raise SystemExit(2)
allowed_subject_tokens = (
    "check-skill-routes.py", "generate-skill-surfaces.py", "copier-update-check.sh",
    "generate-matrix-check.sh", "runtime-skill-receipt.sh", "test-skill-portability.sh",
    "git revert",
)
for case_id, case in actual.items():
    if case.get("family") != registered[case_id].get("family"):
        print(f"HARNESS_BROKEN:family mismatch:{case_id}")
        raise SystemExit(2)
    subject = case.get("subject", "")
    if "oracle" in subject or not any(token in subject for token in allowed_subject_tokens):
        print(f"HARNESS_BROKEN:not a production subject:{case_id}:{subject}")
        raise SystemExit(2)
    if case.get("control_exit") != 0:
        print(f"HARNESS_BROKEN:nonzero same-shape control:{case_id}")
        raise SystemExit(2)
    if case.get("expectation") == "named-nonzero" and case.get("case_exit") == 0:
        print(f"HARNESS_BROKEN:negative case passed:{case_id}")
        raise SystemExit(2)

for scenario, case_ids in crosswalk.items():
    if not case_ids:
        print(f"HARNESS_BROKEN:{scenario}:empty case mapping")
        raise SystemExit(2)
    unregistered_edges = set(case_ids) - set(registered)
    if unregistered_edges:
        print(f"HARNESS_BROKEN:{scenario}:unregistered edges={sorted(unregistered_edges)}")
        raise SystemExit(2)

missing = set(registered) - set(actual)
print(f"SUBJECT_BOUND registered={len(registered)} actual={len(actual)} missing={len(missing)}")
print(f"SCENARIO_REGISTRY scenarios={len(crosswalk)} mapped_edges={sum(map(len, crosswalk.values()))} all_edges_registered=true")
if missing:
    print("MISSING_BEHAVIOR:subject-bound execution receipt incomplete:" + ",".join(sorted(missing)))
    raise SystemExit(3)

for scenario, case_ids in crosswalk.items():
    if not case_ids:
        print(f"HARNESS_BROKEN:{scenario}:empty case mapping")
        raise SystemExit(2)
    for case_id in case_ids:
        if case_id not in actual:
            print(f"HARNESS_BROKEN:{scenario}:mapped case absent after exact-set proof:{case_id}")
            raise SystemExit(2)
print("SCENARIO_COVERAGE=" + ",".join(sorted(crosswalk)))
print(f"SCENARIO_CROSSWALK scenarios={len(crosswalk)} mapped_edges={sum(map(len, crosswalk.values()))} actual_subject_cases={len(actual)}")
PY
)"
  rc=$?
  printf '%s\n' "$output"
  case "$rc" in
    0) pass "$cell machine crosswalk binds every scenario to exact real-subject receipt" ;;
    3) fail "$cell" "MISSING_BEHAVIOR:real-subject execution receipt incomplete" ;;
    *) fail "$cell" "HARNESS_BROKEN:scenario/registry/real-subject receipt" ;;
  esac
}

check_r2_corrections() {
  local cell="P13"
  local output rc
  output="$(python3 "$ROOT/scripts/ci/test-skill-portability-r2.py" 2>&1)"
  rc=$?
  printf '%s\n' "$output"
  if [[ "$rc" -eq 0 ]]; then
    pass "$cell all five correction subjects satisfy the independent acceptance contract"
  else
    fail "$cell" "MISSING_BEHAVIOR:R2 correction subjects"
  fi
}

check_r3_corrections() {
  local cell="P14"
  local output rc
  output="$(python3 "$ROOT/scripts/ci/test-skill-portability-r3.py" 2>&1)"
  rc=$?
  printf '%s\n' "$output"
  if [[ "$rc" -eq 0 ]]; then
    pass "$cell both durable Copier evidence corrections satisfy the frozen contract"
  else
    fail "$cell" "MISSING_BEHAVIOR:R3 durable Copier evidence"
  fi
}

printf 'frontend-design portability acceptance runner\n'
printf 'ROOT=%s\n' "$ROOT"
printf 'HEAD=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"

check_fixture_authority
check_canonical_source
check_physical_projection
check_generator
check_route_validator
check_mutation_inventory
check_copier_subject_contract
check_runtime_subject_contract
check_ci_and_matrix_contract
check_docs_and_scope_contract
check_rollback_scope_subject_contract
check_scenario_crosswalk
check_r2_corrections
check_r3_corrections

printf '\nSUMMARY pass=%d fail=%d\n' "$PASS" "$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  printf 'FAILURE_SIGNATURES_BEGIN\n'
  printf '%s\n' "${FAILURES[@]}"
  printf 'FAILURE_SIGNATURES_END\n'
  exit 1
fi
exit 0

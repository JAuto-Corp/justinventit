#!/usr/bin/env bash
# ===========================================================================
# generate-matrix-check.sh — GENERATE + HARNESS coherence gate (M2-item-1)
# ---------------------------------------------------------------------------
# For each answer set in a representative MATRIX, `copier copy` the template to
# a throwaway dir and assert the generated project is COHERENT. This is the CI
# job the M1 dogfood (docs/DOGFOOD_M1.md) recommended: it catches the class of
# build-time regression that read-only review cannot see — a gating conditional
# that silently flips false and strips machinery, or a rendered hook that comes
# out dead.
#
# The matrix deliberately exercises the two gates the M1 `copier.yml` dict-choice
# bug corrupted: `orchestration_tier` (cluster L2 machinery) and the DB adapter
# (migration guard variant) — across tiers x db adapters.
#
# ASSERTIONS, per generated project:
#   (a) NO unrendered Jinja constructs ({{ }} / {% %}), excluding the KNOWN-SAFE
#       runtime tokens the dogfood identified, and NO leaked *.jinja files.
#   (b) .claude/settings.json is valid JSON (jq).
#   (c) `bash -n` clean on every generated *.sh; every stop check/action is
#       executable (root-cause guard for the M1 "non-executable rendered
#       stop-check → dead pipeline" bug).
#   (d) hook harness green (run-all.sh exit 0) AND the real Stop runner.sh runs
#       to a clean exit (pipeline is live end-to-end).
#   (e) ANSWER-COHERENCE — the rendered project matches its answers on the two
#       dict-gated axes: cluster => heartbeat PRODUCER present (not the inert
#       stub); solo => inert stub. supabase => Supabase migration matcher+guard;
#       postgres => generic-SQL (Bash) matcher+guard; none => no migration hook.
#       (e) is what catches the SILENT form of the dict-choice bug — a project
#       that passes (a)-(d) but has its machinery quietly stripped.
#
# USAGE:
#   scripts/ci/generate-matrix-check.sh [COPIER_BIN]
#     COPIER_BIN   optional path to (or name of) the copier executable; default
#                  `copier` on PATH. Lets CI and a local venv both drive it, e.g.
#                  scripts/ci/generate-matrix-check.sh /tmp/civenv/bin/copier
#
#   JV_TEMPLATE=<dir>   override the template root (default: this repo). Point it
#                  at a NON-git working copy to test uncommitted template edits —
#                  copier always renders a git source from its committed HEAD, so
#                  dirty template changes are only seen via a non-git copy.
#
# Exit: 0 = every matrix set passed; non-zero = at least one set failed (a clear
# per-set report is printed). Temp dirs are cleaned up on exit (trap).
# ===========================================================================
set -uo pipefail

COPIER_IN="${1:-copier}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_ROOT="${JV_TEMPLATE:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# --- resolve the copier binary (accepts a PATH name or an explicit path) -----
if command -v "$COPIER_IN" >/dev/null 2>&1; then
  COPIER="$(command -v "$COPIER_IN")"
elif [ -x "$COPIER_IN" ]; then
  COPIER="$COPIER_IN"
else
  echo "ERROR: copier binary not found or not executable: $COPIER_IN" >&2
  echo "       pass a path, e.g. $(basename "$0") /tmp/civenv/bin/copier" >&2
  exit 3
fi

# --- required tooling --------------------------------------------------------
for tool in jq python3 bash find grep sed; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: required tool missing: $tool" >&2; exit 3; }
done

# --- copier source args: pin a git template to HEAD; a non-git copy renders
#     its working files directly (JV_TEMPLATE dirty-test / catch-proof path) ---
VCS_ARGS=()
if git -C "$TEMPLATE_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  VCS_ARGS=(--vcs-ref HEAD)
fi

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/jv-matrix.XXXXXX")"
cleanup() { rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM

echo "generate-matrix-check"
echo "  copier   : $COPIER  ($("$COPIER" --version 2>/dev/null))"
echo "  template : $TEMPLATE_ROOT ${VCS_ARGS:+(git HEAD)}"
echo "  workdir  : $TMP_ROOT"

TOTAL=0
FAILS=0

# ---------------------------------------------------------------------------
# scan_unrendered <dir> — echo any surviving Jinja OPENER ({{ or {%) as
# file:line:content, after stripping the KNOWN-SAFE tokens the dogfood cleared:
#   * {{SANDBOX}}      — the hook harness's runtime placeholder (test files)
#   * shell ${..}}     — a closing }} with no {{ opener; never matches
#   * pacemaker {role} — single-brace; never matches a {{/{% opener
# Only the two Jinja OPENERS are treated as unrendered — that is what a
# copier-rendered file must never contain, and it will not false-positive on the
# shell/pacemaker closers.
# ---------------------------------------------------------------------------
scan_unrendered() {
  local dir="$1" f rel
  find "$dir" -type f -not -path '*/.git/*' -print | while IFS= read -r f; do
    grep -Iq . "$f" 2>/dev/null || continue          # skip binary/empty files
    rel="${f#"$dir"/}"
    sed 's/{{SANDBOX}}//g' "$f" | grep -nE '\{\{|\{%' | sed "s#^#  ${rel}:#"
  done
}

# ---------------------------------------------------------------------------
# check_set <name> <data-file> <expect_hb> <expect_mig>
#   expect_hb  : producer | inert
#   expect_mig : supabase | sql | none
# ---------------------------------------------------------------------------
check_set() {
  local name="$1" datafile="$2" expect_hb="$3" expect_mig="$4"
  local out="$TMP_ROOT/out-$name"
  local -a errs=()
  TOTAL=$((TOTAL + 1))

  # --- generate ---
  if ! "$COPIER" copy --defaults "${VCS_ARGS[@]}" --data-file "$datafile" \
        "$TEMPLATE_ROOT" "$out" >"$TMP_ROOT/$name.copier.log" 2>&1; then
    errs+=("copier copy FAILED (generation error) — last lines:")
    while IFS= read -r l; do errs+=("    $l"); done < <(tail -n 8 "$TMP_ROOT/$name.copier.log")
    _report "$name" errs
    return
  fi

  local S="$out/.claude/settings.json"
  local HB="$out/.claude/hooks/stop/actions/heartbeat-writer.sh"
  local GUARD="$out/.claude/hooks/guards/migration-safety.sh"

  # --- (a) no leaked .jinja files ---
  local leaked
  leaked="$(find "$out" -name '*.jinja' -print)"
  [ -n "$leaked" ] && { errs+=("(a) leaked *.jinja files:"); while IFS= read -r l; do errs+=("    $l"); done <<<"$leaked"; }

  # --- (a) no unrendered Jinja constructs (known-safe tokens excluded) ---
  local unrendered
  unrendered="$(scan_unrendered "$out")"
  [ -n "$unrendered" ] && { errs+=("(a) unrendered Jinja construct(s):"); while IFS= read -r l; do errs+=("  $l"); done <<<"$unrendered"; }

  # --- (b) settings.json valid JSON ---
  if [ ! -f "$S" ]; then
    errs+=("(b) .claude/settings.json missing")
  elif ! jq -e . "$S" >/dev/null 2>&1; then
    errs+=("(b) .claude/settings.json is NOT valid JSON")
  fi

  # --- (c) bash -n clean on every generated *.sh ---
  local sh nerr
  nerr=""
  while IFS= read -r sh; do
    bash -n "$sh" 2>>"$TMP_ROOT/$name.bashn.err" || nerr="$nerr $sh"
  done < <(find "$out" -name '*.sh' -print)
  [ -n "$nerr" ] && { errs+=("(c) bash -n syntax error in:"); for x in $nerr; do errs+=("    ${x#"$out"/}"); done; }

  # --- (c) every stop check/action is executable (dead-pipeline root cause) ---
  local ne=""
  while IFS= read -r sh; do
    [ -x "$sh" ] || ne="$ne ${sh#"$out"/}"
  done < <(find "$out/.claude/hooks/stop/checks" "$out/.claude/hooks/stop/actions" -name '*.sh' -print 2>/dev/null)
  [ -x "$out/.claude/hooks/stop/runner.sh" ] || ne="$ne .claude/hooks/stop/runner.sh"
  [ -n "$ne" ] && { errs+=("(c) NON-executable stop hook(s) — pipeline would be dead:"); for x in $ne; do errs+=("    $x"); done; }

  # --- (d) hook harness green ---
  if [ -f "$out/.claude/hooks/tests/run-all.sh" ]; then
    if ! bash "$out/.claude/hooks/tests/run-all.sh" >"$TMP_ROOT/$name.harness.log" 2>&1; then
      errs+=("(d) hook harness FAILED (run-all.sh non-zero) — tail:")
      while IFS= read -r l; do errs+=("    $l"); done < <(tail -n 6 "$TMP_ROOT/$name.harness.log")
    fi
  else
    errs+=("(d) harness run-all.sh missing")
  fi

  # --- (d) the real Stop runner executes to a clean exit (pipeline live) ---
  if [ -f "$out/.claude/hooks/stop/runner.sh" ]; then
    local rc
    ( cd "$out" && printf '{"stop_hook_active":false,"transcript_path":"/nonexistent"}' \
        | bash "$out/.claude/hooks/stop/runner.sh" >"$TMP_ROOT/$name.runner.log" 2>&1 )
    rc=$?
    if [ "$rc" -ne 0 ]; then
      errs+=("(d) Stop runner.sh exited $rc (expected 0 — no completion claimed) — tail:")
      while IFS= read -r l; do errs+=("    $l"); done < <(tail -n 6 "$TMP_ROOT/$name.runner.log")
    fi
  else
    errs+=("(d) stop/runner.sh missing")
  fi

  # --- (e) answer-coherence: heartbeat gate (orchestration_tier) ---
  if [ -f "$HB" ]; then
    local has_prod has_inert
    has_prod=$(grep -c 'PRODUCER half' "$HB"); has_inert=$(grep -c 'INERT in this project' "$HB")
    case "$expect_hb" in
      producer)
        { [ "$has_prod" -ge 1 ] && [ "$has_inert" -eq 0 ]; } || \
          errs+=("(e) cluster gate WRONG: expected heartbeat PRODUCER, got producer=$has_prod inert=$has_inert (cluster machinery silently stripped?)") ;;
      inert)
        { [ "$has_inert" -ge 1 ] && [ "$has_prod" -eq 0 ]; } || \
          errs+=("(e) solo gate WRONG: expected inert heartbeat stub, got producer=$has_prod inert=$has_inert") ;;
    esac
  else
    errs+=("(e) heartbeat-writer.sh missing")
  fi

  # --- (e) answer-coherence: migration variant (db_adapter/database) ---
  if [ -f "$S" ] && jq -e . "$S" >/dev/null 2>&1; then
    local matchers
    matchers="$(jq -r '.hooks.PreToolUse[].matcher' "$S" 2>/dev/null)"
    case "$expect_mig" in
      supabase)
        printf '%s\n' "$matchers" | grep -q 'mcp__supabase__execute_sql|mcp__supabase__apply_migration' || \
          errs+=("(e) migration matcher WRONG: expected Supabase matcher, got: $(printf '%s' "$matchers" | tr '\n' ',')")
        grep -q 'execute_sql' "$GUARD" 2>/dev/null || errs+=("(e) migration guard is not the supabase variant (no execute_sql)") ;;
      sql)
        printf '%s\n' "$matchers" | grep -qx 'Bash' || \
          errs+=("(e) migration matcher WRONG: expected generic-SQL 'Bash' matcher, got: $(printf '%s' "$matchers" | tr '\n' ',')")
        { grep -q 'psql' "$GUARD" 2>/dev/null && ! grep -q 'execute_sql' "$GUARD" 2>/dev/null; } || \
          errs+=("(e) migration guard is not the generic-SQL variant") ;;
      none)
        if printf '%s\n' "$matchers" | grep -qE 'supabase|^Bash$'; then
          errs+=("(e) migration hook present but expected NONE (matchers: $(printf '%s' "$matchers" | tr '\n' ','))")
        fi
        grep -q 'DISABLED for this configuration' "$GUARD" 2>/dev/null || \
          errs+=("(e) migration guard is not the disabled no-op variant") ;;
    esac
  fi

  _report "$name" errs
}

# _report <name> <errs-array-name-by-nameref>
_report() {
  local name="$1"; local -n _e="$2"
  if [ "${#_e[@]}" -eq 0 ]; then
    printf '\n[PASS] %s\n' "$name"
  else
    FAILS=$((FAILS + 1))
    printf '\n[FAIL] %s\n' "$name"
    local line
    for line in "${_e[@]}"; do printf '   %s\n' "$line"; done
  fi
}

# ===========================================================================
# THE MATRIX — tiers x db adapters, hitting the dict-gated conditionals.
# ===========================================================================
mkdir -p "$TMP_ROOT/data"

# --- Set 1: solo / greenfield / no DB / no testing (the no-op-shim baseline) ---
cat > "$TMP_ROOT/data/solo-greenfield-none.yml" <<'YML'
project_name: MatrixSolo
project_description: solo greenfield, no DB, no testing
project_type: greenfield
stack: go
language: go
database: none
db_adapter: none
testing: none
unit_testing: go-test
orchestration_tier: solo
isolation_tier: none
type_check_command: go vet ./...
build_command: go build ./...
main_branch: main
staging_branch: ""
YML

# --- Set 2: cluster / brownfield / supabase / playwright+TDS (cp-match) -------
cat > "$TMP_ROOT/data/cluster-brownfield-supabase.yml" <<'YML'
project_name: MatrixSupabase
project_description: cluster brownfield supabase, playwright + TDS
project_type: brownfield
stack: nextjs
language: typescript
database: supabase
db_adapter: supabase
testing: playwright
unit_testing: jest
use_tds: true
orchestration_tier: cluster
team_size: 3
external_pacemaker: tmux-supervisor
isolation_tier: schema
max_parallel_streams: 3
type_check_command: pnpm type-check
build_command: pnpm build:web
main_branch: main
staging_branch: staging
YML

# --- Set 3: cluster / brownfield / postgres (generic-SQL migration branch) ----
cat > "$TMP_ROOT/data/cluster-brownfield-postgres.yml" <<'YML'
project_name: MatrixPostgres
project_description: cluster brownfield postgres, generic-SQL migration guard
project_type: brownfield
stack: fastapi
language: python
database: postgres
db_adapter: postgres
testing: none
unit_testing: pytest
orchestration_tier: cluster
team_size: 2
external_pacemaker: host-cron
isolation_tier: schema
max_parallel_streams: 3
type_check_command: mypy .
build_command: make build
main_branch: main
staging_branch: staging
YML

# --- Set 4: cluster / greenfield / no DB (cluster machinery, no migration) ----
cat > "$TMP_ROOT/data/cluster-greenfield-none.yml" <<'YML'
project_name: MatrixClusterNoDB
project_description: cluster greenfield, no DB, playwright
project_type: greenfield
stack: rust
language: rust
database: none
db_adapter: none
testing: playwright
unit_testing: none
use_tds: false
orchestration_tier: cluster
team_size: 2
external_pacemaker: tmux-supervisor
isolation_tier: none
type_check_command: cargo check
build_command: cargo build
main_branch: main
staging_branch: staging
YML

#            name                            data-file                                        hb        mig
check_set "solo-greenfield-none"        "$TMP_ROOT/data/solo-greenfield-none.yml"        inert     none
check_set "cluster-brownfield-supabase" "$TMP_ROOT/data/cluster-brownfield-supabase.yml" producer  supabase
check_set "cluster-brownfield-postgres" "$TMP_ROOT/data/cluster-brownfield-postgres.yml" producer  sql
check_set "cluster-greenfield-none"     "$TMP_ROOT/data/cluster-greenfield-none.yml"     producer  none

# ===========================================================================
echo ""
echo "==============================================="
echo "matrix sets: $TOTAL, failed: $FAILS"
echo "==============================================="
[ "$FAILS" -eq 0 ]

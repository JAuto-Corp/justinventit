#!/bin/bash
# ===========================================================================
# evidence.sh — machine-checkable evidence helpers for the ATDD/TDD stop gate.
# ---------------------------------------------------------------------------
# Generic port of the customer-portal evidence library
# (.claude/hooks/lib/evidence.sh: check_scenarios_executed, check_red_before_green,
#  check_tdd_cycle) with all domain content removed. The CONCEPTS are generic:
#   * SCENARIOS.md    — the phase's acceptance scenarios (Gherkin-style)
#   * PROGRESS.md     — the phase's implementation checklist
#   * an evidence file — JSON the project's test runner writes to record what ran
#
# Sourced by stop/checks/03..05. Every function is SKIP-SAFE: when the relevant
# state file is absent it returns a benign "no work / pass" verdict so a fresh
# project is never false-blocked. Only a genuine "required-and-missing" returns
# a blocking verdict. Pure bash + jq (optional); no `set -e` (grep-heavy).
#
# Configurable locations (env overrides, generic defaults — matches the fixed
# framework state chain: docs/CURRENT_WORK.md -> context/WORKING.md -> phase files):
#   JUSTINVENTIT_EVIDENCE_DIR   default: <repo>/.claude/memory   (evidence JSON dir)
#   JUSTINVENTIT_CURRENT_WORK   default: <repo>/docs/CURRENT_WORK.md (phase pointer)
# ===========================================================================

# --- repo root (fall back gracefully if utils.sh not sourced) ----------------
_ev_repo_root() {
  if command -v get_repo_root >/dev/null 2>&1; then
    get_repo_root
  else
    git rev-parse --show-toplevel 2>/dev/null || echo "."
  fi
}

# --- evidence dir (where the project's test runner records run evidence JSON) -
_ev_evidence_dir() {
  if [ -n "${JUSTINVENTIT_EVIDENCE_DIR:-}" ]; then
    echo "$JUSTINVENTIT_EVIDENCE_DIR"
  else
    echo "$(_ev_repo_root)/.claude/memory"
  fi
}

# ===========================================================================
# TRANSCRIPT / SIGNAL HELPERS
# ---------------------------------------------------------------------------
# The stop-hook JSON (on the runner's STDIN) carries `transcript_path`. The
# completion signal `[PHASE_COMPLETE]` and the escape hatch `[EVIDENCE_OVERRIDE:]`
# live in the transcript. We grep the transcript FILE for the literal signal so
# detection is format-agnostic (JSONL or array) and domain-free.
# ===========================================================================

# Extract transcript_path from a stop-hook JSON blob (arg 1). Empty if absent.
# grep/sed extraction (no jq dependency) — mirrors the customer-portal stop.sh.
hook_transcript_path() {
  printf '%s' "${1:-}" \
    | grep -o '"transcript_path"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | head -1 \
    | sed 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' 2>/dev/null
}

# True (0) if a literal signal appears in the transcript file. Never errors.
transcript_has_signal() {
  local transcript="$1" signal="$2"
  [ -n "$transcript" ] && [ -f "$transcript" ] || return 1
  grep -qF -- "$signal" "$transcript" 2>/dev/null
}

# ===========================================================================
# PHASE STATE-FILE RESOLUTION
# ---------------------------------------------------------------------------
# The active phase directory is project-variable, discovered at RUNTIME from the
# CURRENT_WORK.md pointer (the framework does not fix a plans/ path). Generic,
# domain-free replacement for the customer-portal `find docs/features/plans
# -path *phase-N* -name X` logic: pull path-like tokens out of CURRENT_WORK.md
# and return the first that resolves to (or contains) the requested file.
# Empty output => no active phase => caller no-ops (never false-blocks).
# ===========================================================================
resolve_phase_file() {
  local name="$1"
  local root; root="$(_ev_repo_root)"
  local cw="${JUSTINVENTIT_CURRENT_WORK:-$root/docs/CURRENT_WORK.md}"
  [ -f "$cw" ] || return 0

  # Path-like tokens (must contain a slash); strip surrounding markdown/punct.
  local tokens t cand d hit
  tokens="$(grep -oE '[A-Za-z0-9_.-]*/[A-Za-z0-9_./-]+' "$cw" 2>/dev/null | sort -u)"
  [ -n "$tokens" ] || return 0

  while IFS= read -r t; do
    [ -n "$t" ] || continue
    t="${t#/}"                      # keep relative to repo root
    cand="$root/$t"
    if [ -f "$cand" ]; then
      [ "$(basename "$cand")" = "$name" ] && { echo "$cand"; return 0; }
      d="$(dirname "$cand")"
      [ -f "$d/$name" ] && { echo "$d/$name"; return 0; }
    elif [ -d "$cand" ]; then
      [ -f "$cand/$name" ] && { echo "$cand/$name"; return 0; }
      hit="$(find "$cand" -name "$name" -type f 2>/dev/null | head -1)"
      [ -n "$hit" ] && { echo "$hit"; return 0; }
    fi
  done <<< "$tokens"
  return 0
}

# ===========================================================================
# SCENARIO ID EXTRACTION
# ---------------------------------------------------------------------------
# Generic replacement for the customer-portal domain regex
# (tech_job_[0-9]+|cust_ord_[0-9]+|...). A scenario is identified by the
# normalized snake_case form of its title. Matches Gherkin `Scenario:` /
# `Scenario Outline:` lines and markdown `## Scenario: <id>` / `#### <id>`
# headers. The project's test runner records evidence keyed by the SAME id.
#   "Scenario: user_login"            -> user_login
#   "## Scenario: User logs in"       -> user_logs_in
# ===========================================================================
extract_scenario_ids() {
  local f="$1"
  [ -f "$f" ] || return 0
  {
    grep -oiE '^[[:space:]]*#*[[:space:]]*scenario( outline)?:[[:space:]]*.+' "$f" 2>/dev/null \
      | sed -E 's/^[[:space:]]*#*[[:space:]]*[Ss]cenario( [Oo]utline)?:[[:space:]]*//I'
    grep -oE '^####[[:space:]]+[a-z][a-z0-9_]+' "$f" 2>/dev/null \
      | sed -E 's/^####[[:space:]]+//'
  } | while IFS= read -r title; do
        [ -n "$title" ] || continue
        printf '%s\n' "$title" \
          | tr '[:upper:]' '[:lower:]' \
          | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//'
      done | grep -vE '^$' | sort -u
}

# ===========================================================================
# SCENARIO EXECUTION EVIDENCE   (check 03)
# ---------------------------------------------------------------------------
# Usage:   check_scenarios_executed <SCENARIOS.md>
# Returns: "no-scenarios"          — no file / no parseable scenarios (SKIP)
#          "complete"              — every scenario has a passing run (PASS)
#          "missing: id1 id2 ..."  — some scenario has no passing run (BLOCK)
# Direct port of the customer-portal check_scenarios_executed mechanism.
# ===========================================================================
check_scenarios_executed() {
  local scenarios_file="$1"
  local evidence_file; evidence_file="$(_ev_evidence_dir)/scenario-evidence.json"

  [ -f "$scenarios_file" ] || { echo "no-scenarios"; return; }

  local required; required="$(extract_scenario_ids "$scenarios_file")"
  [ -n "$required" ] || { echo "no-scenarios"; return; }

  if [ ! -f "$evidence_file" ] || ! command -v jq >/dev/null 2>&1; then
    echo "missing:$(printf '%s' "$required" | tr '\n' ' ' | sed 's/^/ /; s/  */ /g; s/ $//')"
    return
  fi

  local missing="" s found
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    found="$(jq -r --arg s "$s" \
      '.runs[]? | select(.scenario==$s and .status=="pass") | .scenario' \
      "$evidence_file" 2>/dev/null | head -1)"
    [ -n "$found" ] || missing="$missing $s"
  done <<< "$required"

  if [ -z "${missing// /}" ]; then
    echo "complete"
  else
    echo "missing:$missing"
  fi
}

# ===========================================================================
# RED-BEFORE-GREEN (TDD cycle)   (check 04)
# ---------------------------------------------------------------------------
# check_red_before_green <scenario_id>
#   -> valid | missing-red | missing-green | out-of-order
# check_tdd_cycle <SCENARIOS.md>
#   -> pass                      — every scenario went RED before GREEN (or no
#                                  scenarios / no file) (PASS / SKIP)
#      warn: id1 id2 ...         — RED phase never recorded (BLOCK, overridable)
#      fail: id1 id2 ...         — GREEN recorded before RED (BLOCK)
# Direct port of the customer-portal check_red_before_green / check_tdd_cycle.
# Evidence JSON shape: { "red_phases": {id: ts}, "green_phases": {id: ts} }.
# ===========================================================================
check_red_before_green() {
  local scenario="$1"
  local file; file="$(_ev_evidence_dir)/scenario-evidence.json"

  if [ ! -f "$file" ] || ! command -v jq >/dev/null 2>&1; then
    echo "missing-red"; return
  fi

  local red_ts green_ts
  red_ts="$(jq -r --arg s "$scenario" '.red_phases[$s] // ""' "$file" 2>/dev/null)"
  green_ts="$(jq -r --arg s "$scenario" '.green_phases[$s] // ""' "$file" 2>/dev/null)"

  if [ -z "$red_ts" ] || [ "$red_ts" = "null" ]; then echo "missing-red"; return; fi
  if [ -z "$green_ts" ] || [ "$green_ts" = "null" ]; then echo "missing-green"; return; fi

  local red_epoch green_epoch
  red_epoch="$(date -d "$red_ts" +%s 2>/dev/null || echo 0)"
  green_epoch="$(date -d "$green_ts" +%s 2>/dev/null || echo 0)"

  if [ "$red_epoch" -lt "$green_epoch" ]; then echo "valid"; else echo "out-of-order"; fi
}

check_tdd_cycle() {
  local scenarios_file="$1"
  [ -f "$scenarios_file" ] || { echo "pass"; return; }

  local required; required="$(extract_scenario_ids "$scenarios_file")"
  [ -n "$required" ] || { echo "pass"; return; }

  local missing_red="" out_of_order="" s status
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    status="$(check_red_before_green "$s")"
    case "$status" in
      missing-red)  missing_red="$missing_red $s" ;;
      out-of-order) out_of_order="$out_of_order $s" ;;
    esac
  done <<< "$required"

  if [ -n "${out_of_order// /}" ]; then
    echo "fail:${out_of_order}"
  elif [ -n "${missing_red// /}" ]; then
    echo "warn:${missing_red}"
  else
    echo "pass"
  fi
}

#!/bin/bash
# ===========================================================================
# Stop CHECK 03 — SCENARIO-EXECUTION EVIDENCE  (ATDD gate)
# ---------------------------------------------------------------------------
# ENFORCES: when a phase is signaled complete ([PHASE_COMPLETE]) and the phase
# has SCENARIOS.md, every scenario must have a recorded PASSING run before the
# session may stop. Prevents "phase done" with untested acceptance scenarios.
#
# Ported from customer-portal stop.sh §0.9 (Scenario Evidence Check, Layer 2)
# + lib/evidence.sh check_scenarios_executed. Domain content removed.
#
# BLOCK  (exit 1): phase-complete signaled, SCENARIOS.md present, a scenario has
#                  no passing run.  ->  "missing: ..."
# SKIP   (exit 0): no transcript / no [PHASE_COMPLETE] / [EVIDENCE_OVERRIDE:*] /
#                  no SCENARIOS.md for the active phase / no parseable scenarios
#                  / every scenario passed.  A fresh project is NEVER blocked.
# ===========================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/utils.sh"
source "$SCRIPT_DIR/../../lib/evidence.sh"

# --- Read the stop-hook JSON (forwarded by runner.sh; empty when run manually) -
INPUT=""
if [ ! -t 0 ]; then INPUT="$(cat)"; fi

# --- Gate: only enforce at phase-completion time -----------------------------
TRANSCRIPT="$(hook_transcript_path "$INPUT")"
transcript_has_signal "$TRANSCRIPT" '[PHASE_COMPLETE]' || exit 0      # not signaled -> skip
transcript_has_signal "$TRANSCRIPT" '[EVIDENCE_OVERRIDE:' && exit 0   # override -> skip

# --- Locate the active phase's SCENARIOS.md; absent => no-op -----------------
SCENARIOS_FILE="$(resolve_phase_file SCENARIOS.md)"
[ -n "$SCENARIOS_FILE" ] && [ -f "$SCENARIOS_FILE" ] || exit 0

STATUS="$(check_scenarios_executed "$SCENARIOS_FILE")"
case "$STATUS" in
  missing:*)
    MISSING="${STATUS#missing:}"
    report_check "block" \
      "Phase completion signaled but scenarios were not run/passed:${MISSING}. Run each phase scenario and record a passing result, or add [EVIDENCE_OVERRIDE:manual-testing]." \
      || exit 1
    ;;
esac
exit 0

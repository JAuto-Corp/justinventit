#!/bin/bash
# ===========================================================================
# Stop CHECK 04 — RED-before-GREEN  (TDD cycle)
# ---------------------------------------------------------------------------
# ENFORCES: when a phase is signaled complete and has SCENARIOS.md, each scenario
# must have been seen FAIL (RED) before it passed (GREEN). Proves the test can
# actually fail, so GREEN means something. Catches tests written after the code.
#
# Ported from customer-portal stop.sh §0.95 (TDD cycle branch) + lib/evidence.sh
# check_tdd_cycle / check_red_before_green. Domain content removed.
#
# BLOCK (exit 1): phase-complete signaled, SCENARIOS.md present, and either
#                 GREEN-before-RED (fail:) or no RED evidence (warn:, overridable).
# SKIP  (exit 0): no transcript / no [PHASE_COMPLETE] / [EVIDENCE_OVERRIDE:*] /
#                 no SCENARIOS.md / no parseable scenarios / clean RED->GREEN.
# ===========================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/utils.sh"
source "$SCRIPT_DIR/../../lib/evidence.sh"

INPUT=""
if [ ! -t 0 ]; then INPUT="$(cat)"; fi

TRANSCRIPT="$(hook_transcript_path "$INPUT")"
transcript_has_signal "$TRANSCRIPT" '[PHASE_COMPLETE]' || exit 0
transcript_has_signal "$TRANSCRIPT" '[EVIDENCE_OVERRIDE:' && exit 0

SCENARIOS_FILE="$(resolve_phase_file SCENARIOS.md)"
[ -n "$SCENARIOS_FILE" ] && [ -f "$SCENARIOS_FILE" ] || exit 0

STATUS="$(check_tdd_cycle "$SCENARIOS_FILE")"
case "$STATUS" in
  fail:*)
    OOO="${STATUS#fail:}"
    report_check "block" \
      "Phase completion signaled but TDD cycle violated (GREEN recorded before RED) for:${OOO}. A scenario must be seen failing before it passes, or add [EVIDENCE_OVERRIDE:manual-testing]." \
      || exit 1
    ;;
  warn:*)
    MR="${STATUS#warn:}"
    report_check "block" \
      "Phase completion signaled but no RED-phase evidence for:${MR}. Run each scenario BEFORE implementing (expect failure) to prove the test is valid, then implement and re-run for GREEN, or add [EVIDENCE_OVERRIDE:no-red-phase]." \
      || exit 1
    ;;
esac
exit 0

#!/bin/bash
# ===========================================================================
# Self-test: Stop CHECK 04 — RED-before-GREEN (TDD cycle)
# ---------------------------------------------------------------------------
# Contract: BLOCK (exit 1) when a phase is signaled complete, SCENARIOS.md
# exists, and a scenario went GREEN before RED (fail:) or has no RED evidence
# (warn:). Otherwise SKIP (exit 0), incl. no SCENARIOS.md and no signal.
# Run: bash test-stop-tdd-cycle.sh   (exit 0 = all pass)
# ===========================================================================
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

CHECK="$HERE/../stop/checks/04-tdd-cycle.sh"
STDIN='{"transcript_path":"{{SANDBOX}}/transcript.txt","stop_hook_active":false}'

seed='git init -q; git config user.email t@t; git config user.name t;
 mkdir -p docs/plans/phase-1 .claude/memory;
 printf "Active phase: docs/plans/phase-1\n" > docs/CURRENT_WORK.md;
 printf "## Scenario: user_login\n" > docs/plans/phase-1/SCENARIOS.md;'

# (a) SKIP — no SCENARIOS.md, signal present ---------------------------------
run_case --name "04 no-op: phase-complete but no SCENARIOS.md -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup 'git init -q; mkdir -p docs/plans/phase-1;
           printf "Active phase: docs/plans/phase-1\n" > docs/CURRENT_WORK.md;
           printf "[PHASE_COMPLETE]\n" > transcript.txt' \
  --expect-exit 0

# (a2) SKIP — SCENARIOS.md, out-of-order evidence, but NO signal --------------
run_case --name "04 no-op: violation present but no phase-complete -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf '%s' '{\"red_phases\":{\"user_login\":\"2020-01-01T00:00:02Z\"},\"green_phases\":{\"user_login\":\"2020-01-01T00:00:01Z\"}}' > .claude/memory/scenario-evidence.json;
           printf \"still going\n\" > transcript.txt" \
  --expect-exit 0

# (b) PASS — RED before GREEN ------------------------------------------------
run_case --name "04 pass: RED recorded before GREEN -> exit 0" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf '%s' '{\"red_phases\":{\"user_login\":\"2020-01-01T00:00:01Z\"},\"green_phases\":{\"user_login\":\"2020-01-01T00:00:05Z\"}}' > .claude/memory/scenario-evidence.json;
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 0

# (c) BLOCK — GREEN recorded before RED (out-of-order) -----------------------
run_case --name "04 BLOCK: GREEN before RED -> exit 1" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf '%s' '{\"red_phases\":{\"user_login\":\"2020-01-01T00:00:05Z\"},\"green_phases\":{\"user_login\":\"2020-01-01T00:00:01Z\"}}' > .claude/memory/scenario-evidence.json;
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 1 \
  --expect-out "GREEN recorded before RED" --channel any

# (c2) BLOCK — no RED evidence at all (warn -> block) ------------------------
run_case --name "04 BLOCK: no RED-phase evidence -> exit 1" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 1 \
  --expect-out "no RED-phase evidence" --channel any

# (d) SKIP — override present ------------------------------------------------
run_case --name "04 no-op: [EVIDENCE_OVERRIDE] present -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf \"[PHASE_COMPLETE] [EVIDENCE_OVERRIDE:no-red-phase]\n\" > transcript.txt" \
  --expect-exit 0

harness_summary
exit $?

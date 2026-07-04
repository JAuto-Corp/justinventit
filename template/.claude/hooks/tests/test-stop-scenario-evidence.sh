#!/bin/bash
# ===========================================================================
# Self-test: Stop CHECK 03 — scenario-execution evidence
# ---------------------------------------------------------------------------
# Contract: BLOCK (exit 1) only when a phase is signaled complete, SCENARIOS.md
# exists for the active phase, and a scenario has no passing run. Otherwise SKIP
# (exit 0) — including the fresh-project case with no SCENARIOS.md.
# Run: bash test-stop-scenario-evidence.sh   (exit 0 = all pass)
# ===========================================================================
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

CHECK="$HERE/../stop/checks/03-scenario-evidence.sh"
STDIN='{"transcript_path":"{{SANDBOX}}/transcript.txt","stop_hook_active":false}'

# Seed a phase pointer + SCENARIOS.md (+ optional evidence). $1 = evidence JSON
# ('' => no evidence file), $2 = transcript body.
seed='git init -q; git config user.email t@t; git config user.name t;
 mkdir -p docs/plans/phase-1 .claude/memory;
 printf "Active phase: docs/plans/phase-1\n" > docs/CURRENT_WORK.md;
 printf "## Scenario: user_login\n" > docs/plans/phase-1/SCENARIOS.md;'

# (a) SKIP — no SCENARIOS.md even though phase-complete IS signaled -----------
run_case --name "03 no-op: phase-complete but no SCENARIOS.md -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup 'git init -q; mkdir -p docs/plans/phase-1;
           printf "Active phase: docs/plans/phase-1\n" > docs/CURRENT_WORK.md;
           printf "[PHASE_COMPLETE]\n" > transcript.txt' \
  --expect-exit 0

# (a2) SKIP — SCENARIOS.md + missing evidence but NO phase-complete signal ----
run_case --name "03 no-op: scenarios+missing evidence but no signal -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf \"mid-phase, still working\n\" > transcript.txt" \
  --expect-exit 0

# (b) PASS — scenario has a passing run --------------------------------------
run_case --name "03 pass: scenario has passing evidence -> exit 0" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf '%s' '{\"runs\":[{\"scenario\":\"user_login\",\"status\":\"pass\"}]}' > .claude/memory/scenario-evidence.json;
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 0

# (c) BLOCK — required scenario, no evidence file ----------------------------
run_case --name "03 BLOCK: phase-complete + scenario never run -> exit 1" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 1 \
  --expect-out "were not run/passed" --channel any

# (c2) BLOCK — evidence present but scenario failed (not pass) ----------------
run_case --name "03 BLOCK: scenario ran but did not pass -> exit 1" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf '%s' '{\"runs\":[{\"scenario\":\"user_login\",\"status\":\"fail\"}]}' > .claude/memory/scenario-evidence.json;
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 1 \
  --expect-out "user_login" --channel any

# (d) SKIP — override escape hatch present -----------------------------------
run_case --name "03 no-op: [EVIDENCE_OVERRIDE] present -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf \"[PHASE_COMPLETE] [EVIDENCE_OVERRIDE:manual-testing]\n\" > transcript.txt" \
  --expect-exit 0

harness_summary
exit $?

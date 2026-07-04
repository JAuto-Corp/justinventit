#!/bin/bash
# ===========================================================================
# Self-test: Stop CHECK 05 — PROGRESS.md evidence
# ---------------------------------------------------------------------------
# Contract: BLOCK (exit 1) when a phase is signaled complete, PROGRESS.md exists,
# and either an item is unchecked OR >=3 items are checked with no recent commit.
# Otherwise SKIP (exit 0), incl. no PROGRESS.md and no signal.
# Run: bash test-stop-progress-evidence.sh   (exit 0 = all pass)
# ===========================================================================
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

CHECK="$HERE/../stop/checks/05-progress-evidence.sh"
STDIN='{"transcript_path":"{{SANDBOX}}/transcript.txt","stop_hook_active":false}'

# Base: git repo + phase pointer. Caller appends PROGRESS.md + transcript.
seed='git init -q; git config user.email t@t; git config user.name t;
 mkdir -p docs/plans/phase-1;
 printf "Active phase: docs/plans/phase-1\n" > docs/CURRENT_WORK.md;'

# (a) SKIP — no PROGRESS.md, signal present ----------------------------------
run_case --name "05 no-op: phase-complete but no PROGRESS.md -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 0

# (a2) SKIP — unchecked items present but NO phase-complete signal ------------
run_case --name "05 no-op: unchecked items but no signal -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf -- \"- [ ] build it\n\" > docs/plans/phase-1/PROGRESS.md;
           printf \"working...\n\" > transcript.txt" \
  --expect-exit 0

# (b) PASS — all items checked AND backed by a commit ------------------------
run_case --name "05 pass: all checked + commit present -> exit 0" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf -- \"- [x] a\n- [x] b\n- [x] c\n\" > docs/plans/phase-1/PROGRESS.md;
           git add -A; git commit -qm 'work';
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 0

# (c) BLOCK — an item is unchecked -------------------------------------------
run_case --name "05 BLOCK: unchecked item + phase-complete -> exit 1" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf -- \"- [x] a\n- [ ] b\n\" > docs/plans/phase-1/PROGRESS.md;
           git add -A; git commit -qm 'work';
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 1 \
  --expect-out "unchecked" --channel any

# (c2) BLOCK — 3+ items checked but NO commits (checklist without work) -------
run_case --name "05 BLOCK: 3 checked, zero commits -> exit 1" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf -- \"- [x] a\n- [x] b\n- [x] c\n\" > docs/plans/phase-1/PROGRESS.md;
           printf \"[PHASE_COMPLETE]\n\" > transcript.txt" \
  --expect-exit 1 \
  --expect-out "NO commits found" --channel any

# (d) SKIP — override on the unchecked case ----------------------------------
run_case --name "05 no-op: unchecked but [EVIDENCE_OVERRIDE] -> pass" \
  --hook "$CHECK" --stdin "$STDIN" \
  --setup "$seed printf -- \"- [ ] b\n\" > docs/plans/phase-1/PROGRESS.md;
           printf \"[PHASE_COMPLETE] [EVIDENCE_OVERRIDE:no-code-changes]\n\" > transcript.txt" \
  --expect-exit 0

harness_summary
exit $?

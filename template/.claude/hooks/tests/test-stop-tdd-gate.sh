#!/bin/bash
# ===========================================================================
# Self-test: Stop CHECK 01 — TDD gate (scenarios must exist for standard+ scope)
# ---------------------------------------------------------------------------
# Regression guard for the shallow/first-commit false-block: `git diff HEAD~1`
# under `set -e` exited 128 when HEAD had no parent, false-blocking a fresh
# project's FIRST stop. Fixed via skip-when-no-parent (graceful no-op).
# Run: bash test-stop-tdd-gate.sh   (exit 0 = all pass)
# ===========================================================================
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

CHECK="$HERE/../stop/checks/01-tdd-gate.sh"
seed='git init -q; git config user.email t@t; git config user.name t;'

# (a) REGRESSION — single-commit repo (no HEAD~1), 5 files: must NOT exit 128;
#     can't diff a first commit -> treat as quick scope -> pass.
run_case --name "01 regression: first-commit repo (no HEAD~1) -> pass, not 128" \
  --hook "$CHECK" \
  --setup "$seed touch f1 f2 f3 f4 f5; git add -A; git commit -qm init" \
  --expect-exit 0

# (b) PASS — 2 commits, last touched <4 files -> quick scope -> pass.
run_case --name "01 pass: last commit <4 files -> exit 0" \
  --hook "$CHECK" \
  --setup "$seed touch a; git add -A; git commit -qm c1; touch b; git add -A; git commit -qm c2" \
  --expect-exit 0

# (c) BLOCK — 2 commits, last touched 4+ files, no SCENARIOS.md -> block.
run_case --name "01 BLOCK: standard+ scope, no SCENARIOS.md -> exit 1" \
  --hook "$CHECK" \
  --setup "$seed touch a; git add -A; git commit -qm c1; touch g1 g2 g3 g4; git add -A; git commit -qm c2" \
  --expect-exit 1 \
  --expect-out "SCENARIOS.md" --channel any

harness_summary
exit $?

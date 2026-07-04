#!/bin/bash
# ===========================================================================
# Run every hook self-test in this directory (test-*.sh), aggregate results.
# Each test-*.sh sources harness.sh and exits 0 = all cases pass, non-zero =
# a failure. This runner exits non-zero if ANY suite fails (0 = all pass).
#
# Wire into CI or run locally:  bash template/.claude/hooks/tests/run-all.sh
# ===========================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FAILED=0
RAN=0

for suite in "$HERE"/test-*.sh; do
  [ -f "$suite" ] || continue
  RAN=$((RAN + 1))
  echo "### $(basename "$suite")"
  if bash "$suite"; then
    echo ">>> $(basename "$suite"): OK"
  else
    echo ">>> $(basename "$suite"): FAILED"
    FAILED=$((FAILED + 1))
  fi
  echo ""
done

echo "==============================================="
echo "Suites run: $RAN, failed: $FAILED"
echo "==============================================="
[ "$FAILED" -eq 0 ]

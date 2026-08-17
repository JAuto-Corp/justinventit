#!/usr/bin/env bash
# R4 top-level wrapper: retain the frozen R1-R3 gate, then run only R4 assertions.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

retained_rc=0
r4_rc=0

"$ROOT/scripts/ci/test-skill-portability.sh" || retained_rc=$?
python3 "$SCRIPT_DIR/r4_acceptance.py" || r4_rc=$?

printf 'R4_GATE retained_exit=%d r4_exit=%d\n' "$retained_rc" "$r4_rc"
if [[ "$retained_rc" -ne 0 || "$r4_rc" -ne 0 ]]; then
  exit 1
fi

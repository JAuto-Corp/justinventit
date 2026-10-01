#!/usr/bin/env bash
# Shared binding and migration boundary for portable liveness commands.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/jv-project.sh"
# Released knobs selected independent stores or effects. Refuse before access.
for key in ${!PACEMAKER_@} CADENCE_DIR WATCHDOG_STATE_DIR WATCHDOG_LOG WATCHDOG_WT; do
  if [[ -v "$key" ]]; then
    _jv_fail "migration required: $key is retired; configure JV_PROJECT_ID, JV_PROJECT_ROOT and JV_STATE_ROOT; see docs/PACEMAKER.md"
  fi
done
_jv_project_configure
if [[ "${1:-}" == cadence ]]; then
  _jv_init_store cadence
else
  _jv_verify_store
fi
export JV_PROJECT_ID JV_PROJECT_ROOT JV_STATE_ROOT JV_STORE
exec python3 "$HERE/jv-liveness.py" "$@"

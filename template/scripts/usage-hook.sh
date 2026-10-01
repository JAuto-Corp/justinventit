#!/usr/bin/env bash
# Uninstalled wake entry; other seats must not touch any observation data.
[[ "${JV_ROLE:-}" == [oO] ]] || exit 0
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 0
bash "$HERE/lib/jv-observability.sh" hook "$@" 2>/dev/null || true
exit 0

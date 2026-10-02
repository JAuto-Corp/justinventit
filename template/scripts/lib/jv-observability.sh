#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/jv-project.sh"
[[ $# == 1 && "$1" =~ ^(usage|hook|disk)$ ]] || exit 64
_jv_project_configure
_jv_verify_store
export JV_PROJECT_ID JV_PROJECT_ROOT JV_STATE_ROOT JV_STORE
exec python3 "$HERE/jv-observability.py" "$1"

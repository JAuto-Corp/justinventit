#!/usr/bin/env bash
# A Stop event refreshes an existing declaration; it never invents wake intent.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 0
bash "$HERE/lib/jv-liveness.sh" heartbeat "$@" || printf 'heartbeat update refused; existing intent retained\n' >&2
exit 0

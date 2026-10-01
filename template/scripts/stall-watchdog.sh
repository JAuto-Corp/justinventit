#!/usr/bin/env bash
# Explicit single sweep, local reports only. See docs/PACEMAKER.md.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$HERE/lib/jv-liveness.sh" observe "$@"

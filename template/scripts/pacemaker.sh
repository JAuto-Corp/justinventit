#!/usr/bin/env bash
# Compatibility entry name for the report-only observer.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$HERE/stall-watchdog.sh" "$@"

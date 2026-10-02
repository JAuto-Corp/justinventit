#!/usr/bin/env bash
# One explicitly configured, report-only sweep; no host cleanup or scheduler.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$HERE/lib/jv-observability.sh" disk "$@"

#!/usr/bin/env bash
# Invoke the sibling lifetime wrapper from any cwd. See docs/HOST_CAPACITY.md.
set -euo pipefail
[[ $# -ge 1 ]] || { printf 'Usage: build-guarded.sh <command> [args...]\n' >&2; exit 64; }
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec bash "$SCRIPT_DIR/build-lock.sh" run "$@"

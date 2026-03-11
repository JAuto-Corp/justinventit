#!/bin/bash
# justinventit pre-compact hook
# Preserves critical state before context compression

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/utils.sh"

REPO_ROOT=$(get_repo_root)
STATE_DIR=$(get_state_dir)
WORKING_FILE="$STATE_DIR/WORKING.md"

# Append a compaction marker to WORKING.md
if [ -f "$WORKING_FILE" ]; then
  cat >> "$WORKING_FILE" << EOF

## $(get_timestamp) [AUTO-COMPACT]
Context compaction occurred. Re-read this file and docs/PLAYBOOK.md to reconstruct context.
EOF
fi

echo "Pre-compact: State preserved in context/WORKING.md"

#!/bin/bash
# Action: Extract [DISCOVERY:*] signals and optionally create GitHub issues
# This is a post-check action — it never blocks, only logs

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/utils.sh"

REPO_ROOT=$(get_repo_root)
STATE_DIR=$(get_state_dir)
DISCOVERIES_FILE="$STATE_DIR/DISCOVERIES.md"

# Read session input
SESSION_INPUT="${1:-}"
if [ -z "$SESSION_INPUT" ] && [ ! -t 0 ]; then
  SESSION_INPUT=$(cat)
fi

# Extract DISCOVERY signals
DISCOVERY_SIGNALS=$(echo "$SESSION_INPUT" | grep -oP '\[DISCOVERY:[^\]]+\].*' 2>/dev/null || true)

if [ -n "$DISCOVERY_SIGNALS" ]; then
  if [ ! -f "$DISCOVERIES_FILE" ]; then
    cat > "$DISCOVERIES_FILE" << 'EOF'
# Discoveries

> Automatically extracted from agent sessions. Review and create issues as needed.

EOF
  fi

  TIMESTAMP=$(get_timestamp)
  echo "$DISCOVERY_SIGNALS" | while IFS= read -r signal; do
    echo "## $TIMESTAMP" >> "$DISCOVERIES_FILE"
    echo "$signal" >> "$DISCOVERIES_FILE"
    echo "" >> "$DISCOVERIES_FILE"
  done
fi

exit 0

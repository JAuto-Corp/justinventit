#!/bin/bash
# Action: Extract [FRICTION:*] signals from session and log them
# This is a post-check action — it never blocks, only logs

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/utils.sh"

REPO_ROOT=$(get_repo_root)
STATE_DIR=$(get_state_dir)
FRICTION_LOG="$STATE_DIR/FRICTION_LOG.md"

# Read session input (passed via stdin from Claude Code stop hook)
SESSION_INPUT="${1:-}"

# If no input, try to read from the hook's input
if [ -z "$SESSION_INPUT" ] && [ ! -t 0 ]; then
  SESSION_INPUT=$(cat)
fi

# Extract FRICTION signals
FRICTION_SIGNALS=$(echo "$SESSION_INPUT" | grep -oP '\[FRICTION:[^\]]+\].*' 2>/dev/null || true)

if [ -n "$FRICTION_SIGNALS" ]; then
  # Ensure friction log exists
  if [ ! -f "$FRICTION_LOG" ]; then
    cat > "$FRICTION_LOG" << 'EOF'
# Friction Log

> Automatically extracted from agent sessions. Review and classify as PROJECT or FRAMEWORK.

EOF
  fi

  # Append each signal
  TIMESTAMP=$(get_timestamp)
  echo "$FRICTION_SIGNALS" | while IFS= read -r signal; do
    echo "## $TIMESTAMP" >> "$FRICTION_LOG"
    echo "$signal" >> "$FRICTION_LOG"
    echo "Classification: TODO" >> "$FRICTION_LOG"
    echo "Resolution: TODO" >> "$FRICTION_LOG"
    echo "" >> "$FRICTION_LOG"
  done
fi

exit 0

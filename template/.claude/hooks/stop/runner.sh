#!/bin/bash
# justinventit stop hook — check pipeline runner
# Runs all check scripts in order, aggregates results

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKS_DIR="$SCRIPT_DIR/checks"
ACTIONS_DIR="$SCRIPT_DIR/actions"
SKIP_FILE="$SCRIPT_DIR/skip"

# Collect skipped checks
SKIPPED=()
if [ -f "$SKIP_FILE" ]; then
  while IFS= read -r line; do
    SKIPPED+=("$line")
  done < "$SKIP_FILE"
fi

is_skipped() {
  local check_num="$1"
  for skip in "${SKIPPED[@]+"${SKIPPED[@]}"}"; do
    if [ "$skip" = "$check_num" ]; then
      return 0
    fi
  done
  return 1
}

# Run all checks in order
BLOCKED=false
BLOCK_MESSAGES=()

if [ -d "$CHECKS_DIR" ]; then
  for check in "$CHECKS_DIR"/[0-9]*.sh; do
    [ -f "$check" ] || continue

    # Extract check number (e.g., "01" from "01-tdd-gate.sh")
    CHECK_NUM=$(basename "$check" | grep -oP '^\d+')

    if is_skipped "$CHECK_NUM"; then
      continue
    fi

    # Run the check
    CHECK_OUTPUT=$("$check" 2>&1) || {
      BLOCKED=true
      BLOCK_MESSAGES+=("$CHECK_OUTPUT")
    }
  done
fi

# Run actions (discovery extraction, friction logging, etc.)
if [ -d "$ACTIONS_DIR" ]; then
  for action in "$ACTIONS_DIR"/*.sh; do
    [ -f "$action" ] || continue
    "$action" 2>/dev/null || true  # Actions don't block
  done
fi

# Report results
if [ "$BLOCKED" = true ]; then
  echo ""
  echo "=== STOP HOOK: BLOCKED ==="
  for msg in "${BLOCK_MESSAGES[@]}"; do
    echo "$msg"
  done
  echo "==========================="
  echo ""
  echo "Fix the issues above before ending the session."
  echo "To skip a check: echo 'NN' >> .claude/hooks/stop/skip"
  echo "To relax all checks: export JUSTINVENTIT_HOOK_MODE=relaxed"
  exit 2
fi

exit 0

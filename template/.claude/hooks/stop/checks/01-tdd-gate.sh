#!/bin/bash
# Check: TDD gate — scenarios must exist for standard+ scope
# Checks if modified files suggest standard+ scope but no SCENARIOS.md exists

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/utils.sh"

REPO_ROOT=$(get_repo_root)

# Count modified files in this session
MODIFIED_COUNT=$(git diff --name-only HEAD~1 2>/dev/null | wc -l | tr -d ' ')

# If fewer than 4 files, likely quick scope — pass
if [ "$MODIFIED_COUNT" -lt 4 ]; then
  exit 0
fi

# Check if any SCENARIOS.md exists in the active work directory
# This is a basic check — projects can customize with more specific logic
SCENARIOS_EXISTS=false
find "$REPO_ROOT/docs" -name "SCENARIOS.md" -newer "$REPO_ROOT/.git/refs/heads/$(git branch --show-current)" 2>/dev/null | head -1 | grep -q . && SCENARIOS_EXISTS=true

if [ "$SCENARIOS_EXISTS" = false ]; then
  report_check "block" "Standard+ scope detected ($MODIFIED_COUNT files changed) but no SCENARIOS.md found. Create scenarios before continuing."
  exit 1
fi

exit 0

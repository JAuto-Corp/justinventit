#!/bin/bash
# Shared utilities for justinventit hooks

# Get repository root (worktree-safe)
get_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || echo "."
}

# Get current timestamp in ISO 8601
get_timestamp() {
  date -u "+%Y-%m-%dT%H:%MZ"
}

# Check if we're in a worktree (not the main repo)
is_worktree() {
  local root
  root=$(get_repo_root)
  [ -f "$root/.supabase-branch.json" ] || \
    [ "$(git rev-parse --git-common-dir)" != "$(git rev-parse --git-dir)" ]
}

# Read a JSON field from .supabase-branch.json (if it exists)
get_branch_config() {
  local field="$1"
  local root
  root=$(get_repo_root)
  local config="$root/.supabase-branch.json"
  if [ -f "$config" ]; then
    python3 -c "import json; print(json.load(open('$config')).get('$field', ''))" 2>/dev/null
  fi
}

# Get the state directory (context/ relative to repo root)
get_state_dir() {
  echo "$(get_repo_root)/context"
}

# Get the docs directory
get_docs_dir() {
  echo "$(get_repo_root)/docs"
}

# Append an observation block to WORKING.md
append_working_block() {
  local phase="$1"
  local completed="$2"
  local next="$3"
  local blockers="${4:-none}"
  local working_file
  working_file="$(get_state_dir)/WORKING.md"

  cat >> "$working_file" << EOF

## $(get_timestamp)
Phase: ${phase}
Completed: ${completed}
Next: ${next}
Blockers: ${blockers}
EOF
}

# Check if a hook mode is set (relaxed, strict, etc.)
get_hook_mode() {
  echo "${JUSTINVENTIT_HOOK_MODE:-strict}"
}

# Report a check result. In relaxed mode, blocks become warnings.
report_check() {
  local status="$1"  # pass, warn, block
  local message="$2"

  if [ "$status" = "block" ] && [ "$(get_hook_mode)" = "relaxed" ]; then
    echo "WARN (relaxed): $message" >&2
    return 0
  fi

  if [ "$status" = "block" ]; then
    echo "BLOCK: $message" >&2
    return 1
  fi

  if [ "$status" = "warn" ]; then
    echo "WARN: $message" >&2
    return 0
  fi

  return 0
}

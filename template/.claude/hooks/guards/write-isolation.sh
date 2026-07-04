#!/bin/bash
#
# PreToolUse guard: write-isolation
# ---------------------------------------------------------------------------
# Blocks Write / Edit / MultiEdit / NotebookEdit whose target path resolves
# OUTSIDE the project (or worktree) root — i.e. CLAUDE_PROJECT_DIR. Agents can
# freely modify anything INSIDE their boundary, but cannot accidentally mutate
# files above it: parent dirs, sibling worktrees, /etc/*, ../ escapes, or any
# absolute path outside the tree.
#
# Ported from: customer-portal/.claude/hooks/pre-tool-write-guard.sh
# Faithful to cp's core mechanism (resolve target -> compare against
# CLAUDE_PROJECT_DIR -> exit 2 to block). Deliberate, justified divergences:
#   1. UNGATED / default-ON. cp only armed inside a worktree (keyed off the
#      domain marker .supabase-branch.json) and allowed everything in the main
#      repo. Here CLAUDE_PROJECT_DIR is the repo root even without worktrees,
#      so the guard is universally protective and carries NO domain content.
#   2. Reads the PreToolUse payload from STDIN (.tool_name + .tool_input) — the
#      current Claude Code contract — instead of the legacy CLAUDE_TOOL_INPUT
#      env var cp used.
#   3. Also covers MultiEdit (.file_path) and NotebookEdit (.notebook_path).
#   4. Boundary test is exact-root-or-root-slash (not a bare prefix), so a
#      sibling like "<root>-evil" is correctly treated as outside.
#
# Blocking convention (matches cp): exit 2 == block, exit 0 == allow. The block
# reason is emitted on BOTH channels — as {"decision":"block","reason":...} on
# stdout (cp parity) and as a plain message on stderr (the channel Claude Code
# surfaces to the agent on exit 2), so the boundary message always reaches it.
#
# Fail-open-safe: any missing / empty / unparseable payload, or a missing jq,
# results in ALLOW (exit 0). The guard must never crash or hard-error-block a
# legitimate write. (No `set -e` for exactly this reason.)
# ---------------------------------------------------------------------------

# Allowed root — set by Claude Code; fall back to CWD (matches cp).
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Read the PreToolUse JSON payload from stdin.
PAYLOAD="$(cat 2>/dev/null)"
[ -z "$PAYLOAD" ] && exit 0

# Need jq to parse; if unavailable, fail open (allow) rather than false-block.
command -v jq >/dev/null 2>&1 || exit 0

# Extract the target path. Write/Edit/MultiEdit use .file_path;
# NotebookEdit uses .notebook_path.
TARGET_PATH=$(printf '%s' "$PAYLOAD" \
  | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' 2>/dev/null)
[ -z "$TARGET_PATH" ] && exit 0

# Resolve relative paths against the project root (matches cp).
if [[ "$TARGET_PATH" != /* ]]; then
  TARGET_PATH="$PROJECT_DIR/$TARGET_PATH"
fi

# Normalize both paths (collapses .., resolves symlinks where possible).
TARGET_RESOLVED=$(realpath -m "$TARGET_PATH" 2>/dev/null || echo "$TARGET_PATH")
PROJECT_RESOLVED=$(realpath -m "$PROJECT_DIR" 2>/dev/null || echo "$PROJECT_DIR")

# Inside the boundary (root itself, or anything under root/) -> allow.
if [[ "$TARGET_RESOLVED" == "$PROJECT_RESOLVED" || "$TARGET_RESOLVED" == "$PROJECT_RESOLVED"/* ]]; then
  exit 0
fi

# OUTSIDE the boundary -> BLOCK.
TOOL_NAME=$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // "Write/Edit"' 2>/dev/null)

# stderr: the channel Claude Code shows the agent on a PreToolUse exit-2 block.
echo "WRITE ISOLATION: ${TOOL_NAME} targets a path OUTSIDE the project root and was blocked." >&2
echo "  Target:  ${TARGET_RESOLVED}" >&2
echo "  Allowed: ${PROJECT_RESOLVED} (and anything beneath it)" >&2
echo "  Write inside the project/worktree root, or ask the user if an out-of-boundary write is truly required." >&2

# stdout: structured block decision (cp parity).
cat << EOF
{
  "decision": "block",
  "reason": "WRITE ISOLATION: ${TOOL_NAME} targets a path OUTSIDE the project root and was blocked.\n\nTarget:  ${TARGET_RESOLVED}\nAllowed: ${PROJECT_RESOLVED} (and anything beneath it)\n\nYou may only write inside the project/worktree root. Move the target inside the root, or ask the user if an out-of-boundary write is genuinely required."
}
EOF

exit 2

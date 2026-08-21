#!/bin/bash
# Prove Claude and Codex consume one session-start implementation.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$HERE/../../.." && pwd)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/justinventit-session-start.XXXXXX")"
SANDBOX="$TMP_ROOT/project"

cleanup() { rm -rf "$TMP_ROOT"; }
trap cleanup EXIT INT TERM

PASS=0
FAIL=0

check() {
  local name="$1"
  shift
  if "$@"; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $name"
    FAIL=$((FAIL + 1))
  fi
}

mkdir -p \
  "$SANDBOX/.agents/hooks" \
  "$SANDBOX/.agents/hooks/lib" \
  "$SANDBOX/.claude/hooks/lib" \
  "$SANDBOX/context" \
  "$SANDBOX/docs" \
  "$SANDBOX/src/nested"

cp "$PROJECT_ROOT/.agents/hooks/session-start.sh" "$SANDBOX/.agents/hooks/session-start.sh"
cp "$PROJECT_ROOT/.agents/hooks/lib/utils.sh" "$SANDBOX/.agents/hooks/lib/utils.sh"
cp "$PROJECT_ROOT/.claude/hooks/session-start.sh" "$SANDBOX/.claude/hooks/session-start.sh"
cp "$PROJECT_ROOT/.claude/hooks/lib/utils.sh" "$SANDBOX/.claude/hooks/lib/utils.sh"
chmod +x "$SANDBOX/.agents/hooks/session-start.sh" "$SANDBOX/.claude/hooks/session-start.sh"

printf '%s\n' \
  '# Current Work' \
  '' \
  '## Active' \
  '- Runtime adapter acceptance' \
  '' \
  '## Later' > "$SANDBOX/docs/CURRENT_WORK.md"

printf '%s\n' \
  '# Working State' \
  '' \
  '## 2026-08-21T12:00Z' \
  'Phase: runtime adapter' \
  'Completed: shared hook source' \
  'Next: verify both runtime adapters' > "$SANDBOX/context/WORKING.md"

git -C "$SANDBOX" init -q -b adapter-test
git -C "$SANDBOX" config user.name "justinventit test"
git -C "$SANDBOX" config user.email "test@example.invalid"
git -C "$SANDBOX" add .
git -C "$SANDBOX" commit -qm "test fixture"

INPUT='{"session_id":"test-session","cwd":"src/nested","hook_event_name":"SessionStart","source":"startup","model":"test"}'
SHARED_OUT="$TMP_ROOT/shared.out"
CLAUDE_OUT="$TMP_ROOT/claude.out"
FRESH_SHARED_OUT="$TMP_ROOT/fresh-shared.out"
FRESH_CLAUDE_OUT="$TMP_ROOT/fresh-claude.out"

(cd "$SANDBOX/src/nested" && printf '%s' "$INPUT" | bash "$SANDBOX/.agents/hooks/session-start.sh") > "$SHARED_OUT"
(cd "$SANDBOX/src/nested" && printf '%s' "$INPUT" | bash "$SANDBOX/.claude/hooks/session-start.sh") > "$CLAUDE_OUT"

check "Claude wrapper is byte-equivalent to the shared hook" cmp -s "$SHARED_OUT" "$CLAUDE_OUT"
check "Claude utility adapter resolves the shared implementation" bash -c \
  "cd '$SANDBOX' && source '$SANDBOX/.claude/hooks/lib/utils.sh' && test \"\$(get_repo_root)\" = '$SANDBOX'"
check "nested cwd resolves the repository branch" grep -qF 'Branch: adapter-test (0 uncommitted files)' "$SHARED_OUT"
check "ordinary nested checkout is not labeled as an isolated worktree" bash -c \
  "! grep -qF 'Worktree:' '$SHARED_OUT'"
check "active work is included" grep -qF 'Runtime adapter acceptance' "$SHARED_OUT"
check "latest state is included" grep -qF 'Completed: shared hook source' "$SHARED_OUT"
check "session output remains concise" test "$(wc -c < "$SHARED_OUT")" -le 6000

# A freshly generated WORKING.md has instructions but no dated observation yet.
# SessionStart must still complete successfully and both adapters must agree.
printf '%s\n' \
  '# Working State' \
  '' \
  '> Append-only observation blocks.' \
  '' \
  '<!-- Append new entries below this line -->' > "$SANDBOX/context/WORKING.md"

SHARED_RC=0
CLAUDE_RC=0
(cd "$SANDBOX/src/nested" && printf '%s' "$INPUT" | bash "$SANDBOX/.agents/hooks/session-start.sh") \
  > "$FRESH_SHARED_OUT" || SHARED_RC=$?
(cd "$SANDBOX/src/nested" && printf '%s' "$INPUT" | bash "$SANDBOX/.claude/hooks/session-start.sh") \
  > "$FRESH_CLAUDE_OUT" || CLAUDE_RC=$?

check "fresh project shared hook exits cleanly" test "$SHARED_RC" -eq 0
check "fresh project Claude wrapper exits cleanly" test "$CLAUDE_RC" -eq 0
check "fresh project adapters remain byte-equivalent" cmp -s "$FRESH_SHARED_OUT" "$FRESH_CLAUDE_OUT"
check "fresh project session brief reaches its end marker" grep -qF '=== END ===' "$FRESH_SHARED_OUT"

LINKED_WORKTREE="$TMP_ROOT/linked-worktree"
git -C "$SANDBOX" worktree add -qb adapter-linked "$LINKED_WORKTREE"
check "real linked worktree is detected from an absolute Git-dir comparison" bash -c \
  "cd '$LINKED_WORKTREE' && source '$LINKED_WORKTREE/.agents/hooks/lib/utils.sh' && is_worktree"

echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
echo "================================"
[ "$FAIL" -eq 0 ]

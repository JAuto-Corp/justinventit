#!/bin/bash
# ===========================================================================
# Self-test: write-isolation PreToolUse guard  (guards/write-isolation.sh)
# ---------------------------------------------------------------------------
# Proves the generic harness end-to-end. The guard's contract:
#   * reads a PreToolUse JSON payload on STDIN (.tool_name / .tool_input)
#   * exit 0 = allow (target INSIDE CLAUDE_PROJECT_DIR)
#   * exit 2 = block (target OUTSIDE the root); reason on stderr + stdout JSON
#
# Each case runs in a fresh sandbox that the harness sets as CLAUDE_PROJECT_DIR,
# so "inside/outside the boundary" is exercised without any hardcoded path.
# Run: bash test-write-isolation.sh   (exit 0 = all pass, non-zero = failure)
# ===========================================================================

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

GUARD="$HERE/../guards/write-isolation.sh"
FIX="$HERE/fixtures"

# --- Trivial sanity: harness green path works (fixture hook, exit 0) ---------
run_case --name "sanity: trivial hook exits 0" \
  --hook "$FIX/sanity-exit0.sh" \
  --expect-exit 0 \
  --expect-out "sanity: ok" --channel stdout

# --- In-boundary write (relative path, from a static fixture) -> ALLOW --------
run_case --name "in-boundary relative Write -> allow (exit 0)" \
  --hook "$GUARD" \
  --stdin-file "$FIX/write-in-boundary.json" \
  --expect-exit 0

# --- In-boundary write (absolute path inside sandbox via token) -> ALLOW ------
run_case --name "in-boundary absolute Write -> allow (exit 0)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"Write","tool_input":{"file_path":"{{SANDBOX}}/sub/dir/file.md"}}' \
  --expect-exit 0

# --- Out-of-boundary write (/etc/passwd, from fixture) -> BLOCK ---------------
run_case --name "out-of-boundary /etc/passwd -> block (exit 2 + message)" \
  --hook "$GUARD" \
  --stdin-file "$FIX/write-out-boundary.json" \
  --expect-exit 2 \
  --expect-out "WRITE ISOLATION" \
  --channel stderr

# --- Out-of-boundary via ../ escape -> BLOCK ---------------------------------
run_case --name "out-of-boundary ../ escape -> block (exit 2)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"Edit","tool_input":{"file_path":"../escapes/evil.md"}}' \
  --expect-exit 2 \
  --expect-out "OUTSIDE the project root" \
  --channel stdout

# --- NotebookEdit outside boundary uses .notebook_path -> BLOCK --------------
run_case --name "NotebookEdit outside (notebook_path) -> block (exit 2)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"/tmp/not-mine.ipynb"}}' \
  --expect-exit 2

# --- Fail-open: empty STDIN must ALLOW (never crash a legit write) -----------
run_case --name "empty STDIN -> allow (fail-open, exit 0)" \
  --hook "$GUARD" \
  --stdin "" \
  --expect-exit 0

harness_summary
exit $?

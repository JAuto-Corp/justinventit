#!/bin/bash
# ===========================================================================
# justinventit — generic hook test harness
# ---------------------------------------------------------------------------
# A reusable, domain-free library for testing hook scripts (PreToolUse guards,
# Stop checks/actions) WITHOUT a live Claude session. A test defines a case:
#
#     (hook path, mock STDIN, env vars, optional state-file setup,
#      expected exit code, expected output substring on a channel)
#
# and the harness runs it, asserts exit-code AND output, tallies PASS/FAIL,
# and exits non-zero if ANY case fails (exit 0 = all pass).
#
# USE: source this file, call `run_case` per scenario, end with `harness_summary`.
#
#     source "$(dirname "${BASH_SOURCE[0]}")/harness.sh"
#     run_case --name "allowed" --hook "$GUARD" --stdin '...' --expect-exit 0
#     harness_summary; exit $?
#
# ---------------------------------------------------------------------------
# I/O contracts this harness supports (both framework hook shapes):
#
#   * PreToolUse guards  — JSON payload on STDIN (.tool_name/.tool_input);
#                          exit 2 = block, exit 0 = allow; reason on stderr
#                          and/or a {"decision":"block"} object on stdout.
#   * Stop checks/actions— read state/transcript; exit 0 = pass,
#                          non-zero = block/fail; message on stderr.
#
# Both reduce to the same testable primitives: feed STDIN + env + a seeded
# state dir, run the script, assert (exit code, output substring). The harness
# is agnostic to which shape a hook is — it only drives those primitives.
#
# ---------------------------------------------------------------------------
# STATE BACKUP / RESTORE (the safety contract):
#
# The harness NEVER mutates the real repo. Each case is given a fresh, private
# sandbox directory (mktemp -d) that becomes CLAUDE_PROJECT_DIR by default. Any
# state file a hook reads or writes is seeded INTO that sandbox via --setup, so
# every mutation lands on a disposable copy. A single `trap` removes the whole
# temp root on EXIT/INT/TERM — so state is torn down even on failure or Ctrl-C.
# This is the generic form of "back up + restore mutated state": originals are
# never touched, so there is nothing to restore.
#
# PORTABILITY: bash, jq assumed available (as the rest of the framework does).
# No hardcoded absolute paths — everything derives from a temp dir. No `set -e`
# (a failing assertion must tally, not abort the run).
# ===========================================================================

set -uo pipefail

# --- Temp root for this harness invocation (all sandboxes live under it) -----
HARNESS_TMP="$(mktemp -d "${TMPDIR:-/tmp}/justinventit-hooktest.XXXXXX")"

_harness_cleanup() { [ -n "${HARNESS_TMP:-}" ] && rm -rf "$HARNESS_TMP"; }
trap _harness_cleanup EXIT INT TERM

# --- Tally state -------------------------------------------------------------
_HARNESS_PASS=0
_HARNESS_FAIL=0
_HARNESS_FAILED=()

_pass() { _HARNESS_PASS=$((_HARNESS_PASS + 1)); echo "PASS: $1"; }
_fail() {
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1))
  _HARNESS_FAILED+=("$1")
  echo "FAIL: $1"
  [ -n "${2:-}" ] && printf '      %s\n' "$2"
}

# Replace the {{SANDBOX}} token with the case's sandbox path. Lets a case
# reference an absolute in-boundary path in STDIN / env before the sandbox
# exists at call time. Relative paths need no token (resolved vs CLAUDE_PROJECT_DIR).
_subst_sandbox() { printf '%s' "${1//\{\{SANDBOX\}\}/$2}"; }

# ---------------------------------------------------------------------------
# run_case — define + execute one test case.
#
# Flags (all optional except --name, --hook, --expect-exit):
#   --name        <str>   human label for the case
#   --hook        <path>  hook script to run (absolute, or relative to CWD)
#   --stdin       <str>   literal string piped to the hook's STDIN
#   --stdin-file  <path>  file whose contents are piped to STDIN (fixture)
#   --env         <K=V>   extra env var for the hook (repeatable)
#   --setup       <shell> shell run INSIDE the sandbox before the hook
#                         (seed state files, `git init`, etc.)
#   --expect-exit <int>   required exit code
#   --expect-out  <str>   substring that must appear in output (fixed-string)
#   --channel     <ch>    where --expect-out must appear: stdout|stderr|any
#                         (default: any = stdout+stderr combined)
#
# Environment provided to the hook:
#   CLAUDE_PROJECT_DIR defaults to the case sandbox (override via --env).
#   CASE_SANDBOX is exported for --setup. The token {{SANDBOX}} in --stdin and
#   --env values (and in --stdin-file contents) expands to the sandbox path.
# ---------------------------------------------------------------------------
run_case() {
  local name="" hook="" stdin="" stdin_is_file="" setup=""
  local expect_exit="0" expect_out="" channel="any"
  local -a xenv=()

  while [ $# -gt 0 ]; do
    case "$1" in
      --name)        name="$2";        shift 2 ;;
      --hook)        hook="$2";        shift 2 ;;
      --stdin)       stdin="$2"; stdin_is_file=""; shift 2 ;;
      --stdin-file)  stdin="$2"; stdin_is_file="1"; shift 2 ;;
      --env)         xenv+=("$2");     shift 2 ;;
      --setup)       setup="$2";       shift 2 ;;
      --expect-exit) expect_exit="$2"; shift 2 ;;
      --expect-out)  expect_out="$2";  shift 2 ;;
      --channel)     channel="$2";     shift 2 ;;
      *) echo "run_case: unknown flag '$1'" >&2; return 2 ;;
    esac
  done

  [ -n "$name" ] || { echo "run_case: --name required" >&2; return 2; }
  if [ ! -f "$hook" ]; then
    _fail "$name" "hook not found: $hook"
    return
  fi

  # Fresh per-case sandbox (isolated, disposable).
  local sandbox
  sandbox="$(mktemp -d "$HARNESS_TMP/case.XXXXXX")"
  export CASE_SANDBOX="$sandbox"

  # Resolve STDIN payload + expand the {{SANDBOX}} token.
  local payload=""
  if [ -n "$stdin_is_file" ]; then
    if [ ! -f "$stdin" ]; then
      _fail "$name" "stdin fixture not found: $stdin"
      return
    fi
    payload="$(cat "$stdin")"
  else
    payload="$stdin"
  fi
  payload="$(_subst_sandbox "$payload" "$sandbox")"

  # Optional state-file setup, run inside the sandbox.
  if [ -n "$setup" ]; then
    if ! ( cd "$sandbox" && eval "$setup" ) >/dev/null 2>&1; then
      _fail "$name" "--setup failed"
      return
    fi
  fi

  # Build the env list: CLAUDE_PROJECT_DIR defaults to sandbox; case --env
  # entries follow (and thus override), with {{SANDBOX}} expanded.
  local -a envs=("CLAUDE_PROJECT_DIR=$sandbox")
  local e
  for e in "${xenv[@]+"${xenv[@]}"}"; do
    envs+=("$(_subst_sandbox "$e" "$sandbox")")
  done

  # Run the hook: seeded env, mocked STDIN, captured stdout/stderr + exit code.
  local out_f="$sandbox/.stdout" err_f="$sandbox/.stderr" rc
  ( cd "$sandbox"; env "${envs[@]}" bash "$hook" ) \
      >"$out_f" 2>"$err_f" <<<"$payload"
  rc=$?

  # --- Assert exit code -----------------------------------------------------
  local why=""
  if [ "$rc" != "$expect_exit" ]; then
    why="exit $rc, expected $expect_exit"
  fi

  # --- Assert output substring on the chosen channel ------------------------
  if [ -z "$why" ] && [ -n "$expect_out" ]; then
    local hay
    case "$channel" in
      stdout) hay="$(cat "$out_f")" ;;
      stderr) hay="$(cat "$err_f")" ;;
      any|*)  hay="$(cat "$out_f" "$err_f")" ;;
    esac
    if ! printf '%s' "$hay" | grep -qF -- "$expect_out"; then
      why="missing substring on $channel: '$expect_out'"
    fi
  fi

  if [ -n "$why" ]; then
    _fail "$name" "$why"
    # Show captured output to aid debugging.
    printf '      --- stdout ---\n'; sed 's/^/      /' "$out_f" | head -8
    printf '      --- stderr ---\n'; sed 's/^/      /' "$err_f" | head -8
  else
    _pass "$name"
  fi
}

# ---------------------------------------------------------------------------
# harness_summary — print the tally; return 1 if any case failed, else 0.
# ---------------------------------------------------------------------------
harness_summary() {
  echo ""
  echo "================================"
  echo "Results: $_HARNESS_PASS passed, $_HARNESS_FAIL failed"
  if [ "$_HARNESS_FAIL" -gt 0 ]; then
    local n
    for n in "${_HARNESS_FAILED[@]}"; do echo "  - FAILED: $n"; done
  fi
  echo "================================"
  [ "$_HARNESS_FAIL" -eq 0 ]
}

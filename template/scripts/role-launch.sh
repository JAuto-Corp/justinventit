#!/usr/bin/env bash
# Record-authoritative launch; origins and intentional differences: CLUSTER_PROVENANCE.md.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
fail() { printf 'ERROR (launch): %s\n' "$*" >&2; exit 2; }
for cmd in python3 node jq flock realpath; do
  command -v "$cmd" >/dev/null 2>&1 || fail "required executable missing: $cmd"
done
for rel in lib/jv-project.sh lib/codex-seat.sh validate-seat-record.mjs ../docs/seat-record.schema.json; do
  [[ -f "$SCRIPT_DIR/$rel" ]] || fail "missing launcher dependency: $rel"
done
source "$SCRIPT_DIR/lib/jv-project.sh"
_jv_project_configure
[[ $# -gt 0 && "$1" =~ ^[A-Z]$ ]] || fail 'usage: role-launch.sh LETTER [--worktree PATH] [--fresh] [--runtime claude|codex --model MODEL [--tier thinking|doing]] [--at-machine]'
LETTER="$1"; shift
LETTER_LC="${LETTER,,}"
FRESH=0; AT_MACHINE=0; BOOTSTRAP=0
RUNTIME_ARG=''; MODEL_ARG=''; TIER_ARG=thinking; WORKTREE=''
while (( $# )); do
  case "$1" in
    --fresh) FRESH=1; shift ;;
    --at-machine) AT_MACHINE=1; shift ;;
    --worktree|--runtime|--model|--tier)
      (( $# >= 2 )) || fail "missing value for $1"
      case "$1" in
        --worktree) WORKTREE="$2" ;;
        --runtime) RUNTIME_ARG="$2"; BOOTSTRAP=1 ;;
        --model) MODEL_ARG="$2"; BOOTSTRAP=1 ;;
        --tier) TIER_ARG="$2"; BOOTSTRAP=1 ;;
      esac
      shift 2 ;;
    *) fail "unknown argument: $1" ;;
  esac
done
if [[ -z "$WORKTREE" ]]; then
  case "$LETTER" in O|I) WORKTREE="$JV_PROJECT_ROOT" ;; *) fail 'this letter requires --worktree PATH' ;; esac
fi
[[ -d "$WORKTREE" ]] || fail 'worktree must be an existing directory'
WORKTREE="$(cd -P -- "$WORKTREE" && pwd -P)"
SEAT_NAME="$JV_PROJECT_ID-$LETTER_LC"
export JV_PROJECT_ID JV_PROJECT_ROOT JV_STATE_ROOT
export JV_ROLE="$LETTER"
_jv_init_store sessions
SESSIONS_DIR="$JV_STORE/sessions"
SEAT_RECORD="$SESSIONS_DIR/$LETTER_LC.json"
_jv_check_state_paths
exec 201>>"$SEAT_RECORD.lock"
flock -x 201 || fail 'cannot acquire seat record lock'
# The decision and every dispatch remain inside this checked lock, through exit.
_jv_check_state_paths
VALIDATOR="$SCRIPT_DIR/validate-seat-record.mjs"
TEMP_FILES=()
trap 'for tmp in "${TEMP_FILES[@]}"; do rm -f -- "$tmp"; done' EXIT
read_seat_record_snapshot() {
  local snapshot tuple
  snapshot="$(mktemp)" || fail 'cannot prepare record snapshot'
  TEMP_FILES+=("$snapshot")
  # Open the authoritative pathname ONCE. Validation and tuple extraction below
  # consume only this private byte image, including during a pathname replacement.
  python3 - "$1" "$snapshot" <<'PY' || fail 'cannot read seat record snapshot'
import sys
with open(sys.argv[1], 'rb') as src:
    data = src.read()
with open(sys.argv[2], 'wb') as dst:
    dst.write(data)
PY
  node "$VALIDATOR" "$snapshot" >/dev/null || fail 'seat record schema validation failed'
  tuple="$(mktemp)" || fail 'cannot prepare record tuple'
  TEMP_FILES+=("$tuple")
  python3 - "$snapshot" "$JV_PROJECT_ID" "$LETTER_LC" "$WORKTREE" >"$tuple" <<'PY' || fail 'invalid seat record binding or tuple'
import json, sys
with open(sys.argv[1]) as src:
    rec = json.load(src)
for key, expected in zip(('project_id', 'letter', 'workdir'), sys.argv[2:]):
    if rec.get(key) != expected:
        sys.exit('seat record '+key+' does not match configured identity/workdir')
values = [rec.get(k) for k in ('runtime', 'model', 'effort')]
if any(not isinstance(v, str) or not v or '\0' in v for v in values):
    sys.exit('seat record requires a nonempty NUL-free runtime/model/effort tuple')
if values[0] not in ('claude', 'codex') or values[2] not in ('xhigh', 'medium'):
    sys.exit('unsupported seat record runtime/effort')
for value in values:
    sys.stdout.buffer.write(value.encode('utf-8') + b'\0')
PY
  local -a fields=()
  mapfile -d '' -t fields < "$tuple"
  [[ ${#fields[@]} == 3 ]] || fail 'incomplete seat record tuple'
  RUNTIME="${fields[0]}"; SEAT_MODEL="${fields[1]}"; SEAT_EFFORT="${fields[2]}"
}
if [[ -e "$SEAT_RECORD" ]]; then
  [[ -f "$SEAT_RECORD" ]] || fail 'seat record must be a regular file'
  (( ! BOOTSTRAP )) || fail 'record exists; bootstrap flags cannot override it'
else
  [[ "$RUNTIME_ARG" == claude || "$RUNTIME_ARG" == codex ]] || fail 'bootstrap requires --runtime claude|codex'
  [[ -n "$MODEL_ARG" ]] || fail 'bootstrap requires a nonempty --model'
  case "$TIER_ARG" in thinking) EFFORT_ARG=xhigh ;; doing) EFFORT_ARG=medium ;; *) fail 'unsupported bootstrap tier' ;; esac
  CANDIDATE="$(mktemp "$SESSIONS_DIR/.candidate.XXXXXXXX")" || fail 'cannot write seat record candidate'
  TEMP_FILES+=("$CANDIDATE")
  python3 - "$CANDIDATE" "$JV_PROJECT_ID" "$LETTER_LC" "$WORKTREE" "$RUNTIME_ARG" "$MODEL_ARG" "$EFFORT_ARG" <<'PY' || fail 'cannot write seat record candidate'
import json, sys
path, project, letter, workdir, runtime, model, effort = sys.argv[1:]
with open(path, 'w') as dst:
    json.dump({'schema_version': 1, 'project_id': project, 'letter': letter,
               'runtime': runtime, 'model': model, 'effort': effort, 'workdir': workdir,
               'session_handle': None, 'state': 'booted', 'capabilities': {},
               'lease': {'holder': None, 'epoch': 0, 'expires_at': None},
               'watcher': {'location': None, 'generation': 0}}, dst, indent=2)
    dst.write('\n')
PY
  node "$VALIDATOR" "$CANDIDATE" >/dev/null || fail 'candidate record schema validation failed'
  mv -T -- "$CANDIDATE" "$SEAT_RECORD" || fail 'cannot publish seat record'
fi
read_seat_record_snapshot "$SEAT_RECORD"
if [[ "$RUNTIME" == "claude" ]] && ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: 'claude' CLI not found on PATH" >&2
  exit 1
fi

# ===========================================================================
# CODEX RUNTIME BRANCH (record-authoritative launch/resume)
# ===========================================================================
if [[ "$RUNTIME" == "codex" ]]; then
  # shellcheck source=lib/codex-seat.sh
  source "$SCRIPT_DIR/lib/codex-seat.sh"

  codex_seat_resolve_bin || exit 1

  # THE RECORD IS THE AUTHORITY for what this seat must run at; the launcher does not carry
  # its own table of tiers to disagree with. Profile name is project-qualified so two
  # consuming projects sharing one CODEX_HOME never collide (§3), and the profile is
  # SELECTED by the record's effort rather than stored separately — one source of truth.
  WANT_MODEL="$SEAT_MODEL"
  WANT_EFFORT="$SEAT_EFFORT"
  case "$SEAT_EFFORT" in
    xhigh)  SEAT_TIER="thinking" ;;
    medium) SEAT_TIER="doing"    ;;
    *) echo "ERROR: no Codex profile is defined for effort '$SEAT_EFFORT'." >&2
       echo "  Profiles exist for xhigh (thinking) and medium (doing). Add one, or correct" >&2
       echo "  the record — the launcher will not silently substitute a tier." >&2
       exit 1 ;;
  esac
  CODEX_PROFILE="$JV_PROJECT_ID-$SEAT_TIER"

  # The Claude branch creates this directory; a Codex-only setup never reaches that line,
  # so the post-exit thread-name write would fail under `set -e` and silently cost the seat
  # its resumable state.
  mkdir -p "$SESSIONS_DIR"
  CODEX_STATE_FILE="$SESSIONS_DIR/$LETTER.codex-thread"
  BRANCH="$(git -C "$WORKTREE" branch --show-current 2>/dev/null || echo '?')"

  echo "==============================================================="
  echo " Role:          $LETTER  (runtime: codex)"
  echo " Worktree:      $WORKTREE"
  echo " Branch:        $BRANCH"
  echo " Profile:       $CODEX_PROFILE"
  echo " Intended tier: $WANT_MODEL / $WANT_EFFORT"
  echo " Binary:        $CODEX_BIN ($CODEX_VERSION)"
  echo " Thread file:   $CODEX_STATE_FILE"
  echo "==============================================================="
  echo

  # Gate 1 — trust. An untrusted workdir silently no-ops its .codex/ layer.
  codex_seat_verify_trust "$WORKTREE" || exit 1

  # Gate 2 — tier. MANDATORY: --profile alone proves nothing (a nonexistent profile boots
  # the default tier at exit 0, no warning). This costs one throwaway exec turn and is the
  # only thing standing between a typo and a silently mis-tiered seat.
  codex_seat_verify_tier "$CODEX_PROFILE" "$WANT_MODEL" "$WANT_EFFORT" "$WORKTREE" || exit 1

  # Gate 3 — resume modal policy. Only applies when we are actually resuming.
  CODEX_RESUME=0
  if (( ! FRESH )) && [[ -s "$CODEX_STATE_FILE" ]]; then
    CODEX_THREAD="$(<"$CODEX_STATE_FILE")"
    if [[ -n "$CODEX_THREAD" ]]; then
      [[ "$CODEX_THREAD" == "$SEAT_NAME" ]] || _jv_fail "saved Codex thread name does not match project seat"
      codex_seat_resume_guard "$LETTER_LC" "$AT_MACHINE" || exit 1
      CODEX_RESUME=1
    fi
  fi

  cd "$WORKTREE"
  export JV_ROLE="$LETTER"

  echo
  if (( CODEX_RESUME )); then
    echo "Resuming Codex thread '$CODEX_THREAD'. Answer the resume modal promptly —"
    echo "while it is unanswered the seat takes NO turns and looks entirely healthy."
  else
    echo "New Codex session. FIRST ACTION IN THE TUI: /rename $SEAT_NAME"
    echo "The thread name is how this seat is resumed and it is an intended name, not an observed thread UUID;"
    echo "an unnamed thread is only reachable through the session picker."
    echo "Then push the role-template boot prompt (codex takes no positional boot prompt):"
    echo "  $SCRIPT_DIR/boot-role.sh $LETTER"
  fi
  echo

  LAUNCH_EPOCH="$(date +%s)"

  EXIT_CODE=0
  if (( CODEX_RESUME )); then
    "$CODEX_BIN" resume "$CODEX_THREAD" --profile "$CODEX_PROFILE" || EXIT_CODE=$?
  else
    "$CODEX_BIN" --profile "$CODEX_PROFILE" || EXIT_CODE=$?
  fi

  echo
  echo "--- codex session for role $LETTER ended (exit $EXIT_CODE) ---"

  # Record the thread name we INSTRUCTED, flagged as unverified: /rename happens inside the
  # TUI and the launcher cannot observe it. Claiming a verified name here would be exactly
  # the plausible-looking fiction this fleet keeps getting bitten by.
  if (( ! CODEX_RESUME )); then
    printf '%s\n' "$SEAT_NAME" > "$CODEX_STATE_FILE"
    echo "Thread name recorded as '$SEAT_NAME' (INTENDED, not verified — depends on /rename"
    echo "having been run). If resume fails to find it, the rename did not happen."
  fi

  # Post-exit reconciliation: what the session ACTUALLY ran at, from its own rollout.
  # Bound to THIS session by workdir + launch time. The previous global-newest-by-mtime
  # lookup could reconcile against an unrelated Codex session that happened to run at the
  # expected tier — reporting a clean tier for a seat that produced no evidence at all.
  RECONCILE_RC=0
  ROLLOUT_AFTER="$(codex_seat__rollout_for_session "$WORKTREE" "$LAUNCH_EPOCH")"
  if [[ -n "$ROLLOUT_AFTER" ]]; then
    codex_seat_reconcile_tier "$ROLLOUT_AFTER" "$WANT_MODEL" "$WANT_EFFORT" || RECONCILE_RC=$?
  else
    echo "tier recheck  NO EVIDENCE — no rollout uniquely attributable to this session"
    RECONCILE_RC=2
  fi

  case "$EXIT_CODE" in
    0|130|137|143) : ;;
    *)
      echo "Unexpected exit ($EXIT_CODE) — pane held for forensics. Press Enter to close."
      read -r _ || true
      ;;
  esac

  # Exit status carries the outcome. A supervisor reading only the status must not see a
  # tier mismatch or an abnormal codex death as a clean launch.
  #   exit 0  — codex ended normally or by a PLANNED signal, and the tier reconciled
  #   exit 4  — TIER MISMATCH: the seat ran at a tier nobody asked for
  #   exit 5  — codex ended cleanly but produced NO attributable evidence AND was not a
  #             planned teardown — we cannot say what tier it ran at
  #   exit $EXIT_CODE — codex itself failed or was killed abnormally
  #
  # 137 (SIGKILL, e.g. the OOM killer) is NOT in the planned set. It was previously grouped
  # with the clean exits because the Claude branch treats it as a pane-teardown signal, but
  # an OOM-killed seat is precisely the abnormal death a supervisor must be able to see.
  # 130 (SIGINT) and 143 (SIGTERM) remain planned teardowns.
  if (( RECONCILE_RC == 1 )); then
    echo "EXITING NONZERO: tier mismatch — this launch is not a clean seat." >&2
    exit 4
  fi
  case "$EXIT_CODE" in
    0|130|143)
      # A seat booted and closed without being given work legitimately takes no turns, so
      # no-evidence after a PLANNED teardown is normal and stays exit 0. No-evidence after
      # a plain exit 0 is reported as unverified rather than passed off as reconciled.
      if (( RECONCILE_RC == 2 && EXIT_CODE == 0 )); then
        echo "EXITING 5: no rollout attributable to this session — nothing observed post-boot." >&2
        echo "  (The PRE-boot probe still verified the profile's resolved tier; this is the" >&2
        echo "   weaker post-exit observation, which is advisory in the passing direction.)" >&2
        exit 5
      fi
      exit 0
      ;;
    *) exit "$EXIT_CODE" ;;
  esac
fi

# ===========================================================================
# CLAUDE RUNTIME BRANCH (unchanged behaviour)
# ===========================================================================

# Compute claude's project storage path for this worktree. Claude stores
# sessions at ~/.claude/projects/<sanitized-cwd>/<uuid>.jsonl, where the
# sanitizer is "replace each / with -".
SANITIZED="${WORKTREE//\//-}"
CLAUDE_PROJECT_DIR="$HOME/.claude/projects/$SANITIZED"

# State file ensures the role's session ID is known across crashes.
mkdir -p "$SESSIONS_DIR"
STATE_FILE="$SESSIONS_DIR/$LETTER.id"

new_uuid() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen
  else
    cat /proc/sys/kernel/random/uuid
  fi
}

# Determine session-attach mode.
SESSION_FLAGS=()
SESSION_MODE=""

if (( FRESH )); then
  SESSION_ID="$(new_uuid)"
  echo "$SESSION_ID" > "$STATE_FILE"
  SESSION_FLAGS=(--session-id "$SESSION_ID")
  SESSION_MODE="fresh (--fresh) — new UUID $SESSION_ID"
elif [[ -s "$STATE_FILE" ]]; then
  PRIOR_ID="$(<"$STATE_FILE")"
  [[ "$PRIOR_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] || _jv_fail "invalid saved Claude UUID"
  if [[ -n "$PRIOR_ID" && -f "$CLAUDE_PROJECT_DIR/$PRIOR_ID.jsonl" ]]; then
    SESSION_FLAGS=(--resume "$PRIOR_ID")
    SESSION_MODE="resume — $PRIOR_ID"
  else
    SESSION_ID="$(new_uuid)"
    echo "$SESSION_ID" > "$STATE_FILE"
    SESSION_FLAGS=(--session-id "$SESSION_ID")
    SESSION_MODE="fresh (prior session ${PRIOR_ID:-<empty>} gone) — new UUID $SESSION_ID"
  fi
else
  SESSION_ID="$(new_uuid)"
  echo "$SESSION_ID" > "$STATE_FILE"
  SESSION_FLAGS=(--session-id "$SESSION_ID")
  SESSION_MODE="initial — new UUID $SESSION_ID"
fi

# Current branch (informational only — claude inherits whatever's checked out).
BRANCH="$(git -C "$WORKTREE" branch --show-current 2>/dev/null || echo '?')"

ROLE_MODEL="$SEAT_MODEL"
ROLE_EFFORT="$SEAT_EFFORT"

echo "==============================================================="
echo " Role:          $LETTER"
echo " Worktree:      $WORKTREE"
echo " Branch:        $BRANCH"
echo " Session name:  $SEAT_NAME"
echo " Remote ctrl:   $SEAT_NAME"
echo " Model/effort:  $ROLE_MODEL / $ROLE_EFFORT"
echo " State file:    $STATE_FILE"
echo " Session mode:  $SESSION_MODE"
echo "==============================================================="
echo
case "$SESSION_MODE" in
  fresh*|initial*)
    echo "New session — push the role-template boot prompt via Remote Control"
    echo "once the TUI loads. Get the template with:"
    echo "  $SCRIPT_DIR/boot-role.sh $LETTER"
    echo
    ;;
esac

cd "$WORKTREE"

export JV_ROLE="$LETTER"

EXIT_CODE=0
claude \
  -n "$SEAT_NAME" \
  --remote-control "$SEAT_NAME" \
  --effort "$ROLE_EFFORT" \
  --model "$ROLE_MODEL" \
  --add-dir "$WORKTREE" \
  "${SESSION_FLAGS[@]}" || EXIT_CODE=$?

echo
echo "--- claude session for role $LETTER ended (exit $EXIT_CODE) ---"
echo "State file still holds: $(cat "$STATE_FILE" 2>/dev/null || echo '<none>')"

# Pane lifecycle. Windows Terminal's closeOnExit=automatic closes a tab only
# when its root process exits 0. A planned teardown (claude SIGTERM->143,
# SIGINT->130, SIGKILL->137) or a clean exit (0) therefore self-closes the
# tab — no leftover [process exited] pane after a role cutover. An unexpected
# crash holds the pane open for a forensic trail.
case "$EXIT_CODE" in
  0|130|137|143) : ;;
  *)
    echo "Unexpected exit ($EXIT_CODE) — pane held for forensics. Press Enter to close."
    read -r _ || true
    ;;
esac
exit 0

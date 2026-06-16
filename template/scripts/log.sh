#!/usr/bin/env bash
# log.sh — the dev-log primitive (M0 DEV-LOG layer / generalized Orchestration Hub).
#
# ONE append command that records dev-log events as an APPEND-ONLY event stream,
# with DERIVED current-state views computed on read (never a mutable state file
# that drifts write-only — that is the lesson of the 1.2MB STATE.md and the dead
# #2249 tables: recording must be cheaper than not-recording).
#
# The spine is the THREAD: every event links to one thread_id. Threads are the
# unit of coherence — "where did I leave everything" resolves to open threads +
# their pending gates + blocked-on-user items.
#
# AUTO vs MANUAL (the round-table cut):
#   AUTO   — ts, event id, last_event_at (derived), links, actor
#   MANUAL — intent_anchor (a QUOTED source), decision text, state, the human call
#
# RECORD-AS-BYPRODUCT: the SAME call, when orchestration_tier=cluster, ALSO emits
# the mailbox message (transport is a side-effect of recording — log once, the
# coordination tier rides along). At solo it just appends. This is finding #2:
# one action both transports and records, so recording is never extra work.
#
# Usage:
#   log.sh thread   <thread_id> "<title>" [--intent "<quoted source>"] [--anchor-src <ref>]
#   log.sh decision <thread_id> "<decision text>" [--anchor "<quoted source>"]
#   log.sh action   <thread_id> "<action>" [--for user|self|<role>] [--urgency now|soon|whenever] [--unblocks "<why>"]
#   log.sh finding  <thread_id> "<finding>" [--severity high|med|low] [--class <tag>]
#   log.sh done      <thread_id> [--ref <id>]                 # close a thread / resolve a gate or action by event id
#   log.sh gate      <thread_id> "<what is gated>" [--on user|ci|<role>]   # an open gate awaiting something
#   log.sh note      <thread_id> "<free text>"                # a plain narrative event on a thread
#
#   log.sh view threads        # open threads (spine) with last_event_at + staleness
#   log.sh view gates          # pending gates (open, not resolved)
#   log.sh view user-actions   # blocked-on-user queue (the highest-ROI artifact)
#   log.sh view thread <id>    # full event history for one thread
#
# Cross-cutting flags (any subcommand):
#   --to <recipient>    cluster-mode mailbox recipient (defaults broadcast 'all')
#   --actor <name>      override actor (default: $DEVLOG_ACTOR or 'me')
#   --json              emit the appended event JSON to stdout (for piping/tests)
#
# DATA LOCATION (decision f): defaults in-repo at context/devlog/ — the N=1
# coherence anchor, git-tracked structure but gitignored data. Relocatable to a
# shared ~ path for cluster + multi-worktree via DEVLOG_DIR (so cross-worktree
# sessions share one stream). Either way it is excluded from `copier update`.

set -euo pipefail

# --- locate the event stream ---------------------------------------------------
repo_root() { git rev-parse --show-toplevel 2>/dev/null || pwd; }

# DEVLOG_DIR override = relocate to ~ for cluster/multi-worktree (decision f).
DEVLOG_DIR="${DEVLOG_DIR:-$(repo_root)/context/devlog}"
EVENTS="$DEVLOG_DIR/events.jsonl"
mkdir -p "$DEVLOG_DIR"
[ -f "$EVENTS" ] || : > "$EVENTS"

# orchestration_tier: solo (default) = append only; cluster = also emit mailbox.
ORCH_TIER="${ORCHESTRATION_TIER:-solo}"
# Mailbox transport command (generalizes scripts/msg.sh). Cluster-mode only.
MSG_CMD="${DEVLOG_MSG_CMD:-}"   # e.g. "scripts/msg.sh" — if empty, falls back to a file drop.
MAILBOX_DIR="${DEVLOG_MAILBOX_DIR:-$DEVLOG_DIR/outbox}"

ACTOR="${DEVLOG_ACTOR:-me}"
now() { date -u "+%Y-%m-%dT%H:%M:%SZ"; }

# --- minimal JSON helpers (no jq dependency for WRITE; reads degrade if absent) -
have_jq() { command -v jq >/dev/null 2>&1; }

# Escape a string for embedding in JSON.
json_str() {
  if have_jq; then jq -Rn --arg s "$1" '$s'; else
    local s="$1"; s="${s//\\/\\\\}"; s="${s//\"/\\\"}"
    s="${s//	/\\t}"; printf '"%s"' "${s//$'\n'/\\n}"
  fi
}

# Append one event object (already-formed inner key/values string) to the stream.
emit_event() {
  local etype="$1"; local thread="$2"; local inner="$3"
  local id="${etype}-$(date -u +%s)-$RANDOM"
  local obj
  obj=$(printf '{"id":%s,"ts":%s,"type":%s,"thread_id":%s,"actor":%s%s}' \
    "$(json_str "$id")" "$(json_str "$(now)")" "$(json_str "$etype")" \
    "$(json_str "$thread")" "$(json_str "$ACTOR")" \
    "${inner:+,$inner}")
  printf '%s\n' "$obj" >> "$EVENTS"
  EMITTED_OBJ="$obj"
  EMITTED_ID="$id"
}

# RECORD-AS-BYPRODUCT: in cluster-mode the same call transports via the mailbox.
maybe_transport() {
  [ "$ORCH_TIER" = "cluster" ] || return 0
  local to="${1:-all}"; local subject="$2"; local body="$3"
  if [ -n "$MSG_CMD" ]; then
    # Generalizes `msg.sh send <from> <to> <subject> <body>` (from-first direction).
    $MSG_CMD send "$ACTOR" "$to" "$subject" "$body" >/dev/null 2>&1 \
      || echo "log.sh: warn: mailbox transport failed (event still recorded)" >&2
  else
    # Portable fallback: drop a message file the coordination tier can drain.
    mkdir -p "$MAILBOX_DIR"
    printf '%s\n' "$(printf '{"ts":%s,"from":%s,"to":%s,"subject":%s,"body":%s}' \
      "$(json_str "$(now)")" "$(json_str "$ACTOR")" "$(json_str "$to")" \
      "$(json_str "$subject")" "$(json_str "$body")")" \
      >> "$MAILBOX_DIR/to-${to}.jsonl"
  fi
}

# --- flag parsing --------------------------------------------------------------
EMIT_JSON=false; TO_RECIP="all"
declare -A OPT=()
parse_flags() {
  REST=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --json)      EMIT_JSON=true; shift ;;
      --to)        TO_RECIP="$2"; shift 2 ;;
      --actor)     ACTOR="$2"; shift 2 ;;
      --intent)    OPT[intent_anchor]="$2"; shift 2 ;;
      --anchor)    OPT[intent_anchor]="$2"; shift 2 ;;
      --anchor-src) OPT[anchor_src]="$2"; shift 2 ;;
      --for)       OPT[for]="$2"; shift 2 ;;
      --urgency)   OPT[urgency]="$2"; shift 2 ;;
      --unblocks)  OPT[unblocks]="$2"; shift 2 ;;
      --severity)  OPT[severity]="$2"; shift 2 ;;
      --class)     OPT[class]="$2"; shift 2 ;;
      --on)        OPT[gated_on]="$2"; shift 2 ;;
      --ref)       OPT[ref]="$2"; shift 2 ;;
      --*)         echo "log.sh: unknown flag $1" >&2; exit 2 ;;
      *)           REST+=("$1"); shift ;;
    esac
  done
}

# Build the inner JSON fragment from collected OPT[] keys (+ explicit extras).
build_inner() {
  local frag=""
  for k in "$@"; do
    [ -n "${OPT[$k]:-}" ] || continue
    frag+="${frag:+,}$(json_str "$k"):$(json_str "${OPT[$k]}")"
  done
  printf '%s' "$frag"
}

finish() {
  if [ "$EMIT_JSON" = true ]; then printf '%s\n' "$EMITTED_OBJ"
  else echo "logged ${EMITTED_ID}"; fi
}

# --- subcommands ---------------------------------------------------------------
cmd="${1:-}"; shift || true

case "$cmd" in
  thread)
    parse_flags "$@"
    tid="${REST[0]:?thread <thread_id> <title>}"; title="${REST[1]:?title required}"
    inner="$(json_str "title"):$(json_str "$title")"
    extra="$(build_inner intent_anchor anchor_src)"; inner+="${extra:+,$extra}"
    emit_event "thread" "$tid" "$inner"
    maybe_transport "$TO_RECIP" "[THREAD] $tid" "$title"
    finish ;;

  decision)
    parse_flags "$@"
    tid="${REST[0]:?decision <thread_id> <text>}"; text="${REST[1]:?decision text required}"
    inner="$(json_str "text"):$(json_str "$text")"
    extra="$(build_inner intent_anchor)"; inner+="${extra:+,$extra}"
    emit_event "decision" "$tid" "$inner"
    maybe_transport "$TO_RECIP" "[DECISION] $tid" "$text"
    finish ;;

  action)
    parse_flags "$@"
    tid="${REST[0]:?action <thread_id> <action>}"; act="${REST[1]:?action text required}"
    OPT[for]="${OPT[for]:-user}"; OPT[urgency]="${OPT[urgency]:-soon}"; OPT[status]="open"
    inner="$(json_str "action"):$(json_str "$act")"
    extra="$(build_inner for urgency unblocks status)"; inner+="${extra:+,$extra}"
    emit_event "action" "$tid" "$inner"
    maybe_transport "$TO_RECIP" "[ACTION:${OPT[for]}] $tid" "$act"
    finish ;;

  finding)
    parse_flags "$@"
    tid="${REST[0]:?finding <thread_id> <finding>}"; fnd="${REST[1]:?finding text required}"
    OPT[severity]="${OPT[severity]:-med}"
    inner="$(json_str "finding"):$(json_str "$fnd")"
    extra="$(build_inner severity class)"; inner+="${extra:+,$extra}"
    emit_event "finding" "$tid" "$inner"
    maybe_transport "$TO_RECIP" "[FINDING:${OPT[severity]}] $tid" "$fnd"
    finish ;;

  gate)
    parse_flags "$@"
    tid="${REST[0]:?gate <thread_id> <what>}"; what="${REST[1]:?gate text required}"
    OPT[gated_on]="${OPT[gated_on]:-user}"; OPT[status]="open"
    inner="$(json_str "gate"):$(json_str "$what")"
    extra="$(build_inner gated_on status)"; inner+="${extra:+,$extra}"
    emit_event "gate" "$tid" "$inner"
    maybe_transport "$TO_RECIP" "[GATE:${OPT[gated_on]}] $tid" "$what"
    finish ;;

  done)
    parse_flags "$@"
    tid="${REST[0]:?done <thread_id> [--ref <id>]}"
    OPT[status]="resolved"
    inner="$(json_str "resolves"):$(json_str "${OPT[ref]:-thread}")"
    inner+=",$(build_inner status)"
    emit_event "done" "$tid" "$inner"
    maybe_transport "$TO_RECIP" "[DONE] $tid" "resolved ${OPT[ref]:-thread}"
    finish ;;

  note)
    parse_flags "$@"
    tid="${REST[0]:?note <thread_id> <text>}"; text="${REST[1]:?note text required}"
    inner="$(json_str "note"):$(json_str "$text")"
    emit_event "note" "$tid" "$inner"
    finish ;;

  view)
    sub="${1:-threads}"; shift || true
    exec "$(dirname "$0")/devlog-view.sh" "$sub" "$@"
    ;;

  attention)
    exec "$(dirname "$0")/attention.sh" "$@"
    ;;

  ""|-h|--help|help)
    sed -n '2,60p' "$0" | sed 's/^# \{0,1\}//'
    ;;

  *)
    echo "log.sh: unknown command '$cmd' (try: thread|decision|action|finding|gate|done|note|view|attention)" >&2
    exit 2 ;;
esac

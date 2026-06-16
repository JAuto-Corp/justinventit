#!/usr/bin/env bash
# devlog-view.sh — DERIVED current-state views over the append-only event stream.
#
# Nothing here mutates state. Every view is a fold over events.jsonl computed at
# read time, so the "current state" can never drift from the record (the failure
# mode of a hand-maintained STATE.md). Threads are the spine: a thread is OPEN
# until a `done` event resolves it; a gate/action is PENDING until resolved.
#
# Views:
#   threads        open threads with last_event_at + staleness (hrs since activity)
#   gates          pending gates (open, not resolved)
#   user-actions   blocked-on-user queue (actions with for=user, ordered by urgency)
#   thread <id>    full chronological event history for one thread
#
# STALE_HOURS (env, default 24): a thread with no event for longer is "stalled".

set -euo pipefail
repo_root() { git rev-parse --show-toplevel 2>/dev/null || pwd; }
DEVLOG_DIR="${DEVLOG_DIR:-$(repo_root)/context/devlog}"
EVENTS="$DEVLOG_DIR/events.jsonl"
STALE_HOURS="${STALE_HOURS:-24}"

[ -f "$EVENTS" ] || { echo "(no dev-log yet — $EVENTS)"; exit 0; }
command -v jq >/dev/null 2>&1 || { echo "devlog-view: jq required for views" >&2; exit 1; }

sub="${1:-threads}"; shift || true

case "$sub" in
  threads)
    # Fold: per thread, title (first thread event) + last_event_at + resolved?
    jq -rs --argjson stale "$STALE_HOURS" '
      ( [ now ] | .[0] ) as $now
      | group_by(.thread_id)
      | map({
          thread_id: .[0].thread_id,
          title: ( map(select(.type=="thread")) | (.[-1].title // "—") ),
          last_event_at: ( map(.ts) | max ),
          resolved: ( any(.type=="done" and (.resolves=="thread")) ),
          events: length
        })
      | map(select(.resolved | not))
      | sort_by(.last_event_at) | reverse
      | .[]
      | ( ($now - (.last_event_at|fromdateiso8601)) / 3600 ) as $age
      | "\(if $age > $stale then "STALLED" else "open    " end) | \(.thread_id) | \(.title) | last: \(.last_event_at) (\($age|floor)h) | \(.events) ev"
    ' "$EVENTS"
    ;;

  gates)
    # A gate is pending unless a later `done` event references its id or thread.
    jq -rs '
      ( map(select(.type=="done") | (.resolves // empty)) ) as $resolved_refs
      | ( map(select(.type=="done") | .thread_id) ) as $resolved_threads
      | map(select(.type=="gate"))
      | map(select( (.id as $i | $resolved_refs | index($i)) | not ))
      | map(select( (.thread_id as $t | $resolved_threads | index($t)) | not ))
      | sort_by(.ts)
      | if length==0 then "(no pending gates)" else .[]
        | "GATE | \(.thread_id) | on:\(.gated_on // "?") | \(.gate) | \(.ts)" end
    ' "$EVENTS"
    ;;

  user-actions)
    # Blocked-on-user queue: action events with for=user, not yet resolved,
    # ordered by urgency (now > soon > whenever). The highest-ROI artifact.
    jq -rs '
      def urank: {"now":0,"soon":1,"whenever":2}[.urgency // "soon"] // 1;
      ( map(select(.type=="done") | (.resolves // empty)) ) as $resolved_refs
      | ( map(select(.type=="done") | .thread_id) ) as $resolved_threads
      | map(select(.type=="action" and ((.for // "user")=="user")))
      | map(select( (.id as $i | $resolved_refs | index($i)) | not ))
      | map(select( (.thread_id as $t | $resolved_threads | index($t)) | not ))
      | sort_by(urank)
      | if length==0 then "(nothing blocked on user)" else .[]
        | "[\(.urgency // "soon")] \(.thread_id) | \(.action)\(if .unblocks then " — unblocks: \(.unblocks)" else "" end)" end
    ' "$EVENTS"
    ;;

  thread)
    tid="${1:?view thread <thread_id>}"
    jq -rs --arg t "$tid" '
      map(select(.thread_id==$t)) | sort_by(.ts)
      | if length==0 then "(no events for thread \($t))" else .[]
        | "\(.ts) | \(.type) | \(.title // .decision // .action // .finding // .gate // .note // .resolves // "")" end
    ' "$EVENTS"
    ;;

  *)
    echo "devlog-view: unknown view '$sub' (threads|gates|user-actions|thread)" >&2
    exit 2 ;;
esac

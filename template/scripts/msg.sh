#!/usr/bin/env bash
# Portable mailbox and bounded hub client. See ../docs/CLUSTER.md.
# Guard reasons and dated source evidence: CLUSTER_PROVENANCE.md.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/jv-project.sh"

_jv_role() {
  [[ "$1" =~ ^[A-Za-z][A-Za-z0-9_]{0,63}$ ]] || _jv_fail "invalid role identifier"
}
_jv_task() {
  [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$ ]] || _jv_fail "invalid archive task identifier"
}

_jv_setup() {
  case "${1:-}:${2:-}:${3:-}" in
    help:*|--help:*|-h:*|hub:--help:*|hub:-h:*|hub:*:--help|hub:*:-h) return 0 ;;
  esac
  _jv_project_configure
  local old
  for old in MSG_MAILROOT HUB_EVENT_LOG HUB_APPEND_LOCK HUB_DRAIN_TRIGGER; do
    [[ -z "${!old:-}" ]] || _jv_fail "unset legacy $old override; configure JV_PROJECT_ID, JV_PROJECT_ROOT and JV_STATE_ROOT"
  done
  MAILROOT="$JV_STORE/mail"
  HUB_EVENT_LOG="$MAILROOT/events.jsonl"
  HUB_APPEND_LOCK="$MAILROOT/.hub-append.lock"
  HUB_DRAIN_TRIGGER="$MAILROOT/.hub-drain-trigger"
  case "${1:-}:${2:-}" in
    hub:target|hub:seats|hub:open|hub:mine|hub:blocked) return 0 ;;
  esac
  case "${1:-}" in
    read|peek|search|archive) [[ $# -lt 2 ]] || _jv_role "$2" ;;
    tail) [[ $# -lt 2 ]] || _jv_role "$2" ;;
  esac
  [[ "${1:-}" != read || $# -lt 3 ]] || _jv_role "$3"
  [[ "${1:-}" != archive || $# -lt 3 ]] || _jv_task "$3"
  _jv_check_state_paths
  _jv_init_store mail/cursors
}

_CROCKFORD="0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_DISPATCH_STATUSES="planned dispatched acked in_flight blocked review staged prod done cancelled"
_THREAD_STATES="live parked dead shipped"
_SCOPE_CLASSES="Quick Standard M L XL"

_upper() { printf '%s' "$1" | tr '[:lower:]' '[:upper:]'; }
_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
_in_set() { local v="$1"; shift; local x; for x in "$@"; do [[ "$x" == "$v" ]] && return 0; done; return 1; }
hub_fail() { echo "ERROR (hub): $*" >&2; exit 2; }

_ULID_RE='^[0-7][0-9A-HJKMNP-TV-Z]{25}$'
_valid_ulid() { [[ "$1" =~ $_ULID_RE ]]; }

mint_ulid() {
  local ms n i t="" r="" bytes b
  ms="$(date -u +%s%3N)" || { echo "ERROR (hub): mint_ulid: date failed" >&2; return 1; }
  [[ "$ms" =~ ^[0-9]+$ && "$ms" -gt 0 ]] || { echo "ERROR (hub): mint_ulid: date returned '$ms'" >&2; return 1; }
  n="$ms"
  for (( i=0; i<10; i++ )); do
    t="${_CROCKFORD:$((n % 32)):1}$t"
    n=$(( n / 32 ))
  done
  bytes="$(head -c 16 /dev/urandom | od -An -tu1)" \
    || { echo "ERROR (hub): mint_ulid: entropy read failed" >&2; return 1; }
  [[ -n "$bytes" ]] || { echo "ERROR (hub): mint_ulid: entropy read empty" >&2; return 1; }
  for b in $bytes; do
    r="${r}${_CROCKFORD:$((b % 32)):1}"
  done
  local out="${t}${r}"
  _valid_ulid "$out" || { echo "ERROR (hub): mint_ulid produced an invalid ULID '$out'" >&2; return 1; }
  printf '%s' "$out"
}

_log_bytes()   { printf '%s' "$1" | wc -c | tr -d ' '; }
_log_frame()   { printf '%s\t%s\n' "$(_log_bytes "$1")" "$1"; }
_log_payload() { printf '%s' "${1#*$'\t'}"; }
_log_valid()   { local len="${1%%$'\t'*}" pay bytes
                 [[ "$1" == *$'\t'* ]] || return 1
                 pay="$(_log_payload "$1")"
                 [[ "$len" =~ ^[0-9]+$ ]] || return 1
                 bytes="$(_log_bytes "$pay")" || { echo "ERROR (hub): authority byte count failed" >&2; return 3; }
                 [[ "$bytes" -eq "$len" ]]; }

_authority_barrier() {
  local f="$1" d
  d="$(dirname "$f")"
  if   sync --data "$f" 2>/dev/null; then :
  elif sync "$f" 2>/dev/null;        then :
  elif sync 2>/dev/null;             then :
  else
    echo "ERROR (hub): durability barrier FAILED (file) for '$f'" >&2
    return 1
  fi
  if   sync --data "$d" 2>/dev/null; then :
  elif sync "$d" 2>/dev/null;        then :
  elif sync 2>/dev/null;             then :
  else
    echo "ERROR (hub): durability barrier FAILED (directory) for '$d'" >&2
    return 1
  fi
  return 0
}

_log_truncate_torn_tail() {
  local f="$1"
  [[ -s "$f" ]] || return 0
  local complete keep last_byte last_line valid_rc=0
  complete="$(wc -l < "$f")" || { echo "ERROR (hub): authority line count failed" >&2; return 3; }
  last_byte="$(tail -c 1 "$f")" || { echo "ERROR (hub): authority tail read failed" >&2; return 3; }
  if [[ -n "$last_byte" ]]; then
    keep="$complete"
  else
    last_line="$(tail -n 1 "$f")" || { echo "ERROR (hub): authority record read failed" >&2; return 3; }
    _log_valid "$last_line" || valid_rc=$?
    case "$valid_rc" in
      0) return 0 ;;
      1) keep=$((complete - 1)) ;; # Successful inspection proved corruption.
      *) return 3 ;; # Inspection failed; authority must remain untouched.
    esac
  fi
  echo "WARN (hub): torn trailing record in '$f' — truncating to last valid record (§5 recovery)" >&2
  if [[ "$keep" -le 0 ]]; then : > "$f"
  else head -n "$keep" "$f" > "$f.repair" && mv "$f.repair" "$f"; fi
}

_log_record_for() {
  local id="$1" line rc=0
  [[ -e "$HUB_EVENT_LOG" ]] || return 1
  line="$(grep -F -m1 "\"hub_id\":\"$id\"" "$HUB_EVENT_LOG" 2>/dev/null)" || rc=$?
  case "$rc" in
    0) ;;
    1) return 1 ;; # A successful search with no match permits a new identity.
    *) echo "ERROR (hub): authority identity lookup failed" >&2; return 3 ;;
  esac
  [[ -n "$line" ]] && _log_valid "$line" || {
    echo "ERROR (hub): authority identity lookup returned an invalid record" >&2; return 3;
  }
  _log_payload "$line"
}

_event_recipients_json() {
  local canon="$1"
  printf '%s' "$canon" | jq -ce '
    if (.recipients? | type) == "array" and (.recipients | length) > 0
    then .recipients
    elif (.to? | type) == "string" and (.to | length) > 0
    then [.to]
    else error("canonical event has no recipients or to")
    end'
}

_event_projection_view() {
  local canon="$1" recipient="$2"
  if printf '%s' "$canon" | jq -e '(.recipients? | type) == "array"' >/dev/null 2>&1; then
    printf '%s' "$canon" | jq -c --arg to "$recipient" '.to = $to'
  else
    printf '%s' "$canon"
  fi
}

_ensure_projection_view() {
  local canon="$1" recipient="$2" canon_from proj_file view attempt
  canon_from="$(printf '%s' "$canon" | jq -r '.from // empty')" || return 3
  [[ -n "$canon_from" && -n "$recipient" ]] || return 3
  proj_file="$MAILROOT/from-${canon_from}-to-${recipient}.jsonl"
  view="$(_event_projection_view "$canon" "$recipient")" || return 3

  for attempt in 1 2; do
    grep -qxF "$view" "$proj_file" 2>/dev/null && return 0
    if [[ -s "$proj_file" ]] && [[ -n "$(tail -c 1 "$proj_file")" ]]; then
      printf '\n' >> "$proj_file" 2>/dev/null || true
    fi
    printf '%s\n' "$view" >> "$proj_file" 2>/dev/null || continue
    grep -qxF "$view" "$proj_file" 2>/dev/null && return 0
  done
  echo "ERROR (hub): projection for recipient '$recipient' was not verified after 2 attempts" >&2
  return 5
}

_append_missing_projection_view() {
  local proj_file="$1" view="$2" recipient="$3" completion_id="$4" attempt last
  for attempt in 1 2; do
    last="$(tail -n 1 "$proj_file" 2>/dev/null || true)"
    [[ "$last" == "$view" ]] && return 0
    if [[ -s "$proj_file" ]] && [[ -n "$(tail -c 1 "$proj_file")" ]]; then
      printf '\n' >> "$proj_file" 2>/dev/null || true
    fi
    printf '%s\n' "$view" >> "$proj_file" 2>/dev/null || continue
    last="$(tail -n 1 "$proj_file" 2>/dev/null || true)"
    [[ "$last" == "$view" ]] && return 0
  done
  echo "ERROR (hub): historical completion ${completion_id} projection for recipient '$recipient' was not verified after 2 attempts" >&2
  return 5
}

_project_event_locked() {
  local canon="$1" recipients_json recipient
  recipients_json="$(_event_recipients_json "$canon")" || return 3
  while IFS= read -r recipient; do
    _ensure_projection_view "$canon" "$recipient" || return $?
  done < <(printf '%s' "$recipients_json" | jq -r '.[]')
}

_repair_complete_projections_locked() {
  [[ -s "$HUB_EVENT_LOG" ]] || return 0
  local framed canon canon_id canon_from recipients_json recipient proj_file view key line metadata
  local sep=$'\034'
  local -a order=() recipients=()
  declare -A desired=() projection_files=()

  while IFS= read -r framed; do
    [[ "$framed" == *'"op":"complete"'* ]] || continue
    _log_valid "$framed" || return 3
    canon="$(_log_payload "$framed")"
    if printf '%s' "$canon" | jq -e '.hub.op? == "complete"' >/dev/null 2>&1; then
      canon_id="$(printf '%s' "$canon" | jq -r '.hub_id // .hub.hub_id // empty')" || return 3
      canon_from="$(printf '%s' "$canon" | jq -r '.from // empty')" || return 3
      [[ -n "$canon_id" && -n "$canon_from" ]] || return 3
      recipients_json="$(_event_recipients_json "$canon")" || return 3
      mapfile -t recipients < <(printf '%s' "$recipients_json" | jq -r '.[]')
      for recipient in "${recipients[@]}"; do
        [[ -n "$recipient" ]] || return 3
        proj_file="$MAILROOT/from-${canon_from}-to-${recipient}.jsonl"
        view="$(_event_projection_view "$canon" "$recipient")" || return 3
        key="${proj_file}${sep}${view}"
        if [[ -z "${desired[$key]+present}" ]]; then
          desired["$key"]="${recipient}:${canon_id}"
          order+=("$key")
        fi
        projection_files["$proj_file"]=1
      done
    fi
  done < "$HUB_EVENT_LOG"

  for proj_file in "${!projection_files[@]}"; do
    [[ -f "$proj_file" ]] || continue
    while IFS= read -r line || [[ -n "$line" ]]; do
      key="${proj_file}${sep}${line}"
      [[ -z "${desired[$key]+present}" ]] || unset 'desired[$key]'
    done < "$proj_file"
  done

  for key in "${order[@]}"; do
    [[ -n "${desired[$key]+present}" ]] || continue
    metadata="${desired[$key]}"
    recipient="${metadata%%:*}"
    canon_id="${metadata#*:}"
    # JSON escapes control bytes; only the path can contain an earlier separator.
    proj_file="${key%${sep}*}"
    view="${key##*${sep}}"
    _append_missing_projection_view "$proj_file" "$view" "$recipient" "$canon_id" || return $?
  done
}

hub_repair_complete_projections() {
  local rc=0
  (
    flock -x 200 || { echo "ERROR (hub): append lock failed" >&2; exit 3; }
    _log_truncate_torn_tail "$HUB_EVENT_LOG" || exit 3
    [[ ! -s "$HUB_EVENT_LOG" ]] || _authority_barrier "$HUB_EVENT_LOG" || exit 8
    _repair_complete_projections_locked || exit $?
  ) 200>"$HUB_APPEND_LOCK" || rc=$?
  case "$rc" in
    0) return 0 ;;
    8) echo "ERROR (hub): durability barrier failed for '$HUB_EVENT_LOG' — NO completion projection was repaired." >&2; return 8 ;;
    5) echo "ERROR (hub): recorded completion projection repair remains incomplete — delivery status unknown" >&2; return 5 ;;
    *) echo "ERROR (hub): completion projection repair failed before mailbox read" >&2; return 3 ;;
  esac
}

hub_append() {
  local msg="$1" hub_id="$2"
  _jv_role "$(jq -r .from <<<"$msg")"
  _jv_role "$(jq -r .to <<<"$msg")"
  msg="$(jq -c --arg project "$JV_PROJECT_ID" '. + {project_id:$project}' <<<"$msg")"
  local rc=0 repair_rc=0
  (
    flock -x 200 || { echo "ERROR (hub): append lock failed" >&2; exit 3; }
    _log_truncate_torn_tail "$HUB_EVENT_LOG" || exit 3
    [[ ! -s "$HUB_EVENT_LOG" ]] || _authority_barrier "$HUB_EVENT_LOG" || exit 8

    local canon
    if canon="$(_log_record_for "$hub_id")"; then
      _authority_barrier "$HUB_EVENT_LOG" || exit 8
      if [[ "$(printf '%s' "$msg" | jq -cS 'del(.ts)' 2>/dev/null)" \
         != "$(printf '%s' "$canon" | jq -cS 'del(.ts)' 2>/dev/null)" ]]; then
        exit 6
      fi
      _repair_complete_projections_locked || exit $?
      _project_event_locked "$canon" || exit $?
      exit 0
    else
      local lookup_rc=$?
      [[ "$lookup_rc" -eq 1 ]] || exit 3
    fi

    _repair_complete_projections_locked || repair_rc=$?
    [[ "$repair_rc" -ne 5 ]] || exit 7
    [[ "$repair_rc" -eq 0 ]] || exit "$repair_rc"

    _log_frame "$msg" >> "$HUB_EVENT_LOG"                || exit 3
    _log_valid "$(tail -n 1 "$HUB_EVENT_LOG")"           || exit 3
    [[ "$(_log_payload "$(tail -n 1 "$HUB_EVENT_LOG")")" == "$msg" ]] || exit 3
    _authority_barrier "$HUB_EVENT_LOG" || exit 8
    _project_event_locked "$msg" || exit $?
  ) 200>"$HUB_APPEND_LOCK" || rc=$?
  case "$rc" in
    0) ;;
    6) echo "ERROR (hub): hub_id ${hub_id} is already recorded with DIFFERENT content — refusing to replay a conflicting payload under a used id" >&2
       exit 6 ;;
    8) echo "ERROR (hub): durability barrier failed for '$HUB_EVENT_LOG' — NO projection was written. Retry with MSG_HUB_ID=${hub_id} once the filesystem is healthy." >&2
       exit 8 ;;
    7) echo "ERROR (hub): historical completion projection repair failed before append; current event ${hub_id} was NOT recorded. Retry after repairing the historical recipient view." >&2
       exit 5 ;;
    5) echo "ERROR (hub): event ${hub_id} is recorded in '$HUB_EVENT_LOG', but one or more recipient projections were NOT VERIFIED — delivery status unknown. Retry with MSG_HUB_ID=${hub_id}, or let a fresh read/append repair from authority." >&2
       exit 5 ;;
    *) echo "ERROR (hub): append ${hub_id} failed or could not be verified (event log '$HUB_EVENT_LOG'); no projection was verified. Retry with MSG_HUB_ID=${hub_id}" >&2
       exit 3 ;;
  esac
}

hub_touch_trigger() {
  touch "$HUB_DRAIN_TRIGGER" || {
    echo "ERROR (hub): could not touch drain trigger '$HUB_DRAIN_TRIGGER' — the append LANDED but the ingester will not wake early" >&2
    exit 4
  }
}

usage() {
  cat <<'EOF'
Usage:
  msg.sh send [--correlation-id=<id>] <from> <to> <body>
  msg.sh send [--correlation-id=<id>] <from> <to> <subject> <body>
      Exactly 3 or 4 positionals — 5+ is REFUSED, never coerced.
      There is no 'kind' argument; alert/request come from a leading ! or ?
      on the body. --correlation-id must use the ATTACHED form (=value) and
      must come BEFORE the positionals; the space-separated form is refused
      because an omitted value would silently consume <from>. A literal `--`
      ends flag parsing, so a subject or body may begin with a dash.
  msg.sh read <me> [from]                     — read pending from <from> (or all)
  msg.sh peek <me>                            — show pending counts, don't advance
  msg.sh tail [me]                            — follow new messages (blocking)
  msg.sh list                                 — list all mailbox files
  msg.sh archive <role> <task-id> [--from <date>] [--to <date>]
                                              — extract <role>'s messages to archive
  msg.sh search <role> <substring>            — search live mailbox + archive

Roles are project-defined identifiers; hub actors are single letters.
Special recipients: all (broadcast), human (user mailbox).
Read ONLY your own letter — reading another seat's mailbox consumes their messages.
EOF
  exit 1
}

cmd="${1:-}"
[[ -z "$cmd" ]] && usage

send_message() {
  local correlation_id=""
  while [[ "${1:-}" == -* ]]; do
    case "$1" in
      --correlation-id=*)
        correlation_id="${1#*=}"
        [[ -n "$correlation_id" ]] || { echo "ERROR: --correlation-id= requires a value" >&2; exit 1; }
        shift ;;
      --correlation-id)
        echo "ERROR: --correlation-id takes an ATTACHED value: --correlation-id=<value>" >&2
        echo "       The space-separated form is refused on purpose: an omitted value would" >&2
        echo "       silently consume <from> and mail an event with the wrong author." >&2
        exit 1 ;;
      --) shift; break ;;
      *) echo "ERROR: unknown flag '$1' for send" >&2; exit 1 ;;
    esac
  done

  [[ $# -eq 3 || $# -eq 4 ]] || {
    echo "ERROR: send takes <from> <to> <body> or <from> <to> <subject> <body> — got $# argument(s)." >&2
    echo "       There is no 'kind' argument; alert/request come from a leading ! or ? on the body." >&2
    exit 1
  }
  local from="$1" to="$2"
  _jv_role "$from"; _jv_role "$to"
  local subject body
  if [[ $# -eq 4 ]]; then
    subject="$3"; body="$4"
  else
    subject=""; body="$3"
  fi
  local kind="info"
  case "$body" in
    '!'*) kind="alert"; body="${body#!}" ;;
    '?'*) kind="request"; body="${body#?}" ;;
  esac
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  local hub_id; hub_id="${MSG_HUB_ID:-$(mint_ulid)}"
  _valid_ulid "$hub_id" || { echo "ERROR (hub): MSG_HUB_ID '$hub_id' is not a valid Crockford ULID" >&2; exit 2; }
  local msg
  msg="$(jq -cn \
    --arg ts "$ts" --arg hub_id "$hub_id" --arg from "$from" --arg to "$to" \
    --arg kind "$kind" --arg subject "$subject" --arg body "$body" \
    --arg cid "$correlation_id" \
    '{ts:$ts, hub_id:$hub_id, from:$from, to:$to, kind:$kind, subject:$subject, body:$body}
     + (if $cid != "" then {correlation_id:$cid} else {} end)')"
  hub_append "$msg" "$hub_id"
  echo "sent: $from → $to ($kind) $hub_id [$ts]"
}

read_messages() {
  local me="$1" from="${2:-}"
  local files=()
  if [[ -n "$from" ]]; then
    [[ -f "$MAILROOT/from-${from}-to-${me}.jsonl" ]] && \
      files=("$MAILROOT/from-${from}-to-${me}.jsonl")
    [[ -f "$MAILROOT/from-${from}-to-all.jsonl" ]] && \
      files+=("$MAILROOT/from-${from}-to-all.jsonl")
  else
    shopt -s nullglob
    files=("$MAILROOT"/from-*-to-"${me}".jsonl "$MAILROOT"/from-*-to-all.jsonl)
    shopt -u nullglob
  fi
  [[ ${#files[@]} -eq 0 ]] && { echo "(no messages for $me)"; return 0; }
  local had_new=0
  for f in "${files[@]}"; do
    local base
    base="$(basename "$f" .jsonl)"
    local cursor_file="$MAILROOT/cursors/${me}-${base}.offset"
    local offset
    offset="$(cat "$cursor_file" 2>/dev/null || echo 0)"
    local size
    size="$(wc -c < "$f")"
    if [[ "$size" -le "$offset" ]]; then
      continue
    fi
    local new_data
    new_data="$(tail -c +$((offset + 1)) "$f")"
    if [[ -n "$new_data" ]]; then
      had_new=1
      echo "=== new from $base (${size} bytes, cursor was ${offset}) ==="
      printf '%s\n' "$new_data"
      echo ""
      echo "$size" > "$cursor_file"
    fi
  done
  if [[ $had_new -eq 0 ]]; then echo "(no new messages for $me)"; fi
}

peek_messages() {
  local me="$1"
  shopt -s nullglob
  local files=("$MAILROOT"/from-*-to-"${me}".jsonl "$MAILROOT"/from-*-to-all.jsonl)
  shopt -u nullglob
  [[ ${#files[@]} -eq 0 ]] && { echo "(no mailboxes for $me)"; return 0; }
  local total=0
  for f in "${files[@]}"; do
    local base
    base="$(basename "$f" .jsonl)"
    local cursor_file="$MAILROOT/cursors/${me}-${base}.offset"
    local offset
    offset="$(cat "$cursor_file" 2>/dev/null || echo 0)"
    local size
    size="$(wc -c < "$f")"
    local pending=$((size - offset))
    if [[ $pending -gt 0 ]]; then
      local line_count
      line_count="$(tail -c +$((offset + 1)) "$f" | wc -l)"
      echo "${base}: ${line_count} new message(s), ${pending} bytes pending"
      total=$((total + line_count))
    fi
  done
  if [[ $total -eq 0 ]]; then echo "(no pending messages for $me)"; fi
}

tail_messages() {
  local me="${1:-}"
  shopt -s nullglob
  local files
  if [[ -n "$me" ]]; then
    files=("$MAILROOT"/from-*-to-"${me}".jsonl)
  else
    files=("$MAILROOT"/from-*-to-*.jsonl)
  fi
  shopt -u nullglob
  [[ ${#files[@]} -eq 0 ]] && { echo "(no mailboxes yet)"; return 0; }
  echo "tailing ${#files[@]} mailbox file(s); Ctrl-C to stop..."
  tail -F "${files[@]}"
}

list_mailboxes() {
  shopt -s nullglob
  local files=("$MAILROOT"/from-*-to-*.jsonl)
  shopt -u nullglob
  [[ ${#files[@]} -eq 0 ]] && { echo "(no mailboxes yet at $MAILROOT)"; return 0; }
  echo "Mailboxes at $MAILROOT:"
  for f in "${files[@]}"; do
    local base size lines
    base="$(basename "$f")"
    size="$(wc -c < "$f")"
    lines="$(wc -l < "$f")"
    printf "  %-30s %6d bytes  %3d msg\n" "$base" "$size" "$lines"
  done
}

archive_messages() {
  local role="$1" task_id="$2"
  shift 2
  local from_date="" to_date=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from) from_date="$2"; shift 2 ;;
      --to) to_date="$2"; shift 2 ;;
      *) echo "ERROR: unknown archive flag '$1'" >&2; return 1 ;;
    esac
  done

  local archive_dir="$MAILROOT/archive/$role"
  mkdir -p "$archive_dir"
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  local out_file="$archive_dir/${task_id}-${ts}.jsonl"

  shopt -s nullglob
  local files=("$MAILROOT"/from-*-to-*.jsonl)
  shopt -u nullglob
  [[ ${#files[@]} -eq 0 ]] && { echo "(no mailboxes to archive)"; return 0; }

  local total_archived=0
  : > "$out_file"

  for f in "${files[@]}"; do
    local base
    base="$(basename "$f" .jsonl)"
    if [[ ! "$base" =~ ^from-${role}-to- ]] && [[ ! "$base" =~ -to-${role}$ ]]; then
      continue
    fi

    local cursor_file="$MAILROOT/cursors/archive-${role}-${base}.json"
    local last_byte=0
    if [[ -f "$cursor_file" ]]; then
      last_byte=$(jq -r '.last_archived_byte // 0' "$cursor_file" 2>/dev/null || echo 0)
    fi

    local file_size
    file_size="$(wc -c < "$f")"
    if [[ "$file_size" -le "$last_byte" ]]; then
      continue
    fi

    : > "$HUB_APPEND_LOCK" 2>/dev/null || true   # ensure the lock file exists
    local entries
    entries="$( {
      flock -s 200 || exit 7
      tail -c +$((last_byte + 1)) "$f"
    } 200<"$HUB_APPEND_LOCK" )" || {
      echo "ERROR (hub): archive could not take the shared append lock ('$HUB_APPEND_LOCK') — refusing to read the mailbox unlocked" >&2
      exit 7
    }

    [[ -z "$entries" ]] && continue

    local filtered="$entries"
    if [[ -n "$from_date" ]]; then
      filtered="$(printf '%s\n' "$filtered" | jq -c --arg from "$from_date" 'select(.ts >= $from)' 2>/dev/null || printf '%s\n' "$filtered")"
    fi
    if [[ -n "$to_date" ]]; then
      filtered="$(printf '%s\n' "$filtered" | jq -c --arg to "$to_date" 'select(.ts <= $to)' 2>/dev/null || printf '%s\n' "$filtered")"
    fi

    local count=0
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      printf '%s\n' "$line" | jq -c --arg mailbox "$base" --arg task_id "$task_id" \
        '. + {_archive_mailbox: $mailbox, _archive_task_id: $task_id}' >> "$out_file" 2>/dev/null \
        || printf '%s\n' "$line" >> "$out_file"
      count=$((count + 1))
    done <<< "$filtered"

    total_archived=$((total_archived + count))

    (
      flock -x 201
      cat > "$cursor_file" <<EOF
{
  "file": "$base.jsonl",
  "last_archived_byte": $file_size,
  "last_archived_ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "task_id": "$task_id"
}
EOF
    ) 201>"$cursor_file.lock"
  done

  if [[ "$total_archived" -gt 0 ]]; then
    echo "archived $total_archived message(s) to $out_file"
  else
    echo "(no new messages to archive for role $role since last archive)"
    rm -f "$out_file"
  fi
}

# Ordinary grep misses do not abort the remaining mailboxes or archives.
_search_file() {
  local matches rc=0 line
  matches="$(grep -F -- "$2" "$1" 2>/dev/null)" || rc=$?
  case "$rc" in
    0) while IFS= read -r line; do printf '[%s] %s\n' "$3" "$line"; done <<<"$matches" ;;
    1) return 0 ;;
    *) echo "ERROR: search grep failed" >&2; return "$rc" ;;
  esac
}

search_messages() {
  local role="$1" pattern="$2"

  echo "=== live mailboxes ==="
  shopt -s nullglob
  local files=("$MAILROOT"/from-*-to-*.jsonl)
  shopt -u nullglob
  for f in "${files[@]}"; do
    local base
    base="$(basename "$f" .jsonl)"
    if [[ ! "$base" =~ ^from-${role}-to- ]] && [[ ! "$base" =~ -to-${role}$ ]]; then
      continue
    fi
    _search_file "$f" "$pattern" "$base"
  done

  echo ""
  echo "=== archive ==="
  if [[ -d "$MAILROOT/archive/$role" ]]; then
    shopt -s nullglob
    local arc_files=("$MAILROOT/archive/$role"/*.jsonl)
    shopt -u nullglob
    for f in "${arc_files[@]}"; do
      local base
      base="$(basename "$f" .jsonl)"
      _search_file "$f" "$pattern" "archive/$base"
    done
  else
    echo "(no archive yet for role $role)"
  fi
}

hub_usage() {
  cat <<'EOF' >&2
Usage: msg.sh hub <verb> [flags]   (ONE append = transport + record)
  hub dispatch --from R --to A --title "…" --body "…|-" [--body-file F] \
               [--thread SLUG] [--issue N] [--prereq ID] \
               [--scope Quick|Standard|M|L|XL] [--status STATUS]
  hub status   --from R --dispatch ID --status STATUS [--blocked-reason "…"] [--to R]
  hub rule     --from R --thread SLUG --title "…" --body "…" [--supersedes ID] [--to R]
  hub thread --open   --from R --id SLUG --anchor "…" --owner A --title "…" [--lane L] \
             [--after SLUG]… [--checklist '<json>'] [--to R]
  hub thread --update SLUG --from R --state live|parked|shipped|dead [--next-gate "…"] \
             [--after SLUG]… [--checklist '<json>'] [--to R]
  hub finding  --from R --title "…" --body "…" [--suggest-thread SLUG|new] [--to R]
  hub finding  --from R --route <finding-id> --thread SLUG [--to R]   (route finding)
  hub finding  --from R --resolve <finding-id> [--to R]               (resolve finding)
  hub attention --answer <value> --id <attention-uuid> [--from R]     (structured decision answer;
               ingester writes metadata.answered_value/answered_at + resolves the row)
  hub complete --from R --producer ID --correlation-id RUN \
               --outcome success|failure|cancelled|timeout --recipient R [--recipient R]… \
               [--dispatch ID] [--result-ref REF] [--result-digest sha256:HEX] \
               [--verdict VALUE] [--schema-valid yes|no|unknown] [--diagnostic-ref REF] \
               [--body "…|-"|--body-file F]

READ verbs (optional external legacy PostgREST projection; explicit MSG_ENV_FILE
with HUB_PROJECT_ID, HUB_URL and HUB_SERVICE_KEY; no product/home fallback):
  hub target                print the resolved env file and hub URL (never the key)
  hub seats                 role × current open dispatch (the seats/bandwidth view)
  hub open                  all open dispatches (newest first)
  hub mine   [--from R]     open dispatches assigned to R (defaults to $MSG_FROM)
  hub blocked               blocked dispatches with their blocked_reason
  (append --json to any read verb for raw JSON.)

--from defaults to $MSG_FROM. --body accepts '-' to read stdin; --body-file <path>
reads a file (both dodge the shell backtick/$/quote trap). Bad --to/--status/--state
fail loud at the CLI, never silently at ingest.
EOF
  exit 2
}

hub_complete() {
  local from="" producer="" correlation_id="" outcome="" dispatch_id=""
  local result_ref="" result_digest="" verdict="" schema_valid=""
  local diagnostic_ref="" body="" body_file="" body_set=0 body_file_set=0
  local dispatch_set=0 result_ref_set=0 result_digest_set=0 verdict_set=0
  local schema_valid_set=0 diagnostic_ref_set=0
  local -a recipients=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from|--producer|--correlation-id|--outcome|--recipient|--dispatch|--result-ref|--result-digest|--verdict|--schema-valid|--diagnostic-ref|--body|--body-file)
        [[ $# -ge 2 ]] || hub_fail "complete: $1 requires a value"
        case "$1" in
          --from) from="$2" ;;
          --producer) producer="$2" ;;
          --correlation-id) correlation_id="$2" ;;
          --outcome) outcome="$2" ;;
          --recipient) recipients+=("$2") ;;
          --dispatch) dispatch_id="$2"; dispatch_set=1 ;;
          --result-ref) result_ref="$2"; result_ref_set=1 ;;
          --result-digest) result_digest="$2"; result_digest_set=1 ;;
          --verdict) verdict="$2"; verdict_set=1 ;;
          --schema-valid) schema_valid="$2"; schema_valid_set=1 ;;
          --diagnostic-ref) diagnostic_ref="$2"; diagnostic_ref_set=1 ;;
          --body) body="$2"; body_set=1 ;;
          --body-file) body_file="$2"; body_file_set=1 ;;
        esac
        shift 2
        ;;
      -h|--help) hub_usage ;;
      *) hub_fail "complete: flag '$1' is not allowed" ;;
    esac
  done

  [[ -n "$from" ]] || hub_fail "complete: --from required"
  [[ -n "$producer" ]] || hub_fail "complete: --producer required"
  [[ -n "$correlation_id" ]] || hub_fail "complete: --correlation-id required"
  [[ -n "$outcome" ]] || hub_fail "complete: --outcome required"
  [[ ${#recipients[@]} -gt 0 ]] || hub_fail "complete: --recipient required at least once"

  local from_lc; from_lc="$(_lower "$from")"
  [[ "$from_lc" =~ ^[a-z]$ ]] || hub_fail "complete: --from must be one letter"
  _in_set "$outcome" success failure cancelled timeout \
    || hub_fail "complete: --outcome must be success|failure|cancelled|timeout"
  [[ "$dispatch_set" -eq 0 || -n "$dispatch_id" ]] \
    || hub_fail "complete: --dispatch cannot be empty"
  [[ "$dispatch_set" -eq 0 ]] || _valid_ulid "$dispatch_id" \
    || hub_fail "complete: --dispatch must be a valid Crockford ULID"
  [[ "$result_ref_set" -eq 0 || -n "$result_ref" ]] \
    || hub_fail "complete: --result-ref cannot be empty"
  [[ "$result_digest_set" -eq 0 || "$result_digest" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || hub_fail "complete: --result-digest must be sha256:<64 lowercase hex>"
  [[ "$verdict_set" -eq 0 || -n "$verdict" ]] \
    || hub_fail "complete: --verdict cannot be empty"
  [[ "$schema_valid_set" -eq 0 ]] || _in_set "$schema_valid" yes no unknown \
    || hub_fail "complete: --schema-valid must be yes|no|unknown"
  [[ "$diagnostic_ref_set" -eq 0 || -n "$diagnostic_ref" ]] \
    || hub_fail "complete: --diagnostic-ref cannot be empty"
  [[ "$body_set" -eq 0 || "$body_file_set" -eq 0 ]] \
    || hub_fail "complete: use only one of --body or --body-file"

  local raw recipient recipients_json
  local -a canonical_recipients=()
  for raw in "${recipients[@]}"; do
    recipient="$(_lower "$raw")"
    [[ "$recipient" =~ ^[a-z]$ ]] \
      || hub_fail "complete: --recipient must be one letter"
    canonical_recipients+=("$recipient")
  done
  mapfile -t canonical_recipients < <(
    printf '%s\n' "${canonical_recipients[@]}" | LC_ALL=C sort -u
  )
  recipients_json="$(printf '%s\n' "${canonical_recipients[@]}" | jq -R . | jq -cs .)"

  if [[ "$body_file_set" -eq 1 ]]; then
    [[ -n "$body_file" ]] || hub_fail "complete: --body-file cannot be empty"
    [[ -f "$body_file" ]] || hub_fail "complete: --body-file '$body_file' not found"
    body="$(cat "$body_file")"
    body_set=1
  elif [[ "$body_set" -eq 1 && "$body" == "-" ]]; then
    body="$(cat)"
  fi
  [[ "$body_set" -eq 1 ]] || body="run ${correlation_id} finished with ${outcome}"

  local hub_id; hub_id="${MSG_HUB_ID:-$(mint_ulid)}"
  _valid_ulid "$hub_id" || hub_fail "MSG_HUB_ID '$hub_id' is not a valid Crockford ULID"
  local ts; ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  local to_lc="${canonical_recipients[0]}"
  local subject="completion ${correlation_id} -> ${outcome}"
  local hub_obj msg
  hub_obj="$(jq -cn \
    --arg op complete --arg hub_id "$hub_id" --arg cid "$correlation_id" \
    --arg outcome "$outcome" --arg producer "$producer" --arg dispatch "$dispatch_id" \
    --arg result_ref "$result_ref" --arg result_digest "$result_digest" \
    --arg verdict "$verdict" --arg schema_valid "$schema_valid" \
    --arg diagnostic_ref "$diagnostic_ref" --argjson recipients "$recipients_json" '
    {op:$op, hub_id:$hub_id, correlation_id:$cid, outcome:$outcome,
     producer:$producer, recipients:$recipients}
    + (if $dispatch!="" then {dispatch_id:$dispatch} else {} end)
    + (if $result_ref!="" then {result_ref:$result_ref} else {} end)
    + (if $result_digest!="" then {result_digest:$result_digest} else {} end)
    + (if $verdict!="" then {verdict:$verdict} else {} end)
    + (if $schema_valid!="" then {schema_valid:$schema_valid} else {} end)
    + (if $diagnostic_ref!="" then {diagnostic_ref:$diagnostic_ref} else {} end)')"
  msg="$(jq -cn \
    --arg ts "$ts" --arg hub_id "$hub_id" --arg from "$from_lc" --arg to "$to_lc" \
    --arg kind completion --arg subject "$subject" --arg body "$body" \
    --argjson recipients "$recipients_json" --argjson hub "$hub_obj" \
    '{ts:$ts, hub_id:$hub_id, from:$from, to:$to, kind:$kind, subject:$subject,
      body:$body, recipients:$recipients, hub:$hub}')"
  hub_append "$msg" "$hub_id"
  hub_touch_trigger
  echo "hub: complete $hub_id ($from_lc → ${canonical_recipients[*]}) [$ts]"
}

hub_message() {
  local sub="${1:-}"; shift || true
  [[ -z "$sub" ]] && hub_usage
  if [[ "$sub" == "complete" ]]; then
    hub_complete "$@"
    return
  fi

  local from="${MSG_FROM:-}" to="" title="" body="" body_set=0 body_file=""
  local thread="" issue="" prereq="" scope="" status="" dispatch_id=""
  local blocked_reason="" supersedes="" state="" next_gate="" owner="" lane=""
  local anchor="" id_slug="" suggest_thread="" open_flag=0 update_slug=""
  local checklist=""; local -a after_slugs=()
  local route_finding="" resolve_finding=""
  local answer_value=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from) from="${2:-}"; shift 2 ;;
      --to) to="${2:-}"; shift 2 ;;
      --title) title="${2:-}"; shift 2 ;;
      --body) body="${2:-}"; body_set=1; shift 2 ;;
      --body-file) body_file="${2:-}"; shift 2 ;;
      --thread) thread="${2:-}"; shift 2 ;;
      --issue) issue="${2:-}"; shift 2 ;;
      --prereq) prereq="${2:-}"; shift 2 ;;
      --scope) scope="${2:-}"; shift 2 ;;
      --status) status="${2:-}"; shift 2 ;;
      --dispatch) dispatch_id="${2:-}"; shift 2 ;;
      --blocked-reason) blocked_reason="${2:-}"; shift 2 ;;
      --supersedes) supersedes="${2:-}"; shift 2 ;;
      --state) state="${2:-}"; shift 2 ;;
      --next-gate) next_gate="${2:-}"; shift 2 ;;
      --owner) owner="${2:-}"; shift 2 ;;
      --lane) lane="${2:-}"; shift 2 ;;
      --anchor) anchor="${2:-}"; shift 2 ;;
      --id) id_slug="${2:-}"; shift 2 ;;
      --suggest-thread) suggest_thread="${2:-}"; shift 2 ;;
      --after) after_slugs+=("${2:-}"); shift 2 ;;
      --checklist) checklist="${2:-}"; shift 2 ;;
      --route) route_finding="${2:-}"; shift 2 ;;
      --resolve) resolve_finding="${2:-}"; shift 2 ;;
      --answer) answer_value="${2:-}"; shift 2 ;;
      --open) open_flag=1; shift ;;
      --update) update_slug="${2:-}"; shift 2 ;;
      -h|--help) hub_usage ;;
      *) hub_fail "unknown flag '$1' for 'hub $sub'" ;;
    esac
  done

  [[ -z "$from" ]] && hub_fail "--from <role> required (or export MSG_FROM)"
  if [[ -n "$body_file" ]]; then
    [[ -f "$body_file" ]] || hub_fail "--body-file '$body_file' not found"
    body="$(cat "$body_file")"; body_set=1
  elif [[ "$body_set" -eq 1 && "$body" == "-" ]]; then
    body="$(cat)"
  fi

  local from_lc; from_lc="$(_lower "$from")"
  [[ "$from_lc" =~ ^[a-z]$ ]] || hub_fail "--from must be a single letter, got '$from'"
  local hub_id; hub_id="${MSG_HUB_ID:-$(mint_ulid)}"
  _valid_ulid "$hub_id" || hub_fail "MSG_HUB_ID '$hub_id' is not a valid Crockford ULID"
  local ts; ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  local to_lc kind subject hub_obj

  case "$sub" in
    dispatch)
      [[ -n "$to" ]]    || hub_fail "dispatch: --to <A-Z> required"
      [[ -n "$title" ]] || hub_fail "dispatch: --title required"
      [[ "$body_set" -eq 1 && -n "$body" ]] || hub_fail "dispatch: --body (or --body-file / '--body -') required"
      local to_uc; to_uc="$(_upper "$to")"
      [[ "$to_uc" =~ ^[A-Z]$ ]] || hub_fail "dispatch: --to must be a single A-Z letter, got '$to'"
      [[ -z "$status" ]] && status="dispatched"
      _in_set "$status" $_DISPATCH_STATUSES || hub_fail "dispatch: invalid --status '$status'"
      if [[ -n "$scope" ]]; then _in_set "$scope" $_SCOPE_CLASSES || hub_fail "dispatch: invalid --scope '$scope'"; fi
      if [[ -n "$issue" && ! "$issue" =~ ^[0-9]+$ ]]; then hub_fail "dispatch: --issue must be numeric, got '$issue'"; fi
      to_lc="$(_lower "$to")"; kind="dispatch"; subject="$title"
      hub_obj="$(jq -cn \
        --arg op dispatch --arg hub_id "$hub_id" --arg to_role "$to_uc" \
        --arg status "$status" --arg thread "$thread" --arg issue "$issue" \
        --arg prereq "$prereq" --arg scope "$scope" '
        {op:$op, hub_id:$hub_id, to_role:$to_role, status:$status}
        + (if $thread!="" then {thread_id:$thread} else {} end)
        + (if $issue!=""  then {issue:($issue|tonumber)} else {} end)
        + (if $prereq!="" then {prereq:$prereq} else {} end)
        + (if $scope!=""  then {scope_class:$scope} else {} end)')"
      ;;
    status)
      [[ -n "$dispatch_id" ]] || hub_fail "status: --dispatch <id> required"
      [[ -n "$status" ]]      || hub_fail "status: --status required"
      _in_set "$status" $_DISPATCH_STATUSES || hub_fail "status: invalid --status '$status'"
      to_lc="$(_lower "${to:-o}")"; kind="status"; subject="status ${dispatch_id} -> ${status}"
      [[ -n "$blocked_reason" ]] && body="$blocked_reason"
      hub_obj="$(jq -cn \
        --arg op status --arg hub_id "$hub_id" --arg did "$dispatch_id" \
        --arg status "$status" --arg br "$blocked_reason" '
        {op:$op, hub_id:$hub_id, dispatch_id:$did, status:$status}
        + (if $br!="" then {blocked_reason:$br} else {} end)')"
      ;;
    rule)
      [[ -n "$thread" ]] || hub_fail "rule: --thread <slug> required"
      [[ -n "$title" ]]  || hub_fail "rule: --title required"
      [[ "$body_set" -eq 1 && -n "$body" ]] || hub_fail "rule: --body required"
      to_lc="$(_lower "${to:-o}")"; kind="rule"; subject="$title"
      hub_obj="$(jq -cn \
        --arg op rule --arg hub_id "$hub_id" --arg thread "$thread" --arg sup "$supersedes" '
        {op:$op, hub_id:$hub_id, thread_id:$thread}
        + (if $sup!="" then {supersedes_id:$sup} else {} end)')"
      ;;
    thread)
      local after_json checklist_json
      if [[ ${#after_slugs[@]} -gt 0 ]]; then
        after_json="$(printf '%s\n' "${after_slugs[@]}" | jq -R . | jq -cs .)"
      else
        after_json="[]"
      fi
      if [[ -n "$checklist" ]]; then
        checklist_json="$(jq -c . <<<"$checklist" 2>/dev/null)" \
          || hub_fail "thread: --checklist must be valid JSON"
      else
        checklist_json="null"
      fi
      if [[ "$open_flag" -eq 1 ]]; then
        [[ -n "$id_slug" ]] || hub_fail "thread --open: --id <slug> required"
        [[ -n "$anchor" ]]  || hub_fail "thread --open: --anchor required"
        [[ -n "$owner" ]]   || hub_fail "thread --open: --owner <A-Z> required"
        [[ -n "$title" ]]   || hub_fail "thread --open: --title required"
        local owner_uc; owner_uc="$(_upper "$owner")"
        [[ "$owner_uc" =~ ^[A-Z]$ ]] || hub_fail "thread --open: --owner must be A-Z, got '$owner'"
        to_lc="$(_lower "${to:-o}")"; kind="thread_open"; subject="$title"; body="$anchor"
        hub_obj="$(jq -cn \
          --arg op thread_open --arg hub_id "$hub_id" --arg tid "$id_slug" \
          --arg title "$title" --arg anchor "$anchor" --arg owner "$owner_uc" --arg lane "$lane" \
          --argjson after "$after_json" --argjson checklist "$checklist_json" '
          {op:$op, hub_id:$hub_id, thread_id:$tid, title:$title, intent_anchor:$anchor, owner_role:$owner}
          + (if $lane!="" then {lane:$lane} else {} end)
          + (if ($after|length)>0 then {depends_on:$after} else {} end)
          + (if $checklist!=null then {checklist:$checklist} else {} end)')"
      elif [[ -n "$update_slug" ]]; then
        [[ -n "$state" ]] || hub_fail "thread --update: --state <live|parked|shipped|dead> required"
        _in_set "$state" $_THREAD_STATES || hub_fail "thread --update: invalid --state '$state'"
        to_lc="$(_lower "${to:-o}")"; kind="thread_update"; subject="thread ${update_slug} -> ${state}"
        [[ -n "$next_gate" ]] && body="$next_gate"
        hub_obj="$(jq -cn \
          --arg op thread_update --arg hub_id "$hub_id" --arg tid "$update_slug" \
          --arg state "$state" --arg ng "$next_gate" \
          --argjson after "$after_json" --argjson checklist "$checklist_json" '
          {op:$op, hub_id:$hub_id, thread_id:$tid, state:$state}
          + (if $ng!="" then {next_gate:$ng} else {} end)
          + (if ($after|length)>0 then {depends_on:$after} else {} end)
          + (if $checklist!=null then {checklist:$checklist} else {} end)')"
      else
        hub_fail "thread: use '--open' or '--update <slug>'"
      fi
      ;;
    finding)
      if [[ -n "$route_finding" ]]; then
        [[ -n "$thread" ]] || hub_fail "finding --route: --thread <slug> required"
        to_lc="$(_lower "${to:-o}")"; kind="finding_route"
        subject="route finding ${route_finding} -> ${thread}"
        hub_obj="$(jq -cn --arg op finding_route --arg hub_id "$hub_id" \
          --arg fid "$route_finding" --arg tid "$thread" \
          '{op:$op, hub_id:$hub_id, finding_id:$fid, thread_id:$tid}')"
      elif [[ -n "$resolve_finding" ]]; then
        to_lc="$(_lower "${to:-o}")"; kind="finding_resolve"
        subject="resolve finding ${resolve_finding}"
        hub_obj="$(jq -cn --arg op finding_resolve --arg hub_id "$hub_id" \
          --arg fid "$resolve_finding" '{op:$op, hub_id:$hub_id, finding_id:$fid}')"
      else
        [[ -n "$title" ]] || hub_fail "finding: --title required (or --route/--resolve <finding-id>)"
        [[ "$body_set" -eq 1 && -n "$body" ]] || hub_fail "finding: --body required"
        to_lc="$(_lower "${to:-o}")"; kind="finding"; subject="$title"
        hub_obj="$(jq -cn \
          --arg op finding --arg hub_id "$hub_id" --arg st "$suggest_thread" '
          {op:$op, hub_id:$hub_id}
          + (if $st!="" then {suggested_thread_id:$st} else {} end)')"
      fi
      ;;
    attention)
      [[ -n "$answer_value" ]] || hub_fail "attention: --answer <value> required"
      [[ -n "$id_slug" ]] || hub_fail "attention --answer: --id <attention-uuid> required"
      to_lc="$(_lower "${to:-o}")"; kind="attention_answer"
      subject="answer attention ${id_slug} -> ${answer_value}"
      hub_obj="$(jq -cn --arg op attention_answer --arg hub_id "$hub_id" \
        --arg aid "$id_slug" --arg ans "$answer_value" \
        '{op:$op, hub_id:$hub_id, attention_id:$aid, answer:$ans}')"
      ;;
    *)
      hub_fail "unknown hub verb '$sub' (dispatch|status|rule|thread|finding|attention) (read verbs: seats|open|mine|blocked)"
      ;;
  esac

  local msg
  msg="$(jq -cn \
    --arg ts "$ts" --arg hub_id "$hub_id" --arg from "$from_lc" --arg to "$to_lc" \
    --arg kind "$kind" --arg subject "$subject" --arg body "$body" \
    --argjson hub "$hub_obj" \
    '{ts:$ts, hub_id:$hub_id, from:$from, to:$to, kind:$kind, subject:$subject, body:$body, hub:$hub}')"
  hub_append "$msg" "$hub_id"
  hub_touch_trigger
  echo "hub: $sub $hub_id ($from_lc → $to_lc) [$ts]"
}

_OPEN_DISPATCH_STATUSES="planned,dispatched,acked,in_flight,blocked,review,staged"

# Parse data only: this file is never sourced or evaluated as shell code.
_hub_env_val() {
  local line raw
  line="$(grep -m 1 -E "^$1=" -- "$HUB_ENV_FILE")" || return 0
  raw="${line#*=}"
  if [[ "$raw" == \"*\" || "$raw" == \'*\' ]]; then raw="${raw:1:${#raw}-2}"; fi
  printf '%s' "$raw"
}

_hub_load_target() {
  [[ "${MSG_ENV_FILE:-}" == /* && -f "$MSG_ENV_FILE" ]] \
    || hub_fail "explicit absolute MSG_ENV_FILE configuration required"
  HUB_ENV_FILE="$MSG_ENV_FILE"
  local project
  project="$(_hub_env_val HUB_PROJECT_ID)"
  [[ "$project" == "$JV_PROJECT_ID" ]] || hub_fail "hub configuration project identity mismatch"
  HUB_DB_URL="$(_hub_env_val HUB_URL)"
  [[ "$HUB_DB_URL" =~ ^https://([A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9A-Fa-f:]+\])(:[0-9]+)?/?$ ]] \
    || hub_fail "HUB_URL must be an HTTPS origin without userinfo, path, query or fragment"
  HUB_DB_URL="${HUB_DB_URL%/}"
}

_hub_load_creds() {
  _hub_load_target
  HUB_DB_KEY="$(_hub_env_val HUB_SERVICE_KEY)"
  [[ -n "$HUB_DB_KEY" && ! "$HUB_DB_KEY" =~ [[:cntrl:]] && "$HUB_DB_KEY" != *\"* && "$HUB_DB_KEY" != *\\* ]] \
    || hub_fail "invalid or missing HUB_SERVICE_KEY configuration"
}

# -q FIRST disables user curl defaults. Secrets stay on stdin; neither raw HTTP
# errors nor curl diagnostics are safe to echo because either can include them.
_hub_pgrest() {
  local out http code
  out="$(printf 'header = "apikey: %s"\nheader = "Authorization: Bearer %s"\n' \
      "$HUB_DB_KEY" "$HUB_DB_KEY" \
    | curl -q -sS --max-time 15 -w $'\n%{http_code}' -K - \
        "${HUB_DB_URL}/rest/v1/$1" -H "Accept: application/json" 2>/dev/null)" \
    || hub_fail "read: PostgREST request failed (network)"
  code="${out##*$'\n'}"; http="${out%$'\n'*}"
  [[ "$code" =~ ^[0-9]{3}$ ]] || hub_fail "read: invalid HTTP status"
  [[ "$code" == 2* ]] || hub_fail "read: PostgREST HTTP $code"
  printf '%s' "$http"
}

hub_read() {
  local sub="${1:-}"; shift || true
  local as_json=0 arg_from="${MSG_FROM:-}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) as_json=1; shift ;;
      --from) arg_from="${2:-}"; shift 2 ;;
      -h|--help) hub_fail "hub $sub takes no args except --json / --from" ;;
      *) hub_fail "unknown flag '$1' for 'hub $sub'" ;;
    esac
  done
  [[ "$sub" != mine || "$arg_from" =~ ^[A-Za-z]$ ]] || hub_fail "hub mine: --from must be one role letter"
  _hub_load_creds

  local sel_disp="select=id,hub_id,to_role,title,status,blocked_reason,thread_id,dispatched_at&order=dispatched_at.desc.nullslast"
  local no_test_disp="title=not.like.*__TDS_TEST__*"
  local no_test_role="or=(current_branch.is.null,current_branch.not.like.*__TDS_TEST__*)"
  local json
  case "$sub" in
    seats)
      local roles disp
      roles="$(_hub_pgrest "orchestration_roles?select=letter,status&order=letter&is_fixture=eq.false&${no_test_role}")"
      disp="$(_hub_pgrest "orchestration_dispatches?status=in.(${_OPEN_DISPATCH_STATUSES})&${no_test_disp}&${sel_disp}")"
      if [[ "$as_json" -eq 1 ]]; then
        jq -n --argjson roles "$roles" --argjson disp "$disp" \
          '($disp|group_by(.to_role)|map({key:.[0].to_role,value:.[0]})|from_entries) as $l
           | [ $roles[] | . + {current_dispatch: ($l[.letter] // null)} ]'
      else
        jq -rn --argjson roles "$roles" --argjson disp "$disp" \
          '($disp|group_by(.to_role)|map({key:.[0].to_role,value:.[0]})|from_entries) as $l
           | $roles[] | "\(.letter)  [\(.status)]  " +
             (($l[.letter]) | if . then "\(.title)  (\(.status))  [\(.hub_id // .id)]" else "— idle —" end)'
      fi
      ;;
    open|mine|blocked)
      local q
      if [[ "$sub" == "blocked" ]]; then
        q="orchestration_dispatches?status=eq.blocked&${no_test_disp}&${sel_disp}"
      else
        q="orchestration_dispatches?status=in.(${_OPEN_DISPATCH_STATUSES})&${no_test_disp}&${sel_disp}"
        if [[ "$sub" == "mine" ]]; then
          [[ -n "$arg_from" ]] || hub_fail "hub mine: --from <role> required (or export MSG_FROM)"
          q="${q}&to_role=eq.$(_upper "$arg_from")"
        fi
      fi
      json="$(_hub_pgrest "$q")"
      if [[ "$as_json" -eq 1 ]]; then
        printf '%s\n' "$json"
      elif [[ "$sub" == "blocked" ]]; then
        jq -r '.[] | "\(.to_role)  \(.title)  — \(.blocked_reason // "(no reason)")  [\(.hub_id // .id)]"' <<<"$json"
      else
        jq -r '.[] | "\(.to_role)  [\(.status)]  \(.title)  [\(.hub_id // .id)]"' <<<"$json"
      fi
      ;;
    *)
      hub_fail "unknown hub read verb '$sub' (open|mine|blocked|seats)"
      ;;
  esac
}

_jv_setup "$@"

case "$cmd" in
  send)
    shift
    send_message "$@"
    ;;
  hub)
    [[ $# -lt 2 ]] && hub_usage
    shift
    case "${1:-}" in
      open|mine|blocked|seats) hub_read "$@" ;;
      target)
        [[ $# -eq 1 ]] || hub_fail "hub target takes no arguments"
        _hub_load_target
        printf 'project_id=%s env_file=%s url=%s\n' "$JV_PROJECT_ID" "$HUB_ENV_FILE" "$HUB_DB_URL"
        ;;
      *) hub_message "$@" ;;
    esac
    ;;
  read)
    [[ $# -lt 2 ]] && usage
    hub_repair_complete_projections
    read_messages "$2" "${3:-}"
    ;;
  peek)
    [[ $# -lt 2 ]] && usage
    hub_repair_complete_projections
    peek_messages "$2"
    ;;
  tail)
    hub_repair_complete_projections
    tail_messages "${2:-}"
    ;;
  list)
    list_mailboxes
    ;;
  archive)
    [[ $# -lt 3 ]] && usage
    shift
    archive_messages "$@"
    ;;
  search)
    [[ $# -lt 3 ]] && usage
    search_messages "$2" "$3"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd"
    usage
    ;;
esac

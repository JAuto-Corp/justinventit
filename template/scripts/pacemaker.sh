#!/usr/bin/env bash
# pacemaker.sh — EXTERNAL PACEMAKER for the agent wake-loop.
#
# WHY (the structural flaw it fixes):
#   Autonomous roles run a self-perpetuating wake-loop: each turn schedules its own
#   successor (an in-session ScheduleWakeup / `/loop`). That makes the loop the SOLE
#   continuity mechanism — and a single-point-of-failure. A transient model-API error
#   that cuts a turn BEFORE it re-arms the wake leaves the process alive but the loop
#   dead ("live process, dead loop"). The role goes inert until a human pastes a
#   prompt to revive it. That human-paste dependency is the difference between
#   "autonomous" and "autonomous until a turn dies."
#
# WHAT this is:
#   An EXTERNAL, out-of-band supervisor (run from host cron — it can NEVER itself
#   stall, because it is not part of any agent loop). It generalizes the passive
#   stall-watchdog (detect + alert) into an ACTIVE auto-resumer:
#     - reads each role's cadence/heartbeat file,
#     - classifies liveness against the explicit contract below,
#     - on `alive + loop-dead` → INJECTS the resume prompt directly into the role's
#       tmux pane via `tmux send-keys` (the auto-recover that eliminates the
#       human-paste dependency),
#     - on `process dead` → escalates via a pluggable notification adapter
#       (and optionally fires a respawn hook).
#   With the pacemaker running, the in-turn ScheduleWakeup becomes a FAST-PATH
#   optimization, not the only thing keeping a role alive.
#
# ─────────────────────────────────────────────────────────────────────────────
# THE LIVENESS CONTRACT (two independent signals, two states, one action each)
# ─────────────────────────────────────────────────────────────────────────────
#   HEARTBEAT (process-alive)  : `heartbeat_at:` — written every turn-end by the
#                                 Stop hook. Fresh heartbeat ⇒ the OS process and
#                                 the session are alive and taking turns.
#   CADENCE   (intent / loop)  : `next_wake_at:` — the time the role itself said it
#                                 would wake again. Fresh ⇒ the wake-loop is armed.
#                                 Stale / NONE / overdue-past-grace ⇒ the loop is
#                                 dead even if the process is alive.
#
#   STATE 1 — ALIVE + LOOP-DEAD   (heartbeat fresh, next_wake stale/NONE/overdue)
#       → the SPOF case. The exact failure the pacemaker exists to fix.
#       ACTION: RESUME — `tmux send-keys` the resume prompt into the role's pane.
#               Session-bound, no new process, no ghost-cron. (See SOLO note.)
#
#   STATE 2 — PROCESS DEAD        (no live pid / heartbeat absent or far past grace)
#       → a different problem (clean exit, crash, OOM). Not a loop revive.
#       ACTION: ESCALATE — notify via the adapter; optionally fire $RESPAWN_HOOK.
#
#   (Healthy = heartbeat fresh AND next_wake fresh/upcoming → no action.
#    Dormant = next_wake_at: none AND state declares dormancy → intentionally idle,
#    skipped. A role that is genuinely done parks itself with `none`.)
#
# ─────────────────────────────────────────────────────────────────────────────
# SAFETY (per the JAuto ghost-cron / split-brain lesson)
# ─────────────────────────────────────────────────────────────────────────────
#   This is a PASSIVE host-cron supervisor. It does NOT create wake-crons, does NOT
#   re-invoke any conversation headlessly, and does NOT spawn a second session for a
#   live role. The ONLY thing it does to a live role is `send-keys` a resume prompt
#   into that role's EXISTING pane — a session-bound nudge, identical to a human
#   paste. There is no second invocation, so there is no split-brain / cursor-race
#   hazard. Idempotent: a per-role dedup file (keyed on the frozen reference epoch)
#   guarantees one resume per stall window — re-running cron does not re-spam.
#
# WIRE (host crontab, every 5 min is a good default):
#   */5 * * * * /path/to/scripts/pacemaker.sh >> /tmp/pacemaker.log 2>&1
#
# DRY-RUN (smoke-test detection WITHOUT touching a real session):
#   PACEMAKER_DRY_RUN=1 PACEMAKER_CADENCE_DIR=./fixtures ./pacemaker.sh
#   → logs "would resume pane X" / "would escalate role Y" and sends nothing.
#
# SOLO mode (N=1):
#   At N=1 the single session IS the cluster. List that one role's cadence file and
#   the pacemaker still guards its loop — the SPOF is identical at N=1 and N>1, so
#   the guard is identical. No coordination tier required.

set -uo pipefail

# ─── Configuration (env-overridable; sane defaults) ──────────────────────────
# Where the cadence/heartbeat files live. Default: a project-local dir; relocate to
# a shared ~/-path when worktrees demand cross-worktree visibility.
CADENCE_DIR="${PACEMAKER_CADENCE_DIR:-${CADENCE_DIR:-./context/cadence}}"

# Per-role dedup state (one resume/escalation per stall window).
STATE_DIR="${PACEMAKER_STATE_DIR:-${CADENCE_DIR}/.pacemaker-state}"

# Roles to supervise. Space-separated. At N=1 this is a single role, e.g. "main".
# If empty, the pacemaker auto-discovers from *.txt in CADENCE_DIR.
ROLES="${PACEMAKER_ROLES:-}"

# Liveness thresholds.
#   GRACE_FLOOR — minimum overdue (s) before a stale next_wake counts as loop-dead.
#     Real API stalls persist for many minutes; the floor spares a role mid-long
#     turn from a false resume. Per-role grace = max(GRACE_FLOOR, 2×cadence).
GRACE_FLOOR="${PACEMAKER_GRACE_FLOOR:-2700}"           # 45 min
#   HEARTBEAT_DEAD — if the freshest heartbeat is older than this, treat the
#     PROCESS as dead (→ escalate), not merely loop-dead (→ resume).
HEARTBEAT_DEAD="${PACEMAKER_HEARTBEAT_DEAD:-5400}"     # 90 min

# Notification adapter: sms | desktop | none  (NOT hardcoded to any vendor).
NOTIFY_ADAPTER="${PACEMAKER_NOTIFY:-none}"

# The resume prompt injected on STATE 1. Generic + mechanism-framed (per the
# wake-loop-mechanism-framing lesson: describe the mechanism, never "NEVER END THE
# LOOP"). The project may override with its own boot/re-orient prompt.
RESUME_PROMPT="${PACEMAKER_RESUME_PROMPT:-Resume your wake-loop: drain your mailbox, re-arm the next ScheduleWakeup (arm it EARLY this turn), then continue. Your work is safe on disk.}"

# tmux target template. {role} is substituted with the role name. The pane-naming
# assumption is documented in docs/PACEMAKER.md — by default each role runs in a
# tmux session (or window) named after the role, so the target is the session name.
TMUX_TARGET_TEMPLATE="${PACEMAKER_TMUX_TARGET:-{role}}"

# Optional respawn hook for STATE 2 (process dead). Receives the role name as $1.
RESPAWN_HOOK="${PACEMAKER_RESPAWN_HOOK:-}"

DRY_RUN="${PACEMAKER_DRY_RUN:-}"
NOW=$(date -u +%s)

log() { printf '%s pacemaker %s\n' "$(date -u +%FT%TZ)" "$*"; }

mkdir -p "$STATE_DIR" 2>/dev/null || true

# ─── Notification adapter (sms | desktop | none) ─────────────────────────────
# Pluggable. The project supplies the concrete channel via env; the framework never
# hardcodes a vendor (the existing JAuto watchdog hardcoding Twilio is the anti-pattern).
notify() {
  local msg="$1"
  case "$NOTIFY_ADAPTER" in
    sms)
      # Project supplies a send command via $PACEMAKER_SMS_CMD; the message is
      # appended as the final argument. e.g. PACEMAKER_SMS_CMD="/path/notify-sms.sh"
      if [ -n "${PACEMAKER_SMS_CMD:-}" ]; then
        [ -n "$DRY_RUN" ] && { log "[DRY_RUN] would sms: $msg"; return; }
        "$PACEMAKER_SMS_CMD" "$msg" >/dev/null 2>&1 || log "sms adapter failed"
      else
        log "notify=sms but PACEMAKER_SMS_CMD unset — message dropped: $msg"
      fi
      ;;
    desktop)
      [ -n "$DRY_RUN" ] && { log "[DRY_RUN] would desktop-notify: $msg"; return; }
      if command -v notify-send >/dev/null 2>&1; then
        notify-send "Pacemaker" "$msg" >/dev/null 2>&1 || true
      elif command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"$msg\" with title \"Pacemaker\"" >/dev/null 2>&1 || true
      else
        log "notify=desktop but no notify-send/osascript — message dropped: $msg"
      fi
      ;;
    none|*)
      log "notify(none): $msg"
      ;;
  esac
}

# ─── tmux resume injection (the auto-recover) ────────────────────────────────
resume_pane() {
  local role="$1"
  local target="${TMUX_TARGET_TEMPLATE//\{role\}/$role}"
  if [ -n "$DRY_RUN" ]; then
    log "[DRY_RUN] would resume pane '$target' (role=$role) via send-keys"
    return 0
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    log "tmux not found — cannot resume role=$role; escalating instead"
    notify "Pacemaker: role $role loop-dead but tmux unavailable to auto-resume."
    return 1
  fi
  # EXACT session-name match. `tmux has-session -t a` and `send-keys -t a` use
  # PREFIX matching, so with session 'ab' alive and 'a' dead the resume would
  # land in 'ab' (wrong-pane injection). Require an exact name in the live
  # session list, and target it with tmux's exact-match `=` prefix so a later
  # send-keys can never resolve to a different (prefix-shared) session.
  if ! tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -qxF -- "$target"; then
    log "tmux session '$target' not found (exact match) for role=$role — escalating"
    notify "Pacemaker: role $role loop-dead but no tmux session '$target' to resume."
    return 1
  fi
  # Exact-match target for send-keys. tmux anchors a session-exact target as
  # `=name:` (the trailing `:` separates session from window/pane; a bare `=name`
  # is parsed as a PANE name and fails to resolve). `=name:` rejects the prefix
  # collision that a plain `name` would silently accept (`name` → first session
  # whose name starts with it, e.g. 'a' → 'ab').
  local tgt="=$target:"
  # Send the prompt LITERALLY (-l) so an overridden RESUME_PROMPT containing tmux
  # key tokens (Enter/Space/C-c/BSpace) is TYPED, not interpreted. Submit with a
  # separate Enter keystroke. `--` ends option parsing so a prompt starting with
  # '-' is not mistaken for a flag.
  tmux send-keys -t "$tgt" -l -- "$RESUME_PROMPT" 2>/dev/null
  tmux send-keys -t "$tgt" Enter 2>/dev/null
  log "RESUMED role=$role pane='$target' (send-keys resume prompt)"
}

# ─── Parse a single field from a cadence file ────────────────────────────────
field() { grep -m1 "^$2:" "$1" 2>/dev/null | sed "s/^$2:[[:space:]]*//"; }

# Convert an ISO8601 (or empty) timestamp to epoch; empty/garbled → "".
to_epoch() {
  local ts="$1"
  [ -z "$ts" ] && { echo ""; return; }
  date -u -d "$ts" +%s 2>/dev/null || echo ""
}

# ─── Resolve the role list ───────────────────────────────────────────────────
if [ -z "$ROLES" ]; then
  if [ -d "$CADENCE_DIR" ]; then
    for f in "$CADENCE_DIR"/*.txt; do
      [ -f "$f" ] || continue
      b="$(basename "$f" .txt)"
      # skip the heartbeat aggregate log if it happens to be *.txt
      [ "$b" = "heartbeat" ] && continue
      ROLES="$ROLES $b"
    done
  fi
fi
ROLES="$(echo "$ROLES" | xargs)"   # trim
[ -z "$ROLES" ] && { log "no roles to supervise in $CADENCE_DIR"; exit 0; }

log "supervising roles: $ROLES  (dir=$CADENCE_DIR, dry_run=${DRY_RUN:-0})"

# ─── Main supervision sweep ──────────────────────────────────────────────────
for ROLE in $ROLES; do
  CAD="$CADENCE_DIR/$ROLE.txt"
  [ -f "$CAD" ] || { log "role=$ROLE no cadence file — skip"; continue; }

  STATE_FIELD="$(field "$CAD" state)"
  NEXT="$(field "$CAD" next_wake_at)"
  HB="$(field "$CAD" heartbeat_at)"
  CAD_S="$(field "$CAD" cadence_seconds)"
  CAD_MIN="$(field "$CAD" cadence_min)"
  [ -z "$CAD_S" ] && [ -n "$CAD_MIN" ] && CAD_S=$((CAD_MIN * 60))
  [ -z "$CAD_S" ] && CAD_S=900

  # Per-role grace = max(floor, 2× cadence).
  GRACE=$((CAD_S * 2)); [ "$GRACE" -lt "$GRACE_FLOOR" ] && GRACE=$GRACE_FLOOR

  # ── Dormancy: explicit `next_wake_at: none` = intentionally parked. Skip. ──
  if [ "$NEXT" = "none" ] || [ "$NEXT" = "NONE" ]; then
    log "role=$ROLE dormant (next_wake_at=none) — skip"
    continue
  fi

  # ── Process-alive signal: the AUTHORITATIVE source is `heartbeat_at` (written by
  #    the Stop hook every turn-end). File mtime is NOT reliable as a process-alive
  #    signal — anything can touch the file, and a freshly-written file always looks
  #    "alive" (which would mask a real PROCESS-DEAD whose heartbeat is hours stale).
  #    So: use heartbeat_at when present; fall back to mtime ONLY when the role omits
  #    heartbeat_at entirely (the heartbeat-only/next_wake-only cadence formats). ──
  HB_E="$(to_epoch "$HB")"
  if [ -n "$HB_E" ]; then
    ALIVE_E="$HB_E"
  else
    ALIVE_E="$(stat -c %Y "$CAD" 2>/dev/null || stat -f %m "$CAD" 2>/dev/null || echo 0)"
  fi
  HB_AGE=$((NOW - ALIVE_E))

  # ── Loop signal: next_wake_at epoch. Guard empty BEFORE parse (date -d "" = ──
  #    midnight-today, a classic false-alarm). Empty next_wake → fall back to the ──
  #    heartbeat as the reference (loop-liveness then == process-liveness).      ──
  NEXT_E="$(to_epoch "$NEXT")"
  if [ -z "$NEXT_E" ]; then
    NEXT_E="$ALIVE_E"
  fi
  OVERDUE=$((NOW - NEXT_E))

  # ── CLASSIFY ─────────────────────────────────────────────────────────────
  # STATE 2 — PROCESS DEAD: no fresh heartbeat within HEARTBEAT_DEAD.
  if [ "$HB_AGE" -ge "$HEARTBEAT_DEAD" ]; then
    SF="$STATE_DIR/$ROLE.dead"
    KEY="$ALIVE_E"
    if [ -f "$SF" ] && [ "$(cat "$SF" 2>/dev/null)" = "$KEY" ]; then
      log "role=$ROLE process-dead (already escalated for this window) — skip"
      continue
    fi
    # DRY_RUN must NOT mutate dedup state — otherwise a dry-run against the real
    # state dir would suppress the NEXT genuine cron escalation for this window.
    [ -z "$DRY_RUN" ] && { echo "$KEY" > "$SF" 2>/dev/null || true; }
    log "role=$ROLE PROCESS-DEAD (heartbeat ${HB_AGE}s old ≥ ${HEARTBEAT_DEAD}s) — escalate"
    notify "Pacemaker: role $ROLE appears PROCESS-DEAD (no heartbeat for $((HB_AGE/60))m). Manual respawn may be needed."
    if [ -n "$RESPAWN_HOOK" ]; then
      if [ -n "$DRY_RUN" ]; then
        log "[DRY_RUN] would fire respawn hook for role=$ROLE: $RESPAWN_HOOK"
      else
        "$RESPAWN_HOOK" "$ROLE" >/dev/null 2>&1 || log "respawn hook failed for role=$ROLE"
      fi
    fi
    continue
  fi

  # Healthy heartbeat but loop not yet overdue → all good.
  if [ "$OVERDUE" -lt "$GRACE" ]; then
    # Clear any stale dedup so the NEXT genuine stall re-arms.
    rm -f "$STATE_DIR/$ROLE.resume" "$STATE_DIR/$ROLE.dead" 2>/dev/null || true
    log "role=$ROLE healthy (hb ${HB_AGE}s, loop overdue ${OVERDUE}s < grace ${GRACE}s)"
    continue
  fi

  # STATE 1 — ALIVE + LOOP-DEAD: heartbeat fresh, but the wake-loop is overdue
  # past grace (or next_wake was empty/stale). THE SPOF case → auto-resume.
  SF="$STATE_DIR/$ROLE.resume"
  KEY="$NEXT_E"   # frozen while stalled (no new wake) → one resume/window; changes on recovery.
  if [ -f "$SF" ] && [ "$(cat "$SF" 2>/dev/null)" = "$KEY" ]; then
    log "role=$ROLE loop-dead (already resumed for this window, key=$KEY) — skip"
    continue
  fi
  # DRY_RUN must NOT mutate dedup state — otherwise a dry-run against the real
  # state dir would suppress the NEXT genuine cron resume for this stall window.
  [ -z "$DRY_RUN" ] && { echo "$KEY" > "$SF" 2>/dev/null || true; }
  log "role=$ROLE ALIVE+LOOP-DEAD (hb ${HB_AGE}s fresh, loop ${OVERDUE}s overdue ≥ grace ${GRACE}s) — RESUME"
  resume_pane "$ROLE"
done

log "sweep complete"
exit 0

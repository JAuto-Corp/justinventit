# External Pacemaker — wake-loop supervisor

The pacemaker (`scripts/pacemaker.sh`) is an **external, out-of-band supervisor**
that keeps autonomous agent wake-loops alive. It is the framework's #1 load-bearing
reliability fix.

## The problem it solves

Autonomous roles run a **self-perpetuating wake-loop**: every turn schedules its own
successor (an in-session `ScheduleWakeup` / `/loop`). That makes the loop the *only*
continuity mechanism — and therefore a single point of failure. If a transient
model-API error cuts a turn **before** it re-arms the next wake, the OS process is
still alive but the loop is dead:

> **live process, dead loop.**

Without an external pacemaker the role goes inert until a human pastes a prompt to
revive it. The pacemaker eliminates that human-paste dependency. With it running,
the in-turn `ScheduleWakeup` becomes a *fast-path optimization*, not the sole thread
of continuity.

## The liveness contract

The pacemaker reads each role's cadence file and reasons over **two independent
signals**:

| Signal | Field | Meaning |
|-|-|-|
| **Heartbeat** (process-alive) | `heartbeat_at:` | Written every turn-end by the Stop hook. Fresh ⇒ the process is alive and taking turns. **Authoritative** — file mtime is not trusted (anything can touch the file). |
| **Cadence** (intent / loop) | `next_wake_at:` | When the role itself said it would next wake. Fresh ⇒ the loop is armed. Stale / `none` / overdue-past-grace ⇒ the loop is dead. |

These two signals define exactly two actionable states, each with one action:

| State | Detection | Action |
|-|-|-|
| **ALIVE + LOOP-DEAD** | heartbeat fresh **and** `next_wake_at` stale/`NONE`/overdue past grace | **RESUME** — inject the resume prompt into the role's tmux pane via `tmux send-keys`. The auto-recover; no new process. |
| **PROCESS DEAD** | heartbeat absent or older than `HEARTBEAT_DEAD` (default 90 min) | **ESCALATE** — notify via the adapter; optionally fire `$PACEMAKER_RESPAWN_HOOK`. |

Two non-actionable states:

- **Healthy** — heartbeat fresh **and** `next_wake_at` fresh/upcoming → no action.
- **Dormant** — `next_wake_at: none` with the role intentionally parked → skipped.
  A role that is genuinely done writes `none` to opt out of supervision.

**Grace window** per role = `max(GRACE_FLOOR, 2 × cadence_seconds)` (default floor
45 min). Real API stalls persist for many minutes; the floor keeps a role that is
mid-long-turn from being falsely resumed.

## The cadence file format

One file per role, `<role>.txt`, in the cadence directory. The role's Stop hook
appends/updates it each turn-end:

```
state: awake
role: a
heartbeat_at: 2026-06-16T04:34:10Z      # process-alive (authoritative)
wake_count: 113
cadence_seconds: 1800                    # or cadence_min:
context: one-line narrative of current intent
next_wake_at: 2026-06-16T05:04:10Z       # loop-alive; or `none` to go dormant
```

`heartbeat_at` and `next_wake_at` are ISO-8601 UTC. `next_wake_at` may be omitted
(some roles run a heartbeat-only format) — the pacemaker then uses the heartbeat as
both signals (it can still detect PROCESS-DEAD, just not loop-death independently).

## tmux pane-naming assumption

The auto-resume targets a tmux session/window via `send-keys`. The default target
template is the **role name itself** (`PACEMAKER_TMUX_TARGET="{role}"`), i.e. each
role runs in a tmux session named after the role:

```bash
tmux new-session -d -s a   # role "a" lives in tmux session "a"
```

`{role}` is substituted at resume time. If your roles live in **windows** of one
session, set e.g. `PACEMAKER_TMUX_TARGET="cluster:{role}"`; if in **panes**, use the
`session:window.pane` form. The target must be a valid `tmux send-keys -t <target>`
address. If the session is missing, the pacemaker escalates via the notify adapter
instead of silently failing.

> **This is the main wiring assumption to confirm for your environment.** See Open
> questions below.

## Notification adapter

The escalation channel is **pluggable** — the framework never hardcodes a vendor.
Set `PACEMAKER_NOTIFY`:

| Value | Behaviour |
|-|-|
| `none` (default) | log only |
| `desktop` | `notify-send` (Linux) or `osascript` (macOS) |
| `sms` | runs `$PACEMAKER_SMS_CMD "<message>"` — you supply the send command (Twilio, a gateway, etc.) |

## Configuration (env vars)

| Var | Default | Purpose |
|-|-|-|
| `PACEMAKER_CADENCE_DIR` | `./context/cadence` | where the `<role>.txt` files live |
| `PACEMAKER_STATE_DIR` | `<cadence>/.pacemaker-state` | dedup state (one action per stall window) |
| `PACEMAKER_ROLES` | auto-discover `*.txt` | explicit space-separated role list |
| `PACEMAKER_GRACE_FLOOR` | `2700` (45 min) | min overdue before loop counts dead |
| `PACEMAKER_HEARTBEAT_DEAD` | `5400` (90 min) | heartbeat age ⇒ process-dead |
| `PACEMAKER_NOTIFY` | `none` | `sms` / `desktop` / `none` |
| `PACEMAKER_SMS_CMD` | — | send command when notify=sms |
| `PACEMAKER_RESUME_PROMPT` | generic mechanism-framed prompt | text injected on resume |
| `PACEMAKER_TMUX_TARGET` | `{role}` | tmux target template |
| `PACEMAKER_RESPAWN_HOOK` | — | optional script `$1=role` on process-dead |
| `PACEMAKER_DRY_RUN` | — | classify + log only; no send-keys, no notify |

## Wiring the host cron

The pacemaker is designed to run from a **host crontab** — out of band, so it can
never itself stall (it is not part of any agent loop). Every 5 minutes is a good
default:

```cron
*/5 * * * * PACEMAKER_CADENCE_DIR=/path/to/project/context/cadence \
            PACEMAKER_NOTIFY=desktop \
            /path/to/project/scripts/pacemaker.sh >> /tmp/pacemaker.log 2>&1
```

It is **idempotent**: a per-role dedup file (keyed on the frozen reference epoch of
the stall) ensures exactly one resume / one escalation per stall window. Re-running
the cron does not re-spam. The dedup clears automatically once the role recovers
(its `next_wake_at` advances), re-arming a future resume.

## Why this is safe (no ghost-cron / split-brain)

This is a **passive supervisor**. It does **not**:

- create wake-crons, or
- re-invoke any conversation headlessly, or
- spawn a second session for a live role.

The only thing it does to a live role is `send-keys` a resume prompt into that
role's **existing** pane — a session-bound nudge identical to a human paste. There
is no second invocation, so there is no split-brain or shared-cursor race. (This is
the lesson from systems where a `CronCreate` wake-backup survived a reboot and
resurrected as a headless ghost racing the live session — the pacemaker structurally
cannot do that.)

## Solo mode (N=1)

The wake-loop SPOF is identical at N=1 and N>1, so the guard is identical. At N=1,
list your single role's cadence file (or let auto-discovery find it) and the
pacemaker guards that one session's loop. No coordination tier is required — the
pacemaker is part of the liveness primitive, not the multi-agent machinery.

## Dry-run / smoke test

```bash
PACEMAKER_DRY_RUN=1 \
PACEMAKER_CADENCE_DIR=scripts/fixtures \
PACEMAKER_STATE_DIR=/tmp/pm-state \
scripts/pacemaker.sh
```

The `scripts/fixtures/` directory ships sample cadence files for every class
(alive+loop-dead, healthy, dormant, process-dead, heartbeat-only). The dry-run logs
"would resume pane X" / "would escalate role Y" and sends nothing — use it to
validate the classification logic against your own cadence files before wiring the
cron.

## Open questions / environment-specific

1. **tmux pane naming** is the load-bearing assumption. The default (`{role}` = a
   session per role) matches the simplest setup; confirm how your roles are hosted
   (session-per-role vs windows vs panes) and set `PACEMAKER_TMUX_TARGET`
   accordingly. If roles are not in tmux at all (e.g. a different terminal
   multiplexer or a headless launcher), the resume mechanism needs a different
   injector — the classification logic is reusable, only `resume_pane()` changes.
2. **Resume-prompt content** — the default is generic and mechanism-framed. A
   project with a richer re-orient sequence (a boot-prompt re-read chain) should
   override `PACEMAKER_RESUME_PROMPT` to point the role at it.

# The Dev-Log — record-as-byproduct coherence

> The dev-log is the **N=1 coherence engine** — the portable core that lets a
> single agent answer "where did I leave everything" after any gap (a compaction,
> an overnight, a 38-hour model swap). It is the generalized **Orchestration Hub**:
> at solo it is the whole coherence story; at cluster the *same* primitive also
> drives coordination as a byproduct.

## The one idea: recording must be cheaper than not-recording

A dev-log dies on **write-friction**, not on schema. The lesson from the source
system was a 1.2MB write-only state file and a set of structured tables that went
unused because writing to them cost more than skipping. So the dev-log is built
on two rules:

1. **One append per event.** `scripts/log.sh <type> ...` is a single command.
   No multi-file ceremony, no "remember to also update X".
2. **Transport is a side-effect of recording.** In cluster mode the *same*
   `log.sh` call that records an event ALSO emits the mailbox message. You never
   "log it and then message it" — logging *is* messaging. (At solo there is no
   mailbox; it just appends.)

## The model

**Append-only event stream + derived current-state views.** You never edit a
"current state" file (those drift write-only). You append events; the *current
state* (open threads, pending gates, blocked-on-user) is **computed on read** by
folding the stream. The record can never disagree with the state because the
state is derived from the record.

### Threads are the spine

Every event carries a `thread_id`. A **thread** is the unit of coherence — a line
of work, a question, an investigation. Decisions, actions, findings, and gates
all hang off a thread. A thread is **open** until a `done` event resolves it.
"Where did I leave everything" = the set of open threads + what each is waiting on.

### AUTO vs MANUAL

| Field | Source | Notes |
|-|-|-|
| `ts`, `id`, `actor` | AUTO | stamped on every append |
| `last_event_at`, staleness | AUTO (derived) | computed in the views, never stored |
| `links` / `resolves` | AUTO | events reference threads / prior event ids |
| `intent_anchor` | **MANUAL** | a **quoted source** — the anti-drift anchor. Cite *why*, in the originator's words. |
| decision text / state / the human call | **MANUAL** | judgment, not mechanics |

The split is deliberate: the agent should never hand-maintain what a timestamp
or a fold can derive, and should always supply the judgment a machine can't.

## Event types

| Type | Command | What it records |
|-|-|-|
| thread | `log.sh thread <id> "<title>" [--intent "<quote>"]` | opens / re-titles a thread (the spine) |
| decision | `log.sh decision <id> "<text>" [--anchor "<quote>"]` | a judgment call / trade-off resolution |
| action | `log.sh action <id> "<action>" [--for user\|self\|<role>] [--urgency now\|soon\|whenever] [--unblocks "<why>"]` | a to-do; `--for user` feeds the blocked-on-user queue |
| finding | `log.sh finding <id> "<finding>" [--severity high\|med\|low] [--class <tag>]` | a discovery / anomaly worth keeping |
| gate | `log.sh gate <id> "<what>" [--on user\|ci\|<role>]` | a pending gate (work waiting on something) |
| done | `log.sh done <id> [--ref <event-id>]` | resolves a thread, gate, or action |
| note | `log.sh note <id> "<text>"` | plain narrative event on a thread |

Cross-cutting flags on any subcommand: `--to <recipient>` (cluster mailbox target,
default `all`), `--actor <name>`, `--json` (emit the event JSON, for tests/piping).

## Derived views (read)

```bash
scripts/log.sh view threads        # open threads + last_event_at + staleness
scripts/log.sh view gates          # pending gates (unresolved)
scripts/log.sh view user-actions   # blocked-on-user queue, ordered by urgency
scripts/log.sh view thread <id>    # full event history for one thread
```

## The attention query (wake / session-start)

```bash
scripts/log.sh attention
```

The **one read** that opens a session: blocked-on-user + pending gates +
open/stalled threads, in one payload. The `session-start` hook runs it
automatically, so every fresh or post-compaction session lands on "here is
where everything stands" instead of scraping files. This is the solo agent's
core payoff and the wake tick at cluster scale.

## Where the data lives (and why it's safe)

- **Default: in-repo** at `context/devlog/events.jsonl` — the N=1 coherence
  anchor. The **structure** (`context/devlog/`, its README) is git-tracked; the
  **data** (`events.jsonl`, `outbox/`) is **gitignored** and **excluded from
  `copier update`**, so framework updates never clobber your record.
- **Relocate for cluster:** set `DEVLOG_DIR=~/.<project>-devlog` so multiple
  worktrees share one stream, and `ORCHESTRATION_TIER=cluster` so each append
  also emits the mailbox message. Configure the transport with `DEVLOG_MSG_CMD`
  (e.g. `scripts/msg.sh`); absent that, `log.sh` drops message files in
  `outbox/` for the coordination tier to drain.

## Environment

| Var | Default | Effect |
|-|-|-|
| `DEVLOG_DIR` | `<repo>/context/devlog` | relocate the stream (cluster / multi-worktree) |
| `ORCHESTRATION_TIER` | `solo` | `cluster` makes each append ALSO transport |
| `DEVLOG_MSG_CMD` | _(file drop)_ | mailbox send command, e.g. `scripts/msg.sh` |
| `DEVLOG_ACTOR` | `me` | the actor stamped on events / mailbox `from` |
| `STALE_HOURS` | `24` | a thread idle longer is flagged STALLED |

## Worked example (solo)

```bash
scripts/log.sh thread auth-refresh "Refresh-token rotation" \
  --intent "user: 'sessions silently die at 1h, fix the rotation'"
scripts/log.sh decision auth-refresh "Rotate on the 401 retry, not a timer" \
  --anchor "round-table: relax-not-force — let the client re-solve"
scripts/log.sh action auth-refresh "Confirm WorkOS rotation window" --for user --urgency soon
scripts/log.sh attention      # -> shows the open thread + the blocked-on-user item
scripts/log.sh done auth-refresh   # close it when shipped
```

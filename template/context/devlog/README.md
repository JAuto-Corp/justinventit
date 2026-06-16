# context/devlog/ — the dev-log event stream (DATA)

This directory holds the append-only dev-log: `events.jsonl`. The **structure**
is tracked; the **data** (`events.jsonl`, `outbox/`) is gitignored — it is local,
stateful, per-checkout, and excluded from `copier update` so framework updates
never clobber your live record (decision f).

- **Write** events with `scripts/log.sh` (one append per event).
- **Read** derived current-state with `scripts/log.sh view <threads|gates|user-actions>`.
- **Wake/session-start** with `scripts/log.sh attention` (the one query).

See `docs/DEVLOG.md` for the model and full command reference.

> **Relocate for cluster:** set `DEVLOG_DIR=~/.<project>-devlog` (and
> `ORCHESTRATION_TIER=cluster`) so multiple worktrees share one stream and the
> same `log.sh` call also emits the mailbox message. At solo, leave it in-repo.

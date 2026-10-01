# Project-scoped cadence and report-only liveness

`scripts/cadence.sh` publishes declared intent; `heartbeat-hook.sh` refreshes an
existing declaration. `stall-watchdog.sh` performs one local observation sweep.
`pacemaker.sh` is a compatibility entry to the same report-only observer. Neither
entry recovers a session or installs a scheduler.

## BREAKING-CHANGE: adoption and rollback

W-C3 retires the released automatic prompt injection, respawn and external
notification behavior. Every `PACEMAKER_*` setting, `CADENCE_DIR` and independent
watchdog path/effect override now refuses with migration guidance, before opening
those targets. Keep old cadence and dedup files as historical data; they are not
automatically migrated into the new project-bound store. Human/external recovery
is an operator decision. No lease/fencing-based recovery replacement is implied.

Before adopting, commit project-owned changes, save `.copier-answers.yml` and its
resolved revision, and rehearse Copier update in a disposable clone containing
the saved defaults and legacy state. The answer keys/values `external_pacemaker:
tmux-supervisor|host-cron|none` remain compatible. A selected mode enables the
cluster Stop heartbeat producer; neither selection promises injection or installs
cron. Project-owned `AGENTS.md` is retained; incorporate contract changes yourself.

Projects retaining the released behavior can pin `jv-v0.2.3` instead of updating
to HEAD (`copier copy --vcs-ref jv-v0.2.3 ...` for a new disposable copy). Roll back
with `git revert <adoption commit>` (`-m 1` for a merge) to restore generated files
and answers, then pin the restored template revision for later updates. Scheduler
or service configuration is external to that Git revert and needs separate
operator review. Framework tests update disposable consumers only; release bodies
are data, never executed to test migration.

## Explicit identity and producer

Runtime dependencies are Python 3.12+, Bash 4.3+, jq, GNU coreutils/findutils and
util-linux flock on Linux. Tests use Linux inotify and synthetic process files.

Use the same project binding as the portable mailbox and launcher:

```bash
export JV_PROJECT_ID=myproject
export JV_PROJECT_ROOT=/absolute/project/root
export JV_STATE_ROOT=/absolute/operator-owned/state
export JV_ROLE=A
scripts/cadence.sh a awake 900 'working on assigned slice'
scripts/cadence.sh a sleeping 900 'next intended check'
scripts/cadence.sh a standby --doorbell mailbox:a 'waiting for mail'
scripts/cadence.sh a dormant --conclusion 'completed' --brief /absolute/brief.md
scripts/stall-watchdog.sh --dry-run
scripts/stall-watchdog.sh
```

There is no cwd, home, unqualified role or legacy directory fallback. Worktree
commands keep `JV_PROJECT_ROOT` bound to the configured project root. Each project
has `<JV_STATE_ROOT>/<JV_PROJECT_ID>/project.json`; cadence files are
`cadence/<lower-letter>.txt`. The observer requires an existing valid binding.
Nested state symlinks and mismatched project roots refuse before state access.

Awake and sleeping publish canonical `active`. Awake increments `wake_count`;
sleeping preserves it. Active cadence defaults to 900 seconds, is a positive
bounded decimal integer, and computes `next_wake_at`. Standby/dormant use zero and
`event`/`none`; an optional source-style numeric positional value is discarded.
Standby requires its own `mailbox:<letter>` declaration. Dormancy requires a
nonempty conclusion and an existing absolute brief. Publication does not arm any
wake, doorbell or canary.

Records carry project/role identity, state, UTC `heartbeat_at`, `next_wake_at`,
wake count, cadence seconds, context and applicable doorbell/conclusion/brief.
Explicit publication and heartbeat refresh share the same per-seat OS lock
(`cadence/.<letter>.lock`), read inside that lock, validate and atomically replace
the record. Invalid input/prior state or failed publication preserves prior bytes.
Heartbeat-only updates preserve every intent/ceremony field and require an existing
record. The neutral hook bounds lock waiting and returns zero with diagnostics on
refusal. The actual Claude Stop wrapper delegates for cluster + selected pacemaker;
solo/none is explicitly inert. Codex hook installation remains a later adapter slice.

## What observation proves

The roster is the union of local session records and cadence files. Cadence-only
seats are marked unregistered; record-only seats report missing cadence. Malformed
or unreadable evidence remains visible and later seats are still evaluated.

| State/evidence | Local finding |
| --- | --- |
| Active schedule | `now - next_wake_at >= max(2700, 2 * cadence_seconds)` |
| Active heartbeat | `now - heartbeat_at > 3600`, independently of the intended wake |
| Standby mail | Oldest undrained inbound event age **strictly >1800 seconds** |
| Dormant | Suppression requires conclusion plus existing absolute brief |
| Booted/parked | Launcher-owned; no heartbeat-floor finding |

A fresh heartbeat cannot erase an overdue schedule. A future intended wake cannot
erase the heartbeat floor. The schedule reference intentionally preserves the
source's earlier `next_wake_at` behavior; it differs from the normative
`max(heartbeat,next_wake)` table. File mtime never substitutes for event timestamps.
Idle standby does not alert merely because its heartbeat is old.

Mail inspection is non-consuming, across directed and broadcast projections,
excluding self-notes and this seat's outbound broadcasts. Each reader/stream has
its own byte cursor. An absent virgin cursor means byte zero; corrupt/unreadable
cursors, partial lines, bad timestamps and missing mail evidence are unknown.
Fresh arrivals cannot reset the oldest undrained age. No processing or notification
cursor is advanced, and no mailbox read command is invoked.

Optional process observation requires an explicit absolute
`JV_WATCHDOG_PROC_ROOT`. Without it, observation is unavailable. The process view
must be the operator-selected **host namespace**; an empty container view cannot
prove host absence. Matching requires exact NUL-delimited project ID, canonical
project root and uppercase role plus an interactive Claude/Codex argv. Shells and
one-shot invocations do not certify presence. Unreadable evidence is unknown.
No signal, provider, tmux, scheduler or external notification command is invoked.

This is **limited observation**: process presence does not prove loop progress,
intent does not prove a wake is armed, and a stale heartbeat does not prove death.
The normative leased-canary/heartbeat detector, lease/CAS fencing and multi-backend
control plane remain unimplemented. There is no protocol-complete health claim.

## Reports, backoff and dry-run

Stdout is JSONL: a `kind: seat` decision per enumerated seat, followed by one
`kind: complete` record with enumerated, evaluated, unknown and reported counts.
Evaluated + unknown equals enumerated. Zero exit means completed observation,
not healthy seats. Required evidence/output failures are nonzero and diagnostic.

Local alerts append to `watchdog/alerts.jsonl`, identifying project, role, reasons
and episode. Checkpoints are `watchdog/<letter>.json`. A project sweep lock
serializes ordinary concurrent reports. An ongoing episode survives changing
references/additional detectors: report immediately, then after grace, doubled
intervals capped at 24 hours, measured from the last successful report. Recovery
or earned dormancy clears the episode. Failed append never advances its delivery
checkpoint. A crash/failed checkpoint after append can duplicate on retry: this
is not an exactly-once transport.

`--dry-run` prints proposed decisions without any mutation: no identity/bootstrap,
directory or lock creation, log append, checkpoint update or recovery cleanup.
The historical `PACEMAKER_DRY_RUN` variable refuses; use the CLI option. Explicit
invocation, scheduler selection and any external response are operator-owned.

## Origin and checks

The W-C3 extraction preserves source lessons dated 2026-07-26 (frozen-epoch silence
and dry-run budget), 07-27 (state-first, earned dormancy), 07-28/29 (`b88a10f15`,
revival disabled by default), 09-23 (`317dd77f3`, doorbell-only standby and one-shot
exclusion), 09-24 (`e0128d1a6`, roster union) and 09-27 (`b73dfd1b4`, fixture
containment). These historical references are provenance, not operating rules.

`tests/test_liveness.py` uses real rendered consumers, a closed PATH, sanitized
child environments and synthetic process roots. The bounded source gate runs
before candidate/mutant execution; it is not a hostile-code sandbox. The framework
runner exercises saved release defaults, update and adoption-commit rollback.
Destructive source recovery tests are deliberately excluded. Accepted mailbox and
launcher regressions remain required when their shared binding helper changes.

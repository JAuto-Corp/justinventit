# Shared host observations

`scripts/pace.sh` reports selected account usage; `scripts/disk-watch.sh` reports
selected filesystems. These observations are shared host facts, not a project's
quota, spending permission or automatic cleanup policy. No provider is called.

Bind the project using the existing [cluster procedure](CLUSTER.md), then supply
`JV_PROJECT_ID`, `JV_PROJECT_ROOT`, `JV_STATE_ROOT` and an explicit absolute
`JV_HOST_ROOT`. The observers verify binding without initializing project state.
They create private state only in `JV_HOST_ROOT/observability`. Cooperating
projects using the same host root share history, locking and alert suppression.

For usage, select either or both of these read-only inputs:

- `JV_USAGE_ANTHROPIC_FILE`: a regular statusline snapshot with UTC `ts` in
  `YYYY-MM-DDTHH:MM:SSZ` and `rate_limits` containing `seven_day`, `five_hour`
  and/or `model_scoped`. Usage accepts `used_percentage` or `utilization`,
  with integer epoch `resets_at`. Model entries need a string `display_name`;
  output uses its full SHA-256 as an opaque stable ID, never its raw name.
- `JV_USAGE_CODEX_ROOT`: the explicit sessions directory. Read at most six
  newest `*/*/*/*.jsonl` files ordered by mtime then path, each at most its last
  400,000 bytes. Only structured top-level or event-payload `rate_limits` count.
  Partial first lines and malformed records are skipped. No HOME fallback.

Both `pace.sh` and the uninstalled `usage-hook.sh` use weekly pacing: a Codex
primary or secondary window must be exactly 10,080 minutes. Short windows below
1,440 minutes are separately reported without pacing math. Without valid weekly
evidence, fallback tries the next candidate; short-only evidence remains weekly
unavailable. The newest valid credit balance is selected independently across the same
bounded records/files, even from a short-only record while weekly evidence falls
back to an older record. A failed candidate is skipped and counted; selected
weekly data is retained and appended to history. Such partial collection returns
nonzero from the CLI and zero from the hook. Later credit search can add credits,
but cannot remove or replace selected weekly observations.
It is a separate balance/spend series, with explicit `has_credits=true`, `unlimited=false` and finite nonnegative balance.

Weekly target is elapsed percentage of the window; within ±10 points inclusive
is `on-pace`. Burn uses same-series/reset/window samples from the last three
hours, including the current sample, with at least 1,800 seconds of span.
Credits use balance decline per hour. Expired windows get no sustainable rate
and no history append. Age above 1,800 seconds is stale; future/unknown age cannot
be fresh. Snapshot and history reads are limited to 1 MiB each; oversized
snapshots refuse, complete history tail rows remain usable with a truncation
warning. History is one five-field `usage.tsv`, not summed consumption. Samples
must satisfy the same numeric ranges as live data: quota 0–100, finite credit
balance 0–10^20, bounded epochs/positive quota windows, and zero reset/window for
credits. Skipped invalid/incomplete history rows are counted in diagnostics and
cannot influence burn. Very large provider numbers are rejected before float
conversion; a validation failure remains isolated to that provider.
Before changing provider accounts, stop collectors and archive the old history.

For disk, set `JV_DISK_ROOT` and optionally `JV_DISK_SECONDARY_ROOT` to explicit
existing directories. GNU `df` observes only those paths. Primary usage ≥85%
alerts once per UTC day and five-point bucket. Secondary available space below
10 whole GiB alerts once per day and two-GiB bucket. Keys include the selected
target and metric, not the invoking project's ID. Two paths on the same device
can therefore have separate keys. There is no disk discovery or cleanup.

Default alerts append JSON to `disk-alerts.jsonl`. An optional absolute executable
`JV_OBSERVABILITY_NOTIFY_BIN` receives one JSON record on stdin, no arguments,
with a ten-second timeout. Select one director to own routing for a shared host.
Adapter exit 0 means accepted by that adapter, not verified human receipt.
Readers use only complete newline-terminated records. Malformed/incomplete rows
in the inspected tails are skipped and counted in diagnostics (including Codex
JSONL). Under the shared lock, appenders preserve every existing byte: an
unfinished alert is sealed with a newline before the new complete JSON record;
an unfinished history row is sealed with TAB `partial` NEWLINE before appending.
The marker keeps a truncated numeric last field permanently invalid as TSV.
A complete JSON object that lacked only its newline can become readable after
sealing. Alert inspection is capped at 1 MiB, with a truncation warning.
Only successful writing/flushing of the new complete delivery row permits a
suppression checkpoint. Only accepted delivery is checkpointed in `disk-state.json`. Failed delivery or
checkpoint remains retryable; a crash between them can duplicate a notification.
Suppression retains prior daily keys; operators may archive state while all
collectors are stopped. The lock wait is bounded at one second.

CLI output is one JSON object with `observations`, fixed `errors` and `warnings`;
nonzero status means configuration, collection or persistence was incomplete.
A bad provider or secondary target preserves valid independent output/history
or alerts from the same invocation. Common binding/state failure stops collection.
The hook exits silently before any data access unless `JV_ROLE` is `o` or `O`.
For that director it prints at most one 4 KiB `[usage]` line, labels truncation,
and always exits 0. Filesystem stalls are outside this timeout claim.

All paths must be absolute, with ordinary directories/regular files, searchable
ancestors and no static aliases; host state must not overlap project/provider
state. This is a reviewed, cooperating-code accident boundary, not a hostile
filesystem or code sandbox. Provider input is data, never executed. No hook,
statusline producer, cron, daemon, provider profile or live notifier is installed.
Provider shapes are pinned extraction compatibility, not a claim about future
releases. See [provenance](CLUSTER_PROVENANCE.md) and the synthetic offline
`scripts/tests/test_observability.py` suite.

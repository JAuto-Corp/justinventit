# W-C5: explicit host usage and disk observations

Status: **SPEC and finite test list only; awaiting o's audit before RED or implementation.**
Commission: o `01M3WF143WT7SP86CTFW917JKS`, 2026-10-01. W-C4 is accepted
at `be4952b835bc17da51a60304fba2271acb6fcacb` and awaits the hosted lane;
o explicitly authorizes this next local slice in parallel with that wait.
Author a, director o, integrator i. Extraction charter X1–X6 applies.

## Intent

Extract the existing usage-pacing and disk-watch utilities so a generated
project's director can see shared provider-account usage and host storage
pressure from explicitly selected inputs. Preserve the pacing thresholds,
stale-data qualification and bounded disk-alert suppression, while separating
project identity/routing from host-wide observations. Report observations and
uncertainty; do not turn them into provider spending authority or cleanup policy.

## Non-goals

- No provider API calls, credentials, billing reconciliation, budget allocation,
  model switching, quota enforcement or per-project attribution of shared usage.
- No crash-dump deletion, worktree/node_modules pruning, Docker management,
  process discovery/signalling, automatic recovery or shared build-lock changes.
- No scheduler, daemon, cron, live host installation or provider hook/statusline
  wiring. W-D owns the adapters; the source statusline is read for its data
  contract only. Focus-on-wake and browser interaction guidance remain queued.
- No authentication between cooperating local projects, hostile-code sandbox,
  hostile concurrent filesystem-swap defense or exactly-once external delivery.
- No execution of the installed source tools or reads of real provider sessions,
  usage snapshots/ledgers, credentials or customer data during extraction proof.

## Source pin and retained boundaries

Installed host source files were read fully and captured read-only on
2026-10-01. These are byte snapshots, **not a claimed Git revision**. The private
source inventory records exact capture time, byte/line counts and full hashes.

| Source | Lines | SHA-256 | Retained contribution |
| --- | ---: | --- | --- |
| `usage/usage-hook.py` | 96 | `4488d7231cc6fa577ce80cfa0e5948c843f2c25d90ca20faa3e58332689d36e5` | Director-only, nonblocking compact output; latest supported quota observations, elapsed-window target, ±10-point verdict, 3-hour burn, 30-minute history/stale boundaries, credits as a separate series. |
| `usage/pace.sh` | 58 | `4e7ef829a97764da7a944eb1f64b3fb390b985f0e4b7aa8cf686c9e268466b1e` | Explicit CLI snapshot, quota-window presentation, fresh readings ahead of old ledger rows and sustainable rate. Its comments promise manual arguments that its implementation does not consume; no such interface is extracted. |
| `usage/statusline.sh` | 13 | `6a9503bc739edbefb9d71f723b67a820c80bdf08c94c7134a54e22f89d7f10cc` | Producer envelope `{ts, model, rate_limits}`. Read-only contract reference; producer installation is deferred. |
| `scripts/disk-watch.sh` | 36 | `ebb6028975f527c81cf88b006b05e6775a0eb5800008a5eec474b979cd580f27` | Primary filesystem ≥85% with daily five-point buckets; optional second filesystem below 10 GiB with daily two-GiB buckets. Exclude its destructive crash-dump purge and hard-coded notification route. |

Source reasons retained as dated provenance: usage pacing was requested on
2026-09-28; credits were added on 2026-09-30 because subscription percentages
alone do not describe available credits. Disk pressure caused a 2026-09-25
disk-full crash and 2026-09-08/29 Docker outages on the second filesystem.
The 2026-09-30 portability audit identifies shared account/storage facts despite
separate projects. These origins explain the utilities; local paths, account
balances and product-specific recovery instructions are not operating rules.

The three source consumers have no imported project-code dependency. Dependencies
are Python's standard library and shell utilities; the notification edge calls
the source mailbox and is replaced with the explicit adapter below. No focused
source suite was found in the inspected usage/scripts inventory. Do not claim
source-test conformance. Reuse accepted `jv-project.sh` binding verification and
the existing shell-dispatch/Python pattern without changing shared helpers.

## Threat model: reviewed-code accident boundary

All configuration, operating code, adapters and fixture builders are reviewed,
cooperating local code. Provider observations are **data**, not commands or
authority. Path/binding checks protect against accidental wrong roots and static
aliases; numeric/schema checks prevent malformed observations from becoming a
healthy reading or crashing unrelated observations.

Any pre-execution source gate is an accident boundary whose authority is the
committed gate plus its reviewed policy, changed only through a reviewed diff.
Use the W-C4 lesson from the start: a candidate/test that changes policy on disk
or registers images in memory is outside that boundary. A generated child may
load its own candidate-supplied gate/policy. A separate-root witness does not
establish independent authority for that loading path. The accepted W-C4 pidfd
self-registration limitation (o `01M3WEG3R9Y9W6YR6MBWXF50Q8`, 2026-10-01)
applies to the same claim here. Runtime isolation against adversarial candidates
would be a separate slice; do not build it or claim it in this proof.

Before running candidate or mutant children, manually review the declared
operating closure and use a fixed, reviewed complete-image allowlist for that
closure and finite safe mutants. Every sourced/launched helper and external
command is inventoried; unknown changed images refuse until a reviewed update.
This does not authenticate the supplied workload/adapter or protect a policy
from its own author. Malicious effect seeds remain data. A newly found bypass
class goes to o for disposition, not an expanding deny-list patch cycle.

## Proposed delivered contract

### Configuration and state

Require existing `JV_PROJECT_ID`, `JV_PROJECT_ROOT`, `JV_STATE_ROOT` binding;
use the accepted pure verifier, without initializing or changing project state.
Require explicit absolute `JV_HOST_ROOT`, using W-C4's host-root convention.
W-C5 does not call the capacity wrapper and has no code dependency on W-C4.
Its state is `<JV_HOST_ROOT>/observability/`; observations and history are shared
host/account facts, never partitioned or summed by project ID.

Require explicit selected input paths: `JV_USAGE_CODEX_ROOT` (session directory)
and/or `JV_USAGE_ANTHROPIC_FILE` (statusline snapshot). An unset provider is
unconfigured, not a fallback to HOME/CODEX_HOME. Provider files are read-only.
Reject relative paths, symlinks/wrong types along selected input/state paths,
unsearchable ancestors and overlapping input/output trees before data access.
Ordinary directories and regular files only; no FIFO/device reads. The same
static-alias boundary applies to nested session candidates. There is no
automatic source-state migration or reading of old host defaults.

Usage history is one host `usage.tsv`, using the source's five fields:
epoch, series name, numeric value, reset epoch and window seconds. A checked,
bounded host observability lock serializes history and disk suppression updates;
do not reuse the heavy-job capacity lock. Create only this private state directory
and its files. Lock/write failure is unknown, never successful persistence.
Cooperating projects reading the same provider inputs see the same observations;
repeated samples are observations, not summed consumption. Before changing
configured provider accounts, the operator must stop collectors and archive the
old usage history; mixed-account attribution and automatic migration are absent.

### Usage interfaces and calculations

Deliver `scripts/pace.sh` as the explicit CLI and `scripts/usage-hook.sh` as an
uninstalled director-wake entry, sharing one collector/calculation implementation.
The hook does nothing, including no input/state access, unless explicit `JV_ROLE`
is `o` (case-insensitive). For the director it emits at most one 4 KiB compact
line (label truncation explicitly) and exits 0 on errors; it performs no unbounded
lock wait or subprocess call. This is not a deadline on a stalled filesystem.
The CLI shows unavailable/stale states explicitly and returns nonzero for invalid
configuration or collection/storage failure. Neither entry calls a provider CLI.

Retain the source quota inputs, not arbitrary transcript text: Anthropic's
`seven_day`, `five_hour` and `model_scoped` records under `rate_limits`, and
Codex JSONL `rate_limits` records at the top level or under the event `payload`.
For Codex inspect at most the six newest regular candidates in the selected
sessions layout, deterministically ordered by mtime then path, and read at most
the last 400,000 bytes of each. Discard a partial initial JSONL record; skip
malformed/truncated records. Select the newest usable observation, falling back
to an older file only if no supported observation is present. Text resembling
rate limits inside a prompt/string is not a provider observation. Output/state
contain only recognized metrics, fixed labels and bounded model identifiers;
no raw record, prompt, session identifier, token or transcript text is copied.

Accept finite numeric usage percentages 0–100, positive bounded window minutes,
bounded reset epochs and valid timestamps; reject booleans, NaN/infinity and
coercion from arbitrary prose. Missing values are unavailable, not zero used.
Anthropic `used_percentage`/`utilization` and Codex `used_percent` map to the
same internal metric. Normalize bounded model labels to safe printable series
identifiers within an Anthropic-model namespace, never another provider's series.
Credits require explicit finite nonnegative balance with
`has_credits=true` and `unlimited=false`; they are units, never quota percent.
Unknown fields are ignored, and incompatible provider formats are unavailable.
This is compatibility with the pinned source shapes, not a promise about future
provider releases. Synthetic fixtures supply these shapes; no live probe is used.

Target = elapsed fraction of the observation's window, clamped to 0–100%.
Within **±10 percentage points inclusive** is on pace; above/below is ahead/behind.
Those labels are descriptive, not permission to spend more. Remaining time is
clamped at zero; expired windows are labelled expired with no sustainable-rate
division. Sustainable rate is `(100-used)/hours_left` for a live window.
Burn uses valid samples of the same series AND reset epoch from the last three
hours, requiring at least two samples spanning 1,800 seconds. Source age above
1,800 seconds is labelled stale; missing/future timestamps are unknown, never
fresh. Fresh input overrides older ledger values. Do not append fabricated zero
samples or invalid/expired observations; malformed ledger rows are ignored with
an explicit CLI diagnostic, without losing other valid series.

Unify the hook/CLI arithmetic instead of retaining `pace.sh`'s incompatible
whole-window history calculation. A credit series uses balance decline per hour,
never quota-window math (the source's zero-window ledger row must not divide by
zero). Keep history and observation parsing bounded: snapshot/ledger reads at
most 1 MiB each; reject oversized snapshots, use only complete ledger tail rows,
and report truncated-history limits. A generated helper may use stdlib only.

### Disk observations and notification

Deliver `scripts/disk-watch.sh` as one explicit sweep. `JV_DISK_ROOT` selects
the primary filesystem; optional `JV_DISK_SECONDARY_ROOT` selects the second.
Both are explicit absolute, existing non-alias directories. No implicit `/`,
Windows mount, username, size cap or crash-dump path. Observe the selected
filesystems only (standard `df` via argv, no shell-evaluated command text).
Unknown/malformed measurements report unknown/nonzero, not healthy/free; a bad
second target does not discard a valid first observation. No cleanup occurs.

Retain primary ≥85% in five-point buckets (`floor(percent/5)*5`) and optional
secondary availability below 10 whole GiB as reported by GNU `df -BG`, in
two-GiB buckets. At threshold equality, primary 85 alerts and secondary 10 does
not. Deduplication is by UTC day, canonical target, metric and bucket under the
shared host lock; another project does not obtain a fresh budget for the same
host condition. Two configured paths on the same filesystem may still name
separate observation targets; no device registry or discovery is added.

One operator-selected director invocation owns notification routing for a shared
host. Default delivery is an append-only local `disk-alerts.jsonl` in the host
observation directory. Each bounded record includes source project ID, metric,
target and observed value; it makes no project-specific capacity claim. An
optional `JV_OBSERVABILITY_NOTIFY_BIN` must be an explicitly configured absolute
reviewed executable; invoke it directly with one JSON record on stdin, no shell
command string, and a fixed ten-second timeout. Its zero exit means accepted by
the adapter, not verified owner receipt. The adapter may bridge to that project's
mailbox, but this slice installs none and sends no live mail during proof.

Record a suppression checkpoint only after the configured sink accepts the
event. Append/adapter/checkpoint errors are visible, nonzero and retryable; never
mark a failed delivery as complete. A crash after sink acceptance but before
checkpoint can duplicate an alert on retry. The source prematurely touches its
key before sending; that ordering is intentionally corrected here. Lock waits
are bounded at one second; no background delivery/retry loop. For the nonblocking
usage hook, the same timeout is silently skipped; disk/CLI report it.

## Invariants and finite test list

| Invariant | Required behavior |
| --- | --- |
| I1 | Existing explicit project binding and explicit host/input/target paths determine every access; private host state stays separate from project/provider data. |
| I2 | Supported provider observations are bounded data; malformed, missing, stale or incompatible inputs cannot become healthy zero/fresh quota evidence or leak raw records. |
| I3 | Pacing, burn, expiry and credits calculations retain their stated boundaries and series/window identity; descriptive output grants no spending authority. |
| I4 | Host history and suppression are shared across cooperating projects, serialized, and honest about failed persistence; they never claim per-project quotas. |
| I5 | Disk sweeps observe only selected targets, preserve threshold/bucket boundaries, report unknown distinctly and perform no cleanup. |
| I6 | Local/optional adapter notification uses explicit routing and literal data; suppression follows acceptance, failures permit retry, and hook failure cannot block other seats. |
| I7 | Real generated consumers and finite mutants run only in reviewed synthetic fixtures under the stated accident threat model; no live provider/host/service action or automatic wiring. |

Each row is one positive/refusal group; variants below witness its stated
invariants. Commit RED before implementation; distinguish absent-feature failures
from later runtime behavior. Add cells only for a traced finding or surviving
invariant mutant. Setup/syntax errors do not count as mutant kills.

| Cell | Positive witness | Refusal/discriminating witness |
| --- | --- | --- |
| T1 → I1/I4 | Two bound scratch projects, same explicit host root/provider fixtures; distinct project-state canaries and matching shared observations. Paths contain spaces. | Missing/wrong binding, relative roots, static/nested aliases, unsearchable ancestor, special input file or input/output overlap refuse before foreign/provider writes; access observation plus unchanged canaries. Non-director hook touches nothing. |
| T2 → I2 | Synthetic Anthropic records and nested/top-level Codex quota records; latest usable fallback among six files; explicit stale/unknown reporting. | Missing fields, bad types/NaN/ranges, old/future timestamps, oversized snapshot, partial/oversized JSONL records, quota-looking transcript text and secret canaries; inspect both output streams and persistent state for leakage. No seventh-file fallback. |
| T3 → I3 | Fixed fixture time: target and ±10 equality, live/expired window, 1,800-second burn span, same-reset filtering, fresh reading override and separate credit spend. | Mutate threshold, zero-window division, reset filter, stale cutoff and fresh precedence; exact independently calculated expected values, no tests that recompute using production functions. |
| T4 → I4 | Interleaved project collectors and concurrent bounded sweeps preserve whole history rows and share disk suppression. | Checked-lock failure, ledger append/checkpoint fault and malformed/tail-truncated history; no reported persistence on failure or second-project fresh alert budget. |
| T5 → I5 | Fake `df` exact argv for selected primary/secondary paths, 84/85/89/90%, 9/10 GiB and later UTC day; both targets observed. | Unavailable/malformed `df`, bad target, source-like crash-dump fixtures and recording effect stubs; unknown stays unknown, no deletion or host discovery. |
| T6 → I6 | Default local sink and explicit fake executable adapter receive exact bounded JSON; repeat suppresses, new bucket/day alerts. | Adapter exit/timeout, append/checkpoint failure and shell metacharacters in paths/data; no premature checkpoint or shell execution. Non-director hook is silent/no-access; director errors exit 0, explicit CLI errors nonzero. |
| T7 → I7/X1–X6 | Actual task-disabled Copier cluster/solo consumers with closed environments, scratch HOME/provider/host roots, allowlisted commands and fixture-owned children; current four-answer matrix. | Before every candidate/mutant child, fixed reviewed source closure gates seeded unlisted images as DATA; recording provider/network/mail/tmux/deletion stubs stay unused. Missing helper refuses without partial collection. Scan generated operating files for coupling/secrets; provenance is labelled separately. |

Finite initial mutations (15): omit binding verification (T1); restore HOME
provider fallback (T1/T2); turn malformed usage into zero (T2); admit quota-shaped
prompt text (T2); ignore source age (T2/T3); change inclusive pace threshold (T3);
drop reset-epoch filter (T3); apply quota division to credit history (T3); let old
ledger override fresh observation (T3); ignore lock failure (T4); partition
suppression by project ID (T4); change disk threshold equality (T5); checkpoint
before failed sink (T6); remove non-director early exit (T6); add source crash-dump
deletion edge (T5/T7, refusal before execution, never a runtime kill). Runtime
mutants get reviewed safe image entries; source-refusal seeds remain data.

## Delivery and review gates

Proposed files: three entry scripts, the smallest shared shell/Python
observability helper needed for binding/collection, generated
`docs/HOST_OBSERVABILITY.md`, a CLUSTER link and dated provenance; bounded
generated-consumer tests plus existing CI/matrix integration. Do not edit
W-C4's accepted branch or shared earlier-slice implementations for convenience.
This branch starts at main `b5722babd54600ba28c09a68e9c0ada8667928cc`.

O audits this SPEC and test list → admitted folds → tests-only RED and review →
smallest GREEN implementation → all finite mutants, real generated consumers
and matrix → o-commissioned OpenAI code review/verdict → exact-head hosted CI
and i integration. The published provider-availability ruling supersedes the
charter's old Opus wording; no author reviewer or self-acceptance. Keep source
pins/read scope, each actual outcome and mutated bytes in immutable packets.

Publication remains local while the single hosted lane serves the critical
path. No SPEC-only artifact is runtime proof and no local proof authorizes live
hook installation, host cleanup or provider access.

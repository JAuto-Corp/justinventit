# Mailbox and hub client

`scripts/msg.sh` supplies a local mailbox, structured hub events and repairable
completion fan-out. It is inert until explicitly configured and invoked. It
does not start agents, install a daemon or connect the dev log automatically.

## Configure one project

Runtime dependencies: Linux, Bash 4.3+, jq, GNU coreutils/findutils, grep, sed,
awk and util-linux flock. Optional PostgREST reads also need curl. The acceptance
tests use Python 3.12 and Linux inotify; no product stack or database is needed.

Choose a stable, unique adoption ID. All worktrees for that project use the same
ID, canonical project root and state root. Changing the display name does not
change the ID. For example, from the project's adoption directory:

```bash
export JV_PROJECT_ID=example-project-7c3a
export JV_PROJECT_ROOT="$(pwd -P)"
export JV_STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/jv"
scripts/msg.sh send o a 'Smoke check' 'hello from this project'
scripts/msg.sh peek a
scripts/msg.sh read a
```

The CLI requires explicit values; it never infers identity from the current
directory, repository remote, display name or provider runtime. The ID accepts
lowercase letters, digits, underscores and hyphens (1–64 characters, starting
with a letter or digit). Both roots must be absolute; the project root must
exist. Keep state outside the product checkout.

State lives under `$JV_STATE_ROOT/$JV_PROJECT_ID/`: `project.json` binds the ID
to its canonical project root, and `mail/` holds authority, views, cursors,
archives, trigger and transport lock. An existing nonempty unmarked store or a
different project root using the same initialized ID is refused. There is no
automatic migration or re-binding. Back up state before a deliberate relocation.

Initialization first locks the existing project directory, so a failed bootstrap
lock creates no state. The store identity lock then serializes binding attempts
from different roots. Transport uses the project's own `mail/.hub-append.lock`.
Symlinks anywhere inside a selected store are refused before artifact access,
including dangling links. This deliberately conservative check protects against
accidental aliases between projects; it is not a hostile concurrent-swap defense.

Legacy independent `MSG_MAILROOT`, `HUB_EVENT_LOG`, `HUB_APPEND_LOCK` and
`HUB_DRAIN_TRIGGER` overrides are refused. Unset them and configure the three
project variables together. Ordinary role names start with a letter and contain
letters, digits or underscores. Hub actors and completion recipients are single
letters. `all` is broadcast; each reader has its own broadcast cursor. Read only
your own role. These are cooperating local agents, not authenticated tenants.

## Local operations

`send` accepts exactly `from to body` or `from to subject body`. There is no kind
argument: a leading `!` or `?` on the body selects alert/request. Optional work
correlation uses the attached form `--correlation-id=run-1` before positionals;
an omitted or space-separated value is refused to prevent shifted authorship.
The printed `hub_id` identifies the event; `correlation_id` identifies the work.

```bash
scripts/msg.sh send --correlation-id=run-1 o a 'Work' 'literal message'
scripts/msg.sh hub dispatch --from o --to a --title 'Check artifact' --body-file /absolute/path/to/body.txt
scripts/msg.sh hub complete --from a --producer reviewer --correlation-id run-1 \
  --outcome success --recipient o --recipient i --result-ref artifact.json
scripts/msg.sh read o
scripts/msg.sh search o --needle
scripts/msg.sh archive o task-1
```

Hub write verbs include dispatch, status, rule, thread, finding, attention answer
and complete. `--body -` reads literal stdin; `--body-file` reads a file. Both
avoid shell interpolation when the caller passes arguments correctly. See
`scripts/msg.sh hub --help` for their complete forms. Archive extracts sent and
directly addressed mail without deleting live bytes. Search checks live and
archived records, treats patterns literally and continues past ordinary misses.

Every event carries `project_id` and a ULID. Authority records are byte-length
framed; mailbox views remain JSONL. New append and replay use the same exclusive
transport lock and cross file/directory durability barriers before publishing
views. Archive extraction takes that lock in shared mode. Recovery handles a
torn final record; it does not validate or repair arbitrary interior corruption.

For retry, use the original ID with identical content:

```bash
MSG_HUB_ID=01KYZ000000000000000000001 scripts/msg.sh send o a 'same original body'
```

Use the ID actually returned by your operation, not the sample above. A retry
reuses the original timestamp and authority. Different content under that ID is
refused. Completion recipients are normalized, deduplicated and sorted; replay,
a fresh read/peek/tail, or the next append repairs missing completion views.
Repair only appends to mailbox views; it does not invalidate parked byte offsets.
Partial projection fragments can remain; readers must not treat them as valid JSON.

| Exit | Meaning |
| --- | --- |
| 0 | Requested operation completed |
| 1–2 | Usage, input, identity or configuration refusal |
| 3 | Append/read repair failed or could not be verified; do not assume the event is absent; inspect and retry its original ID |
| 4 | Structured append landed, but touching the external drain hint failed |
| 5 | Projection delivery is unknown; diagnostics distinguish an already recorded event from an unrelated current event refused before append |
| 6 | Same event ID already exists with different content |
| 7 | Archive shared-lock refusal |
| 8 | Durability barrier failed; no new view was published; retry after storage recovers |

Byte-offset reads advance their cursor when printing, not after a durable consumer
acknowledgment. Reading another role consumes its mail. There is no exactly-once
consumer contract, ordinary-view rebuild, folded completion queue or supervisor.

## Optional remote projection reads

Local mail and hub writes need no credentials. Remote `hub target`, `seats`,
`open`, `mine` and `blocked` use an externally supplied compatible PostgREST
projection. They never initialize local state, on success or failure. Set
`MSG_ENV_FILE` to an absolute dedicated file outside the repository, mode 0600:

```text
HUB_PROJECT_ID=example-project-7c3a
HUB_URL=https://hub.example.invalid
HUB_SERVICE_KEY=replace-with-dedicated-service-key
```

Use a separate database/projection store for every project. The env-file ID
check is a local assertion, not database tenancy enforcement. The baseline tables
lack multi-project keys and recipient authorization; an administrative service
key can read their whole project. Never point this client at a product database.

```bash
export MSG_ENV_FILE=/absolute/private/path/hub.env
scripts/msg.sh hub target
scripts/msg.sh hub mine --from a --json
```

The file is parsed as data, never sourced. Curl disables default configuration
with `-q` first and receives the key on stdin, not argv. Error responses and curl
diagnostics are suppressed because they can contain credentials. Target inspection
prints only the project ID, env-file path and URL. There is no home/product-env
fallback. The legacy snapshot/backup tools have their own configuration contract.

This slice supplies no projector, ingestion timer, raw-SQL client or cloud setup.
The trigger file is only an external-service hint. A remote query is not evidence
that a local event has reached the database. The broader normative hub contract,
backend conformance, acknowledged cursors and authorization remain future work.

Historical guard reasons: [provenance](CLUSTER_PROVENANCE.md). Generated runtime
tests are in `scripts/tests/test_msg.py`; the framework's Copier acceptance runner
exercises two consumers with isolated state and fake curl, never a live service.

## Seat launch and boot (W-C2)

The same project identity guard binds mailbox and session state. Launch additionally
requires Python 3.11+ (stdlib TOML), Node 22+ (the bundled JavaScript schema
validator), and operator-installed provider CLIs. No pnpm, tsx, application
packages or database are needed. This command runs a seat in the current terminal;
it does not install providers, profiles, a daemon, leases or a supervisor.

```bash
# Set the three JV project variables above first. Choose your own model.
scripts/role-launch.sh A --worktree /absolute/project/worktree \
  --runtime claude --model your-model --tier thinking --fresh
scripts/boot-role.sh A
# Later launches take their entire tuple from the persisted record:
scripts/role-launch.sh A --worktree /absolute/project/worktree
```

O and I default to `JV_PROJECT_ROOT`; every other uppercase ASCII letter requires
an existing `--worktree`. The workdir is canonicalized. Bootstrap requires an
explicit runtime (`claude` or `codex`) and nonempty model; thinking (the default)
means xhigh effort, doing means medium. Once a record exists, bootstrap flags are
refused. To change its tuple, stop the seat and deliberately edit and validate the
record; the launcher does not provide concurrent record administration.

Records live at `$JV_STATE_ROOT/$JV_PROJECT_ID/sessions/<lower-letter>.json`,
with an adjacent `.json.lock` held through runtime exit. The full schema and
project/letter/workdir binding are checked from one opened byte image. Bootstrap
validates a private candidate before atomic publication and rereads the persisted
record. Empty capabilities mean unprobed; `booted` and neutral lease/watcher
shapes do not establish liveness or implement the broader seat protocol.

Claude uses exactly the requested record model/effort, qualified names such as
`example-project-7c3a-a`, and no implicit permission bypass. Its uppercase-letter
`A.id` contains a validated UUID. Resume requires the history file under
`$HOME/.claude/projects/<workdir-with-slashes-replaced-by-hyphens>/<uuid>.jsonl`;
missing history or `--fresh` selects a fresh UUID. This inherited history layout
is a compatibility boundary, not a claim about every CLI version. Prelaunch
refusals fail nonzero; once interactive Claude returns, inherited pane lifecycle
ends at status 0 (unexpected exits hold for Enter). That status is not a supervisor
health verdict or proof of the resolved Claude model.

For Codex, set `JV_CODEX_BIN` to an absolute executable path. The launcher prepends
its directory to PATH and proves `--version` invocation. Configure exact workdir
trust and matching profiles in `${CODEX_HOME:-$HOME/.codex}/config.toml`:

```toml
[projects."/absolute/project/worktree"]
trust_level = "trusted"
[profiles.example-project-7c3a-thinking]
model = "your-model"
model_reasoning_effort = "xhigh"
[profiles.example-project-7c3a-doing]
model = "your-model"
model_reasoning_effort = "medium"
```

Run the same bootstrap with `--runtime codex`. Each launch requires parsed exact
workdir trust, then a bounded 240-second read-only probe. A real probe costs one
provider turn. Only its own `thread.started` rollout and exact recorded tuple can
pass; another thread's evidence cannot substitute. The checked provider-home
`.jv-tier-probe.lock` intentionally serializes probes across projects sharing that
home. Profiles and trust remain operator-managed; W-D3 owns adapter packaging.

A fresh Codex launch prints `/rename <project-id>-<letter>` for the human/agent
inside the TUI. `A.codex-thread` stores that INTENDED, unverified name. Resume
accepts only this seat's qualified name and requires tmux or explicit
`--at-machine` because the resume modal otherwise parks unattended work. A
provider refusal for an ambiguous duplicate name stays nonzero, without automatic
fresh/newest-thread fallback. Dated lesson (2026-09-30): repeated fresh launches
can share a name even after project qualification. Operational UUID recovery
required stopping the seat first; writing the UUID earlier was overwritten by
the launcher's name write on exit. Deterministic UUID recovery/manual migration
is deferred here; this launcher does not accept UUIDs as saved Codex names.

Post-exit Codex workdir/time evidence is advisory: even one matching rollout
cannot prove ownership. Mismatch exits 4, a clean runtime exit with missing or
ambiguous evidence exits 5, abnormal runtime exits propagate (including 137),
and planned 130/143 teardown may end at 0 without evidence. Matching evidence is
reported as consistent, never as verified interactive-thread identity.

Runtime limitation observed with Codex CLI 0.159.2 on 2026-09-30:
the exact resolved gitdir must be an operator-supplied writable root. Resolve it from the seat cwd
with `git -C /absolute/worktree rev-parse --absolute-git-dir`; a parent `.git` or
`.git/worktrees` entry was insufficient. W-D3 owns packaging those writable roots.
The read-only tier preflight cannot verify gitdir writability.

`boot-role.sh` only prints a neutral O/I/implementer prompt pointing to AGENTS.md,
canonical guidance and that seat's mailbox. Project instructions and explicit
dispatch supply authority. Offline acceptance renders cluster and solo consumers,
uses allowlisted utilities and fake providers under scratch homes, and runs
`scripts/tests/test_launch.py`; it is not live-provider compatibility evidence.

## Shared host capacity (W-C4)

After binding the project above, configure one explicit `JV_HOST_ROOT` shared
by all cooperating projects and invoke `scripts/build-guarded.sh <command>`.
[Host capacity](HOST_CAPACITY.md) describes admission outcomes, read-only status,
inherited ownership, manual adoption and the supported child-lifetime limits.

## Optional shared host observations

[Host observability](HOST_OBSERVABILITY.md) documents the explicit usage inputs,
shared history and selected-filesystem alerts. `pace.sh`, `usage-hook.sh` and
`disk-watch.sh` require existing project binding plus an explicit host root.
They install no hooks, query no providers and perform no cleanup.

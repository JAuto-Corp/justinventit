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

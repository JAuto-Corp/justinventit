# Hub Data Model

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §7. The hub is the coordination
> state-of-record for an L2 fleet: one verb append = durable record + transport.

## 1. Event-log core

The hub is an **append-only event log with folded state**. Every write verb appends an event;
current state (dispatch status, thread state, role liveness) is a fold over events —
recomputable, never authoritative on its own.

Semantic contract (every backend MUST pass the shared conformance suite on all of these):

- **Identity**: every event carries a client-minted ULID `hub_id` — the idempotency key.
  Replaying an append with the same `hub_id` is a no-op (dedup at write).
- **Ordering**: total order per stream; a stream is `(project_id, stream_kind, stream_key)`
  (e.g. one dispatch's status events; one thread's updates). No cross-stream ordering promise.
- **Delivery**: at-least-once. Consumers (seats) read via **cursors** — durable per-consumer
  offsets advanced only after processing. Crash recovery = resume from cursor; dedup by
  `hub_id` makes redelivery safe.
- **Atomicity**: one verb = one atomic append (single event or single transaction of events).
  The mailbox side-effect (transport) derives from the same append — record-as-byproduct —
  and MUST NOT be a second, separately-failable write from the client's perspective.
  Concretely: **a mailbox is a recipient-filtered view/stream over hub events.** Where a
  materialized per-recipient file exists (single-host backends), it is a rebuildable
  projection emitted by the append path (outbox pattern) — senders never write mailbox files
  directly, and a lost projection is rebuilt from the log, never the reverse.
- **Recovery**: a backend restarted mid-append leaves either no event or the whole event;
  never a partial.

## 2. Entities

All keys are compound with `project_id` (immutable, issued at adoption; never inferred).

| Entity | Purpose | Notes |
|-|-|-|
| `projects` | consumer registry | id, name, created; issued by adopt tooling |
| `roles` | seat registry + liveness — **authority defined by the seat-control contract** (`SEAT_PROTOCOL.md` §1): authoritative on multi-host (postgrest) fleets; a derived mirror of the file-backed registry on single-host fleets | letter, runtime, model, effort, capabilities |
| `dispatches` | units of assigned work | status ladder; prereq ids; scope class; refs (issue/PR) |
| `status_events` | dispatch transitions | the event stream dispatch state folds from |
| `threads` | long-running workstreams | state: live/parked/dead/shipped; checklist; depends_on |
| `findings` | discoveries awaiting routing | route → thread; resolve |
| `attention` | user-facing questions/blocks | severity; one-tap metadata; answer verb |
| `journal` | rules/decisions/milestones | supersedes chain by hub_id |
| `docs` | doc registry (spec/scope/plan/memory pointers) | **gets a verb** — no verb-gap tables |
| `completions` | durable terminal outcomes of actionable async work (§3a) | run/correlation id; outcome incl. failure/cancellation; deduplicated recipients; atomic multi-recipient projection |

Every entity the protocol needs is reachable through a verb (write) or view (read); raw
backend access is repair-only and logged as such.

## 3. Verb interface

Writes: `dispatch`, `status`, `rule`, `thread --open/--update`, `finding` (+ `--route`,
`--resolve`), `attention` (+ `--answer`), `journal`, `role`, `doc`, `complete` (§3a), and `capture` — the
loop-stage-8 verb: a routing alias that records a `finding` by default, `journal` with
`--kind decision`, or a `doc` pointer with `--doc`, and carries external-tracker refs
(`--issue N`) so "captured" always means "in the hub, linked to wherever else it lives".
Reads: `seats`, `open`, `mine`, `blocked`, `history <stream>`, `--json` everywhere.

CLI-side validation fails loudly (enum checks, letter checks) — malformed input never reaches
a backend as a silent reject. Verbs are runtime-agnostic shell (`hub.sh` successor of
`msg.sh hub`), callable identically from Claude and Codex seats.

### 3a. Completion events (2026-07-28, doorbell ratification — this spec is the normative owner)

A tool completion that others must act on is recorded as a hub event, never only a
session-local notification (which dies with the session). The `complete` verb appends ONE
event carrying: `hub_id`; a run/correlation id; terminal `outcome: success | failure |
cancelled | timeout`; OPTIONAL result reference or digest (cancelled/timed-out work may have
neither); OPTIONAL verdict + schema-validity (review tools); OPTIONAL originating dispatch
`hub_id` (undispatched work has none); OPTIONAL diagnostic/error reference; producer;
recipients, DEDUPLICATED (the invoker-as-recipient case yields one delivery). The single
append projects to all recipient mailbox views atomically per §1 — never N
separately-failable sends. Completion events are doorbell sources under `SEAT_PROTOCOL.md`
§4 and classify as ACTIONABLE for its message-class filter; consumers deduplicate against
runtime task-exit notifications by run id. Origin: 4+ review one-shots in one night whose
finished verdicts reached nobody (detached launches; session-mortal notifications) — a
completed gate result that reaches nobody is not a gate.

## 4. Tenancy and authorization

- `project_id` in every key; verbs are project-scoped by the seat's own config — there is no
  cross-project read or write path through the verb surface.
- **postgrest backend**: authorization enforced AT THE BACKEND — per-project credentials
  (scoped tokens or RLS on `project_id`), so a misconfigured client cannot read another
  project's rows. Mailbox reads are recipient-scoped the same way.
- **sqlite backend**: one DB file per project (isolation by file boundary + fs permissions).
- **jsonl backend**: one directory per project; explicitly the degraded mode (see §5).
- **Recipient-level isolation is enforced only on postgrest.** On sqlite/jsonl the stated
  trust model is: *seats within one project are mutually trusted* — fs permissions are
  optional hardening, and own-letter-only is protocol, not security. Projects needing
  enforced intra-project isolation must run the postgrest backend. (This is a deliberate,
  documented downgrade — not an accidental gap.)
- Adversarial isolation tests are part of the conformance suite (attempt cross-project reads
  with a wrong-project client; must fail).

## 5. Backends

| | postgrest | sqlite (portable default) | jsonl (degraded) |
|-|-|-|-|
| Concurrency | full (DB) | full single-host (WAL) | flock append; single-writer-at-a-time |
| Reads | SQL views | SQL views | full scan folds |
| Cursors | table | table | **hub_id-valued** files (byte offsets would be invalidated by repair-by-rewrite) |
| Multi-host | yes | no | no |
| Guarantees | full contract | full contract | **stated weaker**: no fold caching, O(n) full-scan folds, repair-by-rewrite; crash atomicity is length-prefixed-record + truncate-to-last-valid on open (flock serializes writers but does NOT make appends crash-atomic; >PIPE_BUF appends can tear — the recovery scan is the mechanism, and its fixture corrupts a tail record and asserts truncation) |

Backend choice is a questionnaire dial; the verb surface is identical. The conformance suite
runs against all three in framework CI (idempotent replay, interleaved writers, cursor crash
recovery, tenancy isolation, partial-write recovery).

## 6. Versioning and migration

- `schema_version` per project, written at adopt/upgrade; framework ships ordered
  migrations per backend; verbs refuse to run against a newer schema than they know
  (fail loudly, upgrade instruction in the error).
- **JAuto migration path — corrected by audit (in-place compound-keying is NOT additive)**:
  `orchestration_roles.letter` is a `char(1)` PK with 4 inbound FKs, `threads.id` a slug PK
  with 4 more, plus views and RLS — re-keying in place would drop and recreate all of them
  on the live hub. The actual path: (1) **additive phase**: add `project_id` as a NULLABLE
  column backfilled to the JAuto id, with partial unique INDEXES only — PKs, FKs, views
  untouched; the staging instance remains effectively single-tenant and fully functional.
  `hub_id` dedup tightens via a new-rows-only NOT NULL enforcement (trigger/app-level);
  legacy NULL rows are grandfathered outside the dedup contract. (2) **cutover phase
  (Phase-5 go/no-go, a declared NON-additive exception to law 7, executed as a cutover not
  as surgery)**: stand up a fresh multi-project-schema deployment, export/import with a
  dual-write window and read-compatibility views on the old side, then retire the old
  tables. Verb clients are version-negotiated: refuse-newer applies to WRITES only — reads
  degrade gracefully during the window, so un-upgraded seats are never bricked mid-migration.

## 7. Routed review findings dispositioned here

- Hub delivery semantics (blocker, arch-level): §1 — full semantic contract + conformance suite.
- Tenancy beyond a namespace column (major): §4 — backend-enforced authz, compound keys, adversarial tests.
- Mailbox authorization (major): §4 — recipient-scoped reads at backend where possible; file-boundary isolation otherwise; etiquette is the last resort, not the mechanism.
- Verb gaps (finding from source-system audit): §2/§3 — journal/roles/docs are verbs.
- Framework evolution/versioning (major, partial): §6 — schema_version + refuse-newer + ordered migrations. (Copier/template versioning: `SEAT_PROTOCOL.md` is not the owner either — dispositioned in `ARCHITECTURE.md` §9 note and the template's release discipline, M3 scope.)

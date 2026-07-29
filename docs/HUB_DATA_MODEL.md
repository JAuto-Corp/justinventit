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
  offsets advanced only after processing. Crash recovery = resume from cursor; `hub_id`
  dedup makes replayed APPENDS safe — consumer-EFFECT redelivery safety is §1a's action
  contract (ingest-dedup is not effect-dedup).
- **Atomicity**: one verb = one atomic append (single event or single transaction of events).
  The mailbox side-effect (transport) derives from the same append — record-as-byproduct —
  and MUST NOT be a second, separately-failable write from the client's perspective.
  Concretely: **a mailbox is a recipient-filtered view/stream over hub events.** Where a
  materialized per-recipient file exists (single-host backends), it is a rebuildable
  projection emitted by the append path (outbox pattern) — senders never write mailbox files
  directly, and a lost projection is rebuilt from the log, never the reverse.
- **Recovery**: a backend restarted mid-append leaves either no event or the whole event;
  never a partial.

### 1a. Cursors, acknowledgement, and effect idempotency (canonical; `SEAT_PROTOCOL.md` §4/§5 defer here)

Records (versioned with the schema; one row per key):

- Cursor records are a **DISCRIMINATED PER-KIND schema**. Common fields:
  `{project_id, consumer, stream: (stream_kind, stream_key), kind, position: {seq, hub_id},
  updated_at}` — `seq` is the backend-assigned per-stream sequence (total order per §1),
  `hub_id` cross-checks it. Kind-specific durable fencing fields:
  - `processed` + `{incarnation}` — the seat's fencing term.
  - `notification` + `{incarnation, watcher_generation, watcher_session_handle}` — a
    superseded watcher's identity is representable, so its commit is mechanically
    refusable.
  - `delivered` + `{projection_id}` — backend/projection identity; `incarnation` is
    ABSENT by schema (not nullable-and-ignored): delivered is never seat-written.
  Update authorization is PER CURSOR KIND (the seat predicate table is
  `SEAT_PROTOCOL.md` §2a's; this section applies it, never restates a weaker form):
  - `processed` — complete CAS tuple: `membership == live AND proposed_incarnation ==
    null AND active_incarnation == record.incarnation == writer` + three-way position (an
    incumbent frozen by an installed proposal cannot commit `processed`; a consumer
    following this file literally gets the same freeze §2a defines).
  - `notification` — complete CAS tuple: `active_incarnation == record.incarnation ==
    writer AND watcher.generation == record.watcher_generation == current AND
    watcher.session_handle == record.watcher_session_handle == writer's` + three-way
    position — a superseded watcher generation cannot advance observation state.
  - `delivered` — complete CAS tuple: `writer == the append/projection path AND
    projection_id == record.projection_id` + three-way position; never seat-written;
    recipient tombstone HALTS further projection (stream preserved, nothing deleted).
  Within each writer class, position updates use **three-way commit semantics**: an
  IDENTICAL `{seq, hub_id}` is a successful NO-OP (a lost-response retry must not fail
  loudly — commits are idempotent); a greater contiguous position advances; a lower
  position, a same-seq/different-`hub_id` value, or a failed authorization term is
  refused loudly. Fixture: lost-response retry on every backend, per cursor kind.

  **Creation and takeover (position-preserving rebinds; stored-row vs candidate-row
  terms are explicit).** A cursor's identity fields bind its CURRENT authorized writer;
  succession REBINDS identity without losing position. Every predicate below tests the
  STORED row's identity plus the writer's live authority; the CANDIDATE row carries the
  writer's identity and the new (or preserved) position:
  - `processed` — active-incarnation ADOPTION: a writer holding the complete
    steady-state seat predicate whose incarnation differs from `stored.incarnation`
    performs one atomic rebind `{position preserved, incarnation := writer}`. A stale
    incarnation cannot adopt — it fails the seat predicate, not a cursor-local check.
  - `notification` — current-generation adoption: the watcher matching the seat
    record's CURRENT `watcher.generation`/`watcher.session_handle` rebinds the same
    way; a superseded generation fails the stored-vs-current comparison.
  - `delivered` — backend-authenticated projection takeover: `projection_id` is MINTED
    AND STORED by the backend's projection maintainer (the append path) in the
    projection's own metadata at creation and rotation — it is reachable through NO
    consumer verb, which is what makes "never seat-written" mechanically checkable.
    Rotation mints a fresh `projection_id` and preserves position by rebuild-from-log.
  Fixtures per backend, per kind, both directions: stale-writer rebind refused AND
  successor-takeover succeeds with position intact.
- `ack {project_id, consumer, stream, seq, hub_id, action_kind, target, incarnation, at}`
  — per-event acknowledgement, for acts completed out of order.
- **Contiguous-prefix rule (per stream)**: `processed.position` is the highest seq S such
  that every event ≤ S is acked; acks beyond a gap stay as `ack` rows until the prefix
  closes. A recipient VIEW spanning multiple streams computes per stream — nothing is
  skippable by construction, because `processed` never jumps a gap. Cross-stream ordering
  is still never promised (§1); consumers needing it sequence via explicit dependencies.
- **Backlog age** (the stall-detection input): max over the view's streams of
  (now − ts of the first event past that stream's `processed`). Read PROCESSED — reading
  `delivered` shows a seat as caught-up while its work is pending, a stall the watchdog
  structurally cannot see. `delivered` is transport bookkeeping advanced by the
  append/projection path; `notification` (`SEAT_PROTOCOL.md` §4) acknowledges nothing.

**Effect idempotency — ingest-dedup is not effect-dedup.** `hub_id` dedup (§1) makes
replayed APPENDS no-ops; it does nothing for a consumer's ACTIONS on delivered events.
At-least-once delivery therefore requires per-action idempotency:

- Action key: `{consumer, hub_id, action_kind, target}`.
- **The action record is a versioned outbox** — `action {key, state: prepared |
  effect_pending | complete, child_hub_ids[], incarnation, updated_at}` — and EVERY
  backend provides the atomic envelope for its transitions (postgrest/sqlite:
  transaction; jsonl: the same length-prefixed-record + truncate-to-last-valid recovery
  as §5 — "where supported" is not a conformance level). Lifecycle: `prepared` (child
  `hub_id`s pre-minted into the record) → `effect_pending` (effect issued) → `complete`
  (effect verified) — and the EVENT-LEVEL ack closes only from `complete`, so `processed`
  can never advance past an action whose child append does not yet exist.
- **The recovery actor is the consumer itself, at drain**: before processing any new
  event, a seat scans its own incomplete action records (`prepared`/`effect_pending`) and
  finishes them — retrying pre-minted child appends (deduped at write by the pre-minted
  id) and re-verifying effects — so crash recovery is a normal drain, not a special mode.
- External effects (API calls, file mutations, notifications): sink-enforced idempotency
  via the action key where the sink supports one; otherwise the effect is classified
  **`at_least_once_visible`** — duplicates are possible and the action must be designed
  tolerable. **An action lease (`SEAT_PROTOCOL.md` §2a) is a CONCURRENCY fence only — it
  cannot prevent sequential duplication (crash-after-effect, lease expiry, retry) and is
  never an idempotency substitute.** The classification is explicit at the call site; an
  unclassified external effect is non-conforming.
- Conformance: crash-injection before effect, after effect, and during commit, for every
  action class, on every backend.

**Origin integrity (2026-07-29; from a live false-authorship incident — hub finding
01KYN928QZ). Status: OPEN — schema + verb land with the §1a implementation wave.**
- `origin_claimed` is writer-asserted, always present. `origin_attestation` is a
  **backend-authored** tuple `{project, seat, incarnation, session_handle, transport}`
  written by the append path from its authenticated session context — a client cannot
  self-assert it (a client-supplied attestation field is REFUSED at append); absent means
  unattested, never "attested: false" by assertion.
- Append-only means a misattributed event is never edited or deleted: the correction is a
  **`dispute-origin` VERB** (no verb-gap rule, §2) appending an event
  `{disputes: <hub_id>, claimed_by, evidence}`; folds and views MUST surface disputed
  events AS DISPUTED — both parties visible — rather than silently preferring either.
- Fixtures, per backend, both directions: forged client attestation refused; valid
  backend attestation recorded; dispute surfaces in the fold; undisputed control stays
  clean. The schema anticipates disputes from day one — retrofitting origin disputes onto
  an append-only log is what makes misattribution permanent.

## 2. Entities

All keys are compound with `project_id` (immutable, issued at adoption; never inferred).

| Entity | Purpose | Notes |
|-|-|-|
| `projects` | consumer registry | id, name, created; issued by adopt tooling |
| `roles` | seat registry + liveness — **authority defined by the seat-control contract** (`SEAT_PROTOCOL.md` §1): authoritative on multi-host (postgrest) fleets; a derived mirror of the file-backed registry on single-host fleets | letter, runtime, model, effort, capabilities, active/proposed incarnation, ack, membership (tombstone) — mirrors seat-record schema v2 (§2a) |
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
`--resolve`), `attention` (+ `--answer`), `journal`, `role`, `doc`, `complete` (§3a),
`dispute-origin` (§1a origin integrity), and `capture` — the
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
append MUST project to all recipient mailbox views atomically per §1 — never N
separately-failable sends. Completion events are doorbell sources under `SEAT_PROTOCOL.md`
§4; consumers MUST deduplicate against runtime task-exit notifications by run id.
Implementation status: the `complete` verb and its projections land with the
authoritative-transport conformance wave (the archived doorbell r4 record's B0/B6); this
contract is normative now, its tooling is not yet built. Origin: 4+ review one-shots in one
night whose finished verdicts reached nobody (detached launches; session-mortal
notifications) — a completed gate result that reaches nobody is not a gate.

**Message/event class taxonomy (owned HERE; `SEAT_PROTOCOL.md` §4 owns immediate/defer
behavior; `MODEL_MATRIX.md` owns per-seat-class selections):**

| Class id | Source events | Default interrupt class |
|-|-|-|
| `dispatch` | dispatch appends | actionable |
| `attention` | attention appends, alert-kind mail | actionable |
| `request` | direct request mail addressed to the seat | actionable |
| `completion` | completion events (§3a) | actionable |
| `info` | informational mail, findings routed FYI | deferrable |
| `status` | status events, heartbeat-adjacent traffic | deferrable |
| (unknown/malformed) | anything that resolves to no class id | treated as actionable — fail-toward-ringing |

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
| Cursors | table | table | **{seq, hub_id}-valued** files — both persisted, per the §1a record (byte offsets would be invalidated by repair-by-rewrite) |
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

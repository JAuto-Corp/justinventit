# Seat Protocol

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §6. Seats are the unit of
> cross-session work: persistent, addressable, revivable terminal sessions on any supported
> runtime.

## 1. Seat record

**Seat-control contract — one owner.** Identity, registry, heartbeat, lease, and watcher
state form a single project-namespaced contract with exactly one authoritative backend per
project, named in the project's hub config: single-host fleets (sqlite/jsonl hub, the
default) use the **file-backed registry** below as authoritative, and hub `roles` rows are
derived mirrors written by the ingest path; multi-host fleets (postgrest hub) use **hub
`roles` as authoritative**, and local files are non-authoritative caches. Precedence is
never mixed per-field; the hub spec's `roles` entity defers to this contract.

Registry: one JSON file per seat at `<coordination-root>/<project_id>/sessions/<letter>.json`
(supersedes the bare `<letter>.id` files):

```json
{
  "project_id": "immutable, from adoption",
  "letter": "a",
  "runtime": "claude | codex",
  "model": "from matrix",
  "effort": "from matrix",
  "workdir": "/abs/path",
  "session_handle": "claude conversation UUID | codex thread name/uuid",
  "capabilities": { "resumable": true, "external_invoke": "remote-control | exec-resume | tmux-keys | none", "watcher_locations": ["host", "in-session"], "hooks": true, "memory": false },
  "lease": { "holder": null, "epoch": 0, "expires_at": null },
  "watcher": { "location": null, "generation": 0, "session_handle": null, "status": null, "last_poll_at": null, "expires_at": null }
}
```

**Watcher capability vs live watcher state (2026-07-28, doorbell ratification).**
`capabilities.watcher_locations` names the locations this runtime SUPPORTS; the `watcher`
record is LIVE state for the armed one. The watcher itself renews `last_poll_at`/`expires_at`
on every poll via a channel OUTSIDE the seat's turn-end heartbeat (its own liveness field the
pacemaker reads) — an in-session watcher is conforming ONLY while that externally-readable
renewal is current, because it shares the session's failure domain and its death must be
observable from a different one. Record-of-existence alone proves nothing: a dead watcher
leaves the same record. An EMPTY `watcher_locations` forbids standby/doorbell mode — the seat
degrades to active cadence or human wake under this section's capability rules.

Capabilities are **negotiated at boot** (probed, not assumed) and re-probed on runtime
upgrade. A runtime with `external_invoke: none` is a supported capability level: it is woken
only by its own cadence loop or a human, and the watchdog reports rather than revives.

## 2. Lifecycle state machine

**Canonical states** (the only ones any file may carry): `booted` (pre-first-turn) ·
`active` (cadenced wake loop) · `standby` (event-driven, no scheduled wake) · `dormant`
(deliberate sleep / concluded) · `parked` (booted-not-live: unanswered modal or equivalent;
launcher-diagnosed, §3) · `stalled` / `dead` (derived verdicts, never self-written).

```
booted → active ⇄ standby → dormant        booted → parked (probe unanswered, §3)
active/standby → stalled (per predicate table) → revived → active
any → dead (stalled + revival budget exhausted, or operator-declared) ↘ report-only if not revivable
```

**THE normative stall-predicate table** (single source; §4's prose defers here):

| State | Predicate (STALLED when…) | Terms |
|-|-|-|
| `active` | `now − max(heartbeat_at, next_wake_at) > grace` | `grace = max(grace_floor, 2 × cadence_seconds)` |
| `standby` | `first_undrained_age > mail_grace` **OR** `now − heartbeat_at > 2 × floor_seconds` (the pair is OR — two independent detectors) | `first_undrained_age` = now − ts of the OLDEST event strictly after the processing cursor; **new arrivals never reset it**. `floor_seconds` = the mandatory slow-heartbeat interval (§4) |
| `booted` | probe unanswered past `probe_timeout` → classify per §3 (parked vs unknown) | launcher-owned |
| `dormant` | never | — |
| (no match) | a seat whose state matches no row is itself a LOUD finding | — |

- **Heartbeat**: written ONLY by the seat's own turn-end hook, on both runtimes (Codex Stop
  hook; same portable script). Fields: state, role, heartbeat_at, wake_count,
  cadence_seconds, next_wake_at, context. Schema-validated on write AND read — prose in a
  numeric field is a loud error, not a watchdog crash. **No external process ever writes
  heartbeat fields** — a watchdog-authored heartbeat certifies false liveness (§4 canary).
- `dormant` + a conclusion reason (§4a ceremony) is deliberate sleep, never a stall.
- **Leases exist only for revival windows — liveness is heartbeats.** A healthy seat runs
  **unleased** (`holder: null` is the normal state); staleness is judged by heartbeat age,
  never by lease state. Every revival path (pacemaker, doorbell, human script) must acquire
  the seat's revival lease via **compare-and-swap**: read `{holder, expires_at}`;
  acquisition succeeds only if the CAS primitive atomically verifies
  `holder is null OR expires_at < now` while writing `{holder: <fencing token = fresh ULID>,
  expires_at}`. Fencing is by **token equality, not epoch arithmetic** — ULIDs are unique
  across registry recreation and re-adoption, so there is no counter to reset (the epoch
  field survives only as a human-readable revival counter with no fencing role). Two racers
  cannot both win — exactly one CAS succeeds; the loser observes a foreign token and stands
  down.
  CAS implementation per registry backend: hub-backed registry = transactional
  conditional update; file-backed registry = a **per-seat mutex** (`flock` on
  `<letter>.lock`, held for the whole operation) inside which the acquirer re-reads the
  lease record, re-verifies the full predicate (epoch AND holder AND expiry), and commits
  the new record via temp+rename — versioned claim-file tricks are explicitly rejected
  (a freed pathname readmits delayed racers). Renewal and acquisition run under the SAME
  mutex with the same full-predicate re-read; they differ only in the predicate
  (renewal: holder == self).
  The revived seat **validates its fencing token (holder + epoch) before its first
  side-effect** and re-validates before irreversible actions; a stale token = stop
  immediately. **Handoff**: the reviver passes its fencing token in the revival payload; the
  revived seat validates token-equality against the CURRENT lease record before its first
  side-effect and re-validates before irreversible actions; the reviver releases (nulls
  holder) only AFTER observing the revived seat's first heartbeat — never mid-turn — after
  which the seat runs unleased again. STALLED is defined solely by the predicate table
  above; DEAD = stalled AND the configured revival budget is exhausted (N failed/unclaimed
  revival windows) or an operator declares it. Lease state never defines liveness; process
  checks are diagnostics for reports, never triggers.
  **Parked-revival outcome** (closes the lease/heartbeat deadlock): a revival that lands on
  a PARKED session produces no first heartbeat, so the reviver cannot complete the normal
  handoff. Rule: the reviver renews its lease up to `park_ttl`; at TTL it runs the
  conclusion ceremony (§4a) ON BEHALF of the parked seat — marks the lease record
  `superseded_by: <new token>`, boots a FRESH successor off the durable brief, and notifies
  with attention class "physical (modal)". The old handle is QUARANTINED, not trusted-dead:
  if it ever un-parks, its first mandatory act is token validation — it observes
  `superseded_by`, performs NO side effects, and self-concludes. Human-unpark of a
  not-yet-superseded seat re-acquires the lease and injects a fresh validated token before
  any turn.
  Conformance: adversarial concurrent-acquisition fixtures (two racers, N racers,
  crash-mid-acquire, **delayed-racer-after-commit, renewal-vs-acquisition race, registry
  recreation mid-lease** — token fencing must hold across a recreated registry) run
  against every registry backend.

## 3. Launch and resume

| | Claude seat | Codex seat |
|-|-|-|
| Boot | `role-launch` semantics: `claude -n <L> --remote-control <L> --model <m> --effort <e>` in a pane | `codex --profile <project_id>-<tier>` in a pane; first action `/rename <letter>`; registry stores thread name |
| **Tier verification (both runtimes, mandatory)** | launcher confirms the booted session reports the intended model+effort | **empirically required**: a nonexistent Codex profile boots the DEFAULT tier with exit 0, and config errors are non-fatal — the launcher runs a post-boot probe asserting the RESOLVED model/effort and fails loudly on mismatch; tier selection is never trusted |
| **Modal-parking detection (mandatory on resume)** | the post-boot probe doubles as liveness proof — but an unanswered probe alone classifies as `unresponsive_unknown`; it upgrades to PARKED only on a modal signature (capability `modal_detectable`) or human confirmation | **booted ≠ live**: a resumed session can sit on an interactive resume-mode modal (summary-vs-verbatim); while parked, its main loop takes no turns and in-session subagent deliveries BLOCK (complete but cannot land — the empty-report signature) |
| Resume | `--resume <uuid>` / remote-control push | interactive `codex resume <name>`; headless poke: `codex exec resume <letter> "<drain prompt>" < /dev/null` |
| Tier | model+effort args from matrix | **project-qualified** profile (`~/.codex/<project_id>-<tier>.config.toml`), selected by the launcher from the seat record's `project_id` — two consuming projects never collide; per-poke override `-c model_reasoning_effort=...` |
| Effort constancy | hold constant per session (prompt-cache) | same rule |

**Modal policy is capability-branched** — seat capabilities gain `resume_modal` (does this
runtime's resume present one?), `modal_detectable` (can the launcher recognize its
signature?), `remote_answerable` (can the pane host answer it remotely, tmux-send-keys
class?). Unattended resume is permitted only when `!resume_modal OR remote_answerable`;
otherwise resume is scheduled-with-human or replaced by fresh-boot.

**Modal economics (origin: a fleet held hostage to a human's physical presence — modals were
answerable only at the machine, invisible to remote taps):**
- **Fresh-boot-with-durable-brief is the default revival path** wherever seat context is
  recoverable from briefs/hub/memory — fresh boots hit no modal. Resume is reserved for
  genuinely irreplaceable in-context state, scheduled for when a human is AT the machine.
  (Durable state exists precisely so resume-context is optional; a fleet that must resume
  has under-invested in briefs.)
- **Notify adapters distinguish attention classes**: "remote tap sufficient" vs "physical
  interaction required (modal)" — an alert that can't say which sends the human to the
  wrong device.
- **Remote-answerability is a launcher selection criterion**: pane hosts whose interactive
  surface can be driven remotely (tmux send-keys class) strictly dominate ones that cannot,
  for any seat that may ever be resumed unattended.

Launcher is one script, runtime-dispatched by the seat record. Boot prompts come from
role templates; the launcher never injects them as positional args (silent no-op trap on
Claude interactive; unverified on Codex — templates are pasted/poked, not arg-passed).

## 4. Wake model

- **Doorbell (preferred; cross-seat events + durable actionable completions — the
  completion event is the one non-cross-seat doorbell source, since it may address its own
  invoker; in-session subagents remain native-delivery, never doorbells)**: a bounded watcher re-invokes the seat ON an
  event (mailbox append, artifact landing). **Two cursors, never conflated**: the watcher
  reads from its own *notification cursor* (observation only — advancing it acknowledges
  nothing); the seat's *processing cursor* advances only after the message's side effect is
  recorded. Missed-event-safe: the watcher compares the stream head to the processing
  cursor, so an event landing before the watcher armed still triggers a wake. Redelivery
  after a crash (side effect done, processing cursor not advanced) is safe because consumer
  side effects are idempotent by `hub_id` (the hub contract); crash before the side effect
  simply reprocesses. Bursts coalesce (one wake per quiet-window); watcher expiry = seat's
  grace window; every wake goes through the lease (§2). Conformance fixtures crash the
  consumer both before and after side-effect/cursor-advance. In-session subagents NEVER use
  doorbells — the harness re-invokes the parent natively.
  **Doorbell conformance additions (2026-07-28; these fixtures SHIP WITH the conformance
  wave — the archived doorbell r4 record's B-list — and are normative requirements on it,
  not yet built)**: the watcher-ALIVE check MUST have its own BOTH-DIRECTIONS fixture —
  fire on a killed watcher AND stay quiet on a live one (the armed-once-assumed-alive guard
  class); dual-signal fixtures MUST cover both orderings of task-exit vs completion event;
  a filter-false-stall fixture MUST prove the deferred ring's bound holds against the §2
  standby predicate; watcher restart MUST produce a fixture-verified generation
  supersession; dynamic sender-stream discovery and to-all delivery MUST be covered
  explicitly.
  **Two doorbell shapes, chosen deliberately per seat class**: *own-mailbox* (doing seats —
  waking on another seat's conversation mid-build is pure interruption) vs *total-inbound*
  (coordination seats: baseline = total bytes of inbound fleet mail across all streams,
  **excluding the seat's own outbound** — the naive total self-triggers on every send,
  degrading the doorbell into noise nobody reads). Total-inbound buys two properties: an
  unexpected message cannot hide behind an expected one (the wake you predicted otherwise
  consumes the look), and it yields a per-seat undrained-backlog table on every wake —
  live "receiving-but-not-draining" detection without polling, distinguishing "not drained
  in 9h" from "arrived 2 min ago". Both shapes stay BOUNDED (dead watcher degrades to slow
  polling, never silence).
  **Message-class interrupt filter (2026-07-28)**: the own-mailbox shape gains a
  matrix-owned filter — doing seats ring immediately on actionable classes (dispatch,
  attention/alert, direct request, and actionable COMPLETION events) and DEFER info/status
  behind a **bounded deferred ring**: `max_deferral` is GENERATED under validated
  compositional constraints — `max_deferral + poll_budget + commit_budget < mail_grace`
  (the §2 stall clock is never beaten) and `max_deferral + poll_budget ≤ fallback_interval`
  — never hand-set. The OLDEST deferred event's ring deadline is fixed at its arrival; new
  arrivals never reset it. Unknown or malformed classes ring immediately
  (fail-toward-ringing). The total-inbound shape stays unfiltered. Class taxonomy is owned
  by `HUB_DATA_MODEL.md`; per-seat-class mappings and thresholds by `MODEL_MATRIX.md`.
- **Own tracked background work (2026-07-28)**: actionable asynchronous work — any side
  process whose result someone must act on (review one-shots, CI watches, builds) — is
  SUPERVISED (a component outside the work observes its termination) and produces a
  **durable terminal outcome**: the hub COMPLETION event (`HUB_DATA_MODEL.md` §3a) on every
  exit path including failure and cancellation. Unsupervised detachment (`nohup … &` with
  no supervisor) is forbidden; note that harness tracking alone does not satisfy the
  durability half (a tracked process can die before publishing), and a supervised host
  process that detaches CAN satisfy both. Completion events are doorbell sources.
  **Dual-signal coalescing**: a runtime task-exit notification and the completion event can
  race into two turns — consumers correlate by run id, a doorbell poke is suppressed when
  the processing cursor already covers the completion, and the invoker-as-recipient case is
  deduplicated at the event (one delivery). Runtime launch mechanics and the empirical
  notify table live in `MODEL_MATRIX.md` §3a — this section owns only the invariant.
- **Cadence (fallback)**: self-armed wake at matrix-defined interval; "arm LAST" discipline.
- **Pacemaker/watchdog (external)**: versioned in-repo, fixture-tested, notify-adapter for
  escalation (desktop/SMS/none). All of its reads and writes — heartbeat, roster
  enumeration, lease ops, watcher state — go through the **backend-dispatched seat-control
  interface** (§1): file operations on single-host registries, hub queries on postgrest
  fleets — never a hardcoded path assumption. Acts only through leases; skips `dormant`;
  covers EVERY registered seat by construction (roster = seat-control enumeration, never a
  hardcoded list — the source system's hardcoded roster silently dropped two live seats).
  **Alert dedup must not key on the frozen state it deduplicates**: a dedup key derived
  from the stall's reference epoch degrades "one alert per window" into ONE ALERT EVER for
  a never-recovering seat — the more broken the seat, the more silent its watchdog.
  Re-alert on a continued-stall schedule (interval/backoff), and the sweep always emits a
  completion line so exit-0-with-no-output is impossible (its absence is itself the death
  signal). *Origin: a seat invisible for 69 hours at 278× its cadence behind a
  frozen-epoch dedup key.*
- **Stall predicates live in the §2 table — one source.** The doorbell is never a seat's
  only signal: `standby` pairs oldest-undrained-mail age (first event past the processing
  cursor; arrivals never reset it) with the **heartbeat floor**. The floor is
  **seat-authored via a leased canary-wake**: on `floor_seconds` schedule the pacemaker
  (holding the seat's revival lease) sends a minimal canary poke; the SEAT's own turn-end
  hook writes the heartbeat as a side effect of answering it. The watchdog/pacemaker NEVER
  writes heartbeat fields — an externally-authored heartbeat certifies a dead seat as
  alive. A canary unanswered past `2 × floor_seconds` trips the floor predicate.
  Conformance includes the quiet-period case (no mail, dead loop → floor catches it) and
  the stuck-oldest case (continuous new mail must not mask an old undrained message).
  *Origins: an event-driven orchestrator whose doorbell loop died undetectably; review
  catches — the unmailed-seat blind spot, and newest-arrival masking.*

## 4a. Intentional conclusion (loop-end) protocol

Ending a wake loop at a natural checkpoint is a legitimate, first-class outcome — but only
through this ceremony; a silent non-rearm without it remains a STALL the watchdog treats as
an accident. Required steps, in order:
1. **Durable handoff brief** (the F-brief pattern): task state, branch+SHA, rulings that
   must not be re-litigated, exact next step — written to the durable brief location (never
   a rewrite-per-wake file), referenced from the hub.
2. **State marker**: cadence/registry set to `dormant` with a conclusion reason — the
   watchdog goes silent on it BECAUSE the ceremony ran, not because it lost track.
3. **SMS to the human with a COPY-PASTE BOOT PROMPT** — not a watchdog alert: a short
   message naming the seat, the checkpoint reached, and a paste-ready prompt for the
   SUCCESSOR session (pointing at the brief + dispatch id). The human boots fresh and
   pastes — one move, no archaeology.
4. **Successor is a FRESH session** (terminate-and-fresh): fresh boots hit no modal, carry
   no context rot, and the brief is the contract. Resuming the concluded session is the
   exception and follows modal economics (§3).
**Turn-end continuity check (Stop hook — the synchronous half of the enforcement).** A
commissioned seat ending a turn must hold exactly one of: an armed wake (a wake-arm
detected STRUCTURALLY — a `tool_use` content block whose `name` is a wake-arm tool — on the Claude runtime:
`ScheduleWakeup` or `CronCreate`; Codex seats have no in-session arm and use the doorbell/
pacemaker path — in this turn's transcript (turn = entries since the last REAL user/wake
boundary; `tool_result` carriers arrive typed as user entries and are turn-INTERNAL); NEVER a text match, which was measured unsound: 66% false-mention
rate on one live seat, dominated by the stall-revival directive — i.e. the text is
densest exactly where the fault is, so a text match is blindest where it matters. Turn
scoping must treat `tool_result` carriers as turn-internal, not turn boundaries, or an
early-turn arm goes invisible. Or: helper-written `next_wake_at` in the future), an
armed doorbell (standby seats: watcher marker present), or a completed conclusion ceremony
(`dormant` + reason + brief). The Stop hook checks this and **blocks once** with a
self-correcting message ("arm one or run the ceremony") — the seat still has a turn in
which to fix it, which is the whole point: the lapse is caught at the only moment the
lapser can still act. A named, logged override exists for legitimate hand-to-human waits
(`awaiting-user-tap`). Rollout follows emit-before-enforce (warn-only first) and ships its
negative-case fixture (a transcript with no arm → the check demonstrably fires). Scope
honesty: this catches CONSCIOUS lapses — the majority class in the observed fleet
wind-down; parked sessions and killed processes produce no Stop event, so the watchdog
remains the asynchronous net for those. The two are complementary layers, not
alternatives.

The watchdog's job narrows to what it should be: catching ACCIDENTS. Intentional endings
never reach it. *Origin: seats concluding work without re-arming looked identical to
stalls, burning watchdog attention and human ambiguity on deliberate checkpoints.*

Briefs carry a machine-readable `authored_by` (seat letter, or `orchestrator-reconstructed`
when O writes one on behalf of a seat that never ran the ceremony — the honesty lives in
the artifact; enforcement may key on it).

**Fleet-level wind-down** (the ceremony generalized; origin: an overnight fleet wind-down
without ceremony, benign only because nothing was in flight, costing five morning taps for
one cause): on a single triggering event ("the human is going to sleep"), O broadcasts
WIND-DOWN; every seat runs the per-seat ceremony but does NOT notify individually — a
wind-down that pages the human N times is worse than the silence it replaces; O sends ONE
consolidated resume packet naming every seat, its brief, and its dispatch id. Morning is
one broadcast. **The real property is diagnostic, not convenience**: after a ceremonial
wind-down, any silent seat is silent BY ACCIDENT — silence regains meaning.

## 5. Mailboxes

- **A mailbox is a recipient-filtered view over hub events** — never an independent
  authoritative write (see hub spec §1: the transport derives from the same append).
  Materialized per-recipient JSONL files, where used, are rebuildable projections written by
  the hub append path itself, not by senders directly.
- Recipient isolation is **enforced by the backend where it can be** (postgrest:
  recipient-scoped reads). On the portable single-host backends it is a stated trust
  assumption: **seats within one project are mutually trusted** (hub spec §4); own-letter-only
  remains the protocol rule everywhere because a read advances the processing cursor —
  reading another seat's mail destroys their delivery.
- **Inspecting another seat's mail** (a legitimate operator request) is done
  NON-DESTRUCTIVELY: read the stream from their stored cursor offset WITHOUT writing the
  cursor — never via the consuming read verb, whose obvious use silently eats messages the
  seat is holding.
- Drain on boot and at phase boundaries; drain files are read whole.
- **Assume the transport is lossy; verify, don't trust.** Five silent-corruption modes were
  observed in ONE day on a mature mailbox transport (timeout-never-wrote, backticks blanked,
  sender-shell `$()` execution, subject/body collapse, flag-eaten-as-positional). Rules:
  message bodies never pass through interpolating strings; CLI arg-parsers reject
  flag-shaped positionals loudly instead of absorbing them. **Read-back contract**: every
  send that matters is verified by the SENDER via a non-consuming lookup — by `hub_id` in
  the authoritative log (hub query, or the sender's own outbound file, which no recipient
  cursor touches) — comparing a payload digest, never a skim; on absence/mismatch, one
  retry then a loud failure. Recipient-side projections are NEVER read for verification
  (that would consume another seat's cursor).
- **Subagent results are claimed, not assumed.** A silent return, empty task list, or idle
  notification is NOT evidence an agent produced nothing — completed work can sit
  undelivered (parked sessions, reorientation, delivery drops). **Roster-at-spawn**: BEFORE
  spawning, record the expected agent names in your own notes and reconcile delivery
  against THAT list — never against the runtime's after-the-fact enumeration, which shares
  the failure mode it would be verifying (a baseline consulted from a possibly-broken
  instrument is recorded before the instrument is needed). The portable mechanism is a
  harness task-record per spawn: {task id, agent name, completion receipt, result digest,
  delivery state, parent claim}. **The agent→parent channel is DELAYED AND BATCHED, not
  lossy** (third revision of this guidance, each on new evidence — kept honest by three
  seat self-retractions): sends that return success DO arrive, but delivery can flush
  late, batched at session boundaries (turn events, compaction), with **no signal
  distinguishing "not yet arrived" from "never arriving" — that observability gap is the
  actual defect.** Consequences: a send-success is still not *receipt-yet*; nudging
  remains a valid, cheap prompt for the pipe to flush; and **declaring a lens NOT RUN
  requires a transcript check first** — if the transcript shows the work produced and
  sent, the report is IN FLIGHT: wait or transcript-recover, never declare a produced
  report dead (a false NOT-RUN is its own false claim). Transcript-reading is thus both
  the recovery path and the way to SEE produced-but-unsurfaced work. Transcript-recovered
  findings are labeled as such; provenance upgrades after a posted verdict are disclosed
  in a supplement, never silent. (A pinned agent definition fixes tier inheritance, NOT
  delivery — independent fixes, never read as one.)
  **Reorientation loses subagents**: redirecting a session mid-fan-out silently orphans its
  agents while it believes the fan-out ran — reorientation is BLOCKED while spawned tasks
  are outstanding (finish, or explicitly cancel/snapshot with the orphan list disclosed);
  after any reorientation, delivery is re-verified against the roster-at-spawn.

## 6. Codex-seat specifics (first-generation constraints)

- **Trust**: every workdir (main checkout + each worktree) needs a
  `[projects."<path>"] trust_level = "trusted"` entry, or its `.codex/` layer silently
  no-ops. The launcher verifies trust at boot and fails loudly if absent.
- **Hooks trust**: interactive seats trust hooks once via `/hooks`; headless pokes use
  `--dangerously-bypass-hook-trust` ONLY for definitions vetted in-repo (hash-pinned list).
- **`.rules` execpolicy**: generated from the authored command-policy source
  (`policy.yaml`, owned by `MODEL_MATRIX.md` §1a) per seat class — this spec cites policy
  ids (e.g. `ban.merge.non-integrator`, `ban.staging-ddl.all`) and never restates rule
  content. Unit-tested via `codex execpolicy check`.
- **Delegation gate**: Codex won't self-spawn subagents unless AGENTS.md grants it — the
  no-subagents ruling is enforced by simply never granting it (and `ultra` effort, which
  auto-delegates, is not in the matrix).
- **Auth**: seats share the ChatGPT-plan `auth.json`. Until the concurrent-refresh race is
  tested (Phase 4 checklist), run FEW long-lived Codex seats, not parallel exec fan-outs.
  CI use requires API-key auth — never plan tokens.
- **Roles and write scope — SUPERSEDED 2026-07-28 by the trust-parity ruling**
  (`MODEL_MATRIX.md` §3b). The prior text ("first roles read-heavy; write scope is a Phase-5
  decision on pilot evidence") is retired: a second-runtime thinking seat holds the same
  standing as the first-runtime thinking seat and may hold a seat, take and issue dispatches,
  and write. Sandbox is sized to the WORK, not the runtime — read-only where reading suffices
  (it is also cheaper and clearer to audit), write scope where the work needs it, no separate
  trust argument. Cluster invariants still bind every seat on every runtime: merge
  serialization (integrator only), guarded paths for shared-environment mutation, ceremonies
  for irreversible/outward-facing acts, and no self-verdicting.
- **Capability caveat carried from the trust ruling**: a sandboxed probe proves presence and
  its own sandbox's behavior — never the machine's auth or capability. Two 2026-07-28 probes
  misread sandbox denials as machine defects. Every negative observed from inside a sandbox
  needs an unsandboxed control before it is recorded as a finding.
- **Known runtime gap (this fleet, 2026-07-28)**: snap-packaged CLIs can fail under the Codex
  sandbox before executing (gcloud: `cannot create transient scope` / DBus), while working
  normally unsandboxed. Launcher/profile design must either provision non-snap equivalents or
  grant the sandbox allowance; discover this per-machine rather than assuming.

## 6a. Registry migration (live-path move)

The registry relocation (`sessions/<L>.id` → `<project_id>/sessions/<letter>.json`) moves a
path read by **seven live sites** (launcher, msg CLI, fleet-status, both cron ingest
wrappers, the ingester, and the session-start hook) — so it ships phased: (1) new tooling
writes BOTH forms and reads new-then-legacy; (2) each reader site migrates against a
checklist enumerating all seven; (3) legacy files retire only when the checklist is clean.
**Letter case**: canonical form in all protocol files is **lowercase**; adapters normalize
at external boundaries that demand otherwise (e.g. a DB CHECK constraint requiring
uppercase) — the mirror contract names this conversion explicitly.

## 7. Routed review findings dispositioned here

- Seat lifecycle races / split-brain (major): §2 — leases + fencing epochs on every revival path.
- Non-revivable runtimes (major): §1 — capability negotiation; report-only watchdog mode.
- Doorbell races/bursts/missed events (major): §4 — cursor-based subscribe, coalescing, expiry, lease.
- Mailbox authorization (major, shared with hub spec): §5 — mechanism where possible, etiquette as last resort.
- Trust/secrets boundary (major, partial): §6 — trust verification at boot, hash-pinned hook bypass list, .rules bans; full threat model is the named `THREAT_MODEL.md` planned spec in `ARCHITECTURE.md` §9 with acceptance criteria (not silently dropped).

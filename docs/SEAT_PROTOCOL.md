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
  "capabilities": { "resumable": true, "external_invoke": "remote-control | exec-resume | tmux-keys | none", "hooks": true, "memory": false },
  "lease": { "holder": null, "epoch": 0, "expires_at": null }
}
```

Capabilities are **negotiated at boot** (probed, not assumed) and re-probed on runtime
upgrade. A runtime with `external_invoke: none` is a supported capability level: it is woken
only by its own cadence loop or a human, and the watchdog reports rather than revives.

## 2. Lifecycle state machine

```
booted → active ⇄ standby (armed wake) → dormant (deliberate, next_wake=none)
active/standby → STALLED (heartbeat age > grace)  → revived → active
any → dead (stalled + revival budget exhausted, or operator-declared) ↘ report-only if not revivable
```

- **Heartbeat**: written by a turn-end hook on BOTH runtimes (Codex hooks support Stop; the
  writer is the same portable script). Fields: state, role, heartbeat_at, wake_count,
  cadence_seconds, next_wake_at, context. Schema-validated on write AND read — prose in a
  numeric field is a loud error, not a watchdog crash.
- **Grace**: `max(floor, 2 × cadence_seconds)`. `dormant` + `next_wake_at: none` is
  deliberate sleep, never a stall.
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
  which the seat runs unleased again. **The normative state predicates**: STALLED =
  heartbeat age > grace (and state not `dormant`); DEAD = stalled AND the configured
  revival budget is exhausted (N failed/unclaimed revival windows) or an operator declares
  it. Lease state never defines liveness; process checks are diagnostics for reports, never
  triggers.
  Conformance: adversarial concurrent-acquisition fixtures (two racers, N racers,
  crash-mid-acquire, **delayed-racer-after-commit, renewal-vs-acquisition race, registry
  recreation mid-lease** — token fencing must hold across a recreated registry) run
  against every registry backend.

## 3. Launch and resume

| | Claude seat | Codex seat |
|-|-|-|
| Boot | `role-launch` semantics: `claude -n <L> --remote-control <L> --model <m> --effort <e>` in a pane | `codex --profile <project_id>-<tier>` in a pane; first action `/rename <letter>`; registry stores thread name |
| **Tier verification (both runtimes, mandatory)** | launcher confirms the booted session reports the intended model+effort | **empirically required**: a nonexistent Codex profile boots the DEFAULT tier with exit 0, and config errors are non-fatal — the launcher runs a post-boot probe asserting the RESOLVED model/effort and fails loudly on mismatch; tier selection is never trusted |
| Resume | `--resume <uuid>` / remote-control push | interactive `codex resume <name>`; headless poke: `codex exec resume <letter> "<drain prompt>" < /dev/null` |
| Tier | model+effort args from matrix | **project-qualified** profile (`~/.codex/<project_id>-<tier>.config.toml`), selected by the launcher from the seat record's `project_id` — two consuming projects never collide; per-poke override `-c model_reasoning_effort=...` |
| Effort constancy | hold constant per session (prompt-cache) | same rule |

Launcher is one script, runtime-dispatched by the seat record. Boot prompts come from
role templates; the launcher never injects them as positional args (silent no-op trap on
Claude interactive; unverified on Codex — templates are pasted/poked, not arg-passed).

## 4. Wake model

- **Doorbell (preferred, cross-seat only)**: a bounded watcher re-invokes the seat ON an
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
- **Cadence (fallback)**: self-armed wake at matrix-defined interval; "arm LAST" discipline.
- **Pacemaker/watchdog (external)**: versioned in-repo, fixture-tested, notify-adapter for
  escalation (desktop/SMS/none). All of its reads and writes — heartbeat, roster
  enumeration, lease ops, watcher state — go through the **backend-dispatched seat-control
  interface** (§1): file operations on single-host registries, hub queries on postgrest
  fleets — never a hardcoded path assumption. Acts only through leases; skips `dormant`;
  covers EVERY registered seat by construction (roster = seat-control enumeration, never a
  hardcoded list — the source system's hardcoded roster silently dropped two live seats).
- **Per-state stall predicates — the doorbell is never the only signal.** Cadenced seats
  (`awake`/`sleeping`): heartbeat/`next_wake_at` age vs grace. Event-driven seats
  (`standby`, no `next_wake_at`): **undrained-mail age** — newest mailbox arrival vs the
  seat's processing cursor; a quiet doorbell seat is silent, a DEAF one is loud. `dormant`:
  never alarmed. Every registered seat matches exactly one predicate; a seat whose state
  matches none is itself a loud finding. **Undrained-mail age detects deafness only when
  mail exists** — a seat nobody wrote to looks healthy under it — so event-driven seats
  ALSO keep a slow heartbeat floor (a mandatory minimum-cadence heartbeat write, e.g.
  hourly, independent of any initiator); floor-age is the second predicate, and the pair is
  tested against the quiet-period case explicitly. *Origins: an event-driven orchestrator
  whose doorbell loop died undetectably — heartbeat legitimately quiet by design, broken
  doorbell its only signal; boundary caught in review: the replacement predicate would have
  inherited the same blind spot for unmailed seats.*

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
- Drain on boot and at phase boundaries; drain files are read whole.

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
- **First roles: read-heavy** (review/audit/second-opinion), `sandbox read-only` +
  `codex apply` for proposed patches. Write scope is a Phase-5 decision on pilot evidence.

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

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
any → dead (lease expired, unrenewed past grace)   ↘ report-only if not revivable
```

- **Heartbeat**: written by a turn-end hook on BOTH runtimes (Codex hooks support Stop; the
  writer is the same portable script). Fields: state, role, heartbeat_at, wake_count,
  cadence_seconds, next_wake_at, context. Schema-validated on write AND read — prose in a
  numeric field is a loud error, not a watchdog crash.
- **Grace**: `max(floor, 2 × cadence_seconds)`. `dormant` + `next_wake_at: none` is
  deliberate sleep, never a stall.
- **Leases + fencing (CAS, not blind write)**: every revival path (pacemaker, doorbell,
  human script) must acquire the seat's lease via **compare-and-swap**: read
  `{epoch: n, holder, expires_at}`; acquisition succeeds only if the CAS primitive
  atomically verifies `epoch == n AND (holder is null OR expires_at < now)` while writing
  `{epoch: n+1, holder: <unique token>, expires_at}`. Two racers reading epoch n cannot both
  win — exactly one CAS succeeds; the loser observes the changed epoch and stands down.
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
  immediately. Renewal extends `expires_at` under the same holder; release nulls holder
  without bumping epoch. **The one normative dead predicate: lease expired and unrenewed
  past grace.** Process liveness checks are diagnostics for the report, never the trigger.
  Conformance: adversarial concurrent-acquisition fixtures (two racers, N racers,
  crash-mid-acquire, **delayed-racer-after-commit, renewal-vs-acquisition race**) run
  against every registry backend.

## 3. Launch and resume

| | Claude seat | Codex seat |
|-|-|-|
| Boot | `role-launch` semantics: `claude -n <L> --remote-control <L> --model <m> --effort <e>` in a pane | `codex --profile <tier>` in a pane; first action `/rename <letter>`; registry stores thread name |
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

## 7. Routed review findings dispositioned here

- Seat lifecycle races / split-brain (major): §2 — leases + fencing epochs on every revival path.
- Non-revivable runtimes (major): §1 — capability negotiation; report-only watchdog mode.
- Doorbell races/bursts/missed events (major): §4 — cursor-based subscribe, coalescing, expiry, lease.
- Mailbox authorization (major, shared with hub spec): §5 — mechanism where possible, etiquette as last resort.
- Trust/secrets boundary (major, partial): §6 — trust verification at boot, hash-pinned hook bypass list, .rules bans; full threat model is tracked as a named M3 deliverable in ROADMAP (not silently dropped).

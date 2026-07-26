# Seat Protocol

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §6. Seats are the unit of
> cross-session work: persistent, addressable, revivable terminal sessions on any supported
> runtime.

## 1. Seat record

Registry: one JSON file per seat at `<coordination-root>/sessions/<letter>.json`
(supersedes the bare `<letter>.id` files):

```json
{
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
any → dead (lease expired + process gone)          ↘ report-only if not revivable
```

- **Heartbeat**: written by a turn-end hook on BOTH runtimes (Codex hooks support Stop; the
  writer is the same portable script). Fields: state, role, heartbeat_at, wake_count,
  cadence_seconds, next_wake_at, context. Schema-validated on write AND read — prose in a
  numeric field is a loud error, not a watchdog crash.
- **Grace**: `max(floor, 2 × cadence_seconds)`. `dormant` + `next_wake_at: none` is
  deliberate sleep, never a stall.
- **Leases + fencing**: every revival path (pacemaker, doorbell, human script) must acquire
  the seat's lease (atomic write of holder + incremented epoch + expiry) before acting.
  A revival carries its epoch; a seat that observes a newer epoch than its own **stops** —
  the fencing rule that makes double-revival impossible. Lease expiry, not process guesswork,
  defines `dead`.

## 3. Launch and resume

| | Claude seat | Codex seat |
|-|-|-|
| Boot | `role-launch` semantics: `claude -n <L> --remote-control <L> --model <m> --effort <e>` in a pane | `codex --profile <tier>` in a pane; first action `/rename <letter>`; registry stores thread name |
| Resume | `--resume <uuid>` / remote-control push | interactive `codex resume <name>`; headless poke: `codex exec resume <letter> "<drain prompt>" < /dev/null` |
| Tier | model+effort args from matrix | profile file (`~/.codex/<tier>.config.toml`) from matrix generator; per-poke override `-c model_reasoning_effort=...` |
| Effort constancy | hold constant per session (prompt-cache) | same rule |

Launcher is one script, runtime-dispatched by the seat record. Boot prompts come from
role templates; the launcher never injects them as positional args (silent no-op trap on
Claude interactive; unverified on Codex — templates are pasted/poked, not arg-passed).

## 4. Wake model

- **Doorbell (preferred, cross-seat only)**: a bounded watcher re-invokes the seat ON an
  event (mailbox append, artifact landing). Contract: watcher subscribes **from its hub
  cursor** (missed-event-safe — an event landing before the watcher armed is still seen);
  bursts coalesce (one wake per quiet-window, not per event); watcher expiry = seat's grace
  window; every wake goes through the lease (§2). In-session subagents NEVER use doorbells —
  the harness re-invokes the parent natively.
- **Cadence (fallback)**: self-armed wake at matrix-defined interval; "arm LAST" discipline.
- **Pacemaker/watchdog (external)**: versioned in-repo, fixture-tested, notify-adapter for
  escalation (desktop/SMS/none). Reads heartbeat files; acts only through leases; skips
  `dormant`; covers EVERY registered seat by construction (roster = registry glob, never a
  hardcoded list — the source system's hardcoded roster silently dropped two live seats).

## 5. Mailboxes

- JSONL append files + per-reader cursors (or hub-backed when the backend supports
  recipient-scoped reads). **Reads are recipient-scoped by mechanism wherever the backend
  can enforce it**; own-letter-only remains the protocol rule everywhere (a read advances
  the cursor — reading another seat's mail destroys their delivery).
- Drain on boot and at phase boundaries; drain files are read whole.

## 6. Codex-seat specifics (first-generation constraints)

- **Trust**: every workdir (main checkout + each worktree) needs a
  `[projects."<path>"] trust_level = "trusted"` entry, or its `.codex/` layer silently
  no-ops. The launcher verifies trust at boot and fails loudly if absent.
- **Hooks trust**: interactive seats trust hooks once via `/hooks`; headless pokes use
  `--dangerously-bypass-hook-trust` ONLY for definitions vetted in-repo (hash-pinned list).
- **`.rules` execpolicy**: hard bans generated from policy config per seat class — e.g.
  non-integrator: `gh pr merge` forbidden; all seats: staging `apply_migration` forbidden.
  Unit-tested via `codex execpolicy check`.
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

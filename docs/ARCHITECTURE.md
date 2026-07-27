# Architecture (v2)

> Status: **v2, 2026-07-26** — supersedes the 8-layer model (v1, ~2026-03) and resolves its
> conflict with `REVIVAL_SCOPING.md` §3 in favor of the **three-layer lens**. The old 8 layers
> survive as components mapped into the new layers (§3). Authored under the agentic-separation
> program (customer-portal plan `mossy-discovering-moler`); design inputs traced there.

## 1. Design laws

The v1 principles (route don't dump · load on demand · enforce don't suggest · tests define
done · the system improves itself) still hold. v2 adds seven laws learned from watching the
source system rot in specific, diagnosable ways:

1. **Fail loudly.** A gate or hook that cannot resolve its inputs reports that visibly —
   silent-success and broken must be distinguishable. For *local-only* state (gitignored
   session files), "loud" means a visible warning naming the missing/malformed input; it must
   never brick a seat. Hard-fail is reserved for CI-visible contexts where the input is
   versioned. *Origin: nine enforcement gates in the source system fell through to
   `{"continue": true}` for months after a state-format drift, without one error.*
   **The trust-test generalization** (one incident night produced ~19 defects sharing a
   single shape — every instrument degraded toward "looks fine / looks like a normal
   defect," never toward an obvious error): *for any signal you are about to trust, ask
   what it would show if it were broken. If the answer is "something plausible," that
   signal cannot be used alone — verify at a different layer, or record a baseline BEFORE
   consulting it.* Loud failures get fixed the day they happen; plausible failures
   accumulate (three ran 69 hours), and several were introduced by fixes to the same class.
2. **Single source of truth; indexes are generated.** Four content categories, never
   conflated: *authored source* (edited by humans/agents), *generated artifacts* (derived from
   source; never hand-edited; freshness-gated in CI via regenerate + `git diff --quiet`),
   *runtime state* (rosters, heartbeats, chain state — mutable, excluded from freshness
   gates), and *derived views* (computed on read, never stored). Any index, map, or matrix is
   a generated artifact. Hand-groomed indexes decay to lies. *Origin: a documentation map
   whose every count was wrong and which omitted the system's entire current command surface.*
3. **Two context layers, explicit everywhere.** Layer A = agentic development platform
   (this framework's scope: levers, hooks, coordination, TDD method, seat protocol).
   Layer B = project context (the consuming project's scope: domain skills, schema, product
   docs, deployment). Ownership is at **file granularity everywhere except a small named set
   of composite files** (AGENTS.md, CLAUDE.md, settings) where the two layers must share one
   runtime-facing artifact — there, ownership is at *region* granularity: framework-owned
   regions are forge-marked, region membership is manifested, and updates to framework regions
   are applied by a deterministic composer with a defined conflict policy, not by whole-file
   copy. Copier update-hygiene (`_skip_if_exists` / `_exclude`) enforces the file-level
   boundary; the composer + conformance tests enforce the region-level one. The two layers are
   separately planned, staffed, and paced — each with its own internal tier hierarchy.
4. **Progressive disclosure under a hard budget.** The repo-owned entry payload is
   CI-budgeted (28 KB, headroom-reserving); the **combined** payload including user-level
   context is verified at seat launch / doctor time, where the uncontrolled tier is actually
   visible — so the Codex 32 KB truncation ceiling is never crossed in a conforming
   environment, and a global tier that breaches headroom is a named local-environment
   nonconformance, not silent truncation. Everything deeper is routed by reference.
5. **Multi-consumer from day one.** Coordination state (hub records, rosters, dispatches) is
   project-namespaced; storage backends are pluggable. The framework must serve a second
   consuming project without schema surgery.
6. **Record-as-byproduct.** Transport is a side-effect of recording — one append yields both
   the durable record and the message. Derived views are computed on read, never
   hand-maintained. Cross-seat waits use event doorbells (a bounded watcher that re-invokes
   the session *on* the event); polling cadence is the fallback, not the default. Doorbells
   are a cross-session primitive only — in-session subagents already re-invoke their parent.
7. **Additive migration only.** Every change to a live consuming project ships through its
   normal PR flow, and the old path keeps working until the new one is proven.
8. **A rule that gates an ACTION must state the action's own side effects**, not only the
   preconditions on its subject. *Origin: a freeze rule permitting merges of validly-green
   PRs — every clause individually true — while a merge IS a push that would have fired
   dying CI on the integration branch itself. Checked the artifact's state; never priced
   the action.* Corollary for incident procedure: distinguish merge-READY (a state) from
   merge-PERMITTED (an action authorization); readiness is never permission.
9. **STOP must have a route to the actor.** Every gate and every authority pattern answers
   explicitly: *how does STOP reach the party who can proceed?* A system that makes GO easy
   and STOP hard ships things it already knew were wrong. Two corollaries: a verdict/gate
   tool must be able to EXPRESS a block (gate-lifecycle rule d); and **standing authority
   costs deliberate countermand** — where standing authority exists, a hold is an explicit
   revocation delivered TO THE HOLDER, never silence and never a message to someone else
   (telling the fixer to hurry is not telling the merger to wait). *Origin: a contradiction
   merged to main sixty seconds before its pause-confirm — the hold had been addressed to
   the fixer while the merger held standing GO.*

## 2. The three layers

```
L1  PORTABLE CORE          the single-session development method
    context contract · levers (scope/go/check) + chain state · ATDD/TDD gate ·
    hooks pipeline + evidence ledger · dev-log · memory scaffolding · agents (spec-auditor)

L2  ORCHESTRATION TIER     many sessions, one program
    hub (verbs + project-namespaced state, pluggable backends) · seats + roster + launcher
    (runtime-plural: claude | codex) · mailboxes · cadence/heartbeat · pacemaker/watchdog ·
    doorbells · model/effort matrix (generated config)

L3  INFRA ISOLATION        parallel work without collisions
    worktrees · DB isolation adapters (none/schema/compose/branch) · port allocation ·
    per-worktree trust/config for each runtime
```

Adoption is **cumulative** (L2 builds on L1; L3 assumes L2's seats), while components are
**independently testable**. The following table is THE normative conformance statement —
where any other document's phrasing differs, this table wins:

| Profile | Tiers | Spec-audit cardinality | Second opinion | Author/reviewer separation |
|-|-|-|-|-|
| solo | L1 | 1 fresh-context audit | independent fresh-context pass; **cross-runtime only if a second runtime is configured** | satisfied by fresh context (subagent on Claude; fresh `exec` thread on Codex) — the solo exception |
| fleet | L1+L2 | 2 fresh-context audits | cross-runtime pass **required if a second runtime is configured, recommended otherwise** | reviewers are never the authoring session |
| isolated-fleet | L1+L2+L3 | as fleet | as fleet | as fleet, plus isolation-adapter conformance |

"Fresh context" is runtime-neutral: a Claude subagent, or a fresh Codex `exec` thread — a
Codex-only solo project is fully conformant. Authoring-tier work maps to the best available
runtime's thinking tier when the preferred one is absent (matrix `fallback` chains).

## 3. Where the v1 layers went

| v1 layer | v2 home | Notes |
|-|-|-|
| L0 Entry/router | L1 context contract | AGENTS.md-canonical; see §4 |
| L1 Skills | L1 (orchestrator skills) + **Layer B** (domain skills) | domain skills are project context, not framework |
| L2 State machine | L1 (chain state + lifecycle files) | the "state-file chain" reading; the *orchestration* reading of "L2" is now the actual L2 |
| L3 ATDD gate | L1 TDD gate | rebuilt fail-loud; see TDD_GATE spec |
| L4 Hooks | L1 hooks pipeline | decomposed runner + fixture harness is canonical |
| L5 Agent teams | L1 (in-session teams) + L2 (cross-session seats) | the boundary is the session: teams live inside one session; seats are sessions |
| L6 CI/CD | L1 gate definitions + Layer B implementation | framework ships gate *patterns* + a generated-project CI skeleton; the project owns its pipeline |
| (DB isolation) | L3 **interface** (framework) + Layer B **implementations** | framework owns the adapter interface, lifecycle contract, and conformance suite (`ISOLATION_ADAPTERS.md`, planned); projects own concrete adapters/config |
| L7 Memory | L1 memory scaffolding | index ≤ a hard byte budget; topic files; generated index discipline applies |

The two incompatible definitions of "Layer 2" (state-file chain vs orchestration tier) are
hereby resolved: **L2 means the orchestration tier.** The state-file chain is an L1 component.

## 4. Context contract (summary — full spec: `CONTEXT_CONTRACT.md`)

- **AGENTS.md is canonical.** It is the shared entry contract read natively by Codex and via a
  one-line `@AGENTS.md` import by Claude Code (`CLAUDE.md` = the import + runtime-specific
  extras only). Nested AGENTS.md files scope subtree guidance (loaded only when working
  there). The ecosystem (Cursor, Windsurf, Cline) reads root AGENTS.md natively; this contract
  is CLI-first but IDE-compatible.
- **Delivery tiers**: global (user-level, both runtimes) → repo root → nested. Content at each
  tier is layer-tagged (A or B). The CI budget check (law 4) covers the **deterministic,
  repo-owned** worst-case concatenation per working directory — the ceiling applies to the
  payload, not the root file; uncontrolled user-level/global context is reported separately
  with reserved headroom, since CI cannot see it.
- **Resolution is runtime-specific and must be compiled, not assumed.** Codex discovers
  nested AGENTS.md natively; Claude Code does not — nested delivery to Claude requires
  per-directory `CLAUDE.md` shims (`@AGENTS.md`) or a context compiler that emits each
  runtime's native entry files from the canonical hierarchy, with an exact precedence
  algorithm and per-runtime compatibility tests. Native-discovery claims are pinned to
  tested runtime versions, not taken on faith.
- **Two-axis organization**: tier (global/root/nested) × layer (A agentic / B project). Layer A
  content is forge-marked and framework-owned; Layer B content is project-owned. Nested
  AGENTS.md files are the bridge: they reference Layer B domain indexes so project knowledge
  is one hop from every seat without inflating the entry budget.
- **Runtime deltas stated once**: Claude-only channels (auto-memory, skill `/name` invocation,
  hooks-injected context) and Codex-only channels (`$name` skills, `.rules` execpolicy,
  `--output-schema`) are documented in the contract; durable rules a Codex seat needs must
  live in AGENTS.md or `.rules` — never only in Claude memory.

## 5. Levers and the chain (L1)

The execute lever is **`go`** — the proven live triad is `scope → go → check`, with
convergence state in `context/CHAIN.json` and knobs in `chain-config.json`. The v1 `work`
family is retained as the lifecycle sub-skill set (`start/continue/pause/handoff/done`,
epic/sprint planning) invoked *by* the levers, not as a competing top-level surface. All
three levers share the orient → equip → act skeleton; iteration-counter ownership, tier
ladders, stall detection, and relay mechanics are defined once, in the chain skill, and
referenced — never restated — by the levers (law 2 applies to skill content too).

The development loop, end to end (mandatory stages bolded; audit/second-opinion mechanics
per the §2 profile table): **scope** (design + SPEC) → **spec-audit** → **RED** (Standard+
scope; Quick scope may satisfy it as same-change per `TDD_GATE.md` §4 — the one declared
exemption) → **GREEN** → **review** (cross-review) → **integrate** → **document** (doc delta
or explicit no-doc-impact declaration, gated like tests) → **capture** (durable parking of
discoveries via hub verbs). Details: `DEV_LOOP.md`.

## 6. Seats, runtimes, and models (L2 — full specs: `SEAT_PROTOCOL.md`, `MODEL_MATRIX.md`)

A **seat** is `{letter, runtime: claude|codex, model, effort, workdir, session-handle}` —
a persistent, addressable, revivable terminal session. Revival is governed by a seat state
machine with leases/fencing so watchdog, pacemaker, and doorbell can never revive the same
seat twice (split-brain); runtimes that cannot be externally re-invoked are a declared,
supported capability level, not an assumption violation (spec: `SEAT_PROTOCOL.md`). Seats coordinate through the hub and
mailboxes; they never read another seat's mailbox. In-session subagents are for judgment work
that correctly inherits the seat's tier, and for read-only exploration; **hands work goes to
a seat, and Codex participates only as seats, never as subagents.**

The model/effort matrix is **generated configuration** (questionnaire dial + per-project
overrides), not prose — the source system rewrote its model policy three times in two weeks
inside hand-edited documents; a matrix-as-data with one generator would have been one-line
changes. Tier principles: judgment and synthesis-of-understanding run on thinking-tier
models; execution runs scoped-down; maintenance documentation may drop tiers only after the
hierarchy exists to scope it; cross-runtime second opinions are a standing lane.

## 7. Hub (L2 — full spec: `HUB_DATA_MODEL.md`)

The hub is a verb interface — `dispatch / status / rule / thread / finding / attention /
journal / role` writes, `seats / open / mine / blocked` reads — over project-namespaced state
with pluggable backends: `postgrest` (shared Postgres/Supabase), `sqlite` (portable default),
`jsonl` (degraded file-drop). One append = record + transport (law 6). Every verb the
protocol needs exists as a verb; raw SQL against hub tables is repair-only.

Backends are NOT assumed interchangeable: the hub spec defines a semantic contract — stable
client-minted event IDs, idempotent writes, per-stream ordering, at-least-once delivery with
consumer cursors, and crash-recovery behavior — and every backend must pass one shared
conformance suite, with degraded-mode guarantees (jsonl) stated, not implied. Tenant
isolation is part of the same contract (immutable project IDs, compound keys,
backend-enforced authorization), not a namespace column bolted on.

## 8. Enforcement doctrine (L1)

- Gates read **machine-readable, schema-validated state** — never prose formats that drift
  silently. Absent-state semantics per law 1.
- The evidence ledger records what *ran* (build, tests, RED/GREEN phases) from inside the
  actual runners — an agent's claim that a test ran is not evidence. Evidence carries
  **provenance**: bound to the commit/tree hash, worktree, and command it came from, with
  freshness rules — stale or unrelated results cannot satisfy a gate. Overrides exist but are
  named, logged tokens, never silent bypasses.
- Every check is a file, independently testable against shipped fixtures; the hook test
  harness is part of the framework and runs in the framework's own CI *and* in generated
  projects.
- **Gate lifecycle rules**: (a) *a requirement for a guard specifies how its negative case
  will be demonstrated* — "hard-fail if X" is unobservable as stated; "and show it fires
  when X is forced" makes it provable; (b) *emit before enforce* — a gate judging state
  other parties write emits its evidence fields before enforcing them, so enforcement day
  is never migration day; (c) *no off-by-default enforcement* — a gate defaulting to
  not-gating tends to stay that way (a toll nobody collects); prefer strict code behind
  explicit sequencing over flags; (d) *a well-formedness tool supports the full disposition
  space* — a gate tool that can only emit PASS applies its structural guarantee precisely
  where the stakes are lowest, forcing every blocking verdict back into the hand-authored
  path the tool was built to eliminate; (e) *grounding-at-authoring-time beats intent* —
  the author who RULED an enforcement is the person most likely to describe it as already
  live ("I made the ruling, so it felt true"); guidance describes the runtime as it IS and
  states obligations on actors, gaining tool-enforced halves when they actually land.
- **The aggregate gate is not a formality.** Units that each pass their own review can
  create a contradiction ONLY on merge — a defect class invisible to per-unit review by
  construction. The integration-level gate (cascade review) exists precisely for this, and
  "everything in it was already reviewed" is exactly the wrong argument against it. When an
  aggregate contradiction is found pre-merge, the fix precedes the merge: the target is
  consistent NOW; the merge is what would create the defect.
- **Schema'd files humans write under pressure get helpers that refuse invalid input** —
  hand-authoring is how `state: active` and prose-in-numeric-fields enter production state;
  the helper IS the schema enforcement (two independent instances in one day, one of them
  the orchestrator's own file, one the director's habit).
- Documentation is a gated stage (law: doc delta or explicit no-doc-impact), and generated
  indexes are freshness-gated — the two mechanisms that keep the delivery layer current-by
  construction rather than current-by-diligence.

## 9. Sibling specifications

| Spec | Scope | Status |
|-|-|-|
| `CONTEXT_CONTRACT.md` | AGENTS.md hierarchy, budgets, runtime deltas, layer tagging | Phase 1 |
| `HUB_DATA_MODEL.md` | namespaced schema, verb interface, backend adapters | Phase 1 |
| `SEAT_PROTOCOL.md` | roster, launcher, revival, codex seat mechanics, doorbells | Phase 1 |
| `MODEL_MATRIX.md` | matrix-as-data format, generator, initial values | Phase 1 |
| `DEV_LOOP.md` | loop stages, role→seat mapping, mandatory gates | Phase 1 |
| `TDD_GATE.md` | fail-loud gate rebuild, evidence ledger, state contract | Phase 1 |
| `REVIVAL_SCOPING.md` | strategic memo this v2 ratifies (its §3 lens, its §7 rulings) | historical |
| `WORKSPACE_LIFECYCLE.md` | workspace/DB/local-file classes, persistence tiers, provisioning/sync/cleanup ownership, registry semantics | Phase 1 (added by director ruling 07-26) |
| `ISOLATION_ADAPTERS.md` | L3 adapter interface: lifecycle state machine, provisioning/cleanup/recovery contract, port leases, conformance suite | **planned (M3)** — acceptance: all four adapters pass one suite |
| `VERSIONING.md` | template/schema/state compatibility: semver, ranges, migrations, deprecation windows, Copier upgrade tests | **planned (M3)** — acceptance: upgrade from prior template version passes generate-matrix CI |
| `THREAT_MODEL.md` | trust boundaries, credentials, secret redaction, hook integrity, untrusted-PR behavior, override-token audit | **planned (M3)** — acceptance: every enforcement mechanism maps to a stated boundary |

A cross-runtime adversarial review of this document (GPT-5.6 Sol @ xhigh via `codex exec
--output-schema`, 2026-07-26) is archived at `docs/reviews/2026-07-26-codex-architecture-v2.json`.
Its architecture-level findings are incorporated above; its spec-level findings (hub delivery
semantics, seat leases, isolation-adapter lifecycle, evidence provenance details, mailbox
authorization, doorbell races, framework versioning/threat model, CI gate contract) are
routed to the owning sibling specs and MUST be dispositioned there before each spec is
considered complete.

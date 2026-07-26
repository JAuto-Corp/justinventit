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
2. **Single source of truth; indexes are generated.** Any index, map, roster, or matrix is
   generated from the filesystem or config and freshness-gated in CI (regenerate +
   `git diff --quiet`). Hand-groomed indexes decay to lies. *Origin: a documentation map whose
   every count was wrong and which omitted the system's entire current command surface.*
3. **Two context layers, explicit everywhere.** Layer A = agentic development platform
   (this framework's scope: levers, hooks, coordination, TDD method, seat protocol).
   Layer B = project context (the consuming project's scope: domain skills, schema, product
   docs, deployment). Every file belongs to exactly one layer; forge markers and Copier
   update-hygiene (`_skip_if_exists` / `_exclude`) enforce the boundary. The two layers are
   separately planned, staffed, and paced — each with its own internal tier hierarchy.
4. **Progressive disclosure under a hard budget.** The entry contract (the AGENTS.md
   concatenation a session actually receives) stays ≤32KB worst-case — the Codex
   `project_doc_max_bytes` ceiling doubles as the health budget for every runtime. Everything
   deeper is routed by reference, not inlined.
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

A solo project consumes L1 only (`orchestration_tier: solo`). A fleet adds L2. Parallel
write-heavy work adds L3. Each tier is independently adoptable and independently testable.

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
  tier is layer-tagged (A or B). The worst-case concatenation per working directory is
  budget-checked in CI (law 4) — the ceiling applies to the *payload*, not the root file.
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

The development loop, end to end (mandatory stages bolded):
**scope** (design + SPEC) → **spec-audit** (fresh-context adversarial ×2 + cross-runtime
second opinion) → **RED** → **GREEN** → **review** (cross-review) → **integrate** →
**document** (doc delta or explicit no-doc-impact declaration, gated like tests) →
**capture** (durable parking of discoveries). Details: `DEV_LOOP.md`.

## 6. Seats, runtimes, and models (L2 — full specs: `SEAT_PROTOCOL.md`, `MODEL_MATRIX.md`)

A **seat** is `{letter, runtime: claude|codex, model, effort, workdir, session-handle}` —
a persistent, addressable, revivable terminal session. Seats coordinate through the hub and
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

## 8. Enforcement doctrine (L1)

- Gates read **machine-readable, schema-validated state** — never prose formats that drift
  silently. Absent-state semantics per law 1.
- The evidence ledger records what *ran* (build, tests, RED/GREEN phases) from inside the
  actual runners — an agent's claim that a test ran is not evidence. Overrides exist but are
  named, logged tokens, never silent bypasses.
- Every check is a file, independently testable against shipped fixtures; the hook test
  harness is part of the framework and runs in the framework's own CI *and* in generated
  projects.
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

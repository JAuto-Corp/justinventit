# justinventit — Revival Scoping Memo

**Authored:** 2026-07-01 (role P) · **For:** O · **Class:** research / decision-input, no repo restructuring
**Supersedes-as-repo-copy-of:** `~/.jauto-orchestration/framework-revival-scoping.md` (2026-06-15, 21KB) — that doc holds the full staleness audit; this memo consolidates it into the repo and **refreshes to current ground truth**, folds in issue #2824, and locks the M1 cut.

---

## 0. Ground-truth correction (read first)

The revival is **further along than the resume dispatch assumed.** The "~3.5-month-stale sketch, research phase only" framing is a pre-work snapshot. Actual timeline from git + hub:

- **2026-03-11** — initial scaffold (4 commits): Copier base, `template/` subdir, CLAUDE.md.jinja router, 5 orchestrator skills, hook pipeline, docs. This is the ~Feb-2026 JAuto captured as L1.
- **2026-06-15** — **scoping proposal written** (`framework-revival-scoping.md`) + **M0 built** (commit `2511c3f`): copier.yml questionnaire (project_type / orchestration_tier[default solo] / team_size / isolation_tier / db_adapter / external_pacemaker) + `_exclude`/`_skip_if_exists` update-hygiene; dev-log template + scripts (log.sh, devlog-view.sh, attention.sh); external pacemaker (pacemaker.sh, passive-watchdog→auto-resumer, dry-run-validated across 5 liveness states).
- **2026-06-16** — **M0 second-opinion hardened** (commit `25bcab5`): 2 opus reviewers fixed a P0 dev-log data-loss (`done` over-resolved sibling open actions), a P1 pacemaker wrong-pane injection (prefix-collision `a`→`ab`), and P2s.
- **~06-21 → 07-01** — cluster dark.

**Current state:** branch `feat/m0-revival`, M0 done + hardened, **NOT pushed / NOT merged** (origin has only `main`), **awaiting user review**. So: the staleness audit and REVIVE verdict already exist; M0 is already built. Only the newest sketch layer is stale, and it's ~2 weeks stale, not 3.5 months.

**Implication for this assignment:** the useful artifact is not re-deriving the scope — it's (a) this consolidation, (b) the delta since 06-15, (c) the M1 cut, (d) the #2824 open question, and (e) the decision surface in §6. No rebuild.

---

## 1. Inventory — sketch vs architecture-added-since

Verdict from the prior audit stands: **~35% KEEP as-is / ~30% UPDATE / ~35% ADD**, with ADD concentrated in the orchestration substrate (L2, ~100% new) and the dev-log (100% new — now built in M0).

What the sketch already has (KEEP/UPDATE):
- Copier base, `template/` subdir convention, forge-marker (`<!-- forge:start/end -->`) merge boundary, `_answers_file`/`_subdirectory` config.
- CLAUDE.md.jinja `<200`-line router (TDD-gate table, scope classification, work routing).
- 5 orchestrator skills (work, verify, capture, team-lead, patterns) — team-lead already carries the WAIT pattern, file-ownership manifest, model-selection tier table.
- Stop-check pipeline (session-start / pre-compact / stop runner) with 2 checks (TDD gate, type-check evidence) + 2 actions (friction, discovery extraction).
- Staged-adoption doc set (ARCHITECTURE 8-layer, ROADMAP M0–M3, GETTING_STARTED, CUSTOMIZATION, MIGRATION, SELF_IMPROVEMENT, DOGFOODING).
- **M0 additions (built):** orchestration_tier/isolation_tier/external_pacemaker questionnaire dials; dev-log (record-as-byproduct); external pacemaker (the PI-34 live-process/dead-loop SPOF fix).

What the current architecture added since March (the ADD/UPDATE bucket):
- The `~/.jauto-orchestration/` **hub** — boot-prompts per role, cadence files, STATE.md/LEDGER.md, stall-watchdog.sh (SMS liveness, ~Jun-11), `.watchdog-state/` dedup.
- The **mailbox substrate** — `.jauto-coordination/` JSONL append-only `from-X-to-Y.jsonl` channels + `msg.sh` (flock, cursors, kinds). Absent from the template entirely.
- **Role/naming scheme** A/D/I/O/P (+ E/F, invoicing) and `boot-role.sh`. New.
- **TDD-gate maturation** — `/verify` command family, `tds-author` agent, SCENARIO_CONTRACTS pattern, `tds-evidence.json`, branch-DB-per-PR (Epic #1580). The sketch's TDD gate is the ~Feb shape.
- **`heartbeat.sh` Stop hook** (hub, user-level) — appends turn-end liveness regardless of whether the agent reached its own cadence write. **This is the exact producer the M0 review flagged as missing** (pacemaker READS cadence/heartbeat, nothing in-template WROTE them). The port target for M1 now has a proven reference.

---

## 2. Ports cleanly vs needs redesign (3-layer lens)

The co-designed target (per memory + roundtable) is **3 layers, not core-vs-tier**:

- **L1 — Portable core** (every project, agent-count-agnostic): CLAUDE.md routing, skills, ATDD/TDD gate, hooks, state-chain, TDS, **and the dev-log** (thread organization — durable nouns, useful even at cluster-size-1). **Ports cleanly.** Mostly KEEP/UPDATE; dev-log built in M0. The one currency fix: refresh the TDD-gate shape to the matured `/verify` + SCENARIO_CONTRACTS form.
- **L2 — Orchestration tier** (scales 1→N): mailbox / roles / cadence / wake-loop / dispatch — the **coordination = transport+liveness** verbs, only meaningful at >1. **Needs design-forward add**, ~100% new. Gated behind `orchestration_tier: cluster` (default solo = no-op shim, already in copier.yml). Open: agentic sizing policy vs a static knob.
- **L3 — Infra/isolation tier**: worktrees + DB branches. Key principle: isolation scales with **parallel-WRITE streams**, not total agents (O + read-only roles share main checkout; only parallel-mutating roles need worktree+branch-DB). **Needs a DB-isolation adapter** (`db_adapter`: supabase-branch / pg-schema / compose-per-wt / none). Sketch had only `use_worktrees: bool` → redesign into the `isolation_tier` dial (M0 added the dial; adapters are M3).

**Nothing in the sketch's architecture is contradicted by the target** — the adds slot in. That is why this is REVIVE-not-rebuild.

---

## 3. Is `copier update` still viable as the cross-maintenance mechanism?

**Yes — it remains the right answer to the user's core ask** ("one unified place that designs how we work, with easy cross-maintainability + updating"). `copier copy` scaffolds; `copier update` pulls framework improvements back into every generated project via three-way merge against `.copier-answers.yml`. Conditions for it to hold, all tractable:

- **Forge markers** (`<!-- forge:start/end -->`) must bound framework-owned regions in generated files so user edits outside them survive update — present in CLAUDE.md.jinja; needs the M1 validation test (ROADMAP M1 "forge markers validated").
- **State-file update-hygiene** — `_skip_if_exists` (WORKING.md, devlog, pacemaker runtime state) + `_exclude` (env, generated types) — **built + hardened in M0**. This is what stops `update` from clobbering live project state.
- **Three-way merge regression test** — modify template → `copier update` a project → verify no state loss. Listed in M1 ("copier update test"). Not yet run; it's the gate that certifies the mechanism.

Risk if skipped: silent state clobber on update. Mitigation is already scoped in M1, so viability is a "prove it with the dogfood test," not an architectural doubt.

---

## 4. Right-sized M1 cut — "Dogfood-Ready"

M1's contract (ROADMAP): *scaffold a real project and run a full ATDD cycle; first external test = re-scaffold customer-portal with justinventit and validate nothing breaks.* Right-sized cut, ordered by load-bearing-first:

1. **Heartbeat-writer Stop hook** (the review-surfaced gap) — port the hub's `heartbeat.sh` pattern into `template/.claude/hooks/stop/` so generated cluster projects actually *produce* the liveness signal the pacemaker consumes. Without this the L2 liveness contract has a consumer and no producer. **Item 0.**
2. **Complete the enforcement hooks** — stop-check 03 (scenario-execution evidence) + 04 (RED-before-GREEN) + a SCHEMA-GATE / equip-delta check, matching the matured customer-portal gate. Plus the **hook test harness** (mock transcript + state → run check → assert) so checks are individually testable.
3. **Skill chain-shape** — flesh the orchestrator sub-skills that the dogfood cycle exercises (work: start/continue/done/epic-plan/sprint; verify: complete/sprint). Defer the long tail.
4. **Stack-aware minimum** — `.gitignore.jinja` + `.gitattributes.jinja` (state-file merge strategy) for the customer-portal stack (nextjs/supabase) only. Other stacks are M2/M3; don't build the matrix now.
5. **TDS contract** — epic folder structure template (SPEC/SCENARIOS/PROGRESS) + Gherkin example, enough to run one ATDD cycle.
6. **Dogfood gate** — generate the scaffold for customer-portal's answers, diff against its actual `.claude/`, list gaps, backport, run one ATDD cycle. This is the M1 exit test and it *is* the validation the user wants.

Explicitly **out of M1** (defer): full stack matrix, brownfield onboarding automation (M2), DB-isolation adapters beyond the dial (M3), community polish (M3). Keeping M1 to "dogfood against customer-portal" is the right-sizing.

---

## 5. Issue #2824 — dynamic AI model selection (folded-in open question)

**Grounding (C, 07-01):** refs are correct (CLAUDE.md §Agent Deployment; team-lead skill consumes a model-selection table). Live cross-provider routing via benchmark APIs is **INFEASIBLE on an Anthropic-only Claude Code stack** — there is no runtime provider-swap surface. C classified it Investigation / outside the TDD gate / not a portal build → fold here or park.

**Reframe for the framework (open question, not a build item):** the *intent* — "use the right model tier for each role/task" — is already served statically and portably by the **model-selection tier table in the team-lead skill** (opus for judgment/review/planning; sonnet for context-gathering/structured authoring; haiku for mechanical). That convention is the portable, provider-agnostic form of #2824 and it ships in L1.

The *dynamic/benchmark-driven* form is speculative and op-complexity-heavy for the quality delta. Park the mechanism; keep two threads open for a future milestone (M3 "guardrail model tier" already gestures at this):
- A **guardrail/screening tier** (cheap-model pre-screen via prompt hooks) — already an M3 ROADMAP line; that's the realistic near-term expression.
- If Claude Code ever exposes runtime model routing, revisit auto-selection by task-shape. Until then: **static convention, documented, not dynamic.**

Recommendation: record #2824 as an M3-adjacent research note in the framework, not an M1 build. No portal work.

---

## 6. Decision surface (for O → user where product-facing)

1. **M0 branch disposition** — `feat/m0-revival` (built + hardened) is unpushed/unmerged, awaiting user review. Push + open a self-PR for review, or hold? (Repo has no CI yet; merge is O-ack-gated per side-project process.) *Recommend: push + PR so M0 is reviewable and durable; it's already second-opinion-hardened.*
2. **Proceed to M1?** — the cut in §4 is idle-bandwidth-sized and dogfood-anchored. Green-light M1 item 0 (heartbeat-writer) as the first build, or keep research-only?
3. **Carried-open from the 06-15 scoping** (product-ish, route user-ward): (a) sizing-policy-vs-knob for L2 (agentic auto-scaling vs a static `team_size`); (b) default isolation tier; (c) the log/coordination cut boundary (cadence is dual-use — dev-log noun vs coordination verb).

No action taken beyond this memo. Health U-20 HOLD respected. Awaiting O.

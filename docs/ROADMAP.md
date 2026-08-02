# Roadmap

> Single source of truth for justinventit development planning.

## Milestones

### M0: Foundation — done
The initial scaffold — enough structure to demonstrate the architecture and start dogfooding.

### M1: Dogfood-Ready (current)
Complete enough to scaffold a real project and run a full ATDD cycle. First external test: re-scaffold customer-portal with justinventit and validate nothing breaks. The dogfood gate passed (`docs/DOGFOOD_M1.md` §7); the templates/state/copier-robustness items below are still open.

### M2: Brownfield-Ready
Complete enough for the staged bootstrap path. Someone can `copier copy` into an existing codebase and get value from session one.

### M3: Community-Ready
Documentation, examples, and polish for public use. First public announcement.

## Conformance wave — live host before portable generation

The conformance wave sits between the normative L2 specs and template generation. It makes a
bounded surface true on a live consumer, records the observed guarantees and gaps, then ports
only that exercised contract and its shared tests. A live-host candidate is evidence for the
portable source; it is not itself a template deliverable.

### C0: durable async completion — host core accepted, integration and producer pending

`complete` is the first named conformance/transport unit because supervised fan-out cannot
become durable asynchronous work until a returning orchestrator can receive one structured,
dispatch-correlated terminal outcome without reconstructing mailbox prose.

- **Host core built and accepted, not integrated:** JAuto draft PR #3446 contains the narrow
  JSONL core at exact head `973e19e4a43cfc868a8a2d436652d0a7ae078310`. Its base is
  `0992dce5922975febd3b01581c9be5b57939127c`; initial RED is `7b6cff3e`; a fresh review
  found a same-id retry truthfulness defect; correction RED `6990fffd` isolated it; final
  GREEN is 87/87. Fresh exact-head primary and adversarial review-of-review each returned
  zero-finding `PASS_WITH_NOTES`. The PR remains draft/unmerged; integration is an I-owned,
  user-called window.
- **What the accepted core exercises:** strict `hub complete` CLI validation; one JSONL
  authority append; canonical multi-recipient projections; fresh-process authority-derived
  append-only repair; identical replay and conflicting-content refusal; truthful
  recorded-versus-not-recorded failure diagnostics; and typed, side-effect-free completion
  recognition. Isolated dogfood `01KYZRS56B2E543H38JZ0V0FEQ` proved one authority, one exact
  projection, replay dedup and consumer readback without claiming live-registry acknowledgement.
- **What the core does not unlock by itself:** no automatic producer emits the event, no
  returning orchestrator drains a folded completion queue, and no process/runtime supervisor
  has been accepted. Therefore fire-and-forget seats and unsupervised scale-out are still
  pending capabilities. The stopped overcoupled attempt is preserved at closed PR #3444 and
  must not be revived as an implicit next revision.
- **Next host slices, separately bounded:** integrate #3446 through its governed window;
  design a producer adapter from actual runtime terminal evidence; characterize or explicitly
  defer process supervision instead of coupling it to transport; then prove a returning
  orchestrator can consume completion without reconstructing prose. Each slice names its own
  executable falsifier before implementation.
- **What remains portable work:** normative folded completion state, durable consumer
  cursors/effect acknowledgement, cross-backend conformance, doorbell coalescing, template
  emission and a scratch-consumer proof. The JAuto JSONL core must not be described as
  satisfying those unbuilt guarantees.
- **Dependents:** context-delivery and local-substrate work may use the accepted core manually
  in isolated feature environments after their own gates. Safe async seat scale-out depends
  on the producer/consumer slices above, and fleet-wide use depends on merge/deployment. No
  dependent may treat an unmerged CLI as deployment.

Program closure therefore has at least three separately visible implementation steps, and
**each** traverses its applicable SPEC → audit → RED → GREEN → independent review gate before
it counts: (1) integrate the accepted JAuto host core through its governed window; (2) prove
host producer/consumer behavior against real runtime evidence, with process supervision split
where reality requires it; (3) derive the backend-neutral contract/tests from exercised host
behavior and pass them in a generated scratch consumer. Do not collapse those steps into one
checkbox or let integration substitute for review evidence.

**Review economy for this wave:** hub rule `01KYZNHFAMPWM8Y6HQRS0DW6K2` tiers review by
authority. Governing contracts/gates receive primary plus review-of-review when they claim
authority. Working notes and draft deltas receive at most one pass until promotion. Every unit
declares a correction budget; exhausting it leaves a visible provisional artifact with
residuals rather than an unbounded revision chain. Prefer runnable artifacts because execution
provides the falsifier that prose review cannot.

---

## M0: Foundation — DONE

- [x] Copier template structure with questionnaire
- [x] CLAUDE.md.jinja template (<200 lines, TDD gate, routing)
- [x] 5 orchestrator skills (work, verify, capture, team-lead, patterns)
- [x] Hook pipeline architecture (session-start, pre-compact, stop runner)
- [x] 2 stop checks (TDD gate, type-check evidence)
- [x] 2 stop actions (friction extraction, discovery extraction)
- [x] State file templates (WORKING.md, CURRENT_WORK.md, PLAYBOOK.md)
- [x] Framework docs (Architecture, Getting Started, Customization, Migration, Self-Improvement)
- [x] MIT license, README

## M1: Dogfood-Ready

> **Checkbox provenance (2026-07-27).** Every box below was flipped against a named artifact
> in the tree or a named section of `docs/DOGFOOD_M1.md` — the evidence is on the line. Items
> with no such artifact are left **unchecked** even where the milestone reads as "done";
> `docs/DOGFOOD_M1.md` §7 verdicts the *dogfood gate*, not all 26 items, so M1 is
> **substantially but not fully complete**. Do not flip a box here without naming what makes
> it true.

### Skills — Complete the orchestrator set
- [x] `e2e` skill — testing modes (conductor, direct, SQL), browser coordination · `skills/orchestrators/e2e/{SKILL,modes}.md`
- [x] `workflow` skill — meta-skill for editing the system itself (skills, hooks, rules, CLAUDE.md) · `skills/orchestrators/workflow/` (SKILL + skill/command/hook/rule/claude-md/validate)
- [x] `work` sub-skills — start.md, continue.md, pause.md, handoff.md, done.md, epic-plan.md, sprint.md · all 7 present
- [x] `verify` sub-skills — complete.md, phase.md, sprint.md, file.md, feature.md, audit.md, recent.md · all 7 present
- [x] `capture` sub-skills — block.md, audit.md, findings.md, triage.md, epic.md · all 5 present

### Hooks — Complete the pipeline
- [x] Stop check: scenario execution evidence (03) · `hooks/stop/checks/03-scenario-evidence.sh`
- [x] Stop check: TDD cycle validation — RED before GREEN (04) · `hooks/stop/checks/04-tdd-cycle.sh`
- [x] Stop check: PROGRESS.md evidence — commits match checked items (05) · `hooks/stop/checks/05-progress-evidence.sh`
- [x] Stop action: landmark checkoff — commit trailers → PROGRESS.md auto-update · `hooks/stop/actions/landmark-checkoff.sh`
- [x] Guard: write isolation (worktree boundaries) · `hooks/guards/write-isolation.sh`
- [x] Guard: migration safety (DB-system-aware, Jinja2 templated) · `hooks/guards/migration-safety.sh.jinja`
- [x] Hook test harness — mock transcript + state → run check → assert result · `hooks/tests/{harness,run-all}.sh` + 7 suites; green in a generated project per DOGFOOD_M1 §3(e)

### Templates — Stack-aware generation
- [ ] `.gitattributes.jinja` — merge strategies for state files, auto-generated files — **not present**
- [ ] `.gitignore.jinja` — stack-appropriate ignores — **not present**
- [ ] Domain skill stubs per stack (nextjs, rails, django, fastapi, go) — **not present**; `skills/domain/` is user-created, not generated
- [ ] Worktree scripts (conditional on `use_worktrees` answer) — **not present**, and `copier.yml` has no `use_worktrees` question, so this item needs restating before it can be built
- [ ] CI workflow templates (GitHub Actions, per stack) — **not present**

### State — Full lifecycle support
- [ ] Epic folder structure template (INDEX, SPEC, SCENARIOS, PROGRESS per phase) — **not present**
- [ ] SPEC.md template with entry/exit landmarks — **not present**
- [ ] SCENARIOS.md template with Gherkin examples — **not present**
- [ ] PROGRESS.md template with checkbox protocol — **not present**

### Copier — Robustness
- [x] End-to-end test: `copier copy` with each stack → validate output · `scripts/ci/generate-matrix-check.sh` — 4 answer sets (go/nextjs/fastapi/rust) with coherence assertions (a)–(f)
- [ ] `copier update` test: modify template → update project → verify three-way merge — **no such test exists**
- [ ] Forge markers (`<!-- forge:start/end -->`) validated in CLAUDE.md output — markers are emitted (`template/CLAUDE.md.jinja:17`) but **nothing asserts them**; the validation is the deliverable, not the markers
- [ ] Empty directory handling (Git doesn't track empty dirs — use .gitkeep) — **no `.gitkeep` anywhere in `template/`**

### Dogfood — Validate against customer-portal
- [x] Generate justinventit scaffold for customer-portal's stack answers · DOGFOOD_M1 §1 (110 files, cp-matching answer set)
- [x] Diff generated output against customer-portal's actual `.claude/` structure · DOGFOOD_M1 §4
- [x] Identify gaps — what does customer-portal have that justinventit doesn't generate? · DOGFOOD_M1 §4 (portable-gap vs. domain split)
- [x] Backport missing patterns into the template · DOGFOOD_M1 §5
- [x] Run one full ATDD cycle using the generated scaffold · DOGFOOD_M1 §6 (block-then-pass on checks 03/04/05, harness 7/7)

## M2: Brownfield-Ready

### Onboarding automation
- [ ] `copier copy` preserves existing CLAUDE.md content outside forge markers
- [ ] Existing skills auto-detected and moved to `domain/` directory
- [ ] Existing hooks coexistence guide + conflict detection
- [ ] First-session explorer pattern — agent fills codebase map on initial run

### Friction loop — Production-grade
- [ ] Friction log format standardized (YAML? Markdown? JSON?)
- [ ] Classification guide embedded in friction-extraction action
- [ ] `gh issue create` automation for FRAMEWORK-classified friction
- [ ] Skill drift detection — coverage metadata in SKILL.md, audit command

### Documentation
- [ ] Video/walkthrough: "Adding justinventit to an existing project"
- [ ] Example project: minimal Next.js app with full justinventit scaffold
- [ ] Example project: minimal Python/FastAPI app with justinventit scaffold
- [ ] Troubleshooting guide: common hook issues, Copier conflicts

### Testing
- [ ] Hook test suite (bash unit tests with mock transcripts)
- [ ] Copier generation test matrix (all stack × database × testing combinations)
- [ ] `copier update` regression tests

## M3: Community-Ready

### Polish
- [ ] README with demo GIF/video
- [ ] Contributing guide
- [ ] Changelog
- [ ] Semantic versioning (Copier uses git tags for versions)
- [ ] GitHub releases with migration notes per version

### Ecosystem
- [ ] Community skill packs (submit your domain skills)
- [ ] Community hook checks (submit your stop checks)
- [ ] Cross-IDE guidance (Cursor rules, Windsurf, Codex equivalents)
- [ ] Integration with awesome-claude-code listing

### Advanced features
- [ ] Guardrail model tier (Haiku/Flash screening via prompt hooks)
- [ ] Plan approval gate for team-lead (read-only until approved)
- [ ] Adversarial debugging mode (competing hypothesis agents)
- [ ] Agentic Plan Caching (reuse plan templates across similar tasks)
- [ ] Automated friction clustering (Factory.ai Signals pattern)

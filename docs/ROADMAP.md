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

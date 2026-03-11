# Roadmap

> Single source of truth for justinventit development planning.

## Milestones

### M0: Foundation (current)
The initial scaffold — enough structure to demonstrate the architecture and start dogfooding.

### M1: Dogfood-Ready
Complete enough to scaffold a real project and run a full ATDD cycle. First external test: re-scaffold customer-portal with justinventit and validate nothing breaks.

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

### Skills — Complete the orchestrator set
- [ ] `e2e` skill — testing modes (conductor, direct, SQL), browser coordination
- [ ] `workflow` skill — meta-skill for editing the system itself (skills, hooks, rules, CLAUDE.md)
- [ ] `work` sub-skills — start.md, continue.md, pause.md, handoff.md, done.md, epic-plan.md, sprint.md
- [ ] `verify` sub-skills — complete.md, phase.md, sprint.md, file.md, feature.md, audit.md, recent.md
- [ ] `capture` sub-skills — block.md, audit.md, findings.md, triage.md, epic.md

### Hooks — Complete the pipeline
- [ ] Stop check: scenario execution evidence (03)
- [ ] Stop check: TDD cycle validation — RED before GREEN (04)
- [ ] Stop check: PROGRESS.md evidence — commits match checked items (05)
- [ ] Stop action: landmark checkoff — commit trailers → PROGRESS.md auto-update
- [ ] Guard: write isolation (worktree boundaries)
- [ ] Guard: migration safety (DB-system-aware, Jinja2 templated)
- [ ] Hook test harness — mock transcript + state → run check → assert result

### Templates — Stack-aware generation
- [ ] `.gitattributes.jinja` — merge strategies for state files, auto-generated files
- [ ] `.gitignore.jinja` — stack-appropriate ignores
- [ ] Domain skill stubs per stack (nextjs, rails, django, fastapi, go)
- [ ] Worktree scripts (conditional on `use_worktrees` answer)
- [ ] CI workflow templates (GitHub Actions, per stack)

### State — Full lifecycle support
- [ ] Epic folder structure template (INDEX, SPEC, SCENARIOS, PROGRESS per phase)
- [ ] SPEC.md template with entry/exit landmarks
- [ ] SCENARIOS.md template with Gherkin examples
- [ ] PROGRESS.md template with checkbox protocol

### Copier — Robustness
- [ ] End-to-end test: `copier copy` with each stack → validate output
- [ ] `copier update` test: modify template → update project → verify three-way merge
- [ ] Forge markers (`<!-- forge:start/end -->`) validated in CLAUDE.md output
- [ ] Empty directory handling (Git doesn't track empty dirs — use .gitkeep)

### Dogfood — Validate against customer-portal
- [ ] Generate justinventit scaffold for customer-portal's stack answers
- [ ] Diff generated output against customer-portal's actual `.claude/` structure
- [ ] Identify gaps — what does customer-portal have that justinventit doesn't generate?
- [ ] Backport missing patterns into the template
- [ ] Run one full ATDD cycle using the generated scaffold

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

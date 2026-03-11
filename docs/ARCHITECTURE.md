# Architecture

> Why each layer exists, and how they connect.

## Design Principles

1. **Route, don't dump** — CLAUDE.md is a routing table, not a manual. Under 200 lines.
2. **Load on demand** — Skills, rules, and docs are lazy-loaded. Only what's needed enters context.
3. **Enforce, don't suggest** — Hooks turn conventions into gates. Without enforcement, conventions drift.
4. **Tests define done** — The agent doesn't decide when work is complete. The ATDD cycle does.
5. **The system improves itself** — Friction signals feed back into skills, hooks, and rules.

## The 8 Layers

### Layer 0: CLAUDE.md (Entry Point + Router)

The single file every Claude Code session reads first. It answers three questions:
1. **Where am I?** — Codebase map (directories, core flow, schema source of truth)
2. **What should I do first?** — Before-working checklist, routes to PLAYBOOK.md
3. **How do I do it?** — Routing tables mapping needs → skills, tools, documents

**Hard constraint**: Under 200 lines. Anthropic's research shows adherence drops significantly past this threshold. Domain-specific knowledge belongs in path-scoped rules (Layer 1) or skills (Layer 1), not CLAUDE.md.

### Layer 1: Skills (Lazy-Loaded Knowledge)

Two categories:

**Orchestrator skills** control workflow:
- `work` — lifecycle state machine (start → continue → pause → handoff → done)
- `verify` — verification gates (phase, sprint, epic, file, feature, audit)
- `capture` — issue parking without context-switching
- `team-lead` — agent team coordination (WAIT pattern, file ownership)
- `e2e` — test execution modes (conductor, direct, SQL)
- `patterns` — shared sub-patterns loaded by other skills
- `workflow` — meta-skill for editing the system itself

**Domain skills** encode best practices:
- Invoked before writing 20+ lines of code
- Scoped to technology (API patterns, frontend aesthetics, DB relationships, etc.)
- Project-specific — these are stubs in the framework, filled in per project

Skills use SKILL.md with YAML frontmatter (`name`, `description`). Only frontmatter loads at session start. Full content loads on invocation via the Skill tool.

### Layer 2: State Machine (Work Lifecycle)

State file chain (read in order each session):

```
PLAYBOOK.md        → Which lifecycle phase? (planning, execution, validation)
CURRENT_WORK.md    → What epic/sprint/phase is active?
WORKING.md         → What's the immediate next action? (append-only observation blocks)
SPEC.md            → What are the acceptance criteria for this phase?
SCENARIOS.md       → What are the Gherkin scenarios? (ENTRY GATE)
PROGRESS.md        → What's been checked off?
```

The `work` skill manages transitions between states. Handoffs write goal-focused context to WORKING.md so the next agent (or session) can reconstruct intent.

**WORKING.md format** — append-only dated observation blocks:
```markdown
## 2026-03-11T14:30Z
Phase: epic-N/sprint-1/phase-1
Completed: PROGRESS #1-3
Next: PROGRESS #4
Blockers: none
```

This format hits Anthropic's prefix cache (stable prefix = cached) for significant cost/latency reduction.

### Layer 3: ATDD Gate (Quality Control)

The sequence: **Plan → RED → GREEN → VALIDATE**

```
SPEC.md (what to build, exit landmarks)
  → SCENARIOS.md (Gherkin — MUST exist before code)
    → Stories (.stories.ts — given/when/then, seeds)
      → Scenarios (.scenario.ts — executable config)
        → RED (scenario fails — feature absent)
          → Implementation
            → GREEN (scenario passes)
              → /verify:complete (exit gate)
```

**Scope classification is objective** — the agent doesn't self-classify:

| Trigger | Scope | TDD Required? |
|-|-|-|
| New DB tables/columns | Standard+ | Yes |
| New API routes | Standard+ | Yes |
| New UI pages/major components | Standard+ | Yes |
| 4+ files modified | Standard+ | Yes |
| Single-file bug fix, no new surface area | Quick | No |

Gates are enforced at multiple system boundaries:
- `/work:start` and `/work:continue` block without SCENARIOS.md
- `/verify:complete` hard-blocks on missing scenarios
- Stop hook blocks session exit if scenarios weren't executed

### Layer 4: Hooks (Invisible Enforcement)

Hook pipeline architecture:

```
.claude/hooks/
  session-start.sh       ← Session brief (phase, next item, skill routing)
  pre-compact.sh         ← State preservation before context compression
  stop/
    checks/              ← Individual check functions
      01-tdd-gate.sh     ← Scenarios exist for standard+ scope
      02-evidence.sh     ← Commits match checked PROGRESS items
      03-type-check.sh   ← Build validation ran
      04-scenarios.sh    ← Scenarios were executed
      05-tdd-cycle.sh    ← RED recorded before GREEN
    actions/             ← Post-check actions
      discovery.sh       ← [DISCOVERY:*] → GitHub issues
      friction.sh        ← [FRICTION:*] → friction log
      landmarks.sh       ← Commit trailers → PROGRESS checkoff
    runner.sh            ← Aggregates check results
  guards/
    write-guard.sh       ← Worktree isolation
    migration-guard.sh   ← DB migration safety
  lib/
    utils.sh             ← Shared utilities
    evidence.sh          ← Build evidence tracking
```

Each check is independently testable: `bash checks/01-tdd-gate.sh` exits 0 (pass) or 1 (block with message). New checks are added by dropping a file. Project-specific checks go in a separate directory from framework checks.

**Relaxation mode**: `JUSTINVENTIT_HOOK_MODE=relaxed` downgrades blocks to warnings for prototype spikes.

### Layer 5: Agent Teams (Coordination)

**The WAIT pattern**: After spawning teammates and assigning tasks, the lead must stop making tool calls. Messages only arrive when the lead is idle. Act → stop → receive → act → stop.

**File ownership**: Absolute — no two teammates edit the same file. The lead writes a team ownership manifest before spawning. Each teammate's prompt includes their owned files and off-limits zones.

**Recovery**: Git commits are the durable checkpoint. PROGRESS.md is the phase checkpoint. After context compression, rebuild from `git log` + PROGRESS.md.

### Layer 6: CI/CD Pipeline

Required status checks before merge:
- Type checking (language-appropriate)
- Build validation
- Test suite
- Migration validation (if applicable)

Merge path: `feature/*` → `staging` → `main`. Agents commit freely; humans push.

### Layer 7: Memory (Three-Tier Persistence)

| Tier | Scope | Location | Survives |
|-|-|-|-|
| Session | Current session | `.claude/memory/` | Until session ends |
| Cross-session | All sessions for this project | `~/.claude/projects/.../memory/` | Forever |
| Durable | All time | Git-tracked state files (`context/`, `docs/`) | Forever |

MEMORY.md (cross-session, auto-loaded) stays under 200 lines. Topic files hold details, referenced from MEMORY.md.

## How Layers Connect

A single development cycle traced through every layer:

1. **Session starts** → Hook (L4) injects session brief from state files (L2)
2. **Agent reads CLAUDE.md** (L0) → routes to PLAYBOOK → identifies execution phase
3. **`/work:continue`** (L1 skill) → reads state chain (L2) → checks SCENARIOS gate (L3)
4. **Implementation** → domain skill invoked (L1) → tool guards enforce isolation (L4)
5. **Each PROGRESS item**: implement → check off → commit (L2 state + L6 git)
6. **E2E validation** → test runner seeds data → agent executes (L3)
7. **`/verify:complete`** (L1 skill) → exit gate (L3 + L4 + L6)
8. **Session ends** → stop hook validates evidence, extracts signals (L4) → memory updated (L7)

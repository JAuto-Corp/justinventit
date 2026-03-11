# justinventit

> Whatever problem needs a solution, just invent it.

AI-native development framework — the engine that builds the engine. Portable ATDD workflows, skills, hooks, and state management for Claude Code projects.

## What This Is

A Copier template that scaffolds the full AI-native development infrastructure for any project: CLAUDE.md routing, lazy-loaded skills, ATDD enforcement, lifecycle hooks, state management, and agent team coordination.

Built by extracting what works from 18 months of AI-paired development on a production SaaS platform — validated against academic research, Anthropic's official guidance, and community best practices.

## Philosophy

1. **Tests define done, not the agent.** ATDD gates prevent "2000 lines that don't work."
2. **Context is finite. Route, don't dump.** Skills load on demand. Rules scope to file paths.
3. **Conventions without enforcement drift.** Hooks turn "you should" into "you must."
4. **The system improves itself.** Friction signals flow from projects back to the framework.

## Architecture

```
CLAUDE.md (router, <200 lines)
  → Skills (lazy-loaded domain + orchestrator knowledge)
    → State Chain (PLAYBOOK → CURRENT_WORK → WORKING → SPEC → SCENARIOS → PROGRESS)
      → ATDD Cycle (SPEC → SCENARIOS → RED → GREEN → VERIFY)
        → Hooks (session-start, pre-compact, stop pipeline, tool guards)
          → Agent Teams (WAIT pattern, file ownership, worktree isolation)
```

### The 8 Layers

| Layer | Purpose | Key Files |
|-|-|-|
| 0. Entry Point | Route the agent to the right knowledge | `CLAUDE.md` |
| 1. Skills | Lazy-loaded domain + orchestrator expertise | `.claude/skills/` |
| 2. State Machine | Work lifecycle (start → continue → handoff → done) | `context/WORKING.md`, `docs/CURRENT_WORK.md` |
| 3. ATDD Gate | Acceptance criteria before code, tests define done | `SCENARIOS.md`, `PROGRESS.md` |
| 4. Hooks | Invisible enforcement of conventions | `.claude/hooks/` |
| 5. Coordination | Agent teams with file ownership + worktree isolation | `.claude/skills/team-lead/` |
| 6. CI/CD | Required status checks, merge path gates | `.github/workflows/` |
| 7. Memory | Three-tier persistence (session → cross-session → durable) | `.claude/memory/`, `context/` |

## Quick Start

```bash
# Prerequisites: Claude Code, Copier (pip install copier)

# Scaffold a new project
copier copy gh:JAuto-Corp/justinventit my-project

# Or add to an existing project
cd existing-project
copier copy gh:JAuto-Corp/justinventit .

# Update when framework improves
copier update
```

The questionnaire asks about your stack, database, testing approach, and team size — then generates the appropriate CLAUDE.md, skills, hooks, and state files.

## Staged Adoption (Brownfield)

You don't need the full system on day one:

| Stage | What | Time |
|-|-|-|
| 0 | `copier copy` — scaffolds structure from questionnaire | 5 min |
| 1 | First session: agent explores, fills codebase map, generates first domain rule | 1 session |
| 2 | First task: SPEC + SCENARIOS for one feature, minimal TDD cycle | 1 task |
| 3 | Domain skills emerge from repeated friction | ~1 week |
| 4 | Full system: teams, worktrees, comprehensive hooks | ~2 weeks |

Each stage is independently useful. No stage requires understanding the full system.

## Self-Improvement

The framework includes a first-class feedback loop:

```
Agent encounters friction
  → Emits [FRICTION:SKILL|HOOK|WORKFLOW|CONTEXT] signal
    → Stop hook extracts → context/FRICTION_LOG.md
      → Classifies: PROJECT (update local) or FRAMEWORK (upstream PR)
```

When you find improvements that are portable across projects, contribute them back:
- Project-specific → update your local skills/hooks/rules
- Framework-portable → PR to this repo → all projects benefit via `copier update`

## Research Validation

Key design decisions validated by independent research:

- **ATDD gate**: Test-first improves LLM code quality by 45.97% (ICSE 2025), independently converged on by community (swingerman/atdd, Tweag TDD handbook, Paul Duvall's ATDD methodology)
- **Scope classification**: AI reliability degrades non-linearly with complexity (GAIA benchmark, Anthropic autonomy measurement)
- **File ownership > locking**: Universal consensus across all multi-agent systems
- **Lazy-loaded skills**: Matches Anthropic's "specific, concise instructions" guidance and Cursor's MDC rule types
- **Append-only state**: Observational memory pattern hits prefix cache (90% cost reduction)

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) — Installation, first project, first task
- [Architecture](docs/ARCHITECTURE.md) — Why each layer exists
- [Customization](docs/CUSTOMIZATION.md) — How to extend without breaking sync
- [Self-Improvement](docs/SELF_IMPROVEMENT.md) — Friction journal and upstream contribution
- [Brownfield Migration](docs/MIGRATION.md) — Bringing an existing project into the framework

## Origin

Extracted from [JAuto-Corp/customer-portal](https://github.com/JAuto-Corp/customer-portal) — 18 months of AI-paired development, 225+ issues, 17 merged PRs in a single weekend at peak velocity. The framework is what made that possible.

## License

MIT

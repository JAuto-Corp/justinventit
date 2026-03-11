# Getting Started

## Prerequisites

- [Claude Code](https://claude.ai/download) installed and configured
- [Copier](https://copier.readthedocs.io/) installed (`pip install copier` or `pipx install copier`)
- Git repository (existing or new)

## New Project

```bash
# Create project directory
mkdir my-project && cd my-project
git init

# Scaffold justinventit
copier copy gh:JAuto-Corp/justinventit .

# Follow the questionnaire:
#   - Project name
#   - Stack (nextjs, rails, python, go, etc.)
#   - Database (supabase, postgres, none)
#   - Testing approach (playwright, cypress, none)
#   - Team size (solo, small, large)
```

This generates:
- `CLAUDE.md` — routing table tailored to your stack
- `.claude/skills/` — orchestrator skills + domain skill stubs
- `.claude/hooks/` — session-start, stop pipeline, tool guards
- `context/WORKING.md` — initial state file
- `docs/PLAYBOOK.md` — lifecycle routing

## Existing Project (Brownfield)

```bash
cd existing-project

# Scaffold into existing repo (Copier preserves existing files)
copier copy gh:JAuto-Corp/justinventit .
```

Then follow the staged adoption path:

### Stage 0: Scaffold (5 minutes)
The questionnaire generates structure. Review `CLAUDE.md` — it will have placeholders for your codebase map. Fill them in or let Claude do it in your first session.

### Stage 1: Orient (First Session)
Start Claude Code. It reads CLAUDE.md, sees the codebase map placeholders, and explores your project. At the end of the session, your CLAUDE.md has a real codebase map and initial routing.

### Stage 2: First ATDD Cycle (First Real Task)
Pick a feature. Create SPEC.md + SCENARIOS.md. Follow the RED → GREEN → VERIFY cycle. This is where the system proves itself — you'll see the difference between "AI wrote code" and "AI wrote code that passes acceptance criteria."

### Stage 3: Domain Skills (First Week)
As you work, friction reveals where domain knowledge is needed. The agent proposes new skills via `[FRICTION:SKILL]` signals. Create them — these are your project's institutional knowledge.

### Stage 4: Full System (First Two Weeks)
Enable team coordination if working with multiple agents. Add worktree isolation if running parallel epics. Customize stop hook checks for your CI/CD gates.

## Updating the Framework

When justinventit improves (new skills, better hooks, refined templates):

```bash
copier update
```

Copier runs a three-way merge:
- Framework changes apply cleanly to files you haven't customized
- Files you've customized get a merge — your changes are preserved
- Conflicts (rare) are flagged for manual resolution

## First Session Checklist

After scaffolding, your first Claude Code session should:

1. Read CLAUDE.md (automatic)
2. Fill in codebase map placeholders
3. Review generated hooks — disable any that don't apply to your stack
4. Try one ATDD cycle on a small feature
5. Check `context/FRICTION_LOG.md` at the end — did the system cause any friction?

## What You Get

| Component | Purpose | Customizable? |
|-|-|-|
| `CLAUDE.md` | Agent routing table | Yes — fill in project specifics |
| Orchestrator skills | Workflow control (work, verify, capture) | Extend, don't replace |
| Domain skill stubs | Best-practices for your stack | Fill in from experience |
| Session-start hook | Context injection at session start | Add project-specific context |
| Stop hook pipeline | Exit gate enforcement | Add project-specific checks |
| State files | Work lifecycle tracking | Format is framework; content is yours |
| Path-scoped rules | Domain rules loaded for matching files | Fully project-specific |

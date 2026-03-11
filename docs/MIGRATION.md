# Brownfield Migration

> Bringing an existing project into justinventit.

## Overview

Adding justinventit to an existing codebase is the hardest adoption path — but also the most valuable. The key insight: **don't try to build the full system on day one.** Follow the staged bootstrap.

## Before You Start

Understand what you have:
- **Existing CLAUDE.md?** Copier will merge, not overwrite. But review the merge.
- **Existing hooks?** Back them up. justinventit's hooks can coexist if they use different event matchers.
- **Existing skills?** Move to `.claude/skills/domain/` — framework won't touch that directory.
- **Existing CI/CD?** justinventit doesn't override CI. It provides templates you can adopt.

## Step-by-Step

### 1. Scaffold

```bash
cd your-project
copier copy gh:JAuto-Corp/justinventit .
```

Review every generated file before committing. Key files to check:
- `CLAUDE.md` — does the codebase map make sense?
- `.claude/hooks/session-start.sh` — does it conflict with existing hooks?
- `.claude/hooks/stop/` — are the checks appropriate for your project?

### 2. Integrate Existing Knowledge

If you have an existing CLAUDE.md, merge the best of both:
- Keep your codebase map and project-specific routing
- Adopt the framework's TDD gate and before-working checklist
- Move domain knowledge to path-scoped rules (`.claude/rules/`)

If you have existing skills:
```bash
mv .claude/skills/my-skill .claude/skills/domain/my-skill
```

### 3. Adapt Hooks

Review each framework hook against your project:

| Hook | Likely needs adaptation? |
|-|-|
| session-start.sh | Yes — add project-specific state file paths |
| pre-compact.sh | Usually works as-is |
| stop/checks/01-tdd-gate.sh | Maybe — adjust scope triggers for your project |
| stop/checks/03-type-check.sh | Yes — adjust the type-check command |
| guards/write-guard.sh | Only if using worktrees |
| guards/migration-guard.sh | Yes — adapt to your DB migration tool |

### 4. First ATDD Cycle

Pick a **small, well-understood feature**. Not the hardest thing on your backlog — something you could do in your sleep without AI. This proves the ATDD cycle works with your codebase before you depend on it for hard problems.

1. Write SPEC.md (acceptance criteria)
2. Write SCENARIOS.md (Gherkin)
3. Run the RED phase (scenario should fail)
4. Implement
5. Run the GREEN phase (scenario should pass)
6. Run `/verify:complete`

If any step feels wrong, emit a `[FRICTION:*]` signal and note what needs to change.

### 5. Iterate

After the first ATDD cycle:
- Check `context/FRICTION_LOG.md` — what caused friction?
- Update skills, hooks, or rules based on what you learned
- Classify improvements as PROJECT or FRAMEWORK
- Share FRAMEWORK improvements upstream

## Common Migration Issues

### "My project doesn't have tests"
Start with ATDD as documentation, not automation. Write SCENARIOS.md as Gherkin specifications. The scenarios describe expected behavior even if no test runner executes them. As you build test infrastructure, the scenarios become executable.

### "My CLAUDE.md is already 500 lines"
This is the most common brownfield problem. Strategy:
1. Move domain knowledge to `.claude/rules/` with path scoping
2. Move best practices to `.claude/skills/domain/`
3. Keep only the codebase map and routing table in CLAUDE.md
4. Target: under 200 lines

### "My hooks are complex and custom"
Keep your hooks. Add justinventit's hooks alongside them with different event matchers. Gradually migrate checks into the stop pipeline as you verify they work.

### "My team uses Cursor / Windsurf / other IDE"
justinventit is built for Claude Code but the concepts are portable:
- CLAUDE.md → `.cursorrules` or `.cursor/rules/`
- Skills → rule files with conditional loading
- State files → same pattern works everywhere
- Hooks → IDE-specific extension points

The ATDD cycle and state management work regardless of IDE.

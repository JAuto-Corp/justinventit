# Customization

> How to extend without breaking sync.

## The Merge Boundary

justinventit uses Copier's three-way merge for updates. Understanding the boundary between framework and project content is key to pain-free updates.

### Framework Content (updated by `copier update`)

Files between `<!-- forge:start -->` and `<!-- forge:end -->` markers in CLAUDE.md:

```markdown
<!-- forge:start — DO NOT EDIT between forge markers -->
## TDD Gate (Non-Negotiable)
... (framework content)
<!-- forge:end -->

## My Project Conventions
... (your content — never touched by copier update)
```

Orchestrator skills (`work`, `verify`, `capture`, `team-lead`, `patterns`, `workflow`, `e2e`) are framework-managed. Updates to these skills come from `copier update`.

Hook check scripts in `stop/checks/01-*` through `stop/checks/50-*` are framework-managed. Numbers 51+ are project-specific.

### Project Content (never touched by updates)

- Domain skills (`.claude/skills/domain/*`)
- Path-scoped rules (`.claude/rules/*`)
- Project-specific hook checks (`stop/checks/51-*` and above)
- State file contents (`context/WORKING.md`, `docs/CURRENT_WORK.md`)
- Project-specific scripts

## Adding Domain Skills

Create a new skill directory:

```
.claude/skills/domain/my-api-patterns/
  SKILL.md
```

With SKILL.md:
```yaml
---
name: my-api-patterns
description: API route patterns for this project's stack
covers:
  files: "src/api/**/*.ts"
  patterns: ["prisma", "zod"]
  conventions: ["validate-input", "return-typed-response"]
---

# My API Patterns

## Route Structure
...
```

The `covers` metadata enables drift detection — the framework's `/verify:skill-health` can compare your assertions against actual code.

## Adding Path-Scoped Rules

Create a rule file:

```
.claude/rules/api-routes.md
```

```yaml
---
paths: ["src/api/**/*.ts", "src/routes/**/*.ts"]
---

# API Route Rules

- Always validate input with zod schemas
- Return typed responses
- Log errors with full context
```

Rules only load when Claude works with matching files — no context wasted on irrelevant rules.

## Adding Stop Hook Checks

Create a numbered check script:

```bash
#!/bin/bash
# .claude/hooks/stop/checks/51-my-custom-check.sh
# Description: Ensure all API routes have input validation

# Source shared utilities
source "$(dirname "$0")/../../lib/utils.sh"

# Your check logic
# Exit 0 = pass, Exit 1 = block (prints message to stderr)

if some_condition_fails; then
  echo "BLOCK: API routes missing input validation" >&2
  exit 1
fi

exit 0
```

Framework checks use numbers 01-50. Project checks use 51+. This ensures framework updates don't conflict with your checks.

## Extending Orchestrator Skills

Don't edit orchestrator skills directly — they'll be overwritten by `copier update`. Instead:

1. **Add sub-files**: Orchestrator skills load sub-files from their directory. Add `my-extension.md` alongside `SKILL.md`.
2. **Create wrapper skills**: A project skill that loads the orchestrator skill and adds project context.
3. **Contribute upstream**: If the extension is framework-portable, PR it to justinventit.

## Overriding Framework Behavior

If a framework convention doesn't fit your project:

1. **Relaxation mode**: Set `JUSTINVENTIT_HOOK_MODE=relaxed` in `.env` to downgrade hook blocks to warnings
2. **Skip specific checks**: Create `.claude/hooks/stop/skip` file listing check numbers to skip: `echo "03" >> .claude/hooks/stop/skip`
3. **Full override**: Replace the hook script entirely (but it won't receive framework updates)

The skip file is the recommended approach — it's explicit, version-controlled, and survives framework updates.

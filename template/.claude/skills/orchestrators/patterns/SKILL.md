---
name: patterns
description: "Shared workflow patterns used across multiple skills. Load on-demand when referenced."
---

# Shared Patterns

## Multi-Explorer Pattern

Deploy parallel explore agents for codebase context:

```
Explorer 1: Frontend architecture (components, pages, routing)
Explorer 2: Backend architecture (API routes, services, middleware)
Explorer 3: Data layer (schema, migrations, relationships)
Explorer 4: Testing infrastructure (test files, fixtures, scenarios)
```

Each explorer returns findings under 2000 characters.

## Interview Protocol

When gathering requirements from the user:
1. Ask focused questions (not open-ended)
2. Provide options where possible
3. Record decisions in the relevant SPEC.md or skill
4. Don't ask what you can discover from code

## State File Protocol

### WORKING.md (Append-Only Observation Blocks)
```markdown
## YYYY-MM-DDTHH:MMZ
Phase: [path]
Completed: [what]
Next: [what]
Blockers: [none or description]
```

### PROGRESS.md (Checkbox Protocol)
- [ ] Item description
  - implement → check off → commit
  - Never batch checkoffs
  - If all items done → Signal `[PHASE_COMPLETE]`

## Discovery Signals

Emit when finding something outside current scope:
- `[DISCOVERY:BLOCKER]` — blocks current work
- `[DISCOVERY:DEFECT]` — bug found
- `[DISCOVERY:ADJACENT]` — related, not blocking
- `[DISCOVERY:DISTANT]` — unrelated

## Friction Signals

Emit when the system causes friction:
- `[FRICTION:SKILL]` — skill was wrong or outdated
- `[FRICTION:HOOK]` — hook blocked incorrectly
- `[FRICTION:WORKFLOW]` — workflow step was unnecessary
- `[FRICTION:CONTEXT]` — missing context caused confusion

---
name: work/sprint
description: Transition to the next sprint within an epic. Stays on the epic branch.
---

# /work:sprint

Advance to the next sprint within an epic, staying on the current epic branch.

## When to use

The current sprint's phases are complete (exit gates passed, issues closed) and the next sprint is defined in the epic plan. You're on an epic-level branch, not an issue-level one.

## Workflow

### 1. Confirm the current sprint is complete

```bash
git log --oneline -10
gh issue list --label "epic:N,sprint-M" --state closed
```

Each phase must have passed its exit gate (see `done.md` step 1). If any exit landmark is partial, do NOT advance — finish or escalate first.

### 2. Read the transition context

`docs/CURRENT_WORK.md` (sprint status + next-sprint pointer) → the epic INDEX (sprint structure) → the epic issue for full scope.

### 3. Identify the next sprint's issues

```bash
gh issue list --label "epic:N,sprint-(M+1)" --state open --json number,title
```

### 4. Explore the next sprint's scope

```
Task(subagent_type="Explore", prompt="For Sprint M+1 of epic #N:
- Which issues are in scope, and their acceptance criteria?
- What code areas change; what patterns from Sprint M carry forward?
- Dependencies between issues; suggested phase breakdown (3-4 phases)?")
```

### 5. Scaffold the next sprint's plan (if needed)

Create the sprint's phase directories, each with `SPEC.md` / `SCENARIOS.md` / `PROGRESS.md` (see `epic-plan.md` step 5).

### 6. Advance the state chain

- `docs/CURRENT_WORK.md` — set the pointer to the new sprint's **Phase 1**, including the SPEC path (the session-start hook reads this for scope injection). Add a one-line summary of the completed sprint.
- `context/WORKING.md` — append a `SPRINT TRANSITION` block with the immediate next task (create/begin Phase 1).

### 7. Output a transition report

Previous-sprint summary (issues closed, key changes), next-sprint scope table, recommended phase breakdown, then hand to `/work:continue` to begin Phase 1.

## Related

- Whole-epic planning: `epic-plan.md`
- Resuming within a sprint: `continue.md`

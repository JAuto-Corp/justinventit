---
name: work/start
description: Begin work on an issue. Anchor in the plan, assess scope, cut a branch, clear the entry gate.
---

# /work:start #N

Start work on an issue: assess scope, gather context, point the state chain at the new work.

## Workflow

### 1. Fetch the work item

```bash
gh issue view N --json title,body,labels
```

### 2. Anchor in the greater plan (mandatory, any scope)

Before assessing scope or branching, locate this issue in the bigger picture. ~3 minutes; the cost of skipping is implementing something the plan already rules out.

- Read `docs/CURRENT_WORK.md` — the active epic/sprint/phase pointer.
- Read the epic plan's INDEX (sprint structure, dependencies, success criteria) and skim sibling sprints for cross-sprint contracts.
- `git log --oneline -10 -- <relevant-paths>` — recent changes in the area.

Even a Quick fix does this: a one-line change in a file an active epic is restructuring conflicts regardless of size.

### 3. Assess scope (objective triggers — do not self-classify)

Standard+ if ANY: new DB tables/columns, new API routes, new UI pages/major components, or 4+ files. Otherwise Quick. When in doubt, it's Standard. See `SKILL.md` § Scope Classification.

### 4. Sync remote, then cut the branch

```bash
git fetch --all --prune
git checkout <integration-branch> && git pull   # clean starting point
git checkout -b feature/issue-N-description
```

Before the first commit, check nothing is already in flight: `gh pr list --search "N in:title"`, and the issue's comments for reviewer notes.

### 5. ATDD entry gate (Standard+)

No implementation without scenarios:

1. Check the phase directory for `SCENARIOS.md`.
2. If missing, **create it now** by distilling `SPEC.md` into acceptance scenarios — this is the first task, before any code.
3. Confirm any referenced stories exist; scaffold them if not.

The stop hook `checks/01-tdd-gate.sh` blocks session exit if Standard+ scope has no `SCENARIOS.md`. Skip this gate only for Quick scope.

### 6. Deploy an explorer (Standard+)

```
Task(subagent_type="Explore", prompt="For issue #N, find:
- Files I'll modify and related patterns to follow
- Test files and the validation approach
- Recent changes affecting this work")
```

### 7. Point the state chain at the new work

- `context/WORKING.md` — append an observation block: status "Issue #N started", the scope assessment, and the immediate next task (goal / key files / how to validate).
- `docs/CURRENT_WORK.md` — set/refresh the pointer (and SPEC path) if this is phased work.

### 8. Output a short context report

Summary (1-2 sentences), key files table, patterns to follow, recommended approach.

## Related

- Epic-level planning: `epic-plan.md`
- Resuming later: `continue.md`

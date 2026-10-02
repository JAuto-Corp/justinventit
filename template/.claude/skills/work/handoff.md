---
name: work/handoff
description: Package full work state for a clean handoff to another session, with a goal-focused prompt.
---

# /work:handoff

Comprehensive handoff to another session. Full state update plus a goal-focused prompt.

## Workflow

### 1. Timestamp

```bash
date "+%Y-%m-%d %H:%M %Z"
```

### 2. Read current state

`context/WORKING.md` → `docs/CURRENT_WORK.md` → phase `PROGRESS.md` (if applicable).

### 3. Gather session info

```bash
git log --oneline -5    # recent commits
git status              # uncommitted work
```

### 4. Determine the goal

The single next task — usually the first unchecked `PROGRESS.md` item, or an explicit focus.

### 5. Bring the state chain fully current

- `context/WORKING.md` — append a block: one-line status, what was done this session, the immediate next task (goal / key files / how to validate), uncommitted changes (or none), blockers/discoveries (or none).
- `docs/CURRENT_WORK.md` — update if phase status changed.
- Phase `PROGRESS.md` — check off completed items (checkbox truth).

### 6. Confirm ground truth

Verify the tree is committed and pushed so the receiver starts from a known state; if anything is uncommitted, say so **explicitly** in the handoff.

### 7. Emit a goal-focused handoff prompt

Use the single delivery reference in `docs/DELIVERY.md` for goal, scope, exact
revision, acceptance/evidence, governing inputs and next permitted action.
Link the existing record and changed facts; do not retype a parallel status summary.
Include the state paths from step 5 when they are not already in that record.
The receiver still performs the required checks below:

```markdown
Delivery reference: [existing work record containing the DELIVERY.md fields]

## Before working, you MUST
1. Read the linked governing inputs and current state files
2. Deploy an Explore to verify current state
3. Audit findings against the relevant best-practices skill
4. Add a verification entry to CURRENT_WORK.md
5. Confirm scope before proceeding
```

## Related

- Quick save: `pause.md`
- Resuming: `continue.md`

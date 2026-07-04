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

Not a context dump — a directive:

```markdown
GOAL: [specific, actionable, verifiable]

## Scope
- IN: [tasks from the issue / PROGRESS.md]
- OUT: [adjacent work to avoid]

## Key files
- context/WORKING.md — session state
- docs/CURRENT_WORK.md — work pointer
- [path]/PROGRESS.md — checklist

## Before working, you MUST
1. Read the files above
2. Deploy an Explore to verify current state
3. Audit findings against the relevant best-practices skill
4. Add a verification entry to CURRENT_WORK.md
5. Confirm scope before proceeding
```

## Related

- Quick save: `pause.md`
- Resuming: `continue.md`

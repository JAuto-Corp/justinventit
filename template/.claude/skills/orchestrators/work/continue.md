---
name: work/continue
description: Resume work from the state chain after a pause, handoff, or context reset.
---

# /work:continue

Resume from state files. Handles phase/sprint transitions automatically.

## Workflow

### 0. Compaction recovery (if applicable)

If this session just woke from a context-compaction archive, treat it as a **fresh session**, not a resume — compacted context is lossy. Re-read `CLAUDE.md` § Before Working, `git log --oneline -10` (what shipped while compacting), and any open-PR feedback, then continue to step 1 including the full plan re-read. Resuming mid-task on compacted context is the #1 source of drift.

### 1. Read the state chain (in order)

`docs/CURRENT_WORK.md` → `context/WORKING.md` → phase `SPEC.md` → phase `SCENARIOS.md` → phase `PROGRESS.md`. `SPEC.md` is required reading — it holds the acceptance criteria `/verify:complete` will check.

### 1.5. Re-anchor in the greater plan (any scope)

Phase context alone is insufficient. Re-read the epic plan's INDEX and skim sibling sprints so this phase is grounded in cross-sprint context. If the state files reference no epic plan, that's a smell — surface it.

### 2. Detect transitions

- WORKING.md says the phase was verified → identify the next phase from the plan INDEX, advance the `CURRENT_WORK.md` pointer (+ SPEC path), read the new SPEC, clear the transition note, continue.
- WORKING.md says the sprint was verified → invoke `/work:sprint`.
- Otherwise → normal resume (step 3).

### 3. Verify actual state (code is the oracle)

```bash
git status                       # uncommitted work?
git log --oneline -5             # recent commits?
git fetch --all --prune
git log --oneline HEAD..origin/$(git branch --show-current) | head -5   # remote ahead?
```

**Drift check**: if `PROGRESS.md` shows many `[x]` but there are no recent commits, sample 2-3 "done" items and look for evidence (git log, file existence). Missing evidence → treat as incomplete. When trackers and code disagree, update the tracker.

### 4. ATDD gate before any code (Standard+)

Scope is objective (see `SKILL.md` § Scope Classification). If the phase has a `SPEC.md`: `SCENARIOS.md` must exist (create it first if missing) and referenced stories must exist (scaffold if missing). Enforced at exit by `checks/01-tdd-gate.sh`. Skip only for Quick scope.

### 5. Pre-flight skill loading

Before writing code, invoke the best-practices skill matching the files in scope. Loading before implementation prevents whole categories of mistakes. For a large multi-area phase, consider the `team-lead` skill instead of solo work.

### 6. Deploy an explorer (always)

Timestamp freshness ≠ context validity.

```
Task(subagent_type="Explore", prompt="Verify current state for [issue/phase]:
- What files have been modified?
- What remains per PROGRESS.md?
- Any blockers or unexpected state?")
```

### 7. Log a verification entry (required)

Append to `docs/CURRENT_WORK.md`: `| [timestamp] | Read chain + explored [key files]. Goal: [next task]. |`. This proves the docs were read — accountability, not bureaucracy.

### 8. Resume from the immediate next task

Continue from WORKING.md's documented next task.

## Related

- Sprint transitions: `sprint.md`

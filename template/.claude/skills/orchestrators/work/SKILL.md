---
name: work
description: "Work lifecycle orchestration: start, continue, pause, handoff, complete. Includes context gathering and goal-focused state transitions."
---

# Work Lifecycle

## Commands

| Command | Purpose |
|-|-|
| `/work:start #N` | Begin work on GitHub issue #N |
| `/work:continue` | Resume work from state files |
| `/work:pause` | Save state and commit WIP |
| `/work:handoff` | Full context handoff to another agent |
| `/work:done` | Close issue, clear state |
| `/work:epic-plan #N` | Plan ALL sprints for epic #N |
| `/work:sprint` | Transition to next sprint |

## State Chain

Read in this order every session:
1. `docs/CURRENT_WORK.md` — active epic/sprint/phase pointer
2. `context/WORKING.md` — immediate next action (append-only blocks)
3. Phase `SPEC.md` — acceptance criteria
4. Phase `SCENARIOS.md` — Gherkin scenarios (ENTRY GATE)
5. Phase `PROGRESS.md` — implementation checklist

## ATDD Gate

Before implementation on Standard+ scope:
1. Check SCENARIOS.md exists → block if missing
2. Check stories exist with seed data → block if missing
3. Proceed with RED → GREEN → VERIFY cycle

## Handoff Format

When writing handoffs to WORKING.md:
```markdown
## [timestamp]
Phase: [current phase path]
Goal: [single sentence — what the next agent should accomplish]
Completed: [bullet list of done items]
Uncommitted: [list of modified files not yet committed]
Blockers: [none or description]
Next steps:
1. [specific action]
2. [specific action]
```

## PROGRESS.md Protocol

For each item: implement → check off → commit (with descriptive message).
Never batch — check off immediately after implementing.
If exit landmarks met → Signal `[PHASE_COMPLETE]`.

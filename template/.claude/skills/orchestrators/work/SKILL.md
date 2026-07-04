---
name: work
description: "Work lifecycle orchestration: start, continue, pause, handoff, done, plus epic/sprint planning. Context gathering + goal-focused state-chain transitions."
---

# Work Lifecycle

Orchestrates the full lifecycle of an issue: START → (WORK) → PAUSE/HANDOFF → CONTINUE → DONE, with EPIC-PLAN / SPRINT for multi-phase planning. Every transition updates the state chain and preserves goal-focused context for the next session.

> Don't guess — a 30-second Explore saves 30 minutes. Handoffs are goal-focused, not context dumps. Code is the oracle: when trackers and code disagree, trust the code.

## Commands

| Command | Purpose | Workflow |
|-|-|-|
| `/work:start #N` | Begin work on issue #N (scope, branch, entry gate) | `start.md` |
| `/work:continue` | Resume from state files | `continue.md` |
| `/work:pause` | Checkpoint + commit WIP | `pause.md` |
| `/work:handoff` | Full context handoff to another session | `handoff.md` |
| `/work:done` | Verify, close issue, clear state | `done.md` |
| `/work:epic-plan #N` | Plan ALL sprints/phases for epic #N | `epic-plan.md` |
| `/work:sprint` | Transition to the next sprint | `sprint.md` |

## State Chain

Read in this order every session (see `docs/ARCHITECTURE.md` § Layer 2):

1. `docs/CURRENT_WORK.md` — active epic/sprint/phase pointer (+ SPEC path)
2. `context/WORKING.md` — immediate next action (append-only observation blocks)
3. Phase `SPEC.md` — acceptance criteria + exit landmarks
4. Phase `SCENARIOS.md` — acceptance scenarios (ATDD ENTRY GATE)
5. Phase `PROGRESS.md` — implementation checklist (checkbox truth)

**WORKING.md observation block** (append-only — stable prefix hits the cache):

```markdown
## [timestamp]
Phase: [epic/sprint/phase pointer]
Goal: [one sentence — what the next session should accomplish]
Completed: [PROGRESS #n-m or bullets]
Next: [specific next action]
Uncommitted: [modified-but-uncommitted files, or none]
Blockers: [none or description]
```

## Scope Classification (objective — do not self-classify)

Standard+ is triggered by ANY of: new DB tables/columns, new API routes, new UI pages/major components, or 4+ files modified. Single-file fix with no new surface area = Quick. When in doubt, it's Standard. (Mirrors `CLAUDE.md` § TDD Gate.)

| Scope | Ceremony |
|-|-|
| Quick | Issue body = spec; unit tests = acceptance. No SCENARIOS. |
| Standard+ | SPEC → SCENARIOS → RED → GREEN → VALIDATE. Plan doc if 10+ files. |

## ATDD Gate

The cycle is **Plan → RED → GREEN → VALIDATE** (see `docs/ARCHITECTURE.md` § Layer 3).

- **Entry** (`start`/`continue`, Standard+): `SCENARIOS.md` must exist before any code — distill it from `SPEC.md` if missing. The stop hook `checks/01-tdd-gate.sh` blocks session exit if Standard+ scope has no scenarios.
- **Exit** (`done`/phase completion): before signaling `[PHASE_COMPLETE]`, every scenario must have a recorded RED-then-GREEN run and `PROGRESS.md` must be fully checked. Enforced by stop hooks `checks/03-scenario-evidence.sh` (passing run), `checks/04-tdd-cycle.sh` (RED before GREEN), `checks/05-progress-evidence.sh` (no unchecked items + commit evidence). Run `/verify:complete` as the exit gate.

## PROGRESS Protocol

For each item: implement → check off → commit (descriptive message). Never batch checkoffs — check off immediately after implementing. Commit trailers referencing a landmark are auto-checked off by the stop hook `actions/landmark-checkoff.sh`. When exit landmarks are met → signal `[PHASE_COMPLETE]`.

---

## /work:start

Begin work on an issue. Fetch the item, **anchor it in the greater plan** (read `CURRENT_WORK.md` + the epic plan for cross-sprint context), classify scope, sync remote and cut a branch, clear the ATDD entry gate for Standard+, deploy an Explore for context, then point the state chain at the new work. Full workflow: `start.md`.

## /work:continue

Resume from the state chain. If waking from compaction, treat as a fresh session and re-orient. Read the chain in order, detect phase/sprint transitions, verify actual state against git (drift check), clear the ATDD gate before any code, load the matching best-practices skill, deploy an Explore, and log a verification entry before resuming the immediate next task. Full workflow: `continue.md`.

## /work:pause

Briefly stepping away — minimal ceremony. Timestamp, commit WIP if the tree is dirty, append a PAUSED observation block to `WORKING.md` recording the exact next task, and report what was saved. Full workflow: `pause.md`.

## /work:handoff

Comprehensive handoff to another session. Bring the state chain fully current, summarize done / in-flight / exact-next, confirm the tree is committed-and-pushed (or note uncommitted state explicitly), and emit a goal-focused handoff prompt with scope boundaries and a verification checklist. Full workflow: `handoff.md`.

## /work:done

Close out verified work. Confirm the exit gate passed (`/verify:complete`, stop-hook evidence), run a code review on changed files for Standard+, make the final commit, close the issue with a summary, align docs/labels and file any deferred-work issues, clear the active pointer, then push and open a PR per the project's git workflow. Full workflow: `done.md`.

## /work:epic-plan

Plan an entire epic coherently in one pass — sequential per-sprint planning loses cross-sprint coherence. Read the epic scope, deploy comprehensive explorers (architecture / dependencies / integration / risk), optionally interview for observable outcomes, break into sprints and phases, scaffold the epic/sprint/phase folder tree with per-phase SPEC/SCENARIOS/PROGRESS, and point `CURRENT_WORK.md` at the first phase. Full workflow: `epic-plan.md`.

## /work:sprint

Advance to the next sprint within an epic (stays on the epic branch). Confirm the current sprint's phases passed their exit gates, read the transition context, identify the next sprint's issues, explore its scope, scaffold its plan structure if needed, advance the `CURRENT_WORK.md` pointer to the next Phase 1, and open a fresh `WORKING.md` block. Full workflow: `sprint.md`.

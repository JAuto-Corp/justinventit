---
name: work/epic-plan
description: Plan an entire epic coherently in one pass — all sprints and phases upfront.
---

# /work:epic-plan #N

Create the complete structure for ALL sprints and phases at epic-creation time.

> Plan the whole epic coherently in one session. Sequential per-sprint planning loses cross-sprint coherence — context from the first planning session is gone by Sprint 3.

## When to use

New epic, epic restructure (significant scope change), or any initiative of 3+ interdependent sprints.

## Workflow

### 1. Read the epic scope

```bash
gh issue view N --json title,body,labels
```

### 2. Deploy comprehensive explorers (ENTIRE epic, not just Sprint 1)

Run these in parallel:

- **Architecture**: major code areas touched across all sprints; existing patterns to follow; schema/API changes; refactor targets to bundle in.
- **Dependencies**: what must be built before what; sequential vs parallelizable ordering.
- **Integration**: external integrations involved; existing patterns; test infrastructure and fixtures/seeds needed.
- **Risk**: riskiest parts; likely blockers; what needs human decisions; what's been tried and failed.

```
Task(subagent_type="Explore", prompt="For epic #N: [one focus per explorer above]")
```

### 3. Interview for observable outcomes (optional but recommended)

Don't just gather requirements — **propose outcomes and validate them**. Cover ALL sprints, not just the first. For feature epics, ask outcome-focused questions ("user does X — what do they see?") with hypothesized options via `AskUserQuestion`. For audit-style epics, align on scope, protocol, and how findings are categorized.

### 4. Break into sprints and phases

Group the work into sprints (one coherent theme each) and, within each sprint, 3-4 phases. Capture cross-sprint contracts and dependencies now, while the whole picture is in context.

### 5. Scaffold the folder tree

Create the epic → sprint → phase hierarchy. Per level:

- **Epic INDEX** — single source of truth for sprint structure, dependencies, completion status.
- **Sprint INDEX** — that sprint's issues, phases, technical context.
- **Phase** — `SPEC.md` (acceptance criteria + exit landmarks), `SCENARIOS.md` (acceptance-scenario shape, even if stubbed), `PROGRESS.md` (implementation checklist).

Before referencing any story ID in a SPEC, verify it exists — never reference ghost stories.

### 6. Point the state chain at the first phase

Update `docs/CURRENT_WORK.md` to the epic's first sprint / Phase 1 (with the SPEC path), and note the plan in `context/WORKING.md`.

## Related

- Detailing one sprint: `sprint.md`
- Starting execution: `continue.md`

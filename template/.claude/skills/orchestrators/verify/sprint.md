---
name: verify/sprint
description: Full validation of an entire sprint before marking it complete and merging.
---

# /verify:sprint

Validate a whole sprint — every phase, plus cross-phase coherence — before merging.

## Workflow

### 1. Scope the sprint

Identify the sprint's phases and their combined changed surface from `docs/CURRENT_WORK.md` and the epic INDEX; read the epic issue for full scope.

### 2. Aggregate scenario coverage

Collect each phase's `SCENARIOS.md` into a coverage table. Phases missing scenarios are a non-blocking warning here (they block at each phase's own `/verify:complete`).

```markdown
| Phase | SCENARIOS.md | Passing | Complete |
|-|-|-|-|
| 1 | yes | 4/4 | yes |
| 2 | missing | - | - |
```

### 3. Cross-phase audit

Deploy the applicable perspectives across the sprint (see `audit.md`), plus a coherence pass specifically for drift **between** phases: schema/pattern consistency, no orphaned code from earlier phases, no broken references across phase outputs.

### 4. Cross-reference best-practices skills

Invoke the matching skill(s) in `.claude/skills/domain/` and resolve violations across all phases.

### 5. Confirm each phase's exit gate

Each phase must have passed `/verify:complete` (scenarios passing, PROGRESS checked, SPEC met). **Block the merge on any phase with unmet criteria.**

### 6. Docs ↔ issues

Verify code state first, then close (or explicitly defer, with citation) the sprint's issues and update the roadmap.

### 7. Output + marker

```markdown
## Sprint Validation: [epic] Sprint [N] — [date]
| Phase | Scenarios | Audit | Build | Status |
|-|-|-|-|-|
| 1 | 4/4 | PASS | PASS | ok |

### Sprint Status: COMPLETE   (or: BLOCKED — <items>)
```

Append a sprint-transition marker to `context/WORKING.md` for the next agent.

## Related

- Per-phase exit gate: `complete.md`
- Sprint transition (planning): `work` skill § /work:sprint

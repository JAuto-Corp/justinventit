---
name: verify/phase
description: Light audit of the current phase's changed surface for pattern alignment and coherence.
---

# /verify:phase

A targeted, lighter-weight audit of the current phase — a sanity pass before moving on. For official phase completion use `/verify:complete`.

## Workflow

### 1. Gather context

Read the phase pointer from the state chain (`docs/CURRENT_WORK.md` → `context/WORKING.md` → phase `PROGRESS.md`), then the changed surface:

```bash
git diff --name-only HEAD~5
```

### 2. Audit the changed surface

Deploy the subset of perspectives that applies to what changed (see `audit.md`), scoped to the phase's files.

### 3. Cross-reference best-practices skills

Invoke the matching skill(s) in `.claude/skills/domain/` and compare the findings against their guidelines; record violations by severity.

### 4. Findings report

Use the template in `audit.md`. File issues (or emit `[DISCOVERY:*]`) for out-of-scope items; note any `[FRICTION:*]`.

### 5. Post-verification marker

Append a phase-transition marker to `context/WORKING.md` so the session-start hook can orient the next agent:

```markdown
## Phase Transition
Phase [N] audited via /verify:phase on [timestamp]. Findings: [clean / N issues filed].
```

## Related

- Official exit gate: `complete.md`
- Audit engine + report template: `audit.md`

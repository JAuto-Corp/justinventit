---
description: Audit the current phase for pattern alignment.
---

# /verify:phase

Read the `verify` skill and execute the `/verify:phase` workflow.

**Steps**:
1. Read the active phase from the state chain (`docs/CURRENT_WORK.md` → `context/WORKING.md` → phase `PROGRESS.md`)
2. Audit the phase's changed surface against project patterns and conventions
3. Record findings; file issues for out-of-scope items and note any friction signals

See **SKILL.md § /verify:phase** for full details.

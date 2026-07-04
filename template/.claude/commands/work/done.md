---
description: Close the completed issue and clear the active work state.
---

# /work:done

Read the `work` skill and execute the `/work:done` workflow.

**Steps**:
1. Confirm the work is verified complete (the phase exit gate has passed) before closing anything
2. Close the referenced issue(s) with a summary comment
3. Clear the active pointer: reset `docs/CURRENT_WORK.md` and close the current `context/WORKING.md` block

See **SKILL.md § /work:done** for full details.

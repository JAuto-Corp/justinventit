---
description: Capture a blocking discovery as a status:blocked issue.
---

# /capture:block

Read the `capture` skill and execute the `/capture:block` workflow.

**Steps**:
1. Create the issue with a `status:blocked` label capturing the blocker
2. Add it to the current blockers list in `context/WORKING.md`
3. Append a `[DISCOVERY:BLOCKER]` line to `context/DISCOVERIES.md` and keep moving

See **SKILL.md § /capture:block** for full details.

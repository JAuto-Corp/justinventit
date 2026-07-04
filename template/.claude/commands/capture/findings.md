---
description: Capture ad-hoc discoveries from the current session as issues.
---

# /capture:findings

Read the `capture` skill and execute the `/capture:findings` workflow.

**Steps**:
1. Collect the discoveries surfaced during work that fall outside the current task
2. Create an issue per item (labelled `captured`) with a brief body
3. Append the matching `[DISCOVERY:*]` signal to `context/DISCOVERIES.md` and continue

See **SKILL.md § /capture:findings** for full details.

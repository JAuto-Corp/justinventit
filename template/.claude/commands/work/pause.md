---
description: Checkpoint and pause work, preserving resumable state.
---

# /work:pause

Read the `work` skill and execute the `/work:pause` workflow.

**Steps**:
1. Flush current context into the state chain: update `context/WORKING.md` (observation block) and the active phase `PROGRESS.md`
2. Record the exact next task so a later `/work:continue` resumes cleanly
3. Commit any in-progress work with a clear WIP message

See **SKILL.md § /work:pause** for full details.

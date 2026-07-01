---
description: Package work state for a clean handoff to another session or agent.
---

# /work:handoff

Read the `work` skill and execute the `/work:handoff` workflow.

**Steps**:
1. Bring the state chain fully current: `docs/CURRENT_WORK.md` (pointer), `context/WORKING.md` (latest observation), active phase `PROGRESS.md` (checkbox truth)
2. Summarize what is done, what is in-flight, and the exact next task
3. Verify the working tree is committed/pushed (or note uncommitted state explicitly) so the receiver starts from ground truth

See **SKILL.md § /work:handoff** for full details.

---
description: Resume work from state files after a pause or handoff.
---

# /work:continue

Read the `work` skill and execute the `/work:continue` workflow.

**Steps**:
1. Read the state chain in order: `docs/CURRENT_WORK.md` → `context/WORKING.md` → the active phase `PROGRESS.md`
2. Verify against git: `git status`, `git log --oneline -5`
3. Resume at the documented next task (treat timestamp freshness as not-equal to context validity — re-ground before acting)

See **SKILL.md § /work:continue** for full details.

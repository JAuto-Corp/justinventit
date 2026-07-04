---
description: Begin work on a GitHub issue — gather context and set the state chain.
---

# /work:start

Read the `work` skill and execute the `/work:start` workflow.

**Steps**:
1. Read the target issue and gather context (`git status`, relevant skills, `docs/CURRENT_WORK.md`)
2. Point the state chain at the new work: set the `docs/CURRENT_WORK.md` pointer and open a fresh `context/WORKING.md` observation block
3. Confirm the ATDD entry gate for the scope (scenarios/spec present) before starting implementation

See **SKILL.md § /work:start** for full details.

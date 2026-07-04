---
description: Run an end-to-end validation flow for the active phase.
---

# /e2e:run

Read the `e2e` skill and execute the `/e2e:run` workflow.

**Steps**:
1. Read the active phase's scenarios from the state chain (`docs/CURRENT_WORK.md` → the phase's `SCENARIOS.md`)
2. Choose the testing mode appropriate to the change (conductor, direct, or SQL) and drive the flow
3. Capture evidence (screenshots, logs) for each scenario so the verify exit gate can confirm it

See **SKILL.md § /e2e:run** for full details.

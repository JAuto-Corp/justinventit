---
description: Triage captured issues — classify, label, and route.
---

# /capture:triage

Read the `capture` skill and execute the `/capture:triage` workflow.

**Steps**:
1. List open captured issues (`gh issue list --label captured`)
2. Classify each by discovery type (blocker / defect / adjacent / distant) and set labels and priority
3. Promote blockers into the active state chain; leave the rest parked

See **SKILL.md § /capture:triage** for full details.

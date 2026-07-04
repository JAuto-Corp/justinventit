---
description: Convert audit findings into tracked issues.
---

# /capture:audit

Read the `capture` skill and execute the `/capture:audit` workflow.

**Steps**:
1. Read the audit findings to triage
2. Create one issue per actionable finding (labelled `captured`), grouping duplicates
3. Append `[DISCOVERY:*]` lines to `context/DISCOVERIES.md` linking the created issues

See **SKILL.md § /capture:audit** for full details.

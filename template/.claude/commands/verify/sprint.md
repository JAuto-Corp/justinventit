---
description: Audit an entire sprint before merging.
---

# /verify:sprint

Read the `verify` skill and execute the `/verify:sprint` workflow.

**Steps**:
1. Identify the sprint's phases and their combined changed surface
2. Run a multi-perspective audit across the sprint (coherence, correctness, patterns)
3. Confirm each phase's exit gate passed; block the merge on any unmet criteria

See **SKILL.md § /verify:sprint** for full details.

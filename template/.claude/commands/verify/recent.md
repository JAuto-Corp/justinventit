---
description: Audit the most recent commits for regressions.
---

# /verify:recent

Read the `verify` skill and execute the `/verify:recent` workflow.

**Steps**:
1. List the recent commits (`git log --oneline -5`) and inspect their diffs
2. Audit the changed surface for correctness, patterns, and coherence
3. Report findings; file issues for anything needing follow-up

See **SKILL.md § /verify:recent** for full details.

---
name: verify/recent
description: Quick audit of the last few commits for regressions and pattern drift.
---

# /verify:recent

A fast audit of the last few commits — a sanity check before a PR or `/work:handoff`.

## Workflow

### 1. Gather the changes

```bash
git log --oneline -5
git diff --name-only HEAD~5
```

(Adjust the range to the set actually under review.)

### 2. Categorize changed files

Group the changed files by role — entry points, logic, data, config, docs — to decide which perspectives apply.

### 3. Deploy explorers scoped to the changes

Deploy the applicable perspectives (see `audit.md`), scoped to the changed files.

### 4. Cross-reference best-practices skills

Invoke the matching skill(s) in `.claude/skills/domain/` for the categories that changed.

### 5. Quick report

```markdown
## Recent Changes Audit — [date]
Commits: [hashes + messages] · Files changed: [n]

| Category | Files | Issues |
|-|-|-|
| [category] | [n] | [n] |

### Status: CLEAN / ISSUES FOUND
```

File issues (or emit `[DISCOVERY:*]`) for anything needing follow-up.

## When to use

- Before opening a PR or running `/work:handoff`
- A quick sanity pass after a burst of commits

## Related

- Audit engine + report template: `audit.md`
- Full phase gate: `complete.md`

---
name: work/pause
description: Checkpoint and commit WIP when stepping away briefly. Minimal ceremony.
---

# /work:pause

Briefly stepping away. Commit WIP, flush state, minimal ceremony.

## Workflow

### 1. Timestamp

```bash
date "+%Y-%m-%d %H:%M %Z"
```

### 2. Check for uncommitted work

```bash
git status
git diff --stat
```

### 3. Commit WIP if the tree is dirty

```bash
git add -A
git commit -m "WIP(#N): [brief description]"
```

### 4. Flush state to WORKING.md

Append an observation block (see `SKILL.md` § State Chain) with status `PAUSED` and the **exact next task** so a later `/work:continue` resumes cleanly:

```markdown
## [timestamp]
Phase: [pointer]
Goal: [what to do on resume]
Next: [specific next action — files + how to validate]
Uncommitted: [none — WIP committed]
Blockers: [none or description]
```

### 5. Report

Tell the user what was saved and that `/work:continue` resumes it.

## Related

- Full handoff to another session: `handoff.md`
- Resuming: `continue.md`

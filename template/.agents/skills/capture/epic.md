---
name: capture/epic
description: Group related captured issues into a new epic and hand off to /work:epic-plan.
---

# /capture:epic

When several captured issues share a theme, roll them up into one epic issue that names the initiative and links them as its scope. This creates a NEW epic; it does not plan it — `/work:epic-plan` does that later.

> Routing issues into an EXISTING epic is `/capture:triage`. Reach for an epic when a cluster of issues (roughly 5+) shares a feature area, spans several surfaces, or forms one strategic outcome.

## Workflow

### 1. Select the cluster

```bash
gh issue list --state open --json number,title,labels
```

Pick the related issues. If the grouping isn't obvious, deploy an Explore to cluster them by theme and surface dependencies:

```
Task(subagent_type="Explore", prompt="Group these open issues by theme/feature area and
note dependencies between them: <list>. Return under 2000 characters.")
```

### 2. Create the epic issue

```bash
gh issue create \
  --title "Epic: <theme>" \
  --label "epic" \
  --body "$(cat <<'EOF'
## Overview
[What this epic achieves — 2-3 sentences]

## Scope (issues)
- [ ] #A — title
- [ ] #B — title
- [ ] #C — title

## Success criteria
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

## Dependencies
- Depends on: [epic/system]
- Blocks: [epic]
EOF
)"
```

### 3. Link the children

```bash
gh issue edit <A> --add-label "epic:<N>" --remove-label "captured"
gh issue edit <B> --add-label "epic:<N>" --remove-label "captured"
```

### 4. Note it for planning

Record the new epic in the state chain (`context/WORKING.md`, and `docs/CURRENT_WORK.md` if it's next up) so it's visible. Sprint/phase breakdown is out of scope here — hand off:

```
/work:epic-plan #<N>
```

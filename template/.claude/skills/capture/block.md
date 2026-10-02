---
name: capture/block
description: File a status:blocked issue for an external blocker, record it in the state chain, and keep moving.
---

# /capture:block

An external dependency stops the current task. Park it as a tracked blocker so nothing is lost, record it where the next session will see it, then continue on work that isn't blocked. Use for a `[DISCOVERY:BLOCKER]` signal or any hard external stop.

## Workflow

### 1. Create the blocked issue

```bash
gh issue create \
  --title "<type>: <brief description>" \
  --label "captured,status:blocked" \
  --body "$(cat <<'EOF'
## Context
[What we were trying to do]

## Blocked by
[External dependency, missing access, or pending decision]

## Unblock criteria
[What must happen before this can proceed]

## Workaround
[Temporary path forward, if any — or "none"]
EOF
)"
```

### 2. Record it in the state chain

- Add a line to the **Blockers** field of the latest `context/WORKING.md` observation block.
- If the blocker gates the active phase, note it in `docs/CURRENT_WORK.md` too.
- Append the discovery to `context/DISCOVERIES.md` so the log and the issue agree:

```markdown
## [timestamp]
[DISCOVERY:BLOCKER] #<n> — <brief description>
```

### 3. Keep moving

Switch to unblocked work. Don't stall the session waiting on the dependency; the issue and the state chain hold the context.

## When to use

- Missing credentials, access, or environment
- An external API/service not yet available
- A pending decision from the user or another team
- A dependency on unmerged upstream work

Genuinely blocked (can't proceed) → here. Merely out of scope (could proceed, shouldn't now) → `/capture:findings`.

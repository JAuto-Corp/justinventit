---
name: capture/findings
description: Convert session discoveries logged in context/DISCOVERIES.md into tracked issues.
---

# /capture:findings

Process the discoveries surfaced during work into tracked issues. The stop action `stop/actions/discovery-extraction.sh` collects every `[DISCOVERY:*]` signal into `context/DISCOVERIES.md`; this is the deliberate pass that converts the open ones into issues so nothing stays only in the log.

## Prerequisite

`context/DISCOVERIES.md` has unprocessed entries (or you have discoveries from the live session to file). Skip anything a signal already turned into an issue.

## Workflow

### 1. Read the discovery log

```bash
cat context/DISCOVERIES.md
```

Each block is a timestamp + a `[DISCOVERY:*]` line. Note which already reference an issue number — skip those.

### 2. Triage each open discovery

Map the signal to intent (see the `patterns` skill § Discovery Signals):

| Signal | File as |
|-|-|
| `[DISCOVERY:BLOCKER]` | Prefer `/capture:block` (adds `status:blocked` + state chain) |
| `[DISCOVERY:DEFECT]` | `bug` |
| `[DISCOVERY:ADJACENT]` | `enhancement` / `tech-debt` |
| `[DISCOVERY:DISTANT]` | `enhancement`, low priority |

### 3. Create one issue per open discovery

```bash
gh issue create \
  --title "<type>: <brief description>" \
  --label "captured,<type>,<priority>" \
  --body "$(cat <<'EOF'
## Context
[Where discovered — what was being worked on]

## Problem
[What's wrong or missing]

## Evidence
[file:line, error text, or artifact path]
EOF
)"
```

Add `discovered:from-#N` when the discovery came from working another issue.

### 4. Close the loop on the log

Annotate the processed entry so the log and the tracker agree:

```markdown
[DISCOVERY:DEFECT] #<n> — <brief description>   <- filed
```

Leave blockers you routed to `/capture:block` marked accordingly. Batches go to `/capture:triage` for priority/epic routing.

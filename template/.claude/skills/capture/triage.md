---
name: capture/triage
description: Classify parked captured issues by discovery type, label and prioritize, promote blockers, park the rest.
---

# /capture:triage

Give the parking lot a deliberate pass. Captured issues arrive fast and lightly labeled; triage classifies each, sets consistent labels, promotes anything that blocks active work, and clears the `captured` flag once an issue has a home.

> Distributing issues into EXISTING epics/sprints is part of this pass. Creating a NEW epic is `/capture:epic`.

## Workflow

### 1. List the parking lot

```bash
gh issue list --label captured --state open --json number,title,labels
```

### 2. Classify each by discovery type

| Type | Signal | Action |
|-|-|-|
| Blocker | `[DISCOVERY:BLOCKER]` | Promote — see step 4 |
| Defect | `[DISCOVERY:DEFECT]` | `bug` + priority |
| Adjacent | `[DISCOVERY:ADJACENT]` | `enhancement`/`tech-debt`, this or next sprint |
| Distant | `[DISCOVERY:DISTANT]` | Low priority, backlog |

For non-obvious ones, deploy an Explore to check impact and dependencies before deciding:

```
Task(subagent_type="Explore", prompt="For issues #A #B #C: what does each touch,
what depends on them, and what's the real severity? Return under 2000 characters.")
```

### 3. Set labels and priority

```bash
gh issue edit <n> --add-label "<type>,<priority>" --remove-label "captured"
```

Removing `captured` marks the issue as triaged. Add `epic:N` here if it clearly belongs to an existing epic.

### 4. Promote blockers into the active state chain

For a genuine blocker: add `status:blocked`, record it in the latest `context/WORKING.md` **Blockers** field, and — if it gates the active phase — in `docs/CURRENT_WORK.md`. Everything else stays parked (backlog), just with real labels now.

### 5. Ambiguous classification — ask, don't guess

When an issue could be several priorities, or its scope hints it needs its own epic, use `AskUserQuestion` (structured, not a text dump) rather than assuming. A 30-second question beats re-triaging later.

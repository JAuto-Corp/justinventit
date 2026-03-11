---
name: capture
description: "Quick issue capture and labeling. Park discoveries and keep moving. Supports blocking issues and conversion from audit findings."
---

# Capture

## Purpose

When you discover something during work that isn't part of the current task, capture it as an issue and keep moving. Don't context-switch.

## Commands

| Command | Purpose |
|-|-|
| `/capture` | Quick issue capture |
| `/capture:block` | Create blocked issue with status:blocked label |
| `/capture:audit` | Convert audit findings to issues |

## Quick Capture

```bash
gh issue create --title "..." --body "..." --label "captured"
```

Then append to `context/DISCOVERIES.md`:
```markdown
## [timestamp]
[DISCOVERY:ADJACENT] Created #N — brief description
```

## Discovery Signal Types

| Signal | Meaning | Action |
|-|-|-|
| `[DISCOVERY:BLOCKER]` | Blocks current work | Create issue, add to blockers |
| `[DISCOVERY:DEFECT]` | Bug found during work | Create issue, continue working |
| `[DISCOVERY:ADJACENT]` | Related but not blocking | Create issue, continue working |
| `[DISCOVERY:DISTANT]` | Unrelated finding | Create issue, continue working |

The stop hook extracts these signals automatically.

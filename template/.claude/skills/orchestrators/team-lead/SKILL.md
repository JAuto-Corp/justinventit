---
name: team-lead
description: "Coordinate Agent Teams for parallelizable work. Manages WAIT pattern, file ownership, and worktree safety."
user-invocable: true
---

# Team Lead

## The WAIT Pattern

The central mechanical constraint for agent teams:

```
Lead: spawn teammates → assign tasks → STOP (zero tool calls)
                                         ↓
Messages arrive (only when lead is idle)
                                         ↓
Lead: process message → assign next → STOP
```

Messages queue indefinitely during active turns. The lead MUST oscillate between acting and waiting.

## File Ownership

**Absolute rule**: No two teammates edit the same file concurrently.

Before spawning, write a team ownership manifest:
- Each teammate gets a list of owned files/directories
- Each teammate gets a list of off-limits zones
- Cross-zone tasks become dependent task chains

## Spawn Context

Each teammate's prompt should include:
1. Which skills to invoke for their task
2. Which files they own
3. Which files are off-limits
4. The acceptance criteria for their deliverable
5. How to signal completion

## Model Selection

| Role | Model |
|-|-|
| Planning / architecture | opus |
| Implementation | sonnet |
| Exploration / research | sonnet |
| Simple lookups | haiku |

## Recovery

After context compression or team failure:
1. `git log` — commits are the durable checkpoint
2. `PROGRESS.md` — the phase checkpoint
3. Rebuild team from remaining work items

## Team Size

3-5 teammates is the practical sweet spot. Start smaller than you think — three focused teammates outperform five scattered ones.

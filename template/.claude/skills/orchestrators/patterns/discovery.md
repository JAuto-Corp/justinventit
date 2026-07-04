---
name: patterns/discovery
description: The discovery and friction signal vocabulary — emit to capture issues outside current scope without derailing the task.
---

# Discovery & Friction Signals

Two append-only logs collect signals emitted during work. You never edit them by hand — the stop actions append, and the `capture` skill processes them into issues and fixes.

| Log | Stop action | Scans for |
|-|-|-|
| `context/DISCOVERIES.md` | `stop/actions/discovery-extraction.sh` | `[DISCOVERY:*]` |
| `context/FRICTION_LOG.md` | `stop/actions/friction-extraction.sh` | `[FRICTION:*]` |

Both actions run at session stop, match the bracketed signal anywhere in output, and append a timestamped block. They never block — logging is automatic; acting on the logs is deliberate (`capture`).

---

## Discovery Signals (issues outside current scope)

| Signal | When to use | Action |
|-|-|-|
| `[DISCOVERY:BLOCKER]` | Security hole, or requirements are wrong | STOP work, escalate |
| `[DISCOVERY:DEFECT]` | Bug in existing code | Capture & continue |
| `[DISCOVERY:ADJACENT]` | Same epic, a different phase | Capture for later phase |
| `[DISCOVERY:DISTANT]` | Unrelated to current work | Capture for backlog |

### Format

```
[DISCOVERY:TYPE] One-line description

Context:  what you were doing when you found it
Impact:   why it matters
Location: file:line or area affected
```

### Triage matrix

| Current scope | Discovery location | Signal |
|-|-|-|
| This phase | This phase | Fix now (no signal) |
| This phase | Later phase, same epic | `[DISCOVERY:ADJACENT]` |
| This epic | A different epic | `[DISCOVERY:DISTANT]` |
| Any | Security / broken requirements | `[DISCOVERY:BLOCKER]` |

---

## Friction Signals (the process got in the way)

Emit when a skill, hook, or workflow step — not the code — caused the problem. This is the self-improvement loop's raw input.

| Signal | When |
|-|-|
| `[FRICTION:SKILL]` | A skill was wrong, outdated, or missing for this codebase |
| `[FRICTION:HOOK]` | A hook blocked or fired when it shouldn't have |
| `[FRICTION:WORKFLOW]` | A workflow step was unnecessary or in the wrong order |
| `[FRICTION:CONTEXT]` | Missing context caused confusion or rework |

### Format

```
[FRICTION:TYPE] What got in the way, and what you expected instead
```

`capture` classifies each logged entry as **PROJECT** (fix the local artifact) or **FRAMEWORK** (file it upstream so a template update pulls the fix back). Keep the signal one line — detail goes in the follow-up issue.

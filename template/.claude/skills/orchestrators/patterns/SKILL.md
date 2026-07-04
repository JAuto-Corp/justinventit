---
name: patterns
description: "Shared workflow patterns referenced across orchestrator skills — multi-explorer deployment, the discovery/friction signal vocabulary, the outcome interview, and state-chain file formats. Load on-demand when a skill points to a section."
---

# Shared Patterns

Reusable patterns extracted from the orchestrator skills so they live in one place. Load the specific pattern a skill points you to — don't preload.

## Available Patterns

| Pattern | Depth file | Referenced by |
|-|-|-|
| Multi-Explorer | `explorer.md` | work, verify |
| Discovery Signals | `discovery.md` | verify, capture |
| Friction Signals | `discovery.md` | verify, capture |
| Interview Protocol | `interview.md` | work |
| State Files | `state-files.md` | work, verify, capture |

## When to Load

A skill says "see the `patterns` skill § X" or "see `patterns/explorer.md`". Read the matching file only when you hit that reference. The sections below are the quick reference; the depth files carry formats, examples, and edge cases.

---

## Multi-Explorer Pattern

Deploy read-only `Explore` sub-agents to gather context before acting. Each gets one viewpoint over a fixed scope and returns bounded, evidence-backed findings; you cross-reference them and verify the cited lines before trusting anything.

```
Task(subagent_type="Explore", prompt="[Viewpoint] for [SCOPE]:
- <focused questions for this viewpoint>
Return findings under 2000 characters, each with file:line and (for audits) a severity.")
```

Explorers cannot load skills — after they report, YOU invoke any matching best-practices skill and reconcile. Full deployment guidance, the viewpoint menu, and the validation checklist: `explorer.md`.

---

## Discovery Signals

Emit when you find something **outside the current scope** and want it tracked without derailing. The stop action `stop/actions/discovery-extraction.sh` scans session output for `[DISCOVERY:*]` and appends each to `context/DISCOVERIES.md`; the `capture` skill later turns those into issues.

| Signal | Meaning | Action |
|-|-|-|
| `[DISCOVERY:BLOCKER]` | Security/requirements wrong; blocks current work | STOP, escalate |
| `[DISCOVERY:DEFECT]` | Bug in existing code | Log, continue |
| `[DISCOVERY:ADJACENT]` | Related to this epic, a different phase | Log for later phase |
| `[DISCOVERY:DISTANT]` | Unrelated to current work | Log for backlog |

Format, examples, and the triage matrix: `discovery.md`.

---

## Friction Signals

Emit when the **process itself** was wrong — a skill, hook, or workflow step got in the way. The stop action `stop/actions/friction-extraction.sh` scans for `[FRICTION:*]` and appends each to `context/FRICTION_LOG.md`; `capture` classifies each PROJECT vs FRAMEWORK.

| Signal | When |
|-|-|
| `[FRICTION:SKILL]` | A skill was wrong, outdated, or missing for this codebase |
| `[FRICTION:HOOK]` | A hook blocked or fired when it shouldn't have |
| `[FRICTION:WORKFLOW]` | A workflow step was unnecessary or in the wrong order |
| `[FRICTION:CONTEXT]` | Missing context caused confusion or rework |

Format and the classification handoff: `discovery.md`.

---

## Interview Protocol

Use the `AskUserQuestion` tool for iterative Q&A before writing a spec or making a UX/architecture decision the code can't answer. Ask 1-4 structured questions per round, process answers, ask again — never dump a wall of text. Skip for single-file fixes and clear technical tasks. Categories, rhythm, and output: `interview.md`.

---

## State Files

The state chain carries work across sessions and context resets.

| File | Purpose |
|-|-|
| `docs/CURRENT_WORK.md` | Active epic/sprint/phase pointer |
| `context/WORKING.md` | Append-only session observation blocks |
| Phase `PROGRESS.md` | Implementation checklist |

Read order and templates: `state-files.md`.

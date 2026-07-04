---
name: patterns/explorer
description: Deploy read-only Explore sub-agents to gather codebase context before acting, then cross-reference and verify their findings.
---

# Multi-Explorer Pattern

> A 30-second Explore often saves 30 minutes.

Deploy parallel `Explore` sub-agents, each with a distinct viewpoint over one fixed scope. Cross-reference their findings; the disagreements are usually the most important signal.

## The Explore sub-agent

`Explore` agents are **read-only** — they investigate and report, they do not edit. They **cannot load skills**, so any best-practices reconciliation is yours to do after they report. Keep each report **under 2000 characters** so several fit in your context at once.

```
Task(subagent_type="Explore", prompt="[Viewpoint] for [SCOPE]:
- <focused questions for this viewpoint>
Return findings under 2000 characters, each as {claim, evidence: file:line, reasoning}.")
```

## Evidence over trust

Every finding must carry:
- **Claim** — what was observed (1-2 sentences)
- **Evidence** — `file:line` where it was found
- **Reasoning** — why, if non-obvious

Evidence enables verification, not trust. A claim with no `file:line` can't be checked efficiently — re-explore or ignore it. Read the cited lines yourself before acting on anything critical.

## Viewpoint menu (pick the subset the scope warrants)

| Viewpoint | Asks |
|-|-|
| Files & patterns | What files exist here? What conventions and dependencies apply? |
| Data & schema | What data structures are involved? What relationships and constraints? |
| Interfaces & flows | What APIs / UI / entry points touch this? What states must exist? |
| Tests & validation | What tests cover this? What edge cases? How is it validated? |
| Dependencies | What depends on this? What does it depend on? What breaks if it changes? |
| Risk | What's riskiest? What could block progress? What needs a human decision? |

For scouting an unfamiliar area, 3-5 broad viewpoints. For a scoped audit, one Explore per applicable perspective (correctness, coherence, integration, …) — see the `verify` skill.

## Give context when exploring for implementation

When you already know the goal, say so — otherwise explorers may treat legacy or deprecated code as the current pattern:

```
Task(subagent_type="Explore", prompt="
CONTEXT: implementing [X] per [plan/issue]. Goal: [specific objective].
Find: [specific questions].
Flag anything that looks outdated or inconsistent with that goal rather than assuming it's current.
Return under 2000 characters with file:line evidence.")
```

## Validate before acting

1. Audit evidence quality — does each finding cite `file:line`?
2. Verify critical claims — read the cited lines; does the code match?
3. Cross-reference explorers — reconcile disagreements.
4. Cross-reference skills — explorers can't load them; you invoke the matching best-practices skill and compare.
5. Confirm paths exist before building on them.

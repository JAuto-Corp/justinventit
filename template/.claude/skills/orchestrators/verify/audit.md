---
name: verify/audit
description: The multi-perspective audit engine — parallel explorers, one per applicable perspective.
---

# /verify:audit

Deploy parallel Explore agents with distinct viewpoints over a scoped surface, then cross-reference the project's best-practices skills. This is the engine `phase`, `sprint`, `file`, `feature`, `recent`, and `complete` all call.

## 1. Scope

Fix the surface up front — a phase, sprint, feature, file set, or commit range. Every explorer prompt names it.

## 2. Perspectives (deploy the subset that applies)

Pick the perspectives the changed surface warrants; skip the rest. Each is one Explore agent (see the `patterns` skill § Multi-Explorer Pattern), returning **under 2000 characters**.

| Perspective | Asks |
|-|-|
| **Correctness** | Logic sound? Edge cases, error paths, and failure modes handled? |
| **Coherence** | Consistent with existing patterns and naming? Dead code, unused imports, orphaned files? |
| **Integration** | Do the pieces connect? Every new surface reachable? No broken/dangling references? |
| **Conventions** | Follows project conventions and the matching best-practices skill? |
| **Configuration** | Conflicting settings? Contradictory defaults? Env-specific config separated? |
| **Consumer journey** | Can a user/caller complete the end-to-end flow? Empty/loading/error/edge states present? Messages actionable? |

Explorer prompt shape:

```
Task(subagent_type="Explore", prompt="[Perspective] audit for [SCOPE]:
- <perspective questions from the row above>
Return findings under 2000 characters, each with file:line and a severity.")
```

## 3. Cross-reference best-practices skills (mandatory)

Explorers cannot load skills. After they report, YOU invoke each applicable skill in `.claude/skills/domain/`, compare every finding against its guidelines, and mark violations `critical` or `warning`. **Critical violations block phase completion.**

## 4. Findings report

```markdown
# Audit: [SCOPE] — [date]
Files analyzed: [n] · Skills cross-referenced: [list / none]

## Summary
| Perspective | Issues | Max severity |
|-|-|-|
| [perspective] | [n] | critical/warning/info |

## Critical (must fix)
### [Perspective]: [title]
- **File**: `path:line`
- **Problem**: [what]
- **Fix**: [action]
- **Skill**: [skill name / n/a]

## Warnings (should fix)
[same shape]

## Positive findings
- [pattern done well]

## Status: CLEAN / ISSUES FOUND
```

Out-of-scope problems become issues (or `[DISCOVERY:*]` signals — see `patterns` skill), not scope creep.

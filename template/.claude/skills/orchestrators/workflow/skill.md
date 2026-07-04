---
name: workflow/skill
description: Patterns for adding or editing a skill — frontmatter contract, router + sub-file split, line budgets.
---

# Add or Edit a Skill

A skill is lazy-loaded knowledge: only its frontmatter enters context at session start, the body loads on invocation. Two kinds live in the framework.

| Kind | Location | Owner |
|-|-|-|
| Orchestrator (workflow control) | `.claude/skills/orchestrators/<name>/` | Framework-managed (arrives via `copier update`) |
| Domain (best practices) | `.claude/skills/domain/<name>/` | Project-owned (never touched by updates) |

## Frontmatter contract (required)

```yaml
---
name: skill-name          # matches the directory
description: One sentence — WHEN to invoke this skill. This is all the runtime sees until invocation, so make it a good trigger.
---
```

Domain skills may add `covers:` metadata (`files:` glob, `patterns:`, `conventions:`) so drift detection can compare the skill's claims against real code. Orchestrator skills omit it.

## Structure — router + sub-files

For anything with more than one operation, split like the neighbors (`work`, `verify`):

```
.claude/skills/<group>/<name>/
├── SKILL.md      # router: frontmatter, philosophy line, operations table, per-op one-liners
├── op-a.md       # one focused workflow
└── op-b.md       # one focused workflow
```

The router carries a one-line intent per operation and points to the sub-file for the full workflow — it does NOT inline the workflow. Sub-files carry the steps.

## Line budgets

| File | Target |
|-|-|
| Router SKILL.md | 60–150 |
| Sub-file (one workflow) | 30–90 |
| Single-file skill (no sub-ops) | up to ~200 |

## Rules

- One authoritative home per topic. If it lives in a skill, `CLAUDE.md` and commands only POINT to it.
- Pointers over copies — reference a file/section, don't paste its content.
- Tables over prose for anything scannable.
- A new command wrapper is optional; a skill is invoked by name via the Skill tool regardless.

When done, run `validate.md`.

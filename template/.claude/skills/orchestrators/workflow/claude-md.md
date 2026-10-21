---
name: workflow/claude-md
description: Editing AGENTS.md (the router) and CLAUDE.md (Claude extras). The 200-line budget, forge markers, pointers over content.
---

# Edit AGENTS.md and CLAUDE.md

`AGENTS.md` is the one file every runtime reads first (Claude Code through `CLAUDE.md`'s `@AGENTS.md` import). It is a routing table, not a manual: where am I, what do I do first, how do I find the right skill/rule/doc. Adherence drops sharply past ~200 lines, so every line must earn its place.

## Where your edit goes

- `AGENTS.md` is project-owned: edit it directly. Framework contract changes arrive as `entry-contract` rows in the framework's CHANGES.md for you to merge.
- `CLAUDE.md` holds Claude Code extras only. Its forge-marker block is framework-managed (source `CLAUDE.md.jinja`, overwritten by `copier update`); project additions go outside the markers.

## Budget & content

| Metric | Target |
|-|-|
| Total lines | < 200 |
| Per skill/rule pointer | 1–2 lines |

Belongs here: orientation table, authority/routing map (topic → skill or rule), the most-used commands, "for X, invoke Y skill". Does NOT belong here: full workflows (→ skill), code snippets (→ file reference), path-specific guidance (→ rule), exhaustive command lists (→ the command files themselves).

## Rules

- Pointers over copies. If content lives in a skill or rule, `AGENTS.md` only names it.
- Tables over prose.
- Use `IMPORTANT` / `NEVER` / `ALWAYS` sparingly — overuse dilutes them.

When done, run `validate.md`.

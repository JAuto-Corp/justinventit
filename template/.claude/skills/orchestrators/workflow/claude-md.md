---
name: workflow/claude-md
description: Editing CLAUDE.md — the session router. Forge markers, the 200-line budget, pointers over content.
---

# Edit CLAUDE.md

`CLAUDE.md` is the one file every session reads first. It is a routing table, not a manual: where am I, what do I do first, how do I find the right skill/rule/doc. Adherence drops sharply past ~200 lines, so every line must earn its place.

## Forge markers — where your edit goes

```
<!-- forge:start — DO NOT EDIT between forge markers (updated by copier update) -->
   ...framework-managed router content...
<!-- forge:end -->
   ...project-owned content (survives copier update)...
```

- **Framework content** (applies to every generated project) belongs BETWEEN the markers — and its source is `CLAUDE.md.jinja`, not the generated `CLAUDE.md`. Edit the template, not the output, or `copier update` will overwrite you.
- **Project content** (this repo's specifics) belongs OUTSIDE the markers, where updates leave it alone.

## Budget & content

| Metric | Target |
|-|-|
| Total lines | < 200 |
| Per skill/rule pointer | 1–2 lines |

Belongs here: orientation table, authority/routing map (topic → skill or rule), the most-used commands, "for X, invoke Y skill". Does NOT belong here: full workflows (→ skill), code snippets (→ file reference), path-specific guidance (→ rule), exhaustive command lists (→ the command files themselves).

## Rules

- Pointers over copies. If content lives in a skill or rule, `CLAUDE.md` only names it.
- Tables over prose.
- Use `IMPORTANT` / `NEVER` / `ALWAYS` sparingly — overuse dilutes them.

When done, run `validate.md`.

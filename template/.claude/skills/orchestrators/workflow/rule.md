---
name: workflow/rule
description: Adding or editing a path-scoped rule — loads only for matching files, keeps CLAUDE.md lean.
---

# Edit a Rule

A rule is path-scoped guidance that loads ONLY when Claude works with a matching file. It is the right home for domain knowledge that is real but not universal — putting it here keeps `CLAUDE.md` under budget while the guidance still reaches the agent exactly when it is relevant.

Location: `.claude/rules/<name>.md`. Project-owned — `copier update` never touches it.

## Frontmatter contract

```yaml
---
paths: ["src/api/**/*.ts", "src/routes/**/*.ts"]
---
```

`paths` is a list of globs. The rule enters context only when the agent reads/edits a file one of them matches. No glob = no scoping benefit, so always scope.

## Body

Lean, imperative, scannable — the same bar as a skill sub-file, but narrower:

```markdown
# API Route Rules

- Validate input against a schema.
- Return typed responses.
- Log errors with full context.
```

## Rules

- One topic per rule; scope it tightly so it doesn't load for unrelated work.
- Prefer a rule over adding lines to `CLAUDE.md` for anything path-specific.
- If the guidance is a full workflow, it belongs in a skill; a rule is a short list of do/don't for a file class.

When done, run `validate.md`.

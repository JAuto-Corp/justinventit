---
name: workflow/command
description: Patterns for adding or editing a command — thin pointer into a skill, auto-discovered by path.
---

# Add or Edit a Command

A command is a lean entry point. It is auto-discovered from its path (`.claude/commands/<domain>/<name>.md` → `/<domain>:<name>`), so creating the file IS creating the slash command. Its whole job is to route into a skill; the skill holds the workflow.

## Frontmatter contract

```yaml
---
description: "Brief line — shows up in slash-command discovery. Without it the command isn't listed."
argument-hint: <arg>   # only if it takes an argument
---
```

## Pure-pointer shape (preferred)

```markdown
---
description: Resume work from the state chain.
---

# /work:continue

Invoke the `work` skill, then read `.claude/skills/orchestrators/work/continue.md` for the workflow.
```

A few numbered steps are fine when they aid orientation (see `commands/workflow/edit-skill.md`), but the workflow itself stays in the skill — an agent that reads a self-contained command may skip the skill and miss context.

## Line budgets

| Kind | Target |
|-|-|
| Pure pointer | 5–8 |
| Pointer + orienting steps | 13–40 |
| Anything over 60 | move content into the skill |

## Rules

- MUST contain the pointer phrase: `Invoke the <skill> skill, then read <sub-file>` (or `See SKILL.md § <section>`). This is how the command → skill jump stays discoverable, and how a wrapper's "§ section" reference resolves.
- Don't duplicate skill content — it diverges.
- Add a wrapper only for a genuinely new entry point. Most operations are skill sub-sections with no wrapper.

When done, run `validate.md`.

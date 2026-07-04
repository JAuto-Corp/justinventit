---
name: workflow
description: "Meta-skill for editing the framework itself — skills, hooks, commands, rules, CLAUDE.md. Use before changing anything under .claude/ or the routing docs, so the change keeps the system's shape (lazy-load, forge markers, hook auto-discovery, harness)."
---

# Workflow (Self-Edit Meta-Skill)

This is how the framework safely edits ITSELF. Every artifact under `.claude/` (skills, hooks, commands, rules) and the `CLAUDE.md` router follows a shape the runtime depends on. Editing one blindly breaks discovery, enforcement, or `copier update`. Read the matching operation before you touch it.

> Route, don't dump. Load on demand. Enforce, don't suggest. A system artifact earns its tokens — keep every layer lean and let the layer below hold the detail. (`docs/ARCHITECTURE.md` § Design Principles.)

## Operations

Only `edit-skill` has a command wrapper; the rest are sub-operations you reach by reading this skill. Do NOT add new wrappers.

| Operation | When | Sub-file |
|-|-|-|
| Add / edit a skill | New capability or changed workflow knowledge | `skill.md` |
| Add / edit a command | New or changed slash-command entry point | `command.md` |
| Add / edit a hook | New/changed guard, stop check, or action | `hook.md` |
| Edit a rule | Path-scoped domain guidance | `rule.md` |
| Edit CLAUDE.md | The session router | `claude-md.md` |
| Validate a change | Before committing any of the above | `validate.md` |

## System map (what the runtime depends on)

| Layer | Location | Contract |
|-|-|-|
| Router | `CLAUDE.md` (< 200 lines) | Copier-managed content lives between `<!-- forge:start -->` / `<!-- forge:end -->`; edits OUTSIDE the markers survive `copier update`. Source: `CLAUDE.md.jinja`. |
| Skills | `.claude/skills/**/SKILL.md` | Lazy-loaded: only frontmatter (`name`, `description`) enters context at session start; the full body loads on invocation. Router SKILL.md + lean sub-files. |
| Commands | `.claude/commands/<domain>/<name>.md` | Auto-discovered by path → slash command. Thin pointer into a skill. |
| Rules | `.claude/rules/*.md` | Frontmatter `paths: [...]` globs; load only when Claude touches a matching file. Project-owned. |
| Hooks | `.claude/hooks/` | Stop `stop/checks/[0-9]*.sh` + `stop/actions/*.sh` are auto-discovered by `stop/runner.sh` (checks run in order, exit ≠0 blocks; actions never block). PreToolUse `guards/*.sh` are NOT auto-discovered — register them in `settings.json`. |
| Tests | `.claude/hooks/tests/` | `harness.sh` drives a hook with no live session; suites are `test-*.sh`; `run-all.sh` aggregates them. |

**Copier suffix**: a template file rendered with answer variables ends in `.jinja` (stripped on generation); a generic file is copied verbatim. Match the neighbor you are editing.

## /workflow:edit-skill

The general self-edit workflow. The `/workflow:edit-skill` command routes here; despite the name it covers ANY system artifact — skill, hook, command, rule, or `CLAUDE.md`.

1. **Identify the artifact** and read it *in full*, plus one sibling as a shape reference. Meta-work rewards full context — read before editing.
2. **Pick the operation** from the table above and read its sub-file.
3. **Edit, preserving shape** — keep the frontmatter contract, the router-then-sub-file split, and the line budgets. Content lives in the lowest layer that can hold it; higher layers only point.
4. **Validate** — run the `validate.md` checklist. A hook change also needs a harness test (`hook.md`).
5. **Record it** in the state chain (`context/WORKING.md`) like any other change.

For skill-specific structure and line budgets, read `skill.md`.

## Add or edit a command

Thin pointers only — a command reads its skill; it does not embed the workflow. Commands are auto-discovered by path, so a new file IS a new slash command; don't add one unless a genuinely new entry point is needed. Full patterns: `command.md`.

## Add or edit a hook

A guard (PreToolUse), a stop check, or a stop action. Stop checks/actions are auto-discovered by `stop/runner.sh`; guards must be registered in `settings.json`. EVERY hook change ships with a harness test (`test-*.sh`) and a green `run-all.sh`. Full workflow: `hook.md`.

## Edit a rule

Path-scoped guidance that loads only for files matching its `paths:` globs — cheaper than CLAUDE.md for anything not universal. Full patterns: `rule.md`.

## Edit CLAUDE.md

The router every session reads. Stay under 200 lines; framework content goes between the forge markers (in `CLAUDE.md.jinja`), project content outside them. Full guidance: `claude-md.md`.

## Validate a change

Before committing any system edit: frontmatter intact, line budgets met, pointers resolve, hooks have passing harness tests, `CLAUDE.md` under budget. Full checklist: `validate.md`.

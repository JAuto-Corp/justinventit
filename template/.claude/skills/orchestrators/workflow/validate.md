---
name: workflow/validate
description: Validation checklist for any framework self-edit — run before committing a change to a skill, command, hook, rule, or CLAUDE.md.
---

# Validate a Change

Run the checklist for the artifact you touched before you commit. A system edit that breaks a contract is invisible until it silently stops enforcing or routing.

## Every artifact

- [ ] Frontmatter intact and well-formed (`name`/`description` for skills, `description` for commands, `paths` for rules).
- [ ] Line budget met (see the artifact's sub-file).
- [ ] Pointers resolve — every referenced file/section actually exists. In particular, a command's `§ section` reference must match a real `## heading` in the target SKILL.md.
- [ ] No content duplicated from a lower layer — higher layers point, they don't copy.

## Skill

- [ ] Router carries a one-line intent per operation and points to the sub-file for the full workflow.
- [ ] Directory name matches `name`.

## Command

- [ ] Contains the pointer phrase into its skill.
- [ ] Path is correct — the file location IS the slash-command name.

## Hook

- [ ] Correct kind/location (guard → `guards/` + `settings.json`; stop check → `stop/checks/NN-*.sh`; stop action → `stop/actions/*.sh`).
- [ ] A `test-*.sh` covers both the block and the allow/pass path.
- [ ] `bash .claude/hooks/tests/run-all.sh` is green.

## Rule

- [ ] `paths` globs scope it to the intended file class only.

## CLAUDE.md

- [ ] Under 200 lines.
- [ ] Framework edits went into `CLAUDE.md.jinja` between the forge markers; project edits went outside them.

Then record the change in `context/WORKING.md` and commit.

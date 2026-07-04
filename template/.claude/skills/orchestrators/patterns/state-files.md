---
name: patterns/state-files
description: State-chain file conventions — how work survives session boundaries and context resets.
---

# State File Conventions

The state chain lets a fresh agent resume exactly where the last one stopped.

| File | Purpose | Updated by |
|-|-|-|
| `docs/CURRENT_WORK.md` | Active epic/sprint/phase pointer (+ SPEC path) | start, sprint, handoff, done |
| `context/WORKING.md` | Append-only session observation blocks | every session |
| Phase `PROGRESS.md` | Implementation checklist | during work, at handoff |

**Read order**: `CURRENT_WORK.md` → `WORKING.md` (latest block) → `SPEC.md` → `PROGRESS.md`.

The `SessionStart` hook injects the `CURRENT_WORK.md` active pointer and the last `WORKING.md` block automatically, so keep both current.

---

## CURRENT_WORK.md

One pointer at the active work. Update it when the phase or sprint changes, not every session.

```markdown
## Active Work

**Epic**: #N — [title]
**Sprint**: [path]
**Phase**: [path]
**SPEC**: [path to the active phase SPEC]
**Status**: [In Progress / Phase Complete / Sprint Complete]
**Branch**: [branch name]
```

Keep the `## Active` heading — the SessionStart hook reads that block.

---

## WORKING.md (append-only)

Never rewrite prior blocks — append a new one each session. The heading must start `## ` + a timestamp; the hook surfaces the last such block.

```markdown
## [timestamp]
Phase: [path or milestone]
Completed: [what you finished]
Next: [immediate next task — goal / key files / how to validate]
Blockers: [none, or description — capture also records blockers here]
Friction: [any [FRICTION:*] signals emitted this session]
```

---

## PROGRESS.md (per phase)

```markdown
# Phase P: [title] — Progress

- [ ] Item 1
- [x] Item 2 (done)
```

Check items off **immediately** when complete — never batch. When every box is checked, the phase is ready for `/verify:phase`.

---

## Update rules

1. `CURRENT_WORK.md` — on phase/sprint change.
2. `WORKING.md` — every session; always fill "Next".
3. `PROGRESS.md` — check off as you go; commits are the durable checkpoint alongside it.

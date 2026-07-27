---
description: Plan and design work before building — orient, equip, produce SPEC/SCENARIOS/PROGRESS, converge the plan.
---

# /scope

Read the `scope` skill and execute the planning front of the plan → build → verify chain.

**Steps**:
1. **Orient** — read `context/CHAIN.json` first (a `ready_for == "scope"` state means you're resuming a convergence loop), then `docs/CURRENT_WORK.md`, `context/WORKING.md`, `docs/ROADMAP.md` and the issue
2. Classify the scope objectively against `CLAUDE.md` § TDD Gate — Quick vs. Standard+ decides how much planning is warranted
3. **Equip** — load the planning procedure for the size of the work (`work:epic-plan` for an epic, the `work` skill's sprint shape for a phase) plus any matching domain skills
4. **Act** — author `SPEC.md` / `SCENARIOS.md` / `PROGRESS.md` for the phase; scenarios must exist before any code (the stop check `checks/01-tdd-gate` blocks Standard+ scope without them)
5. Run the grounding self-check, then converge Standard+ plans through the audit loop before handing to `/work`

> `/scope` orchestrates the existing planning pieces — it does not reimplement them.

See **SKILL.md § Phase 3: Act** for full details, and **converge.md** for the plan-convergence loop.

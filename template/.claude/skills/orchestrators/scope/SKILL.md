---
name: scope
description: "Plan and design work before building. Invoke when starting an epic, scoping a sprint, or planning any Standard+ change: orient on what exists, equip the planning procedure + domain skills, then produce the SPEC/SCENARIOS/PROGRESS structure and converge it through an audit loop. Feeds /work:epic-plan and the ATDD entry gate."
---

# Scope — Plan and Design Work

**Intent**: understand what needs building, then produce plan artifacts solid enough to hand to `/work`.

**Flow**: Orient → Equip → Act. Finish each phase before the next.

`/scope` is the *planning* front of the plan → build → verify chain. It doesn't reimplement planning — it orchestrates the existing pieces (`work:epic-plan`, the ATDD gate, the `patterns` interview) and, for Standard+ work, converges the plan through an audit loop before any code is written.

---

## Phase 1: Orient

**STEP 0 — chain state.** Read the `chain` skill (`schema.md` § Reading state) and `context/CHAIN.json`. If `chain.ready_for == "scope"` you're RESUMING a plan-convergence loop → jump to Phase 3's loop with the saved iteration/tier. Terminal / stale / branch-mismatch handling: per `schema.md`.

Then read, to know what exists and where this fits:

| Read | Learn |
|-|-|
| `docs/CURRENT_WORK.md` · `context/WORKING.md` | What's already in flight — don't plan over active work |
| `docs/ROADMAP.md` | Where this work sits in the bigger picture |
| The issue/epic (`gh issue view N`) | Scope, constraints, acceptance criteria |
| Existing plans under `docs/` | Patterns to follow for structure |
| `CLAUDE.md` § TDD Gate | **Scope classification** — decides how much planning is needed |

**Scope classification is objective — do not self-classify.** Apply `CLAUDE.md` § TDD Gate (mirrored in the `work` skill): new tables/routes/pages or 4+ files → Standard+; single-file, no new surface → Quick.

**Refactor awareness**: note messiness in the code this work will touch — competing abstractions, dead code, pattern drift. These are refactor targets to *bundle into the plan*, not separate debt. A plan is the cheapest place to decide what to clean up.

---

## Phase 2: Equip

| Load | When | Why |
|-|-|-|
| `Skill(skill: "work:epic-plan")` | Epic (3+ sprints) | The full planning procedure — explorer waves, folder tree, state-chain updates |
| `work` skill § scope + PROGRESS | Single sprint/phase | Sprint-level planning shape |
| Matching skill(s) in `.claude/skills/domain/` | The work touches that domain | SPECs written without domain conventions drift — wrong names, missing constraints |
| `patterns` skill § Interview | Outcomes the code can't answer | Structured Q&A before writing the SPEC |
| `team-lead` | Parallel explorer/audit waves | Spawn templates, file ownership |

**Quick scope** (1-3 files, no new surface): skip Phase 2 — domain skills load too much context for a small fix.

---

## Phase 3: Act

Pick the approach for the scope, then execute:

| Situation | Approach |
|-|-|
| New epic | Run the `work:epic-plan` workflow you loaded |
| Single phase in a planned epic | Author its `SPEC.md` / `SCENARIOS.md` / `PROGRESS.md` |
| Quick scope | No formal plan — assess and start |
| Investigation / research | Deploy explorers (`patterns` § Multi-Explorer), report findings |

**Output shape** (Standard+): each phase gets `SPEC.md` (acceptance criteria + exit landmarks), `SCENARIOS.md` (the ATDD contract — must exist before any code; the stop check `checks/01-tdd-gate` blocks Standard+ scope with no scenarios), and `PROGRESS.md` (implementation checklist). This is the entry gate `/work` inherits.

**If scope isn't clear**: ask one focusing question. Ten seconds saves thirty minutes of wrong-direction work.

### Grounding self-check (before the audit loop)

Cheap pass over every SPEC authored this round, catching the drift an audit would otherwise burn cycles on:

1. **Named things exist.** Every function/route/type/table the SPEC cites: grep the codebase. Present → ok. Absent but declared in this SPEC's own scope → ok (new surface). Absent and undeclared → hallucination; remove it or expand scope. Don't write names from memory.
2. **Numbers are sourced.** Every numeric fact (cutoffs, thresholds, counts) cites its source inline, or the SPEC is rewritten range-tolerant / to read the value dynamically. Unsourced literals are the highest-risk drift.
3. **Consumer claims are concrete.** Every "consumed by X / downstream reads Y" names the consumer file, or is rewritten as forward-compat. Don't claim a reader that doesn't exist yet.

Clean → enter the audit loop. Issues → fix the SPEC, re-check, then enter.

### Plan-convergence loop (Standard+)

After the plan docs are written, converge them through escalating audit rounds — revise the plan between rounds, don't just re-run the audit. Tier ladder, exit rules, and chain I/O: **`converge.md`**. Skip only if the user says "just plan this, skip the audit" — record the skip in `context/WORKING.md` so the next agent knows.

---

## Related

- Plan-convergence loop: `converge.md`
- Convergence machinery: `chain` skill
- Executing the plan: `work` skill (`/work:continue`)
- Verifying the built result: `check` skill

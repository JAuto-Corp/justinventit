---
name: scope/converge
description: Plan-convergence loop — escalating plan audits, revise-between-rounds, chain I/O for /scope.
---

# Plan-Convergence Loop

For Standard+ plans, after the initial docs are written, converge them before handing to `/work`. Mechanics are the shared `chain` machinery (`chain` skill § `convergence.md`) — this file only names `/scope`'s tier ladder and the revise step.

## Tier ladder

Climb only when progress stalls (per the decision function in `chain/convergence.md`). `min_iterations` (default 2) means run at least tiers 0 and 1 even if round 1 is clean — a plan that passes its first audit is usually under-audited.

| Index | Tier | Deploy | Finds |
|-|-|-|-|
| 0 | plan-review | `patterns` § Multi-Explorer (via `team-lead` for parallel waves) — one explorer each for feasibility, scope/sequencing, devil's-advocate, doc-coherence | Missing ACs, infeasible ordering, over/under-scoped phases |
| 1 | cross-layer | `Skill(skill: "verify:feature")` scoped to the planned surface | Incoherence across the layers the change spans (UI/API/DB/etc.) |
| 2 | collision | `Skill(skill: "verify:feature")` vs. other active plans | Files this plan touches that another in-flight plan also touches — surface as coordination signals, not just findings |
| 3 | multi-perspective (terminal) | `Skill(skill: "verify:audit")` | Last-resort wider audit before human escalation |

The self-loop is `scope → scope`: `/scope` is both auditor and reviser. It owns the iteration counter (`chain.iteration`).

## Each round

1. Read caps + tier from `context/CHAIN.json` (defaults in `chain` SKILL.md § Config).
2. Set `chain.in_progress = true`, run the tier's audit, collect findings into the shape in `chain/schema.md`.
3. Compute `weighted_severity_score`, `findings_hash`, `progress_delta` (`chain/convergence.md`).
4. **Revise the plan** — edit SPEC ACs for gaps, restructure phase boundaries if the audit said so, absorb refactor opportunities the audit surfaced, update `PROGRESS.md`. Revising the docs is the point; re-running the audit without revising wastes the round.
5. Apply the exit/escalate/continue decision, write `context/CHAIN.json`: append the round to `levers.scope.iterations[]`, update `levers.scope.plan_paths[]`, set `chain.verdict` and `chain.ready_for` (`work` on pass, `scope` on continue, `human` on terminal), clear `in_progress`.

## Exit

- **Converged** (`findings == 0` and `iteration >= min_iterations`): `verdict = pass`, `ready_for = work`. The plan is ready to build. Announce round count + final tier.
- **Terminal** (hard_cap, or stall/regression at the top tier): write the escalation report (`chain/convergence.md` § Exit) and surface it. Don't silently re-loop.

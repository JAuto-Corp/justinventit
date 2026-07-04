---
name: check/converge
description: Verify-convergence loop — escalating audit tiers, relay remediation to /work, chain I/O for /check.
---

# Verify-Convergence Loop

Drive a body of work to a clean verdict. Mechanics are the shared `chain` machinery (`chain` skill § `convergence.md`) — this file names `/check`'s tier ladder and the relay to `/work`.

## The relay

`check → work → check`. `/check` finds and scores; `/work` (`/work:continue`) remediates; `/check` re-verifies next round. **`/check` owns `chain.iteration`** — `/work` reads it and writes it back unchanged, so caps count rounds of findings, not relay hops.

## Tier ladder

Climb only when progress stalls (decision function in `chain/convergence.md`).

| Index | Tier | Deploy | When |
|-|-|-|-|
| 0 | standard | `Skill(skill: "verify:recent")` / `verify:phase` | First rounds, or still making good progress |
| 1 | cross-layer | `Skill(skill: "verify:feature")` | Slow burn at tier 0 — trace coherence across layers |
| 2 | multi-perspective | `Skill(skill: "verify:audit")` | Wider cross-cutting audit (parallel explorers) |
| 3 | adversarial-wave (terminal) | `team-lead` — parallel adversarial review waves | Last resort before human escalation |

## Each round

1. Read caps + tier from `context/CHAIN.json` (defaults in `chain` SKILL.md § Config). Set `chain.in_progress = true`.
2. Run the tier's audit over the changed surface. Cross-reference any matching `.claude/skills/domain/` skills against the findings — explorers can't load skills, so you do it.
3. Collect findings in the shape from `chain/schema.md`. Set each finding's `category` to the domain best-practices skill name when one applies — that drives `/work`'s equip on the next round.
4. Compute `weighted_severity_score`, `findings_hash`, `domains_with_findings`, `progress_delta` (`chain/convergence.md`).
5. Apply the exit/escalate/continue decision. Write `context/CHAIN.json`: append to `levers.check.iterations[]`, set `current_findings`/`current_findings_hash`/`domains_with_findings`, set `chain.verdict` and `chain.ready_for` (`work` to remediate, `done` on pass, `human` on terminal), clear `in_progress`.

## Equip feedback

`domains_with_findings` is the signal to `/work`: its next remediation round loads exactly those domain skills before touching code (`chain/schema.md` § Equip feedback loop). This is how `/check` teaches `/work` which conventions it keeps missing.

## Exit

- **Converged** (`findings == 0` and `iteration >= min_iterations`): `verdict = pass`, `ready_for = done`. If this was the final check for the unit of work, do the handoff per the project's Git Workflow — push the branch and open a PR whose body references the convergence history (rounds, findings resolved, final tier). Don't self-merge; that's the reviewer's call.
- **Terminal** (hard_cap, or stall/regression at the top tier): write the escalation report (`chain/convergence.md` § Exit) with the full iteration history and surviving findings, and surface it. Never silently re-loop.

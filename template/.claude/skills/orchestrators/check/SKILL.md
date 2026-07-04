---
name: check
description: "Orchestrate verification ACROSS a chain of work — the multi-round, multi-tier audit loop that drives findings to zero. Distinct from /verify:complete (one phase's exit gate): /check escalates verify:* tiers and relays remediation to /work until a sprint/epic/change converges clean. Invoke to converge-verify a body of work, not to gate a single phase."
---

# Check — Converge Verification Across a Chain

**Intent**: take a body of work that spans phases (a sprint, an epic, a remediation chain) and drive it to a clean verdict through escalating audit rounds.

**Flow**: Orient → Equip → Act. Finish each phase before the next.

## /check vs. /verify:complete

Don't confuse them — they sit at different altitudes:

| | `/verify:complete` | `/check` |
|-|-|-|
| Scope | One phase | A chain — sprint / epic / remediation loop |
| Shape | A gate, run once, produces stop-hook evidence | A loop — audit → `/work` remediates → re-audit |
| Ends when | Every SPEC line met, scenarios pass | Findings converge to zero, or escalate to human |

`/verify:complete` is the exit gate `/work:done` calls. `/check` is the orchestrator that keeps invoking `verify:*` commands at escalating tiers, relaying findings to `/work`, until the whole surface is clean. They compose: a `/check` round may *use* `verify:complete` as one tier.

---

## Phase 1: Orient

**STEP 0 — chain state.** Read the `chain` skill (`schema.md` § Reading state) and `context/CHAIN.json`. If `chain.ready_for == "check"` you're RESUMING a verify-convergence loop → increment `chain.iteration`, note `current_tier_index` (the tier to load) and `levers.work.last_unit.remediated_finding_ids` (what `/work` claims it fixed), and go to Phase 3's loop. Terminal / stale / mismatch: per `schema.md`.

Then read, to know what to check:

| Read | Learn |
|-|-|
| `docs/CURRENT_WORK.md` · `context/WORKING.md` | What stage the work is at |
| The relevant `SPEC.md` / `PROGRESS.md` | Acceptance criteria to check against; how far along |
| `git diff --stat` · `git log --oneline` | The changed surface and recent logical units |

After orienting you know: the surface, the domains touched, and whether this is a fresh check or a continuing convergence round.

---

## Phase 2: Equip

**In a convergence loop** (`iteration > 1` or `current_tier_index > 0`): load the skill named by `/check`'s tier ladder at `current_tier_index` — see `converge.md`.

**Fresh check** — pick the `verify:*` command matching the surface:

| Surface | Invoke |
|-|-|
| Last few commits (pre-PR/handoff) | `Skill(skill: "verify:recent")` |
| The current phase | `Skill(skill: "verify:phase")` |
| A named feature across layers | `Skill(skill: "verify:feature")` |
| A whole sprint before merge | `Skill(skill: "verify:sprint")` |
| Wider / cross-cutting concern | `Skill(skill: "verify:audit")` |

**Always also:**

| Load | When |
|-|-|
| Matching skill(s) in `.claude/skills/domain/` | The changed surface touches that domain — explorers can't load skills; you cross-reference their findings |
| `Skill(skill: "e2e")` | Runtime behavior needs proving, not just reading code |
| `team-lead` | The tier calls for parallel adversarial review waves |

---

## Phase 3: Act

Run the verification workflow you equipped. **Audit (reading code for pattern violations) ≠ e2e (executing scenarios for runtime failures)** — a phase needs both; if you need runtime evidence you loaded `e2e` in Phase 2. Report findings with the report template in `verify` skill § `audit.md`.

### Verify-convergence loop

If this is a chain round (driving a body of work to clean, not a one-off audit), run the convergence logic: collect structured findings, compute the metric, apply the exit rules, relay to `/work` for remediation, and re-verify next round. Tier ladder, relay, and chain I/O: **`converge.md`**. The shared math lives in the `chain` skill.

**Non-chain `/check`** (user just wants an audit, no active loop): report findings in the standard template and stop. The user decides what to do with them.

---

## Related

- Verify-convergence loop: `converge.md`
- Convergence machinery: `chain` skill
- Single-phase exit gate: `verify` skill (`/verify:complete`)
- Remediating findings: `work` skill (`/work:continue`)

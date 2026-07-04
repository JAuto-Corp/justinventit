---
name: chain
description: "Convergence-state model for multi-round orchestration loops. Defines context/CHAIN.json — the baton /scope (plan-converge) and /check (verify-converge) pass between rounds: progress metric, tier-ladder climb, stall detection, exit + escalation rules. A reference, not an executor."
---

# Chain — Convergence State

> The output of one round is the structured input to the next. `context/CHAIN.json` is the baton the loop passes forward.

Some work doesn't finish in one pass — a plan gets audited, revised, re-audited; code gets reviewed, remediated, re-reviewed. **Chain** is the shared model those loops converge over. It does NOT do work; it defines the state (`context/CHAIN.json`), the progress math, and the rules for when to iterate, escalate, or exit. `/scope` and `/check` read this skill when they run a convergence loop; each owns its own tier ladder but shares this machinery.

## The levers

| Lever | Loop | Owns iteration counter? |
|-|-|-|
| `scope` | Plan-convergence — audit → revise plan → re-audit | Yes (self-loop) |
| `check` | Verify-convergence — audit → `/work` remediates → re-audit | Yes |
| `work` | Relay participant — remediates findings, does NOT increment | No |

**Only the lever producing new findings increments `chain.iteration`.** The remediator (`/work`) reads the counter and writes it back unchanged — this keeps `hard_cap` counting rounds of *findings*, not relay bounces.

## State file

`context/CHAIN.json` — one per active branch/loop, transient working state that lives alongside `context/WORKING.md`. Schema, entry shapes, and the read/write patterns each phase uses: **`schema.md`**.

## The loop

Every round: run the tier's audit → collect findings → compute the progress metric → apply exit rules → write state. The metric (weighted severity + `progress_delta`), the tier-ladder climb logic, stall detection, and the exit/escalation table all live in **`convergence.md`**. Both `/scope` and `/check` call into that same math; only their tier ladders differ.

Quick shape (full rules in `convergence.md`):

| Signal | Action |
|-|-|
| `findings == 0` and `iteration >= min_iterations` | EXIT — converged |
| `iteration >= hard_cap` | EXIT TERMINAL — human escalation |
| stall (same `findings_hash` twice) | ESCALATE TIER |
| `progress_delta <= threshold` (slow burn / regression) | ESCALATE TIER |
| `progress_delta > threshold` | CONTINUE at current tier |

Tier escalation past the end of a lever's ladder → TERMINAL: write an escalation report and surface it; never silently loop again.

## Config

Knobs are read from an optional `.claude/chain-config.json` (per-lever `min_iterations`, `soft_cap`, `hard_cap`, `progress_delta_threshold`, `severity_weights`, `tier_ladder`). When that file is absent, use these defaults — do NOT hardcode alternatives in the lever skills:

| Knob | Default |
|-|-|
| `min_iterations` | 2 |
| `soft_cap` | 5 |
| `hard_cap` | 8 |
| `progress_delta_threshold` | 0.3 |
| `severity_weights` | critical 8 · high 4 · medium 2 · low 1 |

Keeping knobs in config (not skill prose) makes the loop tunable per project without editing markdown.

## Related

- Schema + read/write patterns: `schema.md`
- Metric, tier climb, exit rules, escalation: `convergence.md`
- Plan-convergence lever: `scope` skill
- Verify-convergence lever: `check` skill
- Remediation relay: `work` skill (`/work:continue`)

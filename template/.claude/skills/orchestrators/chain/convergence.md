---
name: chain/convergence
description: The convergence math — progress metric, tier-ladder climb, stall detection, exit + escalation rules.
---

# Convergence Math

Shared by `/scope` (plan-convergence) and `/check` (verify-convergence). Both run this loop; only their tier ladders differ.

## Progress metric — weighted severity

Each round's findings collapse to one number using the config severity weights (defaults: critical 8 · high 4 · medium 2 · low 1):

```
weighted_severity_score = sum(weight[f.severity] for f in findings)
```

Progress between rounds:

```
progress_delta = (prev.weighted_severity_score - curr.weighted_severity_score)
                 / max(prev.weighted_severity_score, 1)
```

- `1.0` = all severity resolved this round
- `0.0` = no progress
- negative = regression (worse than last round)
- first round has no `prev` → `progress_delta = null`

Threshold (default `0.3`) means: reduced severity by less than 30% → slow burn → go deeper.

## Findings hash — stall detection

Sort findings by `(file, line, category, severity)`, serialize canonically, take the first 8 hex of a SHA-1. If `curr.findings_hash == prev.findings_hash`, the last remediation changed nothing observable → **stall**.

## Decision function (checked in order)

```
findings       = curr.findings_count
progress_delta = compute(prev, curr)   # null on round 1

if findings == 0 and round >= min_iterations:  EXIT  pass    → ready_for = done
if round >= hard_cap:                          EXIT  escalate → ready_for = human (TERMINAL)
if stalled(prev, curr):                        ESCALATE_TIER
if round >= soft_cap and findings > 0:         ESCALATE_TIER
if progress_delta is null:                     CONTINUE_TIER   # round 1 — relay, no delta yet
if progress_delta < 0:                         ESCALATE_TIER   # regression
if progress_delta <= threshold:                ESCALATE_TIER   # slow burn
otherwise:                                      CONTINUE_TIER
```

`min_iterations` (default 2) means a plan/change that passes on its very first audit is almost always under-audited — run at least two rounds before EXIT-pass is honored.

**Edge case:** if `prev.weighted_severity_score == 0` but `curr.findings_count > 0`, treat `progress_delta = null` (fresh findings on re-entry, not a regression) rather than computing a spurious negative delta.

## Tier escalation

On `ESCALATE_TIER`:

- `current_tier_index + 1 >= len(tier_ladder)` → **TERMINAL**: `chain.terminal = true`, `human_escalation_reason = "tier-exhausted"`.
- else → `current_tier_index += 1`, update `current_tier`, set `ready_for` to the relay target (the remediator for `/check`; self for `/scope`), write state, relay.

On `CONTINUE_TIER`: keep `current_tier_index`, relay to the same target.

## Exit + escalation

- **Converged** (`verdict = pass`): the loop's owner does the natural handoff (e.g. `/check` pushes + opens a PR; `/scope` marks the plan ready for work). Announce the round count and final tier.
- **Terminal** (`hard_cap`, or stall/regression at the top tier): set `chain.terminal = true` with the reason (`hard-cap` / `tier-exhausted` / `stall`), write an escalation report to `context/AUDIT_chain_escalation_<timestamp>.md` containing the full iteration history (round · tier · findings · weighted score · progress_delta), surviving findings with `file:line` and the rounds they appeared in, the termination reason, and a recommended next step. Surface it to the user in conversation — never silently loop again.

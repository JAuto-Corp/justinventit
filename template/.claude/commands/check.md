---
description: Converge verification across a chain of work — escalating audit tiers, relay remediation to /work, drive findings to zero.
---

# /check

Read the `check` skill and run the verify-convergence loop over a body of work.

**Steps**:
1. **Orient** — read `context/CHAIN.json` first (a `ready_for == "check"` state means you're resuming: increment `chain.iteration` and note the tier to load), then establish what surface is under audit
2. **Equip** — load the skill named by `/check`'s tier ladder at `current_tier_index`
3. **Act** — run the tier's audit, collect structured findings in the `chain/schema.md` shape, and set each finding's `category` to the domain skill that applies
4. Compute the progress metric, apply the exit rules, and either relay to `/work` for remediation or exit converged
5. On a one-off audit with no active chain, report findings in the standard template and stop — the user decides what happens next

> Distinct from `/verify:complete`, which is a single phase's exit gate. `/check` is the loop that keeps invoking `verify:*` at escalating tiers until the whole surface is clean.

See **SKILL.md § Phase 3: Act** for full details, and **converge.md** for the tier ladder and the relay to `/work`.

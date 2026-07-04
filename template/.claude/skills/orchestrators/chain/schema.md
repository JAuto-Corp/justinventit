---
name: chain/schema
description: context/CHAIN.json schema, entry shapes, and the read/write patterns each phase uses.
---

# CHAIN.json Schema

Transient working state at `context/CHAIN.json`, alongside `context/WORKING.md`. One `chain.*` block (the active loop) plus a per-lever `levers.*` block holding that lever's round history.

```json
{
  "schema_version": 1,
  "updated_at": "2026-01-01T00:00:00Z",
  "branch": "feature/example",
  "chain": {
    "active_loop": "check",
    "last_lever": "check",
    "verdict": "iterate",
    "ready_for": "work",
    "current_tier": "standard",
    "current_tier_index": 0,
    "iteration": 1,
    "in_progress": false,
    "terminal": false,
    "human_escalation_reason": null
  },
  "equip_loaded": [],
  "levers": {
    "scope": { "iterations": [], "plan_paths": [], "ready_for_next": false },
    "work":  { "last_unit": { "files": [], "remediated_finding_ids": [] } },
    "check": { "iterations": [], "current_findings": [], "current_findings_hash": null, "domains_with_findings": [] }
  }
}
```

`ready_for` names the next lever (`scope` / `work` / `check`), or `done` on a clean pass, or `human` on terminal escalation.

### Iteration entry (ring buffer — keep last 8)

```json
{
  "round": 1,
  "tier_name": "standard",
  "tier_index": 0,
  "skill_invoked": "verify:recent",
  "findings_count": 7,
  "weighted_severity_score": 23,
  "findings_hash": "a3f9c8b1",
  "domains_with_findings": ["<domain-skill-name>"],
  "progress_delta": null
}
```

### Finding entry

```json
{
  "id": "f1",
  "file": "path/to/file",
  "line": 142,
  "severity": "high",
  "category": "<domain-skill-name>",
  "message": "what's wrong",
  "suggested_action": "how to fix",
  "introduced_round": 1,
  "resolved_round": null
}
```

`category` should be the name of a domain best-practices skill (`.claude/skills/domain/`) when one applies — that's what drives the equip feedback loop (below).

## Reading state (each lever's Phase 1, FIRST step)

1. Read `context/CHAIN.json`. Missing → fresh loop, continue Phase 1 normally.
2. `updated_at` age > 24h → STALE → reset the `chain.*` block (preserve `levers.*.iterations`), continue fresh.
3. `branch` != current branch → MISMATCH → full reset.
4. `chain.terminal == true` → surface the pending escalation, do NOT start a round.
5. `chain.in_progress == true` → a prior round was interrupted → resume or abandon its last iteration.
6. `chain.ready_for == this lever` → RESUME → jump to the lever's convergence phase with state loaded.
7. `chain.ready_for` is a different lever → nudge the user about the pending lever unless they invoked out of order deliberately.

## Writing state (each lever's Phase 3, LAST step)

Atomic full-file write — read, mutate, write the whole object; never partial. Set `chain.in_progress = true` before long-running audit work and `false` on completion. Update `last_lever`, `verdict`, `ready_for`, `iteration`/tier (if this lever owns them), `updated_at`, and append the round to `levers.<self>.iterations[]`.

## Equip feedback loop

When `/check` reports `domains_with_findings`, the next `/work` remediation round loads those domain skills before touching code: `needed = domains_with_findings − equip_loaded`, invoke each, append to `equip_loaded`. This is how the verifier teaches the remediator which best-practices it keeps missing.

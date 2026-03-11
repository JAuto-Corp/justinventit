---
name: verify
description: "Verification and auditing. Run tests, check acceptance criteria, deploy multi-perspective audits, and validate phase/sprint completion."
---

# Verification

## Commands

| Command | Purpose |
|-|-|
| `/verify:complete` | Full phase validation (exit gate) |
| `/verify:phase` | Audit current phase for pattern alignment |
| `/verify:sprint` | Audit entire sprint before merging |
| `/verify:file` | Audit specific file(s) |
| `/verify:feature` | Audit named feature across codebase |
| `/verify:recent` | Audit last 5 commits |
| `/verify:audit` | Deploy multi-perspective audit |

## /verify:complete — Exit Gate

Steps (all required for Standard+ scope):

1. **SCENARIOS.md checked** — all scenarios have evidence (screenshots, logs)
2. **SPEC.md user stories** — each implemented or explicitly deferred
3. **Multi-perspective audit** — deploy explorers for Frontend, Backend, Coherence
4. **Domain skill cross-reference** — invoke relevant best-practices skills, resolve violations
5. **Type check** — zero errors
6. **Build** — success
7. **State files updated** — PROGRESS.md, CURRENT_WORK.md, WORKING.md
8. **Issues closed** — referenced issues closed with comments

Both audit AND E2E are required. Audit validates code looks correct. E2E validates code works.

## Friction Signals

If verification reveals:
- Skill was wrong about a pattern → `[FRICTION:SKILL] skill-name: description`
- Hook blocked incorrectly → `[FRICTION:HOOK] hook-name: description`
- Workflow step was unnecessary → `[FRICTION:WORKFLOW] description`

These signals are extracted by the stop hook and logged to `context/FRICTION_LOG.md`.

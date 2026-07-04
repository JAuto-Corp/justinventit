---
name: verify
description: "Verification and auditing. Validate acceptance scenarios, run multi-perspective audits, check type-check/build evidence, and gate phase/sprint completion."
---

# Verification

Prove work does what the SPEC said, then gate the phase/sprint. `/verify:complete` is the exit gate `/work:done` calls — it PRODUCES the evidence the stop hooks look for (`checks/03-scenario-evidence`, `04-tdd-cycle`, `05-progress-evidence`) when you signal `[PHASE_COMPLETE]`. The other commands are lighter, on-demand audits over a chosen surface.

> Audit validates code *looks* correct. Scenario evidence validates code *works*. A phase needs both. Walk the SPEC line-by-line — never aggregate a "looks done" verdict.

## Commands

| Command | Purpose | Workflow |
|-|-|-|
| `/verify:complete` | Full phase validation — the exit gate | `complete.md` |
| `/verify:phase` | Light audit of the current phase | `phase.md` |
| `/verify:sprint` | Audit an entire sprint before merge | `sprint.md` |
| `/verify:file` | Audit specific file(s) + their callers | `file.md` |
| `/verify:feature` | Audit a named feature across the codebase | `feature.md` |
| `/verify:audit` | Deploy a multi-perspective audit (the engine) | `audit.md` |
| `/verify:recent` | Audit the last few commits | `recent.md` |

## Shared foundations

**State chain** (read in order — see `CLAUDE.md` § Session State Management): `docs/CURRENT_WORK.md` → `context/WORKING.md` → phase `SPEC.md` / `SCENARIOS.md` / `PROGRESS.md`.

**Configured commands**: reference the project's type-check and build commands abstractly — read `type_check_command` / `build_command` from `.copier-answers.yml`, or `CLAUDE.md` § Essential Commands. Never hardcode a stack's tooling.

**Multi-perspective audit**: every audit command deploys parallel Explore agents (see the `patterns` skill § Multi-Explorer Pattern) — one per perspective that applies to the changed surface, each returning a bounded (<2000 char) summary. Explorers cannot load skills; after they report, YOU invoke the project's matching best-practices skill(s) (`.claude/skills/domain/`) and cross-reference their findings. The perspective menu and report template live in `audit.md`.

**Coherence rule**: verify code state first (git log, file reads), then update docs/issues — never record from memory alone.

**Friction**: when verification exposes a bad skill/hook/workflow step, emit the matching `[FRICTION:*]` signal (see `patterns` skill § Friction Signals); the stop hook logs it.

---

## /verify:complete

Exit gate for phase completion. Confirm every acceptance scenario has a recorded passing run, walk the SPEC line-by-line into a met/partial/not-met verdict table, run a multi-perspective audit, cross-reference best-practices skills, pass the configured type-check + build, update the state chain, and align docs ↔ issues. Any `partial`/`not-met` row blocks. Only on a clean pass do you check off `PROGRESS.md` and signal `[PHASE_COMPLETE]` — the moment the stop-hook evidence checks fire. Full workflow: `complete.md`.

## /verify:phase

Lighter than `complete` — a targeted audit of the current phase's changed surface for pattern alignment and coherence, ending in a `WORKING.md` phase-transition marker. Use before moving on; use `/verify:complete` for official completion. Full workflow: `phase.md`.

## /verify:sprint

Full validation before marking a sprint complete and merging. Aggregate scenario coverage across the sprint's phases, run a cross-phase audit, confirm each phase passed its exit gate, and block the merge on any unmet criteria. Full workflow: `sprint.md`.

## /verify:file

Targeted audit of specific file(s). Read the target and its immediate dependencies, find its callers, deploy explorers scoped to the file's role, cross-reference the matching best-practices skill, and assess caller impact. Full workflow: `file.md`.

## /verify:feature

Audit a named feature across its full implementation. Discover every participating file, deploy explorers scoped to them, check completeness across every layer the feature touches, and report gaps. Full workflow: `feature.md`.

## /verify:audit

The multi-perspective audit engine the other commands call. Scope the surface, deploy the subset of perspectives that applies, consolidate bounded explorer findings, and cross-reference best-practices skills. Full workflow: `audit.md`.

## /verify:recent

Quick audit of the last few commits before a PR or handoff. Read the recent diffs, categorize the changed files, deploy the applicable perspectives, and report CLEAN / ISSUES. Full workflow: `recent.md`.

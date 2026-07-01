---
description: Full phase validation before marking a phase complete.
---

# /verify:complete

Read the `verify` skill and execute the full phase-completion validation.

**Steps**:
1. Confirm every acceptance-criteria scenario for the phase passes (no unrun scenarios — the stop-gate hard-blocks on missing evidence)
2. Multi-perspective audit of the changed surface
3. Run the project's configured type-check and build commands (see `.copier-answers.yml` / CLAUDE.md for this project's commands)
4. Update the state chain: active phase `PROGRESS.md`, then `context/WORKING.md`
5. Align docs ↔ issues: close completed issues, update `docs/ROADMAP.md`, file issues for deferred work

> **Coherence rule**: verify code state first, then update docs — never update docs from memory alone.

See **SKILL.md § /verify:complete** for full details.

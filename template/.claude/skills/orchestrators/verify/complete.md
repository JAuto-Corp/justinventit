---
name: verify/complete
description: Full phase validation — the exit gate. Produces the evidence the stop hooks check.
---

# /verify:complete

Full validation before a phase is complete. **All steps must pass.** This is the gate `/work:done` invokes; it produces the evidence `checks/03-05` enforce when `[PHASE_COMPLETE]` is signaled.

## Steps

### 1. Scenario evidence (ATDD)

Locate the active phase's `SCENARIOS.md`.
- **Standard+ scope** (new tables/routes/pages, or 4+ files — see `CLAUDE.md` § Scope): FAIL hard if missing.
- **Quick scope**: warn if missing.

If present, verify each scenario has a recorded **RED-then-GREEN** run (seen failing before passing) and its evidence fields (logs/output/screenshots) are filled and passing. This is exactly what stop `checks/03-scenario-evidence` and `04-tdd-cycle` verify — record the runs here so the signal at the end doesn't block.

### 2. SPEC adherence (line-by-line — load-bearing)

Read the **entire** phase `SPEC.md`. Do NOT aggregate. Every numbered/bulleted item under Acceptance Criteria, Exit Landmarks, and each user story gets **one row**:

| SPEC line | Status | Evidence |
|-|-|-|
| [item] | met / partial / not-met / deferred | file:line, commit SHA, query result, scenario name + SHA, or deferral citation |

- **met**: shipped + verifiable evidence. **partial**: name what shipped vs didn't. **not-met**: absent/deferred without citation. **deferred**: allowed only if the row cites the decision (issue # / PR comment).
- **Block rule (non-negotiable)**: if ANY row is `partial` or `not-met`, the verdict is `BLOCKED`, not PASS. Surface the unmet items; don't smuggle partial through prose.

The line-by-line walk exists because an aggregated "looks done" checklist lets an agent self-certify a phase that left exit landmarks unshipped.

### 3. Multi-perspective audit

Deploy the perspectives that apply to the changed surface (see `audit.md`); collect the bounded findings.

### 4. Best-practices cross-reference (gate)

Explorers can't load skills. Invoke each applicable project best-practices skill (`.claude/skills/domain/`), compare the changed surface to its guidelines, and record violations (critical / warning). **Critical violations block.**

### 5. Type-check + build

Run the project's configured `type_check_command` then `build_command` (see `.copier-answers.yml` / `CLAUDE.md` § Essential Commands). Both must pass with zero errors.

### 6. State files

Check off every item in the phase `PROGRESS.md` (backed by real commits — `check/05` blocks bare checkoffs), append a verification block to `context/WORKING.md`, and record the phase-transition in `docs/CURRENT_WORK.md`.

### 7. Docs ↔ issues

Verify code state first, then close completed issues (`gh issue close N --comment ...`), update the roadmap, and file issues for any deferred work.

## Output + signal

```markdown
## Phase Validation: [phase] — [date]
| Step | Status | Notes |
|-|-|-|
| 1. Scenarios | PASS/WARN | X/Y passing |
| 2. SPEC adherence | PASS/BLOCKED | n met / m partial / k not-met / d deferred |
| 3. Audit | PASS | perspectives deployed |
| 4. Best-practices | PASS | skills checked / N/A |
| 5. Type-check + build | PASS | 0 errors |
| 6. State files | PASS | PROGRESS/WORKING/CURRENT_WORK updated |
| 7. Docs ↔ issues | PASS | #X, #Y closed |

### Phase Status: COMPLETE   (or: BLOCKED — <blocking items>)
```

Only when every row is PASS/met and `PROGRESS.md` is fully checked do you signal `[PHASE_COMPLETE]`. If any step is BLOCKED, do NOT signal — fix or escalate first. For a legitimate exception (manual-only testing, a code-free phase), the stop checks accept an `[EVIDENCE_OVERRIDE:<reason>]` signal instead — use it honestly, not to bypass real gaps.

## Related

- Audit engine + report template: `audit.md`
- Caller of this gate: `work` skill § /work:done

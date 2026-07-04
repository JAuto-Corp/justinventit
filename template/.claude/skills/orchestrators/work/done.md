---
name: work/done
description: Verify completion, close the issue, clear state, and open the PR.
---

# /work:done #N

Close out verified work and clear the active state.

## Workflow

### 1. Verify completion (exit gate)

Confirm acceptance criteria are met, `PROGRESS.md` is fully checked, and tests pass. Run `/verify:complete` as the exit gate. Before any `[PHASE_COMPLETE]` signal, the stop hooks enforce the evidence:

- `checks/03-scenario-evidence.sh` — every scenario has a recorded passing run.
- `checks/04-tdd-cycle.sh` — each scenario was seen RED before GREEN.
- `checks/05-progress-evidence.sh` — no unchecked required items, and checkoffs are backed by commits.

If any exit landmark is partial or not-met, do NOT close — fix or escalate first. Walk the SPEC line-by-line; never aggregate a "looks done" verdict.

### 2. Code review (Standard+)

Run a review over the changed files before the final commit — it catches pattern drift, duplication, and efficiency issues tests miss. Fix high/medium findings. Skip for Quick scope.

```bash
git diff --name-only <base>...HEAD
```

### 3. Final commit

```bash
git add -A
git commit -m "feat(#N): [description]

Closes #N"
```

### 4. Close the issue

```bash
gh issue close N --comment "Completed. See commits on branch feature/issue-N-*"
```

### 5. Align docs with reality

Confirm `git status` is clean; update `docs/CURRENT_WORK.md` / roadmap if this closed active work; verify issue labels match completion; file follow-up issues for any deferred work discovered.

### 6. Clear state

Remove the issue from `context/WORKING.md`'s immediate-next-task and reset the `docs/CURRENT_WORK.md` pointer.

### 7. Push and open a PR

Per the project's git workflow (see `CLAUDE.md` § Git Workflow — agents commit freely, humans gate the push/merge):

```bash
git push -u origin feature/issue-N-description
gh pr create --base <integration-branch> --title "..." --body "..."
```

Authoring sessions open PRs; they do not merge their own. Merge is gated by the reviewer/human.

### 8. Advance or stop

If a next phase exists in the sprint → invoke `/work:continue` (it detects the transition). If the sprint is complete → re-verify every phase SPEC, then `/work:sprint`. If the epic is complete → surface to the user. Otherwise stop only for: hard human escalation, or tool/permission denied.

## Related

- Phase/sprint exit gates: `/verify:complete`
- Sprint transition: `sprint.md`

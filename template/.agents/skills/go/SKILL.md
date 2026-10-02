---
name: go
description: Execute work. Invoke when ready to implement or resume an accepted plan. Orient on state, equip the relevant project skills, then act on the next item.
---

# Go — Execute Work

**Intent:** pick up where things left off (or start fresh) and build.

**Flow:** Orient → Equip → Act. Complete each phase before the next.
Runtime routes and project-specific tools: `docs/WORKFLOW_SKILLS.md`.

## Phase 1: Orient

Read the existing `work` skill's `continue.md` procedure at
`.agents/skills/work/continue.md`. It owns resumption and the ATDD entry gate;
`go` is the execution front door for that same workflow.

Read `.claude/skills/orchestrators/chain/schema.md` and `context/CHAIN.json` when
present; apply that schema's terminal, stale and branch-mismatch handling. The
portable chain calls the execution lever `work`, not `go`. When `ready_for` is
`work`, load `levers.check.current_findings` for remediation, or
`levers.scope.plan_paths` for a newly audited plan.

| Read | Learn |
|-|-|
| `docs/CURRENT_WORK.md` | Active epic, sprint and phase |
| `context/WORKING.md` | Last session's observations and immediate next action |
| Active `SPEC.md` and `SCENARIOS.md` | Acceptance criteria and scenarios |
| Active `PROGRESS.md` | Completed and remaining items |
| `AGENTS.md` | Scope classification and project constraints |

Unchecked progress means mid-phase work; fully checked progress means a phase
boundary. With no active state, read the issue/epic and follow `work/start.md`.
For a check-remediation round, use the recorded findings as the work queue.

## Phase 2: Equip

Load the project's installed guidance for the domains the next item touches:
frontend, API, schema, test data or debugging. Use the project's actual skill
names and paths; domain conventions are supplied by the adopter.

When resuming findings, include `levers.check.domains_with_findings` in the
loadout. Before touching a new domain mid-task, load its guidance and update
`equip_loaded` according to the existing `chain` schema. Missing guidance is
reported, never represented as loaded.

Use `team-lead` when the work is parallelizable and delegation is authorized.
For Quick scope, follow the project's lighter procedure in `AGENTS.md`.

## Phase 3: Act

| Situation | Action |
|-|-|
| Continuing mid-phase | Implement the next unchecked progress item |
| Starting a phase | Verify entry landmarks, begin its first item |
| Starting a sprint | Follow `work/sprint.md` |
| Starting an issue | Follow `work/start.md` |
| Phase complete | Run the completion gate through `work/done.md` |

Check off progress as it happens and commit each logical unit. Capture discoveries
outside the current task with `capture`; checkpoint a blocked task with
`work/handoff.md`.

After a chain unit, update `updated_at`, set `chain.last_lever = "work"`,
`chain.ready_for = "check"` and `chain.in_progress = false`. Record changed
`files` and `remediated_finding_ids` in `levers.work.last_unit`, preserving
`chain.iteration` (owned by check). Report the unit, commits and next check.
A direct invocation with no chain skips this relay write.

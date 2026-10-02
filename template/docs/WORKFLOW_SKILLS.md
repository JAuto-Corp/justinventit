# Workflow skills

Edit `.agents/skills/<name>/`; Claude Code uses byte-identical physical copies at
`.claude/skills/<name>/`. The framework's `scripts/generate-skill-surfaces.py`
generates those copies; its `--check` mode checks them without writing. Namespaced
commands are hand-written pointers, not additional procedures.

| Task | Canonical procedure | Claude route | Codex route |
|-|-|-|-|
| Plan | `.agents/skills/scope/SKILL.md` | `/scope` | `$scope` |
| Execute | `.agents/skills/go/SKILL.md` | `/go` | `$go` |
| Verify | `.agents/skills/check/SKILL.md` | `/check` | `$check` |
| Record discoveries | `.agents/skills/capture/SKILL.md` | `/capture` | `$capture` |
| Coordinate | `.agents/skills/team-lead/SKILL.md` | `/team-lead` | `$team-lead` |
| Work lifecycle | `.agents/skills/work/SKILL.md` | `/work` | `$work` |

Work modes: start, continue, pause, handoff, done, epic-plan and sprint. Capture
modes: block, audit, findings, triage and epic. Each mode is the corresponding
Markdown file in its canonical directory. Claude's `/<skill>:<mode>` commands
point there; other runtimes read that file with the requested arguments.

## Project configuration and runtime boundaries

`AGENTS.md`, `docs/DELIVERY.md` and `docs/REVIEW_PRACTICE.md` remain the governing
policy. Existing convergence recipes do not override their review scope or caps.
The project supplies domain guidance, issue labels, branches, repository targets,
service identities and role/model pins. Capture's upstream example requires
`FRAMEWORK_REPOSITORY=owner/repository`; there is no source-project fallback.

`Skill(...)`, `TeamCreate`, `Task`, `Explore`, `SendMessage` and `TaskUpdate` are
Claude syntax in the retained examples. Other runtimes read the named procedure
and use their available tools. A skill does not install a tool, authorize a spawn,
or prove a model/effort pin. No compatible tool or role means report it unavailable
and use the project's existing coordination route. Claude Stop hooks apply only
where installed; another runtime must perform the required checks explicitly.

## Origin and upgrade

Origin: **JA workflow skills, inspected 2026-10-01**, checkout
`bd3e7821473401f93ce23af621849f93a49435ef`, `.claude/skills/` paths named above.
The five existing JV copies at `b5722bab` supply the already generalized bodies;
`go` retains orient/equip/act and delegates to JV's existing `work` lever. The
locally modified source team-lead and its transient context are not copied.

| Retained lesson | Why | Source reference (2026-10-01 inspection) |
|-|-|-|
| Ground names, numbers and consumers before planning | Avoid plans built on invented facts | JA `scope/SKILL.md`, grounding self-check |
| Orient, equip, then execute | Preserve state and load the conventions needed by the next item | JA `go/SKILL.md` and `work/continue.md` |
| Separate audits from execution evidence | Reading does not prove runtime behavior | JA `check/SKILL.md` |
| Capture discoveries and return to current work | Prevent unplanned scope growth | JA `capture/SKILL.md` |
| Disjoint write ownership and one shared-data smoke | Avoid concurrent edits and multiply blocked runners | JA `team-lead/{SKILL,spawn-templates}.md` |
| Durable progress and explicit next action | Recover after context loss | JA `work/{pause,handoff,continue}.md` |
| Readiness is separate from integration; markers are not approval | Prevent premature issue closure and self-authorized bypass | W-D1 F1 ruling, 2026-10-01, `01M3WQYEAS97KDV5YEJ1MHRP3B` |

W-D1 moves the five old `.claude/skills/orchestrators/<name>` directories to the
canonical routes above, removes duplicate bare scope/check commands, and seeds
entry contract version 4. Existing `AGENTS.md` is project-owned: apply the CHANGES
entry's work-path and workflow-index edits manually. Reconcile local edits to old
skills/commands during Copier update; do not discard them. Commit before adoption
and rehearse in a disposable clone. Rollback is the adoption commit's revert.

Pinned reviewers, runtime adapters, additional source work modes and isolation
mechanisms remain separate slices. This extraction's render/route smoke establishes
packaging, not live-model invocation or behavioral parity between runtimes.

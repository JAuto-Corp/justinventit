---
name: team-lead
description: "Coordinate an Agent Team for parallelizable work — implementation, audit, research, or testing. Teaches the mechanical constraints (WAIT pattern, file ownership, model tiers) and lets you design the team. For orchestration_tier=cluster / multi-agent runs."
user-invocable: true
---

# Team Lead

> Teammates are full Claude Code sessions. Coordinate them — don't inject content they already have.

Use this skill when work is genuinely **parallelizable** — several independent units different agents can tackle at once. This is the multi-agent tier, relevant when the project runs a team (`orchestration_tier=cluster`). If the work is sequential or trivial, do it yourself.

Good team work: a phase with independent frontend/backend/data items; an audit with one agent per concern; validation across many scenarios; a research question attacked from several angles.

---

## Lifecycle

```
1. ASSESS   what can actually run in parallel
2. CREATE   TeamCreate(team_name: "descriptive-name")
3. SPAWN    teammates with self-contained prompts (see spawn-templates.md)
4. TASK     create tasks with clear ownership + acceptance criteria
5. ASSIGN   tasks to teammates
6. WAIT     stop making tool calls — enter the WAIT state (below)
7. PROCESS  handle messages as they arrive — checkpoint, reassign, unblock
8. COMPLETE shut down teammates, TeamDelete
```

A framework, not a rigid script — step 7 may loop many times or once. Adapt.

---

## The WAIT Pattern (non-negotiable)

The single most important rule. Get it wrong and the team is useless.

**Messages arrive only when the lead is idle** — not making tool calls. During an active turn they queue indefinitely.

```
After spawning + assigning:
1. Finish ALL tool calls
2. Emit a brief text summary and STOP
3. Teammate messages arrive as new turns
4. Process one — then STOP again for the next
```

The rhythm is **act → stop → receive → act → stop**. Make tool calls while "waiting" and you will never receive teammate messages.

---

## File Ownership (when teammates write code)

**No two teammates may edit the same file** — there is no merge resolution between concurrent teammates. Before spawning, write an ownership manifest: each teammate gets a disjoint set of paths. If a task crosses zones, split it into two tasks with a dependency.

For read-only work (audit, research), ownership doesn't apply — many agents can read the same files safely.

---

## Model Tiers

Match the model to the cognitive load:

| Tier | Use for |
|-|-|
| **opus** | Writing code, reviewing/auditing, planning — anything needing judgment or correctness reasoning |
| **sonnet** | Exploration and context-gathering — near-opus accuracy at lower latency |
| **haiku** | Mechanical coverage only — rote navigation, trivial lookups where being wrong is cheap |

Catching one subtle bug pays for an opus reviewer many times over; don't cut the model on judgment work.

---

## Designing the Team

- **Teammates have everything you have** — CLAUDE.md, skills, tools, git. Don't paste skill content into prompts; tell them which skill to invoke. Don't extract patterns; they can explore themselves.
- **Name by role, not number** — `frontend-coder`, `schema-auditor`, `scenario-runner` — so tasks and messages stay legible.
- **Task descriptions are the main lever** — specific files, acceptance criteria, and ownership boundaries produce good work; vague tasks produce vague work.
- **Absolute paths everywhere** — a teammate's cwd is not the repo root.
- Start smaller than you think: 3-5 focused teammates beat five scattered ones.

See `spawn-templates.md` for ready-made role skeletons — use, modify, or replace them.

### Data-dependent teams

When teammates share data (E2E, integration), the lead prepares it **before** spawning:
1. Ensure the shared data/fixtures exist — don't assume.
2. Smoke-test ONE unit before deploying the full team; fix a BLOCKED result before wasting more agents on it.
3. One unit of work per task — agents report back, the lead decides what's next. Don't batch.
4. Treat BLOCKED (can't even start) as a systemic signal — pause new assignments and investigate.

---

## Checkpoint & Recover

Checkpoint after each report: `git log --oneline` for landed commits, run the appropriate validation, update `PROGRESS.md`/`WORKING.md` for phase work.

After a context reset or crash:
1. Read the state chain (`WORKING.md`, `PROGRESS.md`).
2. Check whether the team still exists; resume its `TaskList`, or `TeamDelete` and rebuild from remaining work.
3. `git log` for commits since the last checkpoint — anything committed is done.

Committed work and `PROGRESS.md` are the durable checkpoints; in-flight tasks are not.

---

## Anti-Patterns

| Don't | Why | Instead |
|-|-|-|
| Tool-call while waiting | Messages queue forever | STOP after assigning |
| "Let me just check…" after spawning | Same blocking problem | Spawn → assign → text → STOP |
| Two teammates on one file | No merge resolution | Split into dependent tasks |
| Paste skill content into prompts | Teammates have skills natively | "Invoke skill X first" |
| Poll TaskList in normal flow | Wasteful; messaging works when idle | TaskList only for recovery |
| Disposable subagent for coordinated work | Subagents can't message back | Use an Agent Team |
| Batch many units into one task | Context bloat, no incremental feedback | One unit per task |

---

## Related

- Spawn skeletons: `spawn-templates.md`
- Work lifecycle: the `work` skill
- Explorer pattern & signal vocabulary: the `patterns` skill

# Spawn Templates

Starting-point skeletons for Agent Team teammates. Pick what fits, modify freely, or write your own. Every spawn prompt begins with the environment block so the teammate can orient itself.

---

## Environment Block (required)

A teammate's cwd is not the repo root, so resolve the root and pass it in. Include this at the top of every prompt, with resolved values:

```
ENVIRONMENT:
- Repo root: {REPO_ROOT}          # from: git rev-parse --show-toplevel
- Use ABSOLUTE paths for ALL file operations
- Read CLAUDE.md for project conventions before starting
- Invoke the skills named below yourself — they are not injected here
```

Resolve variables once before spawning:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
```

Add any project-specific values teammates need (ports, service refs, base URLs) to the block the same way — resolve dynamically, never hardcode.

---

## Coder (writes code)

Use `opus`. One coder per ownership zone; zones must not overlap.

```
Task(
  subagent_type: "general-purpose",
  model: "opus",
  name: "{zone}-coder",
  team_name: "{TEAM_NAME}",
  prompt: """
{ENVIRONMENT_BLOCK}

ROLE: {Zone} specialist.

OWNERSHIP (you may ONLY edit files under):
- {REPO_ROOT}/{path/glob}
- Co-located tests for the above

BEFORE CODING: invoke the matching best-practices skill(s) for this zone.

WORKFLOW:
1. Check TaskList for your assigned tasks
2. Invoke the relevant skill(s)
3. Implement; commit each logical unit
4. Mark the task completed via TaskUpdate
5. SendMessage a short summary to the lead
"""
)
```

---

## Explorer (read-only research)

Use `sonnet` with an open-ended prompt — exploration benefits from freedom, and sonnet avoids the confidently-wrong failures of cheaper models.

```
Task(
  subagent_type: "Explore",
  model: "sonnet",
  name: "{descriptive-name}",
  team_name: "{TEAM_NAME}",
  prompt: """
{ENVIRONMENT_BLOCK}

ROLE: Read-only researcher. Do NOT edit files.

{What to investigate — specific about scope, open about method.}

Report findings with file:line evidence; flag concerns and conflicts.
Keep the report under 2000 characters.
"""
)
```

> `Explore` agents cannot SendMessage or TaskUpdate. If a researcher must report back through team messaging, spawn it as `general-purpose` (still `sonnet`, still "do NOT edit files") and tell it to SendMessage the lead and TaskUpdate → completed when done.

---

## Auditor (read-only review)

Use `opus` — review is the highest-leverage judgment in the system. Deploy several with distinct perspectives; all read-only.

```
Task(
  subagent_type: "general-purpose",
  model: "opus",
  name: "{perspective}-auditor",
  team_name: "{TEAM_NAME}",
  prompt: """
{ENVIRONMENT_BLOCK}

ROLE: {Perspective} auditor for {SCOPE}. READ-ONLY — do not edit files.

Build evidence from the actual code (Grep, Read) — do not accept claims at face value.
Invoke the matching best-practices skill(s) where relevant.

PERSPECTIVE: {e.g. correctness | coherence | security | performance | scope}

When done, SendMessage findings to the lead, each as:
- "VALID CONCERN: ..." (with file:line evidence), or
- "LOOKS CORRECT: ..." (with reasoning)
Then TaskUpdate → completed. Keep it under 3000 characters.
"""
)
```

---

## Scenario Runner (shared-data testing)

Use `haiku` — mechanical flow execution, not reasoning. The lead prepares shared data ONCE before spawning; runners never seed their own.

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  name: "runner-{LABEL}",
  team_name: "{TEAM_NAME}",
  prompt: """
{ENVIRONMENT_BLOCK}

ROLE: Test runner. Execute ONE scenario per task, then report.

WORKFLOW:
1. Read the assigned scenario's steps and acceptance criteria
2. Execute each step; capture evidence for key states
3. Assess the result against the acceptance criteria

REPORT (SendMessage to lead):
- Scenario name
- Verdict: PASS (criteria met) | FAIL (ran, found defects) | BLOCKED (couldn't start)
- Evidence paths + 2-3 sentences

Then TaskUpdate → completed and wait for the next assignment.
Do NOT fix infrastructure or run ahead to other scenarios; if BLOCKED, report immediately.
"""
)
```

---

## Notes

- **One unit of work per task.** Assign the next unit on completion — don't batch.
- **Ownership is disjoint.** Two coders must never share a file.
- **Skills aren't injected.** Name the skill; the teammate invokes it.
- These are skeletons, not requirements. Compose the team the task actually needs.

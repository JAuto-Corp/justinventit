---
name: capture/audit
description: Convert findings from a /verify:audit run into tracked captured issues.
---

# /capture:audit

Turn the findings of a prior `/verify:audit` (or any `/verify:*` audit) into tracked issues. The audit produced a findings report; this converts the actionable ones into `captured` issues without re-doing the analysis.

## Prerequisite

A completed `/verify:audit` run with a findings report (see the `verify` skill). Work from that report.

## Workflow

### 1. Re-validate before filing

Findings age. Confirm each is still real and not already tracked:

```
Task(subagent_type="Explore", prompt="For these audit findings: <list>
1. Is each still present in the current code (file:line)?
2. Already fixed, or a duplicate of an existing open issue?
3. Actual impact. Return under 2000 characters.")
```

Drop stale or duplicate findings. Group findings that describe the same root cause into one issue.

### 2. Map severity → priority

| Audit severity | Priority label |
|-|-|
| Critical | `p0` |
| Warning | `p1` |
| Info | `p2` |

### 3. Create one issue per actionable finding

```bash
gh issue create \
  --title "<type>: <finding>" \
  --label "captured,<type>,<priority>" \
  --body "$(cat <<'EOF'
## Source
Audit: [scope] on [date]

## Finding
[What the audit flagged]

## Location
`path/to/file:line`

## Impact
[User impact or maintenance cost]

## Suggested fix
[Action, or the skill that governs the pattern]
EOF
)"
```

### 4. Link the log to the issues

Append a line per created issue to `context/DISCOVERIES.md` so the discovery log points at what tracks it:

```markdown
## [timestamp]
[DISCOVERY:DEFECT] #<n> — <finding> (from audit: <scope>)
```

Hand the batch to `/capture:triage` for epic/priority routing if there are many.

# Self-Improvement

> The system that improves itself.

## The Friction Loop

When an agent encounters friction — a skill was wrong, a hook blocked incorrectly, a workflow step was unnecessary — it should emit a signal rather than silently working around it.

### Signal Format

```
[FRICTION:SKILL] backend-api-patterns said to use X, but codebase uses Y
[FRICTION:HOOK] stop.sh blocked exit for scenario not executed, but scope was Quick
[FRICTION:WORKFLOW] /work:continue deployed 4 explorers but I only needed schema context
[FRICTION:CONTEXT] Session brief didn't mention active worktree port assignment
```

### Extraction Pipeline

The stop hook automatically extracts `[FRICTION:*]` signals from the session:

1. **Detect**: Stop hook scans session output for `[FRICTION:*]` patterns
2. **Log**: Appends to `context/FRICTION_LOG.md` with timestamp and classification
3. **Classify**: Each entry is tagged as PROJECT or FRAMEWORK
4. **Act**: PROJECT → agent updates local skill/hook/rule. FRAMEWORK → creates issue in framework repo.

### Classification Guide

| Improvement | Classification | Example |
|-|-|-|
| Domain best-practice update | PROJECT | "RLS pattern changed for our schema" |
| Orchestration pattern change | FRAMEWORK | "Add skill-health check to verify:complete" |
| Hook pipeline architecture | FRAMEWORK | "Stop check ordering needs adjustment" |
| New domain skill content | PROJECT | "Need a caching patterns skill for Redis" |
| State file format improvement | FRAMEWORK | "Add active-scenarios to session brief" |
| New hook check | Depends | Migration guard = PROJECT. TDD evidence = FRAMEWORK |

### The Upstream Flow

When a friction entry is classified as FRAMEWORK:

```bash
# The agent (or human) creates an issue in the framework repo
gh issue create --repo JAuto-Corp/justinventit \
  --title "FRICTION: Stop check ordering needs adjustment" \
  --body "..."

# After the framework repo merges the fix:
copier update  # Three-way merge brings the improvement to your project
```

### Skill Drift Detection

Skills encode best practices, but codebases evolve. Drift detection catches staleness:

**Coverage metadata** in SKILL.md frontmatter:
```yaml
---
name: backend-api-patterns
description: API route patterns and database operations
covers:
  files: "src/app/api/**/*.ts"
  patterns: ["createServerClient", "Database['public']['Tables']"]
  conventions: ["service-role-for-insert", "log-full-errors"]
---
```

**Drift audit**: Compare skill assertions against actual codebase patterns. If the skill says "always use X" but recent code uses Y, flag it.

**Automated trigger**: After `/verify:complete` or `/verify:sprint`, if audit found pattern violations that turned out to be correct code (the skill was wrong, not the code), prompt agent to update the skill.

## Maturity Levels

### Level 1: Manual Friction Notes
Agent notices friction, mentions it in session. Human reviews and updates.

### Level 2: Signal-Based Extraction (default)
`[FRICTION:*]` signals in agent output. Stop hook extracts and logs. Classification is manual.

### Level 3: Automated Classification
Friction log analysis identifies recurring patterns. Classification rules auto-assign PROJECT vs FRAMEWORK based on what changed.

### Level 4: Self-Patching (aspirational)
Inspired by Factory.ai Signals: automated embedding of friction descriptions, clustering, threshold-triggered self-patch proposals. The agent proposes skill/hook/rule changes based on friction patterns.

Most projects will operate at Level 2-3. Level 4 requires significant session volume to be meaningful.

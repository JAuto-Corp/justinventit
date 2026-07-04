---
name: patterns/interview
description: The AskUserQuestion protocol — collaborative Q&A to pin down requirements before writing a spec or making a decision the code can't answer.
---

# Interview Protocol

> Spec from understanding, not assumption. A 5-minute interview prevents hours of rework.

Use the `AskUserQuestion` tool for iterative Q&A before creating a spec or making a UX/architecture decision. Ask, wait, process, ask again — never dump a wall of questions.

## When to interview

| Trigger | Why |
|-|-|
| Planning a sprint or epic | Cross-phase UX/architecture decisions need human input |
| Writing a SPEC for a multi-component feature | Domain choices the code can't answer |
| A new user-facing surface | Navigation, layout, journey decisions |
| Ambiguous scope or offerings | The user knows the intent; the code doesn't |

**Skip** for single-file fixes, clear technical tasks, and bugs with an obvious solution.

## What to ask about

| Area | Example questions |
|-|-|
| Outcomes | "How do we know this worked? What can the user do afterward?" |
| Journey | "Where does the user start, and what happens next?" |
| Surface | "Where does this live? How is it discovered?" |
| Construction | "One view or progressive disclosure? What's the shape?" |
| Constraints | "Any business rules or edge cases we must handle?" |
| Architecture | "Sync or async? Where does state live? What happens when X fails?" |

Use outcome/journey questions for user-facing work and architecture questions for backend work; many features need both.

## Flow

Use the tool — structured options, not free text:

```
AskUserQuestion(questions: [
  { question: "...", header: "...", options: [
      { label: "Option A", description: "what it means" },
      { label: "Option B", description: "what it means" } ],
    multiSelect: false }
])
```

Rhythm:
1. **Open** — 1-2 broad questions about the goal.
2. **Drill** — 2-4 follow-ups based on the answers (tool limit: 4 per round).
3. **Iterate** — keep going until alignment is clear.
4. **Reflect** — summarize your understanding in text; ask "does this capture it?"
5. **Synthesize** — only after confirmation, write the spec.

Derive the spec's outcomes from confirmed success criteria, its stories from confirmed journeys, and its acceptance checks from confirmed constraints.

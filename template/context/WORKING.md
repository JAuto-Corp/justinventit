# Working State

> Append-only observation blocks. Each entry is a dated snapshot of current state.
> This format is cache-friendly — stable prefix = cached by Anthropic's prefix caching.

## Format

Each block:
```
## YYYY-MM-DDTHH:MMZ
Phase: [epic/sprint/phase or "none"]
Completed: [what was done]
Next: [immediate next action]
Blockers: [none or description]
```

---

<!-- Append new entries below this line -->

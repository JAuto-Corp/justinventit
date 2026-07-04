---
name: verify/file
description: Targeted audit of specific file(s) — patterns, callers, coherence, caller impact.
---

# /verify:file <path> [path...]

Targeted audit of one or more files and the code that depends on them.

## Workflow

### 1. Gather context

Read the target file(s) and their immediate dependencies. Find every caller — use the project's LSP find-references if available, otherwise grep for the exported symbols:

```bash
Grep(pattern="<symbol>", output_mode="files_with_matches")
```

Understand what calls the file, what it depends on, and the related symbols.

### 2. Deploy targeted explorers

Deploy the perspectives that match the file's role (see `audit.md`) — Coherence always; add Correctness for logic, Integration for entry points, Configuration for config files.

### 3. Cross-reference the matching skill

Invoke the applicable best-practices skill in `.claude/skills/domain/` and check the file against it.

### 4. Caller impact

If the file changed: will its callers still compile and behave? Any type mismatches or breaking-change ripples? Enumerate affected callers.

### 5. Report

Use the `audit.md` template. Propose fixes inline, or file issues (`[DISCOVERY:*]`) for out-of-scope findings.

## Usage

```
/verify:file src/lib/orders.ts
/verify:file src/lib/orders.ts src/hooks/use-order.ts
```

## Related

- Audit engine + report template: `audit.md`

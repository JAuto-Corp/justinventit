---
name: verify/feature
description: Audit a named feature across its full implementation — every layer it touches.
---

# /verify:feature <name>

Audit a feature end-to-end across every file and layer it participates in.

## Workflow

### 1. Discover the feature's footprint

Search broadly for the feature's name and identifiers; list every participating file:

```bash
Grep(pattern="<name>", output_mode="files_with_matches")
```

Cover entry points, core logic, data access, shared types, and tests.

### 2. Deploy explorers scoped to the found files

Deploy the applicable perspectives (see `audit.md`), each scoped to the discovered file list rather than a git range.

### 3. Completeness across layers

Check the feature is whole across every layer it touches — gaps are findings:

| Layer | Check |
|-|-|
| Entry points | Present; states (empty/loading/error) handled |
| Logic | Implemented; edge cases covered |
| Data | Storage/queries present and consistent |
| Types | Shared, no untyped escapes |
| Tests | Coverage exists |

### 4. Cross-reference best-practices skills

Invoke the matching skill(s) in `.claude/skills/domain/` and compare each layer against them.

### 5. Feature report

Use the `audit.md` template, adding a layer-coverage table. File issues for gaps or deferred work.

## Usage

```
/verify:feature order-entry
/verify:feature user-authentication
```

## Related

- Audit engine + report template: `audit.md`

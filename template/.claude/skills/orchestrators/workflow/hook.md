---
name: workflow/hook
description: Adding or editing a hook — the three kinds, auto-discovery vs registration, the STDIN/exit-code contract, and the mandatory harness test.
---

# Add or Edit a Hook

A hook turns a convention into a gate. There are three kinds; how they are wired differs.

| Kind | Location | Wiring | Blocks? |
|-|-|-|-|
| Stop check | `.claude/hooks/stop/checks/NN-name.sh` | Auto-discovered by `stop/runner.sh` (glob `[0-9]*.sh`, run in filename order) | Yes — exit ≠0 blocks the stop; runner exits 2 |
| Stop action | `.claude/hooks/stop/actions/name.sh` | Auto-discovered by `stop/runner.sh` (glob `*.sh`, run after checks) | No — failures are swallowed |
| PreToolUse guard | `.claude/hooks/guards/name.sh` | NOT auto-discovered — register in `settings.json` under `hooks.PreToolUse` with a `matcher` | Yes — exit 2 blocks the tool call |

## Numbering (stop checks)

`01`–`50` are framework-managed (arrive via `copier update`); `51`+ are project-specific. Filename order is run order, so number to place the check where you want it in the pipeline.

## I/O contract

- **Stop check/action**: reads state files / the transcript (STDIN carries the Stop-hook JSON, forwarded by the runner). Exit 0 = pass; non-zero = block (checks) or ignored (actions). Emit the block reason on stderr.
- **PreToolUse guard**: reads the tool payload on STDIN (`.tool_name`, `.tool_input`). Exit 0 = allow, exit 2 = block. Emit the reason on stderr (and optionally `{"decision":"block","reason":...}` on stdout).
- Fail-open on a missing/unparseable payload — never wedge the session on your own bug.

## Copier suffix

If the script needs a copier answer variable, name it `name.sh.jinja` (rendered on generation); a fully generic script has no suffix and is copied verbatim. Match the neighbor.

## Mandatory: harness test

EVERY hook change ships with a test. The harness (`.claude/hooks/tests/harness.sh`) drives a hook with no live session — feed STDIN + env + a seeded state dir, assert exit code and an output substring.

1. Add/extend `.claude/hooks/tests/test-<hook>.sh`:
   ```bash
   source "$(dirname "${BASH_SOURCE[0]}")/harness.sh"
   run_case --name "blocks outside boundary" --hook "$GUARD" \
            --stdin '<json>' --expect-exit 2 --expect-out "<substring>"
   run_case --name "allows inside" --hook "$GUARD" --stdin '<json>' --expect-exit 0
   harness_summary; exit $?
   ```
2. Cover both the block path and the allow/pass path.
3. Run the whole suite green: `bash .claude/hooks/tests/run-all.sh` (it runs every `test-*.sh` and fails if any case fails).

A guard also needs its `settings.json` registration verified; a stop check/action just needs to land in the auto-discovered directory. Then run `validate.md`.

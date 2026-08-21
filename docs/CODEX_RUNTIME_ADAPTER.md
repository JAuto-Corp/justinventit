# Codex Runtime Adapter

This adapter is the first non-destructive bridge between justinventit's Claude-first generated
surface and Codex CLI or Codex Desktop running in WSL2. It is deliberately project-local. It does
not edit either runtime's global configuration, select a model, change a sandbox, install MCP
servers, bind a seat, or mutate a consumer repository.

## Generated surfaces

| Surface | Purpose |
|-|-|
| `.codex/config.toml` | Transitional `CLAUDE.md` fallback until canonical `AGENTS.md` composition lands |
| `.codex/hooks.json` | Codex CLI/Desktop `SessionStart` wiring for startup, resume, clear, and compaction |
| `.agents/hooks/` | Provider-neutral session-state implementation and shared utilities |
| `.claude/hooks/session-start.sh` and `lib/utils.sh` | Thin Claude adapters that delegate to shared implementations |

[Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md) checks
`AGENTS.md` before fallback filenames. A project that already has `AGENTS.md`, such as the
customer-portal reference implementation, therefore keeps its existing entry contract and does
not receive duplicate root instructions from `CLAUDE.md`.

The hook command resolves from the Git root, so a task opened in a nested directory receives the
same session brief. Plain stdout is valid `SessionStart` additional developer context in Codex and
remains the existing Claude hook output shape.

## Trust boundary

[Codex project configuration](https://learn.chatgpt.com/docs/config-file/config-basic) loads the
project `.codex` layer only for a trusted project. Codex separately requires the exact project
hook definition to be [reviewed and trusted](https://learn.chatgpt.com/docs/hooks). That review is
an installation step, not something the template bypasses. Codex CLI and Codex Desktop can use
the same project files; their user-level `CODEX_HOME` stores may still differ.

Both `.codex/config.toml` and `.codex/hooks.json` are seed-once files in Copier. A fresh project
receives the adapter. A brownfield project that already has either file keeps its existing file;
the adapter must be merged explicitly after review. This avoids whole-file replacement before the
deterministic region composer described by the context contract exists.

## Compatibility boundary

This slice intentionally leaves the following work for their owning migrations:

- Canonical root and nested `AGENTS.md` composition and Claude import shims.
- Tier-0 global context generation for each runtime home.
- Portable projections for orchestration skills beyond the separately governed skill publication.
- Model/profile, MCP, permission-policy, and runtime-specific agent generation.
- Desktop seat registration and task/thread-handle lifecycle in the seat protocol.
- Consumer installation in customer-portal while its existing publication hold remains active.

## Verification

The generation matrix validates the TOML and JSON shapes, ensures neither file contains model,
sandbox, permission, or MCP policy, runs the provider-neutral hook and Claude wrapper against the
same nested-worktree fixture, and uses `codex debug prompt-input` to prove that a generated
project without `AGENTS.md` receives its generated `CLAUDE.md` through the project-local fallback.

Rollout should proceed as a generated-project pilot first. Consumer installation is a separate,
explicit action after the relevant publication hold is lifted and the consumer diff has been
reviewed.

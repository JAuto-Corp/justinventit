# Context Contract

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §4. Defines how context reaches
> every session, on every runtime, within budget — deterministically.

## 1. Canonical hierarchy

```
TIER 0  global     ~/.codex/AGENTS.md  +  ~/.claude/CLAUDE.md (shim → same content)
TIER 1  repo root  AGENTS.md            (canonical entry contract)
TIER 2  nested     <subtree>/AGENTS.md  (subtree conventions; loaded only when working there)
```

Every block of content is tagged **Layer A** (agentic platform, framework-owned) or
**Layer B** (project context, project-owned). Tier and layer are orthogonal axes.

## 2. Composite files and regions

`AGENTS.md`, `CLAUDE.md`, and `.claude/settings.json` are **composite files**: the only files
where both layers share one runtime-facing artifact. Rules:

- Framework-owned regions are delimited by forge markers (`<!-- forge:begin:<region> -->` /
  `<!-- forge:end:<region> -->`).
- A manifest (`.agents-manifest.json`, generated) lists every region, its owner, and its
  content hash — the composer's source of truth.
- Framework updates are applied by a **deterministic composer** (Copier update task): it
  replaces framework regions by marker, never whole-file copies. Conflict policy: a locally
  modified framework region blocks the update with a named diff (fail loudly), never silent
  overwrite; project regions are never touched.
- Conformance test: compose → recompose → byte-identical (idempotence), and a seeded local
  edit inside a framework region must produce the named-conflict failure.

## 3. Runtime resolution (compiled, not assumed)

| Concern | Codex CLI (≥0.134 semantics; tested at 0.145) | Claude Code CLI |
|-|-|-|
| Root entry | native AGENTS.md discovery (concat global→root→cwd) | `CLAUDE.md` = `@AGENTS.md` + runtime extras |
| Nested entry | native per-directory discovery | **not native** — composer emits per-directory `CLAUDE.md` shims (`@<relpath>/AGENTS.md`) for every nested AGENTS.md |
| Payload ceiling | `project_doc_max_bytes` (default 32768), silent truncation | no hard ceiling; same budget applied by policy |
| Verification | `codex debug prompt-input` fixture test in CI | manual checklist + session-entry smoke test |
| Transitional bridge | `project_doc_fallback_filenames=["CLAUDE.md"]` only for dirs not yet migrated | n/a |

Native-discovery behavior is pinned to tested runtime versions in the compatibility test
fixtures; a runtime upgrade reruns them before rollout. IDE runtimes (Cursor/Windsurf/Cline)
read root AGENTS.md natively; nested behavior there is out of scope until a consumer needs it.

## 4. Budget

- **Budgeted**: the deterministic repo-owned payload — worst-case concatenation
  root + deepest nested chain per working directory. CI computes it per directory containing
  an AGENTS.md and fails above **28 KB** (4 KB reserved headroom for global/user context CI
  cannot see).
- **Reported, not budgeted**: global tier size (measured on developer machines by the doctor
  script, warned above 4 KB).
- Byte counting = bytes of the concatenated payload exactly as the Codex renderer assembles
  it (separators included), reproduced by the check script and verified against
  `codex debug prompt-input` in the fixture test.

## 5. Placement rules (what lives where)

- **Root AGENTS.md** (entry): project identity + codebase map (B), non-negotiables (A+B),
  gate summary with pointers (A), session-entry protocol — stated HERE and nowhere else (A),
  routing tables to skills/docs (A+B). No procedure bodies, no duplicated policy.
- **Nested AGENTS.md**: subtree conventions, subtree test/build commands, pointers to the
  Layer-B domain index for that subtree. One hop from any seat to deep project knowledge.
- **Skills**: procedures. **Docs**: reference. **Neither is restated in entry files.**
- Anything stated twice is a defect; the freshness/coherence CI greps for known-duplicated
  headings as a tripwire.

## 6. Runtime-delta channels

| Channel | Claude | Codex | Rule |
|-|-|-|-|
| Auto-memory (MEMORY.md) | yes | **no** | durable rules BOTH runtimes need live in AGENTS.md; memory is Claude-side working knowledge only |
| Skills | `/name`, `.claude/skills/` | `$name`, `.codex/skills/` | one source tree; composer emits/links both roots |
| Command policy | settings permissions (prose-adjacent) | `.rules` execpolicy (testable) | hard bans authored once in matrix/policy config; generator emits both forms |
| Hooks | settings.json wiring | `[hooks]`/hooks.json | one hook source tree, two thin wirings; hook bodies shared |
| Structured verdicts | text + HTML markers (legacy) | `--output-schema` | schema-verdict is the target form for both (Claude via StructuredOutput-style conventions) |

## 7. Migration order (JAuto)

1. Author root AGENTS.md within budget; CLAUDE.md becomes shim + extras (old content routed
   to skills/docs — nothing dropped without a pointer).
2. Nested AGENTS.md for `apps/web`, `apps/scheduler`, `test-data` + generated Claude shims.
3. Retire duplicated session-entry protocols (PLAYBOOK §, CLAUDE.md Quick Start) in the same
   change that lands the single canonical section.
4. Budget CI check + `codex debug prompt-input` fixture test land with step 1.

## 8. Routed review findings dispositioned here

- Cross-runtime nested resolution (major): §3 — per-directory shims / compiled resolution.
- Budget determinism (major): §4 — repo-owned payload budgeted; global reported separately.
- Region ownership enforceability (blocker, arch-level): §2 — manifest + composer + conformance tests.

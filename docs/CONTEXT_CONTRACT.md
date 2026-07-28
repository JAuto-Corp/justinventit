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
- **Authored source of truth** = the framework's region source files (template-owned,
  versioned in the template repo). The installed `.agents-manifest.json` is a **generated
  LOCK file** (template version + last-applied content hash per region + ownership) — state,
  not source. The composer distinguishes three cases per region by comparing the local file
  against the lock hash and the incoming source: unchanged → apply upstream; locally
  modified → **named conflict, update blocked** (fail loudly, never silent overwrite, and a
  local edit is never absorbed as the new base); project regions → never touched.
- Framework updates are applied by this **deterministic composer** (Copier update task),
  region-by-marker, never whole-file copies. The decision table is TOTAL: unchanged →
  apply; locally modified → named conflict; project region → untouched; **region missing
  locally / markers corrupt → named conflict (treated as local modification, never
  recreated silently); NEW upstream region → inserted at its manifest anchor (the normal
  upgrade case); region removed upstream → deleted only if local hash matches lock, else
  named conflict.** Any input outside these branches is a composer error, not a skip.
- Conformance test: compose → recompose → byte-identical (idempotence), and a seeded local
  edit inside a framework region must produce the named-conflict failure.

## 3. Runtime resolution (compiled, not assumed)

| Concern | Codex CLI (≥0.134 semantics; tested at 0.145) | Claude Code CLI |
|-|-|-|
| Root entry | native AGENTS.md discovery (concat global→root→cwd) | `CLAUDE.md` = `@AGENTS.md` + runtime extras |
| Nested entry | native per-directory discovery | **not native** — composer emits per-directory `CLAUDE.md` shims (`@<relpath>/AGENTS.md`) for every nested AGENTS.md |
| Payload ceiling | `project_doc_max_bytes` (default 32768), silent truncation | no hard ceiling; same budget applied by policy |
| Verification | `codex debug prompt-input` fixture test in CI | automated fixture: headless `claude -p` run in the fixture repo asserting tier-marker visibility AND ordering at root and nested working dirs |

The fixture suite's capstone is an **equivalence assertion**: one canonical fixture
hierarchy rendered through both runtimes (codex `debug prompt-input`, claude headless
probe), normalized, and compared — same regions, same effective order. Per-runtime
visibility checks alone cannot falsify the contract's actual premise.
| Transitional bridge | `project_doc_fallback_filenames=["CLAUDE.md"]` only for dirs not yet migrated | n/a |

**Claude resolution algorithm (normative)**: Claude Code natively loads `CLAUDE.md` files
along the cwd→root chain; each shim's first line is its directory's `@AGENTS.md` import,
followed by any runtime extras. Effective order therefore mirrors Codex's global→root→nested
concat, with nearest-file-last precedence; relative imports resolve against the shim's own
directory; the composer emits each region exactly once across the chain, so duplicate
handling never arises at read time (duplication is a compose-time error).

Native-discovery behavior is pinned to tested runtime versions in the compatibility test
fixtures; a runtime upgrade reruns them before rollout. IDE runtimes (Cursor/Windsurf/Cline)
read root AGENTS.md natively; nested behavior there is out of scope until a consumer needs it.

## 4. Budget

- **Budgeted**: the deterministic repo-owned payload — worst-case concatenation
  root + deepest nested chain per **declared workspace root** (not every directory: see the
  skill-payload exclusion below). CI fails above **26 KB**, with a **6 KB reserve** sized to
  measured reality, not aspiration (the reference environment's global tier already measures
  ~4.8 KB — a 4 KB reserve was arithmetically breached on day one). The doctor script
  re-measures the reserve against actual global files and warns when reality erodes it.
- **Skill-payload AGENTS.md files are NOT entry contracts.** Vendored/skill trees (e.g.
  `.agents/skills/**`, one of which ships an 81 KB AGENTS.md) are excluded from the entry
  hierarchy by an explicit exclusion list: the CI budget check skips them, the composer
  emits no shims for them, and seats do not run with cwd inside them (a cwd inside an
  excluded tree inherits its payload — the doctor flags that configuration).
- **Claude auto-memory is outside this contract** (invisible to Codex, not part of the
  AGENTS payload) but is counted in a separate per-runtime context-health report with its
  own budget, so total Claude-side context stays observable.
- **Enforced at launch**: the seat launcher / doctor script measures the COMBINED payload
  (global + repo chain, exact separators) where the global tier is actually visible, and
  refuses to launch (with the measured breakdown) if it would cross the runtime ceiling —
  truncation is a named local-environment nonconformance, never a silent event. Global >4 KB
  alone is a warning.
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

### 5a. Section-move law (Wave-1 lessons, 2026-07-27 — both learned the expensive way)

- **A section move is not complete until every live consumer is retargeted.** The sweep
  that finds consumers greps ALL file types — workflow YAML comments, shell-script error
  text, and code comments point at doc sections too; an `--include="*.md"` sweep missed
  three of them and a fourth class (the post-compaction recovery command) failed SILENTLY
  at exactly the moment its session couldn't notice. Retarget what is broken, not what is
  merely old; leave historical records unrewritten. The move-PR carries the sweep as
  evidence (the grep + its zero-hit re-run).
- **The move is an ORDERED algorithm; each step gates the next.** (1) VERIFY THE TARGET:
  open the claimed home and confirm the owned content is actually present — by reading it,
  never by locating the file (six false "already homed" claims in one wave shared exactly
  this root cause: grep-for-filename instead of read-the-owner). (2) Enumerate live
  consumers (the all-file-types sweep above). (3) Retarget them. (4) Audit downstream
  shapes where the rule content changed (next bullet). (5) VERIFY THE END STATE: target
  content present, retargeted references resolve live, and the consumer sweep re-runs to
  zero hits. A mover may not retarget consumers at a target step 1 has not proven — that
  ordering is what makes step 3 safe.
- **End-state verification is DIRECT where accessible, provenance-bound otherwise.** Verify
  the authoritative end state yourself when you can reach it; where you cannot, require
  provenance-bound evidence from the authoritative surface (a runner or CI attestation
  carrying its run id). What this rejects is the ungrounded ACTOR REPORT — "I moved it",
  "clean merge" — never machine attestations (`ARCHITECTURE.md` §8's evidence model is
  unchanged). Same rule that caught a silent merge-revert the same night it was written.
- **A rule change audits downstream shapes when it changes what is representable** — the
  normative rule lives at its owning surface, `MODEL_MATRIX.md` §1a (the policy/generator
  ownership contract), where permission authors actually work; this bullet is the pointer
  the section-move context earns, not a second statement of it. Origin: twice in one PR a
  permission was widened while the output template still demanded the old form.
- **Doc claims about surfaces are verified at authoring time, in both tenses.** A
  present-tense claim ("skills resolve on both runtimes", "checked by CI") must name its
  existing referent; a planned surface is written future-tense with the wave that lands
  it. And a pointer's TARGET existing in history is checked before any "restore" — one
  pointer proved BORN dangling (four months old, target never existed), so a
  restore-from-history instruction would have fabricated content under a provenance
  claim. Retrieval claims cite the retrieved SHA.

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
   to skills/docs — nothing dropped without a pointer). Acknowledged magnitude: the current
   root CLAUDE.md is ~43.6 KB against a 26 KB budget — this step sheds >15 KB by routing,
   and is authoring-tier work, not mechanical trimming. The skill-payload exclusion list
   (§4) ships in the same change, since JAuto already contains vendored AGENTS.md files.
2. Nested AGENTS.md for `apps/web`, `apps/scheduler`, `test-data` + generated Claude shims.
3. Retire duplicated session-entry protocols (PLAYBOOK §, CLAUDE.md Quick Start) in the same
   change that lands the single canonical section.
4. Budget CI check + `codex debug prompt-input` fixture test land with step 1.

## 8. Routed review findings dispositioned here

- Cross-runtime nested resolution (major): §3 — per-directory shims / compiled resolution.
- Budget determinism (major): §4 — repo-owned payload budgeted; global reported separately.
- Region ownership enforceability (blocker, arch-level): §2 — manifest + composer + conformance tests.

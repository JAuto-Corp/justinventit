# Model / Effort Matrix

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §6. The matrix is DATA, not
> prose: one authored source, generated consumers, zero hand-edited policy tables.

## 1. Categories (law 2 applied)

- **Authored source**: `matrix.yaml` — the only file humans/O edit. Questionnaire answers
  set project defaults; per-project overrides layer on top with stated precedence
  (override > questionnaire > framework default).
- **Generated artifacts** (freshness-gated): launcher tier table (role-launch dispatch),
  Codex profile files (`~/.codex/<tier>.config.toml` content), `.rules`/permission policy
  emissions, the human-readable policy table in docs, `.claude/agents/*` + `.codex/agents/*`
  effort pins.
- **Runtime state** (never freshness-gated): which seats are currently booted at what tier
  (registry), temporary per-session raises.

Editing a generated file is a defect the freshness gate catches.

## 2. Schema

```yaml
schema_version: 1
tiers:                      # named launchable tiers
  thinking:  { runtime: any,   model: <per-runtime>, effort: xhigh }
  authoring: { runtime: claude, model: fable-class,  effort: xhigh }
  doing:     { runtime: any,   model: <per-runtime>, effort: low }
  maint:     { runtime: any,   model: mid-class,     effort: medium }
seat_classes:               # role → tier (+ rationale, fallback)
  orchestrate:      { tier: thinking, fallback: authoring }
  integrate:        { tier: thinking }
  design_authoring: { tier: authoring, note: "guidance/SPEC/greater-synthesis authoring" }
  implement:        { tier: doing }
  explore:          { tier: doing }
  capture:          { tier: doing }
  diagnostic:       { tier: thinking, note: "escalate-on-stall rule, not default-high" }
  docs_baseline:    { tier: authoring, note: "two-tier synthesis ruling" }
  docs_maintenance: { tier: maint,  requires: "hierarchy exists (gate, not vibe)" }
  cross_review:     { tier: thinking, second_opinion: { runtime: codex, effort: xhigh } }
  frontend:         { tier: doing, raise_to: maint }
models:                     # per-runtime model ids per class, pinned + dated
  claude: { thinking: opus-5, authoring: fable-5, doing: opus-5, maint: sonnet-5 }
  codex:  { thinking: gpt-5.6-sol, doing: gpt-5.6-sol, maint: gpt-5.6-terra }
```

(Exact ids live in the file, dated; benchmarks/pricing that justified them are cited in an
adjacent RATIONALE section with retrieval dates — model facts rot fast.)

## 3. Initial values (2026-07-26, research-grounded)

| Seat class | Runtime/model/effort | Grounding |
|-|-|-|
| orchestrate (O), integrate (I) | claude opus-5 @ xhigh | official "xhigh for demanding agentic work"; FrontierBench xhigh>max |
| design/guidance authoring, docs baseline | claude fable-5 @ xhigh | SWE-bench-Pro lead; no overthink caveat; 2× cost worth it for irreversible decisions; "Fable authors guidance" rule |
| implement, explore, capture | claude opus-5 @ low | official: low "scopes work to what was asked"; cheapest sanctioned Claude tier |
| diagnostic | opus-5 @ high→xhigh on stall | official escalate-on-shallow-reasoning guidance |
| docs maintenance | sonnet-5 @ medium (AFTER hierarchy ships) | two-tier synthesis ruling |
| cross-review | opus-5 @ xhigh + codex sol @ xhigh second opinion | standing cross-runtime lane |
| codex seats (pilot) | gpt-5.6-sol @ xhigh (review) / low (mechanical) | Sol default LOW is official; ultra excluded (auto-delegation) |

Rules that ride along: hold effort constant within a session (prompt cache); raise effort on
demonstrated shallow reasoning rather than prompting around it; `max`/`ultra` are not in the
matrix (xhigh>max data; ultra self-delegates).

## 4. Supersession

Shipping this matrix **supersedes the 2026-07-24 "one model, two efforts" policy**. The
shipping PR must: record the supersede in the policy memory + user CLAUDE.md pointer, extend
the launcher to every tier in `tiers:` (it currently hardcodes two), correct the stale
harness default model, and regenerate all generated consumers. Until that PR lands, 07-24
policy stands.

## 5. Routed review findings dispositioned here

- Generated-config source-of-truth ambiguity (major): §1 — categories + precedence; rosters
  are runtime state, excluded from freshness gates.

# Model / Effort Matrix

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §6. The matrix is DATA, not
> prose: one authored source, generated consumers, zero hand-edited policy tables.

## 1. Categories (law 2 applied)

- **Authored inputs — four, each named and schema-defined**: framework defaults
  (`matrix-defaults.yaml`, template-owned), questionnaire answers (`.copier-answers.yml`),
  project overrides (`matrix-overrides.yaml`), and command policy (`policy.yaml`, §1a).
  Precedence: overrides > answers > defaults.
- **The effective matrix is GENERATED**: `matrix.resolved.yaml` is derived from the four
  inputs by the generator, freshness-gated, never hand-edited — satisfying the architecture
  law that every operative matrix is a generated artifact. All consumers (launcher tiers,
  Codex profiles, `.rules`/permissions, docs tables, agent effort pins) generate from the
  RESOLVED matrix only. Other specs cite policy ids, never restate rule content.
- **Generated artifacts** (freshness-gated): launcher tier table (role-launch dispatch),
  Codex profile files — **project-qualified**: `~/.codex/<project_id>-<tier>.config.toml`,
  selected by the launcher via the seat record's `project_id`, so consuming projects never
  collide — `.rules`/permission emissions from `policy.yaml`, the human-readable policy
  table in docs, `.claude/agents/*` + `.codex/agents/*` effort pins.

### 1a. `policy.yaml` schema (command policy)

```yaml
schema_version: 1
bans:
  ban.merge.non-integrator: { pattern: ["gh","pr","merge"], applies_to: "!integrate", decision: forbidden }
  ban.staging-ddl.all:      { pattern: ["<mcp>","apply_migration"], target: staging, applies_to: "*", decision: forbidden }
prompts:  # decision: prompt — allowed with approval
  ...
```
Each entry carries inline match/not_match test cases (mirroring `.rules` fixtures); the
generator emits both runtime forms and their tests from the same entry.
- **Runtime state** (never freshness-gated): which seats are currently booted at what tier
  (registry), temporary per-session raises.

Editing a generated file is a defect the freshness gate catches.

## 2. Schema

```yaml
schema_version: 1
tiers:                      # named launchable tiers; every tier resolves on every runtime
  thinking:  { effort: xhigh }
  authoring: { effort: xhigh, note: "preferred runtime claude/fable-class; resolves to the available runtime's thinking model otherwise" }
  doing:     { effort: low }
  maint:     { effort: medium }
seat_classes:               # role → tier (+ rationale, fallback CHAIN — never runtime-dead-ends)
  direct:           { tier: authoring, fallback: thinking, note: "user-interaction + program direction; user-driven turns (dormant cadence); optional seat" }
  orchestrate:      { tier: thinking, fallback: authoring }
  integrate:        { tier: thinking }
  design_authoring: { tier: authoring, fallback: thinking, note: "guidance/SPEC/greater-synthesis authoring" }
  implement:        { tier: doing }
  explore:          { tier: doing }
  capture:          { tier: doing }
  diagnostic:       { tier: thinking, note: "dispatched deliberately, not default-on; cost control = dispatch discipline, not lower effort" }
  docs_baseline:    { tier: authoring, fallback: thinking, note: "two-tier synthesis ruling" }
  docs_maintenance: { tier: maint,  requires: "hierarchy exists (gate, not vibe)" }
  cross_review:     { tier: thinking, second_opinion: { when: "second-runtime-configured", runtime: other, effort: xhigh, else: "same-runtime fresh-context pass" } }
  frontend:         { tier: doing, escalate_to: thinking, note: "escalation raises the TIER (judgment-heavy UI work); tiers order thinking > authoring-adjacent > doing > maint on capability — a tier change is never a model downgrade dressed as a raise" }
models:                     # per-runtime model ids per TIER — complete on every runtime
  claude: { thinking: opus-5, authoring: fable-5, doing: opus-5, maint: sonnet-5 }
  codex:  { thinking: gpt-5.6-sol, authoring: gpt-5.6-sol, doing: gpt-5.6-sol, maint: gpt-5.6-terra }
```

(Exact ids live in the file, dated; benchmarks/pricing that justified them are cited in an
adjacent RATIONALE section with retrieval dates — model facts rot fast.)

## 3. Initial values (2026-07-26, research-grounded)

| Seat class | Runtime/model/effort | Grounding |
|-|-|-|
| orchestrate (O), integrate (I) | claude opus-5 @ xhigh | official "xhigh for demanding agentic work"; FrontierBench xhigh>max |
| design/guidance authoring, docs baseline | claude fable-5 @ xhigh | SWE-bench-Pro lead; no overthink caveat; 2× cost worth it for irreversible decisions; "Fable authors guidance" rule |
| implement, explore, capture | claude opus-5 @ low | official: low "scopes work to what was asked"; cheapest sanctioned Claude tier |
| diagnostic | opus-5 @ xhigh (thinking tier) | audits/diagnosis are thinking work; the official escalate-on-shallow-reasoning guidance argues for starting high enough, and effort ladders within a session break prompt caching — so the tier IS the escalation, applied at dispatch time |
| docs maintenance | sonnet-5 @ medium (AFTER hierarchy ships) | two-tier synthesis ruling |
| cross-review | opus-5 @ xhigh + codex sol @ xhigh second opinion | standing cross-runtime lane |
| codex seats (pilot) | gpt-5.6-sol @ xhigh (review) / low (mechanical) | Sol default LOW is official; ultra excluded (auto-delegation) |

Rules that ride along: hold effort constant within a session (prompt cache); raise effort on
demonstrated shallow reasoning rather than prompting around it; `max`/`ultra` are not in the
matrix (xhigh>max data; ultra self-delegates).

**One-shot review lane (experiment, 07-27)**: Codex Sol one-shot `exec` reviews (read-only,
output-schema, xhigh judgment / low mechanical) are the preferred INDEPENDENT-review
substrate while capacity favors it — independence holds by construction (never the authoring
session), and the one-return shape matches verdict gates. A dependability scorecard
(schema-validity, findings survival under adversarial spot-check, ungrounded-claim rate)
gates two promotions: substituting the second fresh-context audit at fleet profile, and the
**terminate-and-fresh session pattern** — clean-dispatch seats END and fresh-boot (with
durable brief) rather than idle/resume, once one-shot external gates make long-lived
reviewer context unnecessary. Cross-provider usage pools are part of matrix input: shift
load toward the pool with headroom.

**Fresh vs continued threads (cache-aware, 07-27)**: grounded one-shots self-cache heavily
WITHIN a run (observed ≈90% cached input on repo-exploring reviews — real cost far below
raw tokens), and `exec resume` turns a thread's whole grounding into a cached prefix. Rules:
- **Fresh thread = the independence instrument** (audits, second opinions, gate passes) —
  default, non-negotiable where anchoring matters.
- **Continued thread = the iteration instrument**: disposition-confirmation ("are my fixes
  faithful to YOUR findings?") returns to the SAME reviewer thread — cheap, already
  grounded, and the right witness for that question; multi-stage work on one material
  (review → prioritize → suggest) stays in-thread; Codex seats are continuation by nature.
- The two questions never share a thread: same-thread confirms dispositions, a FRESH thread
  hunts new blind spots. Never continue across unrelated subjects.
- Scorecard tracks cached/uncached split; whether provider quotas discount cached input is
  an open probe, not an assumption.
- **Provisional promotion (07-27, 8 samples, usage: Sol-xhigh 2% vs Claude 25%)**: Sol
  one-shot is DEFAULT for second spec-audits, disposition-confirmations/gate re-passes,
  wave-PR reviews, workstream SPEC audits, and doc-verification sweeps — Claude in those
  lanes needs a stated reason. **Reliability inversion while the subagent delivery defect
  stands**: a synchronous one-shot has no agent→parent channel to lose, so Sol reviews are
  structurally more reliable than in-session team reviews; for PR code reviews Sol is
  primary and the pinned same-runtime reviewer is the cross-check (revisit on upstream fix).
  Target band: shift review/audit load until the lean pool sits at 10-15% with the
  conserved pool's growth flattened; usage deltas reported at phase boundaries.

## 4. Supersession

Shipping this matrix **supersedes the 2026-07-24 "one model, two efforts" policy**. The
shipping PR must: record the supersede in the policy memory + user CLAUDE.md pointer, extend
the launcher to every tier in `tiers:` (it currently hardcodes two), correct the stale
harness default model, and regenerate all generated consumers. Until that PR lands, 07-24
policy stands.

## 5. Routed review findings dispositioned here

- Generated-config source-of-truth ambiguity (major): §1 — categories + precedence; rosters
  are runtime state, excluded from freshness gates.

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

**Shape-audit rule (normative here; `CONTEXT_CONTRACT.md` §5a points at this).** A policy or
permission change that alters representable SEMANTICS — actors, actions, values, or
cardinality — audits the forms, templates, and schemas downstream of it: shapes encoding
the old restriction are updated; already-compatible shapes get an explicit no-impact
record. Editorial-only changes that do not alter representable semantics carry no shape
obligation — the trigger is semantic, and a semantic change made entirely through prose
still triggers it. A generated consumer list satisfies the audit wherever one exists.
Origin: two instances in one PR of a widened rule surviving as its output template's old
mandatory form.
- **Runtime state** (never freshness-gated): which seats are currently booted at what tier
  (registry), temporary per-session raises.

Editing a generated file is a defect the freshness gate catches.

## 2. Schema

```yaml
schema_version: 1
tiers:                      # named launchable tiers; every tier resolves on every runtime
  thinking:  { effort: xhigh }
  authoring: { effort: xhigh, note: "preferred runtime claude/fable-class; resolves to the available runtime's thinking model otherwise" }
  doing:     { effort: medium }   # raised from low 2026-07-27: low doers over-reasoned without the capability to back it; the EXECUTE register (below) is the boundary, not starved effort
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
  claude: { thinking: fable-5, authoring: fable-5, doing: opus-5, maint: sonnet-5 }   # 2026-07-27 correction: FABLE THINKS, OPUS DOES — opus-as-thinker caused over-engineering-through-misunderstanding; thinking seats consult Sol xhigh frequently (funnel, red-team, escalated judgment)
  codex:  { thinking: gpt-5.6-sol, authoring: gpt-5.6-sol, doing: gpt-5.6-sol, maint: gpt-5.6-terra }
```

(Exact ids live in the file, dated; benchmarks/pricing that justified them are cited in an
adjacent RATIONALE section with retrieval dates — model facts rot fast.)

## 3. Initial values (2026-07-26, research-grounded)

| Seat class | Runtime/model/effort | Grounding |
|-|-|-|
| orchestrate (O/director), integrate (I) | claude fable-5 @ xhigh + frequent Sol xhigh consulting | 07-27 user correction (opus-as-O over-engineered); Sol is the standing second brain |
| design/guidance authoring, docs baseline | claude fable-5 @ xhigh | SWE-bench-Pro lead; no overthink caveat; 2× cost worth it for irreversible decisions; "Fable authors guidance" rule |
| implement, explore, capture | claude opus-5 @ medium, EXECUTE register | 07-27: medium for clean execution; the register (implement per instructions; judgment → short packet to director, resolved with Sol xhigh; outcome-not-essay reports ≤~30 lines) holds the thinking boundary |
| diagnostic | fable-5 @ xhigh (thinking tier, per the 07-27 correction) | audits/diagnosis are thinking work; the official escalate-on-shallow-reasoning guidance argues for starting high enough, and effort ladders within a session break prompt caching — so the tier IS the escalation, applied at dispatch time |
| docs maintenance | sonnet-5 @ medium (AFTER hierarchy ships) | two-tier synthesis ruling |
| cross-review | fable-5 @ xhigh + codex sol @ xhigh second opinion (thinking tier) | standing cross-runtime lane |
| codex seats | gpt-5.6-sol @ xhigh (thinking/judgment/dispatch) / low (mechanical) | **TRUST PARITY, user ruling 2026-07-28 (§3b)**: Sol is a thinking-tier PEER of the Claude thinking model, not a restricted pilot guest; ultra excluded (auto-delegation) |

Rules that ride along: hold effort constant within a session (prompt cache); raise effort on
demonstrated shallow reasoning rather than prompting around it; `max`/`ultra` are not in the
matrix (xhigh>max data; ultra self-delegates).

### 3b. Cross-runtime trust parity (USER RULING 2026-07-28)

**The second-runtime thinking model holds the same standing as the first-runtime thinking
model.** Concretely on this fleet: Sol @ xhigh is a peer of Fable @ xhigh — it may hold a
seat, receive and issue dispatches, author and ratify at its tier, and operate the same tool
surface. It is not a read-only guest whose write scope is earned later. Dispatch hierarchy
descends from EITHER thinking-tier runtime to the doing tier; a Sol-issued dispatch binds a
doing seat exactly as a Fable-issued one does.

**Why (user, verbatim intent):** the fleet runs on a local development machine as one team;
trust is granted to the CLUSTER, and judgment about what is destructive belongs to the
thinking tier rather than to a permission list that tries to enumerate it.

**What this does NOT relax — and the distinction is the load-bearing part.** The bans that
survive are **cluster invariants that bind every seat at every tier, including the
first-runtime thinking model and the director**. They exist for coordination and blast
radius, never as a statement about any runtime's judgment:
- **Merge serialization**: only the integrator seat merges. The director does not merge
  either; this is a serialization invariant, not a trust grade.
- **Shared-environment mutation**: staging/production DDL, migration application, and
  destructive infrastructure operations follow the project's guarded paths (see the
  consuming project's git/CI contract) regardless of who is asking.
- **Irreversible + outward-facing acts** (deploys outside the gated chain, credential
  rotation, data deletion, anything reaching a customer) carry their existing ceremonies.
- **Gate integrity**: nobody self-verdicts their own work, on any runtime. Independence
  comes from being a different context, which Sol satisfies structurally.
A seat of either runtime that needs one of the above asks the owner of that invariant — the
same escalation every Claude seat already makes.

**What actually makes this safe: ORIENTATION, not enumeration.** A permission list tries to
predict every destructive act in advance and fails at the first unlisted one. A seat that has
been *properly initiated into the project* — guided context exploration, entry contract to
domain index to leaf, understanding what the system IS and what depends on what — infers
correctly at the unlisted case, because it understands consequences rather than matching
patterns. That is why trust parity is coherent rather than reckless here, and it makes the
CONTEXT-DELIVERY SYSTEM a safety mechanism, not merely an efficiency one: every improvement
to orientation pathways raises the floor on judgment for every seat on every runtime.
Design consequence, binding on the orientation work (`ORIENTATION_MAPS.md`,
`CONTEXT_CONTRACT.md`): the goal is a seat that could DERIVE the invariants, not one that has
memorized them. Entry contracts therefore route to understanding (what this system is, what
is shared, what is irreversible, where the blast radius lives) rather than reciting
prohibitions; prohibition lists are a fallback for what orientation has not yet covered, and
each one is a signal that some pathway is missing. This is stated so the specs are *built*
that way — seats need not be told it explicitly; correct pathways produce correct operation.

**Credential posture on a single-operator local fleet (recorded, deliberate).** This machine
stores real credentials for the whole toolchain in the operator's own home directory — that
is the intended arrangement and it is what makes the agentic automation possible at all; a
fleet that had to re-authenticate per action could not run unattended. The security boundary
is the MACHINE and its operator, not per-agent credential partitioning. Two obligations
follow rather than any restriction: (1) agents never PRINT credential values — names and
paths only, in reports, verdicts, and archives; (2) artifacts get a REDACTION PASS before
entering any repo (2026-07-28: GitHub push protection caught an account identifier in an
archived probe output — the platform caught what the author's own no-secrets instruction had
not). A consuming project on shared or multi-tenant infrastructure would need a different
posture; this section states the local-fleet one honestly rather than generalizing it.

**Sandbox posture follows trust, with one honest caveat.** Trust parity means the sandbox is
sized to the WORK, not to the runtime: read-heavy work runs read-only because that is
sufficient, and work requiring writes gets write scope without a separate trust argument.
Caveat, evidence-grounded (2026-07-28 probes): a sandboxed runtime cannot prove the machine's
capabilities — two consecutive probes misread sandbox denials as machine/auth defects (a
network-denied `gh auth status` read as an invalid token; a snap/DBus denial read as a broken
gcloud that works fine unsandboxed). **A sandboxed negative is never a machine finding until
an unsandboxed control confirms it.**

**Verified surface at ruling time** (artifacts: `~/.jauto-orchestration/sol-runs/`
`2026-07-28-codex-tool-surface-{probe,validity}.json`; both controls passing, tree-verified
no writes): authenticated end-to-end from a Codex process — GitHub CLI (push+admin scopes),
private git transport, Supabase (prod+staging), Vercel (team scope), Codex's own session.
Open: npm unauthenticated (publishing only); Twilio key-class question; **gcloud unusable
under the Codex sandbox (snap needs a DBus transient scope) though fine unsandboxed — the one
concrete capability gap, fix = non-snap install or a sandbox allowance**. Codex-side MCP
config is empty by default; MCP grants are a deliberate per-profile addition, and because
seats inherit the user's whole CLI surface, per-profile config is SUBTRACTIVE (what to deny)
rather than additive.

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
  **Invocation mechanics (from field friction)**: grounded xhigh repo-reads exceed
  foreground shell ceilings — always BACKGROUND the run, and use PER-ATTEMPT output paths
  so a relaunch cannot truncate a prior attempt's evidence (one SIGKILLed foreground run +
  path reuse cost ten minutes of reading with zero evidence captured). **Resume mechanics (07-27, learned by three failed launches)**: `codex exec resume`
  rejects `-s` and `-C`; sandbox rides `-c sandbox_mode="read-only"`, cwd rides the
  invocation directory (UUID session ids bypass cwd-filtering). The wrapper — `scripts/sol-review.sh` in the consuming project (a forge-marked template
  artifact; ported in Phase 3 of the separation program, the template rebuild) — needs its own resume mode before disposition-confirmations are
  seat-self-serve; until then they route through the dispatcher. **A pinned path is not a working invocation** (the node-shim
  lesson): pinning fixes WHICH binary, not whether it runs — the runtime that must
  accompany a shim lives next to it, so wrappers prepend the shim's own directory to PATH
  and prove invocation with a `--version` run, not by reading the file. Dependability watch
  list: self-tracking lag (sample 8, not recurred) and **disposition-vs-severity
  inconsistency** (sample 9: verdict BLOCK with no blocker-severity finding — the
  instrument may reach for the strongest disposition its own taxonomy doesn't support).
  **Sol review protocol v2 (07-27, adapted from the harness /code-review method)** — the
  funnel shape for ALL judgment-review families (in-session teams, pinned reviewers, scoped
  audits' judgment halves → Sol xhigh; runtime attestation, authoring, and chain equip
  feedback stay native): (1) cheap PRE-FLIGHT triage (skip closed/draft/trivial/already-
  reviewed — SUPERSEDED for the stage-0 lane by `DEV_LOOP.md` §1a: `draft` is never skipped
  there, drafts being that lane's entire subject; `trivial` routes to its premise checklist;
  `closed`/`already-reviewed` stand; the stage-0 lane is also a documented SINGLE-CHARTER
  exception to steps 3-4 below — one red-team one-shot, its same-thread confirmation re-pass
  serving as validation); (2) scoped-guidance collection (only the entry-contract files governing the
  changed paths); (3) DISTINCT-CHARTER lenses as separate one-shots (guidance-compliance
  with exact-quote citations; diff-scoped bugs; introduced-logic/security), few-concurrent;
  (4) **independent VALIDATION pass** — every finding re-examined by a fresh thread charged
  to refute it; unvalidated findings are filtered, not hedged; (5) verdict via schema with
  full-SHA citations. **High-signal doctrine riding every lens prompt**: objective defects
  and unambiguous quoted-rule violations only; explicit false-positive list (pre-existing,
  linter-catchable, pedantic, silenced, unverifiable-without-outside-context); *if not
  certain, do not flag* — this is also the standing treatment for the disposition-overreach
  blemish. **Ruling red-team lane (pilot — WIDENED 2026-07-28)**: on orchestrator/director wakes that issue
  policy-shaping, irreversible, or batch rulings, the drafted rulings go through one Sol
  xhigh adversarial pass BEFORE sending — best-reasoning adversarial pairing at the top of
  the stack, complementing the incremental reviews near the details. The stage-0 protocol
  (`DEV_LOOP.md` §1a) extends this lane to every full-pass-class design artifact; the pilot
  scoping in this paragraph is the historical origin, not the current boundary.
  **Rollout law (learned by violating it): a protocol is not live until its invocation tool
  exists and is reachable from every seat it binds** — announcing a funnel whose
  speaking-tool is absent at the bound seats is law 9's composer clause violated by the
  rollout itself (two seats blocked honestly rather than approximating; the funnel ran
  interim through the dispatcher until the wrapper shipped).
  **Coverage caveat riding every promotion claim**: "structurally more reliable" is about
  DELIVERY, not coverage — all samples to date are static analysis (no runtime in the
  review environment; the instrument declares this itself in not_checked, which is a
  dependability credit). A one-shot review cannot tell you a test passes; runtime-backed
  claims still require a runner.

### 3a. Runtime wake/launch adapter facts (2026-07-28, doorbell ratification)

The SEAT_PROTOCOL §4 invariant (actionable async work: supervised + durable terminal
outcome) is runtime-neutral; the MECHANICS live here per runtime.

**Claude harness — empirical notify table (measured in-fleet, 2026-07-28):**
| Launch shape | Wakes the seat? |
|-|-|
| foreground command exceeding tool timeout | yes — harness rescues + task-notification |
| tracked background (`run_in_background` class) | yes — notification on exit |
| subagent completion | yes |
| scheduled wake (timer) | yes |
| `nohup … &` detach | **NEVER** (4+ review runs recovered only by manual polling) |

Claude seats therefore MUST launch actionable EXTERNAL side processes via the
tracked-background mechanism only; raw detach is forbidden (origin rule 01KYK8TC8P).
In-session subagents are NOT in this rule's scope — they remain governed by
`SEAT_PROTOCOL.md` §4/§5 native delivery and appear in the table only as an observed native
wake source. The tracked notification satisfies SUPERVISION for the invoking session only —
DURABILITY additionally requires the completion event (`HUB_DATA_MODEL.md` §3a), which is
what survives session death. Behavioral evidence: the rule's own author reflexively
detached a run twenty minutes after ratifying the ban (self-caught) — enforcement belongs
in the Stop-hook/conformance class, not discipline.

**Codex runtime**: UNVERIFIED — the notify table's Codex column is a Phase-4 pilot probe
(exec-resume/tmux invocation, modal handling, whether any launch shape notifies at all).
Until the probe runs AND the `complete` verb exists, Codex seats have NO conforming channel
for async results — a named Phase-4 pilot blocker, not a silent gap.

**Interrupt-filter ownership (SEAT_PROTOCOL §4 filter)**: per-seat-class mappings and the
wake-policy inputs (`mail_grace`, poll budget, per-class cursor-commit SLOs, fallback
interval) WILL be authored matrix values — the schema fields land with the Phase-3 matrix
regeneration (the same wave as `review_families`), written future-tense here per the
both-tenses rule. `max_deferral` is never authored in any wave: it is derived from those
inputs under SEAT_PROTOCOL §4's compositional constraints. Until Phase 3, implementations
take interim per-fleet values; the CONSTRAINTS bind now, the data shape does not exist yet.

## 4. Supersession

Shipping this matrix **supersedes the 2026-07-24 "one model, two efforts" policy**. The
shipping PR must: record the supersede in the policy memory + user CLAUDE.md pointer, extend
the launcher to every tier in `tiers:` (it currently hardcodes two), correct the stale
harness default model, and regenerate all generated consumers. Until that PR lands, 07-24
policy stands.

## 5. Routed review findings dispositioned here

- Generated-config source-of-truth ambiguity (major): §1 — categories + precedence; rosters
  are runtime state, excluded from freshness gates.

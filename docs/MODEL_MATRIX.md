# Model / Effort Matrix

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §6. The matrix is DATA, not
> prose: one authored source, generated consumers, zero hand-edited policy tables.
>
> **Implementation status (2026-07-28 confirm-pass): everything §1 describes is the Phase-3
> GENERATION TARGET, none of it exists yet** — verified at writing: no `matrix*` input or
> resolved file, no `policy.yaml`, no generated `.rules`, no Codex profile in
> `~/.codex/config.toml`, in this repo or the consuming project. Until Phase 3 ships, §3b
> "What actually constrains a seat TODAY" is the honest statement of live bounds.

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
| orchestrate (O/director), integrate (I) | claude fable-5 @ xhigh + frequent Sol xhigh consulting | 07-27 user correction (opus-as-O over-engineered); Sol is the standing second brain. **ROUTING VALUES, not eligibility restrictions** (§3b): any thinking-tier runtime may hold these seats, and a Sol thinking seat issuing dispatches is in-contract |
| design/guidance authoring, docs baseline | claude fable-5 @ xhigh | SWE-bench-Pro lead; no overthink caveat; 2× cost worth it for irreversible decisions; "Fable authors guidance" rule — same §3b reading as the row above: ROUTING VALUE, not an eligibility restriction; Sol authoring at tier is in-contract, fable-class is the preferred default |
| implement, explore, capture | claude opus-5 @ medium, EXECUTE register | 07-27: medium for clean execution; the register (implement per instructions; judgment → short packet to director, resolved with Sol xhigh; outcome-not-essay reports ≤~30 lines) holds the thinking boundary |
| diagnostic | fable-5 @ xhigh (thinking tier, per the 07-27 correction) | audits/diagnosis are thinking work; the official escalate-on-shallow-reasoning guidance argues for starting high enough, and effort ladders within a session break prompt caching — so the tier IS the escalation, applied at dispatch time |
| docs maintenance | sonnet-5 @ medium (AFTER hierarchy ships) | two-tier synthesis ruling |
| cross-review | fable-5 @ xhigh + codex sol @ xhigh second opinion (thinking tier) | standing cross-runtime lane |
| codex seats | gpt-5.6-sol @ xhigh (thinking/judgment/dispatch) / **medium** (doing) | **TRUST PARITY, user ruling 2026-07-28 (§3b)**: Sol is a thinking-tier PEER of the Claude thinking model, not a restricted pilot guest. Doing tier corrected 2026-07-29 to track the 07-27 low→medium raise the Claude rows already carry (profiles jauto-thinking/jauto-doing built to this; Sol default LOW is the provider default, never our doing tier); ultra excluded (auto-delegation) |

Rules that ride along: hold effort constant within a session (prompt cache); raise effort on
demonstrated shallow reasoning rather than prompting around it; `max`/`ultra` are not in the
matrix (xhigh>max data; ultra self-delegates).

### 3b. Cross-runtime trust parity (USER RULING 2026-07-28)

**The second-runtime thinking model holds the same standing as the first-runtime thinking
model.** Concretely on this fleet: Sol @ xhigh is a peer of Fable @ xhigh — it may hold a
seat, receive and issue dispatches, author and ratify at its tier (subject to the epistemic
invariants below — authoring and ratifying the SAME artifact remains forbidden on every
runtime), and may be granted tool access on the SAME TRUST BASIS as the first runtime —
the actual reachable surface is runtime- and session-specific (sandbox grant, PATH,
credential reachability, runtime configuration; the verified-surface record below is the
current measurement), never a function of runtime identity. It is not a read-only guest whose write scope is earned later. Dispatch hierarchy
descends from EITHER thinking-tier runtime to the doing tier; a Sol-issued dispatch binds a
doing seat exactly as a Fable-issued one does.

**Why (user, verbatim intent):** the fleet runs on a local development machine as one team;
trust is granted to the CLUSTER, and judgment about what is destructive belongs to the
thinking tier rather than to a permission list that tries to enumerate it.

**What this does NOT relax.** The surviving constraints bind **every seat at every tier,
including the first-runtime thinking model and the director** — but they are TWO DIFFERENT
KINDS of rule and conflating them was an error in this section's first draft (caught by its
own stage-0 red-team):

*Coordination / blast-radius invariants* — about serialization and reach, not judgment:
- **Merge serialization**: only the integrator seat merges. The director does not either.
- **Shared-environment mutation**: staging/production DDL, migration application, and
  destructive infrastructure operations follow the project's guarded paths.
- **Shared-workspace safety** (multi-seat machines): a seat does not destroy another seat's
  uncommitted work (`reset --hard`, `clean`), mutate shared git state (common refs, hooks,
  config) out from under a live branch, corrupt another seat's heartbeat/lease/cursor state,
  or consume another seat's mailbox. None of these require a merge or a DDL, so the earlier
  four-item list did not cover them.
- **Self-applied fleet guidance**: a seat does not edit the standing rules or entry contract
  that governs it without ratification — the loop that closes here is a real one.

*Epistemic invariants* — these DO exist because judgment can be biased, and they apply to
every runtime for exactly that reason:
- **No self-verdicting**: nobody reviews their own work. **Independence means a FRESH
  CONTEXT that did not author the change — not a different runtime**; a continuation-capable
  session on another runtime is not independent, and the first draft's claim that a second
  runtime "satisfies independence structurally" was wrong.
- **Actor reports are not evidence** (`CONTEXT_CONTRACT.md` §5a): a claim about what was done
  is not verification that it was done, whoever makes it.
Applying these equally to the director and to both runtimes is consistent and correct;
denying that they exist because judgment is fallible would not be. Trust parity means the
same standard for everyone, not the absence of a standard.

**What actually constrains a seat TODAY, stated honestly** (the first draft implied
generated-policy enforcement that does not exist): launch-time sandbox and approval settings,
the entry contract and standing rules the seat reads, host-level permissions, and
provider-side controls. Generated Codex profiles, `.rules` execpolicy, and pinned agent
definitions are **planned** (Phase 3 generation from this matrix); MCP is unconfigured. Until
those ship, do not describe seat authority as policy-bounded — it is bounded by sandbox,
instruction, and host, and the honest gap between those is why the orientation work below is
load-bearing rather than decorative. The **threat model remains a planned spec**
(`ARCHITECTURE.md` §9), so "existing ceremonies" covers the merge/deploy/migration paths that
demonstrably exist and NOT the full irreversible-action surface a credentialed seat can
reach (force-push, ref deletion, repository settings, package publication, credential
disclosure) — those are named here as an open gap rather than implied to be covered.

**The intended safety mechanism is ORIENTATION rather than enumeration — a DESIGN GOAL, not a
current control.** A permission list tries to
predict every destructive act in advance and fails at the first unlisted one. A seat that has
been *properly initiated into the project* — guided context exploration, entry contract to
domain index to leaf, understanding what the system IS and what depends on what — is
hypothesized to infer correctly at the unlisted case, because it understands consequences
rather than matching patterns. **That bet is not yet evidenced**: orientation maps are a Phase-1 design with pilot
and sequencing work outstanding, and no observable initiation or correctness criterion exists.
Naming the criterion is part of the work — orientation is demonstrable only when a seat can be
shown to DERIVE a constraint it was never told, and that test does not exist yet. Until it does,
this is what the context-delivery system is being built toward; the operative constraints today
are the ones named above (sandbox, entry contract, host permissions, invariants).
Design consequence, binding on the orientation work (`ORIENTATION_MAPS.md`,
`CONTEXT_CONTRACT.md`): the goal is a seat that could DERIVE the invariants, not one that has
memorized them. Entry contracts therefore route to understanding (what this system is, what
is shared, what is irreversible, where the blast radius lives) rather than reciting
prohibitions; prohibition lists are a fallback for what orientation has not yet covered, and
each one is a signal that some pathway is missing. This is stated so the specs are *built*
toward that goal — whether correct pathways in fact produce correct operation is precisely
what the readiness criterion above must demonstrate; it is the design bet, not an
established property.

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

**Sandbox posture follows trust, with two rules that close a loophole.** Trust parity means
the sandbox is sized to the WORK, not to the runtime: read-heavy work runs read-only because
that is sufficient, and work requiring writes gets write scope without a separate trust
argument. **Sizing authority belongs to the DISPATCHER, at launch — never to the seat being
sandboxed.** A seat may request a wider sandbox with its reason; it does not widen its own,
and a probe that hits a sandbox denial reports the denial rather than re-running itself
unsandboxed. (The re-probe is a legitimate act — performed by the dispatcher, which is how
both 2026-07-28 misdiagnoses were actually corrected.)
Caveat, evidence-grounded: a sandboxed runtime cannot prove the machine's capabilities — two
consecutive probes misread sandbox denials as machine/auth defects (a network-denied
`gh auth status` read as an invalid token; a snap/DBus denial read as a broken gcloud that
works fine unsandboxed). **A sandboxed negative is never a machine finding until an
unsandboxed control confirms it** — and that control is run by the dispatcher.

**Verified surface at ruling time** (artifacts: `~/.jauto-orchestration/sol-runs/`
`2026-07-28-codex-tool-surface-{probe,validity}.json`; both controls passing, tree-verified
no writes): authenticated end-to-end from a Codex process — GitHub CLI (push+admin scopes),
private git transport, Supabase (prod+staging), Vercel (team scope), Codex's own session.
Open: npm unauthenticated (publishing only); Twilio key-class question; **gcloud unusable
under the Codex sandbox (snap needs a DBus transient scope) though fine unsandboxed — the one
concrete capability gap, fix = non-snap install or a sandbox allowance**. Codex-side MCP
config is empty by default; MCP grants are a deliberate per-profile addition, and because
a seat launched as this user can REACH much of that surface (bounded by sandbox grant, PATH,
credential validity and runtime config), per-profile config WILL BE subtractive (what to deny)
rather than additive once profiles exist — they do not yet.

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

**Codex runtime — empirical notify table (measured in-fleet 2026-07-29, codex-cli 0.145.0;
probe artifacts `~/.jauto-orchestration/sol-runs/codex-notify-probe-20260729T072309Z/`,
re-runnable via `scripts/codex-notify-probe.sh`, seat b):**

| Launch shape | Wakes the seat? |
|-|-|
| `codex exec` one-shot, `notify` configured | **yes** — notify program runs on turn completion |
| `codex exec resume <id>` headless poke | **yes** — poke lands in the SAME thread; notify fires on completion |
| interactive TUI pane + `tmux send-keys` | delivers (an INVOCATION channel, not a notify channel) |
| interactive TUI, no notify configured | unprobed |

`notify` is a top-level config key taking a program vector (`-c notify='["/path/prog"]'`),
invoked with one argv holding an `agent-turn-complete` JSON payload carrying `thread-id`,
`turn-id`, `cwd`, `client`, `input-messages`, and `last-assistant-message` — enough to route
a completion to a seat AND to record a durable terminal outcome, not merely a ping.

**The named Phase-4 blocker is cleared on the CHANNEL half**: Codex has a completion
channel. Durability still additionally requires the `complete` verb (`HUB_DATA_MODEL.md`
§3a), unchanged and outstanding — the blocker narrows, it does not vanish.
`remote_answerable` = true for tmux-hosted panes (measured: send-keys reached the TUI and
the model answered) — under `SEAT_PROTOCOL.md` §3's modal policy that permits unattended
resume for Codex seats launched in a tmux pane, and only there. Profile resolution
transfers from `codex exec` (where the launcher's pre-boot tier probe measures it) to the
interactive session where the seat runs — observed (`--profile jauto-doing` TUI header:
`gpt-5.6-sol medium`), no longer argued.

**Interrupt-filter ownership (SEAT_PROTOCOL §4 filter)**: per-seat-class mappings and the
wake-policy inputs (`mail_grace`, poll budget, per-class cursor-commit SLOs, fallback
interval) WILL be authored matrix values — the schema fields land with the Phase-3 matrix
regeneration (the same wave as `review_families`), written future-tense here per the
both-tenses rule. `max_deferral` is never authored in any wave: it is derived from those
inputs under SEAT_PROTOCOL §4's compositional constraints. Until Phase 3, implementations
take interim per-fleet values; the CONSTRAINTS bind now, the data shape does not exist yet.

**Seat-control budgets (`SEAT_PROTOCOL.md` §2a)**: `effect_commit_budget` — per ACTION
CLASS, the minimum remaining lease validity an effect-commit must hold across
validate→effect→record — and `hb_write_deadline` (the bounded heartbeat write) are
likewise matrix-authored values whose schema fields land with the same Phase-3
regeneration, written future-tense here per the both-tenses rule. Until Phase 3,
implementations take interim per-fleet values; the §2a constraints bind now.

## 4. Supersession

Shipping this matrix **supersedes the 2026-07-24 "one model, two efforts" policy**. The
shipping PR must: record the supersede in the policy memory + user CLAUDE.md pointer, extend
the launcher to every tier in `tiers:` (it currently hardcodes two), correct the stale
harness default model, and regenerate all generated consumers. Until that PR lands, 07-24
policy stands.

## 5. Routed review findings dispositioned here

- Generated-config source-of-truth ambiguity (major): §1 — categories + precedence; rosters
  are runtime state, excluded from freshness gates.

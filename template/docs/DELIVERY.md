# Delivery field manual

Use this at an ordinary work boundary, alongside the project's governing entry
instructions. It consolidates the handoff summary into the existing work record;
it adds no approval step, status store, hook, or mandatory per-turn form.
JV owns the portable behavior. Products supply field evidence and opt into useful
changes independently. Extract local improvements when cheaper than maintaining
them locally; neither migration nor portable development is a product prerequisite.

## Start from one delivery reference

The accountable lead carries these facts in the existing dispatch, issue or work
record. Link that record through authoring, review, integration and capture instead
of transcribing another status account:

1. Owner outcome and one observable next checkpoint.
2. Work identity, exact subject/revision, bounded scope and exclusions.
3. Finite acceptance requirements, each with its affected gate and evidence links.
4. Current result, limitations and material changes since the previous decision.
5. Next permitted action, responsible person/agent, authority and decision deadline.
6. Required governing inputs and relevant source/test paths; details by reference.

Follow required entry reads. Start with current assignment and governing inputs,
then inspect affected source and dependencies. Expand context to resolve a concrete
uncertainty; do not add archive reconstruction or a new reading attestation. Preserve
mandatory state updates until the project explicitly consolidates them. A digest
helps navigation; source, accepted requirements and authorized decisions control.

Use project-qualified identities, for example `PROJECT-O` and `PROJECT-I`. Existing authority
assigns responsibilities; a name grants none. One lead owns the decision, authors
produce, independent reviewers check their commissioned scope, and the assigned
integrator integrates. Provider/model/session are provenance, never role semantics.
Use the runtime's existing permitted tools; do not borrow another seat's mailbox.

## Classify exposure before choosing the work

These tiers guide decomposition and proposed assurance. They do not override a
project's existing classification, required audits, assertions, or effect gates.
Record any desired policy exception for its authorized decision-maker explicitly.

| Tier | Actual exposure | Smallest useful path |
|---|---|---|
| R0 | Read-only inspection or local document analysis | Answer the bounded question from current evidence. Preserve source/unknown distinctions. |
| R1 | Reversible source edits or an empty, disposable local experiment | Named outcome and operator, meaningful executable checks, required independent checks, bounded correction. For experiments establish containment first. |
| R2 | Shared integration, persistent test data, application schema or shared services | Explicit integration owner, compatibility/rollback evidence, affected acceptance and target checks. |
| R3 | Production, financial/customer/provider actions, credentials, destructive or external effects | Retain strict authority, independent assurance, target-specific preflight and fresh effect approval where required. |

Use the highest applicable exposure. A one-line financial change can be R3; file
count alone cannot establish risk. An unfamiliar target or uncertain containment
does not qualify for the disposable fast path.

For R1 experiments: use an existing authorized local route, dedicated empty target,
synthetic inputs, no customer data/credentials, no exposed listener, no persistent
host database volume, enforced resource/time limits, and exact-target cleanup.
Freshly check actual host resources, isolation, ownership and access. Carry the
standing substrate grant when applicable; do not ask the owner again for the same
grant. A substrate grant is separate from this attempt's admission. Keep the
project's required scope audits, runner RED/GREEN and reviewer checks. Test harness
clock boundaries and cleanup failure paths cheaply before a scarce runtime attempt.

## Evidence packets: one tool, one manifest

A new evidence packet is sealed with `scripts/evidence-seal.py seal <dir>` and checked with
`scripts/evidence-seal.py verify <dir>`; cite the printed `manifest_sha256` in the record that accepts the packet, and
keep that record outside the packet (or under a path declared in `.sealignore`). Hand-built manifests are retired
for new work: never write, append to or edit `SHA256SUMS` by hand — reseal with `--reseal`, which prints the delta.
`sha256sum -c --strict SHA256SUMS` remains the independent verification and the fallback when the tool is absent.
The tool makes a complete content manifest; it does not decide what belongs in the packet, semantic acceptance,
effects, permissions or immutability — those stay with the lead and the gates. Existing packets are never resealed
or rewritten to fit this rule; it binds new packets only. Where a fleet installs the released tool outside the
project (the JV upstream document `docs/ADOPTION.md` in the justinventit repository describes that shared-install
shape; it is not rendered into projects), the fleet's pinned path is the default for the same rule.

## Reuse evidence at its actual granularity

Accept a named requirement at a named level: design, implementation, integration,
rehearsal or enabled behavior. Record execution outcome and operational exposure
separately. A completed task or clean cleanup is not a passing functional proof.

For static reviews and tests, retain the exact original subject, evidence and
accepted decision. Reconsider applicability when relevant code, tests/oracles,
configuration, dependencies, requirements, environment or material findings change.
Elapsed wall time and an unrelated documentation edit do not alone erase evidence.
Old tests remain tests of the old revision; input equality does not claim a new run.
Use whole-subject scope if a dependency footprint has not been established.

`python3 scripts/evidence-delta.py BEFORE AFTER --input src --input tests`
compares local committed Git inputs and reports all changed paths plus the selected
subset. Omit `--input` for the whole tree. A directory includes new and deleted
descendants. List all relevant tracked inputs, including lockfiles and requirements;
the helper cannot discover completeness. Include `.gitattributes`, `.gitmodules`
and LFS configuration when applicable; blob identity does not establish the actual
checkout bytes tested after filters or EOL conversion. It rejects selected symlinks/submodules
and unknown paths. Checkout state is explicitly unknown: it does not inspect staged,
unstaged, untracked or ignored files, or invoke Git status/content filters. Its report
describes commits, not uncommitted work, live runtime,
review completeness, or permission. Exit 0 means a report was computed, including
when inputs changed; exit 2 means unavailable. Neither grants acceptance or action.
It refuses inherited Git repository-selector variables, including those set by Git
hooks; run it from an ordinary environment with those selectors unset. On unavailable
input, use normal source inspection; never drop dependencies to obtain unchanged.

Use the report to focus the lead's applicability decision in the same record.
Refresh runtime identity, live resources, credentials/permissions, revocations,
deadline and target facts at the point required by the existing gate. Exact-head
integration checks remain exact-head checks. No time-based automatic renewal.

Instrumentation has its own result: distinguish a behavioral failure, an unavailable
measurement and incomplete execution. Retain independently supported observations
with their limits; missing evidence still blocks its affected gate. A safety monitor
failure must stop work when safety depends on that monitor. Never disable it to
finish a proof. Use one shared elapsed clock domain for age checks, reject missing,
future or stale samples, and retain the actual read/observation clocks on refusal.
UTC belongs to chronology and absolute authorization deadlines. Correct bookkeeping
without rerunning safe work unless the evidence needed for that work was affected.

## Close correction loops with a decision

Each blocker names the accepted requirement/invariant, concrete failure or credible
counterexample, earliest affected gate, and smallest discriminating check. The lead
records block-now, later-proof, owned follow-up, or rejected with reason. A new
guarantee requires scope disposition. Sibling work proceeds when unaffected.

Each correction has one purpose and a decision deadline. At the deadline choose
the next lawful proof, justified scope change, or a named blocker with owner and
next decision date. After two failures at the same gate, challenge the diagnosis
and harness before buying another unchanged round. No automatic restart or pass.
Fresh independent audits establish independence; a focused correction confirmation
should cover the change and regression risk under the project's required rules.
Do not add duplicate reviews without a distinct required question.
Correction cardinality, bounded code-fix re-review and provider bookends/availability
are defined once in `REVIEW_PRACTICE.md` §4 and §6. Preserve the project's initial audit
count, independent roles and effect gates; neither a deadline nor unavailable provider
supplies a missing completed opinion.

Capture what changed, scoped acceptance, evidence/limitations, exposure and the next
owner checkpoint once through the required project path. If recording fails, retain
the result and report the recording boundary through the existing fallback; do not
claim it was recorded. Never turn local counters into overall completion percentages.

## Check orientation and cost without building a reporting system

Give fresh agents from two available providers this same manual, the same bounded
work reference, and this unhinted request: **Identify the owner outcome, current
work, accepted scope, actual exposure, governing authority and next permitted
action. Name uncertainties.** Judge factual agreement, missing authority assumptions
and source choice; do not demand identical prose. Record unavailable providers as
untested. Runtime packaging differences belong in adapters.

At the next two delivery boundaries use existing timestamps/records to compare
lead time to useful execution, handoffs, distinct review charters, correction
attempts, reopened decisions and why. If effort durations are available, compare
implementation/testing minutes with coordination/rechecking minutes. Unknown effort
stays unknown. Success means faster useful proof with retained invariant coverage
and no escaped defects; fewer files/findings alone do not establish improvement.
Remove optional steps that add maintenance or duplicate records without improving
those outcomes. No dashboard or new mandatory metric event is required.

## Active milestone and standing authorities

Maintain one project-owned `docs/FOCUS.md` under 60 lines: owner outcome, ordered steps
with one owner/state each, the Lane, queued next, parked work and capacity/CI lane order.
It may live host-local instead (AGENTS.md names the path) when edit cadence or customer
data rule out the repo; cloud and clone sessions then get the active row in their dispatch.
Re-read it at ordinary boot and before dispatch; update a line when state changes, with
detail linked elsewhere.
Only business decisions go to the owner. Technical/process decisions go to the director
as a short packet or use an existing standing authority. Prioritize by actual exposure;
a single-user pre-public deployment does not acquire an internet-facing threat model by
analogy. Existing security, correctness and effect gates remain binding.
Why: the owner-visible milestone was getting displaced by ceremony and speculative work.
Origin: **JA, 2026-09-30**, `FOCUS.md` and `PONYTAIL-BOOT-v1.md` Notch-up.

A pre-scope workstream keeps ONE source index (requirements, evidence map, dated field
examples; host-local when it holds customer data). Fragments join it as a dated file plus an
index row, never a new issue or epic; a FOCUS row, a hub thread `next_gate` and one anchor
issue titled with the group's name each point at it. Scoping materializes the epic from it.
Why: a related idea spawned a duplicate epic. Origin: **JA, 2026-10-07**, DEV-STRUCTURE-PLAN §0b.

After ruling a recurring mechanical failure class, the director can grant a bounded
standing authority: named holder, exact predicate/evidence, permitted action, invalidations
or expiry, and escalation on mismatch/recurrence. Record each use on the existing PR/work
record; preserve raw failures and distinguish qualification from PASS. A grant is not a
general retry budget, assertion waiver, merge permission or production-effect approval.
A later hold must reach the holder before it can countermand the grant. Do not ask again
when its conditions still hold; otherwise send the smallest decision packet to the director.

The following are **historical JA examples, not grants to a generated project**. Adopt
only a pattern the project's authorized director has actually ruled:

| Origin example | Predicate and bounded response |
|-|-|
| SA1, 2026-09-29 | Metadata/review-only inventory drift: sanctioned regeneration, verify the gated diff, PR note. |
| SA2, 2026-09-29 | Exact gateway-5xx setup signature with an earlier hosted pass and identical fixtures: classify once; recurrence is filed, not retried. |
| SA3, 2026-09-29 | A later commit changes no runtime, tests, workflows, dependencies or SQL: qualify existing proof by the complete relevant delta; do not call it a new run. |
| SA4, 2026-09-29 | Local failures match a merge-base control with unchanged tests/helpers: retain raw FAIL, require hosted PASS; new failure or changed blob escalates. |
| SA5, 2026-09-29 | Generated-artifact freshness failure: documented regeneration from clean scratch, generated-only diff, one batched follow-up after terminal CI; other deltas escalate. |
| SA6, 2026-09-30 | One default-timeout failure and every other check passes: one whole-file rerun at the same head; record qualification, expire on the systemic fix. |
| SA7, 2026-09-30 | Exact post-seed restart/502 sequence: require exact migration-version set, timely service health and relevant live predicates; retain qualified raw failure, expire on the fix. |
| SA8, 2026-09-30 | Read-only migration-validation race: lag is exactly the newly merged migrations and fresh readback proves catch-up; rerun that job once, second red escalates. |

Why: mechanical snags caused repeated director round-trips and duplicate diagnosis.
Origin: **JA, 2026-09-29–30**, `feedback-ceremony-tangle-standing-authorities.md`,
`standing-authorities-canonical.json` (SA1–5), integrator handoff (SA6–8); primary SA1–3
ruling `01M3PN19EJZM301TM52NBG31S4`. Project-specific paths, fixtures and live grants stay
with the source project; these examples supply no runtime configuration.

## Seat communication

Commissioned seats drain **their own** mailbox on boot/wake, at every implementation ↔
check handoff and phase boundary, and immediately before acting on a dispatch delayed
roughly ten minutes or more. Drain and reconcile first, then act: never batch substantive
work with the drain. A scheduled wake is a snapshot, so a current hold/reprioritization
wins. Read every new message; when output is persisted or truncated, read the whole saved
output from its beginning and reconcile all mailbox section headers. A preview or newest
message is not a complete drain. Ad-hoc sessions follow direct user work and consume no
commissioned seat's mail. Use the project's installed transport; this guidance alone does
not install a mailbox or move its cursor semantics into this document.
Why: stale wake intent raced a hold, and consumed-but-unread output hid delivered blockers.
Origin: **JA, 2026-04-30** chain-handoff incident (PR #2035), **2026-05-18** stale dispatch
(PRs #2353/#2354), **2026-05-31** parallel drain/action (Epic #2249), and
**2026-07-10 / 2026-09-30** `persisted-drain-output-skip-trap.md`.

Mail the director only at milestones: CI terminal, landed, blocker or a decision outside
standing authority (plus a deliverable explicitly requested in the dispatch). No ACK,
“recorded” or “adopted” messages. Lead with outcome and the one decision needed; evidence
belongs in the linked PR/packet. Existing dispatch-specific START/END protocols still apply.
Why: every mail wakes an expensive director context; repeated acknowledgements burned
capacity without advancing the outcome. Origin: **JA, 2026-09-28**, milestone-mail ruling
`01M3KM7X69GARREETG41VVZE7E`; **2026-09-30**, Ponytail reporting addendum.

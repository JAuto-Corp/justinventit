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

Use project-qualified identities, for example `JV-O` and `JA-O`. Existing authority
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
Cardinality binds the INITIAL audit of a subject; every subsequent correction owes exactly one focused confirmation at the corrected exact head, by a fresh context that is not the author, covering the change and its regression risk — the correction is the distinct required question. A further full-cardinality round is owed only when the correction adds a guarantee or changes scope (scope disposition). After two failures at the same gate the existing rule applies first — challenge the diagnosis and harness before buying another round of any size; no round is automatically owed. A confirmation on a predecessor head never covers the merged head.
**Provider bookend.** Where two runtimes are configured, a change at an R2/R3 boundary (the exposure tiers above — that table is the canonical classification) is touched once by each runtime's thinking-tier model across authoring, challenge (spec-audit or review) or acceptance — distinct roles and questions count; a duplicate full review does not. For other judgment-bearing changes, an author and an independent reviewer from different runtimes satisfy it at any tier; trivial, mechanical, reversible work with deterministic checks owes none. A runtime's unavailability never stalls independent work: proceed at the authorized equivalent tier and record `bookend: <runtime> missing` in the acceptance record. No further round is owed unless the head or the contract changed or a named blocker remains (**Corrections**); stricter gates win.

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

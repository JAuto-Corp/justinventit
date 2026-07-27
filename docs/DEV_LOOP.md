# Development Loop

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §5. Maps responsibilities onto
> loop stages and seat classes; defines the mandatory gates and escalation pathways.

## 1. The loop

| # | Stage | Owner (seat class) | Artifact | Gate (exit condition) |
|-|-|-|-|-|
| 1 | scope | design_authoring (fleet: O routes; solo: the session) | SPEC.md + SCENARIOS.md + grounding citations | SPEC self-check: every named API/number/consumer claim cited or refused |
| 2 | spec-audit | cross_review — cardinality, second-opinion, and separation rules per THE normative profile table (`ARCHITECTURE.md` §2) | verdicts, dispositions | all blockers dispositioned; PLAUSIBLE-only findings noted |
| 3 | RED | implement (or test-execution specialist) | executable failing tests + ledger event `kind: red` (canonical schema: `TDD_GATE.md` §3) | Standard+: runner exit non-zero recorded with provenance. Quick scope: may be satisfied as same-change (`TDD_GATE.md` §4 — the one declared exemption) |
| 4 | GREEN | implement | code + ledger event `kind: green` | runner exit zero, same provenance chain |
| 5 | review | cross_review | review findings, fixes | no unresolved actionable findings |
| 6 | integrate | integrate (I) | merge | checks green ON current head (SHA-bound); merge protocol satisfied |
| 7 | document | author of change (baseline: docs_baseline) | doc delta OR explicit `no-doc-impact: <reason>` in PR body | doc gate: delta present or declaration present; generated indexes fresh |
| 8 | capture | any seat | hub `capture` verb (alias over `finding`/`journal`/`doc` with external-tracker refs — `HUB_DATA_MODEL.md` §3) | nothing left only-in-context: every discovery has a hub record |

Stages 3-5 iterate via the chain (`go ⇄ check` relay, convergence math in the chain skill).
Stage 7 is NOT optional and NOT a tail: the doc gate fails the same way a test gate fails.

Named practices (ratified from independent convergent field use):
- **Verify the consequence, not the cause**: confirm the file is on the target branch and
  the gate passed on the target's own run — never that "the PR merged" (four seats
  converged on this unprompted; it caught real gaps every time).
- **Recorded-not-fixed**: a real adjacent defect you deliberately do not fix (to protect a
  valid green, to stay in scope) goes IN THE VERDICT, never only in your head — that is
  what separates a judgment call from an omission.
- **Standing-trigger-is-authorization**: a dispatch trigger stated with explicit CONDITIONS
  and INVALIDATIONS (what voids it: head moved, new red class, freeze declared) IS the
  authorization — re-asking converts it back into per-instance approval and reinstates the
  dependency it removed. "Hold for my word" is the explicit opt-out. **The pattern's cost
  (law 9): a later hold is a deliberate countermand delivered to the HOLDER**, never an
  instruction to a third party.
- **Doc-reality-fix PR bodies**: when a PR fixes a documentation-reality gap, its body
  states which ADJACENT claims are aspirational and where their implementation is tracked
  (else the fix creates the next gap — corrected text beside uncorrected text is
  indistinguishable from all-true); every citation inside the fix is resolved against the
  target branch before commit ("never cite a line in a fix for a miscited line without
  checking it"); and **attribution belongs in the coordination record, state belongs in the
  artifact** — a PR body states what is true about the tree and never litigates fault.

## 2. Responsibilities → seats (overlap by design)

| Responsibility | Seat mapping |
|-|-|
| DIRECT | director seat (authoring tier, user-driven turns): the user↔cluster interaction point; program direction, design authority, directs ORCHESTRATE by mail; ratifies program-level direction. Does NOT touch cluster mechanics. Optional — in fleets without a director, the user interfaces with O directly and design authority sits with design_authoring sessions. |
| ORCHESTRATE | O seat: dispatch, cadence, stall watch, user escalation, queueing. Sole approver of memory/guidance revisions proposed by other seats; takes program directives from DIRECT where present, reports cluster state to it at phase boundaries. |
| SYSTEM DESIGN & BACKEND | design_authoring sessions (fable-class) for SPECs/architecture; implement seats execute them |
| TEST EXECUTION | implement seats own their RED/GREEN; suite/e2e sweeps are dispatched doing-work; results land as evidence events |
| DIAGNOSTIC | an implement seat *escalated* (matrix diagnostic class): hypotheses become durable tests + logging in the SAME PR (diagnostic-in-fix discipline), never prose tracethrough |
| SYNTHESIS / DOCUMENTATION | baseline = docs_baseline (smart model); maintenance = docs_maintenance once hierarchy exists; stage-7 deltas by the change author |
| INTEGRATION | I seat exclusively (merge authority enforced by .rules for codex + protocol for claude) |
| CAPTURE | every seat captures; O triages; periodic label/epic/roadmap reviews are dispatched doing-work |
| CROSS REVIEW | cross_review class: fresh-context audits + codex second-opinion lane; reviewers are NEVER the authoring session |
| FRONTEND | implement seats with frontend charter (design-system conventions, i18n/mobile principles from Layer B skills) |

One seat can hold several responsibilities; a responsibility never straddles two seats
mid-artifact (ownership = dispatch row).

## 3. Escalation pathways

1. Gate failure → owner fixes (normal loop).
2. Same gate fails twice for the same cause → **zoom-out**: question the gate/design, don't
   force through (gate-integrity rule); zoom-outs are authoring-tier work.
3. Judgment call outside a seat's charter (assertion weakening at review, scope change,
   policy touch) → packet to O; work continues elsewhere meanwhile.
4. Needs the user → `attention` verb with severity; blocking severity = broadcast + push
   notification; decisions pre-locked before known absences.
5. Memory/guidance revision → proposed by any seat as a diff, ratified by O (or the
   designated highest-reasoning seat); never self-applied ad-hoc.
6. **Waste loop** (repeated CI runs without new information, retrigger cycles, redundant
   suites, token-heavy fan-outs with low yield, own work burning budget without progress) →
   HOLD the loop and route to the director with evidence. Waste loops look locally
   justified one iteration at a time — the escalation exists so someone sees the loop.
   Composes with gate integrity: a gate you keep re-running is either right, or a defect to
   file — never a toll; and rerun-to-check on an exhausted/flaky resource is
   confirmation-shaped waste.
7. **Route past the evidence node**: when the node you would normally escalate through is
   itself part of the evidence (a stall report about a possibly-stalled orchestrator), go
   around it — "a report that depends on the suspect reading it is a hope, not a report."
   Named expected behavior, never insubordination; the bypassed node is informed once it is
   demonstrably live.
8. **Constraint-vs-mechanism collision** (a seat cannot satisfy both a standing constraint
   and a dispatched gate without degrading one) → DIRECTOR-lane finding; the seat HOLDS and
   routes, never resolves by fiat in either direction. Ratified principle: a constraint
   satisfiable only by degrading the work it governs is a design bug, not a discipline
   problem. Standing resolution for the spawn case: **dispatch-carried spawn
   authorization** — a dispatch naming subagent work (pinned reviewers, auditors) carries
   Agent-tool authorization within its scope; per-instance human approval remains for
   undispatched or beyond-scope fan-outs and implementation-by-subagent. Seat constraints
   yield to dispatch authorization only via this rule, never by self-generalization.

## 4. Profiles

- **solo**: one session holds all responsibilities; audits = fresh-context passes per THE
  normative profile table (`ARCHITECTURE.md` §2 — runtime-neutral: subagent on Claude,
  fresh `exec` thread on Codex); stage 6 = the session with the merge checklist; loop
  unchanged otherwise.
- **fleet**: as mapped above.
- Stage mechanics (which verbs fire, which files update) are identical across profiles —
  only the actor cardinality changes.

## 5. Routed review findings dispositioned here

- L1-only conformance contradiction (blocker, arch-level): §4 — solo profile substitutes.
- CI ownership boundary (minor): gate definitions here are provider-neutral (commands,
  inputs, exit semantics); provider skeletons are adapters shipped by the template
  (`TDD_GATE.md` §5 carries the contract).

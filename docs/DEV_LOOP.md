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

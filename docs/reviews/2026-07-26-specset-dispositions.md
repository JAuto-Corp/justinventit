# Spec-set coherence review — disposition ledger

Source verdict: `2026-07-26-codex-specset-coherence.json` (GPT-5.6 Sol @ xhigh, cross-doc
coherence pass over ARCHITECTURE v2 + 6 sibling specs). Overall: revise.
**Status: R1 LANDED — all 17 rows dispositioned in their owner specs** (this commit).
Notes: #11 resolved by naming three planned specs (ISOLATION_ADAPTERS, VERSIONING,
THREAT_MODEL) in ARCHITECTURE §9 with acceptance criteria — those remain planned M3
deliverables, honestly marked, not claimed complete. Confirmation: R2 coherence pass verdict
archived beside this file; residual R2 findings, if any, tracked below it.

| # | Sev | Finding (short) | Owner for fix |
|-|-|-|-|
| 1 | blocker | Lease acquisition lacks CAS semantics — equal epochs can't fence; split-brain still possible | SEAT_PROTOCOL §2 |
| 2 | major | Hub `roles` vs seat JSON files both claim registry/liveness authority; seat record lacks project_id | SEAT_PROTOCOL + HUB (one seat-control contract) |
| 3 | major | Mailbox: JSONL appends vs hub-derived views ambiguity; possible second failable write | HUB §1 + SEAT §5 (mailbox = recipient-filtered view/outbox) |
| 4 | major | Notification vs processing cursors conflated; doorbell can lose or duplicate work | SEAT §4/§5 (two cursors + ack contract) |
| 5 | major | Recipient isolation unenforced on sqlite/jsonl backends; etiquette ≠ authorization | HUB §4 (or threat-model downgrade: intra-project seats mutually trusted) |
| 6 | major | Conformance profiles inconsistent (cross-runtime lane conditional vs unconditional; Codex-only solo unsatisfiable) | ARCHITECTURE §2 (single normative profile/capability table) |
| 7 | major | RED mandatory vs `same-change` acceptable; `phase:` vs `kind:` schema mismatch | TDD_GATE §3/§4 + DEV_LOOP §1 (one schema, one exit rule per scope) |
| 8 | major | Evidence ledger storage/lifecycle undefined (git self-reference vs CI attestation) | TDD_GATE (new §: ledger storage + SHA-keyed attestation) |
| 9 | major | CHAIN.json / work-state.json / checks 01-05 / pairing-registry source / scope defs / override tokens have no owning spec | TDD_GATE (gate-state contract section) |
| 10 | major | `.agents-manifest.json` both generated and source-of-truth | CONTEXT_CONTRACT §2 (authored region sources + generated lock) |
| 11 | major | Versioning, threat model, isolation lifecycle punted without named owner | ARCHITECTURE §9 (add named specs w/ acceptance criteria; mark open) |
| 12 | major | DB isolation ownership contradictory (L3 framework vs Layer B) | ARCHITECTURE §3 + TDD_GATE §6 (interface=framework, impl=project; name the doc) |
| 13 | major | 32KB law vs 28KB CI + warn-only global — truncation can still occur | CONTEXT_CONTRACT §4 (launch/doctor-time combined check or narrowed law) |
| 14 | major | Claude import precedence algorithm + automated fixture missing | CONTEXT_CONTRACT §3 |
| 15 | major | Policy/matrix authored-input ownership split across three docs; bans restated | MODEL_MATRIX (schemas for questionnaire/overrides/policy) + SEAT §6 (reference, don't restate) |
| 16 | major | `~/.codex/<tier>.config.toml` collides across consuming projects | MODEL_MATRIX §1 + SEAT §3 (project-qualified/repo-local profiles) |
| 17 | major | `capture` stage verb undefined in hub verb set | HUB §3 + DEV_LOOP §1 |

R1 exit: every row dispositioned in its owner spec, ledger updated to point at the
disposition, then the fresh-context spec-auditor ×2 pass runs on the revised set (Phase-1
gate).

## R2 confirmation pass (same day)

Verdict: `2026-07-26-codex-r2-confirmation.json` — 8 residuals (1 blocker, 7 majors),
including 3 contradictions introduced by R1 itself. All 8 dispositioned in revision R2
(this commit): file-backed lease = per-seat flock mutex + full-predicate re-read (versioned
claim files rejected; delayed-racer + renewal-race fixtures added); watchdog routed through
the backend-dispatched seat-control interface; DEV_LOOP solo audits made runtime-neutral;
`red-phase`/`green-phase` naming purged from TDD §4; attestation bundle split per-kind
provenance (green = head, red = ancestor via merge-base); matrix recast as four named
authored inputs → generated `matrix.resolved.yaml`; authoring tier resolvable on every
runtime with fallback chains; single dead-state predicate (lease expiry, process checks
diagnostic-only). Remaining verification: the fresh-context spec-auditor ×2 phase gate.

## R3 — spec-auditor ×2 batch (same day)

Inputs: `2026-07-26-spec-auditor-1.md` (1B/5M/4m, DISPATCH WITH FIXES) and
`2026-07-26-spec-auditor-2.md` (4B/8M, DESIGN ROUND NEEDED; two claims empirically
confirmed by g). All 22 distinct findings dispositioned in this commit:
- HUB §6 migration rebuilt: additive nullable-project_id phase + declared non-additive
  cutover phase w/ dual-write + read-degrading version negotiation (both audits' blocker).
- Leases: revival-window-only; fencing by ULID token equality (kills epoch-reset AND
  equal-epoch classes); reviver→seat token handoff + release-after-first-heartbeat;
  liveness = heartbeats; DEAD = stalled + revival budget exhausted.
- Codex tier verification mandatory post-boot (empirical: missing profile = silent default).
- RED workflow stated (commit-the-red); ancestry bounded to PR range via merge-base;
  push-time attestation bundle defeats rotation; classifier case 4 (in-progress) added;
  exit-code space totalized (crash ≠ pass).
- Budget 26KB + measured 6KB reserve; skill-payload AGENTS.md exclusion list; Claude
  memory in a separate per-runtime health report; >15KB CLAUDE.md shed acknowledged.
- Composer decision table totalized (missing/corrupt/new/removed-upstream branches).
- Matrix: diagnostic = thinking tier at dispatch (no phantom efforts); frontend
  escalate_to:thinking (tier ordering defined); ROADMAP citations re-pointed to ARCH §9.
- jsonl honesty: hub_id-valued cursors, O(n) folds, length-prefixed records +
  truncate-to-last-valid recovery w/ tail-corruption fixture.
- Registry migration section (7 reader sites, dual-write phase); lowercase-canonical
  letter case w/ boundary conversion.
- #3225 autopsy corrected; cross-runtime equivalence fixture added as capstone.

PHASE-1 GATE: both auditors + two Codex passes complete, all findings dispositioned →
**gate CLOSED**. Residual verification rides the implementation PRs' normal review flow.

## R4 — under-fire additions review (07-27, Sol one-shot; verdict: 2026-07-27-codex-delta-underfire.json)

The six incident-driven additions (predicates, heartbeat floor, modal economics, transport,
subagent delivery, multi-resident/sandbox) took 9 majors + 1 minor. **Status: ALL OPEN**,
owner SEAT_PROTOCOL (7) + WORKSPACE_LIFECYCLE (2) + formatting (1). Sharpest: oldest-vs-
newest undrained-mail formula (time-sensitive — checked against D's in-flight P0-3);
heartbeat-floor writer must be a leased canary-wake, never watchdog-authored (false
liveness); parked-revival lease deadlock needs quarantine/supersession + human-unpark;
worktree-rooted sandbox cannot write the common git dir (grant required — Phase-4 gating).
R4 revision LANDED (same day): canonical state enum + THE normative predicate table (§2,
single source; §4 defers); oldest-undrained formula w/ arrivals-never-reset + stuck-oldest
fixture; heartbeat floor = seat-authored via leased canary-wake, external writes banned;
parked-revival outcome (park_ttl, supersede-on-behalf, quarantined old handle,
human-unpark); capability-branched modal policy (resume_modal/modal_detectable/
remote_answerable) + unresponsive_unknown classification; launch table restored;
sender-side hub_id read-back contract (non-consuming, digest-compared); roster-at-spawn +
portable task-record + reorientation block (incl. O's rule-2 amendment); guarded-command
enumeration w/ ack/timeout/lease semantics + remote-ops rewording; common-git-dir grant +
command-policy protection for repo metadata. Lesson ratified: under-fire spec additions get
their own review round before the next consumer reads them.

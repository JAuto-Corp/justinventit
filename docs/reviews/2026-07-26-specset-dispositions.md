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

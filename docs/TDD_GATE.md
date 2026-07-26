# TDD Gate v2

> Phase-1 spec (2026-07-26). Companion to `ARCHITECTURE.md` §8. Rebuilds the test-driven
> gate on the fail-loud law, with evidence that can't lie and enforcement that can't
> silently die. Portable method here; project adapters (DBs, seeds, suites) stay Layer B.

## 1. Why v2 (the autopsy, in one paragraph)

The source system's local gate stack died silently: evidence recorders with zero callers, a
scenario-name regex covering 17% of the suite, gates parsing a state-file format that had
drifted to prose, an advisory CI check whose promotion window lapsed unnoticed — while every
one of them reported success. v2's test is simple: **delete a gate's input and the gate must
complain, not pass.**

## 2. State contract (what gates read)

- Gates read **schema-validated machine state only** — each input has a named owner:
  - `CHAIN.json` — owned by the chain skill (its schema + transition rules; `schema_version`d).
  - `work-state.json` — owned by THIS spec: `{ spec_path, scenarios_path, progress_path,
    scope_class, updated_at, schema_version }`, written exclusively by the levers at phase
    transitions; anything else writing it is a defect.
  - evidence ledger (§3) — owned by this spec; written exclusively by runners.
  - pairing registry — a generated artifact; its authored source is the scenario files
    themselves (the barrel/registry generator derives it).
  - scope definitions — the classifier config (patterns + thresholds), authored, versioned
    with the framework.
  Checks `01-05` (scenarios-exist, type/build evidence, scenarios-executed, red-before-green,
  progress-complete) consume ONLY these inputs, with a uniform exit contract:
  0 = pass, 1 = block (message names the failed rule), 3 = cannot-evaluate (message names the
  missing/malformed input) — and 3 is rendered as loudly as 1, never as success.
- Absent/malformed state: local session → visible warning naming the missing input
  (never brick); CI → fail closed. "Cannot evaluate" is a distinct, visible outcome from
  "pass" EVERYWHERE (exit codes and messages distinguish them).
- Scenario enumeration derives from the **generated barrel/registry**, never a name regex.

## 3. Evidence ledger

Append-only JSONL events written by the RUNNERS (test runner reporter hook, build wrapper),
not by agents:

Canonical schema (every other document references this; `kind` is the discriminator —
no `phase:` variant exists):

```json
{ "kind": "test-run | build | red | green | override",
  "status": "pass | fail",
  "provenance": { "commit": "<sha>", "dirty": false, "worktree": "<path>", "command": "<argv>" },
  "scope": { "suite": "...", "scenarios": ["..."] },
  "mode": "runner",
  "expected_fail": "assertion | infra | null",
  "ts": "..." }
```

- **Provenance binds evidence to the exact revision** — a gate compares the ledger's commit
  to the candidate; stale/unrelated evidence cannot satisfy it. `dirty: true` evidence
  satisfies local gates only, never CI.
- **RED classification**: an expected failure is an *assertion* failure of the named
  scenarios; infra errors (connection refused, missing env) record `expected_fail: "infra"`
  and do NOT count as RED.
- Recorders live inside the runner path every developer/agent actually uses (`pnpm test:*`
  via a reporter, build via the guarded wrapper) — not a parallel path nobody invokes.
- Overrides are events too — `kind: "override"` with `{token, check, reason, actor,
  candidate_sha, expiry, issuer}`; tokens are issued by the orchestrate seat (or the solo
  session, logged identically), bound to one check + one candidate, and expire. Named,
  logged, surfaced in the PR gate summary. No silent bypass exists.

**Ledger storage and lifecycle**: the ledger is **runtime state — never git-tracked** (a
tracked ledger would self-reference the commit hash it must bind to). It lives beside the
worktree (`<state-dir>/evidence.jsonl`, rotated at N runs). It reaches the authoritative
gate as an **attestation bundle keyed to the candidate head**: pushed as a CI artifact (or
regenerated in CI by running the same runners). Within the bundle, per-kind provenance
rules apply: `green`/`test-run`/`build` events must carry `provenance.commit == candidate
head`; `red` events are valid when their commit is an **ancestor of the head** (verified
via merge-base) — RED necessarily predates the fix. Local gates read the local ledger; CI
trusts only what it can attest.

## 4. RED-before-GREEN, correctly classified

The unit of classification is the **scenario/behavior, not the file**. For each behavior
touched by a PR:

1. From the ledger: a `kind: red` event for its scenarios at some ancestor commit, then a
   `kind: green` at a descendant → **RED-observed** (the ideal).
2. No red event but tests for the behavior were added/modified in the PR and pass →
   **same-change**: satisfies the gate for Quick scope ONLY (the declared exemption,
   restated in ARCHITECTURE §5 and DEV_LOOP §1). For Standard+ it is a **block**, not a
   flag — the RED stage is mandatory there, full stop.
3. Impl changed with no test touch and no ledger events → **untested-change** (the
   violation class).

This replaces diff-filter heuristics (the v1 CI classifier compared *added* test files
against *added-or-modified* impl files, misclassifying every PR that edited existing code —
verified defect). Test-touch detection uses the pairing registry (§5), not filename addition.

## 5. Enforcement placement (provider-neutral contract)

| Where | Mechanism | Authority |
|-|-|-|
| Session (Stop hook) | checks 01-05 read state contract + ledger; block once, override-token escape | advisory-strong |
| CI | the same checks run against pushed ledger + candidate SHA; fail closed on missing inputs | authoritative signal |
| Merge | integrator protocol (or branch protection where the plan allows): red = no-merge, SHA-bound | authoritative action |

The framework ships the checks as provider-neutral commands (stdin/env in, exit code +
message out) plus tested adapters (GitHub Actions skeleton). Where required status checks
are unavailable (the source project's plan), the merge-protocol row is the binding one — the
docs must say so rather than imply branch protection exists.

- **Pairing gate**: every scenario has a paired test (registry-derived). Adoption on a
  brownfield project grandfathers existing violations with a **no-new-violations ratchet**
  (count can only go down; recorded in a baseline file).
- **Scope classifier**: pure git-diff path/count heuristic, patterns in config —
  self-classification is not a bypass (label-based bypass requires an O-granted label, logged).

## 6. Layer split

Portable (framework): state contract, ledger schema + reporter hooks, classification logic,
check files + fixtures, ratchet tooling, scope-classifier engine, gate summary renderer —
plus the **DB-isolation adapter interface** (lifecycle, cleanup/recovery, conformance:
`ISOLATION_ADAPTERS.md`, planned M3, per ARCHITECTURE §3).
Project (Layer B): seed/data systems, concrete isolation-adapter implementations and their
config, suite definitions, which runners exist, e2e cadence decisions (e.g. nightly partial
suites), classifier patterns' values.

## 7. Routed review findings dispositioned here

- Evidence staleness/provenance (major): §3 — commit-bound, dirty-flagged, infra-vs-assertion RED.
- Fail-loud vs local-only inputs (major): §2/§5 — authority classification per input; CI fails closed; ledger travels with the push.
- Classifier promotion blocked (blocker, arch-level): §4 — behavior-unit classification replaces the diff-filter heuristic entirely.
- Isolation-adapter lifecycle (major): out of this spec's scope — owned by the L3 adapter
  interface (template M3 deliverable, tracked in ROADMAP; not silently dropped).

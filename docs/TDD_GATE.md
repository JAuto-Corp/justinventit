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

- Gates read **schema-validated machine state only**: the chain file (`CHAIN.json`), the
  evidence ledger (§3), and a small `work-state.json` (current spec path, scenarios path,
  progress path) written by the levers — never prose documents.
- Absent/malformed state: local session → visible warning naming the missing input
  (never brick); CI → fail closed. "Cannot evaluate" is a distinct, visible outcome from
  "pass" EVERYWHERE (exit codes and messages distinguish them).
- Scenario enumeration derives from the **generated barrel/registry**, never a name regex.

## 3. Evidence ledger

Append-only JSONL events written by the RUNNERS (test runner reporter hook, build wrapper),
not by agents:

```json
{ "kind": "test-run | build | red-phase | green-phase",
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
- Overrides are events too (`kind: "override", token, reason, actor`) — named, logged, and
  surfaced in the PR gate summary. No silent bypass exists.

## 4. RED-before-GREEN, correctly classified

The unit of classification is the **scenario/behavior, not the file**. For each behavior
touched by a PR:

1. From the ledger: a `red-phase` event for its scenarios at some ancestor commit, then a
   `green-phase` at a descendant → **RED-observed** (the ideal).
2. No red event but tests for the behavior were added/modified in the PR and pass →
   **same-change** (acceptable for Quick scope; flagged for Standard+).
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
check files + fixtures, ratchet tooling, scope-classifier engine, gate summary renderer.
Project (Layer B): seed/data systems, DB isolation, suite definitions, which runners exist,
e2e cadence decisions (e.g. nightly partial suites), classifier patterns' values.

## 7. Routed review findings dispositioned here

- Evidence staleness/provenance (major): §3 — commit-bound, dirty-flagged, infra-vs-assertion RED.
- Fail-loud vs local-only inputs (major): §2/§5 — authority classification per input; CI fails closed; ledger travels with the push.
- Classifier promotion blocked (blocker, arch-level): §4 — behavior-unit classification replaces the diff-filter heuristic entirely.
- Isolation-adapter lifecycle (major): out of this spec's scope — owned by the L3 adapter
  interface (template M3 deliverable, tracked in ROADMAP; not silently dropped).

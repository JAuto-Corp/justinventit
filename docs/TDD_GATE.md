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
  missing/malformed input), and **any other exit (2, 127, signals, crashes) = runner-error,
  handled identically to 3** — the contract enumerates the full code space so a crashed
  check can never read as success; 3-and-above render as loudly as 1.
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
- **The vacuous-guard class**: an assertion must fail when its SUBJECT IS ABSENT —
  `row?.field ?? null === null` passes when the row does not exist, which is the trust-test
  failure inside a test (it was found living inside a test whose entire job was catching
  silent absence). Assert existence separately before comparing fields; a guard that
  passes on absence protects nothing.
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

**The RED workflow, stated**: local dirty-tree red runs guide the session but are
inadmissible for CI; the admissible RED is produced by **committing the failing test (the
RED commit) and running the suite at that commit** — clean provenance, exit non-zero,
ledger `red` event. This is one extra commit per behavior, by design: the RED point becomes
part of the PR's history and the classifier's evidence.

1. From the ledger: a `kind: red` event for its scenarios at a commit **within the PR's own
   range** — ancestor of head AND descendant of `merge-base(head, target)` (an unrelated
   branch's historical red never qualifies) — then a `kind: green` at a descendant →
   **RED-observed** (the ideal). Rotation cannot evict it: the attestation bundle is
   assembled at push time from the PR range and travels with the PR, independent of local
   ledger rotation thereafter.
2. No red event but tests for the behavior were added/modified in the PR and pass →
   **same-change**: satisfies the gate for Quick scope ONLY (the declared exemption,
   restated in ARCHITECTURE §5 and DEV_LOOP §1). For Standard+ it is a **block**, not a
   flag — the RED stage is mandatory there, full stop.
3. Impl changed with no test touch and no ledger events → **untested-change** (the
   violation class).
4. A `red` event exists and the behavior's tests still fail at head → **in-progress**:
   block with a distinct "RED not yet GREEN" message (not misclassified as any of 1-3).
No PR state falls outside these four; the classifier's own no-match branch is a
cannot-evaluate error, never a pass.

This replaces diff-filter heuristics. Accuracy note (audit-corrected): the v1 classifier's
AM-on-impl side was the *deliberate* #3225 remedy (A-only had made every edit-shaped PR look
impl-less); the residual defect is that TEST detection remained A-only, so PRs modifying
existing test files misclassify. Behavior-unit classification supersedes both sides rather
than reverting the #3225 ruling. Test-touch detection uses the pairing registry (§5), not
filename addition.

## 5. Enforcement placement (provider-neutral contract)

| Where | Mechanism | Authority |
|-|-|-|
| Session (Stop hook) | checks 01-05 read state contract + ledger; block once, override-token escape | advisory-strong |
| CI | the same checks run against pushed ledger + candidate SHA; fail closed on missing inputs | authoritative signal |
| Merge | integrator protocol (or branch protection where the plan allows): red = no-merge, SHA-bound | authoritative action |

**Outage-artifact signature (quota/billing-limit kills)** — a CI red class that is
completely false while looking completely real, landing on your own PR where you are most
primed to believe it. Four markers: (1) ALL jobs in one run fail, not a subset; (2) they
start within seconds and die at start; (3) **the failure set is incoherent with the diff**
— jobs the change cannot possibly affect fail alongside ones it could (this marker stands
alone and works before the outage is known); (4) timestamp coincides with a limit/outage
event. Handling: report and class it, never diagnose or "fix" it — and never rerun-to-check:
a rerun consumes the exhausted resource AND reproduces the failure identically, which reads
as confirmation. During any CI freeze the no-push rule protects more than budget: **a push
destroys a pre-outage green that cannot currently be regenerated** — merge-ready state is
irreplaceable until capacity returns.

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
- Isolation-adapter lifecycle (major): out of this spec's scope — workspace/DB classes and
  registry semantics are normative in `WORKSPACE_LIFECYCLE.md`; the adapter interface is the
  named `ISOLATION_ADAPTERS.md` planned spec in `ARCHITECTURE.md` §9 with acceptance criteria.

## Harness-integrity law (2026-07-28, four independent instances in one week)

A fixture suite proves nothing by passing — it proves something by having been WATCHED TO FAIL
against the unfixed code. Four seats independently shipped harnesses that reimplemented the
logic under test (an extractor's field selection, a gate's regexes, a detector's boundary rule,
a cache writer's guards); every one stayed green while the shipped code was broken, and every
one was caught only by RED-verification or review, never by inspection. Binding rules:
1. Tests invoke the SHIPPED artifact (imported function, executed script, extracted expression)
   — never a local restatement of its logic.
2. Every guard-class test is RED-VERIFIED: temporarily break the shipped code, watch exactly the
   guarding assertions fail, restore. The RED run is evidence, recorded with the change.
3. Where extraction is used (testing a workflow's own regexes), a MUTATION test guards the
   extraction: mutate the source, require the control fixture to go red.

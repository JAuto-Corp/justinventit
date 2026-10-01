# W-C3 review and evidence ledger

## Commission and current gate

O's `01M3V742AADC9P8T8CVTY76SJC` (2026-10-01) accepts W-C2 at
`1d6e3f9d7bf6b03964e854efa58bafb26261d666` and commissions W-C3 liveness,
SPEC first, same review/test flow. W-C2 PR CI `36832519964` passed every step;
duplicate push `36832514595` is terminal cancelled. I owns that integration.

Current deliverable is author GREEN after the accepted SPEC and RED-review folds. The
[SPEC](../specs/W-C3-LIVENESS.md) and dated sections below preserve the pre-code
reading, disposition and new evidence. The generated runtime is implemented;
no source-script execution or independent code acceptance is claimed.

## Reading and reconciliation

The source pin remains `57d273154cf029158b7cc118143808e524baf28c`. The author
read complete cadence/heartbeat/watchdog/propagation bodies and both watchdog
suites through source Git objects, plus the existing generated pacemaker,
heartbeat writer, standby tests and guidance. The private inventory records
hashes and exact read scope; the source-test map labels retained/adapted/excluded
witnesses. No source suites were executed or copied wholesale.

Three differences require an explicit audit disposition:

- The source watchdog has disabled-by-default destructive revival and unresolved
  lease/canary gaps. The existing JV pacemaker injects prompts and can call an
  optional respawn hook. The SPEC proposes report-only consolidation, with an
  explicit migration notice and refusal of retired action knobs; automatic
  recovery is deferred. This is a deliberate change to current JV behavior.
- Source standby observation uses mail backlog and process presence. JV's
  normative protocol specifies a leased canary/heartbeat detector. The SPEC
  preserves useful partial observation, labels its limits, and leaves the
  normative target intact. A present process is not loop health.
- The source aggregate heartbeat hook is not the producer for per-seat cadence.
  The existing JV writer is that producer but has different roots/role variables
  and rewrites a fixed field set. The SPEC shares one project-scoped, serialized
  writer so turn-end updates preserve schedule, doorbell and ceremony evidence.

The proposed roster is local seat-record UNION cadence-file enumeration; no
PostgREST/hub fallback or credentials. Existing shared identity, launcher and
mailbox interfaces supply the project boundary. The acceptance list is seven
paired groups and 21 finite mutants, traced to I1–I7; the SPEC gate may revise it
before RED. Destructive recovery source fixtures are explicitly excluded.

## Evidence and next action

The SPEC packet binds the exact commit and diff, source hashes, existing JV
hashes, normative sections read, source-test mapping, commission and W-C2
acceptance/current-head CI receipts. It contains no generated runtime result:
that belongs to the later RED/GREEN gates.

Next: o commissions the SPEC audit under the current provider-availability
disposition. No author-spawned review and no runtime implementation before the
SPEC disposition. Follow the pilot's bounded rounds; no extra provider-diversity
debt or unrequested design expansion. A authors, o decides, i integrates.

## SPEC disposition and five folds

Sol audit at `0b381ae` is ACCEPT-WITH-FOLDS. O's
`01M3V8BF6K011E15CT91X3NP49` expressly admits retiring generated recovery
as a safety narrowing, with a breaking-change notice, pin/rollback guidance and
a real disposable release-to-candidate Copier update witness. O reports no live
v0.2.3 pacemaker adopters; the author did not inspect host consumers. Decisions
(2) and (3) are approved. No new leases or additional SPEC round are authorized.

F1 adds the saved-default/legacy-state update and rollback witness. F2 fixes
backlog timing to strict age >1800 independently of process availability. F3
keeps absent cursor=byte zero while corrupt/unreadable means unknown. F4 isolates
schedule detection with a fresh heartbeat, exact thresholds and its own mutant.
F5 requires the effect/coupling gate before every executable render/mutant
closure, synthetic process roots and the closed-PATH/sanitized-environment
harness; source-gate refusals are not runtime behavioral kills. The finite plan
is now 26 mutants (21 initial + one traced fold per finding).

W-C2 integrated-main CI36833759217 passed atcdeb36e; i's exact receipt
`01M3V882A2ZNRVEN73D70BGXHQ` confirms its landing is complete. Next authorized
action: bounded tests-first RED, then o commissions one RED review, then GREEN
and one code review. No runtime implementation before the RED disposition.


## RED candidate (tests only)

The folded SPEC now names the local JSONL decision/accounting format and lock
paths so the bounded tests can assert coverage and use real OS locks. This adds
no runtime implementation. `test_liveness.py` contains T1–T7 positive/refusal
witnesses with the five audit folds explicitly traced. The finite mutant list
remains 26; mutants follow implementation and are not claimed at RED.

The new portability runner gates each pinned Copier input before rendering,
passes `--skip-tasks`, and rejects custom render tasks/extensions/migrations.
Unsafe legacy/current pacemaker bodies are data only: their runtime findings
are retained, never treated as a source-gate pass. Generated tests recheck the
complete liveness closure before each child; missing closure is feature-absence
RED. Two separate containment/clock calibration cells do not execute production.
The F5 gate is bounded source inspection, not a hostile-code sandbox.

The release-to-candidate witness uses the actual `jv-v0.2.3` saved cluster
defaults, a project-owned AGENTS edit and untracked legacy cadence/dedup state.
It runs Copier update and reverts the resulting adoption commit in disposable
Git state, comparing all file hashes. Updated migration refusal remains a
separate gated runtime cell. No source scripts, host processes, provider homes
or released pacemaker are executed. Runtime acceptance remains pending.


## RED evidence at `13f1a908ac98481d2542d3b972e31a8090b7073f`

Real Copier 9.17.1 cluster/solo renders succeeded. The `jv-v0.2.3` update retained
saved user answers (including `tmux-supervisor`), the project-owned AGENTS edit,
and legacy cadence/dedup bytes. Reverting the disposable adoption commit
restored every baseline file hash, including answers and legacy state.

The generated suite ran **21 methods: two containment/clock calibration PASS,
19 feature-absence failures, zero errors**. Every runtime method failed at the
missing `cadence.sh`, `heartbeat-hook.sh`, `stall-watchdog.sh` closure assertion,
before any candidate or legacy liveness body ran. This is initial feature-
absence RED, not behavioral refusal coverage or mutant kills. The pre-render
records additionally disclose existing unsafe legacy/current operating bodies.
Runtime migration diagnostics, concurrency, detection and finite mutants remain
unproven until implementation follows o's RED disposition.

A first run at `90958fb` stopped after a successful Copier update because the
runner compared Copier's Git describe `_commit` directly to a full SHA. The
corrected runner resolves that recorded ref to the exact commit. Its stopped
logs are retained as a harness failure, not counted as RED. The bounded hook
wait and backoff-cap controls were also completed before the successful full
RED run; no runtime file changed.

Next gate: o commissions the one tests-only RED review. The existing hosted
framework CI is separate from these deliberately RED liveness cells. No author
acceptance or GREEN implementation precedes that review disposition.


## RED review disposition and containment folds

Sol's tests-only review is BLOCK on four P1 containment findings. O's
`01M3VA2QS9QVC3E487FA897MYD` directs a new RED commit for all four, then GREEN
without another RED review. R1→I6/F5 adds unexecuted compound `if kill` and
absolute tmux/kill seeds. R2→I6/F5 covers the sourced hook utility dependency
with a helper-effect seed. R3→I1/I7 watches both projects' roster, mail, cursors
and cadence during normal and dry-run sweeps. R4→I1/I7/F1 snapshots and watches
all seeded legacy targets around each refused upgrade knob. The schedule-
deletion mutant and actual updated-runtime migration proof remain GREEN gates.


## Author GREEN and finite mutations

After all four RED folds, `9af1de0` reproduces five containment assertion failures
(four compound/absolute forms and the omitted helper) without executing any unsafe
seed. `66cd307` fixes the gate: two calibration methods PASS; the actual Copier
RED still has 19 missing-closure assertions and zero errors. No second RED review
was commissioned, as o directed.

`dd006ed` implements the shared cadence/heartbeat writer, pure binding verifier,
report-only observer and pacemaker alias, generated Stop delegation and migration
guidance. The actual Copier suite passes all 21 methods, including real upgrade
runtime refusals and rollback. The old matrix standby entry reuses the guarded
standby and migration cells; it no longer executes the retired recovery fixture.

The first finite run at `7ef8853` has 30 valid outcomes: 26 runtime assertion kills,
three harness assertion kills, and one unsafe-effect source refusal before any
child. No survivors, errors or syntax/setup kills. This includes independent
schedule-deletion and all four RED-review findings. The initial baseline renders
carry the identical runtime from `dd006ed`; the later commit adds the mutant runner
and changes only a Copier comment and root change-log grammar.

The shared binding helper addition triggers actual mailbox and launcher
regressions: 27 mailbox methods and 20 launcher methods PASS at `7ef8853`. The
four-answer render matrix also PASSes at that head. No old W-C1/W-C2 mutant run is
claimed; their existing caller implementations are unchanged.

An author check against I3 found that a file occupying `sessions/` could silently
look like an empty roster. `d0eb6c5` adds the refusal inside the existing malformed-
evidence method; it fails once against retained real Copier runtime `dd006ed`
(with zero errors). The observer now rejects non-directory owned roster paths
before sweeping. One narrowly traced mutant removes that check, bringing the
finite total to 31. Final generated GREEN and that finite run follow; no unrelated
case expansion or additional review round is introduced.

CI now runs the actual liveness/update runner and finite mutants, retaining compact
receipts. The current-head framework CI and one independent full code review are
still required before o acceptance and i integration. No live adopter or host
scheduler has been changed.

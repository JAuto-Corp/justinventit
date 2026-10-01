# W-C5 observability review and evidence ledger

Status: the introduced candidate-read regression is corrected with actual
RED/GREEN, every mutant and the matrix passing. O personal exact-head acceptance
remains pending; publication and hosted CI remain held.

O commissioned the next local W-C slice in `01M3WF143WT7SP86CTFW917JKS` on
2026-10-01 after accepting W-C4. Branch `extract/w-c5-observability`, worktree
`/home/justi/dev/wt/jv-observability`, base
`b5722babd54600ba28c09a68e9c0ada8667928cc`. W-C4's accepted checkout/head remain
separate and await the hosted lane; this branch does not depend on its code.

The [SPEC](../specs/W-C5-OBSERVABILITY.md) records intent, non-goals, explicit
guard threat model, seven invariants and seven positive/refusal groups. The
initial 15 mutations gain only the seven runtime mutants traced below. Source
`usage-hook.py`, `pace.sh`, `disk-watch.sh` and the
statusline producer contract were read fully as installed byte snapshots,
with line counts and SHA-256 pins. No provider sessions, real usage history,
snapshots, credentials or source tests were read/run. No live source script
was executed. The private preflight inventory holds exact capture scope.

The proposed extraction retains usage pacing and disk observations. It excludes
the disk source's crash-dump purge and source notification destination, provider
wiring and account policy. Guard/policy authority belongs to reviewed code;
candidate policy self-registration and hostile concurrent filesystem changes
are outside the accident boundary. Any claim beyond that goes to o.

Audit decisions concern the finite delivered contract and witnesses, including
unifying the two source pacing calculations, shared-host state and notification
failure ordering. After audit, traced corrections precede RED. No implementation
or test run begins before that gate. Hosted publication/CI respects the one-lane
critical-path queue. W-D3 focus-hook and interaction-acceptance guidance stay
queued; no work on either is included here.

## SPEC audit folds (2026-10-01)

Sol xhigh audited `e949128e190dfac12bea18d45069b59fe2509b60`:
ACCEPT-WITH-FOLDS. O `01M3WGD0ZB1X64PKHJCTCZB822` confirms the threat model,
scope, adaptation decisions and original 15 seeds, admits all F2–F7 changes in
one SPEC revision, and will check the diff before RED. No second Sol
audit or author acceptance is authorized.

| Finding | Fold and planned discriminating evidence |
| --- | --- |
| F2→I1–I7/X4 | Every invariant now maps to pinned source file:line, tagged retained / portability correction / charter obligation. Source hashes remain pins, not substitutes for traceability. |
| F3→I3 | Weekly-only pacing in hook and CLI; explicit weekly/short/model/credit series mapping replaces the source CLI's primary-only assumption. T3-two-windows checks differing simultaneous windows and swapped field positions; short-only data cannot supply weekly pacing. |
| F4→I2/X6 | Never emit `display_name`; model series use stable opaque SHA-256 IDs instead of printable names. T2-label-canary checks both streams and all written state while retaining valid model observations. |
| F5→I2/I5 | Providers/targets fail independently after common binding/state validation. T2-mixed-providers and T5-bad-secondary retain a good observation and its valid history/alert in the same invocation as the bad input, with truthful nonzero CLI status. |
| F6→I3 | T3-burn-limits distinguishes 1,799/1,800-second spans and removes a same-window outlier older than three hours; exact expected burn, not production-derived calculations. |
| F7→I2 | T2-read-budget observes actual bytes read/seeks on synthetic files, calibrated against read-all-then-slice despite identical output; per-file and collection bounds are explicit. |

Seven added runtime mutants trace exactly to F3 (one), F4 (one), F5 (two),
F6 (two) and F7 (one). Total 22 planned witnesses: 21 runtime mutants plus the
retained destructive-source refusal seed. No tests, mutants, source scripts or
provider-data collectors are executed at this SPEC stage. The original SPEC
packet remains immutable; a new fold packet preserves the exact review/ruling,
before/after docs, fold diff and the line-addressed trace sources. Publication
remains held by the shared lane; W-C4's accepted head is unchanged.

## RED authorization and test closure

O `01M3WGYTB630GAQV10RAMRGSRB` checked F2–F7 at `5bde487` and admitted all
22 planned witnesses. The RED review is explicitly skipped: commit tests-only
RED with missing-feature failures and zero errors, then proceed directly to
GREEN; mail o at GREEN for the Sol code review. The neutral-reference wording
nit is folded into this tests-only commit.

The bounded suite contains 20 methods: two harness calibrations and 18 runtime
methods covering T1–T7 plus the six named audit cells. The two harness methods
pass against inert data controls; read instrumentation distinguishes 400,000
actual bytes from an 800,000-byte read-all-then-slice control with identical
retained output. This calibration is not a generated-consumer or runtime proof.
The operating scripts/helpers remain absent. Each runtime method asserts the
missing closure before creating a candidate child. The committed Copier runner
will render real cluster/solo consumers with tasks disabled and retain the
actual RED result before any implementation is added.

## Actual RED and GREEN construction

Tests-only commit `d76cb4251e968e55c9d1896c40a4c9fb2f8de1dc` rendered real Copier
9.17.1 cluster/solo projects. The identical runner exited 1 with two harness
passes, 18 intended missing-feature assertion failures and **zero errors**;
no runtime candidate child ran. Private `wc5-red-classification.json` records
the classification and raw `/tmp/jv-wc5-red` logs are retained for the packet.

The nested-alias fixture was moved into the selected year/month/day session
layout before GREEN; its refusal assertion is unchanged. The first working-tree
implementation run passed all 20 methods. This is preliminary, not committed
Copier evidence. The GREEN closure reuses the unchanged project verifier and
stdlib collection/state operations. Fixed allowlist entries name every reviewed
helper/command and each of the 21 safe runtime mutations; the destructive purge
seed remains unlisted data. Neither runner dynamically admits candidate images.

Generated operator documentation and CI steps cover the new utility/suite and
finite mutations. No live adoption, hosted CI or independent acceptance is
implied by author inspection or local checks.

## Finite witness calibration

Real generated GREEN at `290ee0071a5d621e2a0069d24e8e17f81b941595` passed all
20 methods (21.172 s). The first 22-mutant run produced 18 assertion kills,
one destructive-source refusal, two survivors and one invalid error result;
it is not a passing mutation gate. All raw outcomes remain retained.

- HOME fallback survived because the configured-input refusal case supplied no
  usable HOME data. Add one T1 cell with valid synthetic legacy files and both
  explicit inputs unset; require unavailable, no observations/history.
- Removed role filter survived because the original non-director witness also
  removed project ID, making the binding check mask the missing filter. Retain
  that cell and add one T6 cell with valid binding plus non-director role;
  require silent success and identical complete fixture state.
- Provider-abort mutation omitted the good series and the test raised `KeyError`.
  Add an explicit presence assertion before the unchanged 40% expectation. The
  original result is an error, never retroactively counted as a kill.

These are exactly the admitted stop-rule corrections for surviving/invalid
finite witnesses. No prior expected value or refusal assertion is weakened.
The baseline now has 22 methods; the same 22 mutation seeds remain. The source
closure/pins are unchanged. The code-review packet includes the assertion diff
for o's admission and the rerun's actual classification.

## Local GREEN handoff (2026-10-01)

Tested commit `a5756d0c3786ab551c72b20c0599e9163ad3248c`:

| Gate | Actual result |
| --- | --- |
| Real task-disabled Copier 9.17.1 cluster + solo renders | Both pass |
| Generated observability suite | 22 methods pass in 21.257 s; zero errors |
| Same finite mutation list | 21 runtime assertion kills, one destructive-source refusal before child; zero errors or survivors |
| Existing four-answer generation matrix | Four pass, zero fail |
| Operating closure coupling/credential-pattern scan | Template and both renders clean |
| Reused project verifier, fixture, guard, Copier configuration and matrix runner | Byte-identical to accepted base |

The first run and every correction remain in evidence; they are not relabeled
as passing. Each mutant retains exact changed bytes, source-gate result, selected
cell and both streams. The packet includes source pins, prior authority, actual
RED, both GREEN/mutant runs, matrix logs and the assertion correction diff for
o's admission. The final handoff commit changes only this ledger and SPEC status;
installed evidence-delta compares the committed operating/test/CI inputs with
the tested head. Current-head hosted CI is not yet claimed.

Request o's Sol code review on the exact local handoff head under
`01M3WGYTB630GAQV10RAMRGSRB`. No author reviewer, self-acceptance, integration,
provider wiring or live adoption. The runtime boundary remains reviewed
cooperating code plus committed fixed policy; hostile self-registration/races
remain outside scope. Notification zero means adapter acceptance, with documented
possible duplicate retry after a checkpoint failure. Documentation impact is
covered by generated HOST_OBSERVABILITY guidance and dated CLUSTER provenance.

## Code review fold RED (2026-10-01)

Sol xhigh blocked exact `7a02335037daba959e729ca6f22a33522a578970` with five P2
findings. O `01M3WKZWR6WM0DZ02KQZRKKEVN` admits one fold: F1/F5 append-only
newline framing/recovery, F2 provider-isolated huge numeric rejection, F3 newest
credits independent of quota windows, F4 live-equivalent history ranges. No
truncation or destructive recovery. A complete history record retains the
five-field TSV contract; JSONL sources retain JSON records.

This tests-only commit adds one method per finding (27 total) and a synthetic
partial-write seam. All 22 existing test method ASTs are unchanged. Actual
committed generated RED must precede implementation. After GREEN, rerun every
existing mutant plus one traced fault mutation per finding; then new immutable
evidence and o-commissioned narrow fold review. Publication remains held.

O clarification `01M3WM6DM4G89F8H5HRXPPJ4PE`: JSONL uses newline-only sealing;
an otherwise valid unframed JSON object can legitimately become readable later.
TSV fragments instead receive TAB `partial` NEWLINE, so truncated numeric last
fields can never become valid five-field rows. Append-only, no sidecar or format
migration. Add one explicit truncated-last-field cell; update only the new F5
RED expectations to the ruling. The original 22 methods remain unchanged.
First actual generated RED at `ddec3a4`: 22 existing passes, five intended
assertion failures and zero errors. The additional cell gets a committed RED
before GREEN as well; total 28 methods.

Actual additional RED at `757e26d5ba43c3da90418ad2205d57b1a78f9e06`: 28 methods,
22 prior passes and six intended assertion failures, zero errors. Both RED runs
are retained independently. The first working-template corrected run passed
28 methods in 25.205 s; it is preliminary, not committed generated proof.

The shared append helper repairs framing without rereading ledger content after
its bounded history read, preserving the actual-read budget. It checks write
length and flush before success. Numeric ranges precede conversion; history
validates each series/range; credits have their own latest-record selector.
Fixed complete-image policy entries and command inventory are updated through
this explicit author-inspected diff, never registered by the test runners.
The original 22 mutant mechanisms remain; six code-finding/ruling mutants are
added. Prior independent review/acceptance is not inferred for the new images.

## Corrected GREEN / narrow-review handoff

Tested `b817e6228f16cd47d99c7f1366031f8c95a37900` with real Copier 9.17.1
cluster/solo consumers: **28 methods pass in 24.384 s, zero errors**. The entire
mutation set passes: **27 runtime assertion kills + one destructive-source
refusal before child, zero errors or survivors**. All original 22 names, classes
and witness selectors are unchanged and rerun; six additions trace only to the
five findings and o's TSV ruling. The four-answer generation matrix passes 4/4.

| Fold | New cell / distinguishing evidence |
| --- | --- |
| F1→I6 | Synthetic partial alert write leaves bytes but no checkpoint; retry seals the fragment, appends its own complete row and checkpoints once; repeat suppresses. The framing mutant concatenates and fails the byte-boundary assertion. |
| F2→I2 | `10**400` in either provider preserves the other provider in CLI/hook and history; no traceback or false zero. The numeric-admission mutant fails the truthful status/series checks. |
| F3→I3 | New short-only credits 80 override old weekly credits 100, within one file and across files; spend is 60/h from 110 over 30 minutes. Short-only credits survive weekly absence; unframed JSONL does not count. The weekly-coupled selector fails 80 vs 100. |
| F4→I2/I3 | Quota history 999 is counted/skipped; 20→25 over 30 minutes remains 10/h, and old bytes remain intact. The range mutant admits 999 and fails the diagnostic/status check. |
| F5→I2/I4 | An unterminated valid-looking history row is ignored; actual partial append is retryable. Reader mutation admits the unframed sample. The separate truncated-last-field cell requires permanent TAB `partial` invalidation before/after a later append; newline-only mutation fails it. |

Author checks confirm all 22 pre-review test method ASTs and shared earlier-slice
helpers remain unchanged. Template and both generated operating closures pass
coupling/credential-pattern scans and fixed-image source gates. No provider,
source cleanup, host installation or live notifier was accessed by proof.

The final handoff commit updates only SPEC/ledger status; installed evidence-delta
checks unchanged committed template/test/runner/CI inputs against the tested head.
A new immutable packet retains the original code review/rulings, both actual RED
runs, corrected GREEN, every mutation's changed bytes/gate/streams, matrix,
source provenance, before/after code and fold diff. Prior sealed packets are
untouched. Request only the o-authorized narrow fold re-review; publication and
hosted CI remain held for the lane, with no author acceptance or integration.

## Narrow-review introduced regression / tests-only RED

Sol high confirmed F1–F5 on `a5b26b8951dd1e792c8f545000b94bb98e665285`, including
unchanged original test ASTs and no premature checkpoint. One introduced P2
(I2/I3): searching older files for credits loses selected valid weekly evidence
when an older candidate cannot be read. O `01M3WNBK3AP54VXS4ZY2292HQF` authorizes
one RED cell, GREEN, every mutant rerun and a new packet. O checks the final diff
personally, with no further Sol round; publication remains held.

The new R6 cell supplies newest weekly 40% and unreadable older weekly 70% with
credits 80. CLI/hook must retain 40%, append its history, count the skipped file
and report partial collection truthfully (nonzero CLI, zero hook). Restoring
readability may add credits 80 but never replace weekly 40%. All 28 preexisting
methods remain AST-identical; no implementation changes in this RED commit.

Actual generated RED `1d907a94fa86d52453ca7f4eb6571dc33edb2868`: 29 methods,
28 prior passes, one intended assertion failure (selected `openai-wk` missing),
zero errors. Per-file metadata/read checks now preserve previously selected
observations, count failed candidates, and retain truthful partial-collection
status. Fixed policy adds the traced R6 image and repins the inspected closure;
no runner dynamically registers images. Existing prior test expectations remain
unchanged. Generated guidance explains the partial-result behavior.

## Candidate-failure correction GREEN / o personal check

Tested `3571231eeba6fc28154e58c0e2beb65f61b0cf11`: real task-disabled Copier
9.17.1 cluster/solo renders and **29 methods pass in 25.023 s**, zero errors.
All **29 mutation witnesses** pass: 28 runtime assertion kills plus one
source refusal before child, zero errors/survivors. The original 28 mutant
names/classes/selectors are unchanged and all rerun; only R6 candidate-failure
containment is added. Four-answer generation matrix: **4/4 pass**.

The complete correction adds per-file metadata/read exception containment,
counts skipped candidates, and carries partial-collection status alongside
selected observations. An older failure preserves weekly 40% and its history;
restoring that older file adds credits 80 while weekly remains 40%, even though
the older quota says 70%. CLI reports partial collection nonzero, hook remains
zero. The R6 mutant propagates the read failure and loses the selected series,
failing the intended presence assertion. No former test expectation changed:
all 28 prior method ASTs, shared helpers and prior mutation selectors are
verified unchanged. Template/both generated operating scans and source gates
pass. No new execution edge, hostile-code guarantee or live effect is introduced.

The final handoff commit changes only SPEC/ledger status, with installed
committed-input evidence-delta against the tested head. A new immutable packet
contains the narrow review/ruling, exact runtime-only and full fold diffs,
tests-only RED and actual GREEN logs/renders, all mutant bytes/gates/streams,
matrix and scope checks. Previous sealed evidence remains untouched. O checks
this fold personally and accepts on the exact head under
`01M3WNBK3AP54VXS4ZY2292HQF`; no further Sol round or author acceptance. Hosted
publication remains a separate held gate, followed by current-head CI and i
integration.

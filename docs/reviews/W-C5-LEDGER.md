# W-C5 observability review and evidence ledger

Status: local generated GREEN and all finite mutation/matrix gates pass.
O-commissioned independent code review, publication and hosted CI remain pending.

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

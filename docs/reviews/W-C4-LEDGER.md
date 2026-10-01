# W-C4 host capacity review and evidence ledger

Current stage: Sol RED review folds admitted by o; one tests-only correction commit before GREEN. No production implementation or GREEN runtime proof yet.

O's `01M3VDBBKHFZPY1AFAGP88RSE4` (2026-10-01) accepts W-C3 at `e04c9a4` and commissions W-C4. The admitted scope is only the landed build-lock/build-guarded pair; the unlanded host-reap portion waits. This scope resolves the extraction brief's original “once d lands it” condition for the separate reaper. Author a; director o; integrator i.

The [SPEC](../specs/W-C4-HOST-CAPACITY.md) opens with the smallest solution: one shared host kernel lock. Its seven invariants, seven positive/refusal cell groups and finite 17-mutant set (16 initial plus the admitted F2 probe-error witness) cover project/host separation, ownership, inherited lifetime, reentry, execution/memory/metadata outcomes, read-only/no-recovery behavior, and contained generated proof.

Read-only production source pin: `JAuto-Corp/customer-portal@e6a51abb7a6ca47d885acd72e795ee7177bfe0d8`. Both wrappers and their three focused source suites were read in full. Private source inventory distinguishes this landed kernel-flock version from the root checkout's old PID/age lock and the unlanded #3814 candidate. The latter's large verifier/substrate dependencies were only read in targeted spans; no full-read claim. No source script, host lock, reaper, process inspection or real build was run.

Existing JV has no build-lock/build-guarded implementation. The proposed output reuses the accepted project binding helper unchanged, introduces one explicit shared host root, preserves source memory policy and lifetime limits, and omits product verifier/substrate integration.

Pending gates: o-commissioned SPEC/test-list audit before RED, RED review before GREEN, one full code review at generated GREEN, exact-head CI, o verdict and i integration. No author subagent or self-acceptance.


## SPEC audit disposition

Sol reviewed `bef4650`: ACCEPT-WITH-FOLDS, three correctness findings. O's
`01M3VEJ0X8AVHG1BVDY22DHZG5` directs all folds, final SPEC round, then RED;
mail o only for a scope/owner decision. No finding needs such a decision.

- F1→I3/I7 documents the retained-FD capacity wedge from JA #3814 F1/R4,
  including the opposite closed-FD escape and the explicit exclusion of recovery.
- F2→I4 admits only flock's documented conflict status (75 with `-E 75`),
  adds the non-conflict probe-error refusal cell and its dedicated mutant.
- F3→I5 covers heredoc input through both entries and requires closed FD 0
  to remain closed (EBADF), preserving the landed foreground execution path.

The auditor's notes confirm shared-root coverage, byte identity of all five
source files with `57d273154`, and that stdin loss arose only in the later
background reaper launch. RED and code review remain Sol one-shots, with
o posting verdicts. No additional SPEC round, author review or scope expansion.


## Tests-only RED at `ddac7619829b9a3d566b4100db350ba539b5fcc7`

SPEC folds were committed first at `ff98c94`. The real Copier 9.17.1 runner
renders cluster alpha and solo beta with tasks disabled and closed child
environments. Both renders succeed. Of **16 methods**, the two independent
source-gate/fixture calibration methods PASS, and **14 runtime methods fail
with missing build-lock/build-guarded closure assertions; zero errors**. No
candidate runtime child executes. This is feature-absence RED, not behavioral
proof of the future lock, lifetime, I/O or refusal implementation.

The fixture calibration proves synthetic memory selection, actual private-file
flock contention status 75 versus injected inspection error 74, and EBADF on
closed FD 0. Unsafe source seeds remain data. Runtime fixtures are prepared to
use only private host/project roots and fixture-created Popen/pidfd handles;
the test process adopts its own orphaned descendants for bounded cleanup. The
crash/background/Node lifetime cells themselves remain unexecuted at RED.

The source gate covers both planned wrappers and their sole shared project
helper, admitting only memory and own-descriptor observations from `/proc`.
It is bounded inspection, not a hostile-code sandbox. Memory and metadata/lock
faults are injected at explicit utility boundaries, without a production test
flag. The planned source metadata temporary prefix `.info` is the retained
write/rename injection seam.

The final ledger follow-up does not change explicit render/test inputs. The
finite 17 mutants remain planned, not executed. Existing framework CI is a
separate regression check and cannot turn this RED into W-C4 GREEN. Next gate:
o's Sol one-shot RED review and posted verdict, then implementation if admitted.
Per o's throttle direction, no correctness-fold status mail is sent; any scope
or owner decision would receive the requested one-line packet. None is needed.

## RED review disposition

O `01M3WAG9NWPS2CA4X0FE6Z4PTG` admits every correctness finding, directs
one new RED commit, then GREEN with no further RED round. R1 closes source
helper/launcher edges and wrapped effects. R2 checks source host-path opens,
fixture roots and native-flock targets before execution/delegation. R3 uses
locked canonical and unrelated FDs together. R4 adds the independent
Python-held canonical lock across both entries and projects. SPEC F1–F3 stay.

The two new harness methods first reproduced **9 assertion failures, zero
errors** against the old gates; unsafe shell seeds stayed data, and the native
flock calibration used only a disposable sibling canary. After gate fixes,
all **4 containment/calibration methods pass**. The 15 production methods
remain feature-absence RED until the wrappers exist. The committed Copier
RED rerun and subsequent GREEN results will be retained separately. Six
review-traced mutants extend the finite set to 23. No runtime kill or lock
lifetime proof is claimed by the missing-feature RED.

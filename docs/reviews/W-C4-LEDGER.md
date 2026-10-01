# W-C4 host capacity review and evidence ledger

Current stage: Sol SPEC audit ACCEPT-WITH-FOLDS; o authorizes all three folds as the final SPEC round, then RED. No implementation, runtime proof or integration yet.

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

# W-C4 host capacity review and evidence ledger

Current stage: SPEC/test-list audit requested; no RED, implementation, runtime tests, acceptance or integration.

O's `01M3VDBBKHFZPY1AFAGP88RSE4` (2026-10-01) accepts W-C3 at `e04c9a4` and commissions W-C4. The admitted scope is only the landed build-lock/build-guarded pair; the unlanded host-reap portion waits. This scope resolves the extraction brief's original “once d lands it” condition for the separate reaper. Author a; director o; integrator i.

The [SPEC](../specs/W-C4-HOST-CAPACITY.md) opens with the smallest solution: one shared host kernel lock. Its seven invariants, seven positive/refusal cell groups and finite 16-mutant set cover project/host separation, ownership, inherited lifetime, reentry, execution/memory/metadata outcomes, read-only/no-recovery behavior, and contained generated proof.

Read-only production source pin: `JAuto-Corp/customer-portal@e6a51abb7a6ca47d885acd72e795ee7177bfe0d8`. Both wrappers and their three focused source suites were read in full. Private source inventory distinguishes this landed kernel-flock version from the root checkout's old PID/age lock and the unlanded #3814 candidate. The latter's large verifier/substrate dependencies were only read in targeted spans; no full-read claim. No source script, host lock, reaper, process inspection or real build was run.

Existing JV has no build-lock/build-guarded implementation. The proposed output reuses the accepted project binding helper unchanged, introduces one explicit shared host root, preserves source memory policy and lifetime limits, and omits product verifier/substrate integration.

Pending gates: o-commissioned SPEC/test-list audit before RED, RED review before GREEN, one full code review at generated GREEN, exact-head CI, o verdict and i integration. No author subagent or self-acceptance.

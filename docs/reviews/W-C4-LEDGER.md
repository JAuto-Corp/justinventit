# W-C4 host capacity review and evidence ledger

Local GREEN: both actual Copier consumers pass all **19 methods**. The finite
**23 witnesses** finish with **17 runtime assertion kills, 5 harness assertion
kills and 1 unsafe-source refusal**, zero errors and zero survivors. Independent
code review, exact-head hosted CI, o acceptance and i integration remain pending.

The [SPEC](../specs/W-C4-HOST-CAPACITY.md) defines seven invariants and seven
positive/refusal groups. Author a; director o; integrator i. O's
`01M3VDBBKHFZPY1AFAGP88RSE4` commissions landed build-lock/build-guarded only.
The unlanded #3814 reaper is deferred; there is no live host adoption.

## Source and resulting behavior

Read-only source pin: `JAuto-Corp/customer-portal@e6a51abb7a6ca47d885acd72e795ee7177bfe0d8`.
Both wrappers and all three focused source suites were fully read. No source
test or live host lock was executed. The prior physical checkout's PID/age lock
and unlanded reaper were excluded; large verifier/substrate dependencies were
only read in targeted spans. Source bodies, read scope and hashes are retained.

The generated wrappers require an existing project binding and an explicit
shared `JV_HOST_ROOT`. They retain kernel ownership across supported inherited
FD lifetimes, 4096 MiB admission policy, foreground command semantics, atomic
diagnostic metadata and read-only status. Existing shared project, mailbox,
launcher and liveness implementations are unchanged. The generated contract and
provenance describe both closed-FD escape and indefinitely retained-FD capacity
wedges; no recovery, signalling, provider, process-discovery or scheduler is added.

## Reviewed folds and RED sequence

Sol SPEC audit at `bef4650`: ACCEPT-WITH-FOLDS. O
`01M3VEJ0X8AVHG1BVDY22DHZG5` admitted F1 retained-descriptor lifetime limits,
F2 explicit probe conflict 75 versus errors, and F3 foreground stdin including
heredoc and closed-FD0 EBADF. SPEC folds landed at `ff98c94` before tests.

Initial tests-only RED `ddac761` (ledger head `da510a8`): actual cluster/solo
Copier renders; 16 methods, 2 calibration passes and 14 missing-closure assertion
failures, zero errors. This was feature absence, not behavioral lock proof.
Existing-framework CI at `da510a8` passed; that result does not prove GREEN.

Sol RED review blocked on four correctness findings. O
`01M3WAG9NWPS2CA4X0FE6Z4PTG` admitted every fold in **one new RED commit**, then
GREEN without another RED round; mail at GREEN for the full code review.

| Finding | Correction and discriminating witness |
| --- | --- |
| R1→I6/I7 | Enforce the declared source/launcher dependency edges; reject wrapped effect commands before execution. Extra helper bodies and effect seeds remain data. |
| R2→I1/I7 | Check host-path sources and configured fixture roots before candidate execution; refuse pathname and foreign-FD flock calls before native delegation. Calibration uses a disposable sibling canary, never a live lock. |
| R3→I4 | Hold canonical and unrelated FDs simultaneously; dropping inode validation must admit the wrong FD and fail the refusal assertion. |
| R4→I2 | An independent Python owner holds the canonical inode; both entries in both projects must refuse command admission. |

The new harness witnesses first produced **9 assertion failures, zero errors**
against the old gates. After fixes all four containment/calibration methods
passed. Corrected RED commit `c034b987b049f20ab3e6658d9952f9d0d62e2d01` then rendered
both consumers and ran 19 methods: **4 passes, 15 missing-feature assertion
failures, zero errors**, still no production wrappers. SPEC F1–F3 were retained.

## GREEN and finite mutations

Implementation `dd2c2d5` first passed all 19 methods in actual generated output.
Final tested inputs at `e115b94e32fb045fccaecbfd26bd0da22c52113a` again passed all
19 methods, including actual crash/background/Node lifetime and reacquisition,
both-entry pipe/heredoc/closed-stdin semantics, metadata faults, independent
canonical ownership and the locked-unrelated-FD witness.

Initial mutant execution correctly classified the delete-inode variant as
**invalid**, because a missing file caused `FileNotFoundError` instead of an
assertion. An explicit canonical-file presence assertion repairs that witness;
the final run kills it by the intended assertion. The nested-unlock mutant
releases only after the nested failure, so the final witness observes an actual
outer competitor admitted, rather than counting a readiness timeout. R2's path
check was expanded within its admitted boundary; intermediate calibration
failures remain in evidence. No production behavior changed after first GREEN.

Final results: 17 runtime kills, 5 harness kills, 1 source refusal; all 23
accounted for, no syntax/setup errors or survivors. Mutated bytes, source-gate
reports, assertion output and actual lifetime receipts are retained, including
the initial invalid run. Unsafe source never becomes a runtime kill. The source
gate is bounded inspection of a known closure, not a hostile-shell sandbox.
Fixture children use private project/host roots, closed environment/PATH,
synthetic memory and fixture-owned Popen/pidfd handles; only the test process
adopts its own orphaned descendants for cleanup.

The CI workflow now runs generated capacity acceptance and the finite mutants
and uploads their receipts. Hosted proof remains pending while the owner's
single hosted lane serves Books; no competing run or author review is started.
All four local generation-matrix configurations pass (solo/no DB, cluster/
Supabase, cluster/Postgres and cluster/no DB); results and exact final-input
carry are retained in the sealed GREEN packet. The final ledger/spec update changes no tested runtime,
render, harness or CI inputs. Only o's code-review verdict can advance acceptance;
only i integrates. Author: a/OpenAI Codex (Astra xhigh assigned by the extraction dispatch; no
new runtime-resolution probe). Independent reviews are Sol one-shots
commissioned and ruled on by o, not author self-review.

## Code-review correction in progress

Sol xhigh BLOCK at `ece283d2`; packet hashes and three ownership mutants were
verified. O `01M3WCKZWFPFCTMH0S71BGF95R` admits a closed-world guard redesign
(F1), inaccessible-ancestor refusal (F2), and exact unheld assertions (F3). New
cells precede implementation in a RED commit. The SPEC records o's escalation
stop condition. No additional guard deny-list patch, self-review or push is
authorized. Next proof: actual corrected RED, GREEN, all finite mutants, sealed
fold packet, and narrow independent review commissioned by o.

# W-C4 host capacity review and evidence ledger

Local GREEN after code-review folds: both actual Copier consumers pass all
**21 methods**. All **26 finite witnesses** finish with **19 runtime assertion
kills, 6 harness assertion kills and 1 unsafe-source refusal**, zero errors or
survivors. The narrow review triggered o's policy-authority ruling; this
documentation/inventory addendum is prepared for exact-head acceptance without
another review round. Hosted CI and i integration remain pending.

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

## Code-review folds: F1–F3

Sol xhigh BLOCK at `ece283d2`; the reviewer verified all 343 prior packet hashes
and three ownership mutants. O `01M3WCKZWFPFCTMH0S71BGF95R` admitted a
closed-world guard redesign (F1), inaccessible-ancestor refusal (F2), and exact
unheld assertions (F3), with RED first, all mutants rerun, then one narrow
independent review of this fold delta. Push remains held behind Books' hosted
run. The SPEC records o's stop condition: a new bypass class means escalate to
o, not another guard patch.

RED commit `9fb5742bac587edf26e4d10b8b7bdd8daaebb1bd` changes tests/SPEC/ledger
only. Real Copier renders run 21 methods: the 19 existing methods pass; new F1
refusal cells produce **48 assertion failures**, and F2's two status verbs
produce **2 assertion failures**, zero errors. Unsafe shell/Python seeds stay
data. A separate false-held mutant passes the predecessor F3 witness and fails
the strengthened exact-output witness by assertion, zero errors.

GREEN first passed at `78b9216696a7d9a16989613f88a761e5cbc6eb7c`. The final
command inventory also names the already-pinned `shift` builtin; that metadata
completion changes no admitted image or runtime code. All generated tests and
all mutants were rerun at final tested commit
`9dcf0d94b84da154bd0e09738976c6f23776c2db`:

- F1 removes runtime regex admission. `capacity_allowlist.json` declares the
  complete command/helper inventories for three Bash programs and pins their
  exact complete bytes: three baseline images plus 19 enumerated safe runtime
  mutation images. Arguments, substitutions, ordering and control flow are
  covered by the full image identity. Unknown bytes refuse even if a command
  name would otherwise look safe. There is no operating Python helper edge.
  The exact caller-argv forwarding sites remain the declared workload interface,
  with trusted fixture builders supplying workloads during proof.
- The guard reads its policy beside itself. The fake-policy witness uses an
  already imported guard to inspect a separate candidate root; it proves that
  the separate root's policy does not affect that import. Generated children
  load their own adjacent, candidate-supplied policy. Neither child-loading
  authority nor file/in-memory self-registration is defended by this witness
  or guard. Both guard and policy are reviewed authority under SPEC I7.
  Source aliases and unreadable/missing files refuse under that fixed policy.
  Even harmless source changes require an explicit reviewed pin update. The
  one-time authoring aid is outside the repo and never runs in tests or CI.
- F2 adds one search-permission check along the host directory chain before
  absence can imply unheld. The unprivileged permission witness holds an actual
  canonical flock, removes ancestor search permission and restores it in finally;
  both status verbs refuse and later acquisition succeeds.
- F3 now requires exact unheld output for both absent roots and released slots,
  retaining held-state and read-only snapshots.

All **21 generated methods pass**. All prior 23 mutant witnesses were rerun;
three old regex-specific harness edits now inject the equivalent narrowly
selected admission faults into the mutated guard, exercised on data only. The
trusted outer guard remains unchanged. Three code-review mutants extend the
set to 26: unknown-image admission, absent ancestor-search check, false-held
output. Results: **19 runtime kills, 6 harness kills, 1 unsafe-source refusal;
zero errors or survivors**. Every runtime mutant passes the trusted source gate
and syntax check before its intended behavioral assertion fails. No unknown
image refusal is counted as a runtime kill.

The fold changes no shared project/mailbox/launcher/liveness implementation or
fixture ownership/cleanup mechanism. All four current generation-matrix
configurations pass. Matrix evidence and final doc-only input carry are in a new
immutable fold packet; the earlier 343-entry packet remains
unchanged. Hosted proof remains pending. This
correction does not authorize live adoption, recovery, or author integration.

## Narrow-review authority disposition (2026-10-01)

Sol's narrow review of `ece283d2f..6a1a01bec` verified all 386 packet hashes and
confirmed F2/F3 fixed, intended C2/C3 mutant assertions, zero errors and no
unrelated wrapper regressions. It blocked on policy self-registration and the
missing `stat` inventory entry. The stop condition fired; o ruled the design in
`01M3WEG3R9Y9W6YR6MBWXF50Q8`, with no further behavioral guard patch.

The guard is an accident boundary for reviewed code. Authority is the committed
guard plus `capacity_allowlist.json`, changed only through a reviewed diff.
Policy rewrite/self-registration, on disk or in memory, is outside this threat
model. The review's **pidfd self-registration seed** is the named accepted
limitation: its admission is not prevented by the guard. The fake-policy witness
does not cover generated-child policy loading. These limits now appear in SPEC
I7 and witness/guard documentation. Hostile-code runtime isolation is a separate
future slice, not work in this addendum.

The readable baseline utility inventory now includes `stat` for both existing
device/inode checks. All image pins, executable guard logic, witness assertions,
wrappers and CI behavior stay unchanged. No RED or repeated full proof is
claimed for this documentation/inventory-only addendum; the prior local 21-test,
26-mutant and four-configuration results retain their exact tested-input labels.
Static comparison verifies executable Python ASTs (excluding documentation),
policy image lists and other executable inputs unchanged. O requires a small
sealed addendum and head handoff, then accepts without another review round.
Push waits for Books' hosted run to clear; exact-head hosted CI precedes i's
integration.

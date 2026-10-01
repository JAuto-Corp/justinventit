# W-C2 review and evidence ledger

Purpose and non-goals: [portable launch/boot SPEC](../specs/W-C2-LAUNCH-BOOT.md). Source pin `JAuto-Corp/customer-portal@57d273154cf029158b7cc118143808e524baf28c`; source and host configuration remain unchanged. Author a, director o, integrator i.

## SPEC disposition

Sol audited `3664edf60ffe7a4f1227dc2342e8e7f3c294635f` and returned **ACCEPT-WITH-FOLDS**. O directed the three folds and RED without another SPEC round (`01M3V124X7NG8MEAC6DDF05Z6B`, 2026-10-01). Fold commit `62c4f38` records:

| Finding | Invariant | Fold / witness |
| --- | --- | --- |
| F1: collision test did not explicitly share a state root or protect legacy handles | I1/I4 | Both projects use one `JV_STATE_ROOT`; legacy A/O `.id` and `.codex-thread` files have byte and inotify-open canaries. |
| F2: qualified names still repeat across fresh launches | I4/X4 | Preserve the 2026-09-30 UUID/rewrite lesson, explicitly defer deterministic recovery, and require ambiguous-name failure without fresh/newest fallback. Fake provider maintains a synthetic name index and refuses duplicate names. |
| F3: runtime gitdir prerequisite absent | X4/I6 | Document the 2026-09-30 Codex 0.159.2 exact resolved gitdir writable-root rule, W-D3 packaging deferral, and inability of read-only preflight to prove writability. Generated guidance gets a documentation assertion; no live write probe. |

The reviewer/provider exception is recorded truthfully: independent Sol review under o's active availability exception; no actual cross-provider review or mandatory later duplicate is claimed.

## RED subject and limits

Tests-first commit `7ed0d69` adds only the generated test, fake-provider fixture and real-Copier runner. A subsequent fixture cleanup keeps temporary files inside each test's scratch directory; no launcher/helper/schema implementation is added. Final RED is rerun from the committed subject named in the packet and PR.

Reproduce with `python3 scripts/ci/test-launch-portability.py --evidence <new-directory>` (Copier 9.17.1). It renders cluster alpha and solo beta at HEAD, calibrates the fake provider, and invokes the generated test. Python, Bash, Node and Linux inotify are the fixture environment. Every provider execution is a local synthetic executable, with scratch provider homes and explicit configuration. No authentication, real provider invocation or installed profile mutation is part of this proof.

The suite contains **18 parameterized methods** covering the six approved positive/refusal pairs and fixed variants. Initial runs fail at the explicit missing-generated-closure assertion: **18 failures, zero errors**. These are **feature-absence RED**, not evidence that every behavioral refusal or mutant has executed. No runtime guard, schema conformance, race outcome or GREEN is credited before implementation. Fake-provider calibration and fixture syntax checks are reported separately.

| SPEC cells | Generated test methods / retained source behavior |
| --- | --- |
| T1 / I1 | Shared-root/legacy-canary positive; project/record binding and aliases; shared probe lock. Same A/O letters in both projects, one provider home, disjoint runtime names/profiles, mailbox cross-check. |
| T2 / I2 | Explicit bootstrap/exact tuple; missing inputs and record overrides; source malformed/unsupported tuple cases; two-contender lock barrier; opened-inode snapshot barrier; candidate write, schema and post-validation publication failures. |
| T3 / I3 | Actual fake Codex version/probe/interactive branch; parsed trust variants; own-thread context versus unrelated newer evidence; failed probe command, timeout and lock. |
| T4 / I4 | Claude UUID/history fresh/resume; Codex modal guard and duplicate-name refusal; post-exit evidence, advisory labels and source exit distinctions. |
| T5 / I5 | Print-only O/I/A prompts; invalid boot/missing template; exact names, no bypass argument, empty unprobed capabilities; operating scan with seeded controls. |
| T6 / I6 | Generated closure and prerequisite failures; source schema groups 5a–5e/6, retained schema mutations, unsupported-keyword refusal, dates/Unicode/prototype-key cases; source fleet-inventory assertions excluded. |

The snapshot fixture pauses the Python/Node reader after opening the old inode and before exposing its bytes, then replaces the original pathname. A timing-only open notification would not reliably expose mixed reads. The publication fixture injects an obstruction after the real validator succeeds; a directory created before launch would only prove type refusal. Neither fixture is a production hook or alternate launcher.

The coupling/secret scanner is bounded to the listed generated operating closure and `docs/CLUSTER.md`; dated references belong in `CLUSTER_PROVENANCE.md`. Tests refuse to execute a coupled or missing operating closure. This is not a comprehensive filesystem-adversary defense or a secret-detection oracle.

No behavioral mutant is run against absent production files. The SPEC's finite list is carried to GREEN; new tests require a surviving mutant or traced finding. The accepted W-C1 regression suite and existing generation matrix are GREEN-stage gates after shared-helper extraction. Ordinary CI on this tests-only commit still checks the existing framework; it is not W-C2 acceptance. CI wiring for the new acceptance command waits for implementation.

## RED review disposition

Sol reviewed `dd61731` and returned **BLOCK** on five P2 findings. O (`01M3V2KNHWH5HXJ47ZFN3SQZ8E`, 2026-10-01) requires all five folded into a new RED commit, then GREEN with **no further RED round**:

| Finding | Trace | Test fold |
| --- | --- | --- |
| R1 | I1/I4 | Interleave alpha/beta resumes for Claude and Codex; assert saved handles and exact resume arguments. |
| R2 | I1/I4 | Assert printed qualified `/rename` for each project; fake name selection uses independent configured human input instead of deriving it from the runtime environment. |
| R3 | I3 | Valid TOML trusting only beta must not authorize alpha. |
| R4 | I3 | A newer matching same-workdir thread cannot substitute for wrong/missing own-thread rollout or context. |
| R5 | I5/I6 | Allowlisted PATH; recording refusal stubs for tmux/network tools; zero-call cleanup assertion. Scratch HOME/CODEX_HOME, temp files and records remain isolated. |

The review's two notes preserve the feature-absence disclosure and scratch bindings. No behavioral pass is inferred from these folds; the final RED packet names the actual results. Each finding carries its finite sensitivity mutant into GREEN, reusing an existing mutant only where it exercises the same defect.

## Next permitted action

After committing/running the five RED folds, proceed to the authorized GREEN implementation without another RED review. W-A and W-C1 must land before changing their shared surfaces. No second SPEC audit, no independent acceptance by the author, and no author merge. The full independent code review remains due at GREEN; the pilot governs any traced fixes.

## GREEN implementation and evidence

Dependencies #67/#68/#69 landed in order; i confirmed main
`aa49d9783a0c6b1cb566d3c48728f5365ae60e21` and combined-main CI success.
The author rebased onto that main before implementation. The pre-rebase RED
history remains at `archive/w-c2-red-before-rebase-20261001`; rebased RED
`ab452db` still yields 18 feature-absence failures and zero errors.

Implementation `e607267` adds the complete generated launcher, boot/templates,
Codex helper and bundled schema/evaluator. W-C1's identity functions move into
one shared helper; mailbox transport semantics remain unchanged. The schema
keeps source constraints except the approved project-ID grammar. The evaluator
matches Node's mechanical TypeScript erasure exactly after only shebang, usage
extension and default-schema-path edits. Plain Node executes the delivered file.

First implementation verification passed 17/18 methods. Its only failure was
an exact-gitdir documentation assertion split across a newline. `52ffc9f` fixes
the wording and passes all 18 methods. Two manually seeded fixtures were corrected
to include W-C1's required project binding; fresh-bootstrap cases still exercise
empty state. The allowlist adds the mailbox's existing `od`/`awk` dependencies.
No production guard or expected refusal was relaxed for fixture setup.

The first finite launch-mutant run at `52ffc9f` produced 21 assertion kills and
two error-only results: missing project-qualified handle and missing `--resume`
argument. Neither error-only result counted as a kill. `18c2fcc` adds explicit
handle/argument assertions in the existing cells. Real Copier cluster/solo
acceptance at that commit passes **18 methods, zero failures/errors**; all **23
launch mutants** then fail assertions with **zero test errors**. The 23 include
separate name/profile variants and reuse newest-rollout substitution for R4;
the final raw output shows the same-workdir wrong/missing-own-thread witnesses.
Source schema's two relaxed-schema controls remain in the generated suite.

Accepted mailbox regression passes **27 methods** at `52ffc9f`; the installed
delta helper confirms its production/test/runner inputs are unchanged at
`18c2fcc`. All **21 accepted mailbox mutants** still fail assertions after their
disposable copies include the shared helper. As in the accepted W-C1 packet,
its nested-alias mutant also has one cleanup FileNotFoundError after 16 assertion
failures; that cleanup error is disclosed and supplies no independent kill.
The ordinary unmutated mailbox suite has no errors.

Generated operating scans, seeded scanner refusals, fixture calibration, lock
and pathname-replacement barriers, and the reviewed zero-external-command
assertion pass. The CI job now runs launch acceptance alongside mailbox and the
existing framework gates. Local evidence runs one heavy lane sequentially.
The sealed packet retains initial failures and invalid mutant attempts as well
as final outcomes, rendered input hashes/closure, source mappings, transformation
proof and the actual SPEC/RED verdicts.

Remaining boundaries: synthetic providers prove the launcher contract, not live
provider compatibility or credentials; Codex stored names are intended/unverified,
post-exit attribution remains advisory, UUID recovery and profile/gitdir adapter
packaging are deferred. Claude's inherited pane exit convention is not a health
verdict. No source/host configuration adoption, liveness/lease implementation,
author acceptance or merge is included.

Next: o commissions one full independent code review of the GREEN subject under
the recorded Sol availability exception; i alone integrates after o's verdict
and current-head CI. No additional SPEC/RED review or retroactive provider-diversity
round is introduced.

The local four-answer generation/coherence matrix at `18c2fcc` also passes:
solo/greenfield/none, cluster/brownfield/Supabase, cluster/brownfield/Postgres,
and cluster/greenfield/none. The final review-head commit only updates this ledger
and SPEC status; the installed delta helper records unchanged executable inputs.
Hosted CI and its duplicate-run cancellation receipts are captured separately
from the immutable local GREEN packet.

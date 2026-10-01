# W-C1 review ledger

Historical review evidence; this document does not define operating policy.

## SPEC

Sol xhigh, fresh context, reviewed `3fd69a374` and returned **REJECT** with four
findings. F1–F4 were folded into SPEC r2 (`2f56393`). The director authorized RED
after that revision, with no third SPEC round. The provider substitution was
explicitly authorized because the other provider was throttled. No initial
audit PASS or actual cross-provider review is claimed.

| Finding | Trace | Disposition |
| --- | --- | --- |
| F1 | I1 | Check nested state symlinks, including cursors and mailboxes; observe foreign opens and unchanged bytes |
| F2 | I6 | Curl's first argument is `-q`; offline fixture detects loading defaults |
| F3 | I6 | Successful and failing remote verbs leave no local state artifacts |
| F4 | I5 | Literal search continues after nonmatches and supports leading-dash text; separately filed [JA #3818](https://github.com/JAuto-Corp/customer-portal/issues/3818) |

## RED

Sol reviewed the tests at `ec16e6f86` statically and returned **BLOCK** with ten
findings; the reviewer did not run the suite. On 2026-10-01 the director required
R1, R2, R4, R6 and R7, allowed R3/R5/R9 if small, and accepted R8/R10 as residuals.
All five required changes and the three small changes were folded into the next
RED commit. The director authorized implementation after that commit, with no
further RED review round. Full independent code review remains due at GREEN.

| Finding | Trace | Disposition at test authoring |
| --- | --- | --- |
| R1 | I6 | Every invocation gets offline curl and a dedicated scratch home, including malformed configuration cases |
| R2 | I1 | Distinct direct/broadcast/completion canaries; exact records and archive contents exclude foreign records |
| R3 | F1/I1 | Pair aliases with accessing operations; force the repair and trigger paths (small fold) |
| R4 | I1 | Assert project-local lock targets and unchanged state after identity-lock refusal |
| R5 | I3 | Snapshot authority and all views around each conflicting replay refusal (small fold) |
| R6 | I2/I5 | Compare archive cursors before and after failed extraction |
| R7 | I6/X6 | Check both output streams on every result against each actual configured test secret |
| R8 | F4/I5 | **Accepted residual:** global grep-error injection exercises live search, not an independently injected archive-only error |
| R9 | I2 | Inject failed authority readback and require refusal without publication (small fold) |
| R10 | I7 | **Accepted residual:** automated scan covers four generated operating files, not every changed operating document; no comprehensive relative-link oracle |

R8 and R10 remain visible limitations, not passing evidence. The director's
acceptance of those residuals does not waive scratch rendering, collision proof,
secret/coupling inspection or the full code review. Folded test definitions are
not yet behavioral proof; the GREEN and mutation results must establish them.

Director records: SPEC disposition `01M3TT0Y6SQFQ2YEJH35GKMPT8`; RED disposition
`01M3TVPVBVP6B2CESG77B69JSJ`. Original audit records are retained in the extraction
evidence packets. Earlier RED packets remain immutable. Initial RED is explicitly
feature absence: the generated CLI was missing, so no negative guard had yet run.

## Implementation and validation record

Runtime extraction `411ccad` preserved the noncomment lines of 16 authority,
framing, durability, identity and completion helper functions. The two changed
core functions add project metadata/path validation and clearer lock or
unverified-append diagnostics. Configuration, target selection and search are
the intentional behavior changes. Initialization uses the existing project
directory as a bootstrap lock before creating state, then the store identity
lock to serialize binding the same ID from different project roots.

The final RED review folds were committed before implementation (`dbdfcb1`).
The first implementation run exposed two fixture cleanup errors: the universal
offline PATH retained failed `flock`/`sync` shims during healthy controls. The
shims are now removed after their fault window; assertions were unchanged.

At `411ccad`, both real Copier consumers and all 24 parameterized test methods
passed; the existing generation matrix passed 4/4. Fifteen initial invariant
mutants were killed. Reconciliation with the SPEC's planned configuration
mutants then found one survivor: implicit selection of a valid product-local
env file. The earlier cells supplied no valid fallback file, so they could not
discriminate that defect. One focused witness was added for this survivor and
observed failing against the mutant while passing against the implementation.
The separate key-in-argv mutant was killed without adding a cell. Final evidence
must retain the survivor, its corrective RED, and the complete 17-mutant run.

R8 and R10 remain accepted residuals. Supplemental inspection of changed files
and selected rendered links is useful bounded evidence, not a replacement for
the missing comprehensive oracle in R10. These results do not constitute the
required independent GREEN code review or the integrator's merge decision.

## Full code review and narrow folds

Sol xhigh reviewed `c6e823651` and returned **BLOCK** on 2026-10-01 with three
probe-confirmed findings. The director's disposition
`01M3TY63QDW52AQJ01QAGHJ7PD` requires a RED cell for each, these three fixes only,
and one narrow re-review. No full-review acceptance is claimed.

| Finding | Trace | Fold |
| --- | --- | --- |
| C1, P1 | I2 | Check `wc` and both `tail` command statuses before interpreting a tail as corrupt or truncating authority |
| C2, P1 | I3 | Give lookup errors a distinct failure status and abort append; only an absent log or normal no-match permits a new ID |
| C3, P2 | I1 | Split completion recovery keys at their final separator, preserving control bytes in the original projection path |

RED commit `69a6a13` adds three methods: inspection failures during read/append,
identical/conflicting replay under lookup failure, and completion recovery from
read/replay/append under a root containing byte `0x1c`. The focused runner exited
1 with 11 assertion failures and no fixture errors before runtime edits. An
earlier uncommitted RED run also exposed two cleanup errors after the first path
failure; independent per-case cleanup was corrected before the RED commit.
The same three methods pass with the folds. Three targeted mutants accompany
the fixes; complete generated-suite and mutant results belong in the new packet.

All three defects reproduced on an unmodified copy of the pinned JA script,
using synthetic scratch data only: C1 deleted 137 authority bytes, C2 appended
a conflicting second record under one ID, and C3 changed a 7-byte outside-store
canary to 395 bytes while leaving the intended view absent. Each run exited 0.
Directed source issues are [#3820](https://github.com/JAuto-Corp/customer-portal/issues/3820),
[#3821](https://github.com/JAuto-Corp/customer-portal/issues/3821) and
[#3822](https://github.com/JAuto-Corp/customer-portal/issues/3822), all `tooling`;
issue bodies/labels were read back. JA source remains unchanged.

R8/R10 remain the previously accepted residuals. The earlier GREEN packet and
hosted pass describe `c6e823651`; they do not establish these folds or supersede
the BLOCK verdict. A fresh packet and the director's narrow review are required.

The narrow re-review confirmed C2/C3 fixed with no new findings, but C1 still
discarded a failed `wc -c` inside `_log_valid`. Director disposition
`01M3TZ3QKQWDZW289GJ07JRAFR` requires the last C1 fold and a director diff review,
with no further model review. RED `8f4dcca` extends the existing C1 cell to four
inspection faults across read/append/replay: only the three byte-count variants
fail on the preceding implementation. Frame validation now returns a distinct
inspection-failure status, and recovery truncates only on a successfully inspected
invalid frame. The extended cell passes; a byte-count-status mutant accompanies it.

The same byte-count path was reproduced on the unmodified JA pin for all three
entry points and added to issue #3820, with body/label readback verified. It
destroyed the 137-byte seeded record in each case (read exit 2; append/replay
exit 3); these nonzero exits did not preserve authority. Prior evidence packets
remain immutable and do not imply that the incomplete C1 revision was accepted.

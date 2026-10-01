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

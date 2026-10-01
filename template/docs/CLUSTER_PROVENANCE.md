# Mailbox extraction provenance

These are labeled historical sources, not project-specific operating rules.
The runtime contract is [CLUSTER.md](CLUSTER.md).

Source: JA `scripts/msg.sh` and its 89-cell test file at landed revision
`57d273154cf029158b7cc118143808e524baf28c`. The extraction preserves the existing
authority, replay and completion algorithms, with explicit project configuration,
safe filename components, a dedicated remote client and the reviewed search fixes.

| Date / historical source | Guard and why |
| --- | --- |
| JA 2026-07-28, `136aace47`, PR #3407 | Mint and validate event ULIDs, including clock/entropy failure and overflow, so same-second events remain distinct and retries can reuse identity |
| JA 2026-07-28, `136aace47`, PR #3407 | Byte-length framing and bounded trailing repair detect partial writes independently of JSON character counts |
| JA 2026-07-28, `136aace47`, PR #3407 | One checked append lock, explicit readback and file/directory barriers prevent delivery from unverified authority; shell errexit alone is insufficient inside conditional compounds |
| JA 2026-07-28, `136aace47`, PR #3407 | Replays compare content, retain the original record and append repairs, so retries cannot forge views or invalidate byte cursors |
| JA 2026-07-28, `136aace47`, PR #3407 | Archive uses the writer's shared lock and a healthy positive control, preventing both unlocked reads and an always-refusing archive |
| JA 2026-07-28, `136aace47`, PR #3407 | Projection and trigger failures report their effect honestly; visibility is not durability and unknown delivery is not proven non-delivery |
| JA 2026-07-29, `78679b1bc`, PR #3425 / incident #3385 | Exact send arity and attached correlation values prevent accidentally shifted authorship; `printf` preserves JSON escapes under inherited shell options |
| JA 2026-08-02, `3ae8cf9fe`, PR #3446 | Strict typed completion fields and one canonical recipient set prevent malformed terminal results; historical fan-out repair precedes unrelated appends |
| JA 2026-09-24, `e0128d1a6`, PR #3579 | Explicit hub targets separate control-plane reads from product storage; the extraction removes the temporary fallback |
| JA 2026-09-30, portability audit §3 / extraction X2 | Project IDs, roots and separate stores prevent same-seat collisions; the baseline database still has no project tenancy |
| JV 2026-10-01, W-C1 SPEC F1–F3 | Reject nested state aliases before access, disable curl defaults and bypass local initialization on remote reads to keep project and credential boundaries explicit |
| JV 2026-10-01, W-C1 SPEC F4; JA issue #3818 | Search must continue after ordinary misses and terminate grep options so later matches and leading-dash text remain reachable |
| JV 2026-10-01, W-C1 RED R1–R7/R9 | Offline child environments, distinct project canaries, targeted lock/readback faults and both-stream secret checks keep tests contained and guards observable |

The caller supplies the project ID at adoption; no source paths, personal account
values, live credentials or product data are carried into configuration. Runtime
providers share one implementation. No provider-specific projection is generated
for this script.

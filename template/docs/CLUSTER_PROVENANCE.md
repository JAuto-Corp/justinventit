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
| JV 2026-10-01, W-C1 code C1; JA issue #3820 | Check every authority inspection command, including frame byte counts, before truncation: a failed read is not evidence of a torn record |
| JV 2026-10-01, W-C1 code C2; JA issue #3821 | Distinguish identity lookup errors from normal misses so an unreadable log cannot admit duplicate or conflicting authority |
| JV 2026-10-01, W-C1 code C3; JA issue #3822 | Split recovery keys at the final delimiter because valid filesystem paths may themselves contain the separator byte |

The caller supplies the project ID at adoption; no source paths, personal account
values, live credentials or product data are carried into configuration. Runtime
providers share one implementation. No provider-specific projection is generated
for this script.

## Launch, boot and schema extraction

Pinned source revision remains `57d273154cf029158b7cc118143808e524baf28c`:
`scripts/role-launch.sh`, `scripts/boot-role.sh`, `scripts/lib/codex-seat.sh`,
`docs/orchestration/role-templates/{O,I,IMPLEMENTER}.md`,
`scripts/validate-seat-record.ts` and
`docs/features/plans/b4-seat-records-b2-leases/seat-record.schema.json`.

| Date / origin | Retained reason or intentional extraction difference |
| --- | --- |
| 2026-07-29, `c8564d637` | Schema-driven evaluation, unsupported-keyword refusal, date-time/Unicode/prototype-key guards. The `.mjs` evaluator is mechanical TypeScript erasure plus module/usage/default-schema-path packaging, not a second implementation. |
| 2026-08-02, `29de71234` (2026-07-29 experiments) | Missing Codex profiles can silently resolve defaults; parse trust and prove the exact resolved tuple using the probe's own thread. Checked flock matters because shell errexit is suppressed in conditional compounds. |
| 2026-08-20, `6347c55b0` / `93be966d2` | Persisted record is sole tuple authority; a single byte image prevents a pathname replacement mixing runtime/model/effort. |
| 2026-09-23, `317dd77f3` | Retain UUID/history resume, Codex modal guard, provider exit distinctions and honestly advisory post-exit attribution. |
| 2026-09-30, duplicate-name and gitdir operational record | Qualified names still permit duplicates; UUID recovery had to follow seat shutdown because the launcher rewrites names on exit. Exact cwd gitdir writable-root configuration is separate from read-only tier proof. Both limitations are documented, not claimed implemented. |
| 2026-10-01, W-C2 / charter X2,X3,X5 | Share W-C1 identity checks, qualify names/state, require explicit bootstrap model, validate private candidates, preserve empty unprobed capabilities, remove implicit permission bypass and source fleet policy from prompts. |
| 2026-10-01, W-C2 code C1/C2 | Validate one literal probe UUID and require one rollout; wildcard or ambiguous identities cannot authorize dispatch. Compare parsed trust/model/effort inside Python so shell newline trimming and string coercion cannot convert invalid evidence into a pass, including the shared post-exit tier check. |

The schema retains the full source shape; reserved lifecycle fields do not grant
an implementation of leases, watchers, capabilities, recovery or registry ownership.
Provider profile installation and complete runtime integration remain W-D3 work.

## Host capacity extraction

Read-only source: JA `scripts/build-lock.sh`, `scripts/build-guarded.sh` and their
three focused suites at `e6a51abb7a6ca47d885acd72e795ee7177bfe0d8` (landed
2026-10-01). The unlanded #3814 reaper is excluded. See
[the portable contract](HOST_CAPACITY.md).

| Date / historical origin | Guard and why |
| --- | --- |
| JA 2026-09-26, `25b1f91b4` / #3695 | Kernel flock replaces PID/age stealing because Codex PID namespaces made host ownership inference unreliable. Retained descriptors protect surviving children. |
| JA 2026-09-27, `ead1104f1` / #3713 | Same-inode plus separate-probe and owning-description checks permit real nested ownership without trusting a marker. |
| JA 2026-09-30, portability audit §3 | One explicit host root separates shared capacity from project identity and avoids independent project-local slots. |
| JV 2026-10-01, W-C4 SPEC F1 / JA #3814 F1/R4 | Retained detached descriptors can wedge capacity; closed descriptors can escape it. Document both boundaries without importing unlanded recovery. |
| JV 2026-10-01, W-C4 SPEC F2/F3 | Explicit conflict 75 separates contention from probe errors; foreground execution preserves pipes, heredocs and a genuinely closed stdin. |
| JV 2026-10-01, W-C4 RED R1–R4 | Declared dependency/effect checks and fixture-only paths precede execution; independently owned canonical and unrelated locks make ownership assertions discriminating. |

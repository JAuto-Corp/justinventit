# W-C2: portable seat launch and boot

A generated project must launch the runtime/model/effort recorded for its own seat and resume only its own saved session; extract the existing launcher, its validation/probe closure, and thin boot templates.

Status: **Sol SPEC audit ACCEPT-WITH-FOLDS at `3664edf`; three folds incorporated below, RED authorized by o (`01M3V124X7NG8MEAC6DDF05Z6B`, 2026-10-01). No implementation yet.** Author a; director o; integration i. Authorized after W-C1 ACCEPT at `22cb948c632d2797dd650b221b1308126f607cea` (dispatch `01M3TZPPXSV6GJRH27BQ7K1T7A`, 2026-10-01). Implementation depends on the accepted W-A guidance and W-C1 project-store implementation landing. This SPEC can be audited before those merges.

## Intent

Give a Copier consumer the exercised, terminal-driven Claude/Codex seat launcher and a printable role boot prompt, with explicit project identity, authoritative seat records, isolated resume state, and the source's Codex trust/profile checks. Two projects sharing one host and the same seat letters must not overwrite each other's records, resume handles, or runtime names. Invalid records or failed checks must refuse dispatch instead of silently selecting a different runtime or tier. Preserve source mechanisms and their limits; remove source-project policy and host assumptions.

## Non-goals

- No daemon, terminal/tmux creation, doorbells, heartbeat, watchdog, lease acquisition/fencing, registry/backend writes, automatic restart, or full SEAT_PROTOCOL conformance. W-C3 owns liveness.
- No model catalogue, model-policy generation, profile/trust installer, runtime installation, global instruction editing, or hook/config parity. W-D3 extends existing PR #34; this launcher consumes operator-installed prerequisites.
- No legacy live-state migration, changes to the reference application's source/configuration, or launch of a real provider session during acceptance. No authenticated provider capability or current CLI-version compatibility claim from fake-runtime tests.
- No automatic permissions bypass, standing authority grant, boot-prompt injection, or external notification. Project/runtime policy continues to govern permissions; producing a boot prompt does not execute it.

## Source and delivery boundary

Read-only reference pin: `JAuto-Corp/customer-portal@57d273154cf029158b7cc118143808e524baf28c`. Extract Git objects at that pin, not the host checkout's mutable files. Source references below are provenance, never generated operating defaults.

| Source at the pin | Generated destination / purpose |
| --- | --- |
| `scripts/role-launch.sh` | `scripts/role-launch.sh`: terminal launch, authoritative record selection and resume |
| `scripts/lib/codex-seat.sh` | `scripts/lib/codex-seat.sh`: executable resolution, parsed trust, attributed tier probe and resume guard |
| `scripts/boot-role.sh` | `scripts/boot-role.sh`: validate a letter and print its template |
| `docs/orchestration/role-templates/{O,I,IMPLEMENTER}.md` | Same relative destinations, reduced to portable role identity, own-mailbox drain and canonical entry pointers |
| `scripts/validate-seat-record.ts` | `scripts/validate-seat-record.mjs`: same schema evaluator in plain JavaScript, requiring Node rather than a consumer's package manager/TypeScript stack |
| `docs/features/plans/b4-seat-records-b2-leases/seat-record.schema.json` | `docs/seat-record.schema.json`: bundled validation contract, neutral metadata and project-ID grammar |
| `scripts/tests/role-launch-record-authority.test.sh` | Retained behavioral assertions in the generated launch test; replace host paths and real-runtime assumptions |
| `scripts/tests/seat-record-contract.test.sh` | Retained schema/format/keyword-enforcement regressions; omit the source-fleet inventory assertions |

The validator remains schema-driven, with unsupported keywords rejected. Type erasure and module entry handling are packaging changes; do not rewrite the validation algorithm or maintain a second TypeScript implementation. Preserve the source's date-time, Unicode length and prototype-key regressions. The source test's static Codex wiring assertions do not establish runtime behavior: fake Codex must execute the actual branch.

Share W-C1's project configuration/binding functions through `scripts/lib/jv-project.sh`, used by both `msg.sh` and the launcher. This small extraction prevents two identity implementations from drifting. Keep mailbox-only configuration and commands in `msg.sh`; its entire accepted suite remains a regression gate. Do not otherwise change mailbox semantics.

Generated `docs/CLUSTER.md` documents setup, commands and limitations; `docs/CLUSTER_PROVENANCE.md` adds guard reasons and dated origins. Keep rules in W-A's canonical guidance rather than copying them into role templates. Add one generated launch/schema test runner and one repository acceptance/mutation runner as needed; wire the acceptance command into the existing CI job. The existing generation matrix still runs.

## Operating contract

### Project, paths and process environment

- Use W-C1's required `JV_PROJECT_ID`, `JV_PROJECT_ROOT`, and `JV_STATE_ROOT`. Preserve its ID grammar (`[a-z0-9][a-z0-9_-]{0,63}`), physical-root binding, bootstrap/identity locking and cooperating-filesystem symlink refusal. Missing identity is an error, never a source-project fallback.
- Store records at `<state-root>/<project-id>/sessions/<lower-letter>.json`, seat locks beside them, and Claude/Codex resume files in that same project-owned sessions directory. Check these paths before opening or truncating them. Independent legacy path overrides must not redirect state out of this store.
- Keep the source's one-uppercase-ASCII-letter CLI. O/I default to the configured project root. Other letters require `--worktree <existing-path>`; no invented sibling-directory convention or worktree creation. Canonicalize the selected directory and require an existing record's `project_id`, `letter` and `workdir` to agree. An explicit worktree may be outside the main project directory, as ordinary Git worktrees are; it is not inferred from a global name.
- Export `JV_ROLE` plus the configured project identity to the runtime. Qualify runtime-visible names as `<project-id>-<lower-letter>` and Codex profiles as `<project-id>-thinking|doing`. Do not emit a source-specific role variable.
- Provider-owned history remains under the configured provider home: Codex uses `CODEX_HOME` or `$HOME/.codex`; the inherited Claude lookup uses `$HOME/.claude/projects/<encoded-workdir>`. These are provider data, not alternative project coordination stores. Document the supported history layout rather than claiming every runtime version uses it.
- Preserve host-wide probe serialization for a shared Codex home: one `.jv-tier-probe.lock` inside that provider home, with checked acquisition. This is intentionally shared capacity coordination, not project session state. Remove the source host lock path and arbitrary lock-path override. Profiles, trust and binary configuration are not installed or altered by the launcher.

### Seat-record authority and bootstrap

Keep `--fresh`, `--worktree`, `--runtime`, `--tier`, and `--at-machine`. Add only `--model <value>` for bootstrap: the project must choose its model rather than inherit the reference fleet's dated model table. No implicit model or letter-based runtime fallback remains.

A new record requires `--runtime claude|codex --model <nonempty-model>`, with `--tier thinking|doing` selecting the source-supported efforts `xhigh|medium` (default `thinking`). The flags exist only to create the first record. If a record exists, any bootstrap flag is refused; if no record exists and required bootstrap input is absent, refuse before any provider command. An unsupported record effort is also refused rather than mapped to a guessed profile.

Hold the per-seat lock from before the existence/read/bootstrap decision through runtime exit, preserving the source's serial launch behavior. Check lock failure explicitly. Bootstrap writes a private candidate, validates it against the bundled schema, publishes only a valid record, and rereads the persisted record for dispatch. A rejected candidate leaves no authoritative record. An existing record is read from one opened byte image; schema validation, binding checks and tuple extraction use that same image, never separately reread fields from a changing pathname. Preserve model bytes through argument arrays/NUL-safe transport; NUL and unsupported tuple values are invalid.

Bootstrap emits `schema_version: 1`, project/letter/workdir and requested tuple; `state: booted`, null session handle, empty capability object, and the source's neutral lease/watcher placeholders. An unperformed probe gets no fabricated `probed_at`. Lease/watcher shapes are not implemented semantics, and `booted` is not evidence of a live or registered seat. The launcher does not promote the record to active or advertise capabilities.

### Runtime checks and session behavior

Claude consumes the exact recorded model and effort. Preserve its fresh UUID, saved UUID, and history-exists resume decision. Validate a saved UUID before using it as a history path or argument. Names and Remote Control names are project-qualified. Omit the source's unconditional `--dangerously-skip-permissions`; runtime/project configuration owns permissions. The source's Claude pane-exit convention is retained and documented: launch rejection is nonzero, but a returned interactive Claude process follows the inherited pane lifecycle and is not a supervisor health verdict. Do not claim actual resolved Claude model/capabilities from its requested arguments.

Codex requires an explicitly configured absolute executable `JV_CODEX_BIN`; retain prepending its directory to PATH and proving invocation with `--version`. Parse the provider's trust TOML for the exact workdir; missing parser/config/trust refuses. Retain the bounded read-only preflight invocation and require its own `thread.started` identity, matching rollout and exact recorded model/effort before interactive dispatch. Another thread's newer or matching rollout cannot satisfy this check. Failed invocation, timeout, lock acquisition, missing identity, missing context or mismatch is a refusal.

Codex resume requires the source's existing tmux-or-`--at-machine` modal guard. A fresh session prints a project-qualified rename instruction and records that name explicitly as **intended/unverified**, not an observed thread ID. Refuse a saved thread name outside this seat's qualified name; this slice does not migrate externally written arbitrary thread handles. Preserve the post-exit workdir/time attribution check and its weaker, advisory success status. Missing/ambiguous evidence is not resolved by picking the newest rollout. A provider refusal because the saved name matches multiple threads must remain a nonzero failure, with no automatic fresh-session or newest-thread fallback. Deterministic UUID recovery is explicitly deferred. Keep source exit distinctions: mismatch 4, normal exit without attributable evidence 5, abnormal runtime exit propagated, and source-defined planned teardown handling. Do not turn this heuristic into registry ownership or verified TUI-thread evidence.

The dated 2026-09-30 duplicate-name lesson is relevant even with project qualification: repeated fresh launches can share a name. The exercised host recovery wrote the current thread UUID after stopping the seat; writing it earlier failed because the launcher rewrote the name on exit. W-C2 retains labelled name-based state and tests ambiguity refusal; it does not claim to implement that UUID recovery or safe manual migration.

### Boot prompt

`boot-role.sh <LETTER>` only prints the O, I or implementer prompt from its own generated tree. It validates exactly one letter, substitutes that letter for implementers, and has no runtime, mailbox or state side effects. Each prompt names the role, tells the agent to read the project entry contract and its canonical guidance, and directs it to drain its own mailbox with the project command before work. The prompt describes role responsibility; project instructions or explicit dispatch supply authority. Remove product workflows, personal details, provider/model assignments, obsolete process rules and host-specific boot routes.

### Prerequisites and honest compatibility

The supported extraction target is a Unix shell environment with Bash, flock, standard file utilities, jq (shared project identity), Python 3.11+ (TOML/fixtures), and Node 22+ (plain-JavaScript schema evaluator). No pnpm, tsx, application packages or database are required. Actual provider CLIs, trust and matching profiles are operator-installed; W-D3 will package those adapters. Missing dependencies fail before dispatch. Live Codex preflight costs a provider turn when an operator launches a real seat; acceptance substitutes fake CLIs and never makes that call.

Dated runtime limitation (Codex CLI 0.159.2, 2026-09-30): the exact resolved gitdir of the seat's cwd must be an operator-supplied writable root; naming a parent `.git` or `.git/worktrees` does not satisfy that observed runtime rule. Resolve the path from the actual worktree (`git -C <worktree> rev-parse --absolute-git-dir`), not a naming convention. W-D3 owns profile packaging. W-C2's read-only tier preflight cannot verify gitdir writability and must never be described as that proof.

## Invariants

| ID | Required behavior |
| --- | --- |
| I1 | Every project-owned record, resume handle, lock and runtime name is bound to the configured project/seat. Wrong roots/identities and store aliases are refused before dispatch or foreign-state mutation. The intentional shared probe-capacity lock is the only new shared launcher lock. |
| I2 | A valid, single-snapshot seat record is the sole dispatch authority. Bootstrap is serialized and schema-validated, existing records cannot be overridden, and invalid/unreadable/unsupported input never selects a fallback runtime/tier. |
| I3 | Codex interactive dispatch requires executable invocation, exact parsed workdir trust and the preflight thread's matching resolved tuple. Every failed or missing check fails closed, including lock failure and unrelated rollout evidence. |
| I4 | Fresh/resume selection uses this seat's saved state and the source's modal guard. Intended names and advisory post-exit observations remain labelled honestly; rejection/exit classes retain their stated meanings. |
| I5 | Boot prompts and runtime arguments carry portable role identity without source-project policy, fabricated capability evidence or an implicit permissions grant. Printing a prompt has no launch/mail/state side effect. |
| I6 | Real Copier output contains the full dependency closure and runs the contract checks offline in two isolated consumers. Shared-helper extraction preserves accepted W-C1 behavior; no source checkout, live provider config or fleet state is mutated. |

## Bounded test list for pre-code audit

Each row is one positive/refusal pair; listed variants retain source behavior or witness a named boundary. Reuse assertions/fixtures across rows rather than multiplying test infrastructure. RED is committed before runtime implementation. A feature-absence RED proves missing delivery only; behavioral fault witnesses and mutants are separately reported.

| Cells | Invariant | Positive witness | Refusal witness / fixed variants |
| --- | --- | --- | --- |
| T1+/T1− | I1 | Render alpha and beta with the same A/O letters, **one shared `JV_STATE_ROOT`**, and shared synthetic provider home; launch both, verify disjoint records/resume files/names/profiles, and cross-check each mailbox still reads only its own messages. Include paths with spaces and a nonprinting separator. | Missing/invalid identity, same ID bound to another root, nested state/record/handle/lock symlink, foreign record workdir/letter/project and unqualified saved Codex name: nonzero before interactive dispatch; byte-identical foreign canaries. Seed legacy `<state-root>/sessions/<LETTER>.id` and `.codex-thread` canaries; assert neither is opened/consumed nor modified by either project. Verify two probes sharing provider home serialize on the shared capacity lock. |
| T2+/T2− | I2 | Bootstrap each runtime, validate persisted bytes, then launch from the persisted exact tuple (including literal model whitespace/metacharacters). Race two bootstraps under a barrier: one authority, no overwrite or mixed tuple. | Missing bootstrap model/runtime; bootstrap override against existing record; malformed/unreadable JSON; invalid schema/version/tuple; record replacement between pathname accesses; failed seat lock, candidate write, validator or publication. Zero provider dispatch on rejected input; existing record unchanged; no authoritative invalid candidate. |
| T3+/T3− | I3 | Fake Codex exercises version, trusted TOML, preflight thread event, its rollout/context and interactive launch with the qualified profile. Distinct unrelated newer rollout proves attribution. | Nonrunning binary; commented/untrusted/malformed/missing trust; failed probe lock/command/timeout; missing thread/context/rollout; wrong model/effort and a matching foreign rollout beside wrong own evidence. Assert no interactive call, not merely a nonzero parser exit. |
| T4+/T4− | I4 | Fake Claude covers initial UUID, existing-history resume, missing-history fresh and `--fresh`. Fake Codex covers fresh, qualified resume in tmux or with the explicit human-presence flag, and unique post-exit tuple evidence. | Unsafe saved Claude UUID; Codex unattended resume without tmux; repeated fresh launches followed by an ambiguous-name resume must fail nonzero with no fresh/newest-thread fallback; missing/ambiguous post-exit evidence, wrong tuple, abnormal exit and planned teardown variants. Assert source exit mapping and explicit intended/unverified-name and advisory-success messages. |
| T5+/T5− | I5 | Print O/I/A templates, verify identity/substitution, entry/guidance/mailbox routes and no filesystem or process side effects; bootstrap capabilities remain empty and both fake runtimes capture qualified names without a bypass flag. | Invalid/extra boot arguments and missing template fail without stdout success or state mutation. Seed source-host paths, source role env, stale model assignment, bypass flag and fake capability timestamp into inspected artifacts: scan/assertions must detect them. |
| T6+/T6− | I6 | Real Copier cluster and solo consumers execute the launch and schema cells using scratch HOME/CODEX_HOME and fake CLIs. Run the accepted mailbox suite and four-answer generation matrix; inspect changed generated operating files and referenced relative paths. | Remove a helper/schema/validator or a required executable in a disposable render and assert clear refusal before provider dispatch. Retain schema-invalid, unsupported-keyword, date-time, Unicode and prototype-key negative controls from the source tests; scan seeded coupling/secret fixtures and prove no host/source writes. Generated prerequisite guidance must retain the dated exact-gitdir writable-root rule, W-D3 packaging deferral, and read-only-preflight limitation; this is a documentation assertion, not a writability probe. |

Fake provider executables capture argv/cwd/environment, create only synthetic provider artifacts, and distinguish preflight from interactive dispatch. Bound all concurrency/failure fixtures with timeouts; failed setup or errors are not assertion kills. The reference application's actual CLI binaries and credentials never enter fixture configuration. Snapshot relevant scratch/config canaries before and after; filesystem scope checks are bounded evidence, not a claim to defend against a hostile concurrent filesystem attacker.

Finite initial mutants, all tied to the pairs above: remove project/root binding (T1); unqualify resume path (T1/T4); unqualify runtime name/profile (T1/T5); bypass nested-alias rejection (T1); move the bootstrap existence check outside the lock (T2); discard seat-lock failure (T2); skip candidate schema validation (T2/T6); reread one tuple field from the live pathname (T2); let CLI override an existing record (T2); replace parsed trust with textual presence (T3); choose the newest preflight rollout (T3); discard probe-lock failure (T3); skip exact tuple equality (T3); bypass the resume guard (T4); report missing post-exit evidence as verified success (T4); add the inherited permissions bypass (T5); stamp unprobed capabilities as measured (T5). Audit F2→I4 adds one traced mutant: retry an ambiguous-name resume as a fresh session (T4). Retained schema tests keep their finite source mutations. No open-ended mutant expansion: new cells only for a surviving mutant or a finding traced to I1–I6.

## Provenance, evidence and decision

Guard origins to preserve: schema-driven validation and unsupported-keyword refusal (`c8564d637`, 2026-07-29); Codex trust/probe/resume guards (`29de71234`, 2026-08-02, recording the 2026-07-29 experiments); record-authoritative tuple (`6347c55b0` / `93be966d2`, 2026-08-20); source launcher updates (`317dd77f3`, 2026-09-23). The extraction's project qualification, explicit bootstrap model, empty unprobed capabilities and omission of policy grants are dated 2026-10-01 and trace to charter X2/X3/X5. The 2026-09-30 duplicate-name/UUID and exact-gitdir lessons come from the dated `codex-sandbox-cwd-gitdir-readonly` operational record; retain that date and the explicit deferrals in generated guidance. Record per-file hashes and intentional behavior differences in the eventual evidence packet.

SPEC audit asks whether this finite list can miss a violation of intent/I1–I6. O commissions the reviewer under the active provider-availability exception; author does not self-award an independent verdict. SPEC round cap two, then o decides scope. O's 2026-10-01 disposition accepts these three folds without another SPEC round. Next: one tests-only RED review, implementation, generated GREEN/mutant evidence and one full independent code review. Traced fixes each require RED and a killing mutant; security/locking fixes get the pilot's one narrow review, with director decision at the round cap. No extra review debt is invented for the provider exception.

Review packet will name exact commit, rendered inputs, source hashes, RED/GREEN/mutant outcomes, residuals and a sealed evidence manifest. Purpose and Non-goals in the dispatch repeat this SPEC. One heavy local lane and one hosted run at a time; no live provider launch, installation or fleet change is acceptance evidence. I alone integrates after o's verdict and current-head CI.

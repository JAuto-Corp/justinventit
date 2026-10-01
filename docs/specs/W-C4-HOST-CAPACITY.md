# W-C4: one shared host slot for heavy commands

Heavy commands from different projects on one machine must compete for the same kernel lock; extract the two landed wrappers and require an explicit shared host root.

Status: **Sol SPEC audit ACCEPT-WITH-FOLDS at `bef4650`; all three correctness folds admitted by o (`01M3VEJ0X8AVHG1BVDY22DHZG5`) as the final SPEC round, then RED. No implementation yet.** O accepted W-C3 at `e04c9a427612360f44559e491c864eed6a9c999e` and commissioned W-C4 in `01M3VDBBKHFZPY1AFAGP88RSE4` (2026-10-01). O explicitly limits this slice to landed build-lock/build-guarded; host-reap waits for its source to land. Author a, director o, integrator i. Extraction charter X1–X6 applies.

## Intent

Give generated cluster projects an explicitly invoked wrapper that admits at most one cooperating heavy workload on a shared Linux host, including nested invocations and wrapper failure. Keep project identity separate from the shared capacity lock, preserve actual command arguments/stdin/output/exit status, and never mistake PID visibility or stale metadata for permission to steal capacity. Adapt the landed kernel-flock implementation, without importing the product verifier or building a resource manager.

## Non-goals

- No reaper, signal forwarding, stored-PID termination, process discovery, Docker, database/substrate allocation, resource cleanup, port registry, scheduler, queue, fairness or automatic retry. O deferred the unlanded host-reap source explicitly.
- No automatic replacement of project build commands or CI jobs, background worker discovery, multi-host/distributed locking, per-project capacity partitions or installer. All projects must deliberately use the same host root and wrappers.
- No security boundary against a hostile local user concurrently replacing files or deliberately bypassing the wrapper. No claim that detached workers closing the inherited FD remain protected.
- No JA lock/state/configuration mutation, host-shell/process experiment, real build workload or provider invocation in the extraction proof. Existing mailbox, launcher and liveness behavior stays unchanged.

## Source and version choice

The production source is `JAuto-Corp/customer-portal@e6a51abb7a6ca47d885acd72e795ee7177bfe0d8` (landed staging observed 2026-10-01), not the older physical root checkout. These five files were read fully and saved with hashes:

| Source | Retained behavior or boundary |
| --- | --- |
| `scripts/build-lock.sh` (196 lines) | Nonblocking flock, inherited descriptor ownership checks, memory preflight, atomic diagnostic metadata, descriptor-only cleanup, status/wait-info, retired acquire/release verbs. |
| `scripts/build-guarded.sh` (37) | Thin command wrapper. Resolve its sibling from its own script directory rather than the caller's Git checkout; remove product build and scheduling instructions. |
| `scripts/test/test-build-lock.sh` (139) | Contention, inode persistence, status, exit forwarding and memory witnesses. Adapt to explicit scratch host/project roots. |
| `scripts/test/test-build-lock-namespace.sh` (159) | Poisoned PID metadata, killed wrapper, inherited background child and Node launcher awaiting its worker. Only fixture-owned process handles may be signalled. |
| `scripts/test/test-build-lock-reentrancy.sh` (180) | Descriptor reentry and spoof refusal. Product `verify-local.sh`, private env reconstruction and substrate integration are outside this slice; use a small contained nested command, without claiming product verifier conformance. |

Historical reasons: JA 2026-09-26 `25b1f91b41d8d05ea8146e385e43652045feb2ad` / #3695 replaced PID/age stealing after Codex PID-namespace collisions. JA 2026-09-27 `ead1104f18c39e21060397d4c6dd461eff286023` / #3713 added reentry so an inner build could share its verifier's existing capacity ownership. The 2026-09-30 portability audit §3 requires one host capacity owner across projects. These are provenance, not runtime policy identifiers.

The physical root checkout `bd3e7821473401f93ce23af621849f93a49435ef` still has the older mkdir/PID/age lock. Its fixture removes a shared temporary lock and must not run. PR #3814 at `3653ee40456b93e84772d774fdda8fa1a5e89644` adds reaping; it is not the extraction source for this slice. Its core was read only to understand the boundary. The large verifier/substrate dependencies were read only in targeted spans, not in full. No source tests or host recovery commands were executed.

## Delivered contract

### Explicit project and host configuration

Require the existing `JV_PROJECT_ID`, `JV_PROJECT_ROOT`, `JV_STATE_ROOT` binding and reuse `jv-project.sh` configuration plus its pure binding verification. The cluster's existing project store must already be bound through W-C1/W-C2/W-C3 setup; this wrapper does not invent another binding or write project state. Worktree/cwd differences do not change the configured project identity.

Add one required absolute `JV_HOST_ROOT`, selected by the operator and shared across projects on that machine. The capacity paths are `<JV_HOST_ROOT>/locks/build.lock` and `<JV_HOST_ROOT>/locks/info`; neither contains a project ID. Different host roots are separate capacity domains, so incorrect per-project configuration cannot be claimed to serialize the machine. No fallback to HOME, cwd, an old host directory or a project-local lock.

Before opening or changing host paths, reject aliases and wrong path types along the configured root/locks/file/info paths. Require a cooperating local filesystem with flock semantics. Use private directory/file modes for newly created host state. Refuse legacy `JAUTO_BUILD_LOCK_FD`, `BUILD_LOCK_TEST_MODE`, `BUILD_LOCK_TEST_DIR` and `BUILD_LOCK_TEST_AVAILABLE_MB` when set, before reading or changing their targets; tests inject memory observations at the command boundary instead. New inherited ownership uses only `JV_BUILD_LOCK_FD`.

This reuses the accepted project helper unchanged. The host path validation is local to the new lock script; it does not add a general host registry or modify other slices.

### Commands and lifetime

- `build-guarded.sh <command> [args...]` resolves and execs its sibling `build-lock.sh run`. It preserves the caller's cwd, exact argv, stdin/stdout/stderr and command exit code. It does not select a project command, evaluate command text or schedule retries.
- `build-lock.sh run <command> [args...]` performs memory preflight, then attempts the shared kernel lock nonblockingly. It invokes no supplied command on contention, failed validation, failed metadata publication or failed lock acquisition.
- A successful outer invocation keeps an inheritable descriptor open throughout the command. Cleanup closes only its own descriptor; it never explicitly unlocks the shared open-file description and never unlinks/recreates the lock inode.
- A fixture-killed wrapper cannot free capacity while its command retains the descriptor. A background descendant that inherits it keeps the lock after the immediate command returns. A Node launcher that closes extra descriptors in spawned workers must itself retain the descriptor and await those workers.
- A launcher that detaches its work, closes the FD and exits ends this protection. Conversely, a detached launcher/worker that **retains** the FD can wedge capacity indefinitely after its parent exits (F1→I3/I7; JA #3814 code F1/R4). The bounded retained-child fixture proves continued exclusion until its explicitly controlled release, not automatic recovery. Both source ceilings remain explicit; recovery is excluded. An operator must arrange supported launcher lifetimes; this wrapper never reaps or forcibly unlocks a retained descriptor.

PID, project/root label and age metadata are diagnostic only. Missing/malformed/stale metadata cannot authorize a second command or override the kernel lock. Atomic private metadata replacement occurs only after acquisition; failures refuse command admission. Cleanup removes only the current holder's own metadata token. Metadata omits command arguments and environment values; project/root labels are supplied identifiers, not proof of liveness.

### Reentry

If `JV_BUILD_LOCK_FD` is present, fail closed unless all source checks pass:

1. It names a live numeric descriptor and the current regular lock file.
2. Descriptor and lock path have the same device/inode.
3. A separate open-file description returns the explicitly selected/documented flock conflict status (use `flock -n -E 75`). Only status 75 establishes contention. Every other nonzero status is an inspection error and refuses reentry, even if a later re-lock could succeed (F2→I4).
4. Re-locking the inherited descriptor succeeds, proving it is the owning open-file description.

A marker alone, a descriptor for another file, an unlocked same-inode descriptor, or an independently opened same-inode descriptor while another holder owns the lock is insufficient. Invalid markers do not fall back to a fresh acquisition. Valid nested work keeps the same capability and outer metadata; nested success/failure must not release the outer owner's slot. Reentry may cross configured projects because capacity belongs to the shared host, while each invocation independently verifies its project binding.

`verify-inherited` performs these checks without invoking a workload or publishing state. This is a kernel capability check, not a PID/namespace inference.

### Memory, status and failures

Retain the source's 4096 MiB available-memory threshold and exact equality boundary. Below 4096 refuses before the workload. A missing/malformed observation is explicitly unavailable and emits a warning; as in the landed source, it permits the kernel-locked command. This is a conservative admission hint, not a reservation, cgroup limit or proof that the build cannot exhaust memory. Read only the Linux memory observation; never scan process records. No new production test override or configurable threshold is needed.

`status` and `wait-info` inspect the existing lock through a separate descriptor and report held/unheld plus memory availability. They do not create/chmod/delete directories, lock files or metadata, and an absent host root remains absent. Failed inspection must be explicit unknown/nonzero, not an apparently free slot. Info fields are display-only and bounded; an invalid age never drives arithmetic overflow or lock decisions.

Retain ordinary source outcomes: contention 1, insufficient memory 2, usage/retired verbs 64, invalid inherited ownership 65, and the actual command's status after admission. A command may itself return 1 or 2; diagnostics distinguish admission refusal from command completion, so callers must not retry solely by numeric status. Unexpected setup/I/O failures are nonzero and never silently admit a workload. `acquire`/`release` remain refused with guidance to the lifetime wrapper.

### Generated output and adoption

Deliver the two scripts, generated host-capacity setup guidance and dated provenance, plus the bounded portability tests. Reuse existing Bash/Linux util-linux/coreutils/Python test dependencies; Node is needed only for the explicit Node-lifetime fixture. Generated setup documents the existing project binding prerequisite, shared host-root choice, supported child-lifetime requirement and manual invocation.

No live host lock is migrated or opened during adoption. An old PID/age consumer must stop using its old wrapper before its operator switches all cooperating projects to one new host root; mixed lock families do not serialize each other. This PR performs neither change. Copier renders into scratch projects; no new questionnaire option or scheduler installation is needed.

## Invariants and finite test list

| Invariant | Required behavior |
| --- | --- |
| I1 | Explicit verified project identity and one explicit host root; no fallback, alias escape, legacy override or foreign project-state access. |
| I2 | One kernel capacity owner across projects; contention and uncertain acquisition never invoke the workload. PID/age metadata cannot grant ownership, and lock inode persists. |
| I3 | Capacity lasts while a supported command/descendant retains the inherited descriptor; wrapper exit/failure cannot unlock it prematurely. |
| I4 | Reentry requires the actual owning descriptor capability; spoofed markers/same-inode independent opens refuse, and nested exit preserves outer ownership. |
| I5 | Memory and setup failures have truthful admission outcomes; accepted commands preserve exact execution semantics, and metadata failure cannot admit work. |
| I6 | Status/verification are read-only, retired verbs do not release ownership, and runtime code performs no recovery, signalling, provider or service action. |
| I7 | Real generated consumers prove the behavior in contained fixtures; test/environment/source containment is checked before execution, and source limitations remain explicit. |

| Cell group | Positive witness | Refusal / discriminating witness |
| --- | --- | --- |
| T1 → I1 | Two distinct bound projects, shared host root, separate state canaries; run from unrelated cwd with spaced paths. | Missing/mismatched binding, absent/relative host config, aliased or wrong-type host path and each legacy knob refuse before target/foreign-state access. |
| T2 → I2 | One admitted holder; five contenders across both projects all refuse; release permits the next project without changing lock inode. | Poison PID/age and remove diagnostic metadata while kernel holder remains live; no contender command executes. Failed lock inspection cannot report free. |
| T3 → I3 | Own fixture child survives killed wrapper; inherited background child survives normal wrapper exit; Node parent awaits descriptor-closing worker. Release is witnessed by later real acquisition. | Each variant denies a competing marker command until the final relevant descriptor closes. No host process absence assertion, PID-reuse probe or signal from metadata. |
| T4 → I4 | Nested same/cross-project calls and explicit verify-inherited work while outer holder remains; nested command failure preserves outer lock. | Marker-only, wrong file, unlocked same inode and separately opened same inode while held all refuse before command. A forced non-conflict probe error with an otherwise lockable same-inode FD must refuse, not proceed to successful re-lock (F2). Reentry does not republish metadata or explicitly unlock. |
| T5 → I5 | Memory 4096 and 4097 admits; unavailable warns then acquires. Exact spaced/empty/multiline argv, piped and heredoc stdin, cwd, streams and command status survive both entries. Closed FD 0 must remain closed, witnessed as EBADF rather than EOF from `/dev/null` (F3→I5). Retain foreground execution; the later source reaper background launch is what introduced its stdin-loss issue. | Memory 4095, forced metadata write/rename and lock-open failures run no command, leave no private temporary debris, and allow later acquisition when fault clears. |
| T6 → I6 | Status/wait-info report held/unheld; snapshots and access observations prove no mutation, including absent host root. | Unknown inspection remains nonzero; retired acquire/release and foreign-token cleanup cannot drop another holder's metadata/lock. Runtime closure refuses prohibited effect seeds before any child. |
| T7 → I7 | Real Copier cluster and solo output; full runtime closure, no JA coupling, synthetic homes, closed command allowlist and fixture-owned process handles. | Inherited environment/legacy path/source-effect seeds are rejected or contained before execution. No real source tests, shared host roots, Docker/provider/network calls or actual heavy workloads. |

Finite mutant set (17), fixed before RED (16 initial plus F2): bypass project binding (T1); redirect host lock under project ID (T2); skip flock (T2); steal from PID/age metadata (T2); cleanup uses explicit unlock (T3); drop inherited FD (T3); trust marker only (T4); omit owning-open-description check (T4); nested cleanup releases outer ownership (T4); invert memory boundary (T5); swallow command failure (T5); admit after metadata failure (T5); status creates state (T6); delete lock inode on cleanup (T2); bypass containment gate (T7); add a forbidden recovery effect (T6/T7, source refusal before child). The F2 mutant accepts any nonzero probe result as contention, and must fail the probe-error refusal cell. Syntax/setup failures never count as mutant kills. Add cells only for surviving mutants or traced review findings.

## Proof and review sequence

SPEC + test-list audit by o's commission → tests-first RED with intended failures and contained process lifetimes → one RED review → smallest GREEN implementation → finite mutants and actual generated-consumer smoke → one full code review → o verdict and i integration. A finding receives its traced RED cell and mutant; follow-up rules and round caps come from the active review/test pilot.

Before each render, disallow executable Copier tasks/extensions. Before each runtime or mutant child, check the complete operating closure and its permitted path/effect boundary. Fixtures use private temporary host roots and project stores, real kernel flock on those files, marker commands and synthetic memory observations. Only handles for processes spawned by the current fixture may be terminated for the required crash witness or teardown; cleanup must wait/reap them and never act on PIDs read from production metadata. Source fixtures are reading evidence, not executables to run unchanged.

Retain exact source hashes/read scope, RED/GREEN logs, child-lifetime/reacquisition evidence, mutated inputs and outcome classification in sealed packets. Preserve upstream source provenance without making JA names or issue numbers runtime rules. Run affected accepted regressions only if their shared inputs change, plus the current generated matrix/CI before integration. No local proof authorizes installation on a live host.

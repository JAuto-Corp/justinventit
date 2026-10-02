# Shared host capacity

`build-guarded.sh` runs one supplied command under a cooperative kernel flock.
All participating projects on a Linux host must choose the **same** host root.
The wrapper is inert until called; it installs no scheduler or service.

First configure `JV_PROJECT_ID`, `JV_PROJECT_ROOT` and `JV_STATE_ROOT` and bind
that project through the [cluster setup](CLUSTER.md). Existing binding is checked
without modifying project state. Then choose an absolute, non-symlink directory
on a local filesystem supporting flock, outside the project/state stores:

```bash
export JV_HOST_ROOT=/absolute/shared-host-capacity
scripts/build-guarded.sh your-build-command 'argument with spaces'
scripts/build-lock.sh status
scripts/build-lock.sh wait-info
```

Use that same value in every cooperating project. Different roots do not compete.
There is no HOME, current-directory or project-local fallback. Newly created
host directories/files are private. Directory aliases, nonregular lock/info
files, and legacy `JAUTO_BUILD_LOCK_FD`/`BUILD_LOCK_TEST_*` settings are refused.
The wrappers require Bash, util-linux flock, coreutils, jq, find, sed and awk.
Node and Python are test dependencies, not workload-wrapper dependencies.

The stable inode at `$JV_HOST_ROOT/locks/build.lock` owns capacity. PID, age and
project labels in `locks/info` are bounded diagnostic data, never authorization
to take capacity. Missing or poisoned metadata cannot free a kernel lock.
Publication is atomic and precedes command admission; publication failures
refuse the command. Cleanup only removes its own metadata token and closes its
own descriptor. It never deletes the lock inode or explicitly unlocks it.

The command inherits `JV_BUILD_LOCK_FD` and its open descriptor. Nested calls,
even from another configured project, verify the same inode, contention on a
separate descriptor (explicit conflict 75), and successful re-lock of the
inherited descriptor. A marker alone is insufficient. `verify-inherited` only
checks this capability. No PID discovery or namespace assumption is involved.

The command keeps its exact arguments, cwd, stdin (including a closed stdin),
stdout/stderr and exit status. Available memory below 4096 MiB refuses admission;
exactly 4096 is allowed. Unknown memory emits a warning and permits kernel-locked
work, matching the source policy. This is a hint, not a memory reservation.

| Status | Meaning before admission |
| --- | --- |
| 1 | Kernel contention |
| 2 | Insufficient observed memory |
| 64 | Usage or retired acquire/release verb |
| 65 | Invalid inherited ownership |
| Other nonzero | Configuration, binding, inspection or I/O refusal |

After admission the command's own status is returned, including 1 or 2. Read
the completion/refusal diagnostic; do not retry based only on the number.
`status` and `wait-info` never initialize state; failed inspection is unknown
and nonzero. One-shot `acquire`/`release` cannot own command lifetime and are
retired.

A crashed wrapper does not free capacity while a child retains the descriptor.
A Node launcher that closes extra descriptors in workers must itself retain the
descriptor and await its workers. A detached worker that closes the descriptor
escapes protection. Conversely, a detached worker retaining it can hold capacity
indefinitely after its parent exits. Arrange supported launcher lifetimes;
there is no automatic recovery, reaper, signal forwarding or forced release.
This is cooperative admission, not isolation against hostile local file swaps
or programs deliberately bypassing the wrapper.

Adoption is manual: stop old PID/age-lock consumers before switching all projects
to this shared kernel-lock family. Mixed lock families do not serialize each
other. Generation and tests neither open a live host lock nor migrate one.
See [dated provenance](CLUSTER_PROVENANCE.md#host-capacity-extraction).

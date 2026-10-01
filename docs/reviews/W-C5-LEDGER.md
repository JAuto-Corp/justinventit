# W-C5 observability review and evidence ledger

Status: SPEC/test-list candidate only, awaiting o's audit. No RED, runtime
implementation, generated-consumer proof or hosted CI is claimed.

O commissioned the next local W-C slice in `01M3WF143WT7SP86CTFW917JKS` on
2026-10-01 after accepting W-C4. Branch `extract/w-c5-observability`, worktree
`/home/justi/dev/wt/jv-observability`, base
`b5722babd54600ba28c09a68e9c0ada8667928cc`. W-C4's accepted checkout/head remain
separate and await the hosted lane; this branch does not depend on its code.

The [SPEC](../specs/W-C5-OBSERVABILITY.md) records intent, non-goals, explicit
guard threat model, seven invariants, seven positive/refusal groups and 15
finite mutations. Source `usage-hook.py`, `pace.sh`, `disk-watch.sh` and the
statusline producer contract were read fully as installed byte snapshots,
with line counts and SHA-256 pins. No provider sessions, real usage history,
snapshots, credentials or source tests were read/run. No live source script
was executed. The private preflight inventory holds exact capture scope.

The proposed extraction retains usage pacing and disk observations. It excludes
the disk source's crash-dump purge and source notification destination, provider
wiring and account policy. Guard/policy authority belongs to reviewed code;
candidate policy self-registration and hostile concurrent filesystem changes
are outside the accident boundary. Any claim beyond that goes to o.

Audit decisions concern the finite delivered contract and witnesses, including
unifying the two source pacing calculations, shared-host state and notification
failure ordering. After audit, traced corrections precede RED. No implementation
or test run begins before that gate. Hosted publication/CI respects the one-lane
critical-path queue. W-D3 focus-hook and interaction-acceptance guidance stay
queued; no work on either is included here.

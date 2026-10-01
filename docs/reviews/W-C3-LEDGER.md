# W-C3 review and evidence ledger

## Commission and current gate

O's `01M3V742AADC9P8T8CVTY76SJC` (2026-10-01) accepts W-C2 at
`1d6e3f9d7bf6b03964e854efa58bafb26261d666` and commissions W-C3 liveness,
SPEC first, same review/test flow. W-C2 PR CI `36832519964` passed every step;
duplicate push `36832514595` is terminal cancelled. I owns that integration.

Current deliverable is [W-C3-LIVENESS.md](../specs/W-C3-LIVENESS.md), for o's
pre-code audit. No production code, new runtime tests or source-script execution
is part of this SPEC commit. No independent verdict is claimed.

## Reading and reconciliation

The source pin remains `57d273154cf029158b7cc118143808e524baf28c`. The author
read complete cadence/heartbeat/watchdog/propagation bodies and both watchdog
suites through source Git objects, plus the existing generated pacemaker,
heartbeat writer, standby tests and guidance. The private inventory records
hashes and exact read scope; the source-test map labels retained/adapted/excluded
witnesses. No source suites were executed or copied wholesale.

Three differences require an explicit audit disposition:

- The source watchdog has disabled-by-default destructive revival and unresolved
  lease/canary gaps. The existing JV pacemaker injects prompts and can call an
  optional respawn hook. The SPEC proposes report-only consolidation, with an
  explicit migration notice and refusal of retired action knobs; automatic
  recovery is deferred. This is a deliberate change to current JV behavior.
- Source standby observation uses mail backlog and process presence. JV's
  normative protocol specifies a leased canary/heartbeat detector. The SPEC
  preserves useful partial observation, labels its limits, and leaves the
  normative target intact. A present process is not loop health.
- The source aggregate heartbeat hook is not the producer for per-seat cadence.
  The existing JV writer is that producer but has different roots/role variables
  and rewrites a fixed field set. The SPEC shares one project-scoped, serialized
  writer so turn-end updates preserve schedule, doorbell and ceremony evidence.

The proposed roster is local seat-record UNION cadence-file enumeration; no
PostgREST/hub fallback or credentials. Existing shared identity, launcher and
mailbox interfaces supply the project boundary. The acceptance list is seven
paired groups and 21 finite mutants, traced to I1–I7; the SPEC gate may revise it
before RED. Destructive recovery source fixtures are explicitly excluded.

## Evidence and next action

The SPEC packet binds the exact commit and diff, source hashes, existing JV
hashes, normative sections read, source-test mapping, commission and W-C2
acceptance/current-head CI receipts. It contains no generated runtime result:
that belongs to the later RED/GREEN gates.

Next: o commissions the SPEC audit under the current provider-availability
disposition. No author-spawned review and no runtime implementation before the
SPEC disposition. Follow the pilot's bounded rounds; no extra provider-diversity
debt or unrequested design expansion. A authors, o decides, i integrates.

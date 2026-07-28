# Doorbell r4 (FINAL) — ready for ratification

Status: FINAL DRAFT r4. Author: o, 2026-07-28. Red-team chain COMPLETE:
r1 (withdrawn — competing weaker contract) → r2 (rebased) → confirm-1 REVISE (8 findings,
all accepted) → r3 → confirm-2: all 8 graded RESOLVED + 3 refinements → r4 (this, refinements
folded). Verdicts archived under ~/.jauto-orchestration/sol-runs/. Ratification = the JV spec
PR (deltas split across SEAT_PROTOCOL / HUB_DATA_MODEL / MODEL_MATRIX) with this chain
attached per SOL-AT-DESIGN.

## A. Spec deltas — now split by normative owner (JV PR touches three specs)

A1 (SEAT_PROTOCOL §4). RUNTIME-NEUTRAL INVARIANT: actionable asynchronous work — any side
    process whose result someone must act on — is SUPERVISED (some component outside the
    work itself observes its termination) and produces a DURABLE TERMINAL OUTCOME (A2's
    completion event) on every exit path including failure and cancellation. Unsupervised
    detachment (`nohup … &` class with no supervisor) is forbidden. Note: harness tracking
    alone does not satisfy the durability half (a tracked process can die before publishing
    durable evidence); a supervised host process that detaches CAN satisfy both.
    → Claude launch mechanics + the 2026-07-28 empirical notify table + Codex Phase-4 probe
    live in MODEL_MATRIX runtime-adapter conformance, not here.

A2 (HUB_DATA_MODEL — normative owner). GENERIC COMPLETION EVENT: new event type/verb
    carrying {hub_id; run/correlation id; terminal outcome: success|failure|cancelled|
    timeout; result reference or digest; optional verdict + schema-validity; originating
    dispatch hub_id (OPTIONAL — undispatched work has none); producer; recipients
    (deduplicated); optional diagnostic/error reference}. Result reference/digest is
    OPTIONAL (cancelled/timed-out work may have neither). ONE append projects to all
    recipients atomically — never N separately-failing sends; o-as-invoker yields one
    delivery, not two. SEAT_PROTOCOL delta shrinks to one clause: actionable completions
    MUST use this event, and it is a doorbell source. (B6's wrapper mail becomes this
    event's first producer.)

A3 (SEAT_PROTOCOL §4 owns defer behavior; HUB_DATA_MODEL owns the class taxonomy;
    MODEL_MATRIX owns per-seat mappings/thresholds). MESSAGE-CLASS INTERRUPT FILTER with a
    BOUNDED DEFERRED RING: doing seats' own-mailbox doorbells ring immediately on actionable
    classes (dispatch, attention/alert, direct request, and ACTIONABLE COMPLETION EVENTS
    per A2) and DEFER info/status — but deferral
    is bounded by max_deferral, fixed strictly below the §2 standby mail_grace
    at max_deferral the doorbell rings anyway. max_deferral is not a free knob — it is
    GENERATED under validated compositional constraints:
      max_deferral + poll_budget + commit_budget < mail_grace   (stall clock never beaten)
      max_deferral + poll_budget ≤ fallback_interval            (Part C max-latency SLO holds)
    (default poll_budget = 2× watcher poll interval; commit_budget = the class's cursor-commit
    SLO). The OLDEST deferred event's ring deadline is fixed at its arrival; new arrivals
    never reset it. The §2 liveness predicate is UNCHANGED — bounded deferral can never age
    mail into a false STALL. Unknown or malformed classes ring immediately
    (fail-toward-ringing). Coordination seats' total-inbound shape stays unfiltered.

A4 (SEAT_PROTOCOL §1). Watcher capability SPLIT from live watcher state:
    - capabilities.watcher_locations: subset of {host, in-session} the runtime supports.
    - live watcher record (seat-control state): {location, generation, target session
      handle, status, last_poll_at, expires_at}. The watcher itself renews last_poll_at/
      expires_at on every poll via a channel OUTSIDE the seat's turn-end heartbeat (e.g. the
      watcher process touches its own liveness field/file the pacemaker reads). An
      in-session watcher is conforming ONLY while that externally-readable renewal is
      current: session death → renewal stales → pacemaker detects watcher death from a
      different failure domain. Record-of-existence alone proves nothing (a dead watcher
      leaves the same record). EMPTY watcher_locations: standby/doorbell mode is FORBIDDEN —
      the seat degrades to active-cadence or human-wake per §1 capability rules (the
      explicit degradation rule the old `watcher: none` carried).

## B. JAuto conformance gaps (post-C3 dispatch queue; ordered — B0 is prerequisite)

B0 (NEW, prerequisite — from confirm-1 blocker). AUTHORITATIVE-APPEND TRANSPORT: today
    `msg.sh send` writes recipient JSONL directly with no hub_id, and hub verbs write
    mailbox-first with a later ingester creating registry state — a transport/record split
    that violates HUB_DATA_MODEL §1 (authoritative hub append; mailboxes are derived
    projections) and is the same disease as #3399. Migration: all sends become identified
    hub events (hub_id on plain mail); recipient files become projections written by the
    append path; sender read-back = non-consuming digest verification per SEAT_PROTOCOL §5.
    B1 cursors and A2 completions build ON this; they do not ship before it.
B1. msg.sh two-cursor conformance (processing cursor commits after idempotent-by-hub_id
    side effect; read-at-print retires). Depends on B0.
B2. Lease machinery (§2 CAS + fencing tokens) — rides the B4 seat-record migration.
B3 (corrected per confirm-1): watchdog gaps = PID-skip, missing canary/floor branch,
    predicate-table nonconformance, HARDCODED ROSTER (violates §4 registry-enumeration),
    and LIVE-VS-REPO DRIFT (live host copy ≠ newer repo mirror; main checkout carries no
    watchdog file at all — violates versioned-in-repo). The completion-line claim in r2 was
    FALSE and is withdrawn (both copies already emit it). All items remain Sol-asserted
    pending the #3401 grounding pass; fix requires one deployable source with provenance +
    propagation read-back.
B4. Seat records (§1/§6a migration) — prerequisite for A4 state and B2.
B5. Host-side watcher under the pacemaker replaces the nonconforming in-session prototype
    (confined to the retired-g alias until then). Adds per confirm-1: dynamic sender-file
    discovery, to-all coverage, per-seat (not per-file) quiet-window coalescing, generation
    supersession on restart.
B6. Wrapper completion = A2's first producer (owner E, post-C3; rule 01KYK8TC8P stands as
    the interim: tracked launches only).
B7. §4a Stop-hook rollout (D's #3383) — warn-only → enforce-once with negative fixture.
B8 (NEW). DUAL-SIGNAL COALESCING: harness task-exit notification + A2 completion event can
    race into two turns. run_id correlation dedupes; a doorbell poke is suppressed when the
    processing cursor already covers the completion; o-as-invoker recipient dedup per A2.
    Fixtures cover both orderings.

## C. Rollout — thresholds and gates (per confirm-1)

Prerequisites to shadow: B0, B1, B3 (grounded+fixed), B4, B5 built. Prerequisites to LIVE
pilot additionally: B2 (leases — every live wake goes through one), B8 (dual-signal
coalescing), and B6 (completion event producer — completion behavior IS in pilot scope);
full normative
conformance suites pass offline — §2 lease set INCLUDING delayed-racer-after-commit,
renewal-vs-acquisition race, registry recreation mid-lease; crash-before/after cursor
commit; transport partial-write recovery; filter-induced false-stall (A3 bound holds);
watcher restart/generation supersession; dual-signal both orderings; unknown-class ring.
SHADOW (host watcher logs would-have-rung, invokes nobody): ≥1 week AND per-class sample
floors — ≥200 total events, ≥30 per actionable class, ≥2 broadcast bursts, ≥1 coordination-
seat day. Go/no-go SLOs: p95 event→would-ring ≤ 90s, max ≤ fallback interval; 0 lost events
(head vs processing-cursor audit); duplicate-ring ≤ 1%; watcher death detected ≤ 2× poll
interval in kill tests; 0 filter-induced false stalls.
LIVE PILOT (one doing seat + o): ≥3 days AND ≥100 events; inject watcher kill, session
kill, pacemaker kill/restart; SLOs as shadow plus event→processing-cursor-commit p95,
fallback-rescue ≤ 5% (every rescue counted as a doorbell FAILURE), token cost per useful
message ≤ cadence-era baseline (measured, cached+uncached input, output, tool).
Cursor-commit SLOs (per class): actionable classes p95 event→processing-cursor-commit
≤ 5 min; deferred classes ≤ max_deferral + 5 min.
FLEET: staged cohorts (2 seats per stage). ROLLBACK IS TWO-TIER: IMMEDIATE on any
correctness failure — a lost event, cursor corruption/regression, fencing failure, or a
false stall (one occurrence suffices); sustained-window (one day) only for statistical
regressions — latency, duplicate-rate, token cost. Miss-rate CLAIMS carry binomial
confidence honestly (n in the hundreds).

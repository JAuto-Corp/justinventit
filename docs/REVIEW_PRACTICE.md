# Review Practice: consequence-aware, context-fed, discovery-first (v1)

> Normative for DEV_LOOP stages 0 (draft red-team), 2 (spec-audit) and 5 (review), in every
> profile and runtime. Owner-ratified 2026-09-26. It complements `DEV_LOOP.md` and
> `GATE_INTEGRITY` rather than replacing them: gates still fail closed, and this document
> defines what may hold a gate closed.

## Why

The value of review is finding **real consequences in the context of the whole system**. In
one measured week of same-family review (JA, 2026-09-24..26; o's tally of the verdict files in
`~/.jauto-orchestration/sol-runs/`, JA PRs #3674, #3677/#3683, #3662 and #3682 among others), about
39% of 160+ review runs returned BLOCK, and single slices took up to 19 runs (#3674). The rounds produced two kinds
of finding:

- **Signal.** A consequence someone would feel: live under-billing (attached add-ons
  dropped from 18 invoices), invoice lines deleted by a rebuild, a price preview hiding
  parts from technicians, credentials in a world-readable dump, tests passing without
  executing, a sweep silently stopping at 1,000 rows.
- **Noise.** Hardening with no consequence (defense-in-depth on a local-only, synthetic-
  credential test witness), plus one new edge case per round in an area already judged
  safe.

Reviewers are deliberately fresh-context, which protects independence, but they were also
context-FREE. With no production posture, threat model, or accepted residuals, every path
looks internet-facing. The practice below keeps fresh context and full scrutiny, and adds
the big picture.

## 1. The context card (required review input)

The requester attaches a card to every review request. It carries FACTS, not the author's
reasoning, so the reviewer stays independent.

| Field | Content |
|-|-|
| Purpose | what the change is for, in one or two sentences |
| Live posture | what is deployed, who uses it, which switches are on or off (e.g. single-user pilot, pre-public, feature observe-only, sender off) |
| Affected parties | who or what can be harmed if this is wrong: customers, money, data, credentials, CI, operators |
| Non-goals | what is deliberately out of scope, with the ruling ids |
| Accepted residuals | risks already accepted, with ruling ids |
| Code maturity | "Surrounding code may be sketch/placeholder, untested framework; do not assume existing code is finished or coherent. Flag coherence gaps against the purpose." |

A reviewer may argue AGAINST a non-goal or an accepted residual. To do so it must name the
consequence that makes the decision wrong; it may not silently re-litigate.

## 2. Finding fields (required)

Every finding carries these fields, in addition to the canonical verdict schema:

- `consequence`: the concrete harm (who is affected; what money, data or access). "Could be
  more robust" is not a consequence.
- `reach`: exactly one of
  - `PROD`: reachable in production or on a path that ships.
  - `CI_SAFETY`: could make CI lie (false green or a hidden skip), or touch a shared or real
    environment from CI.
  - `LOCAL_ONLY`: confined to an opt-in local or synthetic harness.
  - `HYPOTHETICAL`: requires conditions not present and not planned.
- `origin`: `INTRODUCED` (by this change) or `PRE_EXISTING`.
- `class`: a short failure-class label, used for the delta-round rule (§4).

## 3. Blocking eligibility

- Only `reach ∈ {PROD, CI_SAFETY}` may produce a blocking verdict (`revise` / `BLOCK`). An eligible
  reach is necessary but not sufficient: blocker severity must be justified by the stated consequence.
- `LOCAL_ONLY` and `HYPOTHETICAL` findings are **notes**. The author may take cheap ones;
  deeper ones are recorded as residuals, never chased.
- `PRE_EXISTING` findings are **never auto-deferred and never auto-blocking**. The director
  (solo profile: the session) dispositions each one:
  - **FOLD**, a "Eureka refactor": same subsystem, consequential, and it makes the slice more
    coherent with the big picture. This is the default lean for in-subsystem finds, per the
    Refactor-With principle.
  - **FILE**: distant, or it needs its own design; a durable issue plus a hub capture.

## 4. Discovery first, deltas after

1. **Round 1 is wide.** It asks: "enumerate every way this could fail *with a
   consequence*". For money, security, data-migration or cross-cutting designs, round 1
   includes a reviewer from a **different model family** than the author (the cross-family
   finder). This is where provider diversity pays: a different blind spot, not just a
   repeat.
2. **Rounds 2+ are delta-scoped.** They cover the changed hunks and the previous round's
   findings. A **new class** found in a later round (including a defect introduced by a
   correction) may block when its reach is `PROD` **or `CI_SAFETY`**, the same eligibility as §3.
   Round number and class novelty never waive a substantive safety finding; anything else new
   becomes a note or a follow-up.
3. **Round cap: 3.** After it, structural blockers escalate to the director with a short
   packet. The cap bounds *repetition*, not *acceptance*: fail-closed gates and the
   no-unresolved-blockers exit rule still apply. Nothing loops silently.
4. **Local-only harness hardening is capped at one round.** Beyond that, residuals are
   documented (e.g. "no guarantee of no-operation after abort; target identity, synthetic
   credentials and a post-condition assertion bound the harm").

## 5. Scoreboard (learn which review is signal)

When the director dispositions a finding, it records one tag:
`REAL_PROD` · `REAL_LATENT` · `NON_CONSEQUENTIAL` · `WRONG` (a false claim), together
with the reviewer's model family and charter. Periodically compare signal rates per
reviewer, family and charter, and adjust the matrix. A retro-review batch by a different
family over already-landed work is the canonical experiment: it shows what one family
missed that the other found.

## 6. Provider mix (see `MODEL_MATRIX.md`)

When both families are available:
- **Design and round-1 finder:** the thinking tier plus a cross-family finder.
- **Doing:** cost-efficient doing seats.
- **Delta reviews:** same- or cross-family, cheap.
- **Money/security lens:** cross-family, always.

When only one family is available, the fallback substitutes for **exactly one requirement**: the
cross-family (cross-runtime) second opinion. Everything else still applies: the required
number of fresh-context audits, their independence (distinct seeds and lenses), the stage-0
charter and terminal ratifier confirmation (`DEV_LOOP.md` §1a), and every acceptance obligation.
Round 1 uses at least two independently seeded same-family passes. The substituted cross-family
opinion is still **owed**. This is exactly the `ARCHITECTURE.md` §2 **Provider bookend** path:
proceed at the authorized equivalent tier, record `bookend: <runtime> missing` in the acceptance
record (provenance, never a waiver), and make sure the owed opinion exists before acceptance
wherever the profile requires it. Stricter gates win. The slice joins a cross-family retro once the
other family returns. An owner-authorized temporary suspension (e.g. a usage stretch) is a
**logged deviation**, not a change to this contract.

## 7. Execution hygiene (lessons that cost cycles)

- **Rehearse before target.** Harnesses written without execution get a credential-free,
  end-to-end rehearsal up to the first target call before any shared or hosted attempt.
- **Don't nest review runners inside sandboxed seats.** Submit through the host review
  queue. A nested run can "pass" with no code verdict, and that must never count.
- **Stale-artifact skepticism.** Before calling a type error a baseline break, check the
  tracked file at the exact ref and clear build caches.
- **Same parser as the target.** Environment or flag refusal scans parse sources exactly as
  the target process does.

## 8. Adoption

- **Charters and templates:** the review runner's charter prompts require the context card
  (§1) and the finding fields (§2), and state the blocking eligibility (§3) and delta rule
  (§4). Keep the verdict schema backward-compatible; the new fields are optional for older
  consumers.
- **Project contract:** the project's entry contract (AGENTS.md / CLAUDE.md) references this
  document in its development-loop line. The project's gate-integrity doc names §3 as the
  definition of an actionable finding.
- **JA (reference implementation):** `scripts/sol-review.sh` charters, the review-queue
  prompt template, `AGENTS.md` § Development Loop, and `docs/agentic/GATE_INTEGRITY.md`.

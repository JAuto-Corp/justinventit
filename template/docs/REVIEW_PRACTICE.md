# Review practice: intent, consequences and bounded correction

> Canonical provider-neutral policy, rendered unchanged by Copier. The framework's
> DEV_LOOP and TDD_GATE define the surrounding gates; the project's entry contract
> selects its profile. This policy defines review practice, not automatic enforcement.

## Why

The value of review is finding **real consequences in the context of the whole system**. In
one measured week of same-family review, about 39% of 160+ runs returned BLOCK and single
slices took up to 19 runs. The rounds produced two kinds of finding:

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
| Purpose | the SPEC Intent and numbered invariants (`I1..In`), in one paragraph |
| Live posture | what is deployed, who uses it, which switches are on or off (e.g. single-user pilot, pre-public, feature observe-only, sender off) |
| Affected parties | who or what can be harmed if this is wrong: customers, money, data, credentials, CI, operators |
| Non-goals | repeat the SPEC non-goals, with the ruling ids |
| Accepted residuals | risks already accepted, with ruling ids |
| Code maturity | "Surrounding code may be sketch/placeholder, untested framework; do not assume existing code is finished or coherent. Flag coherence gaps against the purpose." |

A reviewer may argue AGAINST a non-goal or an accepted residual. To do so it must name the
consequence that makes the decision wrong; it may not silently re-litigate.

## 2. Finding fields (required)

Every finding carries these fields, in addition to the canonical verdict schema:

- `trace`: the accepted invariant (`I3`) or purpose threatened, plus the earliest affected
  gate and smallest discriminating check. Untraceable findings are NOTE at most; discoveries
  outside intent are FILED separately.
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

- A blocker must trace to accepted intent or an invariant. Review can discover a defect,
  but cannot invent a requirement; a proposed new guarantee needs explicit scope disposition.
- Only `reach ∈ {PROD, CI_SAFETY}` may produce a blocking verdict (`revise` / `BLOCK`). An eligible
  reach is necessary but not sufficient: blocker severity must be justified by the stated consequence.
- `LOCAL_ONLY` and `HYPOTHETICAL` findings are **notes**. The author may take cheap ones;
  deeper ones are recorded as residuals, never chased.
- `PRE_EXISTING` findings are **never auto-deferred and never auto-blocking**. The director
  (solo profile: the session) dispositions each one:
  - **FOLD**, a "Eureka refactor": same subsystem, consequential, and it makes the slice more
    coherent with the accepted intent. Obtain an explicit scope decision for any new
    requirement; proximity alone does not admit more work.
  - **FILE**: distant, or it needs its own design; a durable issue plus a hub capture.

## 4. Review/test flow

This Standard+ flow preserves the project's existing Quick exemptions; it adds no
full audit or TDD requirement to a change that already qualifies for one.

1. **SPEC + test-list audit before code.** State Intent, numbered invariants and Non-goals.
   Apply the minimum-solution discipline in `SKILL_MODES.md`. The cross-family auditor asks
   what failure the list would miss against those invariants. Preserve the profile's
   initial independent audit cardinality. SPEC audit cap: **two rounds**; a still-blocked
   SPEC goes to the director for a scope cut, not a third round.
2. **RED review, tests only.** Each cell names `I#` or `F#→I#`, asserts the invariant and
   fails for its intended reason. Minimum: one positive and one refusal cell per invariant,
   plus one cell per traced finding. Missing dependencies or broken setup are not RED.
3. **One full first-round code review at GREEN**, cross-family, at the authorized xhigh
   judgment tier. Inspect the whole affected flow against intent and consequences. The
   provider-availability exception in §6 applies; it never supplies a missing opinion.
4. **Follow-up code fixes.** Each finding gets a RED cell and a mutant showing that the
   cell catches the bug. A small single-finding fix with unchanged scope and guarantees
   is then trusted to those tests: no model re-review. Money, security or locking fixes
   still get **one narrow independent re-review**. Other corrections retain one focused
   confirmation at the corrected exact head; scope or guarantee changes (including
   removal) retain full affected audit cardinality. A prior-head opinion is not current.
5. **Bound the negative space.** Mutation testing targets invariant-bearing code only
   (e.g. flip a condition, drop a guard, swap lock order). Beyond the minimum set, add
   cells only for surviving mutants; all killed means done. This bounds test creation,
   not the TDD_GATE harness-integrity evidence, controls or restoration requirements.
6. **Code-review cap: three rounds.** Later model rounds, when required, cover changed
   hunks and prior findings. New findings still need intent trace and §3 eligibility.
   At the cap the director rules; a cap never turns unresolved required evidence into
   PASS. After two failures at one gate, diagnose the gate/harness before another attempt.
   Local-only harness hardening remains capped at one round, with residuals recorded.

Why: tests shared design blind spots, while repeated reviews grew slices and correction
loops. No new mutation runner or enforcement hook ships with this policy.

## 5. Scoreboard (learn which review is signal)

When the director dispositions a finding, it records one tag:
`REAL_PROD` · `REAL_LATENT` · `NON_CONSEQUENTIAL` · `WRONG` (a false claim), together
with the reviewer's model family and charter. Periodically compare signal rates per
reviewer, family and charter, and adjust the matrix. In the existing record also track
rounds per slice, findings per stage and escaped defects (CI or production); do not add
a new reporting system. A retro-review batch by a different
family over already-landed work is the canonical experiment: it shows what one family
missed that the other found.

## 6. Provider mix and availability

Normal pairing uses different providers at matched authorized tiers for design and the
first finder review; money/security reviews use the same cross-family preference.
Substantive authoring, challenge or acceptance on the exact subject may satisfy a
provider bookend; relay reads and predecessor-head work do not. R2/R3 boundaries use
thinking-tier participation (exposure tiers: `DELIVERY.md`). Other judgment-bearing work
can pair author and independent reviewer at the authorized tier; trivial mechanical work
with deterministic checks owes no extra bookend review.

When a frontier provider is exhausted or unavailable, use the available frontier provider
at the authorized tier and **proceed as though the cross-provider preference were met**.
There is no provider-diversity debt and no mandatory retroactive duplicate review. Resume
normal pairing prospectively when availability returns. Record actual author, challenger
and acceptance provider/model/effort and exact subject; never label same-provider work as
cross-provider evidence. Keep role independence, fresh context/blindness, required opinion
count, assertion approvals, RED/GREEN, integration and effect gates. Substitution neither
supplies a missing independent opinion nor permits a lower tier or runtime-policy bypass.

Why: a defer-until-reset reading stranded authorized work without adding an independent
opinion. This is the single availability rule; it does not change initial audit cardinality.

## 7. Execution hygiene (lessons that cost cycles)

- **Rehearse before target.** Harnesses written without execution get a credential-free,
  end-to-end rehearsal up to the first target call before any shared or hosted attempt.
- **Don't nest review runners inside sandboxed seats.** Submit through the host review
  queue. A nested run can "pass" with no code verdict, and that must never count.
- **Stale-artifact skepticism.** Before calling a type error a baseline break, check the
  tracked file at the exact ref and clear build caches.
- **Same parser as the target.** Environment or flag refusal scans parse sources exactly as
  the target process does.

## 8. Adoption and enforcement status

- **Charters and templates:** the review runner's charter prompts require the context card
  (§1) and the finding fields (§2), and state the blocking eligibility (§3) and delta rule
  (§4). Keep the verdict schema backward-compatible; the new fields are optional for older
  consumers.
- **Project contract:** the project's entry contract (AGENTS.md / CLAUDE.md) references this
  document in its development-loop line. The project's gate-integrity doc names §3 as the
  definition of an actionable finding.

The entry projections are hand-written until policy generation exists. Reading this policy
sets instruction behavior; it does not install hooks, reviewer pins or model enforcement.
Pinned reviewers and runtime adapters are separate extraction slices. The framework's
sensitivity check and runner-owned ledger remain specified, not shipped (TDD_GATE §3).

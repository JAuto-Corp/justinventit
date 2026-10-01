# W-D1 — Portable workflow skills

One procedure source serves both runtimes: move the existing workflow skills to
`.agents/skills`, reconcile their procedures with JV's current policy, and generate
Claude's copies and command pointers with the existing projection tool.

Status: **SPEC for o audit; no implementation authorized by this document.**
Author a; director o; integrator i. Commission: o
`01M3WP17Q4ZVHS6GKC67P84WNG` (2026-10-01), next slice in the accepted extraction
plan. Charter: `JV-EXTRACTION-PASS.md`, X1–X6. Base:
`b5722bab` (main, freshly fetched); no W-C4/W-C5 implementation dependency.

## Intent and threat model

A generated project must offer `scope`, `go`, `check`, `capture`, `team-lead` and
`work` through one provider-neutral procedure tree. Those procedures must preserve
the exercised planning, implementation, review, capture and handoff flow while
using the project's own targets and current JV gates. Existing five JV workflow
skills provide the starting bodies; `go` adds a small execution front door that
routes to the existing work lifecycle, not another state machine.

This is an **instruction and packaging boundary for reviewed cooperating code**.
The shipped prose influences future agent actions, so stale authority, missing
procedures and implicit source-project targets matter. It does not mechanically
enforce obedience, prove model reasoning quality, or sandbox hostile skills,
candidate checker changes, runtime plugins or filesystem races. Fixture checks
prove bytes, routing, reference closure and selected instruction contracts; they
do not prove that a live agent performed the workflow correctly. Independent
review checks the instruction meaning. Missing runtime capabilities remain
unavailable rather than being represented as tested parity.

Proof runs only trusted, reviewed repository generation/check code against
disposable local trees. Source skill examples and mutated skill text are **data**:
never execute their shell blocks, invoke a skill in a live model, dispatch a seat,
read provider credentials, send mail, open issues, create a database, or run
cleanup as part of the suite. Copier runs with tasks disabled in the dedicated
suite. Existing CI's separate runtime receipt continues to cover its three pinned
upstream skills; it is not evidence for these six workflows.

## Non-goals

- W-D2 reviewer definitions/pins; W-D3 hooks, profiles, focus-on-wake and runtime
  installation; the separately queued interaction-acceptance guidance; W-E data
  isolation/TDS adapters. No hidden implementation of a deferred slice.
- A new orchestration registry, convergence engine, model router, policy engine,
  runtime receipt protocol, issue tracker or mutable state format.
- Moving all remaining domain, verify, chain, patterns or e2e skills. Selected
  workflows cease depending on stale chain/audit procedures; unrelated existing
  skills remain a separate surface, not silently certified by this extraction.
- General semantic verification of Markdown, hostile checkout isolation, arbitrary
  symlink-race resistance, or a guarantee of actual runtime discovery/obedience.
- Live adoption in JA or the host installation. JA source files remain read-only.

## Orientation and source disposition

Source snapshot: JA checkout HEAD
`bd3e7821473401f93ce23af621849f93a49435ef`, observed 2026-10-01. The six source
directories contain 30 files / 218,943 bytes. `team-lead/SKILL.md` is locally
modified and `team-lead/context/modified-files.json` is untracked; their snapshot
hashes, not HEAD alone, identify the bytes inspected. The latter is transient
state and is excluded. Private `wd1-preflight/source-inventory.json` records each
path, byte count, SHA-256 and last committed revision/date. No source procedures
were executed. Public provenance records sanitized source references and hashes,
never local absolute paths or private state.

| Source / existing target | Retain | Reconcile or exclude |
|---|---|---|
| JA `scope/SKILL.md`; JV `orchestrators/scope/{SKILL,converge}.md` | Orient/equip/act; grounded names, numbers and consumers; plan/test artifacts; dependency collisions | Old mandatory minimum rounds, 5/8-round escalation ladder, automatic nearby-refactor absorption and chain self-auditing yield to `REVIEW_PRACTICE.md` and scoped director decisions. |
| JA `go/SKILL.md`; JV `work/continue.md` | Resume the accepted plan or admitted findings; load the relevant installed domain guidance; execute the next bounded item | No new `levers.go` state or parallel relay. `go` points at canonical `work/continue.md`; stale chain flags cannot grant acceptance or reset a hold. |
| JA `check/SKILL.md`; JV `check/{SKILL,converge}.md` | Establish changed surface; distinguish reading from execution; trace findings and evidence; relay admitted corrections | Current review policy owns cardinality/caps/provider availability. No author self-ACCEPT, unbounded audit waves, scope expansion, inferred model tier, or automatic publication from a `pass` string. |
| JA/JV `capture` bodies and five mode files | Quick capture, blockers, audit/findings deduplication, new epic vs existing-epic triage, durable evidence and return to scope | Use project issue/hub/local capture route; inspect existing records before writing. No hard-coded upstream issue destination, label taxonomy as universal authority, automatic-issue claim from a signal, or forced provider-specific question tool. |
| JA/JV `team-lead` and spawn templates | Disjoint write ownership, explicit roots/targets, bounded tasks, one shared-data smoke before fan-out, terminal evidence and recovery | Remove source staging fallback, provider model literals, Claude TeamCreate/WAIT rules as universal claims, and assumed inherited capabilities. A commissioned lead uses only its runtime's installed/permitted mechanism. Missing judgment pin/commission is unresolved, not a prose-enforced tier. |
| JA/JV `work` start/continue/pause/handoff/done/epic-plan/sprint | Re-anchor in plan; reconcile git/PR/own-seat mail; append local state; preserve exact next action; distinguish authored, reviewed and integrated | No checkout/switch in a shared tree, blanket `git add -A`, close-before-integration, author merge, unqualified force-push/retrigger, broadcast-to-all, or assumed scheduler tool. Existing authority permits progress; a pointer alone grants no effects. |
| JA `work/{pr-ready,emergency,sprint-plan,sprint-detail}.md` | Minimal readiness record, honest emergency handoff, sprint detail within accepted contracts | Reuse work mode files; no duplicate planning framework. Exclude JA label/DB resolution, admin-merge and empty-commit recipes, TDS commands and internally contradictory “NO I/O, then commit everything.” |
| JA `work/patterns/*`, `worktree-list.md`, `worktree-cleanup.md`; JA spawn-template domain roles | General lessons already represented by the policy and the bounded procedures above | Do not copy domain schemas, seed/foundation implementation, registry repair, remote deletion, forced worktree cleanup, browser allocation, or source-specific reviewer waves. W-E/D2/D3 remain deferred. |

The existing projection generator/checker handles three immutable upstream skills
with an exact three-file layout. Its flat-file `materialize` and difference logic
can serve these editable workflow skills too; no recursive copier is needed.
Current commands duplicate procedures and current entry transitions reference
`orchestrators/work`. The matrix resolves bare slash names only through commands,
and `test-skill-multiskill.py` asserts the old work path and bare wrapper files.
Those are real consumers to migrate, not evidence to ignore.

## Bounded design

### Canonical files and routes

Six canonical directories under `template/.agents/skills/`, each with exactly one
`SKILL.md`, matching basename/name and a nonempty discovery description:

| Skill | Additional flat Markdown procedure files |
|---|---|
| scope | none; current policy replaces `converge.md` |
| go | none; routes to `../work/continue.md` |
| check | none; current policy replaces `converge.md` |
| capture | `block.md`, `audit.md`, `findings.md`, `epic.md`, `triage.md` |
| team-lead | `spawn-templates.md` (provider-neutral task record, no executable dispatch example) |
| work | `start.md`, `continue.md`, `pause.md`, `handoff.md`, `done.md`, `epic-plan.md`, `sprint.md`, `sprint-plan.md`, `sprint-detail.md`, `pr-ready.md`, `emergency.md` |

Procedures live once in this canonical tree. Governing rules remain in existing
neutral docs (`DELIVERY.md`, `REVIEW_PRACTICE.md`, `SKILL_MODES.md`, the project
entry's development loop/scope/git workflow). Link them instead of copying rules
or inventing a missing `docs/MODEL_MATRIX.md` in generated projects. The installed
project's actual role/pin configuration determines usable delegation. Document
unsupported or project-supplied capabilities explicitly.

Generate physical byte-identical copies at `.claude/skills/<name>/`, matching the
existing JV route convention. Delete the five old nested skill directories from
the source template so they cannot remain competing discoveries. Remove bare
`commands/scope.md` and `commands/check.md`; bare names resolve directly to the
projected skill. Keep existing work/capture namespaced commands as deterministic
thin pointers to canonical procedures; add pointers for the four additional work
modes. Their descriptions and target paths are generated from a fixed mapping;
they carry no independent procedure steps. Other commands stay untouched.

Extend `scripts/generate-skill-surfaces.py` with the fixed six-name, flat-file
mapping, preserving the exact upstream fixture validation. Source roots require
the complete set. An older generated/probe project with none of the six routes
is out of scope; if any canonical or Claude workflow route exists (including a
dangling symlink), require the complete six-skill set and its aliases. This avoids
breaking the separate three-skill receipt while refusing half-present migration.
Missing, extra, symlinked or executable canonical files fail before writes.
`--check` never mutates. Regeneration owns only these named projection directories
and command files; refuse static symlink ancestors rather than follow them.
Do not remove an unknown/user-owned directory to make a check pass.

The independent route checker validates this fixed inventory, frontmatter,
physical-copy equality, canonical/Claude discovery cardinality at all depths,
namespaced pointer targets and absence of conflicting bare commands. It must not
call the generator to decide its own expected result. The matrix additionally
recognizes an existing direct skill route for a bare token; a namespace directory
alone retains its existing behavior but cannot satisfy the six-skill checker.

### Procedure behavior and policy boundaries

`scope` produces Intent, I#, Non-goals and finite scenario/test requirements;
ground claims in source, and route uncertainty according to DELIVERY. Audits are
commissioned under the existing policy before implementation. `go` resumes only
an authorized next action and loads the relevant available project guidance.
`check` records actual RED/GREEN/review evidence and limits; it does not interpret
successful generation, a checklist or prose tier as completed runtime proof.

`capture` records evidence, duplicate checks, disposition and destination; when
remote capture is unavailable, keep a truthful durable local record and report
the recording boundary. Source labels are examples, not defaults applied to a
foreign repository. Business choices go to the owner; technical/process choices
use the director/standing authority. Honor existing authorization rather than
adding a new confirmation ceremony.

`team-lead` is usable as a coordination procedure by a commissioned lead, not an
authorization to spawn. Its task record includes root/worktree, project identity,
bounded scope, ownership, accepted requirements, allowed effects, available tools,
review independence and return evidence. No default DB, target or model. Capability
absence requires a truthful unavailable result or the existing director route;
it never downgrades a required independent reviewer into author self-review.

`work` preserves project-owned state and the distinction between local completion,
PR-ready and integration. Only the assigned integrator integrates. Resume reconciles
current source, exact PR head, acceptance and mail before acting; ad-hoc sessions
consume no seat mail. Advance independent authorized work when appropriate, while
unmerged prerequisites and current holds remain binding. Emergency output labels
unverified facts and requires receiver reorientation; it does not stage unknown
changes. Sprint-detail expands accepted scenarios and requests disposition for
contract changes rather than fabricating execution or weakening assertions.

### Entry, compatibility and provenance

Update the template's entry transition pointer to canonical work, add the six-skill
index and `go` to Claude's command map, and update the workflow command-authoring
example that references the old path. Add `template/docs/WORKFLOW_SKILLS.md` for
route/mode mapping, explicit capability limits, upgrade instructions and dated
source dispositions. It is a manual, not another rule body. Add a CHANGES entry
for the project-owned AGENTS pointer; existing projects retain their AGENTS edits.

A real task-disabled Copier update from the base must remove clean old framework
routes, install new ones and preserve marked project-owned AGENTS/state bytes.
If the user changed an old framework skill/command, surface the normal update
conflict and require deliberate reconciliation; never force-delete that edit.
Document that an old project-owned AGENTS pointer requires the published entry
delta. No claim that Copier rewrites project-owned policy.

Retained instruction families receive a one-line why and dated source
revision/reference in the manual, with historical JA incidents labelled as
provenance only. Portability corrections are labelled as corrections made here,
not attributed to source enforcement. The operating six-skill tree and aliases
contain no JA identity, host paths, project refs, live labels or secret values.

## Invariants and finite proof

| ID | Invariant | Positive / refusal cells |
|---|---|---|
| I1 / X3,X5 | Exactly six canonical workflow routes, complete declared procedures, byte-identical Claude copies and unambiguous aliases. | T1+: two real Copier consumers have every named route/mode; T1−: missing procedure, duplicate nested discovery and stale alias each produce a named structural failure. |
| I2 / X3,X4 | Selected procedures route to current neutral policy; no retained competing convergence or provider-tier authority. | T2+: required policy references resolve and the instruction inventory retains grounding/trace/evidence obligations; T2−: broken policy pointer or reintroduced old convergence directive is detected. Independent review checks meaning beyond the bounded textual assertions. |
| I3 / X4,X5 | Planning/execution/capture/team/lifecycle procedures preserve the declared outcome and truthful evidence/authority boundaries. | T3+: a read-through fixture maps the six entry requests and all declared work/capture modes to the expected procedure and required instruction clauses; T3−: remove the integrator-only boundary or claim automatic capture from a signal and the selected instruction assertion fails. No model execution claimed. |
| I4 / X1,X2,X6 | Operating guidance uses only project-owned targets and installed capabilities, with source facts kept as labelled provenance. | T4+: independently named solo/cluster projects resolve neutral guidance and no source coupling; T4−: seed the source staging fallback or absolute host target as Markdown data and the bounded coupling scan refuses it. |
| I5 / X3,X5 | Check/regeneration/update are deterministic and preserve unrelated and project-owned files. | T5+: regenerate twice with identical bytes, check is read-only, real clean-base update preserves project-owned markers; T5−: drift fails check without repair, static symlink ancestor refuses before writes, and edited legacy framework content is preserved/conflicted. |
| I6 / X1,X4,X5,X6 | Evidence uses genuine Copier output, pins subject/source, distinguishes structural proof from behavior and never executes source procedures. | T6+: raw render/check/update streams, file hashes and dated disposition coverage are complete; T6−: an unknown/extra executable payload in a workflow directory is refused, and an unsafe source command example is scanned as data with zero effect calls. |

Tests use stdlib unittest and the existing pinned Copier 9.17.1, one local heavy
slot. A dedicated `scripts/ci/test-workflow-skills.py` and small runner retain
raw command/result streams and hashes for two synthetic consumers (solo + cluster,
different project names). No home/provider credentials in child environments.
Generated skill prose is read as UTF-8 only. Known unsafe seeds never become
executed program images. Capture caller-owned fixture sentinel hashes before/after
regeneration/update; use only scratch Git repositories for update/rollback proof.

Finite sensitivity set, fixed before RED:

| Witness | Trace | Deliberate fault | Required observation |
|---|---|---|---|
| M1 | T1/I1 | Omit `work/handoff.md` from the projection | Structural failure names the missing procedure. |
| M2 | T1/I1 | Restore nested `scope/SKILL.md` | Duplicate-discovery failure. |
| M3 | T1/I1 | Point a work alias at a wrong/missing mode | Pointer failure. |
| M4 | T2/I2 | Drop the review-policy reference | Instruction/reference assertion failure. |
| M5 | T2/I2 | Reintroduce the old mandatory minimum-round instruction | Known superseded-directive assertion failure. |
| M6 | T3/I3 | Remove the integrator-only completion boundary | Required-clause assertion failure. |
| M7 | T3/I3 | Reintroduce the automatic issue-creation claim | Known false-enforcement assertion failure. |
| M8 | T4/I4 | Add source staging fallback in a code fence | Coupling refusal, no command executed. |
| M9 | T5/I5 | Drop the projection byte-comparison branch | Drift-control assertion fails despite the mutated check's zero exit. |
| M10 | T5/I5 | Omit one workflow pair from regeneration | Repair/idempotence assertion fails. |
| M11 | T6/I6 | Add an executable workflow payload | Inventory/type refusal before any payload execution. |

M1–M8/M11 are data mutations proving checker/assertion sensitivity. M9–M10 are
reviewed narrow generator-code mutations; retain their changed bytes and exact
selected test results. Do not count setup errors as kills or structural failures
as live agent behavior. Add a cell only for a surviving admitted witness or traced
review finding, per the current review policy.

## Gates and requested audit decision

This commit is SPEC-only. o commissions the SPEC/test-list audit; at most two
rounds before a scope decision. After admission, commit tests first and obtain
actual RED (missing routes/clauses, no setup errors), then the tests-only RED review
unless o explicitly waives that separate gate. Implement the admitted surface,
run the same generated suite, all finite witnesses and the four-answer matrix,
then request one full exact-head review through o. Publication only after o's
acceptance; i integrates after current-head hosted CI is green and JA lane idle.

The audit is also asked to admit these **oracle migrations**, not assertion
weakening: `test-skill-multiskill.py`'s existing entry test changes its work path
from the removed nested directory to the canonical one; its bare scope/check
command check accepts the actual direct skill route while namespaced modes still
require real pointer files. Other existing assertions and upstream pins stay
unchanged. The old tests' literal legacy paths cannot remain true after I1.

Proposed changed surface: six canonical directories; their generated copies;
removal of five old nested directories; selected command pointers; entry/Claude
map and one command-authoring example; generator/checker, matrix route resolution,
the two named legacy assertions, new suite/runner and CI/artifact wiring;
WORKFLOW_SKILLS manual, CHANGES, this SPEC and the review ledger. No hook/launcher,
provider receipt schema or other skill refactor is included.

Evidence packet includes the source hash inventory and snapshots, destination
consumer inventory, scope/diff, context card, raw proof, witness classification
and limitations. Seal once with the installed evidence helper and independently
verify SHA256SUMS. An accepted previous packet is never rewritten.

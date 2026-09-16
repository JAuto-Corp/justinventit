# Adoption and upgrade path (JV → project)

Status: proposed convention (2026-09-14, W/JV-O; revised after one fresh Opus review, its confirmation pass and one
JAuto-side Codex review). Versioned, provider-neutral, opt-in. It adds no service, store, hook or per-turn form. A
project adopts a JV change the way it adopts any change: a reviewed commit on its integration branch. No release, tag
or `CHANGES.md` exists yet; the first release creates them in this shape.

## Unit: a JV release tag

A release is a git tag `jv-vX.Y.Z` on `main`. Each release lists its changes in `CHANGES.md` (created with the first
release), one entry per change:

| Field | Meaning |
|-|-|
| `id` | stable slug, e.g. `evidence-delta` |
| `kind` | doc · skill · script · hook · policy · config |
| `tier` | R0–R3 exposure from `template/docs/DELIVERY.md` (hook and policy entries are at least R2) |
| `requires` | files, sections or commands the project must already have |
| `rollback` | `git revert <adoption commit>` (add `-m 1` when that commit is a merge) unless the entry says otherwise |

## Delivery: an overlay pull request to the project

The JV lead (or a JV seat) opens one PR against the project's integration branch containing only the overlay files
for the release ids the project opted into. The project's own CI is the compatibility check; no JV-specific checker
is added to the project. The project's integrator merges at a natural boundary; JV never blocks project delivery.

Exclusion by name collision is mechanical: any JV path that already exists in the project is left out of the overlay
unless the project explicitly asks for a replacement. A release may OFFER a hook or policy file; enabling it is the
project's own gate decision. Known JV-internal inconsistencies (generated four-step contract vs the documented 0–8
loop; check `06-harness-sensitivity` specified but not shipped; Claude-only generated entry) are JV roadmap items and
are never exported to a project through an overlay.

`copier update` is an adoption path for projects generated from a git-tracked template source (a URL such as
`gh:JAuto-Corp/justinventit` or a stable local clone path): the answers file records the resolved template commit,
the source and every answer, so `copier update --vcs-ref jv-vX.Y.Z` performs Copier's three-way merge, keeps
project-owned files (`_skip_if_exists`) untouched and advances `_commit`. Projects not generated from the template
use the PR path above; converting them is not required.

## Record: committed, not a PR description

The adoption record is the adoption commit on the project's integration branch (merge or squash, whatever the
project uses). Its message carries git trailers:

```
JV-Source: jv-vX.Y.Z/<jv commit sha>
JV-Accepted: <id>, <id>
JV-Declined: <id>
```

`git log --grep '^JV-Source:'` on the integration branch answers "which JV releases does this project run" and
which ids were declined. One line in the project's existing capture channel names the tag. Nothing else is written;
a PR description is context, not the record.

## Delivery alternative: a version-pinned shared install outside the project

When a released tool is seat-side tooling that the project's pipeline would classify as product code (its
executable-class rule, its push-triggered suite and deploys), the overlay PR is the wrong shape. The sanctioned
alternative is a shared install the JV lead prepares OUTSIDE every repository: `releases/<tag>/scripts/<tool>` copied
byte-for-byte from the tag (mode 0555), an `INSTALL-MANIFEST.md` in that directory naming the tag, commit, per-file
sha256, preparation time and the rollback, and ONE stable discovery pointer (`current` → the release directory). The
project's orchestrator accepts by verifying hash parity against the tag and running one real invocation on a real
packet; its acceptance record IS the adoption record, appended to the manifest with the same fields the overlay
trailers carry — `JV-Source: <tag>/<commit>`, `JV-Accepted: <ids>`, and `JV-Declined: <ids>` when applicable — so the
manifest answers the same question `git log --grep` answers for committed adoptions (that grep covers committed
adoptions only; a shared install is discoverable through its manifest, never through the project's history). Shared
tooling lives outside the project's repository and therefore outside its CI by construction: hash parity plus the
orchestrator's real invocation is the whole acceptance, and it waives no project gate — the project's own checks
still govern everything the tool's output is later used for. Rollback is removing or repointing
the pointer; nothing else exists — no PATH change, hook, daemon, store, package manager, CI or product effect. A new
release is a new directory plus an explicit re-acceptance; the pointer alone is never trust. Field origin: JA adopted
`evidence-seal` and `evidence-delta` this way on 2026-09-16 (`~/.jauto-orchestration/jv/current/scripts/`), after the
overlay path had been declined for exactly the reasons above.

## Canary and rollback (overlay PRs)

Canary: one unpublished commit in one isolated project worktree (from the project's then-current integration branch),
containing only the release's files with the trailers above; one seat exercises them once (for a script, one real run
of its tests and one real invocation; for a doc or skill, one bounded item worked while reading it). Pass: the item
completes with no `[FRICTION:*]` signal, workaround or bypass attributable to the overlay; fail: any of those. The
project's orchestrator decides from that evidence; a failed canary declines the id for this release and the worktree
is deleted. Rollback after integration is `git revert <adoption commit>` (`-m 1` for a merge) by the integrator, with
one capture line. No state outside git is touched, and no orchestration-root or shared evidence tree is ever
initialized as a repository by a release.
"Docs-only is inert" is a per-project fact, never an assumption: before offering an overlay as effect-free, check the
project's push-triggered jobs (a staging push may run migration or deploy workflows regardless of paths) and any
composer- or forge-owned regions in the target file (JA field result, 2026-09-16).

## Boundaries

JV release readiness is `scripts/ci/generate-matrix-check.sh` passing on the JV repo; it renders `template/` only, so
JV-repo documents such as this file are reviewed, not rendered. A project is field evidence, never a prerequisite.
Runtime evidence (test-run ledgers, logs) stays where `docs/TDD_GATE.md` §3 puts it; `template/scripts/evidence-delta.py`
reports committed input changes only. Provider, model and runtime are provenance, not part of the release contract.
Roles follow `template/docs/DELIVERY.md` (project-qualified identities, `JV-O`/`JA-O`) and `docs/SEAT_PROTOCOL.md` §3
Launch and resume (project-qualified profiles, the Tier row); the only addition here is that a single-seat JV lane
integrates its own reviewed PRs (solo tier, `docs/DEV_LOOP.md`).

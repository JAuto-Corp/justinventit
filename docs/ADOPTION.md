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

## Canary and rollback

Canary: one unpublished commit in one isolated project worktree (from the project's then-current integration branch),
containing only the release's files with the trailers above; one seat exercises them once (for a script, one real run
of its tests and one real invocation; for a doc or skill, one bounded item worked while reading it). Pass: the item
completes with no `[FRICTION:*]` signal, workaround or bypass attributable to the overlay; fail: any of those. The
project's orchestrator decides from that evidence; a failed canary declines the id for this release and the worktree
is deleted. Rollback after integration is `git revert <adoption commit>` (`-m 1` for a merge) by the integrator, with
one capture line. No state outside git is touched, and no orchestration-root or shared evidence tree is ever
initialized as a repository by a release.

## Boundaries

JV release readiness is `scripts/ci/generate-matrix-check.sh` passing on the JV repo; it renders `template/` only, so
JV-repo documents such as this file are reviewed, not rendered. A project is field evidence, never a prerequisite.
Runtime evidence (test-run ledgers, logs) stays where `docs/TDD_GATE.md` §3 puts it; `template/scripts/evidence-delta.py`
reports committed input changes only. Provider, model and runtime are provenance, not part of the release contract.
Roles follow `template/docs/DELIVERY.md` (project-qualified identities, `JV-O`/`JA-O`) and `docs/SEAT_PROTOCOL.md` §3
Launch and resume (project-qualified profiles, the Tier row); the only addition here is that a single-seat JV lane
integrates its own reviewed PRs (solo tier, `docs/DEV_LOOP.md`).

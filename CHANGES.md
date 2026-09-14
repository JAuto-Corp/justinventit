# Changes

Release entries follow `docs/ADOPTION.md`: one row per change id; `tier` is the exposure tier from
`template/docs/DELIVERY.md`; `requires` names what a consuming project must already have; rollback is
`git revert <adoption commit>` (`-m 1` when that commit is a merge) unless stated otherwise.

## Unreleased

| id | kind | tier | files | requires | notes |
|-|-|-|-|-|-|
| `loop-parity` | policy | R2 | `template/AGENTS.md.jinja`, `template/CLAUDE.md.jinja`, `docs/DEV_LOOP.md` | an entry contract the project owns | the generated contract carries DEV_LOOP's stages 0–8 (review carries the complete gate; document = doc delta or explicit `no-doc-impact`; capture) instead of a 4-step gate; parity test guards re-divergence; no stage-0 full-pass ceremony added (premise checklist by default) |
| `answers-persistence` | config | R1 | `template/.copier-answers.yml.jinja`, `copier.yml` | a project generated from a git-tracked template source | canonical `_copier_answers` file (resolved `_commit`, original `_src_path`, all answers); answers file no longer `_skip_if_exists`, so `copier update` works and advances `_commit` |
| `entry-contract` | policy | R2 | `template/AGENTS.md.jinja`, `template/CLAUDE.md.jinja` | none for greenfield; brownfield merges its AGENTS.md manually | AGENTS.md becomes the canonical provider-neutral contract, seeded once and project-owned (`_skip_if_exists`, never prompted); CLAUDE.md = `@AGENTS.md` + Claude extras (framework-managed); later contract changes ship as rows here for projects to merge |

## jv-v0.1.0 — 2026-09-14

First versioned release. Base: `main` after PR #36 (2dcc610) and PR #37.

| id | kind | tier | files | requires | notes |
|-|-|-|-|-|-|
| `adoption-path` | doc | R0 | `docs/ADOPTION.md` | — | JV-repo document, not an overlay file |
| `delivery-manual` | doc | R2 | `template/docs/DELIVERY.md` | an entry contract to point from; retire any competing delivery-discipline doc | offered, never enacts a gate |
| `evidence-delta` | script | R1 | `template/scripts/evidence-delta.py`, `template/scripts/test_evidence_delta.py` | python3 ≥ 3.9, git | optional committed-input report; grants nothing |
| `ponytail` | skill | R1 | `template/.agents/skills/ponytail/**`, `template/.claude/skills/ponytail/**` | project skill routes `.agents/skills/` and `.claude/skills/` | upstream DietrichGebert/ponytail 4.9.0 @ 356918e, MIT, core `SKILL.md` only |
| `caveman` | skill | R1 | `template/.agents/skills/caveman/**`, `template/.claude/skills/caveman/**` | same | upstream JuliusBrussee/caveman @ 15581d1 `skills/caveman`, MIT, core only |
| `skill-modes` | policy | R2 | `template/docs/SKILL_MODES.md` plus a read-and-apply line in the project's entry contract | an entry contract the project owns | brownfield projects add the line themselves |
| `agents-pointer` | doc | R0 | `template/AGENTS.md.jinja` | none | seeded only when `AGENTS.md` is absent (`_skip_if_exists`) |
| `multi-skill-checks` | script | JV-internal | `scripts/generate-skill-surfaces.py`, `scripts/ci/check-skill-routes.py`, `scripts/ci/skill_inventory.py`, `scripts/ci/test-skill-multiskill.py`, matrix/receipt changes | — | template CI only; never overlaid |

Known limits disclosed with this release: the runtime availability receipt measures `frontend-design` only and
requires CI's exact CLI versions; the generated entry contract was Claude-first in this release (superseded by
`entry-contract` above).

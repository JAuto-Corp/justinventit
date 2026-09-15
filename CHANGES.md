# Changes

Release entries follow `docs/ADOPTION.md`: one row per change id; `tier` is the exposure tier from
`template/docs/DELIVERY.md`; `requires` names what a consuming project must already have; rollback is
`git revert <adoption commit>` (`-m 1` when that commit is a merge) unless stated otherwise.

## Unreleased

Bump rule: any change to the generated entry contract's stages, gates or routing bumps `jv-entry-contract` in
`template/AGENTS.md.jinja` and `jv-entry-contract-expected` in `template/CLAUDE.md.jinja` together and adds an
`entry-contract` row here; the generated session-start hook warns (never blocks) when a project's AGENTS.md lags.

| id | kind | tier | files | requires | notes |
|-|-|-|-|-|-|
| `scope-classify` | script | R1 | `template/scripts/scope-classify.py`, `template/scripts/test_scope_classify.py`, `template/scripts/scope-classes.json.jinja` (rendered `scripts/scope-classes.json`, project-owned via `_skip_if_exists`) | python3 ≥ 3.9; git for range mode (`--paths-from` needs none) | the scope-classifier ENGINE: prints `class=<Quick|Quick(tooling)|Standard+> reason=<trace>` from a git range or a path list and the authored config; implements TDD_GATE §2 rules 1–4 mechanically (triggers, count, executable class, denylist, inventory, consumer grep, product imports, test-in-change or `--red-recorded`); ships INERT — `tooling.inventory: []` — so `Quick(tooling)` cannot fire until a project authors pairs; known v1 limit: `git grep -I` skips binary-attributed files (ROADMAP follow-up); no gate wired yet |
| `route-line` | policy | R2 | `docs/MODEL_MATRIX.md` §3c | a review receipt, PR body or acceptance record to carry it | at most one `route:` line per sampled boundary as the only instrument of evidence-calibrated model routing; hypothesis stated, no rule change, no store/scheduler/form |
| `provider-bookend` | policy | R2 | `docs/ARCHITECTURE.md` §2, `template/docs/DELIVERY.md`, `docs/MODEL_MATRIX.md` (cross_review note) | two configured runtimes; a delivery manual the project owns | at R2/R3 boundaries each runtime's thinking-tier model touches the subject once across authoring/challenge/acceptance (roles count, duplicate reviews don't); elsewhere author + independent reviewer from different runtimes suffices; trivial owes none; unavailability → proceed and record `bookend: <runtime> missing`; no further round unless the head or contract changed or a named blocker remains |
| `scope-class-tooling` | policy | R2 | `docs/TDD_GATE.md` §2 Scope classes + §4/§5 pointers, `template/AGENTS.md.jinja` (scope row + routing row) | an entry contract the project owns; a scope classifier with an authored config | declared `tooling` sub-case of Quick for seat tooling: inventory of helper+test pairs, denylist-first, no hook/CI consumer, test changed or RED observed, PR declaration + reviewer attestation; keeps Quick exemptions + one exact-head review; owes no substrate/scenarios/build/deploy; delete the sub-case to fall back (JA FIELD-LESSON-01) |
| `entry-contract` | policy | R2 | `template/AGENTS.md.jinja`, `template/CLAUDE.md.jinja`, `template/docs/PLAYBOOK.md.jinja`, `template/.claude/skills/orchestrators/{work/SKILL.md,work/start.md,scope/SKILL.md,verify/complete.md}` (summaries now defer to AGENTS.md § Scope classification) | a project generated at contract version 1 | contract version 1 → 2: one scope row and one routing row for `Quick (tooling)`; the session-start hook warns (never blocks) projects whose AGENTS.md still says 1 |
| `seal-report-placement` | script | R1 | `template/scripts/evidence-seal.py` (docstring only) | existing `scripts/evidence-seal.py` | states where a report that cites `manifest_sha256` must live (beside the packet or under a declared `.sealignore` path) — JA CANARY-03 field practice |
| `test-locator` | script | R1 | `template/scripts/test_evidence_delta.py`, `template/scripts/test_evidence_seal.py` | `evidence-delta.py` / `evidence-seal.py` beside the tests or one directory up | tests resolve their CLI beside themselves or one directory up, so a project's `scripts/tests/` placement needs no local edit (JA CANARY-01 field result: the only delta was this line) |
| `correction-review` | policy | R2 | `docs/DEV_LOOP.md`, `docs/ARCHITECTURE.md`, `template/docs/DELIVERY.md` | an entry contract or delivery manual the project owns | cardinality binds the initial audit; each correction owes one focused exact-head confirmation; a full round only on scope/guarantee change; two failures at a gate still route to the diagnosis/harness challenge, never an automatic round |

## jv-v0.2.0 — 2026-09-15

Base: `main` at 2b5ba48 after PR #45 (PRs #38–#45, each merged at an independently reviewed exact head).

| id | kind | tier | files | requires | notes |
|-|-|-|-|-|-|
| `entry-contract` | policy | R2 | `template/AGENTS.md.jinja`, `template/CLAUDE.md.jinja`, `template/docs/PLAYBOOK.md.jinja`, `template/docs/SKILL_MODES.md` (pointers retargeted to AGENTS.md) | none for greenfield; brownfield merges its AGENTS.md manually | AGENTS.md becomes the canonical provider-neutral contract, seeded once and project-owned (`_skip_if_exists`, never prompted); CLAUDE.md = `@AGENTS.md` + Claude extras (framework-managed); later contract changes ship as rows here for projects to merge |
| `answers-persistence` | config | R1 | `template/.copier-answers.yml.jinja`, `copier.yml` | a project generated from a git-tracked template source | canonical `_copier_answers` file (resolved `_commit`, original `_src_path`, all answers); answers file no longer `_skip_if_exists`, so `copier update` works and advances `_commit` |
| `loop-parity` | policy | R2 | `template/AGENTS.md.jinja`, `template/CLAUDE.md.jinja`, `docs/DEV_LOOP.md` | an entry contract the project owns | the generated contract carries DEV_LOOP's stages 0–8 (review carries the complete gate; document = doc delta or explicit `no-doc-impact`; capture) instead of a 4-step gate; parity test guards re-divergence; no stage-0 full-pass ceremony added (premise checklist by default) |
| `contract-version` | hook | R2 | `template/.claude/hooks/lib/contract-version.sh`, `session-start.sh.jinja`, entry markers | generated hooks | one non-blocking warning line when AGENTS.md's `jv-entry-contract` differs from CLAUDE.md's expected version; matrix check asserts the rendered pair agrees |
| `receipt-multiskill` | script | JV-internal | `scripts/ci/runtime-skill-receipt.sh`, receipt schema/validator, `scripts/ci/test-runtime-receipt-multiskill.py` | — | CI availability receipt covers every pinned skill (additive `additional_skills`); never overlaid |
| `check06-status` | doc | R0 | `docs/TDD_GATE.md`, `docs/ROADMAP.md` | — | check `06-harness-sensitivity` marked specified-not-built with its build order; no gate or ruling changed |
| `evidence-seal` | script | R1 | `template/scripts/evidence-seal.py`, `template/scripts/test_evidence_seal.py` | python3 ≥ 3.9 (git optional) | regenerate-only `SHA256SUMS` seal/verify for evidence packets; exact coreutils format; `--reseal` prints the entry delta; verify exits 0 pass / 1 changed-or-missing / 3 unlisted / 2 cannot-evaluate; declared exclusions via `.sealignore` (always sealed itself); undeclared symlinks, `.git`, empty packets, unsealable names and the filesystem root are refused; optional, grants nothing |

Corrections at release time: `contract-version` was merged as tier R1 and is listed here as R2 — `docs/ADOPTION.md`
requires hook entries to be at least R2; `entry-contract` now names the two generated docs whose pointers it retargeted.

Known limits disclosed with this release: check `06-harness-sensitivity` remains specified, not built (the Stop runner
runs `01-05`; see `docs/TDD_GATE.md` §3); the runtime availability receipt still requires CI's exact CLI versions;
`evidence-seal` reports a repository HEAD only via `git rev-parse` and never inspects worktree state.

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

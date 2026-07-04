# M1 Dogfood Exit Gate — generate vs. customer-portal

**Authored:** 2026-07-04 (role P) · **Tranche-2 item-9 (M1 completion test)** · **Class:** framework validation
**Method summary:** first-ever *actual* generation of the template (all prior dogfood work was read-only inspection — no build). Generated a scaffold with a customer-portal-matching answer set, verified coherence, diffed against the reference `.claude/`, backported the critical framework-level residuals found, and ran an end-to-end ATDD gate smoke in the generated project.

> **This is a validation report, not a rubber stamp.** Generation initially **failed** and the stop pipeline was **broken on every run** — both root-caused to real framework bugs that only an actual build could surface. Both are fixed in this PR. See §2 and §5.

---

## 1. Generation method

- **Tool:** Copier `9.16.0`, installed into a throwaway venv (`/tmp/copier-venv`) because the host Python is externally-managed (`pip --user` and system installs are blocked; `--break-system-packages` avoided). No global mutation.
- **Command:** `copier copy --defaults --data-file /tmp/dogfood-answers.yml --vcs-ref HEAD <repo> /tmp/dogfood-out`
- **Answer set (customer-portal match):** `project_type=brownfield, stack=nextjs, language=typescript, database=supabase, db_adapter=supabase, testing=playwright, unit_testing=jest, use_tds=true, orchestration_tier=cluster, team_size=3, external_pacemaker=tmux-supervisor, isolation_tier=schema, max_parallel_streams=3, type_check_command="pnpm type-check", build_command="pnpm build:web", main_branch=main, staging_branch=staging`
- **Output:** `/tmp/dogfood-out` — 110 files. **Never committed** (constraint honored).
- **No Jinja fallback needed** — Copier ran cleanly *after* the blocking bug in §2 was fixed.

## 2. BLOCKER found immediately — `copier.yml` dict-choice inversion (P0, fixed)

The first `copier copy` **errored out**:

```
ValueError: Invalid choice for 'project_type': 'brownfield' is not in
['Greenfield — new project...', 'Brownfield — existing codebase...', 'Framework — ...']
```

**Root cause.** Copier dict-choice semantics are `{label: value}` — the KEY is the human label shown to the user, the VALUE (right-hand side) is what gets **stored** and what the template compares against. Every choice question in `copier.yml` had them **inverted** (`greenfield: "Greenfield — ..."`), so Copier stored the long description strings as the answer, and every `== 'shortkey'` comparison in the template silently evaluated **false**.

Confirmed empirically with a minimal 2-file Copier template (`{shortkey: "label"}` stores `"label"`; `{"label": shortkey}` stores `shortkey`).

**Blast radius (5 dict questions):** `project_type`, `db_adapter`, `orchestration_tier`, `external_pacemaker`, `isolation_tier`. The list-choice questions (`stack/language/database/testing/unit_testing`) were unaffected. The most damaging: **`orchestration_tier == 'cluster'`** gates the heartbeat-writer action, PACEMAKER content, and session-start cluster branch — so a project that chose `cluster` would have had all its L2 machinery **silently stripped**. `db_adapter == 'supabase'` (settings.json migration matcher) was masked only by the `database == 'supabase'` list-fallback.

**Fix (backported, `copier.yml`):** inverted all 5 dict blocks to the correct `"Long label": short_value` form + a comment documenting the semantics. Post-fix, the `cluster` branch renders the full 87-line heartbeat producer (not the "Gated OFF" stub) and the settings.json migration matcher resolves to the Supabase MCP tools — both confirmed.

## 3. Coherence results (regenerated project, post-fixes)

| check | result |
|-|-|
| (a) no unrendered `{{ }}`/`{% %}` | **PASS** — 0 Jinja constructs; 0 `.jinja` files leaked. (Remaining brace hits are legit: nested shell `${..}}`, the harness's own `{{SANDBOX}}` runtime token, pacemaker's `{role}` placeholder.) |
| (b) `.claude/settings.json` valid JSON | **PASS** — valid; migration matcher = `mcp__supabase__execute_sql\|mcp__supabase__apply_migration` (proves `db_adapter=='supabase'` now works) |
| (c) stop runner + checks 01-05 + guards + actions present & `bash -n` clean | **PASS** — 30 shell scripts, 0 syntax failures; write-isolation + migration-safety guards, checks 01-05, 4 actions all present |
| (d) command-wrapper "SKILL.md §" pointers resolve | **PASS** — all 21 pointers resolve to real headings in the generated skills |
| (e) hook harness green **in generated project** | **PASS (after fix §5a)** — `run-all.sh` exit 0, 7/7 suites |

The prior inventory's **P0 "dead slash-command" gap is closed**: all 21 `/ns:cmd` references in the generated `CLAUDE.md`/skills have a backing command file (0 dangling). No dangling references to the not-yet-ported skills either (chain/scope/check appear only as prose or the `orchestrators/` dir path).

## 4. Diff vs. customer-portal `.claude/` — portable-gap vs. domain

customer-portal (READ-ONLY) has 22 skill dirs, 18 hooks, 2 agents, 6 command dirs; the scaffold generates 7 skills, the guard+stop hook set, 0 agents, 5 command dirs. Ranked classification of what cp has that the scaffold lacks:

| rank | cp asset (missing) | class | disposition |
|-|-|-|-|
| — | `orchestration_tier`/`db_adapter` gating (dict-choice) | **PORTABLE (new)** | **BACKPORTED** — §2 |
| — | stop pipeline exec-bit / `.jinja` mode | **PORTABLE (new)** | **BACKPORTED** — §5 |
| P1 | skills `chain` / `scope` / `check` (plan→converge→verify) | PORTABLE | **DEFER** — documented M1-partial in DOGFOOD_GAP_INVENTORY §2; not coherence-breaking |
| P2 | skills `intake` / `integrate` / `orchestrator` | PORTABLE | **DEFER** — M2 (orchestrator needs Supabase-table impl abstracted) |
| P2 | hooks `post-tool-use` / `subagent-stop` / `pre-bash-commit-reminder` / `post-agent-validate` (nudges/monitors) | PORTABLE-low | **DEFER** — M2; not in M1 scope |
| P2 | `lib/generate-scope.sh` | PORTABLE | **DEFER** — pairs with the `scope` skill |
| — | skills `action-catalog`, `backend-api-patterns`, `backend-debugging`, `code-navigation`, `frontend-aesthetics`, `go`, `schema-relationships`, `tds`, `tds-patterns` | DOMAIN | correctly excluded (user-filled `domain/`) |
| — | hooks `lib/notify-sms`, `pre-lsp`, `post-bash-ci-monitor`, `post-bash-issue-comments`, `post-migration` | DOMAIN | correctly excluded (cp SMS/LSP/CI/GH/type-regen) |
| — | `agents/e2e-validator`, `agents/tds-author` | DOMAIN | correctly excluded (domain reference guides) |
| — | `commands/tm/*`, `chain-config.json`, `HOOK_ENHANCEMENTS.md`, `TM_COMMANDS_GUIDE.md`, `database-migration-checklist.md`, `archive/`, `logs/`, `shared/`, `worktrees/`, `settings.local.json`, `scheduled_tasks.lock` | DOMAIN/runtime | correctly excluded (Task-Master, runtime/user-local artifacts) |

**Net:** every remaining PORTABLE gap is an already-documented, dependency-ordered M1-partial/M2 deferral from `DOGFOOD_GAP_INVENTORY.md` — none is a *new* residual and none breaks coherence. The two genuinely new residuals (§2, §5) were both invisible to read-only inspection and are both fixed here.

## 5. Backports made (this PR)

**a. `test-migration-safety.sh` — harness was RED in every generated project (P0).**
The suite rendered the guard's `.jinja` *source* at test time. That source exists only in the template repo; in a generated project the guard already ships rendered as `guards/migration-safety.sh` (no `.jinja`), so the test `FileNotFound`-ed and reddened the whole harness (exit 1). Fix: resolve the guard as it actually ships — prefer the rendered `.sh`, fall back to rendering the `.jinja` (template-repo self-test), and skip cleanly if the guard isn't the supabase variant (postgres/none projects stay green). Green in both contexts now.

**b. Stop pipeline broken on every run — non-executable `.jinja`-rendered check (P0).**
`02-type-check-evidence.sh.jinja` was git-tracked as mode `100644` while every sibling check is `100755`. Copier faithfully preserves the source mode, so the rendered check came out non-executable; the runner execs checks **directly**, so every Stop-hook invocation died with `Permission denied` and blocked the session. (The harness missed it — it invokes tests via `bash`, and check 02 isn't in the suite; only the real runner exposed it.) Two-part fix: (1) hardened `runner.sh` to invoke checks/actions via `bash "$script"` — matches the settings.json convention (`bash .claude/hooks/...`) and makes the pipeline immune to exec-bit drift; (2) set the source file mode to `100755` for consistency.

**Deferred (not built here):** the full `chain/scope/check/intake/integrate/orchestrator` skill ports and the P2 nudge hooks — larger, dependency-ordered, already tracked in `DOGFOOD_GAP_INVENTORY.md`.

## 6. ATDD gate smoke (end-to-end, in the generated project)

Seeded a real phase: `docs/phases/phase-1/{SCENARIOS.md,PROGRESS.md}`, a `CURRENT_WORK.md` pointer, and drove the full `stop/runner.sh` pipeline with/without a `[PHASE_COMPLETE]` transcript signal.

| case | signal | phase state | result |
|-|-|-|-|
| A | none | incomplete | **exit 0** — gate no-ops (correct: no completion claimed) |
| B | `[PHASE_COMPLETE]` | unchecked PROGRESS item + no run evidence | **exit 2** — check 03 (scenario evidence), 04 (RED-phase), **05 (unchecked item)** all BLOCK |
| C | `[PHASE_COMPLETE]` | all items checked + passing run + red-before-green evidence | **exit 0** — all checks PASS |

Block-then-pass demonstrated for checks 03 and 05 (bonus: 04). The gate resolves the phase via the real `CURRENT_WORK.md → phase dir` chain and enforces evidence end-to-end. Harness: 7/7 suites, exit 0.

## 7. VERDICT — **M1 dogfood-ready (with fixes landed in this PR)**

The framework generates a **coherent, self-consistent, enforcement-live** project matching the customer-portal answer set: no unrendered tokens, valid settings, all command pointers resolve, the hook harness is green in the generated project, and the ATDD stop-gate blocks-then-passes end-to-end. The two blocking defects the gate surfaced — the `copier.yml` dict-choice inversion (generation blocker + silent cluster-machinery loss) and the non-executable rendered check (pipeline dead on every run) — are **fixed in this PR** and re-verified. Both were invisible to the prior read-only inventory; catching them is precisely the value of this exit gate.

All remaining `.claude/` deltas vs. customer-portal are either **correctly-excluded domain content** or **already-tracked, dependency-ordered M1-partial/M2 skill/hook deferrals** — none is a new residual, none breaks coherence.

**Residual risk / judgment calls (for role-P M1 sign-off):**
- Verified for the **cp-matching answer set** (brownfield/nextjs/ts/supabase/cluster/schema). Other permutations (greenfield, postgres/none adapters, solo tier) are handled by the same Jinja gates and the variant-aware migration test skips, but were **not each generated end-to-end** — a lightweight matrix-generation smoke is a reasonable M2 follow-up.
- The dict-choice bug implies **no CI ever ran an actual `copier copy`.** Strongly recommend adding a generate-and-harness CI job so this class of build-time regression is caught automatically rather than by manual dogfood.
- Backport (b) changes the runner's child-invocation to `bash`; all checks/actions carry a `#!/bin/bash` shebang and are bash, so behavior is unchanged beyond exec-bit independence.

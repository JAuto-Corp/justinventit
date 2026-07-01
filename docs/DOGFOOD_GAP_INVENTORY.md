# justinventit — Dogfood Gap Inventory

**Authored:** 2026-07-01 (role P) · **For:** O → user (M1 sequencing input, U-27) · **Class:** read-only research, decision-input
**Method:** 3 read-only Explore passes comparing the reference implementation (`customer-portal/.claude/`) against current template output (`justinventit/template/.claude/`). No customer-portal writes; no template build.

> **Framing guard (per O, 07-01):** this inventory *feeds* the user's M1 sequencing decision — it does **not** pre-empt it. Nothing here is built until the user gives the sequencing nod. The "suggested sequencing" in §7 is a recommendation, not a commitment.

---

## 1. Executive summary

The template captures the *shape* of the reference `.claude/` (skill routing, stop-pipeline, forge markers) but ships the orchestrator skills as **stubs** and is **missing the enforcement hooks + the command-wiring layer**. Every M1 target has a concrete cp source to port — **nothing in M1 must be authored from scratch.** **One** *correctness* gap surfaced that is NOT in the current ROADMAP M1 list and is cheap to fix — the command-wiring layer (§6). *(A second candidate, a `memory/` seed, was retracted on verification — the template's `pre-compact.sh` does not read that file; see §4.)*

Scale of the gap: cp has ~24 skill areas (many domain-specific), 18 hooks, 2 agents, 83 command wrappers; the template generates 5 skill files, 9 hooks, 0 agents, 0 commands. But **~half of cp's skills are domain-specific and are deliberately NOT framework gaps** (§5) — the real portable gap is smaller and well-bounded.

**Unified port-value ranking (all categories):**

| rank | gap | category | ROADMAP M1? | source coupling |
|-|-|-|-|-|
| P0 | command-wiring layer (dead `/work:*` etc.) | commands | **NEW** (not listed) | trivial (thin wrappers) |
| P0 | write-isolation guard | hooks | yes | zero — direct port |
| P0 | `work` skill + 7 sub-skills | skills | yes | low |
| P0 | `verify` skill + 7 sub-skills | skills | yes | low |
| P0 | stop-checks 03/04/05 + landmark-checkoff | hooks | yes | low (Jinja path slots) |
| P0 | `workflow` skill (self-edit capability) | skills | yes | none — purest port |
| P1 | hook test harness (**prereq for the checks**) | hooks | yes | pattern-port |
| P1 | `capture` skill + 5 sub-skills | skills | yes | low |
| P1 | `e2e` skill | skills | yes | med (nav needs adaptation) |
| P1 | migration-safety guard | hooks | yes | Jinja `db_system` gate |
| P1 | `patterns` / `team-lead` spawn-templates / `scope` / `chain` / `check` | skills | partial | low-med |
| ~~P1~~ | ~~`memory/` seed file~~ **RETRACTED** on verification — template `pre-compact.sh` does not read `modified-files.json` (see §4) | memory | — | non-defect |
| P2 | `intake` / `integrate` / `orchestrator` skills | skills | no | med-high (orchestrator: abstract Supabase) |
| P2 | portable `code-reviewer` agent (conditional) | agents | no | low |

**Already merged:** M1 item-0 heartbeat-writer (pacemaker producer). **Already in template:** session-start, pre-compact, lib/utils hooks; the 5 orchestrator skill stubs.

---

## 2. Skills gaps

| skill | in-template | missing (cp source, approx lines) | port-value |
|-|-|-|-|
| work | stub (55L) | 7 M1 sub-skills + extras: start/continue/pause/handoff/done/epic-plan/sprint (+sprint-plan/detail/pr-ready/emergency/worktree) ~4106L | P0 |
| verify | stub (42L) | complete/phase/sprint/file/feature/audit/recent (+simplify/code-review-team/epic) ~2423L | P0 |
| workflow | empty | SKILL + command/docs/edit-skill/state/workflow-main — 6 files, fully portable | P0 |
| capture | stub (41L) | block/audit/findings/triage/epic ~1101L | P1 |
| e2e | empty | SKILL (689L) portable; `nav.md` (292L) is Playwright/TDS-specific → adapt | P1 |
| patterns | stub (60L) | discovery/explorer/interview/state-files ~563L (referenced by work/team-lead) | P1 |
| team-lead | stub (59L) | spawn-templates.md (601L) — agent-team coordination | P1 |
| scope / chain / check | none | 207L / 386L / 199L — the plan→converge→verify chain | P1 |
| intake / integrate / orchestrator | none | 214L / 432L / 670L — orchestrator has a Supabase-table impl to abstract | P2 |

All M1 skill targets have direct cp sources at depth. `work` drives every other skill's entry/exit; `verify` gates every phase; `workflow` is what lets the framework self-edit (without it, all future template evolution is manual).

---

## 3. Hooks gaps

| cp hook | enforces | M1 target | port-value |
|-|-|-|-|
| pre-tool-write-guard.sh | blocks Write/Edit outside worktree root | guard: write-isolation | P0 |
| stop.sh §0.9 + lib/evidence.sh | scenario-execution evidence gate | stop-check-03 | P0 |
| stop.sh §TDD + lib/evidence.sh | RED-before-GREEN cycle | stop-check-04 | P0 |
| stop.sh §0.5 + §2 | PROGRESS.md unchecked blocks; auto-check from commits | stop-check-05 + landmark-checkoff action | P0 |
| pre-tool-migration.sh | migration-safety (DDL/apply gating) | guard: migration-safety | P1 (Jinja db_system) |
| test-chain-nudge.sh | fixture→backup→run→assert pattern (149L) | hook test harness | P1 |
| lib/evidence.sh | shared check_scenarios_executed / check_tdd_cycle | 03/04 lib | P1 |
| subagent-stop / commit-reminder / agent-validate / ci-monitor / pre-lsp / issue-comments / post-tool-use | various nudges/monitors | not in M1 | P2 |

**Sequencing note:** the **hook test harness (P1) is a prerequisite** for safely building checks 03/04/05 (P0) — build the harness *first* so each check can be fixture-tested without a live session. The scenario/TDD logic in `lib/evidence.sh` is already generic bash; only the SCENARIOS.md/PROGRESS.md lookup paths need Jinja-injected conventions. The write-isolation guard is the single cheapest P0 (zero coupling, relies only on `CLAUDE_PROJECT_DIR`).

---

## 4. Agents / Commands / Rules / Memory

- **Commands — REAL GAP (P0, correctness).** `CLAUDE.md.jinja` tells the agent to invoke specific slash commands — verified: `/verify:complete` (L34) and `/work:handoff` / `/work:pause` / `/work:continue` (L93) — but the template generates **no `.claude/commands/` files**, so those 4 commands are *dead on arrival* in a generated project. cp's pattern is thin wrappers (~15-25L each: "read the X skill, execute Y"). **Defect fix (this PR):** generate 4 generic wrappers for exactly the invoked commands, pointing at the existing skills — no domain coupling, no skill content. (The *full* commands layer for every skill sub-command is the M1 build, not this defect. cp's `tm/` command dir = Task-Master domain, ignore.)
- **Memory — RETRACTED (verified 07-01, non-defect).** On direct read, the template's `pre-compact.sh` appends a compaction marker to `context/WORKING.md` (via `get_state_dir`) — it does **not** read `.claude/memory/modified-files.json`, and no template hook references it. The original finding conflated cp's `pre-compact.sh` (which does use that file) with the template's. No seed needed; no defect.
- **Agents — mostly NON-gap.** Both cp agents (`e2e-validator`, `tds-author`) are domain-specific reference guides, not portable. Empty `agents/` is largely correct. Only portable candidate: a generic `code-reviewer.md` (Sonnet, file tools) to support `team-lead` multi-agent review — LOW value, conditional on using that flow.
- **Rules — NON-gap.** Neither cp nor template uses path-scoped rules at the primary project level. Nothing to port.

---

## 5. Domain skills — deliberately NOT ported (non-gaps)

These are customer-portal-specific and belong in a generated project's `domain/` (user-filled), not the framework: `action-catalog`, `backend-api-patterns`, `backend-debugging`, `code-navigation` (LSP pattern *extractable* if wanted), `frontend-aesthetics`, `go`, `next-best-practices`, `python-performance-optimization`, `schema-relationships`, `supabase-postgres-best-practices`, `vercel-react-best-practices`, `tds` / `tds-patterns` (cp-specific; the TDS *contract shape* is the portable part, tracked separately in M1 state-templates).

Flagging this explicitly so the port scope is not overstated: the portable gap is the orchestrator/process layer, not cp's domain knowledge.

---

## 6. Newly-surfaced gaps NOT in ROADMAP M1

One cheap, high-leverage item the current M1 checklist does not list — recommend folding in:
1. **Command-wiring layer** (P0) — closes the dead-slash-command correctness gap. The 4 *invoked* commands are fixed as an M0 defect (see §4); the full commands layer for all skills remains an M1 build item.

*(A second item — a `memory/` seed — was listed here on first pass but **RETRACTED on verification**: the template's `pre-compact.sh` does not read that file. See §4.)*

---

## 7. Suggested M1 sequencing (recommendation — user decides)

A dependency-ordered cut, cheapest-correctness and prerequisites first. **Proposal only; awaiting the user sequencing nod (U-27).**

1. **Command-wiring** — the 4 invoked commands are already fixed as an M0 defect (this landed separately); the *full* commands layer (wrappers for every skill sub-command) sequences here. *(The memory-seed item is retracted — see §4.)*
2. **write-isolation guard** — single cheapest P0, zero coupling.
3. **hook test harness** — prerequisite for developing the enforcement checks safely.
4. **stop-checks 03/04/05 + landmark-checkoff** — the enforcement backbone (harness-tested).
5. **`work` + `verify` skills (M1 sub-skills)** — the lifecycle + gating engine; direct cp ports.
6. **`workflow` skill** — self-edit capability (compounds all later template evolution).
7. **`capture` + `e2e` skills** — round out the orchestrator set.
8. **migration-safety guard** (Jinja) + `patterns`/`team-lead`/`scope`/`chain`/`check`.
9. **Dogfood exit gate** — regenerate the scaffold for customer-portal's answers, diff, backport residuals, run one ATDD cycle (the M1 milestone completion test).

`intake` / `integrate` / `orchestrator` skills + the portable `code-reviewer` agent → defer to M2 (higher coupling; orchestrator needs the Supabase-table impl abstracted).

Health U-20 HOLD respected. No build proceeds until the sequencing nod.

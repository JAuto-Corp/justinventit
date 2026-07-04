---
name: e2e
description: "End-to-end / acceptance testing orchestration. Run the project's configured e2e suite against a phase's acceptance scenarios, pick an execution mode (suite / conductor / direct / data-layer), and capture the per-scenario passing evidence the ATDD gate and stop check 03 require."
---

# End-to-End Testing

Exercise the running system the way a user (or an upstream caller) would, and prove each of the phase's acceptance scenarios passes. This is the orchestration that produces the RED-then-GREEN, per-scenario evidence `checks/03-scenario-evidence` and `04-tdd-cycle` look for when a phase signals `[PHASE_COMPLETE]`. Unit tests prove the pieces; e2e proves the whole flow.

> Navigate fast, validate thoroughly. Reach the feature under test by the shortest reliable path, then scrutinise the new behaviour step by step. e2e is milestone-driven — run it at phase/sprint completion, not on every edit.

## The configured runner (never hardcode a framework)

Read the `testing` answer from `.copier-answers.yml` — it names the project's chosen E2E framework (or `none`). The concrete run command lives in `CLAUDE.md` § Essential Commands; always invoke e2e through that command and never assume a specific tool's API. If `testing: none`, there is no automated suite — verify scenarios manually and record completion with `[EVIDENCE_OVERRIDE:manual-testing]`.

---

## /e2e:run

Run the active phase's acceptance suite and capture pass/fail evidence per scenario.

1. **Load the scenarios.** Follow the state chain (`docs/CURRENT_WORK.md` → the active phase's `SCENARIOS.md`). Each `Scenario:` / `####` heading is one acceptance case (Given/When/Then).
2. **Pick a mode per scenario** (menu below) — the automated suite for gating evidence; conductor/direct/data-layer for scrutiny or no-UI flows.
3. **Run RED then GREEN.** Before the feature exists the scenario must fail for the right reason (missing impl, not a bad setup); after it exists it must pass. Both runs are the evidence `check/04` wants.
4. **Capture evidence per scenario.** The configured runner records `{scenario, status}` to the evidence JSON; interactive modes capture logs/screenshots that `/verify:complete` records. One passing run per scenario id, or the phase can't close.

## E2E modes (generic menu)

| Mode | What it is | When |
|-|-|-|
| suite | The configured runner, run headlessly across the scenarios; records machine evidence | Default — the phase-gating evidence path |
| conductor | Guided, step-by-step walk of new UI, capturing key states | New/changed UI that needs visual scrutiny |
| direct | Quick ad-hoc interactive check of one thing | Debugging, spot-checks (not gating evidence) |
| data-layer | No-UI validation: drive via API/CLI, assert via data queries | Engine / scheduler / background / pure-API scenarios |

Mode workflows: `modes.md`.

## Session coordination (portable caveat)

Interactive, stateful session tools (browser drivers, live app sessions) run from the **main session — not from spawned sub-agents.** This framework's Explore/verify sub-agents are read-only context-gatherers: they can't hold a live session or load skills. Drive conductor/direct/data-layer flows yourself; delegate only read-only investigation of results or logs.

## How e2e evidence feeds the gates

`SCENARIOS.md` is the ATDD contract (`CLAUDE.md` § TDD Gate: no code without scenarios). Each scenario id must have a recorded **passing** run before `[PHASE_COMPLETE]`:

| Gate | What it checks |
|-|-|
| TDD/ATDD gate (`checks/01`) | Standard+ scope has a `SCENARIOS.md` |
| `checks/04-tdd-cycle` | RED recorded before GREEN for each scenario |
| `checks/03-scenario-evidence` | Every `SCENARIOS.md` scenario has a passing run in the evidence JSON |

`/e2e:run` produces those runs; `/verify:complete` (the exit gate `/work:done` calls) reads and confirms them. A scenario with no passing run blocks the phase — fix it, or, for a legitimately manual/code-free case, signal `[EVIDENCE_OVERRIDE:manual-testing]` honestly.

## When to run

| Trigger | Scope |
|-|-|
| Phase complete | Every scenario in the phase `SCENARIOS.md` |
| Sprint complete | Full sweep of the sprint's features |
| Bug-fix verify | The affected flow(s) only |

Not on every code change — that's the job of unit tests and the TDD inner loop.

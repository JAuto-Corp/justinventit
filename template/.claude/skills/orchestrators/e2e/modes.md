---
name: e2e:modes
description: "Generic execution-mode playbooks for e2e scenarios — suite (automated), conductor (guided UI walk), direct (ad-hoc), and data-layer (no-UI). Tool-agnostic; drive every mode through the project's configured runner."
---

# E2E Modes

How to exercise one acceptance scenario. Pick per scenario: the automated **suite** is the default and the only mode that records gating evidence unattended — the others are for scrutiny, debugging, or no-UI flows and rely on `/verify:complete` to record their result.

Every command below is abstract — use the project's configured runner (`CLAUDE.md` § Essential Commands), never a specific tool's API.

## suite — automated run (evidence path)

Run the configured e2e command over the phase's scenarios headlessly. It seeds any fixtures, exercises the flow, asserts, and records `{scenario, status}` to the evidence JSON that `checks/03-scenario-evidence` reads. Use this for phase gating: RED before the feature (fails for the right reason), GREEN after (passes). A run that goes green but records zero assertions is hollow — treat it as not-passing.

## conductor — guided UI walkthrough

For new or changed UI that deserves visual scrutiny. Two phases:

1. **Navigate (fast).** Reach the feature under test by the shortest reliable path — reuse a login/setup helper rather than clicking through from scratch.
2. **Validate (slow).** Step through the new behaviour one action at a time; capture a screenshot/log at each key state; check for console/network errors. Record findings against the scenario's Given/When/Then.

Runs from the main session. Capture the evidence so `/verify:complete` can record the scenario as passing.

## direct — ad-hoc check

A quick, unstructured interactive look — reproduce a bug, sanity-check one screen, confirm a fix by hand. Fast and disposable. **Not** valid phase-gating evidence on its own; if it confirms a scenario, re-run that scenario under `suite` or `conductor` to record it.

## data-layer — no-UI validation

For scenarios with no user interface — schedulers, background jobs, engines, pure API/CLI paths. Trigger the behaviour through its entry point (API call, CLI command, job trigger), then assert on the resulting state via data queries or API reads. Record pass/fail per scenario the same way.

## Setup & isolation (any mode)

- **Reach a known state first.** Clear stale session/auth and seed the scenario's fixtures before exercising it, so a failure means a real defect, not leftover state.
- **One scenario, one result.** Don't batch several scenarios into a single run — each acceptance id needs its own recorded pass.
- **Report a clear verdict** per scenario: PASS (criteria met), FAIL (ran, found a defect), or BLOCKED (couldn't run — infra/setup). BLOCKED is an environment problem; stop and fix it before burning through the rest of the queue.

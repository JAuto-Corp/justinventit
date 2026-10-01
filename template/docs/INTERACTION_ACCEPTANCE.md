# Interaction acceptance

For work that changes a user-facing flow, planning lists the observable outcomes
the user must be able to achieve. Before PR-ready, prove each planned outcome by
running the real browser interaction against an authorized preview, staging or
local environment with accurate scenario data.

Trace the result back to the planned outcome in the existing SPEC/scenario or PR
record; no new evidence store is needed. A compact table is enough:

| Planned outcome | Scenario/data | Environment and revision | Interaction | Expected → observed result | Evidence |
|-|-|-|-|-|-|
| Save an edited value | Representative editable record | Authorized local/preview/staging target; tested SHA | Open editor, change value, activate Save, reopen record | Value is saved → actual observed value and state | Browser run/trace or observation link |

Use data that represents the relevant state, role and permissions; empty fixtures
or an unrelated happy path do not demonstrate the planned outcome. Preserve the
project's target, test-data and external-effect rules. Accurate scenario data
does not mean copying customer data or sending real external actions.

Exercise the control and observe its resulting behavior: saving must persist,
navigation must reach the intended destination, and a disabled or rejected action
must show the planned response. A screenshot of the control or passing unit tests
alone does not prove the interaction worked. Visual verification checks appearance;
this pass checks the action and outcome through the rendered application.

An automated or manual browser run may supply the evidence; use the project's
available browser tooling, without requiring a provider-specific tool. Record
PASS, FAIL or BLOCKED for every planned outcome. An unavailable environment is
BLOCKED, not an inferred pass from unit tests. Fix or obtain the existing project's
explicit disposition before claiming PR-ready; do not quietly omit the outcome.
For changes with no user-facing interaction, record that scope fact instead of
inventing a browser flow.

Why: a production completion modal's Done button did nothing despite green unit
tests. Origin: **JA, 2026-10-01**, owner request
`01M3W6MG1T1XGND7MW74GYTX26`. This is provider-neutral acceptance guidance; it
does not install a browser runner, CI gate or result collector.

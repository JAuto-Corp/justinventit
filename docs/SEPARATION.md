# JV / JA separation manifest

Owner direction 2026-09-13: JV (justinventit) is the independently maintained portable agent-development factory
and toolchain; JA (customer-portal) is a product it builds. Evidence: weekly curator packet 2026-09-13 GR-17 (delivery
discipline and Ponytail boot policy belong in the JV portable loop with ONE pointer from the product) and GR-21
(split-readiness test → JV agentic-separation program). These are migration evidence, not self-ratifying authority.

## JV-owned (lives here, versioned, delivered by overlay)

- Generic development loop and gates (`docs/DEV_LOOP.md`, `docs/TDD_GATE.md`), orchestrator skills, commands.
- Canonical provider-neutral skills under `template/.agents/skills/` with deterministic Claude projections, their
  provenance, licenses, fixtures, generator and checks (`scripts/generate-skill-surfaces.py`, `scripts/ci/*`).
- Provider adapters, runtime schemas, hub data model, seat protocol, model/effort matrix, provider compatibility
  work, and the versioned upgrade mechanics (proposed separately in PR #36; not part of this branch).
- Thin portable defaults such as `template/docs/SKILL_MODES.md`.

## JA-owned (never overwritten from JV)

Ownership is not physical location: JA may hold JV-generated framework surfaces (for example projected skill
directories) for runtime discovery, and those stay JV-owned and JV-versioned even inside the JA tree. JA-owned paths
are the product's own and no JV release writes to them. A project's `AGENTS.md` is seeded once and then
project-owned (`_skip_if_exists`, never prompted); it merges framework contract sections from a scratch render and
from CHANGES.md `entry-contract` rows, and adds the `docs/SKILL_MODES.md` read-and-apply line itself if it adopts
the vendored skills.

- Product code, schema, migrations, tests, the product's own generated artifacts (types, barrels, route catalog),
  and domain truth (AGENTS.md § Product domain routing).
- Product commands and JA-specific skills (`tds`, `backend-*`, `schema-relationships`, `action-catalog`, …).
- Effect and safety constraints: production/staging targets, money, customer contact, credentials, DDL, merge
  authority, CI cost rules, hub identity and seat letters.
- The live orchestration machinery JA runs today (`scripts/msg.sh`, `role-launch.sh`, `verdict-post.sh`,
  `verify-local.sh`, `substrate.sh`, pinned `.claude/agents/*`). Where JV's specs describe these as "not yet built",
  the flow is extraction JA → JV with domain content removed, never re-import.
- A thin declaration of which JV version and overrides the product uses, recorded in the adoption commit itself
  (the exact trailer shape is proposed in PR #36) plus one line in its capture channel.

## Bounded overlays (the only JV → JA path)

- Only JV-only artifacts, offered by release id, excluded mechanically when a path already exists in JA (upgrade
  procedure proposed in PR #36). From this branch that is the two pinned skills and `SKILL_MODES.md`. Exclusion is
  decided per runtime route actually present in the project tree: JA today has no project `.agents/skills/ponytail`
  or `.claude/skills/ponytail` route (its `ponytail` is a user-level Claude install at the same upstream hash, which
  Codex does not see), so an overlay would be evaluated route by route, and only when JA asks.
- No copied framework machinery, no hook/engine/plugin ecosystems, no second status store, no gate change by overlay.
- Known JV-internal inconsistencies stay inside JV until fixed: generated four-step contract vs the documented 0–8 loop;
  check `06-harness-sensitivity` specified but not shipped. The generated entry contract is now provider-neutral
  (`AGENTS.md` canonical and project-owned after seeding, `CLAUDE.md` imports it and carries only Claude Code extras). The
  runtime availability receipt still measures `frontend-design` only and requires CI's exact CLI versions; this branch
  only makes its probe project carry every pinned skill.

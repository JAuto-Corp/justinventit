# Spec-auditor pass 2 (fresh-context, opus) — verdict + g's spot-checks

VERDICT: DESIGN ROUND NEEDED (R3). 4 blockers, 8 majors. Status: OPEN, batched with
auditor-1's findings for the R3 round.

## Spot-checks performed by g before acceptance
- **B1 (Codex profile no-op): CONFIRMED empirically, with correction.** `codex exec
  --profile zzz-does-not-exist` runs on the DEFAULT tier, exit 0, no error. Even
  `--strict-config` with an invalid key in a real profile file printed the parse error but
  exited 0. Correction to the auditor's mechanism claim: the profile FILE
  (`~/.codex/<name>.config.toml`) IS read when it exists (invalid key was parsed from it) —
  the generated-file design direction stands; the defect is silent fallback on missing
  profile + non-fatal config errors. Fix (accepted): launcher MUST verify the resolved
  model/effort post-boot (e.g. probe turn asserting model id) — trust nothing about tier
  selection.
- **JAuto migration non-additivity: CONFIRMED.** supabase/migrations/20260517221227:17
  `letter char(1) PRIMARY KEY` + FKs at :33,:34,:61. Compound-keying in place drops FKs and
  rewrites child tables on the live staging hub. HUB §6 migration path must be redesigned
  (candidate: new namespaced tables + compatibility views + dual-write window, not in-place
  re-keying).

## Findings (auditor's text, verbatim below)
B1 — Codex tier selection silently no-ops. Generated per-project profile paths + unqualified --profile boot cell; every Codex seat can boot default tier while reporting success. Fix: launcher verifies RESOLVED model/effort post-boot.
B2 — dirty-RED deadlock: dirty:true never satisfies CI + Standard+ requires ledger red + same-change blocks ⇒ ordinary RED on uncommitted tree is inadmissible; spec never states commit-the-red workflow.
B3 — RED ancestry unbounded: any historical red for the scenario (incl. another PR's) satisfies merge-base ancestry; needs >= merge-base-with-target. Converse: rotation at N runs can evict red before green → false block. No fixtures either direction.
B4 — lease arithmetic: initial {holder:null,epoch:0,expires_at:null} vs dead predicate ⇒ healthy never-revived seat is always-dead or never-dead; reviver-held lease vs revived-seat token validation vs release-nulls-holder mid-turn; handoff unspecified.
M1 — epoch resets on registry recreate/re-adopt; fixture list omits registry recreation.
M2 — jsonl offset cursors invalidated by repair-by-rewrite; cursors must be hub_id-valued; "O(log size)" scan claim wrong (O(n)).
M3 — jsonl atomicity has no mechanism: flock ≠ crash atomicity; >PIPE_BUF appends tear; the partial-write fixture would fail, not catch.
M4 — JAuto migration not additive (CONFIRMED above); backfill vs never-rewritten contradiction; refuse-newer bricks un-upgraded seats mid-migration contra law 7.
M5 — composer decision table lacks branches for missing/corrupt markers, deleted regions, NEW upstream region (the normal upgrade case).
M6 — budget already breached today: ~/.claude/CLAUDE.md 4771B > 4KB headroom; 28KB+global > 32768; Claude auto-memory (~19KB) in neither measure; root CLAUDE.md 43.6KB needs >15KB shed, unacknowledged. (g note: budget model must be per-runtime — Codex chain measures ~/.codex/AGENTS.md not Claude's global; but the underspecification is real.)
M7 — own-letter rationale void: with per-consumer cursors, B reading A's mail advances B's cursor, not A's — stated "destroys delivery" teeth are false; real rationale (confidentiality/noise) must be stated, or teeth added.
M8 — frontend raise_to:maint is a model downgrade under the tier ordering; diagnostic "high→xhigh" uses an effort absent from tiers; Claude fixture asserts visibility but the normative claim is precedence.

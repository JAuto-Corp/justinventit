# Orientation Maps

> Phase-1 spec r2 (2026-07-27, user-directed founding intent; r1 red-teamed by Sol —
> 1 blocker + 7 majors incorporated, verdict archived). Companion to `CONTEXT_CONTRACT.md`
> (nested entry contracts point AT map sections) and terminate-and-fresh (fresh sessions
> make orientation load-bearing).

## 1. What a map is — and is not

A navigable synthesis of a system's **intention, architecture, patterns, and design** —
the high-level understanding from which an agent *directs* deeper autonomous exploration.
A MAP, not a territory substitute: it never replaces reading code; it says what exists,
why, what shape it has, and **where to dig**.

**Two-part construction (this is the anti-rot core, law 2 applied):**
- **Authored leaf sections** — the prose synthesis (intent, design, why). Authored at
  synthesis tier, dated, and each declares its **source inputs** (globs, specs, canonical
  examples) plus a `verified_at_sha`; a CI check invalidates the section (loudly, to a
  re-verification queue) when its declared inputs change. Semantic claims cannot silently
  stale — they visibly expire.
- **Generated everything-else** — navigation, indexes, counts, links, coverage inventory:
  generated from section metadata + the filesystem, freshness-gated, never hand-edited.
  *Origin: the predecessor map hand-maintained its counts and links; every count was wrong
  and four skill links were dead.*

Two hierarchies, one per layer — with ownership split (law 3): the **Layer-A map source is
framework-owned** (this repo); **project adoption/implementation deltas live in a
project-owned OVERLAY** (spec-vs-implemented status per component); the composed view is
generated, never a shared authored file.

## 2. Leaf-section contract (≈1-3KB applies to LEAVES, never whole subsystems)

Hierarchy is **recursively decomposed**: subsystem → domain → leaf (e.g. web → orders
domain → order-entry wizard). A **generated coverage inventory** (derived from runtime
entry points: routes, jobs, commands, functions, migrations groups) is produced BEFORE
synthesis and is the completeness ledger — a leaf either exists, is assigned, or is
explicitly deferred; silence is not an option. Decomposition is PILOTED on one subsystem
(web) before the full set is staffed.

Each leaf carries exactly:
1. **Intent** — what this is FOR.
2. **Architecture** — shape, boundaries, seams.
3. **Patterns** — canonical **rule identifiers + pointers** to the owning contract/skill,
   plus one observed-example pointer each. NEVER restated conventions (the operative rule
   lives in its owning AGENTS.md/skill; duplication is a defect per CONTEXT_CONTRACT §5).
4. **Design decisions** — load-bearing choices + rationale POINTERS.
5. **NYI / aspiration surface** — designed-but-unbuilt, deprecated-but-present,
   known-wrong: explicitly marked, verified in BOTH directions at review.
6. **Dig-here index** — files, skills, docs, tests.
7. **Metadata** (machine-readable): source globs, verified_at_sha, authored_by, date.

## 3. Production method

1. **Tool baseline**: curated repomix packs with a **reproducibility manifest** per pack —
   {source SHA, tool version (pinned in repo config), config hash, token count}. Packs are
   generated from a **sanctioned-synced workspace at a named SHA** — "a worktree exists" is
   not a source identification. Outputs are transient generated lenses (never tracked,
   never documentation). Pack topology: **paired for Layer A** (framework spec/template
   pack + project implementation pack — .claude/, .agents/, scripts/ are the implemented
   surface) and per-subsystem for Layer B **including** edge functions, tooling/simulation,
   and deployment surfaces (the predecessor map's omission class).
2. **Bite-size synthesis**: one or few leaves per dispatch. Executable tier mapping
   (interim manual until the resolved matrix ships): synthesis = docs_baseline/authoring
   tier; coherence + adversarial review = cross_review/thinking tier; collection/tool runs
   = doing tier.
3. **Per-leaf review = Sol review protocol v2, normatively** (MODEL_MATRIX): distinct
   charters (grounded fact-check: map-vs-repo; NYI bidirectional check), independent
   refutation pass on surviving findings, schema verdicts, full-SHA citations. Runtime-
   behaviour claims require runner-backed evidence or are marked static-verified-only.
4. **Coherence passes** at map milestones (cross-section, spec-set-pass pattern) +
   director review.
5. **Wiring**: nested entry contracts point at their subtree's map node (one-hop rule);
   dispatch packets cite map sections; fresh-session briefs point at the map first.

## 4. Future curated use

Dispatchers may attach `{pack manifest ref + map node}` to packets for bounded rapid
absorption; pack configs are reviewed like code. The map hierarchy is the durable
abstraction; packs are the disposable lens.

## 5. Sequencing

0. **Scope-first (user directive 2026-07-29)**: Understand-Anything (+ repomix packs) runs
   as a SCOPING instrument over the codebase BEFORE any synthesis — mapping domains,
   features, boundaries, hotspots — and its output produces the PLAN for the
   documentation/context-delivery deliverables (chunk list, order, per-chunk inputs).
   The tool informs the approach; its output is never the deliverable.
1. Tooling + pack configs + manifests + first packs + generated coverage inventory
   (doing-tier dispatch; exact workspace/SHA named in the dispatch).
2. Decomposition pilot on web → template validated → full leaf assignment.
3. Leaf synthesis batched across authoring-tier sessions (no session holds the whole map).
4. Review cadence per §3; overlay + composed-view generation once leaves exist.

## 6. Comprehension-rebuild method (Phase 2B — user directive 2026-07-29)

- **Chunks follow product seams**: domains and features sized for context — never
  file-count or directory batches.
- **User flows are first-class content**: each domain/feature chunk documents flows from
  high concept down (concept → journey → surfaces/API → data), not just structure.
- **Repeated Sol audit loops per chunk — the triage is the point.** High prior, stated
  before the work starts: the corpus mixes ASPIRATIONAL code with implemented code, and
  CORRECT documentation with incorrect. Every chunk's draft goes through Sol xhigh audit
  passes REPEATEDLY (the standing funnel), with the charter explicitly asking: what is
  implemented vs aspirational; which existing docs are wrong; what was the intent and
  where does the code deviate from it.
- **Every documented claim carries a classification**: IMPLEMENTED (grounded ref) /
  ASPIRATIONAL (no live referent — named as such) / DEVIATES (intent named, actual named)
  / DOC-WRONG (the superseded doc named and corrected or retired). Unclassified claims
  are the hallucination vector this method exists to close.
- **Sol carries the reading load**: reading-dominated passes run on Sol (cross-provider
  token availability); the Claude thinking tier reviews DISTILLATES and rules on
  dispositions — never reads the corpus wholesale. (Generalizes the corpus-comprehension
  routing rule to the entire phase.)
- Elaboration of per-chunk mechanics (pack manifests, audit charters, classification
  storage) is OPEN — designed at Phase-2B start via sequencing step 0's scoping output.

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
  stale — they visibly expire. **Invalidation is TWO-LEVEL (07-27; measured in the Understand-Anything dependency
  trial — repo Egonex-AI/Understand-Anything @ 2cda14e89, tested edit classes:
  comment-append vs exported-function-add; trial record archived at docs/reviews/2026-07-27-ua-trial-record.md in this repo)**:
  ANY content change to a declared input still enqueues the section for re-verification —
  that loud floor is what keeps "semantic claims cannot silently stale" true, since a
  function-BODY edit can change behavior while preserving every structural signature. On
  top of it, a STRUCTURAL/API-level fingerprint over each file's {functions, classes,
  imports, exports} — measured stable under the cosmetic class and name-precise on the
  structural class — classifies the queue: structural-fingerprint change = mandatory full
  re-verification; fingerprint-unchanged (cosmetic AND body-only edits — the trigger
  cannot distinguish them, so both take the stronger path available to them) = lighter
  grounded re-check. The fingerprint prioritizes; it never exempts. Build the extractor tree-sitter-based in-house; the
  trial's verdict was ADAPT the primitive, never adopt the dependency.
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
2. **Bite-size synthesis — INVERTED tier mapping (user ruling 2026-07-27: token-heavy
   analysis runs on the deep-quota runtime)**: leaf-DRAFT synthesis = **Sol xhigh
   one-shots** reading the pack (pack piped in, per-attempt output dirs, backgrounded —
   the corpus tokens land on the deep pool); review splits (item 3): GROUNDED
   lenses re-read the corpus and run on Sol (fresh threads — grounded review is
   corpus-priced, and that cost also lands on the deep pool); ACCEPTANCE/coherence runs
   on the Claude thinking tier reading drafts + verdicts only, never the pack. Claude
   never pays corpus cost; Sol pays it twice (draft + grounded review), by design. Bounded packs fit one-shots today; marginal packs
   (300-400k) get one probe before batching; unbounded subsystems wait for decomposition.
   Collection/tool runs = doing tier. General law: cost dominated by READING large
   corpora → Sol; cost dominated by judgment on small inputs → Claude thinking tier.
3. **Per-leaf review splits by cost shape, method = review protocol v2** (MODEL_MATRIX):
   the GROUNDED lenses (fact-check map-vs-repo; NYI bidirectional check) are corpus-reading
   work and run as **Sol xhigh one-shots** on FRESH threads (never the drafting thread —
   drafter/reviewer independence holds across Sol sessions); the ACCEPTANCE judgment and
   cross-leaf coherence read only drafts + verdicts and run on the **Claude thinking
   tier** — this is the same split as item 2, applied to review. Protocol v2 mechanics
   (distinct charters, independent refutation pass on surviving findings, schema verdicts,
   full-SHA citations) govern regardless of runtime. Runtime-
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

1. Tooling + pack configs + manifests + first packs + generated coverage inventory
   (doing-tier dispatch; exact workspace/SHA named in the dispatch).
2. Decomposition pilot on web → template validated → full leaf assignment.
3. Leaf synthesis batched across authoring-tier sessions (no session holds the whole map).
4. Review cadence per §3; overlay + composed-view generation once leaves exist.

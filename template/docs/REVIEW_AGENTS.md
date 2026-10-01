# Reviewer and drafting agents

The neutral charters below hold the procedures. `.claude/agents/<name>.md` is a
hand-written projection with the source's `model: opus`, `effort: xhigh` and
`Read, Grep, Glob, Bash` fields. There is no matrix generator in this slice.

| Agent | Canonical charter | Required input |
|-|-|-|
| spec-auditor | `docs/agents/spec-auditor.md` | SPEC path and factual context card; fresh context |
| code-reviewer | `docs/agents/code-reviewer.md` | Exact diff/head, assigned lens and factual context card |
| packet-drafter | `docs/agents/packet-drafter.md` | Artifact kind, decisions already made and evidence pointers |

The project's `REVIEW_PRACTICE.md` determines which review is commissioned,
blocking eligibility, round limits and provider availability. The charters do
not commission more reviewers. Supply the project root and resolve all paths
there. Reviewer output is evidence for the director; the drafter returns text
for the director to approve and send.

## Runtime limits

The Claude fields are copied selection settings, not a receipt that a runtime
honored them. `opus` is a runtime alias, not an immutable model-version pin.
An adopter verifies that the installed runtime supports the configured effort
and tools, and that the project's provider policy permits the invocation.
Unavailable or unauthorized settings use the existing policy's dispatch route;
do not silently claim a required tier was used.

The read-path contract is an instruction. Granting Bash does not mechanically
make a process read-only; the reviewer must obey the no-write/no-send charter.
This slice neither installs a sandbox nor invokes a live reviewer.

Codex and other runtimes can receive these same charters through their existing
commissioned seat or review runner. No `.codex/agents` files or equivalent
subagent discovery, model pins or tool enforcement are claimed here. The source
second-opinion definition references the same SPEC charter; review cardinality
continues to come from project policy, not an extra agent file.

## Why and origin

Source: **JA `.claude/agents`, inspected 2026-10-01**. These are historical
references, not required project paths or runtime targets.

- `spec-auditor.md`: arithmetic, prior art, grounded claims, acceptance ordering
  and cross-boundary checks catch defects an internally consistent SPEC can hide.
  The source read-path correction is JA commit `a33cfa383` (2026-07-27, #3390).
- `code-reviewer.md`: require grounded findings and distinguish executable
  coverage from source-pattern, inert or runner-incompatible assertions. Source
  commit `45e7e80e7` (2026-07-28, #3414) includes the coverage-rule wiring.
- `packet-drafter.md`: drafting from named evidence saves director work without
  delegating decisions or sending authority. The source definition is an
  untracked local artifact citing the owner directive of 2026-08-11; it was read
  directly, not attributed to a committed source revision. Snapshot SHA-256:
  `4486babddc08ceb899cb5939be94382117ef624446cf0d0a194a52ad809497db`.
- Explicit model/effort fields prevent accidental inheritance of the spawning
  seat's tier. Source lesson: JA #3354, retained by the 2026-07 agent definitions.

Inherited review recipes and gate-policy reconciliation are tracked separately
in framework issue #76. W-D2 copies and parameterizes the charters; it does not
add review rounds, test cells or mutation machinery.

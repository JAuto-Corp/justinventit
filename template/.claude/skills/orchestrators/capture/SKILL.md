---
name: capture
description: "Turn signals surfaced during work into tracked issues. Park discoveries and keep moving; convert audit/session findings to issues; block, triage, and roll up into epics — the human side of the self-improvement loop."
---

# Capture

Signals in, issues out. During work you surface things outside the current task — a blocker, a defect, an adjacent idea, or system friction. Emit a signal and keep moving; the stop actions log it; `capture` is the deliberate pass that turns those logs into tracked issues (and framework fixes). This closes the feedback loop `docs/SELF_IMPROVEMENT.md` describes.

> Park it and keep moving. A discovery you chase mid-task is two tasks half-done. Capture fast, label correctly, continue — then process the parking lot on purpose.

## Commands

| Command | Purpose | Workflow |
|-|-|-|
| `/capture:block` | File a `status:blocked` issue for an external blocker | `block.md` |
| `/capture:audit` | Convert `/verify:audit` findings into issues | `audit.md` |
| `/capture:findings` | Convert session discoveries (`DISCOVERIES.md`) into issues | `findings.md` |
| `/capture:triage` | Classify parked `captured` issues; label, prioritize, route | `triage.md` |
| `/capture:epic` | Group related captured issues into a new epic | `epic.md` |

## The feedback loop (what feeds this skill)

Two append-only logs collect signals automatically — never edit them by hand as a workaround; process them here.

| Log | Written by (stop action) | From signal | Capture processes it via |
|-|-|-|-|
| `context/DISCOVERIES.md` | `stop/actions/discovery-extraction.sh` | `[DISCOVERY:*]` | `findings` → issues |
| `context/FRICTION_LOG.md` | `stop/actions/friction-extraction.sh` | `[FRICTION:*]` | classify PROJECT/FRAMEWORK (below) |

The signal vocabulary lives in the `patterns` skill (§ Discovery Signals, § Friction Signals). Stop actions never block — they only append; acting on the logs is this skill's job.

**Discovery signals** (outside current scope):

| Signal | Meaning | Typical action |
|-|-|-|
| `[DISCOVERY:BLOCKER]` | Blocks current work | `/capture:block`, then keep moving |
| `[DISCOVERY:DEFECT]` | Bug found during work | Issue, continue |
| `[DISCOVERY:ADJACENT]` | Related, not blocking | Issue, continue |
| `[DISCOVERY:DISTANT]` | Unrelated finding | Issue, continue |

## Processing friction (PROJECT vs FRAMEWORK)

`FRICTION_LOG.md` entries land tagged `Classification: TODO`. Resolve each per `docs/SELF_IMPROVEMENT.md` § Classification Guide:

- **PROJECT** — a local skill/hook/rule was wrong for this codebase. Fix the artifact in-repo (see the `workflow` skill), then set `Resolution:` on the log entry.
- **FRAMEWORK** — an orchestration/hook/state-format problem shared by every project. File it upstream, then let `copier update` pull the fix back:

```bash
gh issue create --repo JAuto-Corp/justinventit \
  --title "FRICTION: <one line>" --body "<log entry + why it's framework-level>"
```

## Label taxonomy (generic — projects extend)

Every captured issue carries the base `captured` label plus a type and priority. Keep it lean; the project defines its own domain labels.

| Facet | Values |
|-|-|
| Base | `captured` (set on creation; removed once triaged/assigned) |
| Type | `bug`, `enhancement`, `tech-debt` |
| Priority | `p0` (now), `p1` (this sprint), `p2` (planned) |
| Status | `status:blocked` |
| Lineage | `epic:N`, `discovered:from-#N` |

## Coherence

Capture writes issues + logs; it does not merge PRs or move work state. Blockers promoted here land in `context/WORKING.md` (Blockers) and, when they gate a phase, `docs/CURRENT_WORK.md`. Epics created here are planned later by `/work:epic-plan`. Verify code state before recording — trust the code over the tracker.

---

## /capture:block

File a blocked issue when an external dependency stops progress. Create the issue with `status:blocked`, record the blocker in `context/WORKING.md` (and `docs/CURRENT_WORK.md` if it gates a phase), append a `[DISCOVERY:BLOCKER]` line to `context/DISCOVERIES.md`, then keep moving on unblocked work. Full workflow: `block.md`.

## /capture:audit

Convert the findings from a prior `/verify:audit` run into tracked issues. Confirm each finding is still valid and not a duplicate, create one `captured` issue per actionable finding (grouping duplicates, mapping severity → priority), and append `[DISCOVERY:*]` lines to `context/DISCOVERIES.md` linking the created issues. Full workflow: `audit.md`.

## /capture:findings

Process the session's discoveries — the `[DISCOVERY:*]` entries the stop action collected in `context/DISCOVERIES.md`, plus any surfaced live — into issues. Read the log, skip already-tracked items, create one `captured` issue per open discovery, and annotate the log entry with the issue number. Full workflow: `findings.md`.

## /capture:triage

Give the parking lot a pass. List open `captured` issues, classify each by discovery type (blocker / defect / adjacent / distant), set type + priority labels, promote blockers into the active state chain, and leave the rest parked with the `captured` label removed. Full workflow: `triage.md`.

## /capture:epic

When several captured issues share a theme, group them into a new epic issue that links them as its scope, and note the epic in the state chain for a later `/work:epic-plan`. This creates a NEW epic — routing issues into EXISTING epics is `/capture:triage`. Full workflow: `epic.md`.

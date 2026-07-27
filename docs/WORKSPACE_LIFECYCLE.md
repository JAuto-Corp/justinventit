# Workspace & Data Lifecycle

> Phase-1 spec (2026-07-26, added by director ruling). Companion to `ARCHITECTURE.md` §2 (L3)
> and `TDD_GATE.md` §2. Defines the classes of workspaces (checkouts/worktrees), databases,
> and local files a fleet runs on — their persistence, ownership, provisioning, and cleanup —
> so the state contract and isolation adapters bind to explicit classes instead of folklore.

## 1. Workspace classes

| Class | Persistence | Backing branch | DB binding | Provisioned by | Cleaned by |
|-|-|-|-|-|-|
| main checkout | permanent | default/staging | shared persistent DB | human, once | never |
| role worktree (`<repo>-role-<L>`) | persistent (seat lifetime) | `role/<L>` off staging | shared persistent DB | seat-commissioning script | decommission script |
| epic worktree | transient (epic lifetime) | `feature/epic-N` | **transient branch DB** | create-epic script | cleanup-epic script (worktree + DB together) |
| agent worktree (in-session teams) | transient (task lifetime) | task branch | inherits parent's | harness/team-lead | harness auto-remove if unchanged; registry sweep otherwise |
| scratch clone | transient (experiment) | any | none/read-only | ad-hoc | owner deletes; never registered |

Rules:
- **A workspace's class is declared, not inferred** — recorded in the seat/workspace record
  (`workspace_class` field) and derivable by tooling; scripts that behave differently per
  class (write guards, DB resolution, trust) read the declaration, never regex the path.
  *Origin: seat identity recovered by regexing `customer-portal-role-X` from paths broke
  silently for every non-matching layout.*
- **Transient workspace + its transient DB are one lifecycle unit**: provisioned together,
  cleaned together; a cleanup that removes one but not the other is a defect the registry
  sweep reports (orphaned branch DBs and orphaned worktrees both rot silently otherwise).
- A **workspace registry** (runtime state, per project) lists every live workspace with
  class, owner, branch, DB ref, created_at; sweeps reconcile registry vs filesystem vs DB
  provider and report drift loudly. *Origin: a live registry file reporting `active: []`
  beside two full agent worktrees.*
- **Multi-resident workspaces are read-mostly.** When more than one seat shares a working
  tree (the main checkout typically hosts director + orchestrate + integrate), the
  **guarded command set** — `checkout`/`switch`, `reset`, `rebase`, local `merge`, `stash`,
  `clean`, `gc`/`prune`, repo-config edits, and deleting branches a co-resident may occupy —
  requires the coordination protocol: mail every co-resident (roster = the workspace
  record's resident list) and proceed on **positive acks or a `coord_timeout` with no
  objection**; for contested or long operations take the **workspace lease** (same CAS/TTL
  mechanics as seat leases; mandatory for `clean`, `reset --hard`, and history rewrites);
  no response past timeout escalates to O, never proceeds silently. The hazard class is
  **any tree-wide operation, not just branch ops** — a shared checkout legitimately carries
  modified tracked state files and untracked strays belonging to several residents.
  Remote-side operations (gh/API merges, pushes of already-committed refs) are exempt from
  the working-tree coordination ONLY — ref and merge policy (integrator authority, cascade
  rules) still fully applies to them. A seat needing a local tree for conflict work uses a
  temporary worktree, never the shared checkout. **Activity in a multi-resident workspace
  is not attributable to a seat by observation** — transcript mtimes, process lists, and
  file activity there cannot distinguish co-residents; attribution comes only from the
  session registry / seat records. *Origins: integrator branch-switches under co-resident
  sessions; a seat nearly booted into another seat's authoring checkout; a sync fix that
  left 19 staged files in six worktrees where any bare `git commit` would have silently
  swept them onto live PR branches; a status report attributing the director's activity to
  the integrator from a shared-checkout transcript.*

## 1a. Worktrees are NOT sandboxes (two axes, never conflated)

| | Git worktree (collision isolation) | Runtime sandbox (capability confinement) |
|-|-|-|
| Protects against | concurrent WRITE collisions between seats | a process exceeding granted capabilities |
| Mechanism | separate working tree + index | OS/process-level jail (Codex `sandbox_mode`, Claude permission modes) |
| Shares with siblings | the ENTIRE repo: objects, refs, config, hooks, credentials, host filesystem, secrets | nothing by default; access is granted per workspace root / `--add-dir` |
| Is a security boundary | **NO** — a seat in a worktree can read/write anything its process can | yes, to the extent of its policy |
| Git semantics | a branch checked out in one worktree is LOCKED to it; gc/prune/config act repo-wide | none — sandboxes know nothing about git |

Rules:
- Never justify running less-trusted work "because it's in its own worktree" — worktree
  isolation is about merge hygiene, not containment. Containment comes from the runtime
  sandbox + command policy, and from nothing else.
- The two compose deliberately for Codex seats, with a precise limit: rooting the sandbox
  at the worktree confines **working-tree files and the per-worktree index** — but normal
  git writes also touch the **common git dir**, which lives OUTSIDE a linked worktree's
  root, so the launcher must grant it explicitly (`--add-dir <git-common-dir>`) or every
  commit fails; that grant necessarily exposes repo-wide metadata (refs, config, hooks),
  whose protection therefore comes from **command policy** (`.rules` ban classes), never
  from the sandbox root. Verify the pairing at boot; remember a parent session's live
  sandbox overrides beat an agent-file `sandbox_mode` (agent-file read-only is not a hard
  boundary); and host-filesystem/secret visibility is a property of the sandbox's grants,
  not of git.
- Shared-`.git` facts every seat must know: branch checkout is exclusive across worktrees;
  `gc`/`prune`/config edits act on ALL worktrees; deleting a worktree directory without
  `git worktree remove` leaves repo-level metadata behind (registry sweep catches it).

## 2. Database classes

| Class | Persistence | Writes from | Notes |
|-|-|-|-|
| production | permanent | deploy pipeline only | never a test/dev target |
| shared persistent (staging-class) | permanent | fleet, gated | doubles as hub backend on postgrest deployments; intentional prod-clone semantics are a PROJECT property, stated in Layer B |
| transient branch DB | epic/PR lifetime | its epic worktree + CI | provisioned/healed/rebased by integrator-owned tooling; identified by PR label, not local files |
| local/embedded (sqlite hub, evidence ledger) | host lifetime | owning seat/tooling | runtime state category; never git-tracked |
| per-test ephemeral (future) | test lifetime | test harness | the end-state that retires shared-foundation serialization |

Rules:
- **DB identity travels with the workspace record and the PR label — never with a
  git-tracked file.** (`.supabase-branch.json`-class files are local-only; tracking one
  leaked a deleted DB ref into unrelated branches.)
- **Transient-DB health is the integrator's responsibility**; workspaces flag, never heal.
- Every DB class names its **test-data policy**: production = forbidden; shared persistent =
  run-scoped markers + capture layer mandatory; branch = disposable, seeds create everything;
  local = owner's concern.

## 3. Local-file taxonomy (binds to ARCHITECTURE law 2 categories)

| Kind | Category | Location rule | Git |
|-|-|-|-|
| entry contracts, skills, hooks, specs | authored source | repo, layer-tagged | tracked |
| barrels, indexes, resolved matrix, manifests/locks | generated artifact | repo | tracked + freshness-gated |
| session state (WORKING-class), chain file, work-state, evidence ledger | runtime state | **workspace-local state dir, resolved from workspace root — never cwd** | ignored |
| seat registry, leases, cadence, mailbox projections | runtime state | coordination root, project-namespaced | outside repo |
| host-installed automation (cron watchdogs, boot prompts) | authored source | repo is canonical; host copy is a deployment | tracked mirror + install step |
| scratch/intermediate | transient | scratchpad dirs | never |

Rules:
- **State paths resolve from the workspace root, not the process cwd.** *Origin: a
  `get_state_dir()` returning the literal string `"context"` scattered state files into
  whatever directory hooks happened to run from.*
- **Runtime state is never merged across workspaces** — each workspace owns its copies
  (merge=ours / de-tracked); the cross-workspace state-of-record is the hub. *Origin:
  last-writer-wins clobbering of tracked state files across roles.*
- Host-installed automation follows the **mirror discipline**: the repo copy is reviewed
  and versioned; an install step (re)deploys it; the two are hash-compared by the doctor
  script so drift is loud.

## 4. Lifecycle contracts (who does what)

- **Provision**: seat commissioning (role worktrees) and epic creation (epic worktree + DB)
  are single scripts that complete the WHOLE checklist (trust entries for every runtime,
  state-dir init, registry entry, port lease) or fail loudly listing what's missing —
  partial commissioning is the source-system's recurring seat-setup gap.
- **Sync**: persistent workspaces sync from the integration branch via one sanctioned
  script that preserves the isolated runtime-state set; transient workspaces are never
  synced, they are recreated.
- **Cleanup**: transient classes have TTL + owner; the registry sweep reports overdue
  transients, orphaned DBs, and unregistered directories. Cleanup of a workspace revokes
  its runtime trust entries and port leases.
- **Provenance**: TDD evidence and hub events carry the workspace identity (§1 record), so
  a gate can distinguish "green on the epic worktree against its branch DB" from "green on
  a role worktree against staging" — these are different claims.

## 5. JAuto current-reality mapping (adoption inputs)

Matches: role worktrees (persistent, staging-backed), epic worktrees + branch DBs
(transient pair, integrator-healed), `.claude/worktrees/` agent class, local-only state
de-tracking, `sync-staging-to-worktree.sh`, mirror discipline precedent (`hub-ingest-tick`).
Known gaps this spec turns into Phase-0/2 work items: cwd-relative state writes;
`worktrees/registry.json` reporting empty beside live worktrees; watchdog/boot-prompt files
existing only host-side; per-worktree Codex trust entries absent; workspace records not yet
declaring class (path-regex inference everywhere).

## 6. Routed findings dispositioned here

- Isolation-adapter *lifecycle* ownership (auditor + coherence passes): the adapter
  interface remains `ISOLATION_ADAPTERS.md` (M3), but workspace/DB **classes, pairing, and
  registry semantics** — the parts the fleet needs before M3 — are normative here.

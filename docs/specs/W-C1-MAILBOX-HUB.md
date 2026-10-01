# W-C1: portable mailbox and bounded hub client

Status: proposed; pre-code SPEC/test-list audit pending. No implementation or
passing behavior evidence is claimed by this document.

## Intent

Extract the landed mailbox CLI into generated projects so two projects on one
host can use the same seat letters without sharing messages, cursors, locks or
completion results. Preserve the existing authoritative append, replay,
completion fan-out and recovery behavior. Make the optional legacy PostgREST
reader's target explicit and keep its credentials out of command arguments and
diagnostics. Document exactly which hub behavior this extraction supplies.

This serves extraction charter X1–X6: read-only source, explicit project roots
and identity, one neutral implementation, dated reasons for guards, actual
Copier execution and no transferred secrets.

## Source and dependency closure

Historical source: JA `scripts/msg.sh` and
`test-data/__tests__/scripts/msg-hub.test.ts`, pinned at
`57d273154cf029158b7cc118143808e524baf28c`. The source working tree is behind
the landed branch; extraction uses the pinned Git objects, not working bytes.

The CLI is self-contained Bash. Its executable dependencies are Bash 4.3+,
jq, GNU coreutils, grep, sed, awk and util-linux flock. Optional remote reads
also use curl. The acceptance runner uses Python's standard library and the
repository's pinned Copier. No product package manager, database or stack is
needed to send or read local mail.

Source tests supply the regression cases, translated into a portable runner.
The product TypeScript ingester, its application dependencies, raw SQL helper
and host tick service are not dependencies of the local transport. They are
not copied. Existing `hub/` assets remain a separate legacy projection schema;
they do not become an installed or running projector through this slice.

## Invariants

- **I1 — Project separation (X1, X2).** Local operations require an explicit
  stable project ID, project root and state root. Every mailbox, authority log,
  cursor, archive, trigger and transport lock is below that project's store.
  Two distinct IDs under one state root do not affect each other. Reusing an
  initialized ID for another project root fails before touching mail. Path
  components supplied as roles or archive task IDs cannot escape the store.
- **I2 — Authority before delivery (X4).** The existing exclusive append lock,
  byte-length framing, trailing-record repair, readback and file/directory
  durability barriers remain on the authoritative write path. A failed lock or
  barrier cannot report successful delivery or publish a new projection. A
  projection or trigger failure reports the correct already-recorded versus
  not-recorded state. Archive extraction takes the same append lock in shared
  mode and refuses an unlocked fallback.
- **I3 — Stable replay identity (X4).** Every event has a valid ULID and project
  ID. Same-ID/same-content retries, ignoring only the retry timestamp, reuse
  the original authority and canonical projection. Changed content or
  recipients under that ID are refused. Projection repair is append-only and
  preserves existing reader byte offsets.
- **I4 — Durable completion fan-out (X4).** A completion creates one authority
  record with sorted, normalized, unique recipients, and a canonical view per
  recipient. Replay, a fresh local read and the next unrelated append retain
  the existing recovery of missing completion views. Recovery failure cannot
  be mislabeled as successful delivery or as a newly recorded unrelated event.
- **I5 — CLI and mailbox fidelity (X4).** Legal send and hub forms keep their
  existing envelopes and structured payloads. Ambiguous send arity, malformed
  supplied identity, bad required fields/enums and completion-only invalid
  flags are refused before append. Unicode, quotes, backslashes and embedded
  newlines survive send/read/search/archive. Direct and broadcast mail retain
  independent per-reader cursors; peek does not consume mail.
- **I6 — Explicit remote target (X2, X6).** Remote reads require an explicit
  dedicated hub configuration file bound to the selected project ID. There is
  no host-home or product-env discovery. Credentials are read as data, never
  sourced as shell code, never placed in curl argv, and never printed by target
  inspection or failure diagnostics. Missing/mismatched configuration,
  malformed transport fields, network errors and non-2xx responses fail loud.
  Remote reads do not initialize a local mailbox store.
- **I7 — Delivered portability (X3–X6).** The CLI and its documentation render
  through Copier and execute in scratch consumer projects. Existing solo
  generation remains inert until the CLI is explicitly configured and invoked.
  Changed operating files contain no source-host paths, project names, live
  project refs, credentials or source issue numbers used as rules. Historical
  references are isolated and labeled in provenance. Smoke results distinguish
  local transport, mocked remote client behavior and unimplemented hub service
  behavior.

## Proposed interface and changes from the source

### Local identity and storage

The operator supplies these environment variables; they are not inferred from
the display name, current directory, Git remote or provider runtime:

| Variable | Meaning |
| --- | --- |
| `JV_PROJECT_ID` | Stable adoption ID matching `[a-z0-9][a-z0-9_-]{0,63}`; unique under the shared state root |
| `JV_PROJECT_ROOT` | Absolute, existing directory identifying the project; all its worktrees use the same root |
| `JV_STATE_ROOT` | Absolute directory for orchestration state; separate from product files is recommended |

The project root is canonicalized physically. The store is
`$JV_STATE_ROOT/$JV_PROJECT_ID`; mailbox artifacts are under `mail/` within it.
A small identity record binds the store to the ID and canonical project root.
Initialization is serialized with a store lock and uses an atomic record
write. An existing nonempty unmarked store or mismatched identity is refused;
no implicit migration or ownership reassignment occurs. Symlinked project-store
or mail directories are refused rather than allowing distinct names to alias
one store. The parent state root may itself be a canonicalized filesystem path.

Legacy independent `MSG_MAILROOT`, `HUB_EVENT_LOG`, `HUB_APPEND_LOCK` and
`HUB_DRAIN_TRIGGER` overrides are refused when nonempty, with migration guidance.
Their paths are derived together from the selected store. `MSG_HUB_ID` replay
and `MSG_FROM` actor defaults remain. The new top-level `project_id` is inserted
on the common append path before identity comparison and framing; mailbox
views carry the same field. This does not claim the full normative schema.

Plain-mail actor/recipient and reader names allow bounded ASCII identifiers
starting with a letter and containing letters, digits or underscores. Existing
`all`, `human`, one-letter seats and service senders remain valid. Hub actors
and completion recipients retain their stricter existing one-letter rules.
Archive task IDs allow letters, digits, underscores and hyphens, beginning with
a letter or digit. Path separators, traversal, glob and regex characters are
not accepted as mailbox path components. Message text is unrestricted data.

Help remains available without configuration. Invalid CLI input must not append
an authority or projection record; an empty initialized store is not delivery.
The filesystem trust model is unchanged: cooperating local agents, not hostile
tenants sharing a writable store. Roles and project IDs are routing metadata,
not authentication.

### Hub reads

`MSG_ENV_FILE` explicitly names an absolute dedicated hub env file. The file
contains `HUB_PROJECT_ID`, `HUB_URL` and `HUB_SERVICE_KEY`; no product variable
names or fallback search remain. `HUB_PROJECT_ID` must match `JV_PROJECT_ID`.
`HUB_URL` is an HTTPS origin without userinfo, query, fragment or embedded
control characters. Curl configuration values reject control characters,
quotes and backslashes before interpolation. The key is passed using curl's
configuration stdin. Error output is bounded to a safe operation/status message;
raw response bodies and credential-bearing curl diagnostics are not echoed.

`hub target` prints only the selected project ID, env-file path and URL; it
requires valid target identity and URL but need not read or print the service
key. `hub seats|open|mine|blocked [--json]` retain the existing legacy queries.
Plain send and hub writes continue to work without any remote credentials.

The identity assertion in an env file is not database tenancy enforcement.
Each project must have its own dedicated database/projection store and its own
externally supplied compatible projector. No remote read is advertised as a
read-after-write proof for the local append. A trigger file is only a hint to
an external service; this slice installs no watcher, cron or daemon.

### Files and integration

- Add `template/scripts/msg.sh` as the sole runtime implementation and a
  portable stdlib test runner under `template/scripts/tests/`.
- Add `template/docs/CLUSTER.md` with configuration, local send/read/completion
  smoke commands, dependency checks, retry/failure meanings, trust model,
  separate-store requirement and explicit missing components. Add a small
  cluster-only link in the generated playbook.
- Add a root extraction provenance record with dated guard origins. Keep
  template comments to the reason and a neutral provenance link/reference.
- Add a narrow CI runner that Copier-renders two projects, invokes the generated
  CLI/tests and performs collision/coupling/secret checks; wire that runner into
  existing CI. No new package manager or runtime dependency installation.
- Update `docs/HUB_DATA_MODEL.md` implementation-status text and `hub/README.md`
  only where needed to explain this bounded client and its new configuration.
  Do not mark pending backend or conformance roadmap items complete.

No Copier question is needed: identity and state belong to an adopted running
cluster, not to the generated display-name answers. The script is inert on
generation and gets no automatic hook, launcher or dev-log transport wiring.

## Non-goals

- Implementing project tenancy or recipient authorization inside PostgREST,
  SQLite, a new ingester/fold, missing hub verbs, database migration, raw SQL
  access, cloud provisioning or a complete backend conformance suite.
- Replacing byte-offset mailbox cursors with durable acknowledged ULID cursors,
  promising exactly-once consumption, rebuilding every ordinary-mail view, or
  repairing arbitrary interior authority-log corruption. Retain the source's
  bounded trailing-record recovery and completion-view recovery.
- Changing host scheduling, launchers, cadence, watchdogs, dev-log routing,
  producer supervision or the completion consumer/acknowledgment lifecycle.
- Running a product stack, changing source-host state, moving source credentials,
  performing a live database/network test, or executing the later adoption pilot.
- General shell modernization or new guarantees unrelated to project separation
  and safe configuration. Changes to inherited semantics require an explicit
  invariant/finding trace and scope disposition.

## Test list for pre-code audit

Each row has a positive witness and a refusal/failure witness. Parameterized
variants are finite source-regression cases, not additional invented contracts.
Fixtures use isolated temporary roots, synthetic data and subprocess argv;
they never read an actual host env file or call a live hub. Assertions check
diagnostics and persisted artifacts as well as exit codes so an absent or
always-refusing CLI cannot satisfy negative cells.

| ID | Positive/control witness | Refusal/failure witness |
| --- | --- | --- |
| I1-A | Two real renders, same seat letters and supplied ULID, distinct project IDs under one state root; independent authority, broadcast/direct mail, cursors, archives, completion and locks after process restart | Missing/invalid ID, relative roots, missing project root, reused ID with another root, nonempty unmarked store, symlink alias and legacy path override all fail without mail outside the selected store |
| I1-B | Concurrent first use binds one store; safe service sender, special recipient and archive task ID work | Role/task path traversal, separator, glob and regex forms fail without external artifacts; identity-lock acquisition failure does not initialize or append |
| I2-A | Plain and structured sends share framed authority, with valid UTF-8 byte lengths and exact projections; concurrent sends remain distinct and parseable | Stubbed append-lock failure, unwritable authority and file/directory sync failure produce no new projection; retry after restored barrier succeeds |
| I2-B | Partial final line and invalid-length final frame are removed before a new valid append; archive succeeds with the shared append lock | Shared-lock failure refuses archive extraction; persistent projection failure reports recorded/unknown; failed trigger reports append already landed, with authority asserted |
| I3-A | Delayed same-ID replay under a different clock deduplicates authority and projects original timestamp/content; missing and partial projections heal append-only with a parked byte cursor | Changed body or recipient with the same ID is refused without new view; invalid/overflow ULID, failed clock and short entropy refuse new events |
| I4-A | Completion normalizes duplicate mixed-case recipients into one authority record and exact per-recipient views; same-ID retry, fresh read and unrelated append each repair a missing view | Persistent view failure stays recorded/unknown; historical repair failure refuses an unrelated append as not recorded; changed completion content under the same ID remains refused |
| I5-A | Three/four-argument send, alert/request prefix, attached correlation ID and literal `--`; dispatch/status/rule/thread/finding/attention payloads; completion optional fields; stdin/body-file input | Five-position send, bare/empty correlation flag, malformed required fields/enums, invalid checklist JSON, and illegal/missing completion flag values fail with operation-specific diagnostics and unchanged authority |
| I5-B | Unicode and escaped/newline bodies survive read, literal search and date-filtered archive under inherited `xpg_echo`; peek preserves offsets; broadcast/direct reads remain independent | Re-reading consumed mail emits no old records; one reader cannot consume another's cursor; invalid path identifiers produce no cursor/archive; failed archive extraction does not advance its cursor |
| I6-A | Fake curl receives the expected seats/open/mine/blocked URL and a synthetic key only on stdin; raw/readable output works; target inspection creates no local store | Absent file, wrong project, product-only env, malformed URL/key, HTTP failure and network failure fail without calling an unintended target or exposing the synthetic key in argv/stdout/stderr; env-file shell syntax never executes |
| I7-A | Pinned Copier renders cluster and solo answers; generated shell syntax/executable modes, relative links and local smoke pass; existing generation matrix remains green | Coupling scan seeded with a source-host path and secret scan seeded with a synthetic credential both detect their seeds; real changed operating files and rendered outputs pass clean; missing executable is not counted as successful refusal |

Source regression mapping at GREEN must account for the source test families:
HUB/S2P0 write shapes and target resolution; finding route/resolve; P0 identity;
P1 authority/projection; HARD replay, framing, durability and archive; FU arity,
correlation and `xpg_echo`; COMPLETE CLI, compatibility, replay, repair and failure.
Product-ingester predicate assertions are replaced by an explicit non-goal;
old host/product target fallback expectations are deliberately inverted by I6.

Mutation checks are restricted to invariant-bearing changed/extracted code:
remove identity binding or path validation; skip append lock/barrier; weaken
same-ID comparison; skip completion recovery; loosen send arity; reintroduce
implicit env selection or put a key in argv. Run the existing cells against
each mutant. Add a cell only for a surviving mutant, traced to its invariant.

## Evidence and gates

1. Director commissions the required independent SPEC/test-list audit before
   any implementation. Preserve required opinion cardinality and cross-family
   review; no same-author substitution is claimed.
2. Write tests and retain a RED commit/run. A missing CLI is the initial positive
   absence witness, not evidence that negative-input guards are correct. Review
   the tests and their operation-specific negative oracles before implementation.
3. Implement from the pinned source, then run the same generated-project runner
   GREEN, finite mutants, existing generation matrix and the coupling/secret
   scans. Retain commands, versions, exit codes, source/candidate hashes and
   scratch paths in a sealed evidence packet. No live product service is used.
4. Full cross-family code review via the director at the exact GREEN head;
   traced fixes get RED/mutant evidence and security/locking fixes get the
   required narrow review. Director verdict precedes integrator-owned merge.

## Guard provenance to retain

These are historical evidence references, not operating rules or project pins.

| Origin | Guard and why |
| --- | --- |
| JA 2026-07-28, `136aace47`, PR #3407 | Framing, barriers, shared/exclusive lock agreement, canonical replay and honest delivery diagnostics prevent partial authority and false success |
| JA 2026-07-29, `78679b1bc`, PR #3425 / incident #3385 | Exact send arity and attached correlation values prevent shifted authorship; `printf` preserves JSON escapes under inherited shell options |
| JA 2026-08-02, `3ae8cf9fe`, PR #3446 | One completion authority record and repairable recipient views avoid duplicate results and lost completion delivery |
| JA 2026-09-24, `e0128d1a6`, PR #3579 | Explicit hub targeting separates control-plane reads from product storage; extraction removes the temporary fallback |
| JA 2026-09-30, portability audit §3 and extraction charter X2 | Explicit ID/roots and separate stores prevent same-seat collisions; baseline projection tables still lack multi-project tenancy |

## Reviewer context card

Purpose: the Intent paragraph above. Contract: I1–I7. Non-goals: the Non-goals
section above. Subject: this SPEC and test list only; no code exists in this
slice yet. Source: the pinned landed revision above. Ask: identify concrete
failures the listed witnesses would miss against I1–I7; trace each finding to
an invariant. An untraced suggestion is a note, not an implicit scope increase.
Implementation claims, backend conformance and final delivery acceptance remain
open until their stated gates.

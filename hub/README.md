# JV hub: postgrest backend (bounded baseline)

The hub is the dev team's coordination state of record (`HUB_DATA_MODEL.md`). With the
`postgrest` backend it lives in **its own Supabase project, never in the product's
database**. A product database gets cloned, reset and truncated on the product's
schedule, and its service-role key reaches customer data. The hub needs neither.

**Scope.** `0001_baseline.sql` is the JAuto-derived *legacy projection schema*, relocated
as-is. It does **not** yet meet the normative model in `HUB_DATA_MODEL.md`. Still
outstanding:
- `project_id` namespacing and tenancy (§4; §6 additive phase)
- `schema_version` (§6)
- durable consumer cursors (§1)
- recipient-scoped reads (§4)
- the shared conformance suite (§1, §5)

The authoritative record is still the append-only event log (the mailbox `events.jsonl`
and `from-*-to-*.jsonl`). These tables are its projection, plus the verb-gap rows written
through `hub-sql`.

## Contents

| Path | Purpose |
|-|-|
| `postgrest/migrations/0001_baseline.sql` | The hub schema: 8 `orchestration_*` tables and 2 views. The header records its provenance and its declared deltas from the JAuto hub. |
| `scripts/hub-schema-fingerprint.sql` | One sorted line per schema fact. Diff the output from two databases to run the schema-parity gate. |
| `scripts/hub-snapshot.sh` | Copies the 8 hub tables between databases, preserving keys and producing a manifest. See the commands below. |
| `scripts/hub-backup.sh` | Takes a nightly data snapshot into `~/.jauto-orchestration/hub-backups/` and keeps 14 days. |

`hub-snapshot.sh` commands:

| Command | What it does |
|-|-|
| `export` | Uses psql to read one `REPEATABLE READ` snapshot into CSVs plus a manifest. |
| `export-api` | Reads through the Management API when you have no database password. Every row is the database's own `to_jsonb(row)::text` in manifest order, so the local md5 of each file must equal its manifest hash. That proves the payload is exactly one consistent state. A mismatch means a writer moved rows mid-export: fence the writers and retry. |
| `import` | Loads everything in one transaction, in FK order, with constraints enforced. |
| `import-api` | Loads through the Management API in pages of about 900 KB each. Every input is validated before the first mutation. It commits one page at a time, so the target's writers must be fenced; on failure, rerun it with `--replace`. |
| `verify` | Checks that the manifest matches and that no FK row is orphaned. |

The manifest has one line per table: the row count and the md5 of the newline-joined `to_jsonb(row)::text`, in primary-key order. Text keys sort with `COLLATE "C"`, and every session pins `TimeZone=UTC`.

Pass a database as `@<env-file>`, which reads `HUB_DB_URL` from that file. The password then never reaches any argv. The API token goes to curl on stdin.

## Provisioning (adopter)

1. Create a Supabase project for the hub alone. On the free tier, it pauses after 7 days without activity and has no managed backups, so schedule `hub-backup.sh`.
2. Apply `postgrest/migrations/*.sql` in order.
3. Write `~/.jauto-orchestration/hub.env` with mode 0600. Never put it in any repository.

   ```
   NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<the hub project's service key>
   HUB_PROJECT_REF=<ref>
   HUB_DB_URL=postgresql://postgres.<ref>:<password>@<pooler-host>:5432/postgres
   ```

   The first two names match what the JAuto verb clients (`msg.sh`, the ingester) read today. A later release renames them to `HUB_URL` and `HUB_SERVICE_KEY`.
4. RLS stays enabled with no policies. The service role bypasses RLS, and anon or authenticated reads return nothing.

## Moving an existing hub out of a product database

Run the steps in this order:

1. **Fence the writers.** Stop the projection writer, and hold every other table writer (CI fixtures, raw SQL). Transport is log-first, so appends keep flowing into the event log.
2. **Consistent export.** Use `export` (one REPEATABLE READ snapshot), or `export-api` when you have no product database password. `export-api` proves consistency with the payload md5.
3. **Import** into the hub project.
4. **Verify.**
5. **Flip.** Point every consumer at `hub.env` in one move.
6. **Unfreeze.** The writer re-drains its window, deduplicated by `hub_id`.

Rollback is the same operation in reverse: `export-api` from the hub, then `import-api --replace` into the old home.

Dual-write is not needed when every table write either comes from the log or can be fenced during the freeze. See `docs/HUB_DATA_MODEL.md` §6.

The first execution was JAuto on 2026-09-23. Its plan and evidence are kept outside this public repository.

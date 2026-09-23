#!/usr/bin/env bash
# hub-snapshot.sh — consistent, key-preserving copy of the JV hub tables
# (postgrest backend) between two Postgres databases, with a verifiable manifest.
#
#   hub-snapshot.sh export   <db-url> <dir>            one REPEATABLE READ snapshot:
#                                                     8 CSVs + MANIFEST.tsv
#   hub-snapshot.sh export-api <project-ref> <dir>      no DB password: read-only
#                                                     Supabase Management API export
#                                                     (JSON pages). Consistent only
#                                                     when writers are QUIESCED: the
#                                                     manifest is taken before and
#                                                     after and must be identical.
#   hub-snapshot.sh import-api <project-ref> <dir> [--replace]
#                                                     no DB password: Management API
#                                                     import of an export-api dir, FK
#                                                     order, ~900 KB pages (one
#                                                     transaction PER PAGE — target
#                                                     must be quiesced; a failure
#                                                     means rerun with --replace);
#                                                     ends with a manifest check
#   hub-snapshot.sh import   <db-url> <dir> [--replace] one transaction, FK order,
#                                                     constraints enforced; --replace
#                                                     TRUNCATEs the 8 tables first
#   hub-snapshot.sh manifest <db-url>                  print the manifest
#   hub-snapshot.sh verify   <db-url> <dir>            manifest == <dir>/MANIFEST.tsv
#                                                     and zero FK orphans
#
# Manifest line per table: <table>\t<count>\t<md5 of to_jsonb rows ordered by pk>.
# to_jsonb makes the hash independent of column order; TimeZone/DateStyle/
# extra_float_digits are pinned so both sides render values identically.
# <db-url> is a libpq URL (e.g. HUB_DB_URL from hub.env). Needs psql >= 16.
# export-api reads SUPABASE_ACCESS_TOKEN (default: ~/.supabase/access-token).
set -euo pipefail

# FK order: parents before children (roles <- threads <- dispatches <- rest).
TABLES=(orchestration_roles orchestration_threads orchestration_dispatches
  orchestration_journal orchestration_attention orchestration_findings
  orchestration_docs orchestration_status_events)
pk() { [[ "$1" == orchestration_roles ]] && echo letter || echo id; }

SESSION_SETUP="SET TimeZone='UTC'; SET DateStyle='ISO'; SET extra_float_digits=3;"

manifest_sql() {
  local t sql=""
  for t in "${TABLES[@]}"; do
    sql+="SELECT '$t' AS t, count(*)::text AS n,
      md5(coalesce(string_agg(to_jsonb(x)::text, E'\\n' ORDER BY x.$(pk "$t")), '')) AS h
      FROM public.$t x
    UNION ALL "
  done
  echo "SELECT * FROM (${sql% UNION ALL }) m ORDER BY t"
}

orphan_sql() {
  # One row per FK constraint on the hub tables with its orphan count.
  cat <<'SQL'
DO $$
DECLARE r record; n bigint; bad int := 0;
BEGIN
  FOR r IN
    SELECT c.conrelid::regclass AS child, c.confrelid::regclass AS parent,
           a.attname AS col, af.attname AS pcol, c.conname
    FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
    JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = c.confkey[1]
    WHERE c.contype = 'f' AND c.conrelid::regclass::text LIKE '%orchestration\_%'
  LOOP
    EXECUTE format('SELECT count(*) FROM %s ch WHERE ch.%I IS NOT NULL AND NOT EXISTS (SELECT 1 FROM %s p WHERE p.%I = ch.%I)',
                   r.child, r.col, r.parent, r.pcol, r.col) INTO n;
    IF n > 0 THEN RAISE WARNING 'orphans % %: %', r.conname, r.child, n; bad := bad + 1; END IF;
  END LOOP;
  IF bad > 0 THEN RAISE EXCEPTION '% FK constraint(s) with orphans', bad; END IF;
END $$;
SQL
}

cmd="${1:-}"; url="${2:-}"
[[ -n "$cmd" && -n "$url" ]] || { sed -n '2,32p' "$0"; exit 2; }
# Refuse any target/source naming a ref listed in HUB_REFUSE_REFS (space-separated;
# JAuto sets its production ref here). Belt, not a boundary.
for ref in ${HUB_REFUSE_REFS:-}; do
  [[ "$url" == *"$ref"* ]] && { echo "hub-snapshot: refusing $ref (HUB_REFUSE_REFS)" >&2; exit 2; }
done

api_query() { # $1 = project ref, stdin = SQL; prints the JSON result array
  local tok="${SUPABASE_ACCESS_TOKEN:-$(cat "$HOME/.supabase/access-token")}"
  python3 -c 'import json,sys; print(json.dumps({"query": sys.stdin.read()}))' \
    | curl -sS --fail-with-body --max-time 120 -X POST \
        -H "Authorization: Bearer $tok" -H "Content-Type: application/json" \
        --data @- "https://api.supabase.com/v1/projects/$1/database/query"
}

api_manifest() { # the API session runs TimeZone=UTC (verified 2026-09-23)
  manifest_sql | api_query "$1" \
    | python3 -c 'import json,sys; [print(r["t"], r["n"], r["h"], sep="\t") for r in json.load(sys.stdin)]'
}

case "$cmd" in
  export-api)
    dir="${3:?export-api needs <dir>}"; ref="$url"; page=2000
    mkdir -p "$dir"
    [[ -z "$(ls -A "$dir")" ]] || { echo "export-api: $dir is not empty" >&2; exit 2; }
    api_manifest "$ref" > "$dir/MANIFEST.tsv"
    for t in "${TABLES[@]}"; do
      n=$(awk -v t="$t" '$1==t{print $2}' "$dir/MANIFEST.tsv")
      : > "$dir/$t.pages"
      for ((off = 0; off < n; off += page)); do
        echo "SELECT coalesce(json_agg(x ORDER BY x.$(pk "$t")), '[]') AS j FROM (SELECT * FROM public.$t ORDER BY $(pk "$t") LIMIT $page OFFSET $off) x" \
          | api_query "$ref" >> "$dir/$t.pages"
        echo >> "$dir/$t.pages"
      done
      python3 - "$dir/$t.pages" "$dir/$t.json" <<'PY'
import json, sys
rows = []
for line in open(sys.argv[1]):
    if line.strip():
        rows += json.loads(line)[0]["j"]
json.dump(rows, open(sys.argv[2], "w"))
PY
      rm "$dir/$t.pages"
    done
    api_manifest "$ref" > "$dir/MANIFEST.after.tsv"
    if ! diff -q "$dir/MANIFEST.tsv" "$dir/MANIFEST.after.tsv" >/dev/null; then
      echo "export-api: manifest changed during export — writers are NOT quiesced; discard $dir" >&2
      exit 1
    fi
    rm "$dir/MANIFEST.after.tsv"
    cat "$dir/MANIFEST.tsv"
    ;;
  import-api)
    dir="${3:?import-api needs <dir>}"; ref="$url"; replace="${4:-}"
    [[ -f "$dir/MANIFEST.tsv" ]] || { echo "import-api: $dir/MANIFEST.tsv missing" >&2; exit 2; }
    if [[ "$replace" == "--replace" ]]; then
      echo "TRUNCATE $(IFS=,; echo "${TABLES[*]/#/public.}");" | api_query "$ref" >/dev/null
    fi
    for t in "${TABLES[@]}"; do
      [[ -f "$dir/$t.json" ]] || { echo "import-api: $dir/$t.json missing (import-api needs an export-api dir)" >&2; exit 2; }
      python3 - "$dir/$t.json" "$t" <<'PY' | while IFS= read -r -d '' stmt; do printf '%s' "$stmt" | api_query "$ref" >/dev/null; done
import json, secrets, sys
rows, table = json.load(open(sys.argv[1])), sys.argv[2]
LIMIT = 900_000  # bytes per request; the Management API answers 413 near 1 MB+

def emit(batch):
    chunk = json.dumps(batch)
    tag = "j" + secrets.token_hex(8)
    while f"${tag}$" in chunk:
        tag = "j" + secrets.token_hex(8)
    sys.stdout.write(f"INSERT INTO public.{table} SELECT * FROM jsonb_populate_recordset("
                     f"NULL::public.{table}, ${tag}${chunk}${tag}$::jsonb);\0")

batch, size = [], 0
for r in rows:
    n = len(json.dumps(r))
    if batch and size + n > LIMIT:
        emit(batch)
        batch, size = [], 0
    batch.append(r)
    size += n
if batch:
    emit(batch)
PY
    done
    if ! diff <(api_manifest "$ref" | sort) <(sort "$dir/MANIFEST.tsv"); then
      echo "import-api: MANIFEST MISMATCH after import — rerun with --replace" >&2; exit 1
    fi
    echo "import-api: manifest identical ($(wc -l < "$dir/MANIFEST.tsv") tables)"
    ;;
  export)
    dir="${3:?export needs <dir>}"
    mkdir -p "$dir"
    [[ -z "$(ls -A "$dir")" ]] || { echo "export: $dir is not empty" >&2; exit 2; }
    {
      echo "\\set ON_ERROR_STOP on"
      echo "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;"
      echo "$SESSION_SETUP"
      for t in "${TABLES[@]}"; do
        echo "\\copy (SELECT * FROM public.$t ORDER BY $(pk "$t")) TO '$dir/$t.csv' WITH (FORMAT csv, HEADER)"
      done
      echo "\\copy ($(manifest_sql | tr '\n' ' ')) TO '$dir/MANIFEST.tsv' WITH (FORMAT text)"
      echo "COMMIT;"
    } | psql "$url" -X -q
    cat "$dir/MANIFEST.tsv"
    ;;
  import)
    dir="${3:?import needs <dir>}"; replace="${4:-}"
    [[ -f "$dir/MANIFEST.tsv" ]] || { echo "import: $dir/MANIFEST.tsv missing" >&2; exit 2; }
    {
      echo "\\set ON_ERROR_STOP on"
      echo "BEGIN;"
      echo "$SESSION_SETUP"
      if [[ "$replace" == "--replace" ]]; then
        echo "TRUNCATE $(IFS=,; echo "${TABLES[*]/#/public.}");"
      fi
      for t in "${TABLES[@]}"; do
        if [[ -f "$dir/$t.json" ]]; then
          echo "\\set j \`cat '$dir/$t.json'\`"
          echo "INSERT INTO public.$t SELECT * FROM jsonb_populate_recordset(NULL::public.$t, :'j'::jsonb);"
        else
          echo "\\copy public.$t FROM '$dir/$t.csv' WITH (FORMAT csv, HEADER)"
        fi
      done
      echo "COMMIT;"
    } | psql "$url" -X -q
    ;;
  manifest)
    printf '%s\n' "\\set ON_ERROR_STOP on" "$SESSION_SETUP" "$(manifest_sql);" \
      | psql "$url" -X -q -At -F $'\t'
    ;;
  verify)
    dir="${3:?verify needs <dir>}"
    got="$("$0" manifest "$url")"
    if ! diff <(printf '%s\n' "$got" | sort) <(sort "$dir/MANIFEST.tsv"); then
      echo "verify: MANIFEST MISMATCH" >&2; exit 1
    fi
    orphan_sql | psql "$url" -X -q -v ON_ERROR_STOP=1
    echo "verify: manifest identical ($(wc -l < "$dir/MANIFEST.tsv") tables), zero FK orphans"
    ;;
  *) sed -n '2,32p' "$0"; exit 2 ;;
esac

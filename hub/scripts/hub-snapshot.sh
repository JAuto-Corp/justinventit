#!/usr/bin/env bash
# hub-snapshot.sh — key-preserving copy of the JV hub tables (postgrest backend)
# between Postgres databases, proven by a manifest.
#
#   hub-snapshot.sh export     <db> <dir>             psql, one REPEATABLE READ snapshot:
#                                                     8 CSVs + MANIFEST.tsv from that snapshot
#   hub-snapshot.sh export-api <project-ref> <dir>    no DB password: Supabase Management API.
#                                                     Each row is the database's own
#                                                     to_jsonb(row)::text, one per line
#                                                     (<table>.jsonl), in manifest order, so
#                                                     the local md5 of the file MUST equal
#                                                     the manifest hash: the payload is
#                                                     proven to be one consistent state.
#                                                     A mismatch means a writer moved rows
#                                                     mid-export: fence writers and retry.
#   hub-snapshot.sh import     <db> <dir> [--replace] psql, ONE transaction, FK order,
#                                                     constraints enforced
#   hub-snapshot.sh import-api <project-ref> <dir> [--replace]
#                                                     Management API; every input is
#                                                     validated BEFORE any mutation; pages
#                                                     of ~900 KB (one transaction per page:
#                                                     the target must be fenced; on failure
#                                                     rerun with --replace)
#   hub-snapshot.sh manifest   <db>                   print the manifest
#   hub-snapshot.sh verify     <db> <dir>             manifest == <dir>/MANIFEST.tsv and
#                                                     zero FK orphans
#
# <db> is @<env-file> (reads HUB_DB_URL from it; preferred) or a libpq URL. A
# password in the URL is moved into PGPASSWORD for psql, never psql's argv; use
# the @file form so it stays out of this script's argv too.
# Manifest line: <table>\t<count>\t<md5 of to_jsonb rows, newline-joined, in
# primary-key order (text keys COLLATE "C")>. Every session pins TimeZone=UTC.
# The API token (SUPABASE_ACCESS_TOKEN, default ~/.supabase/access-token) goes
# to curl via -K on stdin, never argv. HUB_REFUSE_REFS (space-separated) are
# refused on the RESOLVED target. Needs psql >= 16 (server: see migrations).
set -euo pipefail

# FK order: parents before children (roles <- threads <- dispatches <- rest).
TABLES=(orchestration_roles orchestration_threads orchestration_dispatches
  orchestration_journal orchestration_attention orchestration_findings
  orchestration_docs orchestration_status_events)
# Primary-key ORDER BY expression; text keys sort bytewise so every server agrees.
order_by() {
  case "$1" in
    orchestration_roles) echo 'x.letter COLLATE "C"' ;;
    orchestration_threads | orchestration_findings | orchestration_docs) echo 'x.id COLLATE "C"' ;;
    *) echo 'x.id' ;;
  esac
}
SESSION_SETUP="SET TimeZone='UTC'; SET DateStyle='ISO'; SET extra_float_digits=3;"
die() { echo "hub-snapshot: $*" >&2; exit 1; }

manifest_sql() {
  local t sql=""
  for t in "${TABLES[@]}"; do
    sql+="SELECT '$t' AS t, count(*)::text AS n,
      md5(coalesce(string_agg(to_jsonb(x)::text, E'\\n' ORDER BY $(order_by "$t")), '')) AS h
      FROM public.$t x
    UNION ALL "
  done
  echo "SELECT * FROM (${sql% UNION ALL }) m ORDER BY t COLLATE \"C\""
}

orphan_sql() {
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

refuse_check() { # $1 = resolved URL or ref
  local r
  for r in ${HUB_REFUSE_REFS:-}; do
    [[ "$1" == *"$r"* ]] && die "refusing $r (HUB_REFUSE_REFS)"
  done
  return 0
}

# ---- psql side -------------------------------------------------------------
PGURL=""
resolve_db() { # $1 = @file | URL  ->  PGURL (no password) + exported PGPASSWORD
  local spec="$1" url split pw
  if [[ "$spec" == @* ]]; then
    url="$( { grep -m1 '^HUB_DB_URL=' "${spec#@}" || true; } | cut -d= -f2-)"
    [[ -n "$url" ]] || die "no HUB_DB_URL in ${spec#@}"
  else
    url="$spec"
  fi
  refuse_check "$url"
  split="$(python3 - <<'PY' "$url"
import sys, urllib.parse as u
p = u.urlsplit(sys.argv[1])
host = p.hostname or ""
netloc = (u.quote(u.unquote(p.username), safe="") + "@" if p.username else "") \
    + host + (f":{p.port}" if p.port else "")
print(u.unquote(p.password or ""))
print(u.urlunsplit((p.scheme, netloc, p.path, p.query, p.fragment)))
PY
)"
  pw="$(sed -n 1p <<<"$split")"
  PGURL="$(sed -n 2p <<<"$split")"
  if [[ -n "$pw" ]]; then export PGPASSWORD="$pw"; fi
}
pg() { psql "$PGURL" -X -q -v ON_ERROR_STOP=1 "$@"; }

# ---- Management API side ---------------------------------------------------
api_query() { # $1 = project ref, stdin = SQL; prints the JSON result array
  local tok body rc=0
  tok="${SUPABASE_ACCESS_TOKEN:-$(cat "$HOME/.supabase/access-token")}"
  body="$(mktemp)"
  python3 -c 'import json,sys; print(json.dumps({"query": sys.argv[1] + sys.stdin.read()}))' \
    "$SESSION_SETUP " > "$body"
  printf 'header = "Authorization: Bearer %s"\n' "$tok" \
    | curl -sS --fail-with-body --max-time 120 -X POST -K - \
        -H "Content-Type: application/json" --data @"$body" \
        "https://api.supabase.com/v1/projects/$1/database/query" || rc=$?
  rm -f "$body"
  return "$rc"
}
api_manifest() {
  local out
  out="$(manifest_sql | api_query "$1")" || die "manifest query failed on $1"
  python3 -c 'import json,sys; [print(r["t"], r["n"], r["h"], sep="\t") for r in json.load(sys.stdin)]' <<<"$out"
}

# ---- shared checks ---------------------------------------------------------
check_manifest_shape() { # $1 = file
  [[ "$(grep -c . "$1")" -eq "${#TABLES[@]}" ]] || die "$1 does not have ${#TABLES[@]} manifest lines"
  local t
  for t in "${TABLES[@]}"; do
    grep -qP "^$t\t[0-9]+\t[0-9a-f]{32}$" "$1" || die "$1 has no valid line for $t"
  done
}
jsonl_md5() { # $1 = jsonl file -> md5 of its lines newline-joined (= the manifest hash)
  python3 - "$1" <<'PY'
import hashlib, sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
if lines and lines[-1] == "":
    lines.pop()
print(hashlib.md5("\n".join(lines).encode("utf-8")).hexdigest())
PY
}
check_payload() { # $1 = dir: every <t>.jsonl hashes to its manifest line
  local t want got
  for t in "${TABLES[@]}"; do
    [[ -f "$1/$t.jsonl" ]] || die "$1/$t.jsonl missing"
    want="$(awk -F'\t' -v t="$t" '$1==t{print $3}' "$1/MANIFEST.tsv")"
    got="$(jsonl_md5 "$1/$t.jsonl")"
    [[ "$want" == "$got" ]] || die "$t payload md5 $got != manifest $want"
  done
}

cmd="${1:-}"; target="${2:-}"
[[ -n "$cmd" && -n "$target" ]] || { sed -n '2,35p' "$0"; exit 2; }

case "$cmd" in
  export-api)
    dir="${3:?export-api needs <dir>}"; refuse_check "$target"; page=2000
    mkdir -p "$dir"; [[ -z "$(ls -A "$dir")" ]] || die "$dir is not empty"
    api_manifest "$target" > "$dir/MANIFEST.tsv"
    check_manifest_shape "$dir/MANIFEST.tsv"
    for t in "${TABLES[@]}"; do
      n="$(awk -F'\t' -v t="$t" '$1==t{print $2}' "$dir/MANIFEST.tsv")"
      : > "$dir/$t.jsonl"
      for ((off = 0; off < n; off += page)); do
        out="$(echo "SELECT to_jsonb(x)::text AS r FROM public.$t x ORDER BY $(order_by "$t") LIMIT $page OFFSET $off" \
          | api_query "$target")" || die "page query failed ($t @ $off)"
        python3 -c 'import json,sys; [print(r["r"]) for r in json.load(sys.stdin)]' <<<"$out" >> "$dir/$t.jsonl"
      done
    done
    check_payload "$dir"   # proves the payload is exactly the manifest's state
    cat "$dir/MANIFEST.tsv"
    ;;
  import-api)
    dir="${3:?import-api needs <dir>}"; replace="${4:-}"; refuse_check "$target"
    # Validate EVERYTHING before the first mutation.
    [[ -f "$dir/MANIFEST.tsv" ]] || die "$dir/MANIFEST.tsv missing"
    check_manifest_shape "$dir/MANIFEST.tsv"
    check_payload "$dir"
    if [[ "$replace" == "--replace" ]]; then
      echo "TRUNCATE $(IFS=,; echo "${TABLES[*]/#/public.}");" | api_query "$target" >/dev/null \
        || die "TRUNCATE failed on $target"
    fi
    for t in "${TABLES[@]}"; do
      python3 - "$dir/$t.jsonl" "$t" <<'PY' | while IFS= read -r -d '' stmt; do
import secrets, sys
path, table = sys.argv[1], sys.argv[2]
LIMIT = 900_000  # bytes per request; the Management API answers 413 near 1 MB+
def emit(batch):
    chunk = "[" + ",".join(batch) + "]"      # the database's own row text, untouched
    tag = "j" + secrets.token_hex(8)
    while f"${tag}$" in chunk:
        tag = "j" + secrets.token_hex(8)
    sys.stdout.write(f"INSERT INTO public.{table} SELECT * FROM jsonb_populate_recordset("
                     f"NULL::public.{table}, ${tag}${chunk}${tag}$::jsonb);\0")
batch, size = [], 0
for line in open(path, encoding="utf-8").read().split("\n"):
    if not line:
        continue
    if batch and size + len(line) > LIMIT:
        emit(batch)
        batch, size = [], 0
    batch.append(line)
    size += len(line)
if batch:
    emit(batch)
PY
        printf '%s' "$stmt" | api_query "$target" >/dev/null || die "insert page failed ($t)"
      done
    done
    got="$(api_manifest "$target")"
    diff <(printf '%s\n' "$got" | sort) <(sort "$dir/MANIFEST.tsv") \
      || die "MANIFEST MISMATCH after import — rerun with --replace"
    echo "import-api: manifest identical (${#TABLES[@]} tables)"
    ;;
  export)
    dir="${3:?export needs <dir>}"; resolve_db "$target"
    mkdir -p "$dir"; [[ -z "$(ls -A "$dir")" ]] || die "$dir is not empty"
    {
      echo "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;"
      echo "$SESSION_SETUP"
      for t in "${TABLES[@]}"; do
        echo "\\copy (SELECT x.* FROM public.$t x ORDER BY $(order_by "$t")) TO '$dir/$t.csv' WITH (FORMAT csv, HEADER)"
      done
      echo "\\copy ($(manifest_sql | tr '\n' ' ')) TO '$dir/MANIFEST.tsv' WITH (FORMAT text)"
      echo "COMMIT;"
    } | pg
    check_manifest_shape "$dir/MANIFEST.tsv"
    cat "$dir/MANIFEST.tsv"
    ;;
  import)
    dir="${3:?import needs <dir>}"; replace="${4:-}"; resolve_db "$target"
    [[ -f "$dir/MANIFEST.tsv" ]] || die "$dir/MANIFEST.tsv missing"
    check_manifest_shape "$dir/MANIFEST.tsv"
    if [[ -f "$dir/${TABLES[0]}.jsonl" ]]; then check_payload "$dir"; fi
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    for t in "${TABLES[@]}"; do
      if [[ -f "$dir/$t.jsonl" ]]; then
        python3 - "$dir/$t.jsonl" > "$tmp/$t.json" <<'PY'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
print("[" + ",".join(l for l in lines if l) + "]")
PY
      else
        [[ -f "$dir/$t.csv" ]] || die "$dir/$t.csv missing"
      fi
    done
    {
      echo "BEGIN;"
      echo "$SESSION_SETUP"
      if [[ "$replace" == "--replace" ]]; then
        echo "TRUNCATE $(IFS=,; echo "${TABLES[*]/#/public.}");"
      fi
      for t in "${TABLES[@]}"; do
        if [[ -f "$tmp/$t.json" ]]; then
          echo "\\set j \`cat '$tmp/$t.json'\`"
          echo "INSERT INTO public.$t SELECT * FROM jsonb_populate_recordset(NULL::public.$t, :'j'::jsonb);"
        else
          echo "\\copy public.$t FROM '$dir/$t.csv' WITH (FORMAT csv, HEADER)"
        fi
      done
      echo "COMMIT;"
    } | pg
    ;;
  manifest)
    resolve_db "$target"
    printf '%s\n' "$SESSION_SETUP" "$(manifest_sql);" | pg -At -F $'\t'
    ;;
  verify)
    dir="${3:?verify needs <dir>}"; resolve_db "$target"
    check_manifest_shape "$dir/MANIFEST.tsv"
    got="$(printf '%s\n' "$SESSION_SETUP" "$(manifest_sql);" | pg -At -F $'\t')" || die "manifest query failed"
    [[ "$(grep -c . <<<"$got")" -eq "${#TABLES[@]}" ]] || die "target manifest does not have ${#TABLES[@]} lines"
    diff <(printf '%s\n' "$got" | sort) <(sort "$dir/MANIFEST.tsv") || die "MANIFEST MISMATCH"
    orphan_sql | pg
    echo "verify: manifest identical (${#TABLES[@]} tables), zero FK orphans"
    ;;
  *) sed -n '2,35p' "$0"; exit 2 ;;
esac

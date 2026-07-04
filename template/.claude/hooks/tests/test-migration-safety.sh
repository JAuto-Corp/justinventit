#!/bin/bash
# ===========================================================================
# Self-test: migration-safety PreToolUse guard  (guards/migration-safety.sh.jinja)
# ---------------------------------------------------------------------------
# The guard is DB-system-aware and ships as a Jinja template. This suite RENDERS
# it for db_adapter=supabase into the harness temp root, then drives the rendered
# script through the generic harness. Contract (matches write-isolation / cp):
#   * reads a PreToolUse JSON payload on STDIN (.tool_name / .tool_input)
#   * exit 2 = block (DDL in execute_sql; apply_migration with no local file)
#   * exit 0 = allow (DML; apply_migration WITH a file; malformed/empty payload)
#
# Coverage: DDL-in-execute -> block; DML -> allow; DML-that-merely-contains-
# "create" -> allow (no false-block); apply-without-file -> block; with-file ->
# allow; empty-name/malformed/empty-STDIN -> allow (fail-open).
# Run: bash test-migration-safety.sh   (exit 0 = all pass, non-zero = failure)
# ===========================================================================
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

SRC="$HERE/../guards/migration-safety.sh.jinja"

# --- Render the .jinja (db_adapter=supabase) into the harness temp root -------
# HARNESS_TMP is created (and auto-removed on exit) by harness.sh.
GUARD="$HARNESS_TMP/migration-safety.supabase.sh"
if ! python3 - "$SRC" supabase supabase "$GUARD" <<'PY'
import sys, jinja2
src, adapter, database, out = sys.argv[1:5]
env = jinja2.Environment(keep_trailing_newline=True)
tmpl = env.from_string(open(src).read())
open(out, "w").write(tmpl.render(db_adapter=adapter, database=database))
PY
then
  echo "FAIL: could not render migration-safety.sh.jinja (need python3 + jinja2)"
  exit 1
fi

# Rendered script must be valid bash before we exercise it.
if ! bash -n "$GUARD"; then
  echo "FAIL: rendered guard is not valid bash (bash -n)"
  exit 1
fi

# --- (1) DDL in execute_sql -> BLOCK -----------------------------------------
run_case --name "DDL (CREATE TABLE) in execute_sql -> block (exit 2)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"mcp__supabase__execute_sql","tool_input":{"query":"CREATE TABLE foo (id int)"}}' \
  --expect-exit 2 \
  --expect-out "MIGRATION SAFETY" --channel stderr

# --- (2) normal DML in execute_sql -> ALLOW ----------------------------------
run_case --name "DML (SELECT) in execute_sql -> allow (exit 0)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"mcp__supabase__execute_sql","tool_input":{"query":"SELECT * FROM foo WHERE id = 1"}}' \
  --expect-exit 0

# --- (2b) DML mentioning "create" but not DDL -> ALLOW (no false-block) -------
run_case --name "DML SELECT created_at (looks-like-create) -> allow (exit 0)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"mcp__supabase__execute_sql","tool_input":{"query":"SELECT created_at FROM users"}}' \
  --expect-exit 0

# --- (3) apply_migration with NO local file -> BLOCK (file-first) ------------
run_case --name "apply_migration without local file -> block (exit 2)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"mcp__supabase__apply_migration","tool_input":{"name":"add_users","query":"create table users(id int)"}}' \
  --expect-exit 2 \
  --expect-out "no local migration file" --channel stderr

# --- (4) apply_migration WITH a local file -> ALLOW --------------------------
run_case --name "apply_migration with local file -> allow (exit 0)" \
  --hook "$GUARD" \
  --setup "mkdir -p supabase/migrations && printf 'create table users(id int);\n' > supabase/migrations/0001_add_users.sql" \
  --stdin '{"tool_name":"mcp__supabase__apply_migration","tool_input":{"name":"add_users","query":"create table users(id int)"}}' \
  --expect-exit 0

# --- (5) apply_migration with unparseable/empty name -> ALLOW (fail-open) -----
run_case --name "apply_migration empty name -> allow (fail-open, exit 0)" \
  --hook "$GUARD" \
  --stdin '{"tool_name":"mcp__supabase__apply_migration","tool_input":{"query":"create table x(id int)"}}' \
  --expect-exit 0

# --- (6) malformed JSON payload -> ALLOW (fail-open) --------------------------
run_case --name "malformed JSON payload -> allow (fail-open, exit 0)" \
  --hook "$GUARD" \
  --stdin '{not valid json' \
  --expect-exit 0

# --- (7) empty STDIN -> ALLOW (fail-open) ------------------------------------
run_case --name "empty STDIN -> allow (fail-open, exit 0)" \
  --hook "$GUARD" \
  --stdin "" \
  --expect-exit 0

harness_summary
exit $?

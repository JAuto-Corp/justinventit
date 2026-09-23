#!/usr/bin/env bash
# hub-backup.sh — nightly data snapshot of the JV hub (postgrest backend).
# The schema lives in hub/postgrest/migrations; this keeps the DATA, plus the
# verifiable manifest, as the restore/rollback artifact (free-tier Supabase
# projects have no managed backups).
#
#   hub-backup.sh                 # uses HUB_ENV (default ~/.jauto-orchestration/hub.env)
#   HUB_BACKUP_KEEP_DAYS=14 HUB_BACKUP_DIR=... hub-backup.sh
#
# Restore: hub-snapshot.sh import "$HUB_DB_URL" <snapshot-dir> --replace
#          hub-snapshot.sh verify "$HUB_DB_URL" <snapshot-dir>
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUB_ENV="${HUB_ENV:-$HOME/.jauto-orchestration/hub.env}"
DEST="${HUB_BACKUP_DIR:-$HOME/.jauto-orchestration/hub-backups}"
KEEP="${HUB_BACKUP_KEEP_DAYS:-14}"

[[ -f "$HUB_ENV" ]] || { echo "hub-backup: $HUB_ENV not found" >&2; exit 2; }
url="$(grep -m1 '^HUB_DB_URL=' "$HUB_ENV" | cut -d= -f2-)"
[[ -n "$url" ]] || { echo "hub-backup: HUB_DB_URL missing from $HUB_ENV" >&2; exit 2; }

umask 077
mkdir -p "$DEST"
snap="$DEST/$(date -u +%Y%m%dT%H%M%SZ)"
"$HERE/hub-snapshot.sh" export "$url" "$snap" >/dev/null
size="$(psql "$url" -X -Atc "SELECT pg_size_pretty(pg_database_size(current_database()))")"
echo "hub-backup: $snap ($(du -sh "$snap" | cut -f1) on disk; database $size)"

# Retention: snapshot dirs only, by name pattern, older than KEEP days.
find "$DEST" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -mtime +"$KEEP" \
  -exec rm -rf {} +

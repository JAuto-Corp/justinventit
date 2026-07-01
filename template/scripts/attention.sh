#!/usr/bin/env bash
# attention.sh — the ONE attention query (the wake / session-start tick).
#
# The round-table's "one attention-query = the wake/session-start tick": a single
# read that answers "where did I leave everything" for the solo agent. It folds
# three derived views over the append-only stream:
#   1. blocked-on-user actions  (you can't proceed without Justin)
#   2. pending gates            (work waiting on a ratification / CI / a role)
#   3. stalled threads          (open threads with no activity past STALE_HOURS)
#
# Useful at N=1 (the dev-log IS the solo coherence core) and unchanged at N>1
# (same query; the events were just also transported as a byproduct).
#
# Wire into session-start: the session-start hook calls this so every fresh /
# post-compaction session opens on the attention payload — no file-scraping.

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIEW="$HERE/devlog-view.sh"

repo_root() { git rev-parse --show-toplevel 2>/dev/null || pwd; }
DEVLOG_DIR="${DEVLOG_DIR:-$(repo_root)/context/devlog}"
EVENTS="$DEVLOG_DIR/events.jsonl"

echo "=== ATTENTION (dev-log) ==="
if [ ! -s "$EVENTS" ]; then
  echo "(dev-log empty — start a thread: scripts/log.sh thread <id> \"<title>\")"
  echo "=== END ATTENTION ==="
  exit 0
fi

echo ""
echo "▸ Blocked on user:"
"$VIEW" user-actions | sed 's/^/    /'

echo ""
echo "▸ Pending gates:"
"$VIEW" gates | sed 's/^/    /'

echo ""
echo "▸ Open / stalled threads:"
"$VIEW" threads | sed 's/^/    /'

echo ""
echo "=== END ATTENTION ==="
echo "Drill into a thread: scripts/log.sh view thread <thread_id>"

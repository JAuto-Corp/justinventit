#!/bin/bash
# ===========================================================================
# Stop ACTION — landmark-checkoff
# ---------------------------------------------------------------------------
# Auto-checks PROGRESS.md items from recent commit trailers. When a commit
# message carries `landmark:<id>` and a PROGRESS.md has an UNCHECKED item that
# references that same `landmark:<id>`, the box is flipped to [x]. Keeps the
# checklist in sync with committed work with zero manual bookkeeping.
#
# Ported from customer-portal stop.sh §2 (Update PROGRESS.md from Recent Commits).
# Generalized: scans PROGRESS.md under the docs root instead of a domain plans
# path; flips any unchecked checkbox line that mentions the landmark.
#
# ACTION DISCIPLINE: a Stop action NEVER blocks and ALWAYS exits 0 (a non-zero
# stop action would stall the agent loop). Every failure is swallowed. Auto-
# discovered by runner.sh via the actions/*.sh glob — no registration needed.
#
# Config (env override, generic default):
#   JUSTINVENTIT_DOCS_DIR   default: <repo>/docs   (root scanned for PROGRESS.md)
# ===========================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/../../lib/utils.sh" 2>/dev/null || true

REPO_ROOT="$( (get_repo_root) 2>/dev/null || echo . )"
DOCS_DIR="${JUSTINVENTIT_DOCS_DIR:-$REPO_ROOT/docs}"

command -v git >/dev/null 2>&1 || exit 0
[ -d "$DOCS_DIR" ] || exit 0

# Landmarks referenced by recent commit trailers (last 10 commits).
LANDMARKS="$(git log -10 --format='%B' 2>/dev/null \
  | grep -oE 'landmark:[a-z0-9-]+' 2>/dev/null \
  | sed 's/^landmark://' | sort -u || true)"
[ -n "$LANDMARKS" ] || exit 0

# All PROGRESS.md files under the docs root.
PROGRESS_FILES="$(find "$DOCS_DIR" -name 'PROGRESS.md' -type f 2>/dev/null || true)"
[ -n "$PROGRESS_FILES" ] || exit 0

while IFS= read -r landmark; do
  [ -n "$landmark" ] || continue
  while IFS= read -r pf; do
    [ -n "$pf" ] || continue
    # Only act if there is an UNCHECKED item mentioning this landmark (word-bounded
    # so landmark:foo never matches landmark:foobar). Flip only the checkbox on
    # lines that reference the landmark; already-checked lines are left untouched.
    if grep -qE "^[[:space:]]*[-*] \[ \].*landmark:${landmark}([^a-z0-9-]|\$)" "$pf" 2>/dev/null; then
      sed -i -E "/landmark:${landmark}([^a-z0-9-]|\$)/ s/^([[:space:]]*[-*] )\[ \]/\1[x]/" "$pf" 2>/dev/null \
        && echo "[landmark-checkoff] $pf: landmark:${landmark} -> checked"
    fi
  done <<< "$PROGRESS_FILES"
done <<< "$LANDMARKS"

exit 0

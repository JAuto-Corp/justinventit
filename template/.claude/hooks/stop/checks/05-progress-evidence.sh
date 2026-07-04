#!/bin/bash
# ===========================================================================
# Stop CHECK 05 — PROGRESS.md EVIDENCE
# ---------------------------------------------------------------------------
# ENFORCES two things when a phase is signaled complete and has a PROGRESS.md:
#   (1) NO unchecked required items  ("- [ ]")  — the checklist must be done.
#   (2) checked items must be backed by real work — many items checked but ZERO
#       recent commits is suspicious (checklist ticked without implementation).
#
# Ported from customer-portal stop.sh §0.5 (unchecked-items block) and §0.7
# (commit-evidence Layer 0). Domain content removed; git is generic.
#
# BLOCK (exit 1): phase-complete signaled + PROGRESS.md present + (unchecked
#                 items OR >=3 checked items with no commits in last 24h).
# SKIP  (exit 0): no transcript / no [PHASE_COMPLETE] / [EVIDENCE_OVERRIDE:*] /
#                 no PROGRESS.md / all items checked and backed by commits.
# ===========================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/utils.sh"
source "$SCRIPT_DIR/../../lib/evidence.sh"

INPUT=""
if [ ! -t 0 ]; then INPUT="$(cat)"; fi

TRANSCRIPT="$(hook_transcript_path "$INPUT")"
transcript_has_signal "$TRANSCRIPT" '[PHASE_COMPLETE]' || exit 0
transcript_has_signal "$TRANSCRIPT" '[EVIDENCE_OVERRIDE:' && exit 0

PROGRESS_FILE="$(resolve_phase_file PROGRESS.md)"
[ -n "$PROGRESS_FILE" ] && [ -f "$PROGRESS_FILE" ] || exit 0

# (1) Unchecked required items block. "- [ ]" checkbox, any indentation.
UNCHECKED="$(grep -c '^[[:space:]]*- \[ \]' "$PROGRESS_FILE" 2>/dev/null || true)"
UNCHECKED="${UNCHECKED:-0}"
if [ "$UNCHECKED" -gt 0 ]; then
  report_check "block" \
    "Phase completion signaled but $UNCHECKED item(s) still unchecked in $PROGRESS_FILE. Complete them, defer to a new issue, or document why they are not applicable, then re-signal [PHASE_COMPLETE]." \
    || exit 1
  exit 0
fi

# (2) Commit-backing: many items checked but no recent commits is suspicious.
CHECKED="$(grep -c '^[[:space:]]*- \[[xX]\]' "$PROGRESS_FILE" 2>/dev/null || true)"
CHECKED="${CHECKED:-0}"
RECENT="$(git log --oneline --since='24 hours ago' 2>/dev/null | wc -l | tr -d ' ')"
RECENT="${RECENT:-0}"
if [ "$CHECKED" -ge 3 ] && [ "$RECENT" -eq 0 ]; then
  report_check "block" \
    "Phase completion signaled with $CHECKED checked items but NO commits found — PROGRESS.md may be checked off without implementation. Commit your work, or if this phase has no code changes add [EVIDENCE_OVERRIDE:no-code-changes]." \
    || exit 1
fi
exit 0

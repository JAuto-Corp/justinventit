#!/bin/bash
# contract-version.sh — warn (never block) when CLAUDE.md expects a newer AGENTS.md entry contract.
#
# AGENTS.md is seeded once and project-owned; CLAUDE.md is framework-updated. A contract change ships as a
# CHANGES.md `entry-contract` row and bumps both markers; a project that has not merged the row keeps an
# older `jv-entry-contract` in AGENTS.md while its updated CLAUDE.md expects the newer one. This prints ONE
# line so the session knows, and stays silent when the markers agree or either file has no marker.
#
# Usage: contract_version_warning <AGENTS.md path> <CLAUDE.md path>   (exit 0 always)

contract_version_warning() {
  local agents="$1" claude="$2" have expect
  [ -f "$agents" ] && [ -f "$claude" ] || return 0
  have=$(grep -oE '<!-- jv-entry-contract: [0-9]+ -->' "$agents" 2>/dev/null | head -1 | grep -oE '[0-9]+' || true)
  expect=$(grep -oE '<!-- jv-entry-contract-expected: [0-9]+ -->' "$claude" 2>/dev/null | head -1 | grep -oE '[0-9]+' || true)
  [ -n "$have" ] && [ -n "$expect" ] || return 0
  if [ "$have" != "$expect" ]; then
    echo "WARNING: AGENTS.md carries entry contract v$have but CLAUDE.md expects v$expect — merge the CHANGES.md entry-contract rows into AGENTS.md (non-blocking)."
  fi
  return 0
}

# Allow direct invocation for tests: bash contract-version.sh AGENTS.md CLAUDE.md
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  contract_version_warning "${1:-}" "${2:-}"
fi

#!/usr/bin/env bash
# Print only. Project entry instructions and dispatch supply authority.
set -euo pipefail
[[ $# == 1 && "$1" =~ ^[A-Z]$ ]] || { echo 'usage: boot-role.sh LETTER (one uppercase ASCII letter)' >&2; exit 2; }
LETTER="$1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
case "$LETTER" in O|I) TEMPLATE="$LETTER" ;; *) TEMPLATE=IMPLEMENTER ;; esac
FILE="$SCRIPT_DIR/../docs/orchestration/role-templates/$TEMPLATE.md"
[[ -f "$FILE" ]] || { echo "ERROR: missing role template: $FILE" >&2; exit 2; }
sed -e "s/<LETTER>/$LETTER/g" -e "s/<letter>/${LETTER,,}/g" "$FILE"

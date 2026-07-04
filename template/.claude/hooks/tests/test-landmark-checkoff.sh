#!/bin/bash
# ===========================================================================
# Self-test: Stop ACTION — landmark-checkoff
# ---------------------------------------------------------------------------
# Contract: an action NEVER blocks (always exit 0). When a recent commit carries
# a `landmark:<id>` trailer and a PROGRESS.md has an UNCHECKED item referencing
# that landmark, the box is flipped to [x] and a line is emitted. No matching
# landmark => nothing changes. Word-bounded (foo != foobar).
# Run: bash test-landmark-checkoff.sh   (exit 0 = all pass)
# ===========================================================================
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/harness.sh"

ACTION="$HERE/../stop/actions/landmark-checkoff.sh"

base='git init -q; git config user.email t@t; git config user.name t; mkdir -p docs;'

# (a) CHECKOFF — commit trailer matches an unchecked PROGRESS item -----------
run_case --name "landmark: commit trailer flips matching unchecked box" \
  --hook "$ACTION" --stdin "" \
  --setup "$base printf -- '- [ ] \`landmark:setup-db\`\n' > docs/PROGRESS.md;
           git add -A; git commit -qm 'do the thing' -m 'landmark:setup-db'" \
  --expect-exit 0 \
  --expect-out "landmark:setup-db -> checked" --channel any

# (b) NO-OP — no landmark trailer in recent commits --------------------------
run_case --name "landmark: no trailer -> exit 0, no change" \
  --hook "$ACTION" --stdin "" \
  --setup "$base printf -- '- [ ] \`landmark:setup-db\`\n' > docs/PROGRESS.md;
           git add -A; git commit -qm 'unrelated commit'" \
  --expect-exit 0

# (c) NO-OP — trailer present but no matching PROGRESS item -------------------
run_case --name "landmark: trailer with no matching item -> exit 0" \
  --hook "$ACTION" --stdin "" \
  --setup "$base printf -- '- [ ] \`landmark:other\`\n' > docs/PROGRESS.md;
           git add -A; git commit -qm 'x' -m 'landmark:setup-db'" \
  --expect-exit 0

# (d) NO-OP — item already checked (idempotent, no spurious echo) -------------
run_case --name "landmark: already-checked item stays checked -> exit 0" \
  --hook "$ACTION" --stdin "" \
  --setup "$base printf -- '- [x] \`landmark:setup-db\`\n' > docs/PROGRESS.md;
           git add -A; git commit -qm 'x' -m 'landmark:setup-db'" \
  --expect-exit 0

# (e) NO-OP — not a git repo / no docs -> graceful exit 0 ---------------------
run_case --name "landmark: no repo, no docs -> exit 0" \
  --hook "$ACTION" --stdin "" \
  --expect-exit 0

harness_summary
exit $?

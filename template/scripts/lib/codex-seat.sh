#!/bin/bash
# codex-seat.sh — Codex-runtime seat mechanics for role-launch.sh.
#
# Sourced, not executed. Provides:
#   codex_seat_resolve_bin        pin + PATH-prepare the codex binary, prove invocation
#   codex_seat_verify_trust       workdir trust gate (the parsed-trust contract)
#   codex_seat_verify_tier        resolved model/effort assertion (the runtime guard contract)
#   codex_seat_resume_guard       modal-parking policy on resume (the runtime guard contract)
#   codex_seat_reconcile_tier     post-exit check of the seat's OWN session
#
# Every function fails LOUD. The whole reason this file exists is that Codex's failure modes
# in this area are silent: a nonexistent profile boots the default tier at exit 0, and an
# untrusted workdir no-ops its .codex/ layer without a word.

set -euo pipefail

# ---------------------------------------------------------------------------
# Binary resolution
# ---------------------------------------------------------------------------
# PINNED path, and the shim's own directory goes on PATH. Both halves are load-bearing:
# a PATH-resolved copy is a different build, and the codex shim needs `node` next to it —
# without the PATH prepend it dies with "env: 'node': No such file or directory" before any
# call is made. Same lesson sol-review.sh learned: pinning fixes WHICH binary, not whether
# it runs, so we prove invocation with --version rather than by reading the file.
codex_seat_resolve_bin() {
  CODEX_BIN="${JV_CODEX_BIN:-}"
  if [[ "$CODEX_BIN" != /* || ! -x "$CODEX_BIN" ]]; then
    echo "ERROR: codex binary not found or not executable at pinned path: $CODEX_BIN" >&2
    echo "  Override with JV_CODEX_BIN only if you know why the pin is wrong." >&2
    return 1
  fi
  PATH="$(dirname "$CODEX_BIN"):$PATH"
  export PATH
  if ! CODEX_VERSION="$("$CODEX_BIN" --version 2>&1 | head -1)"; then
    echo "ERROR: codex binary at $CODEX_BIN is present but does not run." >&2
    echo "  Output: ${CODEX_VERSION:-<none>}" >&2
    return 1
  fi
  export CODEX_BIN CODEX_VERSION
  return 0
}

# ---------------------------------------------------------------------------
# Trust gate — the parsed-trust contract
# ---------------------------------------------------------------------------
# A workdir with no [projects."<path>"] entry silently no-ops its .codex/ layer. Nothing
# errors; the seat just runs unconfigured. Refuse to launch rather than boot a seat whose
# project configuration is quietly absent.
#
# The check PARSES the config; it does not grep it. A substring match is unsound in both
# directions that matter: `# [projects."/path"]` in a comment matches, and a real section
# whose trust_level is "untrusted" also matches. Both would print "trust OK" over a
# workspace whose .codex/ layer Codex is silently ignoring — the precise failure this gate
# exists to catch, reintroduced by the gate itself.
codex_seat_verify_trust() {
  local workdir="$1"
  local base_config="${CODEX_HOME:-$HOME/.codex}/config.toml"

  if [[ ! -f "$base_config" ]]; then
    echo "ERROR: no Codex base config at $base_config — workdir trust cannot be established." >&2
    echo "  See docs/CLUSTER.md for operator-managed trust and profiles." >&2
    return 1
  fi

  local level
  # A missing/broken parser is a HARD failure, never a skip: "cannot check" and "checked
  # and fine" must never share an exit status.
  if ! level="$(codex_seat__trust_level "$base_config" "$workdir")"; then
    echo "ERROR: could not parse $base_config to verify workdir trust." >&2
    echo "  A TOML parser (python3 >= 3.11, or tomli) is REQUIRED — an unverifiable trust" >&2
    echo "  state is treated as untrusted, not as a pass." >&2
    return 1
  fi

  if [[ "$level" != "trusted" ]]; then
    echo "ERROR: workdir NOT TRUSTED in $base_config:" >&2
    echo "    $workdir" >&2
    echo "    trust_level = ${level:-<no entry>}" >&2
    echo "  Without [projects.\"<path>\"] trust_level = \"trusted\", this workspace's .codex/" >&2
    echo "  layer SILENTLY no-ops (the parsed-trust contract) — the seat would look fine and run" >&2
    echo "  unconfigured. Refusing to launch." >&2
    echo "  See docs/CLUSTER.md for operator-managed trust and profiles." >&2
    return 1
  fi
  echo "trust        OK — $workdir (trust_level = trusted)"
  return 0
}

# Print the parsed trust_level for a workdir ("" if no entry). Non-zero exit = could not
# parse, which callers must treat as failure rather than as an empty answer.
codex_seat__trust_level() {
  python3 - "$1" "$2" <<'PY'
import sys
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        sys.exit(2)
try:
    with open(sys.argv[1], "rb") as fh:
        cfg = tomllib.load(fh)
except Exception:
    sys.exit(2)
entry = (cfg.get("projects") or {}).get(sys.argv[2]) or {}
print(entry.get("trust_level", ""))
PY
}

# ---------------------------------------------------------------------------
# Tier verification — the runtime guard contract, "empirically required"
# ---------------------------------------------------------------------------
# THE TRAP, reproduced 2026-07-29 (codex-cli 0.145.0, two controls): `codex exec -p
# <nonexistent-profile>` exits 0, emits NO warning on stdout or stderr, and runs on the
# default tier (resolved model gpt-5.6-sol, effort unset -> provider default `low`). A
# mis-typed or un-installed profile therefore produces a seat that is confidently the wrong
# tier and looks completely healthy. Config errors are likewise non-fatal.
#
# WHAT THIS PROBE MEASURES, precisely: it runs one throwaway `codex exec` under the SAME
# --profile the seat will use, then reads the RESOLVED model+effort out of that run's
# rollout `turn_context` record — the only place the effective tier is written down
# (`codex doctor --json` reports model "<default>" and does not even accept --profile;
# `codex exec --json` never emits the tier). Profile layering is a property of the config
# resolution, which exec and the interactive TUI share, so this asserts the tier the pane
# will get.
#
# WHAT IT DOES NOT MEASURE: it is a PRE-boot probe, by necessity. An interactive session
# writes no `turn_context` until its first turn, so there is no post-boot artifact to assert
# against at launch time — waiting for one would mean waiting for the seat to be given work,
# which is after the point where a wrong tier has already cost something. The post-exit
# reconciliation below closes the loop empirically once the session HAS taken turns.
codex_seat_verify_tier() {
  local profile="$1" want_model="$2" want_effort="$3" workdir="$4"
  local lock="${CODEX_HOME:-$HOME/.codex}/.jv-tier-probe.lock"
  local out rc=0

  mkdir -p "$(dirname "$lock")"
  echo "tier probe   running (profile=$profile, expect $want_model/$want_effort)…"

  local probe_out; probe_out="$(mktemp)"

  # Serialize tier probes only. Review runs use their own bounded semaphore, so a seat
  # boot never queues behind a long review and reviews never queue behind this short probe.
  #
  # `flock 200 || exit 9` is explicit ON PURPOSE. This subshell is the left operand of a
  # `||`, which suppresses errexit inside it — so a failed lock acquisition would otherwise
  # fall straight through to an UNSERIALIZED codex run and could still finish rc=0. The
  # guard cannot rely on `set -e` here.
  (
    flock 200 || exit 9
    timeout 240 "$CODEX_BIN" exec --json \
      -p "$profile" \
      -s read-only \
      -C "$workdir" \
      "Reply with the single word: ok" < /dev/null
  ) 200>"$lock" > "$probe_out" 2>/dev/null || rc=$?

  if (( rc == 9 )); then
    echo "ERROR: could not acquire the Codex tier-probe lock ($lock). NOT running without probe serialization." >&2
    rm -f "$probe_out"; return 1
  fi
  if (( rc != 0 )); then
    echo "ERROR: tier probe failed (codex exec rc=$rc). NOT launching an unverified seat." >&2
    rm -f "$probe_out"; return 1
  fi

  # Bind the evidence to THIS probe's thread. Selecting the globally-newest rollout by
  # mtime is unsound: any other Codex process writing a rollout in the window would be read
  # instead, and a wrong-tier profile could be validated against an unrelated session that
  # happened to run at the expected tier. The thread id is the only identifier that ties
  # the assertion to the run we actually made.
  local thread_id after
  thread_id="$(codex_seat__thread_id "$probe_out")"
  if [[ -z "$thread_id" ]]; then
    echo "ERROR: tier probe emitted no thread.started event — no identifiable evidence." >&2
    echo "  Absence of evidence is not a pass. Refusing to launch." >&2
    rm -f "$probe_out"; return 1
  fi
  rm -f "$probe_out"

  after="$(codex_seat__rollout_for_thread "$thread_id")"
  if [[ -z "$after" ]]; then
    echo "ERROR: no rollout found for probe thread $thread_id — cannot read the resolved tier." >&2
    echo "  Absence of evidence is not a pass. Refusing to launch." >&2
    return 1
  fi

  if ! out="$(codex_seat__read_tier "$after")"; then
    echo "ERROR: tier probe rollout has no turn_context record: $after" >&2
    return 1
  fi
  local got_model="${out%|*}" got_effort="${out##*|}"

  # An unset effort is the DEFAULT tier leaking through — the exact signature of the
  # nonexistent-profile trap. Treat it as a mismatch, never as "probably fine".
  if [[ "$got_model" != "$want_model" || "$got_effort" != "$want_effort" ]]; then
    echo "ERROR: TIER MISMATCH — the profile did not resolve to the intended tier." >&2
    echo "    expected: $want_model / $want_effort" >&2
    echo "    resolved: ${got_model:-<none>} / ${got_effort:-<unset — default tier>}" >&2
    echo "    profile:  $profile  (${CODEX_HOME:-$HOME/.codex}/$profile.config.toml)" >&2
    echo "    evidence: $after" >&2
    echo "  A nonexistent or unreadable profile boots the DEFAULT tier at exit 0 with no" >&2
    echo "  warning. Configure matching profiles as described in docs/CLUSTER.md." >&2
    return 1
  fi

  echo "tier         OK — $got_model / $got_effort (tier OK: $got_model/$got_effort; evidence: $(basename "$after"))"
  return 0
}

# Thread id from a `codex exec --json` event stream.
codex_seat__thread_id() {
  python3 - "$1" <<'PY'
import json, sys
try:
    for line in open(sys.argv[1]):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") == "thread.started":
            print(rec.get("thread_id") or ""); break
except OSError:
    pass
PY
}

# The rollout file for a SPECIFIC thread id. Codex names rollouts
# rollout-<timestamp>-<thread-id>.jsonl, so the id is a filename match — no mtime racing.
codex_seat__rollout_for_thread() {
  local root="${CODEX_HOME:-$HOME/.codex}/sessions"
  [[ -d "$root" && -n "$1" ]] || return 0
  find "$root" -name "rollout-*$1.jsonl" -type f 2>/dev/null | head -1
}

# Extract "model|effort" from a rollout's first turn_context record.
codex_seat__read_tier() {
  python3 - "$1" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as fh:
    for line in fh:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") == "turn_context":
            p = rec.get("payload", {})
            print("%s|%s" % (p.get("model") or "", p.get("effort") or ""))
            sys.exit(0)
sys.exit(1)
PY
}

# ---------------------------------------------------------------------------
# Resume guard — the runtime guard contract modal policy
# ---------------------------------------------------------------------------
# `codex resume` presents an interactive modal (summary-vs-verbatim). While it is
# unanswered the main loop takes NO turns and in-session subagent deliveries BLOCK —
# complete-but-cannot-land, the empty-report signature that cost this source deployment a full day of
# misdiagnosis. Booted is not live.
#
# The resume contract permits unattended resume only when `!resume_modal OR remote_answerable`. Codex has
# resume_modal = true, so the launcher permits it only where the pane is remotely
# answerable — i.e. running under tmux, where send-keys can drive the modal. Outside tmux
# the modal is answerable only by a human physically at the machine, and an unattended
# resume there parks the seat silently.
#
# The preferred path is not to resume at all: fresh-boot-with-a-durable-brief hits no modal,
# and durable state exists precisely so resume-context is optional.
codex_seat_resume_guard() {
  local letter="$1" allow_unattended="$2"

  if [[ -n "${TMUX:-}" ]]; then
    echo "resume       modal remotely answerable (tmux pane) — unattended resume permitted"
    return 0
  fi
  if (( allow_unattended )); then
    echo "resume       WARNING: not under tmux; proceeding on explicit --at-machine." >&2
    echo "             If nobody answers the resume modal, seat $letter parks SILENTLY:" >&2
    echo "             live PID, stale transcript, no turns, blocked subagent deliveries." >&2
    return 0
  fi
  echo "ERROR: refusing an unattended Codex resume outside tmux." >&2
  echo "  codex resume presents a modal that is answerable only at the machine here" >&2
  echo "  (the runtime guard contract: resume_modal AND NOT remote_answerable). An unanswered modal" >&2
  echo "  parks the seat with every health signal still looking normal." >&2
  echo "  Either: launch fresh (--fresh) with a durable brief — the preferred path, no" >&2
  echo "  modal — or pass --at-machine if a human is here to answer it." >&2
  return 1
}

# ---------------------------------------------------------------------------
# Post-exit reconciliation
# ---------------------------------------------------------------------------
# The pre-boot probe asserts what the profile RESOLVES to; this observes what a
# candidate rollout recorded, once it has taken turns and written a turn_context. It cannot
# gate the launch (it runs after the pane exits) but it converts a silent tier drift into a
# recorded, loud one instead of an assumption nobody ever checks.
# Find the rollout belonging to an INTERACTIVE session: created at/after `since_epoch` and
# whose session_meta.cwd is this seat's workdir. An interactive TUI emits no machine-readable
# thread id to the launcher, so this pair is the strongest available binding — strictly
# better than "globally newest file", which can match another seat's session entirely.
#
# UNIQUENESS IS NOT OWNERSHIP, and this helper does not pretend otherwise. Returning the
# sole match narrows the candidate set; it does NOT prove the rollout belongs to the process
# we launched. The counterexample is concrete: our seat takes no turns while another Codex
# session in the same workdir takes one inside the window — exactly one hit, and it is not
# ours. Because that cannot be excluded from the filesystem, the caller treats a MATCHING
# tier as ADVISORY-ONLY and never as verification (see codex_seat_reconcile_tier). Only the
# pre-boot probe, which is bound to its own thread id, verifies anything.
codex_seat__rollout_for_session() {
  local workdir="$1" since_epoch="$2"
  local root="${CODEX_HOME:-$HOME/.codex}/sessions"
  [[ -d "$root" ]] || return 0
  python3 - "$root" "$workdir" "$since_epoch" <<'PY'
import json, os, sys
root, workdir, since = sys.argv[1], sys.argv[2], float(sys.argv[3])
hits = []
for dirpath, _dirs, files in os.walk(root):
    for name in files:
        if not (name.startswith("rollout-") and name.endswith(".jsonl")):
            continue
        path = os.path.join(dirpath, name)
        try:
            if os.path.getmtime(path) < since:
                continue
            with open(path) as fh:
                first = fh.readline()
            rec = json.loads(first)
        except (OSError, ValueError):
            continue
        if rec.get("type") != "session_meta":
            continue
        if (rec.get("payload") or {}).get("cwd") == workdir:
            hits.append(path)
print(hits[0] if len(hits) == 1 else "")
PY
}

codex_seat_reconcile_tier() {
  local session_file="$1" want_model="$2" want_effort="$3"
  local out

  # THIS CHECK IS ADVISORY IN THE PASSING DIRECTION AND ACTIONABLE IN THE FAILING ONE, and
  # the asymmetry is deliberate. The rollout it reads is selected by workdir + time window,
  # which cannot prove ownership (see codex_seat__rollout_for_session) — so a MATCHING tier
  # is reported as "consistent", never "verified", because it might belong to a different
  # session in the same workdir. A MISMATCH is still worth failing on regardless of
  # ownership: some Codex session ran in this workspace at a tier nobody asked for, and that
  # is actionable whoever started it.
  #   0 = consistent (ADVISORY — ownership not provable)
  #   2 = no evidence
  #   1 = MISMATCH, the loud one
  if [[ -z "$session_file" || ! -f "$session_file" ]]; then
    echo "tier recheck  NO EVIDENCE — no session rollout for this seat (session took no turns?)"
    return 2
  fi
  if ! out="$(codex_seat__read_tier "$session_file")"; then
    echo "tier recheck  NO EVIDENCE — session rollout has no turn_context (no turns taken)"
    return 2
  fi
  local got_model="${out%|*}" got_effort="${out##*|}"
  if [[ "$got_model" == "$want_model" && "$got_effort" == "$want_effort" ]]; then
    echo "tier recheck  CONSISTENT (advisory) — a session in this workdir ran at $got_model / $got_effort"
    echo "              NOT verification: this rollout cannot be proven to belong to this launch."
    return 0
  fi
  echo "ERROR: a candidate session in this workdir ran at a DIFFERENT tier than the launch probe asserted." >&2
  echo "    expected: $want_model / $want_effort" >&2
  echo "    actual:   ${got_model:-<none>} / ${got_effort:-<unset>}" >&2
  echo "    evidence: $session_file" >&2
  echo "  Report this — it means profile resolution differs between exec and the TUI, which" >&2
  echo "  would invalidate the pre-boot gate for every Codex seat." >&2
  return 1
}

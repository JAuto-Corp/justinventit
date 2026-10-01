#!/usr/bin/env python3
"""Finite W-C1 invariant mutants against an already generated consumer.

Each mutant is a disposable script copy. The generated tests force offline curl
and scratch child homes. No live service or product state is involved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("mutation anchor must occur exactly once: " + before[:80])
    return text.replace(before, after, 1)


def early_return(text, function):
    return once(text, function + "() {\n", function + "() {\n  return 0 # mutant\n")


def append_without_lock(text):
    start = text.index("hub_append() {")
    return text[:start] + once(text[start:],
        'flock -x 200 || { echo "ERROR (hub): append lock failed" >&2; exit 3; }', ": # mutant skips transport lock")


def without_readback(text):
    lines = text.splitlines(keepends=True)
    targets = [i for i, line in enumerate(lines) if
               '_log_valid "$(tail -n 1 "$HUB_EVENT_LOG")"' in line or
               '[[ "$(_log_payload "$(tail -n 1 "$HUB_EVENT_LOG")")" == "$msg" ]]' in line]
    if len(targets) != 2:
        raise ValueError("expected exactly two authority readback guards")
    for i in targets:
        lines[i] = "    : # mutant skips readback verification\n"
    return "".join(lines)


def replay_without_comparison(text):
    pattern = r'      if \[\[ "\$\(printf.*?\]\]; then\n        exit 6\n      fi'
    changed, count = re.subn(pattern, "      : # mutant accepts conflicting replay", text, count=1, flags=re.S)
    if count != 1:
        raise ValueError("missing replay comparison")
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    script = project / "scripts/msg.sh"
    tests = project / "scripts/tests/test_msg.py"
    text = script.read_text()
    mutations = [
        ("I1-root-binding", lambda s: once(s, '.project_root == $root', 'true'),
         "test_I1_projects_restart_identity_and_independent_cursors"),
        ("F1-I1-nested-alias", lambda s: early_return(s, "_jv_check_state_paths"),
         "test_F1_I1_nested_aliases_do_not_open_or_mutate_peer"),
        ("I1-role-path", lambda s: early_return(s, "_jv_role"),
         "test_I1_unmarked_store_and_path_identifiers"),
        ("R4-I1-shared-lock", lambda s: once(s, 'HUB_APPEND_LOCK="$MAILROOT/.hub-append.lock"', 'HUB_APPEND_LOCK="$JV_STATE_ROOT/.hub-append.lock"'),
         "test_R4_I1_lock_targets_are_project_local"),
        ("I2-append-lock", append_without_lock, "test_I2_lock_refusal_has_no_unlocked_delivery"),
        ("I2-durability", lambda s: early_return(s, "_authority_barrier"), "test_I2_barrier_failure_new_and_replay"),
        ("R9-I2-readback", without_readback, "test_R9_I2_readback_failure_publishes_no_projection"),
        ("I3-conflicting-replay", replay_without_comparison, "test_I3_replay_conflicts_and_partial_projection"),
        ("I4-completion-recovery", lambda s: early_return(s, "_repair_complete_projections_locked"),
         "test_I4_completion_normalization_and_all_recovery_entries"),
        ("I5-send-arity", lambda s: once(s, '[[ $# -eq 3 || $# -eq 4 ]]', '[[ $# -ge 3 ]]'),
         "test_I5_plain_envelope_arity_and_correlation"),
        ("F2-I6-curl-defaults", lambda s: once(s, 'curl -q -sS', 'curl -sS'),
         "test_F2_F3_I6_remote_success_no_artifacts_key_only_on_stdin"),
        ("F3-I6-remote-artifacts", lambda s: once(s, 'hub:target|hub:seats|hub:open|hub:mine|hub:blocked) return 0',
                                                   'hub:target|hub:seats|hub:open|hub:mine|hub:blocked) _jv_init_store; return 0'),
         "test_F2_F3_I6_remote_success_no_artifacts_key_only_on_stdin"),
        ("R7-I6-secret-stderr", lambda s: once(s, '  HUB_DB_KEY="$(_hub_env_val HUB_SERVICE_KEY)"',
                                               '  HUB_DB_KEY="$(_hub_env_val HUB_SERVICE_KEY)"\n  printf "%s\\n" "$HUB_DB_KEY" >&2'),
         "test_F2_F3_I6_remote_success_no_artifacts_key_only_on_stdin"),
        ("F4-I5-leading-dash", lambda s: once(s, 'grep -F -- "$2" "$1"', 'grep -F "$2" "$1"'),
         "test_F4_I5_search_later_matches_dash_text_and_errors"),
        ("F4-I5-first-nonmatch", lambda s: once(s, '    1) return 0 ;;', '    1) return 1 ;;'),
         "test_F4_I5_search_later_matches_dash_text_and_errors"),
    ]
    results = []
    for name, mutate, cell in mutations:
        candidate = evidence / (name + ".sh")
        candidate.write_text(mutate(text))
        candidate.chmod(0o755)
        syntax = subprocess.run(["bash", "-n", str(candidate)], capture_output=True, text=True)
        if syntax.returncode:
            raise RuntimeError(name + " is not a valid behavioral mutant: " + syntax.stderr)
        env = {**os.environ, "JV_MSG_SCRIPT": str(candidate), "JV_MSG_PEER_SCRIPT": str(candidate)}
        run = subprocess.run([sys.executable, str(tests), "Mailbox." + cell],
                             capture_output=True, text=True, env=env, timeout=90)
        (evidence / (name + ".stdout")).write_text(run.stdout)
        (evidence / (name + ".stderr")).write_text(run.stderr)
        killed = run.returncode != 0 and "FAIL" in run.stderr and "W-C1 feature absent" not in run.stderr
        results.append({"mutant": name, "cell": cell, "status": run.returncode, "killed": killed,
                        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()})
        print(name + ": " + ("KILLED" if killed else "SURVIVED/INVALID"), flush=True)
    summary = {"source_sha256": hashlib.sha256(script.read_bytes()).hexdigest(), "results": results}
    (evidence / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    return int(not all(r["killed"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())

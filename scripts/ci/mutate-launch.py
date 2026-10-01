#!/usr/bin/env python3
"""Finite W-C2 invariant/review mutants against complete real Copier output.

Run one selected generated behavioral cell per mutant. Syntax/setup errors are
not kills; outputs, exact mutated closure and source hashes remain reviewable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('mutation anchor must occur once: ' + before[:100])
    return text.replace(before, after, 1)


def newest_probe(text):
    start = text.index('codex_seat__rollout_for_thread() {')
    end = text.index('\n}\n', start) + 3
    return text[:start] + '''codex_seat__rollout_for_thread() {
  local root="${CODEX_HOME:-$HOME/.codex}/sessions"
  find "$root" -name 'rollout-*.jsonl' -type f -printf '%T@ %p\\n' | sort -n | tail -1 | cut -d' ' -f2-
}
''' + text[end:]


def textual_trust(text):
    start = text.index('codex_seat__compare_trust() {')
    end = text.index('\n}\n', start) + 3
    return text[:start] + '''codex_seat__compare_trust() {
  grep -F -- "$2" "$1" >/dev/null && printf 'trusted\\n'
}
''' + text[end:]


def early_decision(text):
    text = once(text, 'exec 201>>"$SEAT_RECORD.lock"',
                'RECORD_EXISTS=0\n[[ ! -e "$SEAT_RECORD" ]] || RECORD_EXISTS=1\nexec 201>>"$SEAT_RECORD.lock"')
    return once(text, 'if [[ -e "$SEAT_RECORD" ]]; then', 'if (( RECORD_EXISTS )); then')


def live_field(text):
    text = once(text, '"$LETTER_LC" "$WORKTREE" >"$tuple"', '"$LETTER_LC" "$WORKTREE" "$SEAT_RECORD" >"$tuple"')
    # Binding still uses its original three fields; only model comes from a second live open.
    text = once(text, "sys.argv[2:]):", "sys.argv[2:5]):")
    return once(text, "    rec = json.load(src)\n", "    rec = json.load(src)\nwith open(sys.argv[5]) as live:\n    rec['model'] = json.load(live)['model']\n")


def cross_project_resume(text):
    return once(text, 'PRIOR_ID="$(<"$STATE_FILE")"',
                'PRIOR_ID="$(<"$JV_STATE_ROOT/alpha/sessions/$LETTER.id")"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--only', action='append', default=[])
    args = parser.parse_args()
    project, evidence = args.project.resolve(), args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    launch, codex, identity = 'scripts/role-launch.sh', 'scripts/lib/codex-seat.sh', 'scripts/lib/jv-project.sh'
    t1 = 'test_T1_positive_shared_root_and_legacy_canaries_F1'
    t2 = 'test_T2_refusal_bootstrap_and_tuple_variants'
    t3 = 'test_T3_positive_attributed_probe_and_refusal_variants'
    t4 = 'test_T4_codex_resume_guard_and_ambiguous_name_F2'
    c1 = 'test_C1_I3_literal_unique_probe_thread'
    c2 = 'test_C2_I3_I4_exact_typed_trust_and_tier'
    uuid_guard = 'if not isinstance(thread, str) or re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", thread) is None:'
    tier_compare = 'matches = isinstance(model, str) and isinstance(effort, str) and (model, effort) == tuple(sys.argv[2:4])'
    mutations = [
        ('I1-root-binding', identity, lambda s: once(s, '.project_root == $root', 'true'), 'test_T1_refusal_identity_binding_and_aliases'),
        ('I1-unqualified-resume-path', launch, lambda s: once(s, 'STATE_FILE="$SESSIONS_DIR/$LETTER.id"', 'mkdir -p "$JV_STATE_ROOT/sessions"\nSTATE_FILE="$JV_STATE_ROOT/sessions/$LETTER.id"'), t1),
        ('I1-unqualified-name', launch, lambda s: once(s, 'SEAT_NAME="$JV_PROJECT_ID-$LETTER_LC"', 'SEAT_NAME="$LETTER_LC"'), t1),
        ('I1-unqualified-profile', launch, lambda s: once(s, 'CODEX_PROFILE="$JV_PROJECT_ID-$SEAT_TIER"', 'CODEX_PROFILE="$SEAT_TIER"'), t1),
        ('I1-nested-alias', identity, lambda s: once(s, '_jv_check_state_paths() {', '_jv_check_state_paths() {\n  return 0 # mutant'), 'test_T1_refusal_identity_binding_and_aliases'),
        ('I2-decision-before-lock', launch, early_decision, 'test_T2_lock_race_and_failed_lock'),
        ('I2-seat-lock-status', launch, lambda s: once(s, "flock -x 201 || fail 'cannot acquire seat record lock'", 'flock -x 201 || true'), 'test_T2_lock_race_and_failed_lock'),
        ('I2-candidate-validation', launch, lambda s: once(s, '  node "$VALIDATOR" "$CANDIDATE" >/dev/null || fail \'candidate record schema validation failed\'', '  : # mutant skips candidate validation'), 'test_T2_bootstrap_candidate_write_validation_and_publish_failures'),
        ('I2-live-tuple-reread', launch, live_field, 'test_T2_single_image_when_original_path_is_replaced'),
        ('I2-bootstrap-override', launch, lambda s: once(s, "  (( ! BOOTSTRAP )) || fail 'record exists; bootstrap flags cannot override it'", '  : # mutant silently accepts bootstrap overrides'), t2),
        ('I3-textual-trust', codex, textual_trust, t3),
        ('I3-newest-probe-R4', codex, newest_probe, t3),
        ('I3-probe-lock-status', codex, lambda s: once(s, '    flock 200 || exit 9', '    flock 200 || true'), 'test_T1_shared_probe_lock_and_T3_lock_failure'),
        ('I3-tuple-mismatch', codex, lambda s: once(s, tier_compare, 'matches = True'), t3),
        ('I4-resume-modal', codex, lambda s: once(s, 'codex_seat_resume_guard() {', 'codex_seat_resume_guard() {\n  return 0 # mutant'), t4),
        ('I4-missing-evidence-success', launch, lambda s: once(s, '        exit 5', '        exit 0'), 'test_T4_codex_post_exit_evidence_and_statuses'),
        ('I5-permission-bypass', launch, lambda s: once(s, 'claude \\\n', 'claude --dangerously-skip-permissions \\\n'), 'test_T5_print_only_boot_and_neutral_runtime_policy'),
        ('I5-fabricated-capability', launch, lambda s: once(s, "'capabilities': {}", "'capabilities': {'hooks': {'value': True, 'probed_at': '2026-07-28T00:00:00Z'}}"), 'test_T2_positive_bootstrap_and_exact_record_tuple'),
        ('F2-ambiguous-resume-fallback', launch, lambda s: once(s, '"$CODEX_BIN" resume "$CODEX_THREAD" --profile "$CODEX_PROFILE" || EXIT_CODE=$?', '"$CODEX_BIN" resume "$CODEX_THREAD" --profile "$CODEX_PROFILE" || "$CODEX_BIN" --profile "$CODEX_PROFILE" || EXIT_CODE=$?'), t4),
        ('R1-cross-project-resume', launch, cross_project_resume, t1),
        ('R2-unqualified-rename', launch, lambda s: once(s, '/rename $SEAT_NAME', '/rename $LETTER_LC'), t1),
        ('R3-any-trusted-project', codex, lambda s: once(s, 'entry = projects.get(sys.argv[2]) if isinstance(projects, dict) else None', 'entry = next(iter(projects.values()), None) if isinstance(projects, dict) else None'), t3),
        ('R5-external-command', launch, lambda s: once(s, 'FRESH=0; AT_MACHINE=0; BOOTSTRAP=0', 'tmux list-sessions || true\nFRESH=0; AT_MACHINE=0; BOOTSTRAP=0'), 'test_T2_positive_bootstrap_and_exact_record_tuple'),
        ('C1-UUID-validation', codex, lambda s: once(s, uuid_guard, 'if not isinstance(thread, str):'), c1),
        ('C1-rollout-uniqueness', codex, lambda s: once(s, 'if len(hits) != 1:', 'if not hits:'), c1),
        ('C1-event-uniqueness', codex, lambda s: once(s, 'if len(threads) != 1:', 'if not threads:'), c1),
        ('C2-trust-newline', codex, lambda s: once(s, 'level == "trusted"', 'level.rstrip("\\n") == "trusted"'), c2),
        ('C2-effort-newline', codex, lambda s: once(s, tier_compare, tier_compare.replace('(model, effort)', '(model, effort.rstrip("\\n"))')), c2),
        ('C2-model-coercion', codex, lambda s: once(s, tier_compare, 'matches = isinstance(effort, str) and (str(model), effort) == tuple(sys.argv[2:4])'), c2),
    ]
    if args.only:
        unknown = set(args.only) - {m[0] for m in mutations}
        if unknown:
            raise ValueError('unknown mutants: ' + repr(sorted(unknown)))
        mutations = [m for m in mutations if m[0] in args.only]
    results = []
    for name, rel, mutate, cell in mutations:
        consumer = evidence / name / 'consumer'
        shutil.copytree(project, consumer)
        target = consumer / rel
        target.write_text(mutate(target.read_text()))
        syntax = subprocess.run(['bash', '-n', str(target)], capture_output=True, text=True)
        if syntax.returncode:
            raise RuntimeError(name + ' invalid syntax: ' + syntax.stderr)
        env = {**os.environ, 'JV_LAUNCH_PROJECT': str(consumer), 'JV_LAUNCH_PEER': str(consumer), 'PYTHONDONTWRITEBYTECODE': '1'}
        run = subprocess.run([sys.executable, str(consumer / 'scripts/tests/test_launch.py'), 'Launch.' + cell],
                             capture_output=True, text=True, env=env, timeout=120)
        (evidence / (name + '.stdout')).write_text(run.stdout)
        (evidence / (name + '.stderr')).write_text(run.stderr)
        assertion = re.search(r'^FAIL: ', run.stderr, re.M) is not None
        setup_error = 'W-C2 feature-absence' in run.stderr or 'refuse to execute coupled/missing' in run.stderr
        errors = re.search(r'^ERROR: ', run.stderr, re.M) is not None
        killed = run.returncode != 0 and assertion and not setup_error and not errors
        results.append({'mutant': name, 'file': rel, 'cell': cell, 'status': run.returncode,
                        'killed': killed, 'assertion_failure': assertion, 'test_error': errors,
                        'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        print(name + ': ' + ('KILLED' if killed else 'SURVIVED/INVALID'), flush=True)
    summary = {'source': str(project), 'source_sha256': {r: hashlib.sha256((project / r).read_bytes()).hexdigest()
                                                      for r in (launch, codex, identity)}, 'results': results}
    (evidence / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    return int(not all(r['killed'] for r in results))


if __name__ == '__main__':
    raise SystemExit(main())

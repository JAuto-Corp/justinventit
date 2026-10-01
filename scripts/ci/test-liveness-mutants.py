#!/usr/bin/env python3
"""Finite W-C3 witnesses: 26 SPEC, four RED folds, one I3 edge, four code folds.

Only disposable rendered copies are mutated. The trusted effect/source gate
runs before every syntax or test child; unsafe effect seeds are never executed.
Containment refusals and harness-assertion kills remain distinct from runtime
behavioral kills. Syntax/setup errors are never kills.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'template/scripts/tests'))
from liveness_guard import runtime_findings, CLOSURE, OPTIONAL_HELPERS
from liveness_fixture import ALLOWED

ENGINE='scripts/lib/jv-liveness.py'
SHARED='scripts/lib/jv-project.sh'
BOUNDARY='scripts/lib/jv-liveness.sh'
GUARD='scripts/tests/liveness_guard.py'
# (name, file, exact old/new replacement, selected witness, result class)
MUTANTS=[
 ('binding',SHARED,"'.project_id == $id and .project_root == $root'","'true'",'t1_identity_alias_and_legacy_refusals','runtime'),
 ('unqualified-cadence',ENGINE,"path=store/'cadence'/(role+'.txt')","path=store.parent/'beta'/'cadence'/(role+'.txt')",'t1_project_isolation_and_worktree','runtime'),
 ('nested-alias',SHARED,'_jv_check_state_paths() {','_jv_check_state_paths() {\n  return 0','t1_identity_alias_and_legacy_refusals','runtime'),
 ('writer-lock',ENGINE,"def locked(path):\n    with", "def locked(path):\n    yield\n    return\n    with",'t2_writer_lock_and_read_inside_lock','runtime'),
 ('heartbeat-intent',ENGINE,"data={**old,'heartbeat_at':stamp(now)}","data={**old,'heartbeat_at':stamp(now),'conclusion':'','brief':''}",'t2_cadence_shapes_and_hook_preserve_intent','runtime'),
 ('invalid-candidate',ENGINE,'        validate(data,role)\n        atomic',"        data['wake_count']='broken'\n        atomic",'t2_cadence_shapes_and_hook_preserve_intent','runtime'),
 ('records-only',ENGINE,'roles=sorted(records|cadences)','roles=sorted(records)','t3_roster_union_and_independent_schedule_floor','runtime'),
 ('stale-none',ENGINE,"    try:\n        if registered:","    if 'next_wake_at: none' in path.read_text():return row\n    try:\n        if registered:",'t3_unknown_dormancy_and_later_seat','runtime'),
 ('heartbeat-floor',ENGINE,"if now-epoch(data['heartbeat_at'])>3600:",'if False:','t3_f4_exact_schedule_and_floor_thresholds','runtime'),
 ('silence-unknown',ENGINE,"row['reasons'].append('invalid-cadence');row['_unknown']=True","return {**row,'reasons':[],'_unknown':False}",'t3_unknown_dormancy_and_later_seat','runtime'),
 ('newest-mail',ENGINE,'min(oldest,ts)','max(oldest,ts)','t4_oldest_streams_broadcast_and_no_consumption','runtime'),
 ('shared-cursor',ENGINE,"role+'-'+path.stem+'.offset'","role+'-from-i-to-a.offset'",'t4_oldest_streams_broadcast_and_no_consumption','runtime'),
 ('process-project',ENGINE,"env.get('JV_PROJECT_ID')==os.environ['JV_PROJECT_ID'] and",'True and','t4_process_exact_identity_interactive_and_idle_standby','runtime'),
 ('one-shot-runtime',ENGINE,"    if not argv:return False","    if argv and Path(argv[0]).name in {'codex','claude'}:return True\n    if not argv:return False",'t4_process_exact_identity_interactive_and_idle_standby','runtime'),
 ('episode-key',ENGINE,"episode=previous['episode'] if previous else uuid.uuid4().hex",'episode=uuid.uuid4().hex','t5_backoff_stable_episode_recovery_and_dormancy','runtime'),
 ('never-realert',ENGINE,"if previous and now-previous['last_alert']<interval:",'if previous:','t5_backoff_stable_episode_recovery_and_dormancy','runtime'),
 ('retain-recovery',ENGINE,"if not row['_unknown'] and not dry:path.unlink(missing_ok=True)",'if False:path.unlink(missing_ok=True)','t5_backoff_stable_episode_recovery_and_dormancy','runtime'),
 ('checkpoint-before-append',ENGINE,"    with (store/'watchdog/alerts.jsonl').open('a') as output:","    atomic(path,json.dumps({'episode':episode,'count':min(count+1,1000000),'last_alert':now})+'\\n')\n    with (store/'watchdog/alerts.jsonl').open('a') as output:",'t5_concurrent_sweeps_and_failed_output','runtime'),
 ('dry-run-writes',ENGINE,'dry=bool(args);watchdog=', 'dry=False;watchdog=','t5_dry_run_never_writes_stall_or_recovery','runtime'),
 ('legacy-external-effect','scripts/pacemaker.sh','set -euo pipefail','set -euo pipefail\nif /usr/bin/tmux send-keys x; then :; fi',None,'source-refusal'),
 ('silent-wrapper','.claude/hooks/stop/actions/heartbeat-writer.sh','#!/usr/bin/env bash','#!/usr/bin/env bash\nexit 0','t2_cadence_shapes_and_hook_preserve_intent','runtime'),
 ('F1-upgrade-refusal',BOUNDARY,'if [[ -v "$key" ]]; then','if false; then','t7_f1_updated_consumer_refuses_legacy_knobs','runtime'),
 ('F2-inclusive-backlog',ENGINE,'if age>1800:','if age>=1800:','t4_f2_strict_backlog_process_independent','runtime'),
 ('F3-absent-cursor',ENGINE,'        offset=integer(cursor.read_text().strip()) if cursor.exists() else 0',"        if not cursor.exists():raise ValueError('virgin cursor treated as unknown')\n        offset=integer(cursor.read_text().strip()) if cursor.exists() else 0",'t4_f3_virgin_cursor_vs_unknown','runtime'),
 ('F4-schedule-detector',ENGINE,"if now-epoch(data['next_wake_at'])>=row['grace']:",'if False:','t3_f4_exact_schedule_and_floor_thresholds','runtime'),
 ('F5-gate-bypass',GUARD,'    return findings','    return []','t6_f5_source_gate_positive_and_refusals','harness'),
 ('R1-compound-absolute-guard',GUARD,
  r'''(?:^|[;&|()]|\b(?:if|elif|then|do|while|until|else))\s*(?:!\s*)?(?:(?:builtin|command|exec)\s+)?[\"\']?(?:/[^\s\"\']*/)?''',
  r'''(?:^|[;&|()]|\bthen|\bdo)\s*(?:(?:builtin|command|exec)\s+)?''','t6_f5_source_gate_positive_and_refusals','harness'),
 ('R2-helper-closure',GUARD,", '.claude/hooks/lib/utils.sh'",'', 't6_f5_source_gate_positive_and_refusals','harness'),
 ('R3-foreign-read',ENGINE,'def decision(store,role,registered,now):',"def decision(store,role,registered,now):\n    for foreign in store.parent.iterdir():\n        if foreign!=store:\n            for item in foreign.rglob('*'):\n                if item.is_file():item.read_bytes()",'t1_project_isolation_and_worktree','runtime'),
 ('I3-malformed-roster',ENGINE,'if roster.exists() and not roster.is_dir():','if False:','t3_unknown_dormancy_and_later_seat','runtime'),
 ('R4-legacy-read',BOUNDARY,'    _jv_fail "migration required:', '''    if [[ -f "${!key}" ]]; then cat -- "${!key}" >/dev/null; fi
    if [[ -d "${!key}" ]]; then find "${!key}" -type f -exec cat {} \\; >/dev/null; fi
    _jv_fail "migration required:''','t7_f1_updated_consumer_refuses_legacy_knobs','runtime'),
 ('C1-mail-identity',ENGINE,"event.get('project_id')!=os.environ['JV_PROJECT_ID']",'False','c1_mail_event_identity','runtime'),
 ('C2-mail-senders',ENGINE,'[A-Za-z][A-Za-z0-9_]{0,63}','[a-z]','c2_wc1_sender_grammar_and_cursors','runtime'),
 ('C3-informational-argv',ENGINE,"        elif arg.startswith('-'):return False","        elif arg.startswith('-'):continue",'c3_full_interactive_argv','runtime'),
 ('C4-cadence-splitlines',ENGINE,"text.removesuffix('\\n').split('\\n')",'text.splitlines()','c4_cadence_lf_roundtrip','runtime'),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--green-evidence',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    green=args.green_evidence.resolve();out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((green/'upgrade-receipt.json').read_text())
    sources=[green/'scratch/consumer alpha',green/'scratch/consumer beta',Path(receipt['updated_consumer'])]
    if json.loads((green/'result.json').read_text())['failed']:raise SystemExit('baseline must pass before mutants')
    for root in sources:
        assert not runtime_findings(root),'unsafe baseline closure'
    binpath=out/'bin';binpath.mkdir();home=out/'home';home.mkdir();tmp=out/'tmp';tmp.mkdir()
    for name in ALLOWED:
        native=shutil.which(name)
        if native:(binpath/name).symlink_to(native)
    env={'PATH':str(binpath),'HOME':str(home),'TMPDIR':str(tmp),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
         'PYTHONDONTWRITEBYTECODE':'1'}
    results=[]
    for name,rel,old,new,witness,kind in MUTANTS:
        directory=out/name;directory.mkdir();projects=[]
        for n,source in enumerate(sources):
            dst=directory/str(n);shutil.copytree(source,dst,ignore=shutil.ignore_patterns('.git','__pycache__'))
            p=dst/rel;text=p.read_text();assert old in text,(name,rel,'anchor absent')
            p.write_text(text.replace(old,new));projects.append(dst)
        # Trusted gate lives outside the mutated copies, including for guard mutants.
        findings=[{'project':i,**f} for i,p in enumerate(projects) for f in runtime_findings(p)]
        (directory/'source-gate.json').write_text(json.dumps(findings,indent=2)+'\n')
        if kind=='source-refusal':
            assert findings and any(f['check']=='external-effect' for f in findings)
            result={'name':name,'class':kind,'outcome':'refused-before-child','executed':False}
        else:
            if findings:raise RuntimeError(name+': unexpected source gate failure, not a runtime kill')
            for project in projects:
                for operating in (*CLOSURE,*OPTIONAL_HELPERS,GUARD):
                    path=project/operating
                    if not path.is_file():continue
                    if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
                    elif path.suffix=='.sh':
                        p=subprocess.run(['bash','-n',str(path)],env=env,capture_output=True,text=True,timeout=5)
                        if p.returncode:raise RuntimeError(name+': syntax failure is not a kill: '+p.stderr)
            mutant_receipt={**receipt,'updated_consumer':str(projects[2])}
            receipt_path=directory/'upgrade-receipt.json';receipt_path.write_text(json.dumps(mutant_receipt)+'\n')
            childenv={**env,'JV_LIVENESS_PROJECT':str(projects[0]),'JV_LIVENESS_PEER':str(projects[1]),
                      'JV_LIVENESS_UPGRADE_RECEIPT':str(receipt_path)}
            selected=('Containment.' if kind=='harness' else 'Liveness.')+'test_'+witness
            # Recheck at the child boundary, not merely when the mutation was made.
            assert not any(runtime_findings(p) for p in projects)
            p=subprocess.run([sys.executable,projects[0]/'scripts/tests/test_liveness.py',selected],
                             env=childenv,cwd=projects[0],capture_output=True,text=True,timeout=90)
            (directory/'stdout').write_text(p.stdout);(directory/'stderr').write_text(p.stderr)
            errors=re.search(r'errors=(\d+)',p.stderr)
            failures=re.search(r'failures=(\d+)',p.stderr)
            killed=p.returncode==1 and failures and int(failures[1])>0 and not errors and 'FAIL:' in p.stderr
            result={'name':name,'class':kind,'witness':selected,'status':p.returncode,
                    'outcome':'assertion-killed' if killed else 'SURVIVED-OR-INVALID',
                    'errors':int(errors[1]) if errors else 0,
                    'failures':int(failures[1]) if failures else 0}
        result['changed_file']=rel
        result['mutated_sha256']=hashlib.sha256((projects[0]/rel).read_bytes()).hexdigest()
        results.append(result)
        (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(name+': '+result['outcome'],flush=True)
    failed=[r for r in results if r['outcome']=='SURVIVED-OR-INVALID']
    print(json.dumps({'mutants':len(results),'failed':failed},indent=2))
    return int(bool(failed))


if __name__=='__main__':raise SystemExit(main())

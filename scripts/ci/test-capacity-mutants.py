#!/usr/bin/env python3
"""W-C4 finite SPEC and RED-review witnesses; mutate disposable renders only.

Trusted source checks precede every child. Unsafe effects stay data; syntax or
fixture errors never count as kills. Harness and runtime results stay distinct.
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

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'template/scripts/tests'))
from capacity_guard import runtime_findings, CLOSURE
from capacity_fixture import CAPACITY_ALLOWED

LOCK='scripts/build-lock.sh'
GUARD='scripts/tests/capacity_guard.py'
FIXTURE='scripts/tests/capacity_fixture.py'
# Each exact mutation is traced to the fixed SPEC list or a RED review finding.
MUTANTS=[
 ('binding',LOCK,'_jv_verify_store\n',': # bypass binding\n','t1_binding_and_legacy_refusal','runtime'),
 ('project-lock',LOCK,'LOCK_FILE="$LOCK_DIR/build.lock"','LOCK_FILE="$LOCK_DIR/$JV_PROJECT_ID.lock"','r4_python_canonical_owner','runtime'),
 ('skip-flock',LOCK,'  flock -n -E 75 "$LOCK_FD" || rc=$?','  : # no kernel acquisition','r4_python_canonical_owner','runtime'),
 ('metadata-authority',LOCK,'  flock -n -E 75 "$LOCK_FD" || rc=$?',
  '  if [[ "$(read_info held_at_epoch)" == 1 ]]; then :; else flock -n -E 75 "$LOCK_FD" || rc=$?; fi',
  't2_contention_metadata_and_inode','runtime'),
 ('cleanup-unlocks',LOCK,'    # Never flock-unlock or delete the inode:',
  '    flock -u "$LOCK_FD"\n    # Never flock-unlock or delete the inode:',
  't3_crash_background_and_node_lifetime','runtime'),
 ('drop-fd',LOCK,'  JV_BUILD_LOCK_FD="$LOCK_FD" "$@" || rc=$?',
  '  exec {LOCK_FD}>&-\n  "$@" || rc=$?','t3_crash_background_and_node_lifetime','runtime'),
 ('trust-marker',LOCK,'verify_inherited_fd() {','verify_inherited_fd() {\n  return 0',
  't4_spoofed_descriptors','runtime'),
 ('omit-owning-description',LOCK,'  flock -n -E 75 "$fd" ||', '  true ||',
  't4_spoofed_descriptors','runtime'),
 ('nested-unlock',LOCK,'    printf \'build-lock: nested command completed',
  '    if [[ "$rc" != 0 ]]; then flock -u "$JV_BUILD_LOCK_FD"; fi\n    printf \'build-lock: nested command completed',
  't4_nested_same_and_cross_project','runtime'),
 ('memory-boundary',LOCK,'available < MIN_MEM_MB','available <= MIN_MEM_MB',
  't5_memory_boundaries_and_unknown','runtime'),
 ('swallow-command-status',LOCK,'  return "$rc"\n}', '  return 0\n}',
  't5_f3_io_foreground_both_entries','runtime'),
 ('admit-metadata-failure',LOCK,"  write_info || fail 'cannot publish holder metadata'",'  write_info || true',
  't5_metadata_and_open_faults','runtime'),
 ('status-creates',LOCK,'do_status() {','do_status() {\n  mkdir -p -- "$LOCK_DIR"',
  't6_status_readonly_absent_and_held','runtime'),
 ('delete-inode',LOCK,'  exit "$rc"\n}', '  rm -f -- "$LOCK_FILE"\n  exit "$rc"\n}',
  't2_contention_metadata_and_inode','runtime'),
 ('bypass-gate',GUARD,'    return findings','    return []',
  't7_gate_positive_and_refusals','harness'),
 ('forbidden-recovery',LOCK,'set -euo pipefail','set -euo pipefail\nenv /bin/kill -TERM "$pid"',None,'source-refusal'),
 ('F2-probe-error',LOCK,'  [[ "$rc" == 75 ]] ||','  [[ "$rc" != 0 ]] ||',
  't4_f2_probe_error_is_not_conflict','runtime'),
 # Former regex mutants now open the equivalent single admission hole. These
 # mutated guards inspect DATA ONLY; the trusted outer gate is never weakened.
 ('R1-extra-helper',GUARD,'        if digest not in permitted:',
  '        if digest not in permitted and b\'source "$SCRIPT_DIR/lib/extra.sh"\' not in body:',
  'r1_r2_closure_wrapped_effects_and_host_opens','harness'),
 ('R1-wrapped-effect',GUARD,'        if digest not in permitted:',
  "        if digest not in permitted and b'env X=1 tmux' not in body:",
  'r1_r2_closure_wrapped_effects_and_host_opens','harness'),
 ('R2-host-open',GUARD,'        if digest not in permitted:',
  "        if digest not in permitted and b'../capacity.lock' not in body:",
  'r1_r2_closure_wrapped_effects_and_host_opens','harness'),
 ('R2-native-flock',FIXTURE,
  'if not fd.isdecimal() or not target or not pathlib.Path(target).resolve().is_relative_to(root):',
  'if False:', 'r2_native_flock_boundary','harness'),
 ('R3-inode-check',LOCK,'  [[ "$fd_identity" == "$lock_identity" ]] ||','  true ||',
  't4_spoofed_descriptors','runtime'),
 ('R4-other-common-inode',LOCK,'LOCK_FILE="$LOCK_DIR/build.lock"','LOCK_FILE="$LOCK_DIR/other.lock"',
  'r4_python_canonical_owner','runtime'),
 ('C1-unknown-image',GUARD,'        if digest not in permitted:',
  '        if False:', 'c1_closed_world_unknown_edges','harness'),
 ('C2-unsearchable-ancestor',LOCK,
  '    [[ ! -d "$path" || -x "$path" ]] || fail \'host directory is not searchable\'\n',
  '', 'c2_unsearchable_ancestor_is_unknown','runtime'),
 ('C3-false-held',LOCK,"1) printf 'build-lock: unheld\\n'", "1) printf 'build-lock: held\\n'",
  't6_status_readonly_absent_and_held','runtime'),

]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--green-evidence',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();green=args.green_evidence.resolve();out=args.evidence.resolve()
    assert not json.loads((green/'result.json').read_text())['failed'],'baseline must pass'
    sources=[green/'scratch/consumer alpha',green/'scratch/consumer beta']
    assert not any(runtime_findings(p) for p in sources),'unsafe baseline'
    out.mkdir(parents=True,exist_ok=False)
    binpath=out/'bin';binpath.mkdir();home=out/'home';home.mkdir();tmp=out/'tmp';tmp.mkdir()
    for name in CAPACITY_ALLOWED:
        native=shutil.which(name)
        if native:(binpath/name).symlink_to(native)
    env={'PATH':str(binpath),'HOME':str(home),'TMPDIR':str(tmp),'LANG':'C.UTF-8',
         'LC_ALL':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
    results=[]
    for name,rel,old,new,witness,kind in MUTANTS:
        directory=out/name;directory.mkdir();projects=[]
        for i,source in enumerate(sources):
            dst=directory/str(i);shutil.copytree(source,dst,ignore=shutil.ignore_patterns('.git','__pycache__'))
            path=dst/rel;body=path.read_text();assert old in body,(name,'missing mutation anchor')
            path.write_text(body.replace(old,new));projects.append(dst)
        # This imported guard is trusted and outside every mutant copy.
        findings=[{'project':i,**f} for i,p in enumerate(projects) for f in runtime_findings(p)]
        (directory/'source-gate.json').write_text(json.dumps(findings,indent=2)+'\n')
        if kind=='source-refusal':
            assert findings and any(f['check']=='undeclared-executable-image' for f in findings)
            result={'name':name,'class':kind,'outcome':'refused-before-child','executed':False}
        else:
            assert not findings,(name,'source refusal cannot count as behavioral kill',findings)
            for p in projects:
                for operating in (*CLOSURE,GUARD,FIXTURE):
                    path=p/operating
                    if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
                    else:
                        syntax=subprocess.run(['bash','-n',path],env=env,capture_output=True,text=True,timeout=5)
                        assert syntax.returncode==0,(name,'syntax failure is not a kill',syntax.stderr)
            selected=('Containment.' if kind=='harness' else 'Capacity.')+'test_'+witness
            childenv={**env,'JV_CAPACITY_PROJECT':str(projects[0]),'JV_CAPACITY_PEER':str(projects[1]),
                      'JV_CAPACITY_EVIDENCE':str(directory/'lifetime.jsonl')}
            assert not any(runtime_findings(p) for p in projects)
            result_run=subprocess.run([sys.executable,projects[0]/'scripts/tests/test_capacity.py',selected],
                                      env=childenv,cwd=projects[0],capture_output=True,text=True,timeout=90)
            (directory/'stdout').write_text(result_run.stdout);(directory/'stderr').write_text(result_run.stderr)
            errors=re.search(r'errors=(\d+)',result_run.stderr);failures=re.search(r'failures=(\d+)',result_run.stderr)
            killed=result_run.returncode==1 and failures and int(failures[1])>0 and not errors and 'FAIL:' in result_run.stderr
            result={'name':name,'class':kind,'witness':selected,'status':result_run.returncode,
                    'outcome':'assertion-killed' if killed else 'SURVIVED-OR-INVALID',
                    'errors':int(errors[1]) if errors else 0,'failures':int(failures[1]) if failures else 0}
        result.update(changed_file=rel,mutated_sha256=hashlib.sha256((projects[0]/rel).read_bytes()).hexdigest())
        results.append(result);(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(name+': '+result['outcome'],flush=True)
    failed=[r for r in results if r['outcome']=='SURVIVED-OR-INVALID']
    print(json.dumps({'mutants':len(results),'failed':failed},indent=2))
    return int(bool(failed))


if __name__=='__main__':raise SystemExit(main())

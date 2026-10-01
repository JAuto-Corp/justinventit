#!/usr/bin/env python3
"""W-C5 finite admitted witnesses on disposable real renders; errors are not kills."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'template/scripts/tests'))
from observability_guard import CLOSURE, runtime_findings
from observability_fixture import OBSERVABILITY_ALLOWED

CORE='scripts/lib/jv-observability.py'
SHELL='scripts/lib/jv-observability.sh'
MUTANTS=[
 ('binding',SHELL,'_jv_verify_store\n',': # bypass binding\n','t1_binding_and_paths','runtime'),
 ('home-fallback',CORE,"        if key not in os.environ:continue", "        if key not in os.environ:os.environ[key]=str(Path(os.environ['HOME'])/('anthropic.json' if label=='anthropic' else 'sessions'))",'t1_no_home_fallback','runtime'),
 ('malformed-zero',CORE,'used=number(value);','used=number(0 if value is None else value);','t2_formats_stale_and_invalid','runtime'),
 ('prompt-data',CORE,"                limits=record.get('rate_limits')", "                if 'content' in record:record=json.loads(record['content'])\n                limits=record.get('rate_limits')",'t2_formats_stale_and_invalid','runtime'),
 ('ignore-age',CORE,"'stale':age>1800", "'stale':False",'t2_formats_stale_and_invalid','runtime'),
 ('pace-equality',CORE,'abs(delta)<=10','abs(delta)<10','t3_pacing_and_credit_units','runtime'),
 ('reset-filter',CORE," and p[3]==reset",'','t3_reset_and_fresh_precedence','runtime'),
 ('credit-quota',CORE,"if row['series']=='openai-credits':fresh.append", "if row['series']=='openai-credits':\n            row.update(quota(row['series'],row['balance'],0,0,0,now));fresh.append",'t3_pacing_and_credit_units','runtime'),
 ('old-over-fresh',CORE,"        credit=row['series']=='openai-credits'", "        for point in prior:\n            if point[1]==row['series'] and 'used' in row:row['used']=point[2]\n        credit=row['series']=='openai-credits'",'t3_reset_and_fresh_precedence','runtime'),
 ('ignore-lock',CORE,"                time.sleep(.02)\n        yield", "                time.sleep(.02)\n            except OSError:break\n        yield",'t4_persistence_faults','runtime'),
 ('project-suppression',CORE,"[day,str(target),row['metric'],bucket]", "[day,str(target),row['metric'],bucket,os.environ['JV_PROJECT_ID']]",'t4_shared_suppression_and_concurrency','runtime'),
 ('disk-equality',CORE,'due=value>=85','due=value>85','t5_thresholds_and_no_cleanup','runtime'),
 ('premature-checkpoint',CORE,'                notify(directory,row)\n                checkpoint(state,keys+[key]);keys.append(key)', '                checkpoint(state,keys+[key]);keys.append(key)\n                notify(directory,row)','t6_adapter_failure_and_retry','runtime'),
 ('other-seat-hook','scripts/usage-hook.sh','[[ "${JV_ROLE:-}" == [oO] ]] || exit 0',': # no role filter','t6_bound_other_seat_no_access','runtime'),
 ('source-purge','scripts/disk-watch.sh','set -euo pipefail','set -euo pipefail\nrm -f -- "$JV_DISK_SECONDARY_ROOT"/wsl-crash-*.dmp',None,'source-refusal'),
 ('F3-primary-weekly',CORE,'if minutes==10080:',"if key=='primary':",'f3_two_windows','runtime'),
 ('F4-display-name',CORE,"series='anthropic-model-'+hashlib.sha256(name.encode()).hexdigest()","series='anthropic-model-'+name",'f4_label_canary','runtime'),
 ('F5-abort-providers',CORE,"except (OSError,ValueError,TypeError,KeyError,AttributeError,Unavailable):errors.append(label+'-unavailable')", "except (OSError,ValueError,TypeError,KeyError,AttributeError,Unavailable):raise Unavailable('provider-failed')",'f5_mixed_providers','runtime'),
 ('F5-secondary-first',CORE,"    observations=[]\n    for label,envkey", "    checked(os.environ.get('JV_DISK_SECONDARY_ROOT'),'dir')\n    observations=[]\n    for label,envkey",'f5_bad_secondary','runtime'),
 ('F6-no-min-span',CORE,'pts[-1][0]-pts[0][0]>=1800','pts[-1][0]-pts[0][0]>0','f6_burn_limits','runtime'),
 ('F6-no-cutoff',CORE,'now-10800<=p[0]<=now','p[0]<=now','f6_burn_limits','runtime'),
 ('F7-read-all',CORE,'        source.seek(offset)\n        data=source.read(min(size,cap))','        source.seek(0)\n        data=source.read()[-cap:] if tail else source.read(min(size,cap))','f7_read_budget','runtime'),
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
    for name in OBSERVABILITY_ALLOWED:
        native=shutil.which(name)
        if native:(binpath/name).symlink_to(native)
    env={'PATH':str(binpath),'HOME':str(home),'TMPDIR':str(tmp),'LANG':'C.UTF-8',
         'LC_ALL':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
    results=[]
    for name,rel,old,new,witness,kind in MUTANTS:
        directory=out/name;directory.mkdir();projects=[]
        for i,source in enumerate(sources):
            dst=directory/str(i);shutil.copytree(source,dst,ignore=shutil.ignore_patterns('.git','__pycache__'))
            path=dst/rel;body=path.read_text();assert body.count(old)==1,(name,'ambiguous mutation anchor')
            path.write_text(body.replace(old,new));projects.append(dst)
        findings=[{'project':i,**f} for i,p in enumerate(projects) for f in runtime_findings(p)]
        (directory/'source-gate.json').write_text(json.dumps(findings,indent=2)+'\n')
        (directory/'mutation.json').write_text(json.dumps({'file':rel,'before':old,'after':new,'witness':witness},indent=2)+'\n')
        if kind=='source-refusal':
            assert findings and any(f['check']=='unknown-image' for f in findings)
            result={'name':name,'class':kind,'outcome':'refused-before-child','executed':False}
        else:
            assert not findings,(name,'source refusal cannot count as behavioral kill',findings)
            for p in projects:
                for operating in CLOSURE:
                    path=p/operating
                    if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
                    else:
                        syntax=subprocess.run(['bash','-n',path],env=env,capture_output=True,text=True,timeout=5)
                        assert syntax.returncode==0,(name,'syntax failure is not a kill',syntax.stderr)
            selected='Observability.test_'+witness
            childenv={**env,'JV_OBSERVABILITY_PROJECT':str(projects[0]),'JV_OBSERVABILITY_PEER':str(projects[1])}
            assert not any(runtime_findings(p) for p in projects)
            child=subprocess.run([sys.executable,projects[0]/'scripts/tests/test_observability.py',selected],
                                 env=childenv,cwd=projects[0],capture_output=True,text=True,timeout=90)
            (directory/'stdout').write_text(child.stdout);(directory/'stderr').write_text(child.stderr)
            errors=re.search(r'errors=(\d+)',child.stderr);failures=re.search(r'failures=(\d+)',child.stderr)
            killed=child.returncode==1 and failures and int(failures[1])>0 and not errors and 'FAIL:' in child.stderr
            result={'name':name,'class':kind,'witness':selected,'status':child.returncode,
                    'outcome':'assertion-killed' if killed else 'SURVIVED-OR-INVALID',
                    'errors':int(errors[1]) if errors else 0,'failures':int(failures[1]) if failures else 0}
        result.update(changed_file=rel,mutated_sha256=hashlib.sha256((projects[0]/rel).read_bytes()).hexdigest())
        results.append(result);(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(name+': '+result['outcome'],flush=True)
    failed=[r for r in results if r['outcome']=='SURVIVED-OR-INVALID']
    print(json.dumps({'mutants':len(results),'failed':failed},indent=2))
    return int(bool(failed))


if __name__=='__main__':raise SystemExit(main())

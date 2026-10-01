#!/usr/bin/env python3
"""W-C4: task-disabled real Copier consumers, then contained capacity cells."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'template/scripts/tests'))
from capacity_guard import render_findings, runtime_findings
from capacity_fixture import CAPACITY_ALLOWED


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template',type=Path,default=ROOT)
    parser.add_argument('--copier',default='copier')
    parser.add_argument('--evidence',type=Path)
    args=parser.parse_args();template=args.template.resolve()
    out=args.evidence.resolve() if args.evidence else Path(tempfile.mkdtemp(prefix='jv-capacity-evidence-'))
    if args.evidence:out.mkdir(parents=True,exist_ok=False)
    scratch=out/'scratch';scratch.mkdir()
    home=scratch/'home';home.mkdir();binpath=scratch/'bin';binpath.mkdir();tmp=scratch/'tmp';tmp.mkdir()
    for name in (*CAPACITY_ALLOWED,'git'):
        native=shutil.which(name)
        if native:(binpath/name).symlink_to(native)
    env={'PATH':str(binpath),'HOME':str(home),'TMPDIR':str(tmp),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
         'PYTHONDONTWRITEBYTECODE':'1','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
         'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_COUNT':'3','GIT_CONFIG_KEY_0':'core.hooksPath',
         'GIT_CONFIG_VALUE_0':'/dev/null','GIT_CONFIG_KEY_1':'protocol.allow','GIT_CONFIG_VALUE_1':'never',
         'GIT_CONFIG_KEY_2':'protocol.file.allow','GIT_CONFIG_VALUE_2':'always'}
    commands=[];gates=[]
    def run(label,argv,check=True,**kwargs):
        argv=list(map(str,argv))
        r=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=kwargs.pop('timeout',120),**kwargs)
        (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
        commands.append({'label':label,'argv':argv,'status':r.returncode})
        (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        print(label+': exit '+str(r.returncode),flush=True)
        if check and r.returncode:raise RuntimeError(label+' failed; retained logs')
        return r
    try:
        copier=shutil.which(args.copier)
        if not copier:raise RuntimeError('Copier 9.17.1 required')
        assert run('copier-version',[copier,'--version']).stdout.strip()=='copier 9.17.1'
        head=run('source-head',['git','-C',template,'rev-parse','HEAD']).stdout.strip()
        archive=subprocess.run(['git','-C',str(template),'archive','--format=tar',head],env=env,capture_output=True,timeout=60)
        assert archive.returncode==0
        source=scratch/'pinned-source';source.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:tar.extractall(source,filter='data')
        projects=[]
        for name,tier in (('alpha','cluster'),('beta','solo')):
            # Recheck actual pinned render inputs before EVERY Copier process.
            findings=render_findings((source/'copier.yml').read_text())
            gates.append({'label':'render-'+name,'candidate':head,'render_findings':findings,
                          'runtime_findings':runtime_findings(source/'template'),
                          'scope':'data-only render; tasks disabled; runtime independently gated'})
            (out/'pre-execution-gates.json').write_text(json.dumps(gates,indent=2)+'\n')
            assert not findings,'executable/coupled render input'
            project=scratch/('consumer '+name)
            run('render-'+name,[copier,'copy','--defaults','--skip-tasks','--vcs-ref='+head,
                               '-d','project_name=Capacity '+name,'-d','orchestration_tier='+tier,
                               '-d','database=none','-d','db_adapter=none','-d','testing=none',template,project])
            projects.append(project)
        hashes={str(p.relative_to(scratch)):hashlib.sha256(p.read_bytes()).hexdigest()
                for root in projects for p in root.rglob('*') if p.is_file()}
        (out/'rendered-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        env.update(JV_CAPACITY_PROJECT=str(projects[0]),JV_CAPACITY_PEER=str(projects[1]),
                   JV_CAPACITY_EVIDENCE=str(out/'lifetime.jsonl'))
        run('generated-capacity-tests',[sys.executable,projects[0]/'scripts/tests/test_capacity.py'],
            check=False,cwd=projects[0],timeout=180)
        failed=[c['label'] for c in commands if c['status']]
        summary={'candidate':head,'evidence':str(out),'failed':failed,
                 'scope':'real task-disabled Copier renders; every candidate child source-gated; private host roots',
                 'red_boundary':'missing closure is feature-absence RED, not a behavioral kill'}
        (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
        return int(bool(failed))
    except (AssertionError,RuntimeError,OSError,subprocess.TimeoutExpired) as error:
        (out/'runner-error.txt').write_text(type(error).__name__+': '+str(error)+'\n')
        print(str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())

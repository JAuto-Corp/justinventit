#!/usr/bin/env python3
"""W-C3: data-only Copier render/update/rollback, then gated scratch tests.

The historical release and current RED pacemaker are unsafe executable inputs.
Both are materialized only as data, with tasks disabled and no custom render
extensions. Runtime findings are retained and prevent ANY liveness invocation.
"""
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
from liveness_guard import render_findings, runtime_findings
from liveness_fixture import ALLOWED


def hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.relative_to(root).parts}


def answers(path):
    # Only the flat string/number/bool answers emitted by this pinned template.
    return {key:value.strip().strip('\"\'') for line in path.read_text().splitlines()
            if line and not line.startswith('#') and ': ' in line for key,value in [line.split(': ',1)]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template',type=Path,default=ROOT)
    parser.add_argument('--copier',default='copier')
    parser.add_argument('--evidence',type=Path)
    args=parser.parse_args()
    template=args.template.resolve()
    evidence=args.evidence.resolve() if args.evidence else Path(tempfile.mkdtemp(prefix='jv-liveness-evidence-'))
    if args.evidence:evidence.mkdir(parents=True,exist_ok=False)
    scratch=evidence/'scratch';scratch.mkdir()
    home=scratch/'home';home.mkdir();binpath=scratch/'bin';binpath.mkdir();tmp=scratch/'tmp';tmp.mkdir()
    for name in (*ALLOWED,'git','diff','patch'):
        native=shutil.which(name)
        if native:(binpath/name).symlink_to(native)
    # Copier is invoked by its resolved path. Its pinned venv remains installed;
    # its children receive no inherited PATH, credentials, provider or Git homes.
    env={'PATH':str(binpath),'HOME':str(home),'TMPDIR':str(tmp),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
         'PYTHONDONTWRITEBYTECODE':'1','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
         'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_COUNT':'3','GIT_CONFIG_KEY_0':'core.hooksPath',
         'GIT_CONFIG_VALUE_0':'/dev/null','GIT_CONFIG_KEY_1':'protocol.allow','GIT_CONFIG_VALUE_1':'never',
         'GIT_CONFIG_KEY_2':'protocol.file.allow','GIT_CONFIG_VALUE_2':'always'}
    commands=[];gates=[];sources={}

    def run(label,argv,check=True,**kwargs):
        argv=list(map(str,argv))
        p=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=kwargs.pop('timeout',120),**kwargs)
        (evidence/(label+'.stdout')).write_text(p.stdout);(evidence/(label+'.stderr')).write_text(p.stderr)
        commands.append({'label':label,'argv':argv,'status':p.returncode})
        print(label+': exit '+str(p.returncode),flush=True)
        (evidence/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if check and p.returncode:raise RuntimeError(label+' failed; see retained logs')
        return p

    def source(ref):
        if ref not in sources:
            sha=run('resolve-'+ref,['git','-C',template,'rev-parse',ref]).stdout.strip()
            p=subprocess.run(['git','-C',str(template),'archive','--format=tar',sha],env=env,capture_output=True,timeout=60)
            if p.returncode:raise RuntimeError('cannot read pinned source archive')
            tree=scratch/('source-'+ref);tree.mkdir()
            with tarfile.open(fileobj=io.BytesIO(p.stdout)) as archive:archive.extractall(tree,filter='data')
            sources[ref]=(sha,tree)
        return sources[ref]

    def gate(label,*refs):
        # Recompute BEFORE EVERY Copier invocation, including both old/new
        # render inputs used internally by `copier update`.
        for ref in refs:
            sha,tree=source(ref)
            config=render_findings((tree/'copier.yml').read_text())
            runtime=runtime_findings(tree/'template')
            record={'label':label,'ref':ref,'sha':sha,'render_findings':config,'runtime_findings':runtime,
                    'execution':'data-only: --skip-tasks; runtime bodies NOT invoked'}
            gates.append(record);(evidence/'pre-execution-gates.json').write_text(json.dumps(gates,indent=2)+'\n')
            if config:raise RuntimeError('refuse executable/coupled Copier configuration before rendering')

    def git(project,label,*argv):
        return run(label,['git','-C',project,*argv])

    try:
        copier=shutil.which(args.copier)
        if not copier:raise RuntimeError('Copier 9.17.1 required')
        version=run('copier-version',[copier,'--version'])
        if version.stdout.strip()!='copier 9.17.1':raise RuntimeError('Copier 9.17.1 required')
        head,_=source('HEAD')
        common=['--defaults','--skip-tasks','-d','database=none','-d','db_adapter=none','-d','testing=none']
        projects=[]
        for name,tier in (('alpha','cluster'),('beta','solo')):
            project=scratch/('consumer '+name)
            gate('render-'+name,'HEAD')
            run('render-'+name,[copier,'copy',*common,'--vcs-ref='+head,'-d','project_name=Liveness '+name,
                              '-d','orchestration_tier='+tier,template,project])
            projects.append(project)
        release='jv-v0.2.3';upgrade=scratch/'upgrade consumer'
        gate('render-release',release)
        run('render-release',[copier,'copy',*common,'--vcs-ref='+release,'-d','project_name=Upgrade fixture',
                              '-d','orchestration_tier=cluster',template,upgrade])
        old_answers=answers(upgrade/'.copier-answers.yml')
        assert old_answers['external_pacemaker']=='tmux-supervisor','witness must exercise saved released default'
        owned=upgrade/'AGENTS.md';owned.write_text(owned.read_text()+'\nProject-owned upgrade witness: preserve this exact line.\n')
        legacy={
            'context/cadence/a.txt':b'state: awake\nrole: a\nnext_wake_at: 2026-01-01T00:00:00Z\n',
            'context/cadence/.pacemaker-state/a.state':b'last_resume_epoch=1700000000\n',
        }
        for rel,data in legacy.items():
            p=upgrade/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        git(upgrade,'upgrade-init','init','-q')
        git(upgrade,'upgrade-user','config','user.name','JV disposable fixture')
        git(upgrade,'upgrade-email','config','user.email','fixture@example.invalid')
        # Runtime state is deliberately untracked, as in an adopted consumer.
        (upgrade/'.git/info/exclude').write_text('context/cadence/*.txt\ncontext/cadence/.pacemaker-state/\n')
        git(upgrade,'upgrade-add-release','add','-A');git(upgrade,'upgrade-commit-release','commit','-qm','Released consumer with project-owned edit')
        before=hashes(upgrade);owned_before=owned.read_bytes()
        (evidence/'upgrade-before-sha256.json').write_text(json.dumps(before,indent=2)+'\n')
        gate('update-candidate',release,'HEAD')
        run('update-candidate',[copier,'update','--defaults','--skip-tasks','--vcs-ref='+head],cwd=upgrade,timeout=180)
        new_answers=answers(upgrade/'.copier-answers.yml')
        saved=all(new_answers.get(k)==v for k,v in old_answers.items() if not k.startswith('_'))
        assert saved,'update changed saved user answers'
        assert owned.read_bytes()==owned_before,'update overwrote project-owned AGENTS'
        assert all((upgrade/p).read_bytes()==v for p,v in legacy.items()),'update changed legacy runtime state'
        assert new_answers['_commit']==head,'candidate source not recorded in answers'
        updated=scratch/'updated consumer'
        shutil.copytree(upgrade,updated,ignore=shutil.ignore_patterns('.git','__pycache__'))
        (evidence/'upgrade-after-sha256.json').write_text(json.dumps(hashes(upgrade),indent=2)+'\n')
        git(upgrade,'upgrade-add-candidate','add','-A');git(upgrade,'upgrade-commit-candidate','commit','-qm','Adopt W-C3 candidate')
        adoption=git(upgrade,'upgrade-adoption','rev-parse','HEAD').stdout.strip()
        git(upgrade,'upgrade-rollback','revert','--no-edit',adoption)
        after=hashes(upgrade)
        (evidence/'upgrade-rollback-sha256.json').write_text(json.dumps(after,indent=2)+'\n')
        assert after==before,'adoption rollback did not restore release files/answers/owned state'
        receipt={'release':release,'candidate':head,'updated_consumer':str(updated),'external_pacemaker':old_answers['external_pacemaker'],
                 'saved_answers_preserved':saved,'project_edits_preserved':True,'legacy_state_preserved':True,'rollback_equal':True,
                 'adoption_commit':adoption,'legacy_knobs':{'PACEMAKER_CADENCE_DIR':str(updated/'context/cadence'),
                    'PACEMAKER_STATE_DIR':str(updated/'context/cadence/.pacemaker-state'),'PACEMAKER_RESPAWN_HOOK':'/never/execute',
                    'PACEMAKER_NOTIFY':'sms','PACEMAKER_SMS_CMD':'/never/execute'},
                 'scope':'real Copier copy/update and git revert; release bodies never executed; candidate runtime test is separate'}
        receipt_path=evidence/'upgrade-receipt.json';receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
        rendered={str(p.relative_to(scratch)):hashes(p) for p in (*projects,updated)}
        (evidence/'rendered-sha256.json').write_text(json.dumps(rendered,indent=2)+'\n')
        env.update(JV_LIVENESS_PROJECT=str(projects[0]),JV_LIVENESS_PEER=str(projects[1]),
                   JV_LIVENESS_UPGRADE_RECEIPT=str(receipt_path))
        run('generated-liveness-tests',[sys.executable,projects[0]/'scripts/tests/test_liveness.py'],check=False,cwd=projects[0],timeout=180)
        failed=[r['label'] for r in commands if r['status']]
        summary={'candidate':head,'evidence':str(evidence),'failed':failed,
                 'render_scope':'data-only; tasks disabled; runtime source findings retained separately',
                 'upgrade_rollback':'PASS; candidate migration behavior is covered by gated runtime test'}
        (evidence/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
        return int(bool(failed))
    except (AssertionError,RuntimeError,OSError,subprocess.TimeoutExpired) as error:
        (evidence/'runner-error.txt').write_text(type(error).__name__+': '+str(error)+'\n')
        print(str(error),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())

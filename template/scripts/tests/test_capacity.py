#!/usr/bin/env python3
"""W-C4 T1–T7 and SPEC F1–F3. Missing closure is feature-absence RED."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from capacity_guard import CLOSURE, render_findings, runtime_findings
from capacity_fixture import Fixture, opened, snapshot

PROJECT=Path(os.environ.get('JV_CAPACITY_PROJECT',Path(__file__).resolve().parents[2]))
PEER=Path(os.environ.get('JV_CAPACITY_PEER',PROJECT))


class Containment(unittest.TestCase):
    def test_t7_gate_positive_and_refusals(self):
        """I6/I7: unsafe seeds and extra sourced-helper effects remain data."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for rel in CLOSURE:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#!/bin/bash\nexit 0\n')
            self.assertEqual(runtime_findings(root),[])
            seeds=('if /bin/kill -TERM "$pid"; then :; fi','/usr/bin/tmux send-keys x',
                   'curl https://invalid.example','cat /proc/123/environ','cat /proc/*/cmdline',
                   'cat /home/'+'justi/private','os.kill(123,9)','subprocess.run(["anything"])')
            for rel in CLOSURE:
                path=root/rel
                for seed in seeds:
                    with self.subTest(file=rel,seed=seed):
                        path.write_text('#!/bin/bash\n'+seed+'\n')
                        self.assertTrue(runtime_findings(root),'unsafe seed would reach execution')
                path.write_text('#!/bin/bash\nexit 0\n')
            path=root/CLOSURE[0]
            path.write_text('awk x /proc/meminfo\nstat -Lc x "/proc/self/fd/$fd"\n')
            self.assertEqual(runtime_findings(root),[])
            for key in ('_tasks','_migrations','_jinja_extensions'):
                self.assertTrue(render_findings(key+': []\n'))

    def test_r1_r2_closure_wrapped_effects_and_host_opens(self):
        """R1→I6/I7, R2→I1/I7: refuse extra helpers and host opens as DATA."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for rel in CLOSURE:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('exit 0\n')
            helper=root/'scripts/lib/extra.sh';helper.write_text('env /bin/kill -TERM 99999\n')
            entry=root/CLOSURE[0]
            for seed in ('source "$SCRIPT_DIR/lib/extra.sh"', '. "$SCRIPT_DIR/lib/extra.sh"',
                         'bash "$SCRIPT_DIR/lib/extra.sh"', 'env /bin/kill -TERM 99999',
                         'env X=1 command /usr/bin/tmux list-sessions',
                         'exec {fd}>"/tmp/not-a-fixture.lock"',
                         'LOCK_DIR="${JV_HOST_ROOT:-/var/lock}"', 'LOCK_DIR="$HOME/locks"'):
                with self.subTest(seed=seed):
                    entry.write_text(seed+'\n')
                    self.assertTrue(runtime_findings(root),'unsafe seed would execute')
            entry.write_text('source "$SCRIPT_DIR/lib/jv-project.sh"\n')
            self.assertEqual(runtime_findings(root),[])

    def test_r2_native_flock_boundary(self):
        """R2→I1/I7: pathname and foreign FDs never reach native flock."""
        f=Fixture(self,(PROJECT,PEER))
        # Disposable sibling canary, never a real host lock.
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'foreign.lock'
            r=subprocess.run([f.bin/'flock','-n',target,'true'],env=f.environment(),capture_output=True)
            self.assertEqual(r.returncode,92);self.assertFalse(target.exists())
            with target.open('w') as foreign:
                r=subprocess.run([f.bin/'flock','-n',str(foreign.fileno())],env=f.environment(),
                                 pass_fds=(foreign.fileno(),),capture_output=True)
                self.assertEqual(r.returncode,92)
                with target.open('r') as probe:
                    fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_t7_fixture_memory_flock_and_closed_stdin(self):
        """I7/F2/F3: calibrate test seams without executing missing production."""
        f=Fixture(self,(PROJECT,PEER));env=f.environment()
        self.assertEqual(env['PATH'],str(f.bin));self.assertNotIn('JV_BUILD_LOCK_FD',env)
        self.assertNotIn('CODEX_HOME',env)
        r=subprocess.run([f.bin/'awk','memory','/proc/meminfo'],env=env,capture_output=True,text=True)
        self.assertEqual((r.returncode,r.stdout.strip()),(0,'8192'))
        f.lock.parent.mkdir(parents=True)
        with f.lock.open('a') as held, f.lock.open('a') as probe:
            fcntl.flock(held,fcntl.LOCK_EX)
            args=[str(f.bin/'flock'),'-n','-E','75',str(probe.fileno())]
            r=subprocess.run(args,env=env,pass_fds=(probe.fileno(),),capture_output=True,text=True)
            self.assertEqual(r.returncode,75)
            env=f.environment(overrides={'JV_CAPACITY_FLOCK_FAULT':'probe','JV_BUILD_LOCK_FD':str(held.fileno())})
            r=subprocess.run(args,env=env,pass_fds=(probe.fileno(),),capture_output=True,text=True)
            self.assertEqual(r.returncode,74);self.assertTrue((f.root/'fault-reached').exists())
        r=subprocess.run(['bash','-c','exec 0<&-; exec python3 "$1" io','fixture',str(f.work)],
                         env=f.environment(),capture_output=True,text=True)
        self.assertEqual(r.returncode,47);self.assertTrue(json.loads(r.stdout)['closed'])


class Capacity(unittest.TestCase):
    def setUp(self):
        for root in (PROJECT,PEER):
            missing=[rel for rel in CLOSURE if not (root/rel).is_file()]
            self.assertFalse(missing,'W-C4 feature-absence RED; missing generated closure: '+', '.join(missing))
            self.assertFalse(runtime_findings(root),'source refusal; no runtime child')
        self.f=Fixture(self,(PROJECT,PEER))

    def ok(self,r):
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r

    def mark(self,peer=0,**kwargs):
        path=self.f.root/('command-ran-'+str(peer))
        path.unlink(missing_ok=True)
        return self.f.run('python3',self.f.work,'mark',path,peer=peer,**kwargs),path

    def held(self):
        result=self.ok(self.f.verb('status'));self.assertIn('build-lock: held',result.stdout)

    def reacquire(self,peer=1):
        results=[]
        def attempt():
            r,p=self.mark(peer);results.append(r.returncode)
            self.assertIn(r.returncode,(0,1),r.stdout+r.stderr)
            return r.returncode==0 and p.exists()
        self.f.wait(attempt,'kernel slot reacquired')
        self.f.receipt('reacquired',statuses=results)

    def test_t1_projects_host_and_cwd(self):
        """I1/I2 positive: same host root, separate project bindings and state."""
        f=self.f
        for peer in (0,1):
            before=snapshot(f.state);foreign=f.store(1-peer)
            watched=[foreign,*foreign.rglob('*')]
            with opened(watched) as events:
                r,marker=self.mark(peer,guarded=True)
            self.assertFalse(any(events),'foreign project state was opened')
            self.ok(r);self.assertTrue(marker.exists());self.assertEqual(before,snapshot(f.state))
        self.assertTrue(f.lock.is_file())
        self.assertEqual(f.lock.stat().st_mode & 0o777,0o600)
        self.assertEqual(f.lock.parent.stat().st_mode & 0o777,0o700)

    def test_t1_binding_and_legacy_refusal(self):
        """I1 refusal: no legacy target or mismatched project can admit a command."""
        f=self.f;target=f.root/'legacy-target';target.write_text('canary')
        cases=[{'JV_PROJECT_ID':None},{'JV_PROJECT_ROOT':str(f.projects[1])},
               {'JV_STATE_ROOT':'relative'},{'JV_HOST_ROOT':None},{'JV_HOST_ROOT':'relative'}]
        cases.extend({key:str(target)} for key in
                     ('JAUTO_BUILD_LOCK_FD','BUILD_LOCK_TEST_MODE','BUILD_LOCK_TEST_DIR','BUILD_LOCK_TEST_AVAILABLE_MB'))
        before=snapshot(f.state)
        for env in cases:
            with self.subTest(env=env),opened([target]) as events:
                r,p=self.mark(env=env);self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists())
            self.assertFalse(any(events));self.assertEqual(target.read_text(),'canary')
            self.assertEqual(before,snapshot(f.state));self.assertFalse(f.host.exists())

    def test_t1_host_aliases_and_types(self):
        """I1 refusal: root, ancestor and owned lock/info aliases never redirect I/O."""
        f=self.f;f.foreign_host.mkdir();canary=f.foreign_host/'canary';canary.write_text('foreign')
        for rel in ('.','locks','locks/build.lock','locks/info'):
            for kind in ('alias','wrong-type'):
                with self.subTest(path=rel,kind=kind):
                    shutil.rmtree(f.host,ignore_errors=True)
                    if f.host.is_symlink() or f.host.is_file():f.host.unlink()
                    path=f.host if rel=='.' else f.host/rel
                    path.parent.mkdir(parents=True,exist_ok=True)
                    if kind=='alias':path.symlink_to(f.foreign_host if rel in ('.','locks') else canary)
                    elif rel in ('.','locks'):path.write_text('not a directory')
                    else:path.mkdir()
                    saved=snapshot(f.foreign_host)
                    with opened([f.foreign_host,canary]) as events:
                        r,p=self.mark();self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists())
                    self.assertFalse(any(events));self.assertEqual(saved,snapshot(f.foreign_host))
        shutil.rmtree(f.host);alias=f.root/'aliased-parent';alias.symlink_to(f.foreign_host)
        with opened([f.foreign_host,canary]) as events:
            r,p=self.mark(env={'JV_HOST_ROOT':str(alias/'child')})
        self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists());self.assertFalse(any(events))

    def test_t2_contention_metadata_and_inode(self):
        """I2: five cross-project contenders cannot steal from PID/age/absent info."""
        f=self.f;parent,release,_=f.hold(guarded=True);self.held();inode=f.lock.stat().st_ino
        f.info.write_text('pid=999999999\nheld_at_epoch=1\ntoken=poisoned\n')
        children=[]
        for n in range(5):
            marker=f.root/('contender-'+str(n))
            children.append((f.start(f.argv(['python3',f.work,'mark',marker],True,n%2),n%2),marker))
        for child,marker in children:
            self.assertEqual(child.wait(timeout=5),1);self.assertFalse(marker.exists())
        f.info.unlink();r,p=self.mark(1);self.assertEqual(r.returncode,1);self.assertFalse(p.exists());self.held()
        release.touch();self.assertEqual(parent.wait(timeout=5),0);self.reacquire()
        self.assertEqual(f.lock.stat().st_ino,inode)
        f.receipt('five contenders refused; poisoned/absent info did not grant ownership',inode=inode)

    def test_r4_python_canonical_owner(self):
        """R4→I2: independent Python ownership denies both entries/projects."""
        f=self.f;f.lock.parent.mkdir(parents=True)
        with f.lock.open('a') as owner:
            fcntl.flock(owner,fcntl.LOCK_EX)
            inode=f.lock.stat().st_ino
            for peer in (0,1):
                for guarded in (False,True):
                    with self.subTest(peer=peer,guarded=guarded):
                        r,p=self.mark(peer,guarded=guarded)
                        self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertFalse(p.exists())
                        self.assertEqual(f.lock.stat().st_ino,inode)
        self.reacquire()

    def test_t3_crash_background_and_node_lifetime(self):
        """I3/F1: retained FD excludes contenders until explicit fixture release."""
        f=self.f
        for mode in ('foreground','background','node'):
            with self.subTest(mode=mode):
                parent,release,_=f.hold(mode=mode)
                if mode=='background':self.assertEqual(parent.wait(timeout=5),0)
                else:
                    parent.kill();self.assertEqual(parent.wait(timeout=5),-9)  # fixture Popen only
                r,p=self.mark(1);self.assertEqual(r.returncode,1);self.assertFalse(p.exists())
                self.held();f.receipt('parent ended; retained descriptor still excludes',mode=mode)
                release.touch();self.reacquire()
        # No automatic recovery is asserted: a never-released retained FD can wedge capacity.

    def test_t4_nested_same_and_cross_project(self):
        """I4 positive: inner verify/run/failure cannot release or relabel outer owner."""
        f=self.f;ready=f.root/'nested-ready';release=f.root/'nested-release';f.releases.append(release)
        before=f.root/'outer-info';inner=f.root/'inner-ran'
        code='''cp "$JV_HOST_ROOT/locks/info" "$5"
bash "$1" verify-inherited || exit 81
bash "$1" run python3 "$2" mark "$6" || exit 82
JV_PROJECT_ID=beta JV_PROJECT_ROOT="$3" bash "$4" run python3 "$2" mark "$6" || exit 83
if bash "$1" run python3 "$2" io; then exit 84; else test "$?" = 47 || exit 85; fi
touch "$7"
while test ! -e "$8"; do sleep .01; done
'''
        command=['bash','-c',code,'fixture',f.entry(),f.work,f.projects[1],f.entry(peer=1),before,inner,ready,release]
        parent=f.start(f.argv(command));f.wait(ready.exists,'nested work completed')
        self.assertTrue(inner.exists());self.assertEqual(before.read_bytes(),f.info.read_bytes())
        r,p=self.mark(1);self.assertEqual(r.returncode,1);self.assertFalse(p.exists())
        release.touch();self.assertEqual(parent.wait(timeout=5),0);self.reacquire()

    def test_t4_spoofed_descriptors(self):
        """I4 refusal: marker, wrong file and same inode do not prove owning OFD."""
        f=self.f;f.lock.parent.mkdir(parents=True);f.lock.touch()
        for marker in ('','99999','bad'):
            with self.subTest(marker=marker):
                r,p=self.mark(env={'JV_BUILD_LOCK_FD':marker})
                self.assertEqual(r.returncode,65);self.assertFalse(p.exists())
        with f.lock.open('a') as unlocked:
            r,p=self.mark(env={'JV_BUILD_LOCK_FD':str(unlocked.fileno())},pass_fds=(unlocked.fileno(),))
            self.assertEqual(r.returncode,65);self.assertFalse(p.exists())
        # R3→I4: both files locked, so only the inode check can reject this FD.
        with f.lock.open('a') as owner, (f.root/'unrelated').open('w') as wrong:
            fcntl.flock(owner,fcntl.LOCK_EX);fcntl.flock(wrong,fcntl.LOCK_EX)
            for peer in (0,1):
                r,p=self.mark(peer,env={'JV_BUILD_LOCK_FD':str(wrong.fileno())},pass_fds=(wrong.fileno(),))
                self.assertEqual(r.returncode,65);self.assertFalse(p.exists())
        with f.lock.open('a') as owner, f.lock.open('a') as other:
            fcntl.flock(owner,fcntl.LOCK_EX)
            r,p=self.mark(env={'JV_BUILD_LOCK_FD':str(other.fileno())},pass_fds=(other.fileno(),))
            self.assertEqual(r.returncode,65);self.assertFalse(p.exists())

    def test_t4_f2_probe_error_is_not_conflict(self):
        """F2→I4: error 74 cannot authorize an unlocked but otherwise valid descriptor."""
        f=self.f;f.lock.parent.mkdir(parents=True)
        with f.lock.open('a') as unlocked:
            fd=unlocked.fileno()
            r,p=self.mark(env={'JV_BUILD_LOCK_FD':str(fd),'JV_CAPACITY_FLOCK_FAULT':'probe'},pass_fds=(fd,))
            self.assertEqual(r.returncode,65);self.assertFalse(p.exists())
            self.assertTrue((f.root/'fault-reached').exists(),'probe fault did not execute')
            calls=[json.loads(x) for x in (f.root/'capacity-calls.jsonl').read_text().splitlines()]
            self.assertFalse(any(x['command']=='flock' and x['args'][-1]==str(fd) for x in calls),
                             'probe error continued to owning-descriptor re-lock')
        self.reacquire()

    def test_t5_memory_boundaries_and_unknown(self):
        """I5 positive/refusal: 4096 equality and unavailable warning are explicit."""
        f=self.f
        for value in ('4095','4096','4097','unavailable','garbage'):
            with self.subTest(memory=value):
                r,p=self.mark(env={'JV_TEST_MEMORY':value})
                self.assertEqual(r.returncode,2 if value=='4095' else 0,r.stdout+r.stderr)
                self.assertEqual(p.exists(),value!='4095')
                if value in ('unavailable','garbage'):self.assertIn('warning',r.stderr.lower())
        calls=[json.loads(x) for x in (f.root/'capacity-calls.jsonl').read_text().splitlines()]
        self.assertEqual([x['value'] for x in calls if x['command']=='memory'],
                         ['4095','4096','4097','unavailable','garbage'])

    def test_t5_f3_io_foreground_both_entries(self):
        """F3→I5: heredoc/piped bytes, EBADF on closed FD0, exact argv/cwd/status."""
        f=self.f;args=['space arg','','line\nnext','$(not-executed)'];payload='first café\nsecond\n'
        for guarded in (False,True):
            for mode in ('pipe','heredoc','closed'):
                with self.subTest(guarded=guarded,mode=mode):
                    command=['python3',f.work,'io',*args]
                    if mode=='pipe':r=f.run(*command,guarded=guarded,input=payload)
                    elif mode=='heredoc':
                        r=f.shell('"$@" <<\'JV_INPUT\'\n'+payload+'JV_INPUT\n',*f.argv(command,guarded))
                    else:r=f.shell('exec 0<&-; exec "$@"',*f.argv(command,guarded))
                    self.assertEqual(r.returncode,47,r.stdout+r.stderr)
                    data=json.loads(r.stdout)
                    self.assertEqual(data,{'argv':args,'cwd':str(f.root),
                                           'stdin':None if mode=='closed' else payload,'closed':mode=='closed'})
                    self.assertIn('fixture-stderr',r.stderr)
                    self.reacquire()

    def test_t5_metadata_and_open_faults(self):
        """I5 refusal: partial write/rename/open failure cannot admit work or leave debris."""
        f=self.f;self.ok(self.mark()[0])
        for fault in ('write','rename'):
            with self.subTest(fault=fault):
                f.info.write_text('token=prior\n');prior=f.info.read_bytes()
                marker=f.root/'fault-reached';marker.unlink(missing_ok=True)
                r,p=self.mark(env={'JV_CAPACITY_META_FAULT':fault})
                self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists())
                self.assertTrue(marker.exists(),'metadata fault was not reached')
                self.assertEqual(f.info.read_bytes(),prior)
                self.assertEqual(list(f.lock.parent.glob('.info*')),[])
                self.reacquire()
        f.lock.chmod(0o400)
        try:
            r,p=self.mark();self.assertNotEqual(r.returncode,0);self.assertFalse(p.exists())
        finally:f.lock.chmod(0o600)
        self.reacquire()

    def test_t6_status_readonly_absent_and_held(self):
        """I6 positive: status/wait-info never create, chmod or clear owned paths."""
        f=self.f
        for verb in ('status','wait-info'):
            r=self.ok(f.verb(verb));self.assertTrue(r.stdout.strip());self.assertFalse(f.host.exists())
        parent,release,_=f.hold()
        before=snapshot(f.host);modes={str(p):p.stat().st_mode for p in (f.host,f.lock.parent,f.lock,f.info)}
        for verb in ('status','wait-info'):
            r=self.ok(f.verb(verb));self.assertIn('held',r.stdout)
            self.assertEqual(before,snapshot(f.host))
            self.assertEqual(modes,{str(p):p.stat().st_mode for p in (f.host,f.lock.parent,f.lock,f.info)})
        release.touch();self.assertEqual(parent.wait(timeout=5),0)

    def test_t6_unknown_retired_and_foreign_token(self):
        """I6 refusal: inspection errors stay unknown; no forced release/foreign cleanup."""
        f=self.f;parent,release,_=f.hold();before=snapshot(f.host)
        for verb in ('status','wait-info'):
            r=f.verb(verb,env={'JV_CAPACITY_FLOCK_FAULT':'all'})
            self.assertNotEqual(r.returncode,0);self.assertTrue(r.stderr.strip())
            self.assertNotIn('unheld',r.stdout);self.assertEqual(before,snapshot(f.host))
        self.assertTrue((f.root/'fault-reached').exists())
        for verb in ('acquire','release'):
            r=f.verb(verb);self.assertEqual(r.returncode,64);self.held()
        foreign=b'token=foreign-token\nproject_id=beta\n';f.info.write_bytes(foreign)
        release.touch();self.assertEqual(parent.wait(timeout=5),0)
        self.assertEqual(f.info.read_bytes(),foreign);self.reacquire()

    def test_t7_real_render_and_no_external_calls(self):
        """I7: both real generated tiers execute only marker workloads in owned roots."""
        f=self.f
        for peer in (0,1):
            self.assertTrue((f.projects[peer]/'.copier-answers.yml').is_file())
            self.assertEqual(runtime_findings(f.projects[peer]),[])
            r,p=self.mark(peer);self.ok(r);self.assertTrue(p.exists())
        f.no_external()


if __name__=='__main__':unittest.main(verbosity=2)

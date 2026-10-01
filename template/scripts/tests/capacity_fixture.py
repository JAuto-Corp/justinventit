"""W-C4: private host roots, real fixture flock, owned descendant handles only."""
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from capacity_guard import runtime_findings
from liveness_fixture import Fixture as BaseFixture, ALLOWED
from test_launch import opened, snapshot

CAPACITY_ALLOWED = (*ALLOWED, 'node')


class Fixture(BaseFixture):
    def __init__(self, case, sources):
        super().__init__(case, sources)
        self.host = self.root / 'shared host'; self.foreign_host = self.root / 'foreign host'
        self.env.pop('JV_WATCHDOG_PROC_ROOT')
        self.env.update(JV_HOST_ROOT=str(self.host), JV_TEST_MEMORY='8192',
                        JV_CAPACITY_FIXTURE_ROOT=str(self.root),
                        JV_CAPACITY_CALLS=str(self.root/'capacity-calls.jsonl'),
                        JV_CAPACITY_FAULT_MARKER=str(self.root/'fault-reached'))
        self.children = []; self.owned = []; self.handles = []; self.releases = []
        self.sequence = 0
        # Only THIS test process adopts its own orphaned fixture descendants,
        # so a killed wrapper cannot leave unreaped children in the test runner.
        case.assertEqual(ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0), 0)
        case.addCleanup(self.cleanup)
        node = shutil.which('node'); case.assertIsNotNone(node)
        (self.bin/'node').symlink_to(node)
        for peer in (0, 1):
            self.bind(peer)
        self.work = self.root/'workload.py'
        self.work.write_text("""import errno,json,os,pathlib,sys,time
mode=sys.argv[1]
if mode=='mark':
 pathlib.Path(sys.argv[2]).touch()
elif mode=='hold':
 pathlib.Path(sys.argv[2]).write_text(str(os.getpid()))
 while not pathlib.Path(sys.argv[3]).exists(): time.sleep(.01)
elif mode=='io':
 try:
  os.fstat(0); closed=False
 except OSError as e:
  if e.errno!=errno.EBADF: raise
  closed=True
 data=None if closed else sys.stdin.read()
 print(json.dumps({'argv':sys.argv[2:],'cwd':os.getcwd(),'stdin':data,'closed':closed}))
 print('fixture-stderr',file=sys.stderr)
 sys.exit(47)
""")
        # Do not read actual host memory. Record that the exact observation
        # seam was reached, and return a finite synthetic value instead.
        self.stub('awk', """#!/usr/bin/env python3
import json,os,pathlib,sys
if '/proc/meminfo' in sys.argv:
 with pathlib.Path(os.environ['JV_CAPACITY_CALLS']).open('a') as out:
  out.write(json.dumps({'command':'memory','value':os.environ['JV_TEST_MEMORY']})+'\\n')
 value=os.environ['JV_TEST_MEMORY']
 if value!='unavailable': print(value)
 sys.exit(0)
os.execv(NATIVE,['awk',*sys.argv[1:]])
""".replace('NATIVE', repr(shutil.which('awk'))))
        self.stub('flock', """#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]; fd=args[-1] if args else ''; target=''
try: target=os.readlink('/proc/self/fd/'+fd)
except OSError: pass
with pathlib.Path(os.environ['JV_CAPACITY_CALLS']).open('a') as out:
 out.write(json.dumps({'command':'flock','args':args,'target':target})+'\\n')
# R2: never forward a pathname/command form or an off-fixture FD to native.
root=pathlib.Path(os.environ['JV_CAPACITY_FIXTURE_ROOT']).resolve()
if not fd.isdecimal() or not target or not pathlib.Path(target).resolve().is_relative_to(root):
 sys.exit(92)
fault=os.environ.get('JV_CAPACITY_FLOCK_FAULT')
if target==os.environ['JV_HOST_ROOT']+'/locks/build.lock' and (fault=='all' or
 (fault=='probe' and fd!=os.environ.get('JV_BUILD_LOCK_FD'))):
 pathlib.Path(os.environ['JV_CAPACITY_FAULT_MARKER']).touch()
 sys.exit(74)
os.execv(NATIVE,['flock',*args])
""".replace('NATIVE', repr(shutil.which('flock'))))
        self.stub('cat', """#!/usr/bin/env python3
import os,pathlib,sys
try: target=os.readlink('/proc/self/fd/1')
except OSError: target=''
if os.environ.get('JV_CAPACITY_META_FAULT')=='write' and target.startswith(os.environ['JV_HOST_ROOT']+'/locks/.info'):
 pathlib.Path(os.environ['JV_CAPACITY_FAULT_MARKER']).touch()
 os.write(1,b'partial fixture metadata')
 sys.exit(74)
os.execv(NATIVE,['cat',*sys.argv[1:]])
""".replace('NATIVE', repr(shutil.which('cat'))))
        self.stub('mv', """#!/usr/bin/env python3
import os,pathlib,sys
if os.environ.get('JV_CAPACITY_META_FAULT')=='rename' and sys.argv[-1]==os.environ['JV_HOST_ROOT']+'/locks/info':
 pathlib.Path(os.environ['JV_CAPACITY_FAULT_MARKER']).touch()
 sys.exit(74)
os.execv(NATIVE,['mv',*sys.argv[1:]])
""".replace('NATIVE', repr(shutil.which('mv'))))

    @property
    def lock(self):
        return self.host/'locks/build.lock'

    @property
    def info(self):
        return self.host/'locks/info'

    def gate(self, peer=0):
        self.case.assertFalse(runtime_findings(self.projects[peer]),
                              'W-C4 source/closure refusal; no candidate child executed')

    def entry(self, guarded=False, peer=0):
        return self.projects[peer]/'scripts'/('build-guarded.sh' if guarded else 'build-lock.sh')

    def argv(self, command, guarded=False, peer=0):
        return ['bash', str(self.entry(guarded, peer)), *([] if guarded else ['run']), *map(str, command)]

    def run_argv(self, argv, peer=0, env=None, **kwargs):
        self.gate(peer)
        defaults = dict(cwd=self.root, env=self.environment(peer, env),
                        capture_output=True, text=True, timeout=8)
        defaults.update(kwargs)
        if 'input' not in defaults:
            defaults.setdefault('stdin', subprocess.DEVNULL)
        return subprocess.run(list(map(str, argv)), **defaults)

    def environment(self, peer=0, overrides=None):
        env=super().environment(peer,overrides)
        # Check configured open roots BEFORE the candidate shell can redirect.
        for key in ('JV_HOST_ROOT','JV_STATE_ROOT','JV_PROJECT_ROOT'):
            value=env.get(key)
            if value and Path(value).is_absolute():
                self.case.assertTrue(Path(value).resolve().is_relative_to(self.root),
                                     'nonfixture configured path; no candidate child')
        return env

    def run(self, *command, guarded=False, peer=0, env=None, **kwargs):
        return self.run_argv(self.argv(command, guarded, peer), peer, env, **kwargs)

    def verb(self, verb, peer=0, env=None, **kwargs):
        return self.run_argv(['bash', self.entry(peer=peer), verb], peer, env, **kwargs)

    def shell(self, code, *args, peer=0, env=None, **kwargs):
        return self.run_argv(['bash','-c',code,'fixture',*args], peer, env, **kwargs)

    def start(self, argv, peer=0, env=None):
        self.gate(peer); self.sequence += 1
        out=(self.root/('child-'+str(self.sequence)+'.stdout')).open('w')
        err=(self.root/('child-'+str(self.sequence)+'.stderr')).open('w')
        self.handles.extend((out,err))
        p=subprocess.Popen(list(map(str,argv)),cwd=self.root,env=self.environment(peer,env),
                           stdin=subprocess.DEVNULL,stdout=out,stderr=err,text=True)
        self.children.append(p)
        return p

    def hold(self, guarded=False, peer=0, mode='foreground'):
        self.sequence += 1; name=str(self.sequence)
        ready=self.root/('ready-'+name);release=self.root/('release-'+name);self.releases.append(release)
        command=['python3',self.work,'hold',ready,release]
        if mode=='background':
            code='"$@" &\nexit 0'
            command=['bash','-c',code,'fixture',*command]
        elif mode=='node':
            script=self.root/('waiter-'+name+'.cjs');node_ready=self.root/('node-parent-'+name)
            script.write_text("""const {spawn}=require('node:child_process');
require('node:fs').writeFileSync(process.argv[2],String(process.pid));
const p=spawn('python3', process.argv.slice(3), {stdio:'ignore'});
p.on('error',()=>process.exit(1));
p.on('exit',code=>process.exit(code??1));
""")
            command=['node',script,node_ready,self.work,'hold',ready,release]
        parent=self.start(self.argv(command,guarded,peer),peer)
        self.wait(ready.exists, 'owned workload ready')
        if mode=='node':
            node_pid=int(node_ready.read_text());self.owned.append((node_pid,os.pidfd_open(node_pid)))
        pid=int(ready.read_text());handle=os.pidfd_open(pid)
        self.owned.append((pid,handle))
        return parent, release, handle

    def receipt(self, event, **details):
        target=os.environ.get('JV_CAPACITY_EVIDENCE')
        if target:
            with Path(target).open('a') as out:
                out.write(json.dumps({'test':self.case.id(),'event':event,**details})+'\n')

    def cleanup(self):
        for release in self.releases:
            release.touch()
        for child in self.children:
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill();child.wait(timeout=3)  # only this fixture's Popen
        for pid,handle in self.owned:
            # A pidfd pins the fixture-created workload, never a stored host PID.
            try: signal.pidfd_send_signal(handle, signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.waitpid(pid,0)  # only our adopted fixture descendant, if any
            except ChildProcessError: pass
            os.close(handle)
        for handle in self.handles:
            handle.close()

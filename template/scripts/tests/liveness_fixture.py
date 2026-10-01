"""Scratch-only W-C3 fixture. No inherited PATH, provider home or process view."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from liveness_guard import runtime_findings
from test_launch import opened, snapshot

EPOCH = 1800000000
ALLOWED = ('bash', 'sh', 'python3', 'jq', 'flock', 'dirname', 'basename', 'realpath', 'readlink',
           'mkdir', 'mktemp', 'cat', 'find', 'tr', 'head', 'tail', 'rm', 'mv', 'cp', 'chmod', 'date',
           'timeout', 'env', 'grep', 'sed', 'sort', 'cut', 'wc', 'touch', 'sync', 'stat', 'sleep', 'od', 'awk')
DENIED = ('tmux', 'curl', 'wget', 'ssh', 'scp', 'sftp', 'nc', 'ncat', 'netcat', 'claude', 'codex',
          'kill', 'pkill', 'killall', 'pgrep', 'crontab', 'systemctl', 'notify-send', 'osascript', 'xdg-open')


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Fixture:
    def __init__(self, case, sources):
        self.case = case
        tmp = tempfile.TemporaryDirectory(prefix='jv-liveness-')
        case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.projects = [self.root / 'consumer alpha', self.root / 'consumer beta space']
        for source, project in zip(sources, self.projects):
            shutil.copytree(source, project, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        self.state = self.root / 'shared-state'
        self.home = self.root / 'synthetic-home'; self.home.mkdir()
        self.proc = self.root / 'synthetic-proc'; self.proc.mkdir()
        self.bin = self.root / 'bin'; self.bin.mkdir()
        self.hooks = self.root / 'fixture-hooks'; self.hooks.mkdir()
        self.tmp = self.root / 'tmp'; self.tmp.mkdir()
        self.calls = self.root / 'forbidden.jsonl'
        self.now = EPOCH
        for name in ALLOWED:
            native = shutil.which(name)
            if native:
                (self.bin / name).symlink_to(native)
        for name in DENIED:
            self.stub(name, '''#!/usr/bin/env python3
import json,os,pathlib,sys
with pathlib.Path(os.environ['JV_TEST_CALLS']).open('a') as out:
 out.write(json.dumps({'command':pathlib.Path(sys.argv[0]).name,'argv':sys.argv[1:]})+'\\n')
sys.exit(91)
''')
        case.addCleanup(self.no_external)
        # A fixed clock for shell and stdlib Python implementations, without a
        # production-only test flag. No inherited PYTHONPATH enters the child.
        native_date = shutil.which('date')
        self.stub('date', '''#!/usr/bin/env python3
import os,sys
args=sys.argv[1:]
if not any(x in args for x in ('-d','--date','-r','--reference')):
 args=['-d','@'+os.environ['JV_TEST_NOW'],*args]
os.execv(NATIVE,['date',*args])
'''.replace('NATIVE', repr(native_date)))
        (self.hooks / 'sitecustomize.py').write_text('''import datetime,os,time
_real_datetime=datetime.datetime
time.time=lambda: float(os.environ['JV_TEST_NOW'])
class FixedDatetime(_real_datetime):
 @classmethod
 def now(cls,tz=None): return cls.fromtimestamp(time.time(),tz)
 @classmethod
 def utcnow(cls): return cls.fromtimestamp(time.time(),datetime.timezone.utc).replace(tzinfo=None)
datetime.datetime=FixedDatetime
''')
        native_flock = shutil.which('flock')
        self.stub('flock', "#!/usr/bin/env python3\nimport os,sys,pathlib\n"
                  "target=''\n"
                  "try: target=os.readlink('/proc/self/fd/'+sys.argv[-1])\n"
                  "except OSError: pass\n"
                  "if target==os.environ.get('JV_TEST_LOCK_PATH'):\n pathlib.Path(os.environ['JV_TEST_LOCK_MARKER']).touch()\n"
                  "if os.environ.get('JV_TEST_FAULT')=='lock':\n pathlib.Path(os.environ['JV_TEST_FAULT_MARKER']).touch(); sys.exit(73)\n"
                  "os.execv("+repr(native_flock)+",['flock',*sys.argv[1:]])\n")
        native_mv = shutil.which('mv')
        self.stub('mv', "#!/usr/bin/env python3\nimport os,sys,pathlib\n"
                  "if os.environ.get('JV_TEST_FAULT')=='rename':\n pathlib.Path(os.environ['JV_TEST_FAULT_MARKER']).touch(); sys.exit(74)\n"
                  "os.execv("+repr(native_mv)+",['mv',*sys.argv[1:]])\n")
        with (self.hooks / 'sitecustomize.py').open('a') as hook:
            hook.write('''import fcntl,pathlib
_real_flock=fcntl.flock
_real_replace=os.replace
_real_rename=os.rename
def checked_flock(fd,op):
 try: target=os.readlink('/proc/self/fd/'+str(fd))
 except OSError: target=''
 if op & fcntl.LOCK_EX and target==os.environ.get('JV_TEST_LOCK_PATH'):
  pathlib.Path(os.environ['JV_TEST_LOCK_MARKER']).touch()
 if op & fcntl.LOCK_EX and os.environ.get('JV_TEST_FAULT')=='lock':
  pathlib.Path(os.environ['JV_TEST_FAULT_MARKER']).touch()
  raise OSError('fixture lock failure')
 return _real_flock(fd,op)
def checked_replace(src,dst,*args,**kwargs):
 if os.environ.get('JV_TEST_FAULT')=='rename':
  pathlib.Path(os.environ['JV_TEST_FAULT_MARKER']).touch()
  raise OSError('fixture rename failure')
 return _real_replace(src,dst,*args,**kwargs)
def checked_rename(src,dst,*args,**kwargs):
 if os.environ.get('JV_TEST_FAULT')=='rename':
  pathlib.Path(os.environ['JV_TEST_FAULT_MARKER']).touch()
  raise OSError('fixture rename failure')
 return _real_rename(src,dst,*args,**kwargs)
fcntl.flock=checked_flock
os.replace=checked_replace
os.rename=checked_rename
''')
        self.env = {'PATH': str(self.bin), 'HOME': str(self.home), 'TMPDIR': str(self.tmp),
                    'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTHONPATH': str(self.hooks), 'JV_STATE_ROOT': str(self.state),
                    'JV_WATCHDOG_PROC_ROOT': str(self.proc), 'JV_ROLE': 'A',
                    'JV_TEST_CALLS': str(self.calls)}

    def no_external(self):
        self.case.assertFalse(self.calls.exists(), 'prohibited external command reached a recording stub')

    def stub(self, name, text):
        p = self.bin / name
        p.unlink(missing_ok=True)  # never overwrite an allowlist symlink's host target
        p.write_text(text); p.chmod(0o755)
        return p

    def environment(self, peer=0, overrides=None):
        env = {**self.env, 'JV_PROJECT_ID': ('alpha', 'beta')[peer],
               'JV_PROJECT_ROOT': str(self.projects[peer]), 'JV_TEST_NOW': str(self.now)}
        for key, value in (overrides or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = str(value)
        return env

    def store(self, peer=0):
        return self.state / ('alpha', 'beta')[peer]

    def bind(self, peer=0):
        root = self.store(peer); root.mkdir(parents=True, exist_ok=True)
        (root / 'project.json').write_text(json.dumps({'schema_version': 1, 'project_id': ('alpha', 'beta')[peer],
                                                     'project_root': str(self.projects[peer])})+'\n')
        (root / 'mail/cursors').mkdir(parents=True, exist_ok=True)
        return root

    def record(self, peer=0, letter='a', **values):
        root = self.bind(peer); (root / 'sessions').mkdir(exist_ok=True)
        data = {'schema_version': 1, 'project_id': ('alpha', 'beta')[peer], 'letter': letter,
                'runtime': 'claude', 'model': 'fixture-model', 'effort': 'xhigh',
                'workdir': str(self.projects[peer]), 'session_handle': None, 'state': 'booted',
                'capabilities': {}, 'lease': {'holder': None, 'epoch': 0, 'expires_at': None},
                'watcher': {'location': None, 'generation': 0}}
        data.update(values)
        p = root / 'sessions' / (letter+'.json'); p.write_text(json.dumps(data)+'\n')
        return p

    def cadence(self, peer=0, letter='a', **values):
        root = self.bind(peer); (root / 'cadence').mkdir(exist_ok=True)
        data = {'project_id': ('alpha', 'beta')[peer], 'role': letter, 'state': 'active',
                'heartbeat_at': iso(self.now-60), 'next_wake_at': iso(self.now+900),
                'wake_count': 3, 'cadence_seconds': 900, 'context': 'fixture'}
        data.update(values)
        p = root / 'cadence' / (letter+'.txt')
        p.write_text(''.join(str(k)+': '+str(v)+'\n' for k,v in data.items() if v is not None))
        return p

    def fields(self, path):
        return dict(line.split(': ', 1) for line in path.read_text().splitlines() if ': ' in line)

    def mail(self, sender='o', recipient='a', ages=(1801,), peer=0, consumed=0, cursor=True):
        root = self.bind(peer); base='from-'+sender+'-to-'+recipient
        lines=[(json.dumps({'project_id':('alpha','beta')[peer],'ts':iso(self.now-age),'from':sender,'to':recipient,'body':'fixture café'})+'\n').encode() for age in ages]
        p=root/'mail'/(base+'.jsonl');p.write_bytes(b''.join(lines))
        c=root/'mail/cursors'/('a-'+base+'.offset')
        if cursor:
            c.write_text(str(sum(len(x) for x in lines[:consumed]))+'\n')
        else:
            c.unlink(missing_ok=True)
        return p,c

    def process(self, peer=0, pid=4101, role='A', argv=('codex','--profile','alpha-thinking'), **env):
        p=self.proc/str(pid);p.mkdir(exist_ok=True)
        data={'JV_PROJECT_ID':('alpha','beta')[peer], 'JV_PROJECT_ROOT':str(self.projects[peer]), 'JV_ROLE':role, **env}
        (p/'environ').write_bytes(b''.join((k+'='+v).encode()+b'\0' for k,v in data.items()))
        (p/'cmdline').write_bytes(b''.join(str(x).encode()+b'\0' for x in argv))
        return p

    def run(self, script, *args, peer=0, env=None, timeout=10):
        self.case.assertFalse(runtime_findings(self.projects[peer]), 'unsafe/missing runtime closure; no child executed')
        return subprocess.run(['bash',str(self.projects[peer]/'scripts'/script),*map(str,args)],
                              cwd=self.projects[peer],env=self.environment(peer,env),stdin=subprocess.DEVNULL,
                              capture_output=True,text=True,timeout=timeout)

    def spawn(self, script, *args, peer=0, env=None):
        self.case.assertFalse(runtime_findings(self.projects[peer]), 'unsafe/missing runtime closure; no child executed')
        p=subprocess.Popen(['bash',str(self.projects[peer]/'scripts'/script),*map(str,args)],cwd=self.projects[peer],
                           env=self.environment(peer,env),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def reap():
            if p.poll() is None: p.kill()  # only the Popen child created by THIS fixture
            p.communicate(timeout=5)
        self.case.addCleanup(reap)
        return p

    def alerts(self, peer=0):
        p=self.store(peer)/'watchdog/alerts.jsonl'
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def wait(self, predicate, label):
        deadline=time.monotonic()+6
        while not predicate():
            self.case.assertLess(time.monotonic(),deadline,'fixture deadline: '+label)
            time.sleep(.01)

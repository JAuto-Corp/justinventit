"""W-C5 synthetic provider files, fake df/sinks, and observable read budgets."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from liveness_fixture import ALLOWED, Fixture as BaseFixture, iso
from observability_guard import runtime_findings
from test_launch import opened, snapshot

OBSERVABILITY_ALLOWED = ALLOWED


class Fixture(BaseFixture):
    def __init__(self, case, sources):
        super().__init__(case, sources)
        self.host = self.root / 'shared host'
        self.providers = self.root / 'provider data'; self.providers.mkdir()
        self.codex = self.providers / 'sessions'; self.codex.mkdir()
        self.anthropic = self.providers / 'anthropic.json'
        self.primary = self.root / 'disk primary'; self.primary.mkdir()
        self.secondary = self.root / 'disk secondary'; self.secondary.mkdir()
        self.df_data = self.root / 'df-data.json'
        self.df_calls = self.root / 'df-calls.jsonl'
        self.sink = self.root / 'sink.jsonl'
        self.io_receipt = self.root / 'reads.jsonl'
        self.fault = self.root / 'fault-reached'
        self.stub('rm', '#!/usr/bin/env python3\nimport os,pathlib,sys\n'
                  "pathlib.Path(os.environ['JV_TEST_CALLS']).write_text('rm invoked')\nsys.exit(91)\n")
        self.stub('df', '''#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]
with pathlib.Path(os.environ['JV_OBS_DF_CALLS']).open('a') as out: out.write(json.dumps(args)+'\\n')
target=args[-1]
data=json.loads(pathlib.Path(os.environ['JV_OBS_DF_DATA']).read_text())
if target not in data: sys.exit(93)
row=data[target]
if row.get('error'): sys.exit(74)
if row.get('malformed'): print('not a measurement');sys.exit(0)
if '--output=pcent' in args: print('Use%\\n'+str(row['percent'])+'%')
elif '--output=avail' in args and '-BG' in args: print('Avail\\n'+str(row['gib'])+'G')
else: sys.exit(94)
''')
        self.adapter = self.stub('fixture-notifier', '''#!/usr/bin/env python3
import json,os,pathlib,sys,time
body=sys.stdin.read(); row=json.loads(body)
with pathlib.Path(os.environ['JV_OBS_SINK']).open('a') as out: out.write(json.dumps({'argv':sys.argv[1:],'record':row})+'\\n')
mode=os.environ.get('JV_OBS_SINK_MODE','ok')
if mode=='timeout': time.sleep(20)
sys.exit(75 if mode=='fail' else 0)
''')
        for peer in range(2): self.bind(peer)
        self.disk()
        self.env.update(JV_HOST_ROOT=str(self.host), JV_USAGE_CODEX_ROOT=str(self.codex),
                        JV_USAGE_ANTHROPIC_FILE=str(self.anthropic), JV_DISK_ROOT=str(self.primary),
                        JV_DISK_SECONDARY_ROOT=str(self.secondary), JV_ROLE='o',
                        JV_OBS_DF_DATA=str(self.df_data), JV_OBS_DF_CALLS=str(self.df_calls),
                        JV_OBS_SINK=str(self.sink), JV_OBS_READS=str(self.io_receipt),
                        JV_OBS_PROVIDERS=str(self.providers), JV_TEST_FAULT_MARKER=str(self.fault))
        # Observes actual returned bytes for selected fixture data. It does not
        # enforce the cap, so read-all-then-slice produces a discriminating log.
        with (self.hooks / 'sitecustomize.py').open('a') as out:
            out.write('''
import builtins,io,json
_builtin_open=builtins.open
_io_open=io.open
def selected(path):
 try:
  p=os.path.abspath(os.fspath(path))
  return p.startswith(os.environ['JV_OBS_PROVIDERS']+os.sep) or p==os.environ['JV_HOST_ROOT']+'/observability/usage.tsv'
 except (TypeError,KeyError): return False
def note(path,action,offset,amount):
 with _builtin_open(os.environ['JV_OBS_READS'],'a') as out:
  out.write(json.dumps({'path':os.path.abspath(os.fspath(path)),'action':action,'offset':offset,'bytes':amount})+'\\n')
class ReadSpy:
 def __init__(self,file,path): self.file=file;self.path=path
 def __getattr__(self,name): return getattr(self.file,name)
 def __enter__(self): return self
 def __exit__(self,*args): return self.file.__exit__(*args)
 def read(self,*args):
  offset=self.file.tell(); data=self.file.read(*args)
  note(self.path,'read',offset,len(data.encode() if isinstance(data,str) else data));return data
 def readline(self,*args):
  offset=self.file.tell(); data=self.file.readline(*args)
  note(self.path,'read',offset,len(data.encode() if isinstance(data,str) else data));return data
 def readinto(self,buffer):
  offset=self.file.tell(); n=self.file.readinto(buffer);note(self.path,'read',offset,n or 0);return n
 def seek(self,*args):
  offset=self.file.seek(*args);note(self.path,'seek',offset,0);return offset
 def __iter__(self): return self
 def __next__(self):
  data=self.readline()
  if not data: raise StopIteration
  return data
class PartialAppend:
 def __init__(self,file): self.file=file
 def __getattr__(self,name): return getattr(self.file,name)
 def __enter__(self): return self
 def __exit__(self,*args): return self.file.__exit__(*args)
 def write(self,data):
  self.file.write(data[:max(1,len(data)//2)]);self.file.flush()
  with _builtin_open(os.environ['JV_TEST_FAULT_MARKER'],'w') as out: out.write('partial append')
  raise OSError('fixture partial append failure')
def wrapped(original,path,mode='r',*args,**kwargs):
 absolute=os.path.abspath(os.fspath(path)) if isinstance(path,(str,bytes,os.PathLike)) else ''
 fault=os.environ.get('JV_OBS_FAULT')
 if any(c in mode for c in 'wax') and ((fault=='ledger' and absolute.endswith('/observability/usage.tsv')) or (fault=='sink' and absolute.endswith('/observability/disk-alerts.jsonl'))):
  with _builtin_open(os.environ['JV_TEST_FAULT_MARKER'],'w') as out: out.write(fault)
  raise OSError('fixture append failure')
 file=original(path,mode,*args,**kwargs)
 if 'a' in mode and ((fault=='partial-ledger' and absolute.endswith('/observability/usage.tsv')) or (fault=='partial-sink' and absolute.endswith('/observability/disk-alerts.jsonl'))):
  return PartialAppend(file)
 return ReadSpy(file,path) if 'r' in mode and selected(path) else file
builtins.open=lambda path,mode='r',*a,**k: wrapped(_builtin_open,path,mode,*a,**k)
io.open=lambda path,mode='r',*a,**k: wrapped(_io_open,path,mode,*a,**k)
''')

    @property
    def ledger(self): return self.host / 'observability/usage.tsv'

    def anthropic_data(self, used=40, age=0, **extra):
        data={'ts':iso(self.now-age), 'rate_limits':{'seven_day':{'used_percentage':used,'resets_at':self.now+302400}}}
        data['rate_limits'].update(extra)
        self.anthropic.write_text(json.dumps(data)+'\n')
        return self.anthropic

    def rollout(self, used=40, window=10080, *, name='rollout.jsonl', age=0, rate_limits=None):
        path=self.codex/'2026/01/01'/name;path.parent.mkdir(parents=True,exist_ok=True)
        limits=rate_limits or {'secondary':{'used_percent':used,'window_minutes':window,'resets_at':self.now+window*30}}
        path.write_text(json.dumps({'type':'event_msg','payload':{'type':'token_count','rate_limits':limits}})+'\n')
        os.utime(path,(self.now-age,self.now-age));return path

    def disk(self, percent=84, gib=10, secondary=None):
        self.df_data.write_text(json.dumps({str(self.primary):{'percent':percent,'gib':50},
                                           str(self.secondary):secondary or {'percent':20,'gib':gib}}))

    def history(self, rows):
        self.ledger.parent.mkdir(parents=True,exist_ok=True)
        self.ledger.write_text(''.join('\t'.join(map(str,row))+'\n' for row in rows))

    def rows(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def read_totals(self):
        totals={}
        for row in self.rows(self.io_receipt): totals[row['path']]=totals.get(row['path'],0)+row['bytes']
        return totals

    def run(self, script='pace.sh', *args, peer=0, env=None, timeout=18):
        self.case.assertFalse(runtime_findings(self.projects[peer]),'source refusal; no candidate child')
        return subprocess.run(['bash',str(self.projects[peer]/'scripts'/script),*map(str,args)],
                              cwd=self.projects[peer],env=self.environment(peer,env),capture_output=True,
                              text=True,stdin=subprocess.DEVNULL,timeout=timeout)

    def start(self, peer=0):
        self.case.assertFalse(runtime_findings(self.projects[peer]),'source refusal; no candidate child')
        p=subprocess.Popen(['bash',str(self.projects[peer]/'scripts/disk-watch.sh')],cwd=self.projects[peer],
                           env=self.environment(peer),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def reap():
            if p.poll() is None:p.kill()
            p.communicate(timeout=5)
        self.case.addCleanup(reap);return p

    def report(self, result):
        body=result.stdout.removeprefix('[usage] ').strip()
        self.case.assertTrue(body,'missing observation report')
        return json.loads(body)

    def model_id(self, name): return 'anthropic-model-'+hashlib.sha256(name.encode()).hexdigest()

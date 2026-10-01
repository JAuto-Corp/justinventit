#!/usr/bin/env python3
"""File-backed cadence publication and limited liveness observation.

No recovery or external notification. The shell entry verifies the shared
project binding before this module accesses the configured store.
"""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid

MAX_NUMBER=2147483647
FIELDS={'project_id','role','state','heartbeat_at','next_wake_at','wake_count','cadence_seconds',
        'doorbell','conclusion','brief','context'}
ACTIVE={'active','awake','sleeping'}


def integer(value,minimum=0,maximum=MAX_NUMBER):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,10}',value):
        raise ValueError('invalid decimal integer')
    n=int(value)
    if not minimum<=n<=maximum:raise ValueError('integer outside supported range')
    return n


def stamp(epoch):
    return datetime.fromtimestamp(epoch,timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def epoch(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z',value):
        raise ValueError('invalid UTC timestamp')
    return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp())


def letter(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z]',value):raise ValueError('role must be one ASCII letter')
    return value.lower()


def earned(data):
    brief=Path(data.get('brief',''))
    return bool(data.get('conclusion','').strip()) and brief.is_absolute() and brief.is_file()


def validate(data,role,strict=True):
    if data.get('project_id')!=os.environ['JV_PROJECT_ID'] or data.get('role')!=role:
        raise ValueError('cadence project/role identity mismatch')
    if not set(data)<=FIELDS:raise ValueError('unknown cadence field')
    state=data.get('state')
    if state not in ACTIVE|{'standby','dormant','booted','parked'}:raise ValueError('invalid cadence state')
    integer(data.get('wake_count'));seconds=integer(data.get('cadence_seconds'))
    epoch(data.get('heartbeat_at'))
    if state in ACTIVE:
        if seconds==0:raise ValueError('active cadence must be positive')
        epoch(data.get('next_wake_at'))
    elif state=='standby':
        if seconds or data.get('next_wake_at')!='event' or data.get('doorbell')!='mailbox:'+role:
            raise ValueError('standby requires zero cadence and its own mailbox doorbell')
    elif state=='dormant':
        if seconds or data.get('next_wake_at')!='none':raise ValueError('invalid dormant intent')
        if strict and not earned(data):raise ValueError('dormancy requires conclusion and existing absolute brief')
    return data


def read_cadence(path,role,strict=True):
    text=path.read_bytes().decode('utf-8')
    if '\r' in text:raise ValueError('CR in cadence record')
    data={}
    for line in text.splitlines():
        if ': ' not in line:raise ValueError('malformed cadence field')
        key,value=line.split(': ',1)
        if key in data:raise ValueError('duplicate cadence field')
        data[key]=value
    return validate(data,role,strict)


@contextmanager
def locked(path):
    with path.open('a') as handle:
        deadline=time.monotonic()+2
        while True:
            try:
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise ValueError('lock wait exceeded two seconds')
                time.sleep(.01)
        try:yield
        finally:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def atomic(path,text):
    temporary=None
    try:
        fd,name=tempfile.mkstemp(prefix='.'+path.stem+'.',dir=path.parent)
        temporary=Path(name)
        with os.fdopen(fd,'w') as output:
            output.write(text);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def publish(store,args,heartbeat=False):
    if heartbeat:
        if args:raise ValueError('heartbeat takes no arguments')
        role=letter(os.environ.get('JV_ROLE'))
    else:
        if len(args)<2:raise ValueError('usage: cadence.sh letter awake|sleeping|standby|dormant [seconds] [options] [context]')
        role=letter(args[0])
        if os.environ.get('JV_ROLE') and letter(os.environ['JV_ROLE'])!=role:raise ValueError('JV_ROLE differs from writer role')
    path=store/'cadence'/(role+'.txt')
    with locked(path.parent/('.'+role+'.lock')):
        old=read_cadence(path,role) if path.exists() else None
        now=int(time.time())
        if heartbeat:
            if old is None:raise ValueError('heartbeat requires an existing cadence declaration')
            data={**old,'heartbeat_at':stamp(now)}
        else:
            state=args[1]
            if state not in {'awake','sleeping','standby','dormant'}:raise ValueError('unsupported cadence state')
            words=list(args[2:]);seconds=900
            if words and re.fullmatch(r'[+-]?[0-9]+',words[0]):
                raw=words.pop(0)
                seconds=integer(raw,minimum=1) if state in {'awake','sleeping'} else 0
            options={};context=[]
            while words:
                word=words.pop(0)
                if word.startswith('--'):
                    if word not in {'--doorbell','--conclusion','--brief'} or not words or word[2:] in options:
                        raise ValueError('invalid cadence option')
                    options[word[2:]]=words.pop(0)
                else:context.append(word)
            if any('\n' in x or '\r' in x for x in [*context,*options.values()]):raise ValueError('line injection in cadence input')
            count=integer(old['wake_count']) if old else 0
            if state=='awake':count+=1
            data={'project_id':os.environ['JV_PROJECT_ID'],'role':role,'state':'active' if state in {'awake','sleeping'} else state,
                  'heartbeat_at':stamp(now),'next_wake_at':stamp(now+seconds) if state in {'awake','sleeping'} else ('event' if state=='standby' else 'none'),
                  'wake_count':str(count),'cadence_seconds':str(seconds if state in {'awake','sleeping'} else 0),
                  **options,'context':' '.join(context)}
        validate(data,role)
        atomic(path,''.join(key+': '+value+'\n' for key,value in data.items()))


def backlog(store,role,now):
    mail=store/'mail'
    if not mail.is_dir():raise ValueError('mail store is missing or unreadable')
    oldest=None
    for path in sorted(mail.iterdir()):
        match=re.fullmatch(r'from-([a-z])-to-('+role+r'|all)\.jsonl',path.name)
        if not match or match[1]==role:continue
        content=path.read_bytes()
        cursor=mail/'cursors'/(role+'-'+path.stem+'.offset')
        offset=integer(cursor.read_text().strip()) if cursor.exists() else 0
        if offset>len(content) or (offset and content[offset-1:offset]!=b'\n'):
            raise ValueError('mail cursor is outside a complete line boundary')
        for line in content[offset:].splitlines(keepends=True):
            if not line.endswith(b'\n'):raise ValueError('incomplete mail line')
            event=json.loads(line)
            if not isinstance(event,dict):raise ValueError('mail event is not an object')
            ts=epoch(event.get('ts'));oldest=ts if oldest is None else min(oldest,ts)
    return max(0,now-oldest) if oldest is not None else 0


def interactive(argv):
    if not argv:return False
    runtime=Path(argv[0]).name
    if runtime=='claude':
        return not any(x=='--print' or x.startswith('--print=') or x.startswith('-p') for x in argv[1:])
    if runtime!='codex':return False
    values={'--profile','-p','--config','-c','--model','-m','--sandbox','-s','--cd','-C','--add-dir','--enable','--disable','--ask-for-approval','-a'}
    args=iter(argv[1:])
    for arg in args:
        if arg in values:
            if next(args,None) is None:return False
        elif arg.startswith('-'):
            continue
        else:
            return arg not in {'exec','e','review','app-server','mcp','mcp-server','login','logout','completion','debug','help'}
    return True


def process_status(role):
    configured=os.environ.get('JV_WATCHDOG_PROC_ROOT')
    if not configured:return 'unavailable'
    root=Path(configured)
    if not root.is_absolute():raise ValueError('JV_WATCHDOG_PROC_ROOT must be absolute')
    unknown=False
    try:entries=list(root.iterdir())
    except OSError:return 'unknown'
    for entry in entries:
        if not entry.name.isascii() or not entry.name.isdecimal():continue
        try:
            raw=(entry/'environ').read_bytes();cmd=(entry/'cmdline').read_bytes()
            if not raw.endswith(b'\0') or not cmd.endswith(b'\0'):raise ValueError('truncated process evidence')
            pairs=[item.decode().split('=',1) for item in raw[:-1].split(b'\0')]
            if any(len(p)!=2 for p in pairs):raise ValueError('malformed process environment')
            env=dict(pairs)
            if len(env)!=len(pairs):raise ValueError('duplicate process environment field')
            argv=[x.decode() for x in cmd[:-1].split(b'\0')]
            if (env.get('JV_PROJECT_ID')==os.environ['JV_PROJECT_ID'] and
                env.get('JV_PROJECT_ROOT')==os.environ['JV_PROJECT_ROOT'] and
                env.get('JV_ROLE')==role.upper() and interactive(argv)):
                return 'present'
        except (OSError,ValueError,UnicodeError):unknown=True
    return 'unknown' if unknown else 'absent'


def decision(store,role,registered,now):
    row={'kind':'seat','project_id':os.environ['JV_PROJECT_ID'],'role':role,'registered':registered,
         'reasons':[],'grace':2700,'_unknown':False}
    path=store/'cadence'/(role+'.txt')
    if not path.exists():
        row['reasons']=['missing-cadence'];row['_unknown']=True;return row
    try:
        if registered:
            record=json.loads((store/'sessions'/(role+'.json')).read_text())
            if not isinstance(record,dict) or record.get('project_id')!=os.environ['JV_PROJECT_ID'] or record.get('letter')!=role:
                raise ValueError('invalid seat record identity')
        data=read_cadence(path,role,strict=False)
        state=data['state'];row['state']=state
        row['grace']=max(2700,2*integer(data['cadence_seconds']))
        if state in ACTIVE:
            if now-epoch(data['next_wake_at'])>=row['grace']:row['reasons'].append('schedule-overdue')
            if now-epoch(data['heartbeat_at'])>3600:row['reasons'].append('heartbeat-floor')
        elif state=='dormant' and not earned(data):
            row['reasons'].append('unearned-dormancy');row['_unknown']=True
        elif state=='standby':
            row['observation']='limited: process presence and mail only; loop/canary health unproven'
            try:
                age=backlog(store,role,now);row['backlog_seconds']=age
                if age>1800:row['reasons'].append('mail-backlog')
            except (OSError,ValueError,UnicodeError):
                row['backlog_seconds']=None;row['reasons'].append('mail-unknown');row['_unknown']=True
            row['process']=process_status(role)
            if row['process']=='unknown':row['_unknown']=True
    except (OSError,ValueError,UnicodeError) as error:
        row['reasons'].append('invalid-cadence');row['_unknown']=True
        row['diagnostic']=str(error)
    return row


def checkpoint(path):
    if not path.exists():return None
    data=json.loads(path.read_text())
    if (not isinstance(data,dict) or type(data.get('count')) is not int or not 1<=data['count']<=1000000 or
        type(data.get('last_alert')) is not int or data['last_alert']<0 or
        not isinstance(data.get('episode'),str) or not re.fullmatch('[a-f0-9]{32}',data['episode'])):
        raise ValueError('invalid observer delivery checkpoint')
    return data


def report(store,row,now,dry):
    path=store/'watchdog'/(row['role']+'.json')
    previous=checkpoint(path)
    if not row['reasons']:
        if not row['_unknown'] and not dry:path.unlink(missing_ok=True)
        return False
    count=previous['count'] if previous else 0
    interval=min(86400,row['grace']*2**min(max(count-1,0),20))
    if previous and now-previous['last_alert']<interval:return False
    if dry:return True
    episode=previous['episode'] if previous else uuid.uuid4().hex
    alert={'project_id':row['project_id'],'role':row['role'],'reasons':row['reasons'],'episode':episode,'reported_at':stamp(now)}
    with (store/'watchdog/alerts.jsonl').open('a') as output:
        output.write(json.dumps(alert,sort_keys=True)+'\n');output.flush();os.fsync(output.fileno())
    # An append followed by a failed checkpoint can repeat on retry; not exactly once.
    atomic(path,json.dumps({'episode':episode,'count':min(count+1,1000000),'last_alert':now},sort_keys=True)+'\n')
    return True


def observe(store,args):
    if args not in ([],['--dry-run']):raise ValueError('usage: stall-watchdog.sh [--dry-run]')
    dry=bool(args);watchdog=store/'watchdog'
    if not dry:watchdog.mkdir(exist_ok=True)
    # ponytail: one local project sweep lock; per-seat locks only if sweep throughput requires it.
    with nullcontext() if dry else locked(watchdog/'.sweep.lock'):
        records={p.stem for p in (store/'sessions').glob('*.json') if re.fullmatch('[a-z]',p.stem)}
        cadences={p.stem for p in (store/'cadence').glob('*.txt') if re.fullmatch('[a-z]',p.stem)}
        roles=sorted(records|cadences);now=int(time.time());unknown=reported=0
        for role in roles:
            row=decision(store,role,role in records,now)
            try:
                row['reported']=report(store,row,now,dry);reported+=int(row['reported'])
            except (OSError,ValueError,UnicodeError) as error:
                row['_unknown']=True;row['reported']=False
                print('observer report failed for '+role+': '+str(error),file=sys.stderr)
            unknown+=int(row.pop('_unknown'))
            print(json.dumps(row,sort_keys=True))
        print(json.dumps({'kind':'complete','project_id':os.environ['JV_PROJECT_ID'],'enumerated':len(roles),
                          'evaluated':len(roles)-unknown,'unknown':unknown,'reported':reported},sort_keys=True))
        return int(bool(unknown))


def main():
    try:
        mode,*args=sys.argv[1:];store=Path(os.environ['JV_STORE'])
        if mode=='observe':
            if os.environ.get('JV_WATCHDOG_PROC_ROOT') and not Path(os.environ['JV_WATCHDOG_PROC_ROOT']).is_absolute():
                raise ValueError('JV_WATCHDOG_PROC_ROOT must be absolute')
            return observe(store,args)
        if mode not in {'cadence','heartbeat'}:raise ValueError('invalid liveness operation')
        publish(store,args,heartbeat=mode=='heartbeat');return 0
    except (OSError,ValueError,KeyError,UnicodeError,OverflowError) as error:
        print('liveness refused: '+str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())

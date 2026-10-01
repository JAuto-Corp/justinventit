#!/usr/bin/env python3
"""Explicit observations, not account authority. See HOST_OBSERVABILITY.md.

Extracted from installed usage/disk tools, 2026-10-01. Cooperating reviewed
code and static filesystem checks are the threat boundary, not hostile isolation.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time

MIB=1048576
WEEK=604800


class Unavailable(Exception): pass


def checked(value, kind, missing=False):
    if not value or not os.path.isabs(value) or any(p in ('.','..') for p in value.split('/')):
        raise Unavailable('invalid-path')
    path=Path(value)
    chain=list(reversed(path.parents))+[path]
    for part in chain:
        try:info=part.lstat()
        except FileNotFoundError:
            if missing:continue
            raise Unavailable('missing-path')
        if stat.S_ISLNK(info.st_mode):raise Unavailable('aliased-path')
        directory=part!=path or kind=='dir'
        if directory:
            if not stat.S_ISDIR(info.st_mode) or not os.access(part,os.X_OK):raise Unavailable('inaccessible-directory')
        elif not stat.S_ISREG(info.st_mode):raise Unavailable('nonregular-file')
    return path


def overlap(left,right):return left==right or left in right.parents or right in left.parents


def number(value,maximum=100):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=maximum:
        raise Unavailable('invalid-number')
    return float(value)


def integer(value,minimum=0,maximum=10**12):
    if type(value) is not int or not minimum<=value<=maximum:raise Unavailable('invalid-integer')
    return value


def bounded(path,cap,tail=False):
    with open(path,'rb') as source:
        size=os.fstat(source.fileno()).st_size
        if size>cap and not tail:raise Unavailable('oversized-input')
        offset=max(0,size-cap) if tail else 0
        source.seek(offset)
        data=source.read(min(size,cap))
    if offset:data=data.partition(b'\n')[2]
    return data, bool(offset)


def common():
    host=checked(os.environ.get('JV_HOST_ROOT'),'dir',missing=True)
    if host==Path('/') or overlap(host,Path(os.environ['JV_STORE'])):raise Unavailable('overlapping-state')
    for key in ('JV_USAGE_CODEX_ROOT','JV_USAGE_ANTHROPIC_FILE'):
        value=os.environ.get(key)
        if value and os.path.isabs(value) and overlap(host,Path(os.path.abspath(value))):raise Unavailable('overlapping-input')
    directory=host/'observability'
    checked(str(directory),'dir',missing=True)
    for name in ('observability.lock','usage.tsv','disk-state.json','disk-alerts.jsonl'):
        checked(str(directory/name),'file',missing=True)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    return directory


@contextmanager
def locked(directory):
    with (directory/'observability.lock').open('a+') as lock:
        deadline=time.monotonic()+1
        while True:
            try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise Unavailable('lock-timeout')
                time.sleep(.02)
        yield


def quota(series,value,reset,window,age,now,short=False):
    used=number(value);reset=integer(reset);window=integer(window,1)
    if not math.isfinite(age) or age<0:raise Unavailable('unknown-age')
    row={'series':series,'used':used,'resets_at':reset,'window_seconds':window,'stale':age>1800}
    if short:return row
    left=max(0,(reset-now)/3600)
    target=max(0,min(100,(window-(reset-now))/window*100))
    delta=used-target
    row.update(target=round(target,6),verdict='on-pace' if abs(delta)<=10 else ('ahead' if delta>0 else 'behind'),
               expired=reset<=now,sustainable_per_hour=round((100-used)/left,6) if left else None,
               burn_per_hour=None)
    return row


def anthropic(value,now):
    path=checked(value,'file');data=json.loads(bounded(path,MIB)[0])
    stamp=datetime.strptime(data['ts'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
    age=now-stamp
    limits=data['rate_limits'];rows=[]
    for key,series,window in (('seven_day','anthropic-wk',WEEK),('five_hour','anthropic-short',18000)):
        if key in limits:
            item=limits[key]
            rows.append(quota(series,item.get('used_percentage',item.get('utilization')),item['resets_at'],window,age,now,key=='five_hour'))
    for item in limits.get('model_scoped',[]):
        name=item.get('display_name')
        if not isinstance(name,str):continue
        series='anthropic-model-'+hashlib.sha256(name.encode()).hexdigest()
        rows.append(quota(series,item.get('used_percentage',item.get('utilization')),item['resets_at'],WEEK,age,now))
    if not rows:raise Unavailable('missing-observations')
    return rows


def codex(value,now):
    root=checked(value,'dir')
    files=list(root.glob('*/*/*/*.jsonl'))
    for path in files:checked(str(path),'file')
    files.sort(key=lambda path:(path.stat().st_mtime,str(path)),reverse=True)
    short_rows=[]
    for path in files[:6]:
        age=now-path.stat().st_mtime
        if age<0:continue
        data,_=bounded(path,400000,tail=True)
        for line in reversed(data.splitlines()):
            try:
                record=json.loads(line)
                if not isinstance(record,dict):continue
                limits=record.get('rate_limits')
                if limits is None:limits=record.get('payload',{}).get('rate_limits')
                if not isinstance(limits,dict):continue
                weekly=[];short=[]
                for key in ('primary','secondary'):
                    item=limits.get(key)
                    if not isinstance(item,dict):continue
                    minutes=integer(item.get('window_minutes'),1)
                    if minutes==10080:
                        weekly.append(quota('openai-wk',item.get('used_percent'),item.get('resets_at'),minutes*60,age,now))
                    elif minutes<1440:
                        short.append(quota('openai-short',item.get('used_percent'),item.get('resets_at'),minutes*60,age,now,True))
                if not short_rows:short_rows=short
                if len(weekly)!=1:continue
                rows=weekly+short
                credits=limits.get('credits',{})
                if credits.get('has_credits') is True and credits.get('unlimited') is False:
                    balance=credits.get('balance')
                    if isinstance(balance,str) and re.fullmatch(r'[0-9]{1,20}(?:\.[0-9]{1,10})?',balance):balance=float(balance)
                    rows.append({'series':'openai-credits','balance':number(balance,10**20),'spend_per_hour':None})
                return rows,False
            except (ValueError,TypeError,KeyError,AttributeError,Unavailable):continue
    return short_rows,True


def history(path,errors,warnings):
    if not path.exists():return []
    data,truncated=bounded(path,MIB,tail=True)
    if truncated:warnings.append('history-truncated')
    rows=[]
    for line in data.splitlines():
        if not line.strip():continue
        try:
            stamp,name,value,reset,window=line.decode().split('\t')
            point=(int(stamp),name,float(value),int(reset),int(window))
            if not math.isfinite(point[2]) or point[2]<0:raise ValueError()
            rows.append(point)
        except (ValueError,UnicodeError):
            if 'history-invalid' not in errors:errors.append('history-invalid')
    return rows


def usage(directory,now,errors,warnings):
    observations=[]
    for label,key,collect in (('anthropic','JV_USAGE_ANTHROPIC_FILE',anthropic),('openai','JV_USAGE_CODEX_ROOT',codex)):
        if key not in os.environ:continue
        try:
            rows=collect(os.environ[key],now)
            if label=='openai':
                rows,incomplete=rows
                if incomplete:errors.append('openai-weekly-unavailable')
            observations.extend(rows)
        except (OSError,ValueError,TypeError,KeyError,AttributeError,Unavailable):errors.append(label+'-unavailable')
    if not observations and not errors:errors.append('providers-unconfigured')
    ledger=directory/'usage.tsv'
    try:prior=history(ledger,errors,warnings)
    except (OSError,Unavailable):prior=[];errors.append('history-unavailable')
    fresh=[]
    for row in observations:
        if row['series']=='openai-credits':fresh.append((int(now),row['series'],row['balance'],0,0))
        elif 'target' in row and not row['expired']:
            fresh.append((int(now),row['series'],row['used'],row['resets_at'],row['window_seconds']))
    if fresh:
        try:
            with ledger.open('a') as out:out.write(''.join('\t'.join(map(str,row))+'\n' for row in fresh))
        except OSError:errors.append('history-write-failed')
    for row in observations:
        credit=row['series']=='openai-credits'
        if not credit and ('target' not in row or row['expired']):continue
        reset=0 if credit else row['resets_at']
        window=0 if credit else row['window_seconds']
        pts=sorted(((p[0],p[2]) for p in prior+fresh if p[1]==row['series'] and p[3]==reset and p[4]==window and now-10800<=p[0]<=now),key=lambda point:point[0])
        if len(pts)>=2 and pts[-1][0]-pts[0][0]>=1800:
            rate=(pts[-1][1]-pts[0][1])/((pts[-1][0]-pts[0][0])/3600)
            row['spend_per_hour' if credit else 'burn_per_hour']=round(-rate if credit else rate,6)
    return observations


def checkpoint(path,keys):
    fd,temp=tempfile.mkstemp(prefix='.disk-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as out:json.dump(keys,out);out.write('\n')
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def notify(directory,row):
    body=json.dumps(row,separators=(',',':'))+'\n'
    adapter=os.environ.get('JV_OBSERVABILITY_NOTIFY_BIN')
    if adapter is not None:
        path=checked(adapter,'file')
        if not os.access(path,os.X_OK):raise Unavailable('adapter-unavailable')
        result=subprocess.run([str(path)],input=body,text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        if result.returncode:raise Unavailable('adapter-failed')
    else:
        with (directory/'disk-alerts.jsonl').open('a') as out:out.write(body)


def disk(directory,now,errors):
    state=directory/'disk-state.json';keys=[];state_ok=True
    if state.exists():
        try:
            keys=json.loads(bounded(state,MIB)[0])
            if not isinstance(keys,list) or any(not isinstance(k,str) or not re.fullmatch('[0-9a-f]{64}',k) for k in keys):raise ValueError()
        except (OSError,ValueError,TypeError,Unavailable):state_ok=False;errors.append('disk-state-unavailable')
    observations=[]
    for label,envkey in (('primary','JV_DISK_ROOT'),('secondary','JV_DISK_SECONDARY_ROOT')):
        if label=='secondary' and envkey not in os.environ:continue
        try:
            target=checked(os.environ.get(envkey),'dir')
            args=['df','--output=pcent','--',str(target)] if label=='primary' else ['df','-BG','--output=avail','--',str(target)]
            r=subprocess.run(args,capture_output=True,text=True,timeout=5)
            if r.returncode:raise Unavailable('measurement-failed')
            lines=r.stdout.splitlines()
            m=re.fullmatch(r'\s*([0-9]{1,12})'+('%' if label=='primary' else 'G')+r'\s*',lines[-1]) if lines else None
            if not m:raise Unavailable('invalid-measurement')
            value=int(m[1])
            if label=='primary' and value>100:raise Unavailable('invalid-measurement')
            row={'project_id':os.environ['JV_PROJECT_ID'],'target':str(target),'metric':'used-percent' if label=='primary' else 'available-gib',
                 'percent' if label=='primary' else 'gib':value}
            observations.append(row)
            due=value>=85 if label=='primary' else value<10
            bucket=value//(5 if label=='primary' else 2)*(5 if label=='primary' else 2)
            day=datetime.fromtimestamp(now,timezone.utc).strftime('%Y-%m-%d')
            key=hashlib.sha256(json.dumps([day,str(target),row['metric'],bucket]).encode()).hexdigest()
            if due and key not in keys and state_ok:
                notify(directory,row)
                checkpoint(state,keys+[key]);keys.append(key)
        except (OSError,ValueError,TypeError,Unavailable,subprocess.TimeoutExpired):errors.append(label+'-unavailable')
    return observations


def main():
    mode=sys.argv[1];hook=mode=='hook';errors=[];warnings=[];observations=[]
    os.umask(0o077)
    try:
        directory=common()
        with locked(directory):
            observations=disk(directory,time.time(),errors) if mode=='disk' else usage(directory,time.time(),errors,warnings)
    except (OSError,ValueError,TypeError,KeyError,Unavailable):errors.append('configuration-or-state-unavailable')
    report={'observations':observations,'errors':errors,'warnings':warnings}
    if hook:
        if observations:
            body=json.dumps(report,separators=(',',':'))
            while len(('[usage] '+body+'\n').encode())>4096 and observations:
                observations.pop();report['truncated']=True;body=json.dumps(report,separators=(',',':'))
            print('[usage] '+body)
        return 0
    print(json.dumps(report,separators=(',',':')))
    return 2 if errors else 0


if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""W-C3 T1–T7: bounded positive/refusal cells, including SPEC folds F1–F5.

Generated closure absence is setup RED, not a behavioral mutant kill. All
runtime children pass the source gate and use scratch-only process evidence.
"""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from liveness_guard import CLOSURE, render_findings, runtime_findings
from liveness_fixture import Fixture, EPOCH, iso, opened, snapshot

PROJECT = Path(os.environ.get('JV_LIVENESS_PROJECT', Path(__file__).resolve().parents[2]))
PEER = Path(os.environ.get('JV_LIVENESS_PEER', PROJECT))
WRAPPER = '../.claude/hooks/stop/actions/heartbeat-writer.sh'


class Containment(unittest.TestCase):
    def test_t6_f5_source_gate_positive_and_refusals(self):
        """I6/F5: dangerous seeds are DATA; no unsafe child is launched."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in CLOSURE:
                p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('#!/bin/sh\nexit 0\n')
            self.assertEqual(runtime_findings(root), [])
            target = root / 'scripts/stall-watchdog.sh'
            seeds = ('if kill -TERM "$pid"; then :; fi', '/usr/bin/tmux send-keys x',
                     '/bin/kill -TERM "$pid"', 'if /bin/kill -TERM "$pid"; then :; fi',
                     'kill -9 "$pid"', 'builtin kill -TERM "$pid"', 'tmux send-keys x',
                     'exec curl https://invalid.example', 'subprocess.run(["anything"])',
                     'os.kill(123,9)', '"$RESPAWN_HOOK" a', 'cat /proc/123/environ',
                     'cat /home/'+'justi/private', 'echo JA'+'UTO_ROLE')
            for seed in seeds:
                with self.subTest(seed=seed):
                    target.write_text('#!/bin/sh\n'+seed+'\n')
                    self.assertTrue(runtime_findings(root), 'source-gate bypass; unsafe child remains unexecuted')
            target.write_text('#!/bin/sh\nexit 0\n')
            helper=root/'.claude/hooks/lib/utils.sh';helper.parent.mkdir(parents=True,exist_ok=True)
            helper.write_text('#!/bin/sh\nif /bin/kill -TERM "$pid"; then :; fi\n')
            self.assertTrue(runtime_findings(root),'RED-R2: sourced helper effect escaped closure gate')
            self.assertEqual(render_findings('_subdirectory: template\n'), [])
            for key in ('_tasks', '_migrations', '_jinja_extensions'):
                self.assertTrue(render_findings(key+': []\n'))

    def test_t6_f5_fixture_environment_and_clock(self):
        """I6: calibrate harness independently of missing generated features."""
        f = Fixture(self, (PROJECT, PEER))
        self.assertEqual(Path(f.environment()['JV_WATCHDOG_PROC_ROOT']), f.proc)
        self.assertNotIn('CODEX_HOME', f.environment())
        self.assertEqual(f.environment()['PATH'], str(f.bin))
        code = 'import time,datetime; print(int(time.time())); print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))'
        p = subprocess.run([str(f.bin/'python3'), '-c', code], env=f.environment(), capture_output=True, text=True, timeout=5)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.splitlines(), [str(EPOCH), iso(EPOCH)])
        p = subprocess.run([str(f.bin/'date'), '-u', '+%s'], env=f.environment(), capture_output=True, text=True, timeout=5)
        self.assertEqual((p.returncode, p.stdout.strip()), (0, str(EPOCH)))


class Liveness(unittest.TestCase):
    def setUp(self):
        missing = [str(root/rel) for root in (PROJECT, PEER) for rel in CLOSURE if not (root/rel).is_file()]
        self.assertFalse(missing, 'W-C3 feature-absence RED; missing generated closure: '+', '.join(missing))
        for root in (PROJECT, PEER):
            self.assertFalse(runtime_findings(root), 'W-C3 source-gate refusal; no runtime executed')
        self.f = Fixture(self, (PROJECT, PEER))

    def ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return result

    def sweep(self, *args, peer=0, env=None, degraded=False):
        p = self.f.run('stall-watchdog.sh', *args, peer=peer, env=env)
        if degraded:
            self.assertNotEqual(p.returncode, 0, 'required evidence failure must not claim complete coverage')
        else:
            self.ok(p)
        try:
            rows = [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
        except ValueError as error:
            self.fail('observer must emit JSONL decisions/completion: '+str(error)+' '+p.stdout)
        completion = [r for r in rows if r.get('kind') == 'complete']
        self.assertEqual(len(completion), 1, p.stdout+p.stderr)
        self.assertEqual(completion[0]['project_id'], ('alpha','beta')[peer])
        seats = {r['role']:r for r in rows if r.get('kind') == 'seat'}
        self.assertEqual(completion[0]['enumerated'], len(seats))
        self.assertEqual(completion[0]['evaluated']+completion[0]['unknown'], len(seats))
        return seats, completion[0]

    def stale(self, letter='a', peer=0):
        return self.f.cadence(peer, letter, heartbeat_at=iso(self.f.now-4000), next_wake_at=iso(self.f.now+900))

    def standby(self, **fields):
        return self.f.cadence(state='standby', cadence_seconds=0, next_wake_at='event',
                              doorbell='mailbox:a', heartbeat_at=iso(self.f.now-90000), **fields)

    def test_t1_project_isolation_and_worktree(self):
        """I1 positive: same seat and shared state root, disjoint writes/reads."""
        f=self.f
        self.ok(f.run('cadence.sh','A','awake','300','alpha intent'))
        self.ok(f.run('cadence.sh','A','awake','600','beta intent',peer=1))
        for peer in (0,1):
            f.record(peer)
            f.cadence(peer,state='standby',cadence_seconds=0,next_wake_at='event',doorbell='mailbox:a')
            f.mail(ages=(2200+peer*2000,),peer=peer)
            f.process(peer,pid=4101+peer)
        for peer in (0,1):
            for dry in (False,True):
                with self.subTest(peer=peer,dry=dry):
                    foreign=f.store(1-peer);before=snapshot(foreign)
                    watched=[p for p in foreign.rglob('*') if p.is_file()]
                    owned=[f.store(peer)/x for x in ('cadence/a.txt','sessions/a.json','mail')]
                    own_before=[snapshot(p) if p.is_dir() else p.read_bytes() for p in owned]
                    with opened(watched) as events:
                        seats,_=self.sweep(*(['--dry-run'] if dry else []),peer=peer)
                    self.assertFalse(any(events),'RED-R3: observer opened foreign roster/mail/cursor/cadence')
                    self.assertEqual(before,snapshot(foreign))
                    self.assertEqual(own_before,[snapshot(p) if p.is_dir() else p.read_bytes() for p in owned])
                    self.assertEqual(set(seats),{'a'})
                    self.assertEqual(seats['a']['project_id'],('alpha','beta')[peer])
                    self.assertEqual(seats['a']['backlog_seconds'],2200+peer*2000)
        worktree=f.root/'independent worktree'; shutil.copytree(f.projects[0],worktree)
        f.projects[0]=worktree
        # Code may execute from another worktree, but binding remains the original project root.
        bound=json.loads((f.store()/'project.json').read_text())['project_root']
        self.ok(f.run('cadence.sh','a','sleeping','400',env={'JV_PROJECT_ROOT':bound}))
        self.assertEqual(f.fields(f.store()/'cadence/a.txt')['cadence_seconds'],'400')

    def test_t1_identity_alias_and_legacy_refusals(self):
        """I1 refusal: fail before opening redirected state, keep canaries intact."""
        f=self.f; p=f.cadence(); before=p.read_bytes()
        foreign=f.cadence(1); saved=foreign.read_bytes()
        for env in ({'JV_PROJECT_ID':None},{'JV_PROJECT_ROOT':str(f.projects[1])},
                    {'JV_STATE_ROOT':'relative'},{'CADENCE_DIR':str(f.store(1)/'cadence')},
                    {'PACEMAKER_CADENCE_DIR':str(f.store(1)/'cadence')},
                    {'PACEMAKER_STATE_DIR':str(f.store(1))}):
            with self.subTest(env=env), opened([foreign]) as events:
                r=f.run('cadence.sh','a','awake',env=env)
                self.assertNotEqual(r.returncode,0)
            self.assertFalse(any(events)); self.assertEqual(p.read_bytes(),before)
        p.unlink(); p.symlink_to(foreign)
        with opened([foreign]) as events:
            r=f.run('stall-watchdog.sh')
            self.assertNotEqual(r.returncode,0)
        self.assertFalse(any(events)); self.assertEqual(foreign.read_bytes(),saved)

    def test_t2_cadence_shapes_and_hook_preserve_intent(self):
        """I2 positive: source CLI shape and actual cluster/solo Stop wrappers."""
        f=self.f
        self.ok(f.run('cadence.sh','A','awake','300','first'))
        p=f.store()/'cadence/a.txt'; data=f.fields(p)
        self.assertEqual((data['state'],data['wake_count'],data['cadence_seconds']),('active','1','300'))
        self.assertEqual(data['next_wake_at'],iso(f.now+300))
        self.ok(f.run('cadence.sh','a','sleeping','200','second'))
        self.assertEqual(f.fields(p)['wake_count'],'1')
        self.ok(f.run('cadence.sh','a','standby','999','--doorbell','mailbox:a','waiting'))
        self.assertEqual((f.fields(p)['cadence_seconds'],f.fields(p)['next_wake_at']),('0','event'))
        brief=f.root/'conclusion brief'; brief.write_text('fixture')
        self.ok(f.run('cadence.sh','a','dormant','--conclusion','completed','--brief',str(brief),'done'))
        for command in ('heartbeat-hook.sh',WRAPPER):
            before=f.fields(p); f.now+=30
            self.ok(f.run(command))
            after=f.fields(p); self.assertEqual(after.pop('heartbeat_at'),iso(f.now)); before.pop('heartbeat_at')
            self.assertEqual(after,before,'heartbeat erased or rewrote intent/ceremony')
        f.cadence(1); before=snapshot(f.store(1)); self.ok(f.run(WRAPPER,peer=1))
        self.assertEqual(before,snapshot(f.store(1)),'solo Stop must be inert')

    def test_t2_invalid_input_prior_and_hook_diagnostic(self):
        """I2 refusal: invalid candidate never replaces committed cadence."""
        f=self.f;p=f.cadence(); before=p.read_bytes()
        cases=[('a','awake','0'),('a','awake','-1'),('a','awake','999999999999999999999999'),
               ('a','awake','--unknown'),('ab','awake'),('é','awake'),('a','awake','300','bad\nstate: dormant'),
               ('a','standby'),('a','standby','--doorbell','mailbox:b'),('a','dormant'),
               ('a','dormant','--conclusion','done','--brief','relative')]
        for args in cases:
            with self.subTest(args=args):
                self.assertNotEqual(f.run('cadence.sh',*args).returncode,0); self.assertEqual(p.read_bytes(),before)
        p.write_text(p.read_text().replace('wake_count: 3','wake_count: broken')); before=p.read_bytes()
        self.assertNotEqual(f.run('cadence.sh','a','awake').returncode,0); self.assertEqual(p.read_bytes(),before)
        r=self.ok(f.run('heartbeat-hook.sh'));self.assertTrue(r.stderr.strip());self.assertEqual(p.read_bytes(),before)
        p.unlink();r=self.ok(f.run('heartbeat-hook.sh'));self.assertTrue(r.stderr.strip());self.assertFalse(p.exists())
        self.assertNotEqual(f.run('cadence.sh','a','awake',env={'JV_ROLE':'B'}).returncode,0)

    def test_t2_writer_lock_and_read_inside_lock(self):
        """I2: fixture owns the same OS lock while publishing the later intent."""
        f=self.f; p=f.cadence(); lock=p.parent/'.a.lock'
        with lock.open('a') as held:
            fcntl.flock(held,fcntl.LOCK_EX)
            marker=f.root/'lock-attempt'
            child=f.spawn('heartbeat-hook.sh',env={'JV_TEST_LOCK_MARKER':str(marker),'JV_TEST_LOCK_PATH':str(lock)})
            f.wait(marker.exists,'heartbeat attempted seat lock')
            self.assertIsNone(child.poll(),'writer ignored held seat lock')
            brief=f.root/'brief';brief.write_text('done')
            f.cadence(state='dormant',next_wake_at='none',cadence_seconds=0,conclusion='later intent',brief=brief)
            intended=f.fields(p)
            fcntl.flock(held,fcntl.LOCK_UN)
        out,err=child.communicate(timeout=5);self.assertEqual(child.returncode,0,out+err)
        self.assertEqual(f.fields(p),{**intended,'heartbeat_at':iso(f.now)})
        # An explicit writer must also read the count after acquiring this same lock.
        with lock.open('a') as held:
            fcntl.flock(held,fcntl.LOCK_EX);marker.unlink()
            child=f.spawn('cadence.sh','a','awake',env={'JV_TEST_LOCK_MARKER':str(marker),'JV_TEST_LOCK_PATH':str(lock)})
            f.wait(marker.exists,'cadence attempted seat lock'); self.assertIsNone(child.poll())
            f.cadence(wake_count=40); fcntl.flock(held,fcntl.LOCK_UN)
        out,err=child.communicate(timeout=5);self.assertEqual(child.returncode,0,out+err)
        self.assertEqual(f.fields(p)['wake_count'],'41')
        with lock.open('a') as held:
            fcntl.flock(held,fcntl.LOCK_EX);before=p.read_bytes();started=time.monotonic()
            r=self.ok(f.run('heartbeat-hook.sh',timeout=4))
            self.assertLess(time.monotonic()-started,3);self.assertTrue(r.stderr.strip())
            self.assertEqual(p.read_bytes(),before,'timed-out hook changed cadence')

    def test_t2_writer_faults_are_atomic(self):
        """I2 refusal: checked lock/write/rename failure, no candidate debris."""
        f=self.f;p=f.cadence();before=p.read_bytes()
        for fault in ('lock','write','rename'):
            with self.subTest(fault=fault):
                marker=f.root/('fault-'+fault)
                if fault=='write': p.parent.chmod(0o555)
                try:
                    r=f.run('cadence.sh','a','awake','400',env={'JV_TEST_FAULT':fault,'JV_TEST_FAULT_MARKER':str(marker)})
                finally:
                    p.parent.chmod(0o755)
                if fault!='write': self.assertTrue(marker.exists(),'fault injection was not reached')
                self.assertNotEqual(r.returncode,0,r.stdout+r.stderr); self.assertEqual(p.read_bytes(),before)
                debris=[x.name for x in p.parent.iterdir() if x.name not in ('a.txt','.a.lock')]
                self.assertEqual(debris,[])

    def test_t3_roster_union_and_independent_schedule_floor(self):
        """I3/F4 positive: fresh HB cannot hide schedule; future wake cannot hide floor."""
        f=self.f; f.record(letter='a');self.stale('b');f.cadence(letter='z',next_wake_at=iso(f.now-2700))
        seats,done=self.sweep('--dry-run',degraded=True)
        self.assertEqual(set(seats),{'a','b','z'});self.assertEqual(done['unknown'],1)
        self.assertIn('missing-cadence',seats['a']['reasons'])
        self.assertEqual(seats['b']['reasons'],['heartbeat-floor']);self.assertFalse(seats['b']['registered'])
        self.assertEqual(seats['z']['reasons'],['schedule-overdue'])

    def test_t3_f4_exact_schedule_and_floor_thresholds(self):
        """I3/F4: independent equality boundaries at fixed clock, 2×cadence grace."""
        f=self.f
        for cadence,grace in ((900,2700),(2000,4000)):
            for overdue in (grace-1,grace,grace+1):
                with self.subTest(cadence=cadence,overdue=overdue):
                    f.cadence(cadence_seconds=cadence,next_wake_at=iso(f.now-overdue),heartbeat_at=iso(f.now-10))
                    seats,_=self.sweep('--dry-run')
                    self.assertEqual(seats['a']['reasons'],['schedule-overdue'] if overdue>=grace else [])
        for age in (3599,3600,3601):
            with self.subTest(age=age):
                f.cadence(next_wake_at=iso(f.now+5000),heartbeat_at=iso(f.now-age))
                seats,_=self.sweep('--dry-run');self.assertEqual(seats['a']['reasons'],['heartbeat-floor'] if age>3600 else [])

    def test_t3_unknown_dormancy_and_later_seat(self):
        """I3 refusal: malformed/none/mtime never erase later-seat coverage."""
        f=self.f;self.stale('z')
        cases=[{'cadence_seconds':'nonsense'},{'cadence_seconds':'9'*80},{'heartbeat_at':None},
               {'heartbeat_at':'yesterday-ish'},{'next_wake_at':'none'},
               {'state':'dormant','next_wake_at':'none','cadence_seconds':0}, {'role':'b'}]
        for values in cases:
            with self.subTest(values=values):
                p=f.cadence(**values);os.utime(p,(f.now,f.now));seats,done=self.sweep('--dry-run',degraded=True)
                self.assertEqual(set(seats),{'a','z'});self.assertTrue(seats['a']['reasons'])
                self.assertIn('heartbeat-floor',seats['z']['reasons']);self.assertGreater(done['unknown'],0)
        brief=f.root/'brief';brief.write_text('completed')
        f.cadence(state='dormant',next_wake_at='none',cadence_seconds=0,conclusion='complete',brief=brief)
        seats,_=self.sweep('--dry-run');self.assertEqual(seats['a']['reasons'],[])
        for state in ('booted','parked'):
            f.cadence(state=state,heartbeat_at=iso(f.now-90000),next_wake_at='none',cadence_seconds=0)
            seats,_=self.sweep('--dry-run');self.assertNotIn('heartbeat-floor',seats['a']['reasons'])
        # I3: an owned roster path that is a file is invalid evidence, not an empty roster.
        malformed=f.store()/'sessions';malformed.write_text('not a directory')
        r=f.run('stall-watchdog.sh','--dry-run')
        self.assertNotEqual(r.returncode,0,'malformed roster path silently became empty')
        self.assertTrue(r.stderr.strip())

    def test_t4_oldest_streams_broadcast_and_no_consumption(self):
        """I4 positive: continuous arrivals and other cursors cannot hide oldest mail."""
        f=self.f;cad=self.standby();f.process()
        f.mail('o',ages=(9900,2200,3),consumed=1)
        f.mail('i',ages=(9000,2),consumed=1)
        f.mail('d','all',ages=(2600,1),cursor=False)
        f.mail('a','a',ages=(99999,));f.mail('a','all',ages=(99999,))
        before=snapshot(f.store()/'mail');cadence=cad.read_bytes()
        seats,_=self.sweep();row=seats['a']
        self.assertIn('mail-backlog',row['reasons']);self.assertEqual(row['backlog_seconds'],2600)
        self.assertEqual(row['process'],'present');self.assertEqual(before,snapshot(f.store()/'mail'))
        self.assertEqual(cad.read_bytes(),cadence)
        self.assertNotIn('healthy',json.dumps(row).lower());self.assertIn('limited',row['observation'])

    def test_t4_f2_strict_backlog_process_independent(self):
        """I4/F2: 1799/1800/1801 under present, absent and unavailable process data."""
        f=self.f;self.standby()
        for mode in ('present','absent','unavailable'):
            shutil.rmtree(f.proc);f.proc.mkdir()
            if mode=='present':f.process()
            env={'JV_WATCHDOG_PROC_ROOT':None} if mode=='unavailable' else {}
            for age in (1799,1800,1801):
                with self.subTest(mode=mode,age=age):
                    f.mail(ages=(age,),cursor=False);seats,_=self.sweep('--dry-run',env=env)
                    self.assertEqual('mail-backlog' in seats['a']['reasons'],age>1800)
                    self.assertEqual(seats['a']['process'],mode)

    def test_t4_f3_virgin_cursor_vs_unknown(self):
        """I4/F3: absent cursor is zero; invalid/unreadable offsets remain unknown."""
        f=self.f;self.standby();stream,cursor=f.mail(ages=(2200,2),cursor=False)
        seats,_=self.sweep('--dry-run');self.assertEqual(seats['a']['backlog_seconds'],2200)
        for value in ('broken','-1','1',str(stream.stat().st_size+1),'9'*90):
            with self.subTest(value=value):
                cursor.write_text(value);seats,_=self.sweep('--dry-run',degraded=True)
                self.assertIn('mail-unknown',seats['a']['reasons']);self.assertIsNone(seats['a']['backlog_seconds'])
        cursor.unlink();cursor.mkdir();seats,_=self.sweep('--dry-run',degraded=True)
        self.assertIn('mail-unknown',seats['a']['reasons']);cursor.rmdir()
        stream.write_text('{"ts":"not-a-date"}\n');os.utime(stream,(f.now,f.now))
        seats,_=self.sweep('--dry-run',degraded=True);self.assertIn('mail-unknown',seats['a']['reasons'])
        stream.unlink();shutil.rmtree(f.store()/'mail')
        seats,_=self.sweep('--dry-run',degraded=True);self.assertIn('mail-unknown',seats['a']['reasons'])

    def test_t4_process_exact_identity_interactive_and_idle_standby(self):
        """I4 refusal: presence is exact identity plus interactive argv, never loop health."""
        f=self.f;self.standby()
        variants=[(('bash','-c','codex'),{}), (('claude','--print','hi'),{}),
                  (('claude','--model','fixture','-p','hi\nthere'),{}),
                  (('codex','--profile','fixture','exec','hi'),{}),
                  (('codex','--config','x="multi\nline"','exec','hi'),{}),
                  (('codex',),{'JV_PROJECT_ID':'beta'}), (('codex',),{'JV_PROJECT_ROOT':str(f.projects[1])}),
                  (('codex',),{'JV_ROLE':'B'})]
        for argv,env in variants:
            with self.subTest(argv=argv,env=env):
                f.process(argv=argv,**env);seats,_=self.sweep('--dry-run')
                self.assertEqual(seats['a']['process'],'absent');self.assertNotIn('heartbeat-floor',seats['a']['reasons'])
        for argv in (('codex','resume','alpha-a','--profile','fixture'),('claude','--model','fixture','--resume','alpha-a')):
            f.process(argv=argv);seats,_=self.sweep('--dry-run')
            self.assertEqual(seats['a']['process'],'present');self.assertEqual(seats['a']['reasons'],[])
        (f.proc/'4101/environ').unlink();(f.proc/'4101/environ').mkdir()
        seats,_=self.sweep('--dry-run',degraded=True);self.assertEqual(seats['a']['process'],'unknown')

    def test_t5_backoff_stable_episode_recovery_and_dormancy(self):
        """I5 positive: last successful report controls finite backoff and reset."""
        f=self.f;self.stale();self.sweep();first=f.alerts()[0]['episode']
        for delta,wanted in ((2699,1),(2700,2),(8099,2),(8100,3),(18899,3),(18900,4),
                             (40499,4),(40500,5),(83699,5),(83700,6),(170099,6),(170100,7),
                             (256499,7),(256500,8)):
            f.now=EPOCH+delta;self.sweep();self.assertEqual(len(f.alerts()),wanted)
            self.assertEqual(f.alerts()[-1]['episode'],first,'additional schedule detector changed episode')
        f.cadence();self.sweep();self.stale();self.sweep()
        self.assertEqual(len(f.alerts()),9);self.assertNotEqual(f.alerts()[-1]['episode'],first)
        second=f.alerts()[-1]['episode'];brief=f.root/'brief';brief.write_text('done')
        f.cadence(state='dormant',next_wake_at='none',cadence_seconds=0,conclusion='done',brief=brief)
        self.sweep();f.now+=1;self.stale();self.sweep()
        self.assertEqual(len(f.alerts()),10);self.assertNotEqual(f.alerts()[-1]['episode'],second)

    def test_t5_dry_run_never_writes_stall_or_recovery(self):
        """I5 refusal: no directory/lock/log creation, no state clearing or budget use."""
        f=self.f;self.stale();before=snapshot(f.state);self.sweep('--dry-run');self.assertEqual(before,snapshot(f.state))
        self.sweep();f.cadence();before=snapshot(f.state);self.sweep('--dry-run');self.assertEqual(before,snapshot(f.state))
        unknown=f.root/'absent-state'
        r=f.run('stall-watchdog.sh','--dry-run',env={'JV_STATE_ROOT':str(unknown)})
        self.assertNotEqual(r.returncode,0);self.assertFalse(unknown.exists())

    def test_t5_concurrent_sweeps_and_failed_output(self):
        """I5 refusal: serialized reporting, checked append/checkpoint and bounded counters."""
        f=self.f;self.stale()
        children=[f.spawn('stall-watchdog.sh') for _ in range(2)]
        for p in children:
            out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,0,out+err)
        self.assertEqual(len(f.alerts()),1)
        state=f.store()/'watchdog/a.json'; saved=state.read_bytes()
        log=f.store()/'watchdog/alerts.jsonl';log.unlink();log.mkdir();f.now+=2700
        self.sweep(degraded=True);self.assertEqual(state.read_bytes(),saved,'failed append advanced delivery checkpoint')
        log.rmdir();self.sweep();self.assertEqual(len(f.alerts()),1)
        state.unlink();state.mkdir();f.now+=5400
        self.sweep(degraded=True) # append-before-checkpoint may duplicate; never claim complete
        state.rmdir();state.write_bytes(saved)
        broken=json.loads(saved);broken['count']='9'*100;state.write_text(json.dumps(broken))
        self.sweep('--dry-run',degraded=True)

    def test_t6_alias_and_legacy_action_migration(self):
        """I6: same observer via pacemaker; retired effects refuse with useful migration."""
        f=self.f;self.stale()
        a=self.ok(f.run('stall-watchdog.sh','--dry-run'));b=self.ok(f.run('pacemaker.sh','--dry-run'))
        self.assertEqual(a.stdout,b.stdout)
        knobs={'PACEMAKER_RESPAWN_HOOK':'/never/execute','PACEMAKER_NOTIFY':'sms',
               'PACEMAKER_SMS_CMD':'/never/execute','PACEMAKER_TMUX_TARGET':'other:a',
               'PACEMAKER_RESUME_PROMPT':'wake','PACEMAKER_ROLES':'a','PACEMAKER_DRY_RUN':'1'}
        before=snapshot(f.state)
        for key,value in knobs.items():
            with self.subTest(key=key):
                r=f.run('pacemaker.sh',env={key:value});self.assertNotEqual(r.returncode,0)
                self.assertIn('migrat',r.stderr.lower());self.assertIn(key,r.stderr);self.assertEqual(before,snapshot(f.state))

    def test_t7_missing_helper_dependency_and_wrapper_target(self):
        """I7 refusal: diagnostic failure, including bounded always-zero Stop wrapper."""
        f=self.f;f.cadence();p=f.projects[0]/'scripts/heartbeat-hook.sh';p.unlink()
        # Missing closure is an expected harness refusal; never mistake it for runtime proof.
        self.assertTrue(runtime_findings(f.projects[0]));shutil.copyfile(PROJECT/'scripts/heartbeat-hook.sh',p)
        # Broken wrapper target must be exercised while the scanned file itself remains present.
        p.write_text('#!/bin/bash\nprintf "heartbeat target unavailable\\n" >&2\nexit 72\n')
        r=self.ok(f.run(WRAPPER));self.assertTrue(r.stderr.strip(),'wrapper swallowed target failure')
        p=f.bin/'python3';p.unlink()
        r=f.run('cadence.sh','a','awake');self.assertNotEqual(r.returncode,0);self.assertTrue(r.stderr.strip())

    def test_t7_f1_updated_consumer_refuses_legacy_knobs(self):
        """I7/F1: real Copier update supplies this source, not a fresh-render substitute."""
        evidence=os.environ.get('JV_LIVENESS_UPGRADE_RECEIPT');self.assertTrue(evidence,'missing actual upgrade/rollback receipt')
        receipt=json.loads(Path(evidence).read_text())
        self.assertEqual(receipt['release'],'jv-v0.2.3');self.assertTrue(receipt['saved_answers_preserved'])
        self.assertTrue(receipt['project_edits_preserved']);self.assertTrue(receipt['legacy_state_preserved'])
        self.assertTrue(receipt['rollback_equal']);self.assertEqual(receipt['external_pacemaker'],'tmux-supervisor')
        f=Fixture(self,(Path(receipt['updated_consumer']),PEER));f.cadence();self.assertFalse(runtime_findings(f.projects[0]))
        legacy=f.projects[0]/'context/cadence'
        hooks=f.root/'legacy hooks';hooks.mkdir()
        knobs={**receipt['legacy_knobs'],'PACEMAKER_CADENCE_DIR':str(legacy),
               'PACEMAKER_STATE_DIR':str(legacy/'.pacemaker-state')}
        for key in ('PACEMAKER_RESPAWN_HOOK','PACEMAKER_SMS_CMD'):
            target=hooks/(key+'.sh');target.write_text('#!/bin/sh\nexit 99\n');target.chmod(0o755)
            knobs[key]=str(target)
        watched=[p for root in (legacy,hooks) for p in root.rglob('*') if p.is_file()]
        self.assertGreaterEqual(len(watched),4,'legacy cadence/dedup and action targets must exist')
        for key,value in knobs.items():
            with self.subTest(key=key):
                before=[snapshot(root) for root in (legacy,hooks,f.state)]
                with opened(watched) as events:
                    r=f.run('pacemaker.sh',env={key:value})
                self.assertNotEqual(r.returncode,0)
                self.assertIn('migrat',r.stderr.lower());self.assertIn(key,r.stderr)
                self.assertFalse(any(events),'RED-R4: refused knob accessed a legacy target')
                self.assertEqual(before,[snapshot(root) for root in (legacy,hooks,f.state)])
        guidance=(f.projects[0]/'docs/PACEMAKER.md').read_text().lower()
        for phrase in ('breaking-change','jv-v0.2.3','git revert','report-only','canary','lease','namespace'):
            self.assertIn(phrase,guidance)


if __name__=='__main__':
    unittest.main(verbosity=2)

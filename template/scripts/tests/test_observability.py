#!/usr/bin/env python3
"""W-C5 finite invariant cells; all providers, disks, clocks and sinks are fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from observability_guard import CLOSURE, runtime_findings
from observability_fixture import Fixture, opened, snapshot

PROJECT=Path(os.environ.get('JV_OBSERVABILITY_PROJECT',Path(__file__).resolve().parents[2]))
PEER=Path(os.environ.get('JV_OBSERVABILITY_PEER',PROJECT))


class Harness(unittest.TestCase):
    def test_t7_fixed_policy_data_refusals(self):
        """I7: positive fixed-image control; unsafe effect seeds remain DATA."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for rel in CLOSURE:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes((PROJECT/rel).read_bytes() if rel.endswith('jv-project.sh') else
                              (b'pass\n' if rel.endswith('.py') else b'#!/bin/bash\nexit 0\n'))
            self.assertEqual(runtime_findings(root),[])
            for rel in CLOSURE:
                p=root/rel;original=p.read_bytes()
                for seed in ('rm -f "$DUMPS"/*.dmp','source "$helper"','eval "$payload"',
                             'signal.pidfd_send_signal(fd,9)','subprocess.run(["curl",url])'):
                    with self.subTest(file=rel,seed=seed):
                        p.write_bytes(original+seed.encode()+b'\n')
                        self.assertTrue(runtime_findings(root))
                p.write_bytes(original)
            self.assertEqual(runtime_findings(root),[])

    def test_f7_read_witness_calibration(self):
        """F7→I2: same retained output, independently observed different reads."""
        f=Fixture(self,(PROJECT,PEER));path=f.providers/'large.bin'
        path.write_bytes(b'x'*800000)
        outputs=[];totals=[]
        for code in ("f.seek(400000); data=f.read(400000)","data=f.read()[-400000:]"):
            f.io_receipt.unlink(missing_ok=True)
            result=subprocess.run([sys.executable,'-c',"import sys\nwith open(sys.argv[1],'rb') as f:\n "+code+"\nprint(len(data))",str(path)],
                                  env=f.environment(),capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            outputs.append(result.stdout);totals.append(f.read_totals()[str(path)])
        self.assertEqual(outputs,['400000\n','400000\n'])
        self.assertEqual(totals,[400000,800000])
        self.assertLessEqual(totals[0],400000);self.assertGreater(totals[1],400000)


class Observability(unittest.TestCase):
    def setUp(self):
        for root in (PROJECT,PEER):
            missing=[rel for rel in CLOSURE if not (root/rel).is_file()]
            self.assertFalse(missing,'W-C5 feature-absence RED; missing closure: '+', '.join(missing))
            self.assertFalse(runtime_findings(root),'source refusal; no candidate child')
        self.f=Fixture(self,(PROJECT,PEER))

    def sample(self):
        self.f.anthropic_data();self.f.rollout()

    def report(self,result,code=0):
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return self.f.report(result)

    def by_series(self,report): return {row['series']:row for row in report['observations']}

    def test_t1_binding_and_paths(self):
        """I1: binding and static path refusal before foreign data writes."""
        f=self.f;self.sample();before=[snapshot(f.store(i)) for i in range(2)]
        for env in ({'JV_PROJECT_ID':None},{'JV_PROJECT_ROOT':str(f.projects[1])},
                    {'JV_HOST_ROOT':'relative'},{'JV_HOST_ROOT':str(f.providers)},
                    {'JV_USAGE_CODEX_ROOT':'relative','JV_USAGE_ANTHROPIC_FILE':None}):
            with self.subTest(env=env): self.assertNotEqual(f.run(env=env).returncode,0)
        alias=f.root/'host-alias';alias.symlink_to(f.host)
        self.assertNotEqual(f.run(env={'JV_HOST_ROOT':alias}).returncode,0)
        nested=f.codex/'2026/01/01/alias.jsonl';nested.symlink_to(f.anthropic)
        self.assertNotEqual(f.run(env={'JV_USAGE_ANTHROPIC_FILE':None}).returncode,0)
        nested.unlink()
        fifo=f.providers/'pipe';os.mkfifo(fifo)
        self.assertNotEqual(f.run(env={'JV_USAGE_ANTHROPIC_FILE':fifo,'JV_USAGE_CODEX_ROOT':None}).returncode,0)
        self.assertNotEqual(os.geteuid(),0,'permission witness requires an unprivileged fixture')
        f.host.mkdir(exist_ok=True);f.host.chmod(0o600)
        try:self.assertNotEqual(f.run().returncode,0)
        finally:f.host.chmod(0o700)
        self.assertEqual(before,[snapshot(f.store(i)) for i in range(2)])
        self.assertEqual(self.by_series(self.report(f.run()))['anthropic-wk']['used'],40)

    def test_t1_no_home_fallback(self):
        """I1/I2 surviving home-fallback mutant: populated HOME is not authority."""
        f=self.f;self.sample()
        (f.home/'anthropic.json').write_bytes(f.anthropic.read_bytes())
        legacy=f.home/'sessions/2026/01/01/rollout.jsonl'
        legacy.parent.mkdir(parents=True);legacy.write_bytes((f.codex/'2026/01/01/rollout.jsonl').read_bytes())
        os.utime(legacy,(f.now,f.now))
        before=snapshot(f.home)
        r=f.run(env={'JV_USAGE_ANTHROPIC_FILE':None,'JV_USAGE_CODEX_ROOT':None})
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(f.report(r)['observations'],[])
        self.assertEqual(snapshot(f.home),before)
        self.assertFalse(f.ledger.exists())

    def test_t1_two_projects_shared_history(self):
        """I1/I4: both real generated tiers share host facts, not project quotas."""
        f=self.f;self.sample();provider_before=snapshot(f.providers)
        reports=[self.by_series(self.report(f.run(peer=i))) for i in range(2)]
        self.assertEqual(reports[0],reports[1])
        self.assertTrue(f.ledger.is_file());self.assertEqual(snapshot(f.providers),provider_before)
        self.assertFalse((f.store(0)/'observability').exists());self.assertFalse((f.store(1)/'observability').exists())
        self.assertEqual(f.ledger.stat().st_mode & 0o777,0o600)

    def test_t2_formats_stale_and_invalid(self):
        """I2: supported structured records, no transcript lookalike or false zero."""
        f=self.f;f.anthropic_data(age=1801)
        p=f.rollout();record=json.loads(p.read_text());p.write_text(json.dumps({'rate_limits':record['payload']['rate_limits']})+'\n')
        rows=self.by_series(self.report(f.run()))
        self.assertTrue(rows['anthropic-wk']['stale']);self.assertEqual(rows['openai-wk']['used'],40)
        f.anthropic_data(age=1800)
        self.assertFalse(self.by_series(self.report(f.run()))['anthropic-wk']['stale'])
        f.anthropic_data(age=-1)
        r=f.run(env={'JV_USAGE_CODEX_ROOT':None});self.assertNotEqual(r.returncode,0)
        self.assertNotIn('anthropic-wk',self.by_series(f.report(r)))
        for value in (None,True,'not a number',float('nan'),-1,101):
            with self.subTest(value=value):
                f.anthropic_data(used=value)
                r=f.run(env={'JV_USAGE_CODEX_ROOT':None});self.assertNotEqual(r.returncode,0)
                self.assertNotIn('anthropic-wk',self.by_series(f.report(r)))
        canary='SECRET_PROMPT_CANARY_813'
        p.write_text(json.dumps({'prompt':canary,'content':json.dumps(record)})+'\n')
        r=f.run(env={'JV_USAGE_ANTHROPIC_FILE':None});self.assertNotEqual(r.returncode,0)
        self.assertNotIn('openai-wk',self.by_series(f.report(r)))
        self.assertNotIn(canary,r.stdout+r.stderr+f.ledger.read_text())

    def test_t2_latest_six(self):
        """I2: latest usable weekly fallback, bounded to six candidate files."""
        f=self.f
        for n in range(7):
            p=f.rollout(used=20+n,name=str(n)+'.jsonl',age=n)
            if n<5:
                p.write_text('{malformed\n');os.utime(p,(f.now-n,f.now-n))
        rows=self.by_series(self.report(f.run(env={'JV_USAGE_ANTHROPIC_FILE':None})))
        self.assertEqual(rows['openai-wk']['used'],25)
        p=f.codex/'2026/01/01/5.jsonl';p.write_text('{malformed\n');os.utime(p,(f.now-5,f.now-5))
        self.assertNotEqual(f.run(env={'JV_USAGE_ANTHROPIC_FILE':None}).returncode,0)

    def test_f4_label_canary(self):
        """F4→I2/X6: model output survives, raw printable names do not."""
        f=self.f;names=['SECRET_PRINTABLE_LABEL_A_411','SECRET_PRINTABLE_LABEL_B_922']
        models=[{'display_name':name,'used_percentage':20+n,'resets_at':f.now+302400} for n,name in enumerate(names)]
        ids={f.model_id(name) for name in names}
        for entries in (models,list(reversed(models))):
            f.anthropic_data(model_scoped=entries)
            for entry in ('pace.sh','usage-hook.sh'):
                r=f.run(entry,env={'JV_USAGE_CODEX_ROOT':None});rows=self.by_series(self.report(r))
                self.assertTrue(ids<=rows.keys())
                material=r.stdout+r.stderr+'\n'.join(p.read_text(errors='replace') for p in f.host.rglob('*') if p.is_file())
                for name in names:self.assertNotIn(name,material)

    def test_f5_mixed_providers(self):
        """F5→I2: a bad provider cannot void the same invocation's good data."""
        f=self.f
        for bad in ('openai','anthropic'):
            for mode in ('malformed','unreadable'):
                self.sample()
                path=f.codex/'2026/01/01/rollout.jsonl' if bad=='openai' else f.anthropic
                if mode=='malformed':path.write_text('{bad')
                else:path.chmod(0)
                good='anthropic-wk' if bad=='openai' else 'openai-wk'
                f.ledger.unlink(missing_ok=True)
                try:
                    for entry in ('pace.sh','usage-hook.sh'):
                        r=f.run(entry);self.assertEqual(r.returncode==0,entry=='usage-hook.sh')
                        rows=self.by_series(f.report(r))
                        self.assertIn(good,rows,'bad provider discarded the independent valid observation')
                        self.assertEqual(rows[good]['used'],40)
                        self.assertIn('\t'+good+'\t',f.ledger.read_text())
                        self.assertNotIn('\t'+bad+'-wk\t',f.ledger.read_text())
                finally:path.chmod(0o600)

    def test_f7_read_budget(self):
        """F7→I2: actual bytes across opens, not size of the retained result."""
        f=self.f;self.sample();p=f.codex/'2026/01/01/rollout.jsonl';valid=p.read_bytes()
        p.write_bytes((b'{}\n'*400000)+valid);os.utime(p,(f.now,f.now))
        f.history([(f.now-1800,'openai-wk',35,f.now+302400,604800)])
        f.ledger.write_bytes((b'\n'*2000000)+f.ledger.read_bytes())
        f.anthropic.write_bytes(f.anthropic.read_bytes()+b' '*(1048576-f.anthropic.stat().st_size))
        r=f.run();self.report(r)
        totals=f.read_totals();self.assertGreater(totals.get(str(p),0),0)
        self.assertLessEqual(totals[str(p)],400000)
        self.assertLessEqual(totals[str(f.ledger)],1048576)
        self.assertLessEqual(totals[str(f.anthropic)],1048576)
        f.anthropic.write_bytes(f.anthropic.read_bytes()+b' ');f.io_receipt.unlink()
        r=f.run();self.assertNotEqual(r.returncode,0)
        self.assertIn('openai-wk',self.by_series(f.report(r)))
        self.assertEqual(f.read_totals().get(str(f.anthropic),0),0)

    def test_t3_pacing_and_credit_units(self):
        """I3: inclusive ±10, expiry and separate finite credit history."""
        f=self.f
        for used,verdict in ((40,'on-pace'),(60,'on-pace'),(39,'behind'),(61,'ahead')):
            f.anthropic_data(used=used)
            row=self.by_series(self.report(f.run(env={'JV_USAGE_CODEX_ROOT':None})))['anthropic-wk']
            self.assertEqual((row['target'],row['verdict']),(50,verdict))
            self.assertAlmostEqual(row['sustainable_per_hour'],(100-used)/84,places=5)
        f.rollout(rate_limits={'secondary':{'used_percent':40,'window_minutes':10080,'resets_at':f.now+302400},
                              'credits':{'has_credits':True,'unlimited':False,'balance':'100'}})
        f.history([(f.now-1800,'openai-credits',110,0,0)])
        row=self.by_series(self.report(f.run(env={'JV_USAGE_ANTHROPIC_FILE':None})))['openai-credits']
        self.assertEqual((row['balance'],row['spend_per_hour']),(100,20));self.assertNotIn('target',row)
        f.anthropic_data(seven_day={'used_percentage':70,'resets_at':f.now})
        before=f.ledger.read_bytes()
        row=self.by_series(self.report(f.run(env={'JV_USAGE_CODEX_ROOT':None})))['anthropic-wk']
        self.assertTrue(row['expired']);self.assertIsNone(row['sustainable_per_hour'])
        self.assertEqual(f.ledger.read_bytes(),before)

    def test_f3_two_windows(self):
        """F3→I3: weekly duration selects math independently of primary position."""
        f=self.f;weekly={'used_percent':40,'window_minutes':10080,'resets_at':f.now+302400}
        short={'used_percent':90,'window_minutes':300,'resets_at':f.now+16200}
        for limits in ({'primary':short,'secondary':weekly},{'primary':weekly,'secondary':short}):
            f.rollout(rate_limits=limits)
            for entry in ('pace.sh','usage-hook.sh'):
                rows=self.by_series(self.report(f.run(entry,env={'JV_USAGE_ANTHROPIC_FILE':None})))
                row=rows['openai-wk'];self.assertEqual((row['used'],row['target'],row['verdict']),(40,50,'on-pace'))
                self.assertEqual((row['window_seconds'],row['resets_at']),(604800,f.now+302400))
                short_row=rows['openai-short'];self.assertEqual(short_row['used'],90)
                for field in ('target','verdict','sustainable_per_hour','burn_per_hour'):self.assertNotIn(field,short_row)
        f.rollout(rate_limits={'primary':short})
        r=f.run(env={'JV_USAGE_ANTHROPIC_FILE':None});self.assertNotIn('openai-wk',self.by_series(f.report(r)))

    def test_f6_burn_limits(self):
        """F6→I3: exact span and three-hour cutoff, including inclusive edge."""
        f=self.f;f.anthropic_data(used=25);reset=f.now+302400
        for span,want in ((1799,None),(1800,10)):
            f.history([(f.now-span,'anthropic-wk',20,reset,604800)])
            row=self.by_series(self.report(f.run(env={'JV_USAGE_CODEX_ROOT':None})))['anthropic-wk']
            self.assertEqual(row['burn_per_hour'],want)
        f.history([(f.now-10801,'anthropic-wk',100,reset,604800),(f.now-1800,'anthropic-wk',20,reset,604800)])
        self.assertEqual(self.by_series(self.report(f.run(env={'JV_USAGE_CODEX_ROOT':None})))['anthropic-wk']['burn_per_hour'],10)
        f.history([(f.now-10800,'anthropic-wk',10,reset,604800),(f.now-1800,'anthropic-wk',20,reset,604800)])
        self.assertEqual(self.by_series(self.report(f.run(env={'JV_USAGE_CODEX_ROOT':None})))['anthropic-wk']['burn_per_hour'],5)

    def test_t3_reset_and_fresh_precedence(self):
        """I3: foreign reset history cannot alter burn or override fresh values."""
        f=self.f;f.anthropic_data(used=25);reset=f.now+302400
        f.history([(f.now-3600,'anthropic-wk',99,reset-604800,604800),
                   (f.now-1800,'anthropic-wk',20,reset,604800)])
        row=self.by_series(self.report(f.run(env={'JV_USAGE_CODEX_ROOT':None})))['anthropic-wk']
        self.assertEqual((row['used'],row['burn_per_hour']),(25,10))

    def test_t4_persistence_faults(self):
        """I4: a checked lock/append failure is visible and cannot claim success."""
        f=self.f;self.sample()
        for env in ({'JV_TEST_FAULT':'lock'},{'JV_OBS_FAULT':'ledger'}):
            f.fault.unlink(missing_ok=True)
            r=f.run(env=env);self.assertNotEqual(r.returncode,0)
            self.assertTrue(f.fault.exists(),'fault seam not reached')
        self.report(f.run())
        for line in f.ledger.read_text().splitlines():self.assertEqual(len(line.split('\t')),5)
        with f.ledger.open('a') as out:out.write('malformed history\n')
        r=f.run();self.assertNotEqual(r.returncode,0)
        self.assertEqual(self.by_series(f.report(r))['anthropic-wk']['used'],40)

    def test_t4_shared_suppression_and_concurrency(self):
        """I4/I6: cooperating projects share a host alert budget and lock."""
        f=self.f;f.disk(percent=90)
        for i in range(2):self.report(f.run('disk-watch.sh',peer=i))
        alerts=f.host/'observability/disk-alerts.jsonl'
        self.assertEqual(len(f.rows(alerts)),1)
        f.now+=86400
        children=[f.start(i) for i in range(2)]
        for p in children:
            out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,0,out+err)
        self.assertEqual(len(f.rows(alerts)),2)

    def test_t5_thresholds_and_no_cleanup(self):
        """I5: primary inclusive85, secondary strict10; no source cleanup."""
        f=self.f;dump=f.secondary/'wsl-crash-owned.dmp';dump.write_text('KEEP')
        for percent,gib,count in ((84,10,0),(85,10,1),(89,10,1),(90,10,2),(90,9,3)):
            f.disk(percent,gib);self.report(f.run('disk-watch.sh'))
            self.assertEqual(len(f.rows(f.host/'observability/disk-alerts.jsonl')),count)
        self.assertEqual(dump.read_text(),'KEEP')
        for argv in f.rows(f.df_calls):self.assertIn(argv[-1],(str(f.primary),str(f.secondary)))

    def test_f5_bad_secondary(self):
        """F5→I5: valid primary report AND alert survive a bad secondary."""
        f=self.f
        for invalid in (False,True):
            f.now+=86400;f.disk(percent=90,secondary={'malformed':True})
            env={'JV_DISK_SECONDARY_ROOT':str(f.root/'absent disk')} if invalid else None
            count=len(f.rows(f.host/'observability/disk-alerts.jsonl'))
            r=f.run('disk-watch.sh',env=env);self.assertNotEqual(r.returncode,0)
            rows=f.report(r)['observations'];self.assertTrue(any(row.get('percent')==90 for row in rows))
            self.assertEqual(len(f.rows(f.host/'observability/disk-alerts.jsonl')),count+1)

    def test_t6_adapter_failure_and_retry(self):
        """I6: literal JSON stdin, no failed-delivery suppression, bounded timeout."""
        f=self.f;f.disk(percent=90)
        env={'JV_OBSERVABILITY_NOTIFY_BIN':f.adapter,'JV_OBS_SINK_MODE':'fail'}
        self.assertNotEqual(f.run('disk-watch.sh',env=env).returncode,0)
        env['JV_OBS_SINK_MODE']='ok';self.report(f.run('disk-watch.sh',env=env))
        self.assertEqual(len(f.rows(f.sink)),2)
        for row in f.rows(f.sink):self.assertEqual(row['argv'],[]);self.assertEqual(row['record']['project_id'],'alpha')
        self.report(f.run('disk-watch.sh',env=env));self.assertEqual(len(f.rows(f.sink)),2)
        f.now+=86400;env['JV_OBS_SINK_MODE']='timeout'
        self.assertNotEqual(f.run('disk-watch.sh',env=env,timeout=15).returncode,0)
        env['JV_OBS_SINK_MODE']='ok';self.report(f.run('disk-watch.sh',env=env))
        self.assertEqual(len(f.rows(f.sink)),4)
        f.now+=86400;f.fault.unlink(missing_ok=True)
        r=f.run('disk-watch.sh',env={**env,'JV_TEST_FAULT':'rename'})
        self.assertNotEqual(r.returncode,0);self.assertTrue(f.fault.exists())
        self.report(f.run('disk-watch.sh',env=env))
        self.assertEqual(len(f.rows(f.sink)),6,'checkpoint failure must permit duplicate-safe retry')
        f.now+=86400;f.fault.unlink(missing_ok=True)
        r=f.run('disk-watch.sh',env={'JV_OBS_FAULT':'sink'})
        self.assertNotEqual(r.returncode,0);self.assertTrue(f.fault.exists())
        self.report(f.run('disk-watch.sh'))

    def test_t6_hook_no_access_and_fail_open(self):
        """I6: other seats touch no data, director collection errors exit zero."""
        f=self.f;self.sample();before=snapshot(f.root)
        r=f.run('usage-hook.sh',env={'JV_ROLE':'a','JV_PROJECT_ID':None})
        self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''))
        self.assertEqual(snapshot(f.root),before)
        r=f.run('usage-hook.sh',env={'JV_PROJECT_ID':None});self.assertEqual(r.returncode,0)
        self.assertNotEqual(f.run(env={'JV_PROJECT_ID':None}).returncode,0)

    def test_t6_bound_other_seat_no_access(self):
        """I6 surviving role-filter mutant: valid binding must not mask access."""
        f=self.f;self.sample();before=snapshot(f.root)
        r=f.run('usage-hook.sh',env={'JV_ROLE':'a'})
        self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''))
        self.assertEqual(snapshot(f.root),before)

    def test_t7_both_entries_generated_and_missing_helper(self):
        """I7: both generated consumers execute and missing closure refuses."""
        f=self.f;self.sample()
        for i in range(2):
            r=f.run('usage-hook.sh',peer=i);self.report(r)
            self.assertLessEqual(len(r.stdout.encode()),4096)
        helper=f.projects[0]/'scripts/lib/jv-observability.py';helper.unlink()
        self.assertTrue(runtime_findings(f.projects[0]))


if __name__=='__main__':unittest.main(verbosity=2)

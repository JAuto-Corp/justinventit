#!/usr/bin/env python3
"""W-C2 I1-I6 and SPEC F1/F2/F3 witnesses; stdlib, synthetic providers only.

Run from actual Copier output. Missing delivery fails setup as feature-absence
RED; it never counts as a passing refusal or a behavioral mutant kill.
"""
import concurrent.futures
import contextlib
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid


PROJECT = Path(os.environ.get("JV_LAUNCH_PROJECT", Path(__file__).resolve().parents[2]))
PEER = Path(os.environ.get("JV_LAUNCH_PEER", PROJECT))
CLOSURE = ("scripts/role-launch.sh", "scripts/boot-role.sh", "scripts/lib/codex-seat.sh",
           "scripts/lib/jv-project.sh", "scripts/validate-seat-record.mjs", "docs/seat-record.schema.json",
           "scripts/msg.sh", "docs/orchestration/role-templates/O.md",
           "docs/orchestration/role-templates/I.md", "docs/orchestration/role-templates/IMPLEMENTER.md")
MODEL = 'fixture café [1m] `literal` $(never-run) "quoted" \\ slash\nlast\n'
COUPLING = re.compile(r"/home/" + r"justi\b|customer" + r"-portal|\bJA" + r"UTO_ROLE\b|\.jauto-|\bjauto\b")
SECRET = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-proj-[A-Za-z0-9_-]{20,}|\bsb_secret_[A-Za-z0-9_-]{16,}")


def scan_operating(project):
    findings = []
    # Dated origin references belong in provenance, not operating files.
    for rel in (*CLOSURE, "docs/CLUSTER.md"):
        p = project / rel
        if not p.is_file():
            findings.append({"file": rel, "check": "missing"})
            continue
        for line, text in enumerate(p.read_text().splitlines(), 1):
            for label, regex in (("coupling", COUPLING), ("secret", SECRET)):
                if regex.search(text):
                    findings.append({"file": rel, "line": line, "check": label})
    return findings


def snapshot(root):
    result = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(parent) / name
            result[str(p.relative_to(root))] = ("link", os.readlink(p)) if p.is_symlink() else (
                ("file", p.read_bytes()) if p.is_file() else ("directory",))
    return result


@contextlib.contextmanager
def opened(paths):
    """F1: observe consumption, not just byte changes or unreliable atime."""
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "inotify_init1")
    events = []
    try:
        for p in paths:
            if libc.inotify_add_watch(fd, os.fsencode(p), 0x20) < 0:
                raise OSError(ctypes.get_errno(), "inotify_add_watch")
        yield events
        try:
            events.append(os.read(fd, 65536))
        except BlockingIOError:
            pass
    finally:
        os.close(fd)


class Launch(unittest.TestCase):
    def setUp(self):
        missing = [str(p / rel) for p in (PROJECT, PEER) for rel in CLOSURE if not (p / rel).is_file()]
        self.assertFalse(missing, "W-C2 feature-absence RED; missing generated closure: " + ", ".join(missing))
        for project in (PROJECT, PEER):
            self.assertFalse(scan_operating(project), "refuse to execute coupled/missing operating closure")
        self.tmp = tempfile.TemporaryDirectory(prefix="jv-launch-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.projects = [self.root / "consumer alpha", self.root / "consumer beta\x1c space"]
        for src, dst in zip((PROJECT, PEER), self.projects):
            shutil.copytree(src, dst)
        self.state = self.root / "shared-state"
        self.home = self.root / "synthetic-home"
        self.codex = self.home / ".codex"
        self.codex.mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.fixtures = self.root / "fixture"
        self.fixtures.mkdir()
        self.configs = [self.root / "alpha-fixture.json", self.root / "beta-fixture.json"]
        for p in self.configs:
            p.write_text(json.dumps({"model": "fixture-model", "effort": "xhigh"}))
        self.epoch = 1800000000
        for name in ("claude", "codex"):
            shutil.copyfile(Path(__file__).with_name("fake_seat_runtime.py"), self.bin / name)
            (self.bin / name).chmod(0o755)
        # Only the fixture Codex executable is reachable through the explicit pin.
        self.env = {"PATH": str(self.bin) + ":" + os.environ["PATH"], "HOME": str(self.home),
                    "CODEX_HOME": str(self.codex), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                    "JV_STATE_ROOT": str(self.state), "JV_CODEX_BIN": str(self.bin / "codex"),
                    "JV_LAUNCH_FIXTURE": str(self.fixtures), "PYTHONDONTWRITEBYTECODE": "1"}
        self.stub("date", '#!/usr/bin/env python3\nimport os,sys\n'
                  'if sys.argv[1:]==["+%s"]: print(os.environ["JV_LAUNCH_FIXTURE_EPOCH"])\n'
                  'else: os.execv(' + repr(shutil.which("date")) + ',["date",*sys.argv[1:]])\n')
        self.trust()

    def stub(self, name, text):
        p = self.bin / name
        p.write_text(text)
        p.chmod(0o755)
        return p

    def configure(self, peer=0, **values):
        cfg = json.loads(self.configs[peer].read_text())
        cfg.update(values)
        self.configs[peer].write_text(json.dumps(cfg))

    def trust(self, mode="trusted"):
        p = self.codex / "config.toml"
        if mode == "missing":
            p.unlink(missing_ok=True)
        elif mode == "malformed":
            p.write_text("[broken\n")
        else:
            s = "".join('[projects.' + json.dumps(str(root)) + ']\ntrust_level = "' +
                        ("untrusted" if mode == "untrusted" else "trusted") + '"\n' for root in self.projects)
            p.write_text("\n".join("# " + line for line in s.splitlines()) if mode == "comment" else s)

    def environment(self, peer=0, **overrides):
        self.epoch += 100
        env = {**self.env, "JV_PROJECT_ID": ("alpha", "beta")[peer],
               "JV_PROJECT_ROOT": str(self.projects[peer]), "JV_LAUNCH_FIXTURE_CONFIG": str(self.configs[peer]),
               "JV_LAUNCH_FIXTURE_EPOCH": str(self.epoch)}
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = str(value)
        return env

    def command(self, letter="A", peer=0, args=(), worktree=True):
        return ["bash", str(self.projects[peer] / "scripts/role-launch.sh"), letter,
                *(["--worktree", str(self.projects[peer])] if worktree else []), *args]

    def launch(self, *args, peer=0, letter="A", env=None, worktree=True):
        return subprocess.run(self.command(letter, peer, args, worktree),
                              env=self.environment(peer, **(env or {})), cwd=self.projects[peer],
                              input="\n", capture_output=True, text=True, timeout=15)

    def successful(self, *args, **kwargs):
        r = self.launch(*args, **kwargs)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def calls(self, kind=None):
        p = self.fixtures / "calls.jsonl"
        rows = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
        return [r for r in rows if kind is None or r["kind"] == kind]

    def refuse(self, *args, diagnostic, dispatch="none", **kwargs):
        before = len(self.calls())
        r = self.launch(*args, **kwargs)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stderr, diagnostic)
        new = self.calls()[before:]
        if dispatch == "none":
            self.assertFalse(new, "rejected input reached a provider command: " + repr(new))
        elif dispatch == "no-interactive":
            self.assertFalse([c for c in new if c["kind"] == "interactive"], repr(new))
        return r

    def record_path(self, peer=0, letter="a"):
        return self.state / ("alpha", "beta")[peer] / "sessions" / (letter + ".json")

    def record(self, peer=0, letter="a", runtime="claude", **values):
        rec = {"schema_version": 1, "project_id": ("alpha", "beta")[peer], "letter": letter,
               "runtime": runtime, "model": "fixture-model", "effort": "xhigh", "workdir": str(self.projects[peer]),
               "session_handle": None, "state": "booted", "capabilities": {},
               "lease": {"holder": None, "epoch": 0, "expires_at": None},
               "watcher": {"location": None, "generation": 0}}
        rec.update(values)
        p = self.record_path(peer, letter)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec) + "\n")
        return p

    def handle(self, runtime="claude", peer=0, letter="A"):
        return self.record_path(peer, letter.lower()).parent / (letter + (".id" if runtime == "claude" else ".codex-thread"))

    def validator(self, record, schema=None, peer=0):
        return subprocess.run(["node", str(self.projects[peer] / "scripts/validate-seat-record.mjs"), str(record),
                               *([str(schema)] if schema else [])], capture_output=True, text=True,
                              env=self.environment(peer), timeout=10)

    @staticmethod
    def after(args, flag):
        return args[args.index(flag) + 1]

    def wait_for(self, predicate, label):
        deadline = time.monotonic() + 6
        while not predicate():
            self.assertLess(time.monotonic(), deadline, "fixture deadline: " + label)
            time.sleep(0.01)

    def spawn(self, *args, peer=0, env=None):
        p = subprocess.Popen(self.command(peer=peer, args=args), cwd=self.projects[peer],
                             env=self.environment(peer, **(env or {})), stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def reap():
            if p.poll() is None:
                p.kill()
            p.communicate(timeout=5)
        self.addCleanup(reap)
        return p

    def flock_shim(self):
        self.stub("flock", '''#!/usr/bin/env python3
import os, pathlib, sys, time
args=sys.argv[1:]
fd=next((int(a) for a in reversed(args) if a.isdigit()),None)
target=os.readlink('/proc/self/fd/'+str(fd)) if fd is not None else ''
kind='seat' if target.endswith('.json.lock') else 'probe' if target.endswith('.jv-tier-probe.lock') else 'identity'
if os.environ.get('JV_TEST_FAIL_LOCK')==kind: sys.exit(77)
gate=os.environ.get('JV_TEST_SEAT_BARRIER')
if gate and kind=='seat':
    p=pathlib.Path(gate)
    p.with_name(p.name+'.arrived.'+str(os.getpid())).write_text('waiting')
    until=time.monotonic()+8
    while not p.exists():
        if time.monotonic()>until: sys.exit(90)
        time.sleep(.01)
os.execv(REAL_FLOCK,['flock',*args])
'''.replace("REAL_FLOCK", repr(shutil.which("flock"))))

    def test_T1_positive_shared_root_and_legacy_canaries_F1(self):
        """I1/F1: same letters, one state root/home; no legacy consumption."""
        legacy = self.state / "sessions"
        legacy.mkdir(parents=True)
        canaries = []
        for letter in ("A", "O"):
            for suffix, value in ((".id", str(uuid.uuid4())), (".codex-thread", "legacy-" + letter.lower())):
                p = legacy / (letter + suffix)
                p.write_text(value + "\n")
                canaries.append(p)
        before = snapshot(legacy)
        with opened(canaries) as reads:
            for peer in (0, 1):
                self.successful("--runtime", "claude", "--model", "fixture-model", "--fresh", peer=peer)
                self.successful("--runtime", "codex", "--model", "fixture-model", "--fresh",
                                peer=peer, letter="O", worktree=False)
        self.assertFalse(reads, "legacy handles were opened/consumed")
        self.assertEqual(snapshot(legacy), before)
        self.assertNotEqual(self.handle(peer=0).read_text(), self.handle(peer=1).read_text())
        for peer, project_id in enumerate(("alpha", "beta")):
            for letter in ("a", "o"):
                rec = json.loads(self.record_path(peer, letter).read_text())
                self.assertEqual((rec["project_id"], rec["letter"], rec["workdir"]),
                                 (project_id, letter, str(self.projects[peer])))
            self.assertEqual(self.handle("codex", peer, "O").read_text().strip(), project_id + "-o")
        for call in self.calls("interactive"):
            self.assertEqual(call["role"], "A" if call["provider"] == "claude" else "O")
            self.assertIsNone(call["source_role"])
            expected = call["project_id"] + ("-a" if call["provider"] == "claude" else "-thinking")
            self.assertEqual(self.after(call["args"], "-n" if call["provider"] == "claude" else "--profile"), expected)
        for peer in (0, 1):
            msg = self.projects[peer] / "scripts/msg.sh"
            sent = subprocess.run(["bash", str(msg), "send", "o", "a", ("ALPHA", "BETA")[peer]],
                                  env=self.environment(peer), capture_output=True, text=True, timeout=15)
            self.assertEqual(sent.returncode, 0, sent.stderr)
        for peer in (0, 1):
            read = subprocess.run(["bash", str(self.projects[peer] / "scripts/msg.sh"), "read", "a"],
                                  env=self.environment(peer), capture_output=True, text=True, timeout=15)
            self.assertEqual(read.returncode, 0, read.stderr)
            self.assertIn(("ALPHA", "BETA")[peer], read.stdout)
            self.assertNotIn(("BETA", "ALPHA")[peer], read.stdout)

    def test_T1_refusal_identity_binding_and_aliases(self):
        """I1: namespace refusal occurs before a provider/foreign-file open."""
        self.record()
        self.successful("--fresh")
        for env in ({"JV_PROJECT_ID": None}, {"JV_PROJECT_ID": "../foreign"},
                    {"JV_PROJECT_ROOT": None}, {"JV_STATE_ROOT": "relative"},
                    {"JV_PROJECT_ROOT": self.projects[1]}, {"JV_STATE_ROOT": None}):
            with self.subTest(env=env):
                self.refuse(diagnostic=r"(?i)(project|root|identity|state)", env=env)
        for key, value in (("project_id", "beta"), ("letter", "o"), ("workdir", str(self.projects[1]))):
            with self.subTest(binding=key):
                p = self.record(**{key: value}) if key != "letter" else self.record()
                if key == "letter":
                    doc = json.loads(p.read_text()); doc[key] = value; p.write_text(json.dumps(doc))
                before = p.read_bytes()
                self.refuse(diagnostic=r"(?i)(record|identity|workdir|letter|project)")
                self.assertEqual(p.read_bytes(), before)
        self.record()
        foreign = self.root / "foreign-canary"
        foreign.write_text("DO NOT CONSUME OR MUTATE\n")
        for target in (self.record_path(), self.handle(), self.record_path().with_suffix(".json.lock")):
            with self.subTest(alias=str(target)):
                old = target.read_bytes() if target.exists() else None
                target.unlink(missing_ok=True)
                target.symlink_to(foreign)
                try:
                    with opened([foreign]) as reads:
                        self.refuse(diagnostic=r"(?i)(symlink|alias|state)")
                    self.assertFalse(reads)
                    self.assertEqual(foreign.read_text(), "DO NOT CONSUME OR MUTATE\n")
                finally:
                    target.unlink()
                    if old is not None:
                        target.write_bytes(old)
        store = self.state / "alpha"
        for target in (store / "sessions", store):
            with self.subTest(directory_alias=str(target)):
                saved = target.with_name(target.name + "-saved")
                target.rename(saved)
                target.symlink_to(saved, target_is_directory=True)
                before = snapshot(saved)
                try:
                    self.refuse(diagnostic=r"(?i)(symlink|alias|state)")
                    self.assertEqual(snapshot(saved), before)
                finally:
                    target.unlink(); saved.rename(target)

    def test_T1_shared_probe_lock_and_T3_lock_failure(self):
        """I1/I3: shared provider home serializes even distinct project probes."""
        for peer in (0, 1):
            self.record(peer, runtime="codex")
        gate = self.fixtures / "release-probe"
        self.configure(probe_barrier=str(gate))
        one = self.spawn("--fresh")
        self.wait_for(lambda: gate.with_suffix(".entered").exists(), "first probe entry")
        two = self.spawn("--fresh", peer=1)
        self.wait_for(lambda: len([c for c in self.calls("version") if c["project_id"] == "beta"]) == 1,
                      "second project reached preflight")
        # Hold the first probe while the second has a chance to reach the lock.
        deadline = time.monotonic() + 0.4
        while time.monotonic() < deadline and two.poll() is None:
            time.sleep(0.01)
        self.assertFalse((self.fixtures / "probe-overlap").exists())
        self.assertEqual(len(self.calls("probe")), 1)
        gate.write_text("release")
        for p in (one, two):
            out, err = p.communicate(timeout=12)
            self.assertEqual(p.returncode, 0, out + err)
        self.assertEqual(len(self.calls("probe")), 2)
        self.flock_shim()
        self.refuse("--fresh", env={"JV_TEST_FAIL_LOCK": "probe"},
                    diagnostic=r"(?i)(lock|serializ)", dispatch="no-interactive")

    def test_T2_positive_bootstrap_and_exact_record_tuple(self):
        """I2/I5: persisted record, not a model table, drives both runtimes."""
        for peer, runtime in enumerate(("claude", "codex")):
            self.configure(peer, model=MODEL, effort="medium")
            self.successful("--runtime", runtime, "--model", MODEL, "--tier", "doing", "--fresh", peer=peer)
            p = self.record_path(peer)
            rec = json.loads(p.read_text())
            self.assertEqual((rec["runtime"], rec["model"], rec["effort"]), (runtime, MODEL, "medium"))
            self.assertEqual(rec["capabilities"], {})
            self.assertEqual(rec["state"], "booted")
            self.assertIsNone(rec["session_handle"])
            checked = self.validator(p, peer=peer)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            before = p.read_bytes()
            self.successful("--fresh", peer=peer)
            self.assertEqual(p.read_bytes(), before)
        for call in self.calls("interactive"):
            if call["provider"] == "claude":
                self.assertEqual(self.after(call["args"], "--model"), MODEL)
                self.assertEqual(self.after(call["args"], "--effort"), "medium")
            else:
                self.assertEqual(self.after(call["args"], "--profile"), "beta-doing")

    def test_T2_refusal_bootstrap_and_tuple_variants(self):
        """I2: missing inputs, overrides and source invalid-tuple cases refuse."""
        for args in ((), ("--runtime", "claude"), ("--model", "fixture-model"), ("--tier", "doing")):
            with self.subTest(missing=args):
                self.refuse(*args, diagnostic=r"(?i)(bootstrap|record|runtime|model|tier)")
                self.assertFalse(self.record_path().is_file())
        self.record()
        for args in (("--runtime", "codex"), ("--tier", "doing"), ("--model", "other")):
            with self.subTest(override=args):
                before = self.record_path().read_bytes()
                self.refuse(*args, diagnostic=r"(?i)(record.*exist|bootstrap|override)")
                self.assertEqual(self.record_path().read_bytes(), before)
        variants = [("runtime", "other"), ("model", None), ("model", 7), ("model", ""),
                    ("model", "nul\0model"), ("effort", None), ("effort", 7), ("effort", ""),
                    ("effort", "ultra"), ("schema_version", 2), ("capabilities", []), ("lease", None)]
        for key, value in variants:
            with self.subTest(key=key, value=value):
                p = self.record(**{key: value})
                before = p.read_bytes()
                self.refuse(diagnostic=r"(?i)(record|schema|" + key + ")")
                self.assertEqual(p.read_bytes(), before)
        for field in ("model", "effort"):
            p = self.record(); rec = json.loads(p.read_text()); del rec[field]; p.write_text(json.dumps(rec))
            self.refuse(diagnostic=r"(?i)(record|" + field + ")")
        self.record_path().write_text('{"runtime":')
        self.refuse(diagnostic=r"(?i)(json|malformed|record)")
        p = self.record(); p.chmod(0)
        try:
            self.refuse(diagnostic=r"(?i)(read|record|permission)")
        finally:
            p.chmod(0o600)

    def test_T2_lock_race_and_failed_lock(self):
        """I2: decision belongs inside lock; a loser never replaces authority."""
        self.flock_shim()
        self.refuse("--runtime", "claude", "--model", "first", env={"JV_TEST_FAIL_LOCK": "seat"},
                    diagnostic=r"(?i)lock")
        self.assertFalse(self.record_path().is_file())
        gate = self.fixtures / "seat-release"
        one = self.spawn("--runtime", "claude", "--model", "first", "--fresh", env={"JV_TEST_SEAT_BARRIER": gate})
        two = self.spawn("--runtime", "claude", "--model", "second", "--fresh", env={"JV_TEST_SEAT_BARRIER": gate})
        self.wait_for(lambda: len(list(self.fixtures.glob("seat-release.arrived.*"))) == 2, "both seat-lock contenders")
        gate.write_text("release")
        results = [p.communicate(timeout=12) for p in (one, two)]
        self.assertEqual(sum(p.returncode == 0 for p in (one, two)), 1, repr(results))
        loser = 0 if one.returncode else 1
        self.assertRegex(results[loser][1], r"(?i)(record.*exist|bootstrap|override)")
        calls = self.calls("interactive")
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(self.record_path().read_text())["model"], self.after(calls[0]["args"], "--model"))

    def test_T2_single_image_when_original_path_is_replaced(self):
        """I2: swapping authority after its first open cannot produce a mixed tuple."""
        p = self.record(model="image-one", effort="xhigh")
        replacement = {**json.loads(p.read_text()), "model": "image-two", "effort": "medium"}
        # Pause after opening the old inode, before reading it. This makes the
        # pathname swap deterministic; a timing-only inotify race can miss it.
        hooks = self.root / "read-hooks"; hooks.mkdir()
        gate = hooks / "release"
        (hooks / "sitecustomize.py").write_text('''import builtins,os,pathlib,time
_open=builtins.open
def opened(file,*args,**kwargs):
    result=_open(file,*args,**kwargs)
    target=os.environ['JV_TEST_SNAPSHOT_PATH']
    if isinstance(file,(str,bytes,os.PathLike)) and os.fsdecode(file)==target:
        gate=pathlib.Path(os.environ['JV_TEST_SNAPSHOT_GATE'])
        seen=gate.with_suffix('.opened')
        if not seen.exists():
            seen.write_text('opened old inode')
            until=time.monotonic()+8
            while not gate.exists():
                if time.monotonic()>until: raise RuntimeError('snapshot fixture expired')
                time.sleep(.01)
    return result
builtins.open=opened
''')
        (hooks / "node-read.cjs").write_text('''const fs=require('node:fs');
const original=fs.readFileSync;
fs.readFileSync=function(path,...args) {
  if(String(path)!==process.env.JV_TEST_SNAPSHOT_PATH) return original.call(fs,path,...args);
  const fd=fs.openSync(path,'r'), gate=process.env.JV_TEST_SNAPSHOT_GATE;
  if(!fs.existsSync(gate+'.opened')) {
    fs.writeFileSync(gate+'.opened','opened old inode');
    const until=Date.now()+8000, wait=new Int32Array(new SharedArrayBuffer(4));
    while(!fs.existsSync(gate)) {if(Date.now()>until) throw Error('snapshot fixture expired'); Atomics.wait(wait,0,0,10);}
  }
  try {return original.call(fs,fd,...args);} finally {fs.closeSync(fd);}
};
require('node:module').syncBuiltinESMExports();
''')
        proc = self.spawn("--fresh", env={"PYTHONPATH": hooks, "NODE_OPTIONS": "--require=" + str(hooks / "node-read.cjs"),
                                          "JV_TEST_SNAPSHOT_PATH": p, "JV_TEST_SNAPSHOT_GATE": gate})
        self.wait_for(lambda: gate.with_suffix(".opened").exists(), "old inode open, reader paused")
        other = p.with_name("replacement.json"); other.write_text(json.dumps(replacement)); other.replace(p)
        gate.write_text("release")
        out, err = proc.communicate(timeout=12)
        self.assertEqual(proc.returncode, 0, out + err)
        call = self.calls("interactive")[-1]
        self.assertEqual((self.after(call["args"], "--model"), self.after(call["args"], "--effort")),
                         ("image-one", "xhigh"))

    def test_T2_bootstrap_candidate_write_validation_and_publish_failures(self):
        """I2: failed write/validation/publication leaves no invalid authority."""
        self.record_path().parent.mkdir(parents=True)
        lock = self.record_path().with_suffix(".json.lock"); lock.touch()
        self.record_path().parent.chmod(0o555)
        try:
            self.refuse("--runtime", "claude", "--model", "m", diagnostic=r"(?i)(write|record|permission|candidate)")
            self.assertFalse(self.record_path().is_file())
        finally:
            self.record_path().parent.chmod(0o755)
        schema = self.projects[0] / "docs/seat-record.schema.json"
        original = schema.read_bytes()
        bad = json.loads(original); bad["required"].append("fixture_missing_field"); schema.write_text(json.dumps(bad))
        try:
            self.refuse("--runtime", "claude", "--model", "m", diagnostic=r"(?i)(valid|schema|record)")
            self.assertFalse(self.record_path().is_file())
        finally:
            schema.write_bytes(original)
        # Inject a publication obstruction AFTER the real validator succeeded.
        # A directory seeded before launch would only test record-type refusal.
        native_node = shutil.which("node")
        marker = self.fixtures / "publication-injected"
        self.stub("node", '''#!/usr/bin/env python3
import pathlib,subprocess,sys
r=subprocess.run([REAL_NODE,*sys.argv[1:]])
if r.returncode==0 and any(pathlib.Path(a).name=='validate-seat-record.mjs' for a in sys.argv[1:]):
    pathlib.Path(MARKER).write_text('after successful validation')
    target=pathlib.Path(TARGET)
    if not target.exists(): target.mkdir()
sys.exit(r.returncode)
'''.replace("REAL_NODE", repr(native_node)).replace("MARKER", repr(str(marker))).replace("TARGET", repr(str(self.record_path()))))
        self.refuse("--runtime", "claude", "--model", "m", diagnostic=r"(?i)(record|directory|publish|exist)")
        self.assertTrue(marker.is_file(), "publication fault must actually be reached")
        self.assertTrue(self.record_path().is_dir())

    def test_T3_positive_attributed_probe_and_refusal_variants(self):
        """I3: preflight must use its own thread, parsed trust and exact tuple."""
        self.record(runtime="codex")
        self.configure(foreign_rollout=True)
        self.successful("--fresh")
        self.assertEqual([c["kind"] for c in self.calls()], ["version", "probe", "interactive"])
        probe = self.calls("probe")[0]
        self.assertEqual(self.after(probe["args"], "-p"), "alpha-thinking")
        self.assertEqual(self.after(probe["args"], "-s"), "read-only")
        for mode in ("missing", "malformed", "comment", "untrusted"):
            with self.subTest(trust=mode):
                self.trust(mode)
                self.refuse("--fresh", diagnostic=r"(?i)(trust|parse|config)", dispatch="no-interactive")
        self.trust()
        for fault in ("version_fail", "probe_fail", "no_thread", "no_rollout", "no_context"):
            with self.subTest(fault=fault):
                self.configure(**{fault: True})
                self.refuse("--fresh", diagnostic=r"(?i)(binary|probe|thread|rollout|context|run|tier)", dispatch="no-interactive")
                self.configure(**{fault: False})
        for key, value in (("probe_model", "wrong-model"), ("probe_effort", "medium"), ("probe_effort", "")):
            with self.subTest(mismatch=key, value=value):
                self.configure(**{key: value}, foreign_rollout=True)
                self.refuse("--fresh", diagnostic=r"(?i)(mismatch|tier)", dispatch="no-interactive")
                self.configure(**{key: None})
        self.refuse("--fresh", env={"JV_CODEX_BIN": self.root / "not-executable"},
                    diagnostic=r"(?i)(binary|executable|codex)")
        self.refuse("--fresh", env={"JV_CODEX_BIN": None}, diagnostic=r"(?i)(binary|pin|codex)")
        native_timeout = shutil.which("timeout")
        self.stub("timeout", '#!/bin/sh\nexit 124\n')
        before = len(self.calls("probe"))
        self.refuse("--fresh", diagnostic=r"(?i)(probe|timeout)", dispatch="no-interactive")
        self.assertEqual(len(self.calls("probe")), before, "timeout shim never starts a provider")
        self.assertTrue(native_timeout)

    def test_T4_claude_fresh_resume_and_invalid_handle(self):
        """I4: UUID/history existence decide attach; unsafe handles never escape."""
        self.record()
        self.successful()
        first = self.handle().read_text().strip()
        self.assertEqual(str(uuid.UUID(first)), first.lower())
        self.assertEqual(self.after(self.calls("interactive")[-1]["args"], "--session-id"), first)
        history = self.home / ".claude/projects" / str(self.projects[0]).replace("/", "-")
        history.mkdir(parents=True)
        (history / (first + ".jsonl")).write_text("{}\n")
        self.successful()
        self.assertEqual(self.after(self.calls("interactive")[-1]["args"], "--resume"), first)
        (history / (first + ".jsonl")).unlink()
        self.successful()
        second = self.handle().read_text().strip()
        self.assertNotEqual(second, first)
        self.successful("--fresh")
        self.assertNotEqual(self.handle().read_text().strip(), second)
        for value in ("../../foreign", "--dangerous-option", "not-a-uuid"):
            with self.subTest(handle=value):
                self.handle().write_text(value + "\n")
                self.refuse(diagnostic=r"(?i)(uuid|session|handle)")

    def test_T4_codex_resume_guard_and_ambiguous_name_F2(self):
        """I4/F2: duplicate qualified names fail; there is no fresh fallback."""
        self.record(runtime="codex")
        first = self.successful("--fresh")
        self.assertRegex(first.stdout, r"(?i)intended")
        self.assertRegex(first.stdout, r"(?i)(not verified|unverified)")
        self.assertRegex(first.stdout, r"(?i)advisory")
        before = self.handle("codex").read_bytes()
        self.refuse(diagnostic=r"(?i)(resume|modal|tmux)", dispatch="no-interactive", env={"TMUX": None})
        self.assertEqual(self.handle("codex").read_bytes(), before)
        self.successful("--at-machine")
        self.assertEqual(self.calls("interactive")[-1]["args"][:2], ["resume", "alpha-a"])
        self.successful(env={"TMUX": "fixture-session"})
        self.successful("--fresh")  # Same project-qualified name now represents two threads.
        names = json.loads((self.codex / "fixture-names.json").read_text())
        self.assertEqual(names["alpha-a"], 2)
        before = len(self.calls("interactive"))
        r = self.refuse("--at-machine", diagnostic=r"(?i)ambiguous.*thread|thread.*ambiguous", dispatch="allowed")
        self.assertNotEqual(r.returncode, 0)
        attempts = self.calls("interactive")[before:]
        self.assertEqual(len(attempts), 1, "an ambiguous resume must not retry or fresh-boot")
        self.assertEqual(attempts[0]["args"][:2], ["resume", "alpha-a"])
        self.assertEqual(self.handle("codex").read_text().strip(), "alpha-a")
        self.handle("codex").write_text("beta-a\n")
        self.refuse("--at-machine", diagnostic=r"(?i)(name|handle|project|thread)", dispatch="no-interactive")

    def test_T4_codex_post_exit_evidence_and_statuses(self):
        """I4: advisory matches, missing evidence and abnormal exits stay distinct."""
        self.record(runtime="codex")
        variants = [({"post_missing": True}, 5), ({"post_ambiguous": True}, 5),
                    ({"post_no_context": True}, 5), ({"post_model": "wrong-model"}, 4),
                    ({"exit": 37}, 37), ({"exit": 137}, 137),
                    ({"exit": 130, "post_missing": True}, 0), ({"exit": 143, "post_missing": True}, 0)]
        for config, wanted in variants:
            with self.subTest(config=config):
                self.configs[0].write_text(json.dumps({"model": "fixture-model", "effort": "xhigh", **config}))
                r = self.launch("--fresh")
                self.assertEqual(r.returncode, wanted, r.stdout + r.stderr)
                if wanted == 5:
                    self.assertRegex(r.stdout + r.stderr, r"(?i)(no evidence|no rollout|attributable)")
                if wanted == 4:
                    self.assertRegex(r.stderr, r"(?i)(mismatch|different tier)")

    def test_T5_print_only_boot_and_neutral_runtime_policy(self):
        """I5/F3: prompts have no effects; runtime setup guidance states limits."""
        for letter in ("O", "I", "A"):
            before = snapshot(self.root)
            r = subprocess.run(["bash", str(self.projects[0] / "scripts/boot-role.sh"), letter],
                               env=self.environment(), capture_output=True, text=True, timeout=5)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("AGENTS.md", r.stdout)
            self.assertRegex(r.stdout, r"scripts/msg\.sh\s+read\s+" + letter.lower() + r"\b")
            self.assertNotIn("<LETTER>", r.stdout)
            self.assertEqual(snapshot(self.root), before, "printing boot must not mutate state or launch a process")
        for runtime in ("claude", "codex"):
            self.record(runtime=runtime)
            self.successful("--fresh")
        for call in self.calls("interactive"):
            self.assertNotIn("--dangerously-skip-permissions", call["args"])
            if call["provider"] == "claude":
                self.assertEqual(self.after(call["args"], "--remote-control"), "alpha-a")
        docs = (self.projects[0] / "docs/CLUSTER.md").read_text()
        for pattern in (r"0\.159", r"2026-09-30", r"(?i)exact.*gitdir", r"(?i)writable.root", r"W-D3",
                        r"(?is)read.only.*(cannot|does not).*writ", r"(?i)(ambiguous|duplicate).*name", r"UUID"):
            self.assertRegex(docs, pattern)
        for rel in ("AGENTS.md", "docs/DELIVERY.md", "docs/SKILL_MODES.md", "docs/REVIEW_PRACTICE.md"):
            self.assertTrue((self.projects[0] / rel).is_file(), "boot guidance closure missing: " + rel)

    def test_T5_refusal_invalid_boot_and_missing_template(self):
        """I5: invalid boot input is not a printable-success response."""
        script = self.projects[0] / "scripts/boot-role.sh"
        for args in ([], ["a"], ["../O"], ["AA"], ["A", "extra"]):
            with self.subTest(args=args):
                before = snapshot(self.root)
                r = subprocess.run(["bash", str(script), *args], env=self.environment(),
                                   capture_output=True, text=True, timeout=5)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(r.stdout, "")
                self.assertRegex(r.stderr, r"(?i)(usage|letter|argument)")
                self.assertEqual(snapshot(self.root), before)
        (self.projects[0] / "docs/orchestration/role-templates/O.md").unlink()
        r = subprocess.run(["bash", str(script), "O"], env=self.environment(), capture_output=True, text=True, timeout=5)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertRegex(r.stderr, r"(?i)(template|missing|no such)")

    def test_T5_T6_operating_scan_with_seeded_refusals(self):
        """I5/I6: bounded operating scan and explicit sensitivity controls."""
        self.assertFalse(scan_operating(self.projects[0]))
        self.assertFalse(scan_operating(self.projects[1]))
        p = self.projects[0] / "docs/CLUSTER.md"
        original = p.read_bytes()
        for seed, kind in (("/home/" + "justi/dev/" + "customer-portal", "coupling"),
                           ("JA" + "UTO_ROLE", "coupling"),
                           ("ghp_" + "X" * 32, "secret")):
            with self.subTest(kind=kind):
                p.write_bytes(original + b"\n" + seed.encode())
                self.assertIn(kind, {x["check"] for x in scan_operating(self.projects[0])})
        p.write_bytes(original)

    def schema_base(self):
        p = self.record(state="active", session_handle="fixture-handle",
                        heartbeat={"at": "2026-07-28T00:00:00Z", "wake_count": 1, "cadence_seconds": 1800})
        return json.loads(p.read_text())

    def schema_case(self, rec, code=0, diagnostic=None, schema=None):
        p = self.fixtures / "schema-record.json"
        p.write_text(json.dumps(rec))
        r = self.validator(p, schema)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        if code:
            self.assertEqual(r.stdout, "", "a rejected record must emit no consumable stdout")
            self.assertRegex(r.stderr, diagnostic)
        return r

    def test_T6_schema_contract_and_nested_regressions(self):
        """I6: retain source 5a-5d, both polarities, no hand-mirrored validator."""
        base = self.schema_base()
        self.schema_case(base)
        booted = {**base, "state": "booted", "model": None, "effort": None, "session_handle": None}
        del booted["heartbeat"]
        self.schema_case(booted)
        variants = [({"model": None, "effort": None}, r"model|effort"),
                    ({"lease": None, "watcher": None}, r"lease|watcher"),
                    ({"watcher": {}}, "watcher"),
                    ({"lease": {"holder": None, "epoch": -1, "expires_at": None}}, "lease.epoch"),
                    ({"watcher": {"location": None, "generation": 0, "bogus": 1}}, "watcher"),
                    ({"session_handle": 42}, "session_handle"), ({"capabilities": []}, "capabilities")]
        for values, diagnostic in variants:
            with self.subTest(values=values):
                self.schema_case({**base, **values}, 1, diagnostic)
        for value in ("yes", 7):
            self.schema_case({**base, "capabilities": {"hooks": {"value": value, "probed_at": "2026-07-28T00:00:00Z"}}},
                             1, r"hooks.value")
        self.schema_case({**base, "capabilities": {"external_invoke": {"value": "bogus", "probed_at": "2026-07-28T00:00:00Z"}}},
                         1, r"external_invoke.value")
        self.schema_case({**booted, "heartbeat": None}, 1, "heartbeat")
        self.schema_case({**base, "toString": 1}, 1, "toString")
        # Two source mutants prove rejection is controlled by the schema itself.
        path = self.projects[0] / "docs/seat-record.schema.json"
        tier = json.loads(path.read_text())
        for branch in tier["allOf"]:
            if "active" in branch.get("if", {}).get("properties", {}).get("state", {}).get("enum", []):
                branch["if"]["required"] = ["__fixture_never_present__"]
        mutant = self.fixtures / "relaxed-tier.json"; mutant.write_text(json.dumps(tier))
        self.schema_case({**base, "model": None, "effort": None}, schema=mutant)
        lw = json.loads(path.read_text())
        lw["required"] = [k for k in lw["required"] if k not in ("lease", "watcher")]
        for k in ("lease", "watcher"):
            lw["properties"][k]["type"] = ["object", "null"]
        mutant.write_text(json.dumps(lw))
        self.schema_case({**base, "lease": None, "watcher": None}, schema=mutant)

    def test_T6_schema_dates_unicode_and_keyword_refusal(self):
        """I6: retain source format/differential regressions and fail closed gaps."""
        base = self.schema_base()
        timestamps = {
            "not-a-timestamp": False, "2026-02-30T00:00:00Z": False,
            "2026-01-01T24:00:00+14:00": False, "2026-01-01T00:00:00-24:00": False,
            "2026-01-01T00:30:00+01:00": True, "2026-01-01T00:30:00-05:00": True,
            "2026-01-01T00:30:00+14:00": True, "2026-01-01T12:34:60Z": False,
            "2016-12-31T23:59:60Z": True, "2016-12-31T15:59:60-08:00": True,
            "0000-02-29T00:00:00Z": True, "2026-02-29T00:00:00Z": False,
            "2026-01-01T23:59:60Z": False, "2026-06-30T23:59:60Z": True,
            "2026-07-01T00:59:60+01:00": True, "2026-06-30T00:59:60+01:00": False}
        for stamp, valid in timestamps.items():
            with self.subTest(timestamp=stamp):
                self.schema_case({**base, "heartbeat": {**base["heartbeat"], "at": stamp}},
                                 0 if valid else 1, r"heartbeat.at")
        for count in (2000, 2001):
            self.schema_case({**base, "heartbeat": {**base["heartbeat"], "context": "😀" * count}},
                             0 if count == 2000 else 1, r"heartbeat.context")
        schema_path = self.projects[0] / "docs/seat-record.schema.json"
        schema = json.loads(schema_path.read_text())
        schema["properties"]["heartbeat"]["properties"]["context"]["minLength"] = 2
        modified = self.fixtures / "modified-schema.json"; modified.write_text(json.dumps(schema))
        self.schema_case({**base, "heartbeat": {**base["heartbeat"], "context": "😀"}}, 1, "heartbeat.context", modified)
        result = self.validator("--keyword-coverage", schema_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        schema["properties"]["heartbeat"]["unevaluatedProperties"] = False
        modified.write_text(json.dumps(schema))
        self.schema_case(base, 3, r"(?i)(unimplemented|not implement|keyword)", modified)

    def test_T6_missing_dependencies_refuse_before_dispatch(self):
        """I6: missing closure/executables are not silent skipped checks."""
        self.record(runtime="codex")
        for rel in ("scripts/lib/jv-project.sh", "scripts/lib/codex-seat.sh",
                    "scripts/validate-seat-record.mjs", "docs/seat-record.schema.json"):
            with self.subTest(missing=rel):
                p = self.projects[0] / rel
                old = p.read_bytes(); p.unlink()
                try:
                    self.refuse("--fresh", diagnostic=r"(?i)(missing|not found|no such|schema|helper|validat)")
                finally:
                    p.write_bytes(old)
        # PATH controlled to remove one required executable without touching it.
        closed = self.root / "closed-bin"; closed.mkdir()
        commands = ("bash", "python3", "node", "jq", "flock", "dirname", "realpath", "readlink", "mkdir", "mktemp",
                    "cat", "find", "tr", "head", "tail", "rm", "mv", "cp", "chmod", "date", "timeout", "git", "env")
        for name in commands:
            target = shutil.which(name)
            if target:
                (closed / name).symlink_to(target)
        for name in ("node", "python3", "jq"):
            p = closed / name
            target = os.readlink(p); p.unlink()
            try:
                self.refuse("--fresh", env={"PATH": str(closed)},
                            diagnostic=r"(?i)(required|not found|missing|python|node|jq)", dispatch="no-interactive")
            finally:
                p.symlink_to(target)


if __name__ == "__main__":
    unittest.main(verbosity=2)

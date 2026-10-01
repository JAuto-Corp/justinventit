#!/usr/bin/env python3
"""W-C1 generated-CLI witnesses. Python stdlib; Linux/GNU runtime, no live hub.

Run with JV_MSG_SCRIPT and JV_MSG_PEER_SCRIPT pointing to two Copier renders.
Every test names an invariant or the SPEC audit finding it witnesses. Negative
tests require specific diagnostics and artifacts, not just a nonzero status.
An absent CLI is reported as the initial feature-absence RED, never as a passed
refusal. Mutants at GREEN separately establish that guards are observed.
"""
import concurrent.futures
import contextlib
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(os.environ.get("JV_MSG_SCRIPT", Path(__file__).parents[1] / "msg.sh"))
PEER_SCRIPT = Path(os.environ.get("JV_MSG_PEER_SCRIPT", SCRIPT))
ULID = "01KYZ000000000000000000001"
ULID2 = "01KYZ000000000000000000002"
ULID_RE = r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$"
KEY = "synthetic-service-key-only"
LITERAL = 'needle café 日本語 🚀 `ticks` $(not-executed) "quotes" \\ slash\nsecond line'


def snapshot(root):
    """Content/shape oracle; do not follow symlinks while observing damage."""
    result = {}
    if not root.exists():
        return result
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(parent) / name
            rel = str(p.relative_to(root))
            if p.is_symlink():
                result[rel] = ("symlink", os.readlink(p))
            elif p.is_file():
                result[rel] = ("file", p.read_bytes())
            else:
                result[rel] = ("directory",)
    return result


@contextlib.contextmanager
def watch_opens(root):
    """F1: Linux inotify observes foreign opens, including read-only access.

    Install watches after the snapshot oracle has read fixtures. Watching OPEN
    is stronger than checking stdout or atime (relatime can hide a read).
    lstat/readlink safety checks do not trigger OPEN on the foreign target.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "inotify_init1")
    events = []
    try:
        for p in [root, *root.rglob("*")]:
            if p.is_symlink():
                continue
            if libc.inotify_add_watch(fd, os.fsencode(p), 0x20) < 0:  # IN_OPEN
                raise OSError(ctypes.get_errno(), "inotify_add_watch")
        yield events
        try:
            events.append(os.read(fd, 65536))
        except BlockingIOError:
            pass
    finally:
        os.close(fd)


class Mailbox(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "W-C1 feature absent: generated scripts/msg.sh")
        self.assertTrue(PEER_SCRIPT.is_file(), "W-C1 peer CLI absent")
        self.tmp = tempfile.TemporaryDirectory(prefix="jv-msg-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.projects = [self.root / "project alpha", self.root / "project beta"]
        for p in self.projects:
            p.mkdir()
        self.state = self.root / "state"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = {
            "PATH": os.environ["PATH"], "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "JV_PROJECT_ID": "alpha", "JV_PROJECT_ROOT": str(self.projects[0]),
            "JV_STATE_ROOT": str(self.state),
        }

    def run_msg(self, *args, peer=False, env=None, stdin=None, xpg=False):
        run_env = dict(self.env)
        if peer:
            run_env.update(JV_PROJECT_ID="beta", JV_PROJECT_ROOT=str(self.projects[1]))
        for k, v in (env or {}).items():
            if v is None:
                run_env.pop(k, None)
            else:
                run_env[k] = str(v)
        cmd = ["bash", *(["-O", "xpg_echo"] if xpg else []), str(PEER_SCRIPT if peer else SCRIPT), *args]
        return subprocess.run(cmd, env=run_env, input=stdin, text=True,
                              capture_output=True, timeout=20, cwd=self.projects[int(peer)])

    def ok(self, *args, **kwargs):
        r = self.run_msg(*args, **kwargs)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r.stdout

    def refuse(self, args, diagnostic, code=None, **kwargs):
        r = self.run_msg(*args, **kwargs)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        if code is not None:
            self.assertEqual(r.returncode, code, r.stderr)
        self.assertRegex(r.stderr, diagnostic)
        return r

    def mail(self, peer=False):
        return self.state / ("beta" if peer else "alpha") / "mail"

    def events(self, peer=False):
        f = self.mail(peer) / "events.jsonl"
        if not f.is_file():
            return []
        events = []
        for raw in f.read_bytes().splitlines():
            length, payload = raw.split(b"\t", 1)
            self.assertEqual(int(length), len(payload))
            event = json.loads(payload)
            self.assertEqual(event["project_id"], "beta" if peer else "alpha")
            self.assertRegex(event["hub_id"], ULID_RE)
            events.append(event)
        return events

    def views(self, sender="o", recipient="a", peer=False):
        f = self.mail(peer) / f"from-{sender}-to-{recipient}.jsonl"
        return [json.loads(x) for x in f.read_text().splitlines() if x] if f.is_file() else []

    def stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/bin/sh\n" + body + "\n")
        p.chmod(0o755)
        return {"PATH": str(self.bin) + ":" + self.env["PATH"]}

    def completion(self, recipients=("a", "o")):
        args = ["hub", "complete", "--from", "O", "--producer", "reviewer",
                "--correlation-id", "run-1", "--outcome", "success"]
        for recipient in recipients:
            args += ["--recipient", recipient]
        return args

    def test_I1_projects_restart_identity_and_independent_cursors(self):
        for peer in (False, True):
            self.ok("send", "o", "a", "peer" if peer else "local", peer=peer, env={"MSG_HUB_ID": ULID})
            self.ok("send", "o", "all", "broadcast", peer=peer)
            self.ok(*self.completion(), peer=peer)
        beta_before = snapshot(self.state / "beta")
        self.assertIn('"body":"local"', self.ok("read", "a"))
        self.assertEqual(snapshot(self.state / "beta"), beta_before)
        self.assertNotIn('"body":"local"', self.ok("read", "a"))
        self.assertIn('"body":"peer"', self.ok("read", "a", peer=True))
        self.assertIn('"body":"broadcast"', self.ok("read", "b"))
        self.ok("archive", "a", "task-1")
        self.assertFalse((self.mail(True) / "archive").exists())
        self.assertEqual(len(self.events()), 3)
        self.assertEqual(len(self.events(True)), 3)
        before = snapshot(self.state)
        self.refuse(["send", "o", "a", "wrong-root"], r"(?i)(identity|bound|project root)",
                    env={"JV_PROJECT_ROOT": self.projects[1]})
        self.assertEqual(snapshot(self.state), before)

    def test_I1_configuration_refusals(self):
        cases = [{"JV_PROJECT_ID": None}, {"JV_PROJECT_ID": "../beta"},
                 {"JV_PROJECT_ID": ""}, {"JV_PROJECT_ID": "A"},
                 {"JV_PROJECT_ROOT": "relative"}, {"JV_PROJECT_ROOT": self.root / "absent"},
                 {"JV_STATE_ROOT": "relative"}]
        cases += [{key: str(self.root / "legacy")} for key in
                  ("MSG_MAILROOT", "HUB_EVENT_LOG", "HUB_APPEND_LOCK", "HUB_DRAIN_TRIGGER")]
        for env in cases:
            with self.subTest(env=env):
                self.refuse(["send", "o", "a", "bad"], r"(?i)(project|root|legacy|override|unset)", env=env)
                self.assertEqual(self.events(), [])
                self.assertFalse((self.root / "legacy").exists())

    def test_I1_unmarked_store_and_path_identifiers(self):
        store = self.state / "alpha"
        store.mkdir(parents=True)
        (store / "foreign").write_text("unowned")
        before = snapshot(self.state)
        self.refuse(["send", "o", "a", "bad"], r"(?i)(unmarked|identity|nonempty|non-empty)")
        self.assertEqual(snapshot(self.state), before)
        shutil.rmtree(store)
        self.ok("send", "service_1", "human", "safe")
        before = snapshot(self.state)
        for bad in ("../beta", "a/b", "a*", "a[bc]", "a.to", "a-to-b", ""):
            for args in (["send", bad, "a", "bad"], ["send", "o", bad, "bad"],
                         ["read", bad], ["peek", bad], ["search", bad, "text"],
                         ["archive", "o", bad]):
                if args[0] == "archive" and bad == "a-to-b":
                    continue  # hyphens are legal in task IDs
                with self.subTest(args=args):
                    self.refuse(args, r"(?i)(role|sender|recipient|task|identifier)")
                    self.assertEqual(snapshot(self.state), before)

    def test_I1_I2_concurrent_initialization_and_appends(self):
        def send(n):
            return self.run_msg("send", "o", "a", f"message-{n}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(send, range(8)))
        self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results])
        events = self.events()
        self.assertEqual(len(events), 8)
        self.assertEqual(len({e["hub_id"] for e in events}), 8)
        self.assertEqual(self.views(), events)

    def test_F1_I1_nested_aliases_do_not_open_or_mutate_peer(self):
        self.ok("send", "o", "a", "local")
        self.ok("read", "a")
        self.ok("archive", "a", "task-a")
        self.ok("send", "o", "a", "FOREIGN-CANARY", peer=True)
        self.ok("read", "a", peer=True)
        self.ok("archive", "a", "task-b", peer=True)
        a = self.state / "alpha"
        b = self.state / "beta"
        # Every initialized path, including archive cursor JSON and cursor locks;
        # also cover the trigger and repair-temp names before they are created.
        paths = list(dict.fromkeys([Path("."), *(p.relative_to(a) for p in a.rglob("*")),
                                   Path("mail/.hub-drain-trigger"), Path("mail/events.jsonl.repair")]))
        for rel in paths:
            original = a / rel
            backup = self.root / "held-artifact"
            existed = original.exists()
            if existed:
                original.rename(backup)
            target = b / rel
            if not target.exists():
                target = b / "mail/from-o-to-a.jsonl"
            original.symlink_to(target, target_is_directory=target.is_dir())
            try:
                before = snapshot(self.state)
                for args in (["read", "a"], ["send", "o", "a", "bad"], ["archive", "a", "alias"]):
                    with self.subTest(path=str(rel), args=args):
                        with watch_opens(b) as accesses:
                            r = self.refuse(args, r"(?i)symlink")
                        self.assertEqual(accesses, [], "foreign target was opened")
                        self.assertNotIn("FOREIGN-CANARY", r.stdout + r.stderr)
                        self.assertEqual(snapshot(self.state), before)
            finally:
                original.unlink()
                if existed:
                    backup.rename(original)
        dangling = a / "mail/cursors/a-from-o-to-a.offset"
        dangling.unlink()
        dangling.symlink_to(b / "not-created")
        before = snapshot(self.state)
        self.refuse(["read", "a"], r"(?i)symlink")
        self.assertEqual(snapshot(self.state), before)

    def test_I2_lock_refusal_has_no_unlocked_delivery(self):
        env = self.stub("flock", "exit 1")
        self.refuse(["send", "o", "a", "initial"], r"(?i)lock", env=env)
        self.assertEqual(self.events(), [])
        self.ok("send", "o", "a", "control")
        before = self.events()
        # Do not let the new identity lock mask the inherited append/archive
        # guard: allow real locks except on the selected transport lock FD.
        real_flock = shutil.which("flock")
        self.assertIsNotNone(real_flock)
        selector = '''for arg in "$@"; do
  case "$arg" in
    [0-9]*) target=$(readlink "/proc/self/fd/$arg" 2>/dev/null || true) ;;
    *) target="$arg" ;;
  esac
  case "$target" in */.hub-append.lock) exit 1 ;; esac
done
exec "$REAL_FLOCK" "$@"'''
        env = {**self.stub("flock", selector), "REAL_FLOCK": real_flock}
        self.refuse(["send", "o", "a", "append"], r"(?i)lock", env=env)
        # A shared-lock-only refusal reaches archive's own lock, not init.
        env = {**self.stub("flock", 'test "${1:-}" != -s || exit 1\nexec "$REAL_FLOCK" "$@"'),
               "REAL_FLOCK": real_flock}
        self.refuse(["archive", "a", "locked"], r"(?i)shared.*lock", env=env)
        self.assertEqual(self.events(), before)
        self.assertEqual(len(self.views()), 1)

    def test_I2_barrier_failure_new_and_replay(self):
        self.ok("send", "o", "a", "seed")
        for stub in ("exit 1", 'test "$#" -gt 0 || exit 1\nfor p in "$@"; do test ! -d "$p" || exit 1; done\nexit 0'):
            with self.subTest(barrier=stub):
                env = self.stub("sync", stub)
                env["MSG_HUB_ID"] = ULID
                for _ in range(2):
                    self.refuse(["send", "o", "a", "barrier"], r"durability barrier", code=8, env=env)
                    self.assertEqual(len(self.views()), 1)
        self.ok("send", "o", "a", "barrier", env={"MSG_HUB_ID": ULID})
        self.assertEqual(len(self.views()), 2)
        self.assertEqual(len(self.events()), 2)

    def test_I2_framing_unicode_and_torn_tail(self):
        self.ok("send", "o", "a", LITERAL)
        self.assertEqual(self.events()[0], self.views()[0])
        log = self.mail() / "events.jsonl"
        for damage in (b'{"torn":', b'999\t{"body":"wrong-length"}\n', b'{"broken":\n'):
            with log.open("ab") as f:
                f.write(damage)
            self.ok("send", "o", "a", "after-repair")
            self.events()  # independent JSON and byte-length validation
        self.assertEqual(len(self.events()), 4)
        self.assertEqual(self.views()[0]["body"], LITERAL)

    def test_I2_authority_projection_and_trigger_failures(self):
        self.ok("send", "o", "a", "seed")
        authority = self.mail() / "events.jsonl"
        held = self.root / "held-authority"
        authority.rename(held)
        authority.mkdir()
        self.refuse(["send", "o", "a", "not-recorded"], r"(?i)(authority|event log|append|record)")
        self.assertEqual(len(self.views()), 1)
        authority.rmdir()
        held.rename(authority)
        blocked = self.mail() / "from-o-to-b.jsonl"
        blocked.mkdir()
        r = self.refuse(["send", "o", "b", "recorded"], r"delivery status unknown", code=5,
                        env={"MSG_HUB_ID": ULID})
        self.assertIn("is recorded", r.stderr)
        self.assertIn("MSG_HUB_ID=" + ULID, r.stderr)
        self.assertEqual(len(self.events()), 2)
        env = self.stub("touch", "exit 1")
        r = self.refuse(["hub", "finding", "--from", "o", "--title", "trigger", "--body", "landed"],
                        r"(?i)(landed|recorded)", code=4, env=env)
        self.assertEqual(len(self.events()), 3)
        self.assertEqual(self.views("o", "o")[0]["body"], "landed")

    def test_I3_replay_conflicts_and_partial_projection(self):
        self.ok("send", "o", "a", LITERAL, env={"MSG_HUB_ID": ULID})
        canonical = self.events()[0]
        self.ok("send", "o", "a", LITERAL, env={"MSG_HUB_ID": ULID})
        self.assertEqual(len(self.events()), 1)
        for args in (["send", "o", "a", "different"], ["send", "o", "b", LITERAL]):
            self.refuse(args, r"DIFFERENT content", code=6, env={"MSG_HUB_ID": ULID})
        self.assertEqual(self.views("o", "b"), [])
        projection = self.mail() / "from-o-to-a.jsonl"
        partial = b'{"ts":"old","hub_i'
        projection.write_bytes(partial)
        (self.mail() / "cursors/a-from-o-to-a.offset").write_text(str(len(partial)))
        env = self.stub("date", 'case "$*" in *%s%3N*) echo 1000000000000;; *) echo 2099-01-01T00:00:00Z;; esac')
        env["MSG_HUB_ID"] = ULID
        self.ok("send", "o", "a", LITERAL, env=env)
        self.assertTrue(projection.read_bytes().startswith(partial + b"\n"))
        self.assertEqual(json.loads(projection.read_bytes().splitlines()[-1]), canonical)
        read = self.ok("read", "a")
        self.assertEqual([json.loads(x) for x in read.splitlines() if x.startswith("{")], [canonical])
        self.assertEqual(len(self.events()), 1)

    def test_I3_invalid_ids_clock_and_entropy(self):
        for invalid in ("bad", "I" * 26, "8" + "0" * 25, "0" * 25):
            self.refuse(["send", "o", "a", "bad"], r"(?i)ULID", env={"MSG_HUB_ID": invalid})
        self.assertEqual(self.events(), [])
        env = self.stub("date", 'case "$*" in *%s%3N*) exit 1;; *) echo 2026-01-01T00:00:00Z;; esac')
        self.refuse(["send", "o", "a", "bad clock"], r"(?i)(clock|timestamp|ULID)", env=env)
        (self.bin / "date").unlink()
        env = self.stub("od", "echo 1 2")
        self.refuse(["send", "o", "a", "short entropy"], r"(?i)(random|entropy|ULID)", env=env)
        self.assertEqual(self.events(), [])

    def test_I4_completion_normalization_and_all_recovery_entries(self):
        args = self.completion(("O", "a", "o", "A"))
        self.ok(*args, env={"MSG_HUB_ID": ULID})
        canonical = self.events()[0]
        self.assertEqual(canonical["recipients"], ["a", "o"])
        self.assertEqual(canonical["hub"]["recipients"], ["a", "o"])
        for mode in ("replay", "read", "append"):
            (self.mail() / "from-o-to-o.jsonl").unlink()
            prefix = (self.mail() / "from-o-to-a.jsonl").read_bytes()
            if mode == "replay":
                self.ok(*args, env={"MSG_HUB_ID": ULID})
            elif mode == "read":
                self.ok("read", "o")
            else:
                self.ok("send", "d", "o", "unrelated")
            self.assertEqual((self.mail() / "from-o-to-a.jsonl").read_bytes(), prefix)
            self.assertEqual(self.views("o", "o"), [{**canonical, "to": "o"}])
        self.assertEqual(len([e for e in self.events() if e["hub_id"] == ULID]), 1)

    def test_I4_completion_failures_are_truthful(self):
        self.ok("send", "d", "a", "seed")
        blocked = self.mail() / "from-o-to-o.jsonl"
        blocked.mkdir()
        args = self.completion()
        for _ in range(2):
            r = self.refuse(args, r"delivery status unknown", code=5, env={"MSG_HUB_ID": ULID})
            self.assertIn("event " + ULID + " is recorded", r.stderr)
            self.assertNotIn("NOT recorded", r.stderr)
        altered = list(args)
        altered[altered.index("success")] = "failure"
        self.refuse(altered, r"DIFFERENT content", code=6, env={"MSG_HUB_ID": ULID})
        r = self.refuse(["send", "d", "o", "new"], r"historical completion", code=5,
                        env={"MSG_HUB_ID": ULID2})
        self.assertIn("current event " + ULID2 + " was NOT recorded", r.stderr)
        self.assertNotIn(ULID2, [e["hub_id"] for e in self.events()])
        blocked.rmdir()
        self.ok("read", "o")
        self.assertEqual(len(self.views("o", "o")), 1)

    def test_I5_plain_envelope_arity_and_correlation(self):
        for args in (["o", "a", "plain"], ["o", "a", "subject", "body"],
                     ["o", "a", "!alert"], ["o", "a", "?request"],
                     ["--correlation-id=work-1", "--", "o", "a", "-subject", "-body"]):
            self.ok("send", *args)
        events = self.events()
        self.assertEqual([e["kind"] for e in events], ["info", "info", "alert", "request", "info"])
        self.assertTrue(all("hub" not in e for e in events))
        self.assertTrue(all("correlation_id" not in e for e in events[:4]))
        self.assertEqual(events[-1]["correlation_id"], "work-1")
        self.assertEqual(events[-1]["from"], "o")
        for args, diagnostic in [(["o", "a", "info", "subject", "body"], "got 5 argument"),
                                 (["--correlation-id", "o", "a", "subject", "body"], "ATTACHED"),
                                 (["--correlation-id=", "o", "a", "body"], "requires a value"),
                                 (["--nonsense", "o", "a", "body"], "unknown flag")]:
            self.refuse(["send", *args], diagnostic)
        self.assertEqual(self.events(), events)

    def test_I5_hub_payloads_and_body_sources(self):
        cases = [
            (["dispatch", "--to", "A", "--title", "dispatch", "--body", LITERAL,
              "--thread", "thread-1", "--issue", "7", "--scope", "Standard"],
             {"op": "dispatch", "to_role": "A", "status": "dispatched", "issue": 7, "scope_class": "Standard"}),
            (["status", "--dispatch", ULID, "--status", "blocked", "--blocked-reason", "waiting"],
             {"op": "status", "dispatch_id": ULID, "blocked_reason": "waiting"}),
            (["rule", "--thread", "t", "--title", "rule", "--body", "text", "--supersedes", ULID],
             {"op": "rule", "thread_id": "t", "supersedes_id": ULID}),
            (["thread", "--open", "--id", "t", "--anchor", "intent", "--owner", "a", "--title", "title",
              "--after", "one", "--after", "two", "--checklist", '[{"done":false}]'],
             {"op": "thread_open", "owner_role": "A", "depends_on": ["one", "two"], "checklist": [{"done": False}]}),
            (["thread", "--update", "t", "--state", "parked", "--next-gate", "wait"],
             {"op": "thread_update", "state": "parked", "next_gate": "wait"}),
            (["finding", "--title", "finding", "--body", "text", "--suggest-thread", "t"],
             {"op": "finding", "suggested_thread_id": "t"}),
            (["finding", "--route", "finding-1", "--thread", "t"], {"op": "finding_route", "finding_id": "finding-1"}),
            (["finding", "--resolve", "finding-1"], {"op": "finding_resolve", "finding_id": "finding-1"}),
            (["attention", "--answer", "yes", "--id", "attention-1"], {"op": "attention_answer", "answer": "yes"}),
        ]
        for args, expected in cases:
            with self.subTest(op=expected["op"]):
                self.ok("hub", *args, "--from", "o")
                e = self.events()[-1]
                self.assertEqual(e["hub"]["hub_id"], e["hub_id"])
                for key, value in expected.items():
                    self.assertEqual(e["hub"][key], value)
        body_file = self.root / "body.txt"
        body_file.write_text(LITERAL)
        for body_args in (["--body-file", str(body_file)], ["--body", "-"]):
            self.ok("hub", "dispatch", "--from", "o", "--to", "a", "--title", "body", *body_args, stdin=LITERAL)
            self.assertEqual(self.events()[-1]["body"], LITERAL)
        self.assertTrue((self.mail() / ".hub-drain-trigger").exists())

    def test_I5_required_and_typed_refusals(self):
        cases = [
            (["dispatch", "--to", "two", "--title", "x", "--body", "x"], "single"),
            (["dispatch", "--to", "a", "--body", "x"], "title"),
            (["status", "--dispatch", ULID, "--status", "bogus"], "status"),
            (["thread", "--update", "t", "--state", "frozen"], "state"),
            (["thread", "--open", "--checklist", "not-json"], "checklist"),
            (["finding", "--route", "x"], "thread"),
        ]
        for args, diagnostic in cases:
            self.refuse(["hub", *args, "--from", "o"], diagnostic, code=2)
        base = self.completion(("o",))
        for flag in ("--producer", "--correlation-id", "--outcome", "--recipient"):
            missing = list(base)
            at = missing.index(flag)
            del missing[at:at + 2]
            self.refuse(missing, "complete:.*" + flag, code=2)
        for flag, value in (("--outcome", "maybe"), ("--recipient", "two"), ("--dispatch", "bad"),
                            ("--result-digest", "sha256:no"), ("--schema-valid", "maybe"),
                            ("--result-ref", ""), ("--verdict", ""), ("--diagnostic-ref", "")):
            self.refuse([*base, flag, value], "complete:.*" + flag, code=2)
        for flags in (["--to", "a"], ["--title", "x"], ["--bogus", "x"], ["--recipient"], ["bare"]):
            self.refuse([*base, *flags], "complete:", code=2)
        self.assertEqual(self.events(), [])
        self.ok(*base, "--dispatch", ULID, "--result-ref", "artifact.json",
                "--result-digest", "sha256:" + "a" * 64, "--schema-valid", "yes",
                "--verdict", "accept", "--diagnostic-ref", "log.txt", "--body", "-", stdin=LITERAL)
        self.assertEqual(self.events()[0]["body"], LITERAL)

    def test_I5_read_peek_broadcast_and_archive_literal_bytes(self):
        self.ok("send", "o", "a", LITERAL)
        self.ok("send", "o", "all", "broadcast")
        before = snapshot(self.mail() / "cursors")
        self.assertIn("new message", self.ok("peek", "a"))
        self.assertEqual(snapshot(self.mail() / "cursors"), before)
        read = self.ok("read", "a", xpg=True)
        records = [json.loads(x) for x in read.splitlines() if x.startswith("{")]
        self.assertEqual({x["body"] for x in records}, {LITERAL, "broadcast"})
        self.assertNotIn('"hub_id"', self.ok("read", "a"))
        self.assertIn('"body":"broadcast"', self.ok("read", "b"))
        original = (self.mail() / "from-o-to-a.jsonl").read_bytes()
        self.ok("archive", "a", "date-task", "--from", "2000-01-01", "--to", "2099-01-01", xpg=True)
        archives = list((self.mail() / "archive/a").glob("*.jsonl"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(json.loads(archives[0].read_text())["body"], LITERAL)
        self.assertEqual((self.mail() / "from-o-to-a.jsonl").read_bytes(), original)
        self.ok("archive", "a", "repeat-task")
        self.assertEqual(len(list((self.mail() / "archive/a").glob("*.jsonl"))), 1)

    def test_F4_I5_search_later_matches_dash_text_and_errors(self):
        self.ok("send", "a", "o", "ordinary nonmatch")
        self.ok("send", "b", "o", "--needle first\nsecond")
        self.ok("archive", "o", "first")
        arc = self.mail() / "archive/o"
        (arc / "000-nonmatch.jsonl").write_text('{"body":"unrelated"}\n')
        for pattern in ("needle", "--needle"):
            out = self.ok("search", "o", pattern, xpg=True)
            matches = [json.loads(line[line.index("{"):]) for line in out.splitlines() if "{" in line]
            self.assertEqual(len(matches), 2, out)
            self.assertTrue(all(m["body"] == "--needle first\nsecond" for m in matches))
            self.assertIn("[archive/", out)
        self.assertNotIn("{", self.ok("search", "o", "no-such-text"))
        env = self.stub("grep", "exit 2")
        self.refuse(["search", "o", "needle"], r"(?i)(grep|search)", env=env)

    def hub_config(self, **changes):
        cfg = self.root / "dedicated-hub.env"
        values = {"HUB_PROJECT_ID": "alpha", "HUB_URL": "https://hub.example.invalid", "HUB_SERVICE_KEY": KEY}
        values.update(changes)
        cfg.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
        return {"MSG_ENV_FILE": str(cfg)}

    def fake_curl(self, mode="ok"):
        # A populated .curlrc is modeled: without -q FIRST it would add a target
        # and trace credentials. A fake keeps the acceptance suite offline.
        stub = self.bin / "curl"
        stub.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]; data=sys.stdin.read(); root=pathlib.Path(os.environ['FAKE_CURL_ROOT'])
with (root/'calls.jsonl').open('a') as f: f.write(json.dumps({'argv':args,'stdin':data})+'\\n')
if not args or args[0]!='-q':
 (root/'decoy-target').write_text('default curl configuration was loaded')
 (root/'credential-trace').write_text(data)
 sys.exit(92)
mode=os.environ.get('FAKE_CURL_MODE','ok')
if mode=='network':
 print(data,file=sys.stderr); sys.exit(7)
if mode=='http':
 print(data+'\\n403'); sys.exit(0)
if any('orchestration_roles?' in a for a in args):
 print('[{"letter":"A","status":"active"}]\\n200')
else:
 print('[{"id":"internal-id","hub_id":"01KYZ000000000000000000001","to_role":"A","title":"fixture task","status":"blocked","blocked_reason":"wait","thread_id":"t","dispatched_at":"2026-01-01"}]\\n200')
''')
        stub.chmod(0o755)
        curl_home = self.root / "curl-home"
        curl_home.mkdir(exist_ok=True)
        (curl_home / ".curlrc").write_text('url = "https://decoy.example.invalid"\ntrace = "credential-trace"\n')
        return {"PATH": str(self.bin) + ":" + self.env["PATH"],
                "CURL_HOME": str(curl_home), "FAKE_CURL_ROOT": str(self.root), "FAKE_CURL_MODE": mode}

    def test_F2_F3_I6_remote_success_no_artifacts_key_only_on_stdin(self):
        env = {**self.hub_config(), **self.fake_curl()}
        for verb in ("target", "seats", "open", "mine", "blocked"):
            for raw in (False, True) if verb != "target" else (False,):
                args = ["hub", verb]
                if verb == "mine":
                    args += ["--from", "a"]
                if raw:
                    args += ["--json"]
                out = self.ok(*args, env=env)
                self.assertNotIn(KEY, out)
                self.assertFalse(self.state.exists(), (verb, "remote read created state"))
                if verb == "target":
                    self.assertIn("https://hub.example.invalid", out)
                    self.assertIn("alpha", out)
                elif raw:
                    self.assertIsInstance(json.loads(out), list)
                else:
                    self.assertIn(ULID, out)
        calls = [json.loads(x) for x in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertGreaterEqual(len(calls), 4)
        for call in calls:
            self.assertEqual(call["argv"][0], "-q")
            self.assertNotIn(KEY, " ".join(call["argv"]))
            self.assertIn(KEY, call["stdin"])
            self.assertEqual(call["argv"].count("-K"), 1)
            urls = [a for a in call["argv"] if a.startswith("https://")]
            self.assertEqual(len(urls), 1)
            self.assertTrue(urls[0].startswith("https://hub.example.invalid/rest/v1/orchestration_"))
        urls = [a for c in calls for a in c["argv"] if a.startswith("https://")]
        self.assertTrue(any("orchestration_roles?" in u and "is_fixture=eq.false" in u for u in urls))
        self.assertTrue(any("status=eq.blocked" in u for u in urls))
        self.assertTrue(any("status=in.(planned,dispatched,acked,in_flight,blocked,review,staged)" in u for u in urls))
        self.assertTrue(any("to_role=eq.A" in a for c in calls for a in c["argv"]))
        self.assertFalse((self.root / "decoy-target").exists())
        self.assertFalse((self.root / "credential-trace").exists())

    def test_F3_I6_remote_failures_no_artifacts_or_secret_diagnostics(self):
        for verb in ("seats", "open", "mine", "blocked"):
            args = ["hub", verb] + (["--from", "a"] if verb == "mine" else [])
            for mode in ("network", "http"):
                env = {**self.hub_config(), **self.fake_curl(mode)}
                r = self.refuse(args, r"(?i)(network|HTTP|request)", env=env)
                self.assertNotIn(KEY, r.stdout + r.stderr)
                self.assertFalse(self.state.exists())
            for changes in ({"MSG_ENV_FILE": None}, {"MSG_ENV_FILE": self.root / "missing"}):
                self.refuse(args, r"(?i)(MSG_ENV_FILE|config|env|credential)", env=changes)
                self.assertFalse(self.state.exists())
            env = self.hub_config(HUB_PROJECT_ID="beta")
            self.refuse(args, r"(?i)(project|identity)", env=env)
            self.assertFalse(self.state.exists())
            self.refuse([*args, "--unknown"], r"(?i)(flag|argument)", env=self.hub_config())
            self.assertFalse(self.state.exists())
        self.refuse(["hub", "target"], r"(?i)(MSG_ENV_FILE|config|env)")
        self.refuse(["hub", "target"], r"(?i)(project|identity)", env=self.hub_config(HUB_PROJECT_ID="beta"))
        self.assertFalse(self.state.exists())

    def test_I6_bad_config_never_executes_or_requests(self):
        curl = self.fake_curl()
        marker = self.root / "executed"
        for changes in ({"HUB_URL": "http://hub.example.invalid"},
                        {"HUB_URL": "https://user@hub.example.invalid"},
                        {"HUB_URL": "https://hub.example.invalid/?query=1"},
                        {"HUB_SERVICE_KEY": 'quote"injection'},
                        {"HUB_SERVICE_KEY": "back\\slash"},
                        {"HUB_SERVICE_KEY": "control\rvalue"},
                        {"HUB_URL": f"$(touch {marker})"}):
            r = self.refuse(["hub", "open"], r"(?i)(URL|key|config|invalid|origin)",
                            env={**self.hub_config(**changes), **curl})
            self.assertNotIn(KEY, r.stdout + r.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / "calls.jsonl").exists())
        self.assertFalse(self.state.exists())
        cfg = self.root / "product.env"
        cfg.write_text("NEXT_PUBLIC_SUPABASE_URL=https://product.example.invalid\nSUPABASE_SERVICE_ROLE_KEY=" + KEY + "\n")
        self.refuse(["hub", "open"], r"(?i)(HUB_|project|config)", env={"MSG_ENV_FILE": cfg, **curl})
        self.assertFalse((self.root / "calls.jsonl").exists())
        self.assertFalse(self.state.exists())

    def test_I7_executable_syntax_and_unconfigured_help(self):
        for script in (SCRIPT, PEER_SCRIPT):
            self.assertTrue(os.access(script, os.X_OK))
            r = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_msg("--help", env={"JV_PROJECT_ID": None, "JV_PROJECT_ROOT": None, "JV_STATE_ROOT": None})
        self.assertIn("Usage", r.stdout + r.stderr)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Standby seats are event-driven: the pacemaker must never turn "no scheduled wake" into a
loop-dead resume or a process-dead escalation (docs/SEAT_PROTOCOL.md §2; template/docs/PACEMAKER.md).

Fixture-driven, dry-run only: runs scripts/pacemaker.sh against a temporary cadence directory and
inspects its log. Also checks that the Stop-hook heartbeat writer preserves the `doorbell:` field a
standby record depends on. Both run without tmux, notifications, or any live seat.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
PACEMAKER = next((c for c in (_HERE.with_name("pacemaker.sh"), _HERE.parent.parent / "scripts" / "pacemaker.sh") if c.is_file()), None)
_HOOK_DIR = _HERE.parent.parent / ".claude" / "hooks" / "stop" / "actions"
WRITER_RENDERED = _HOOK_DIR / "heartbeat-writer.sh"
WRITER_TEMPLATE = _HOOK_DIR / "heartbeat-writer.sh.jinja"


def _iso(delta_seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=delta_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(path, **fields):
    path.write_text("".join(f"{k}: {v}\n" for k, v in fields.items()), encoding="utf-8")


class PacemakerStandbyTests(unittest.TestCase):
    def setUp(self):
        if PACEMAKER is None:
            raise unittest.SkipTest("scripts/pacemaker.sh not present in this project")
        self.tmp = tempfile.TemporaryDirectory()
        self.cad = Path(self.tmp.name) / "cadence"
        self.cad.mkdir()
        self.state = Path(self.tmp.name) / "state"
        self.state.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _sweep(self, roles=""):
        env = dict(os.environ)
        env.update(
            PACEMAKER_DRY_RUN="1",
            PACEMAKER_CADENCE_DIR=str(self.cad),
            PACEMAKER_STATE_DIR=str(self.state),
            PACEMAKER_NOTIFY="none",
            PACEMAKER_ROLES=roles,
        )
        proc = subprocess.run(["bash", str(PACEMAKER)], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout + proc.stderr

    def test_standby_record_is_never_loop_dead_or_process_dead(self):
        # Idle for three hours: heartbeat far past both grace (45 min) and HEARTBEAT_DEAD (90 min).
        _record(self.cad / "w.txt", state="standby", role="w", heartbeat_at=_iso(3 * 3600),
                next_wake_at="event", wake_count=0, cadence_seconds=0, doorbell="mailbox:w",
                context="event-driven pause")
        # Control: a cadence seat whose loop really is overdue must still be resumed.
        _record(self.cad / "a.txt", state="awake", role="a", heartbeat_at=_iso(600),
                next_wake_at=_iso(3 * 3600), wake_count=5, cadence_seconds=900, context="working")
        # Control: an earned dormant seat is skipped on its state alone.
        _record(self.cad / "z.txt", state="dormant", role="z", heartbeat_at=_iso(3 * 3600),
                next_wake_at="none", wake_count=9, cadence_seconds=0, context="concluded")
        log = self._sweep()
        w_text = "\n".join(l for l in log.splitlines() if "role=w" in l)
        self.assertTrue(w_text, log)
        self.assertNotIn("LOOP-DEAD", w_text, log)
        self.assertNotIn("would resume", w_text, log)
        self.assertNotIn("PROCESS-DEAD", w_text, log)
        self.assertIn("standby", w_text, log)
        self.assertIn("doorbell=mailbox:w", w_text, log)
        a_text = "\n".join(l for l in log.splitlines() if "role=a" in l)
        self.assertIn("LOOP-DEAD", a_text, log)
        self.assertIn("would resume", a_text, log)
        z_text = "\n".join(l for l in log.splitlines() if "role=z" in l)
        self.assertIn("dormant", z_text, log)
        self.assertNotIn("would resume", z_text, log)
        self.assertEqual(sorted(p.name for p in self.state.iterdir()), [], "dry-run must not write dedup state")

    def test_legacy_event_marker_without_state_is_standby(self):
        # JA's cadence helper always writes both; a record carrying only the marker must not be resumed.
        _record(self.cad / "k.txt", role="k", heartbeat_at=_iso(3 * 3600), next_wake_at="event",
                cadence_seconds=0, doorbell="mailbox:k", context="legacy shape")
        log = self._sweep()
        k_text = "\n".join(l for l in log.splitlines() if "role=k" in l)
        self.assertNotIn("would resume", k_text, log)
        self.assertNotIn("PROCESS-DEAD", k_text, log)
        self.assertIn("standby", k_text, log)

    def test_standby_without_doorbell_is_flagged_not_resumed(self):
        _record(self.cad / "q.txt", state="standby", role="q", heartbeat_at=_iso(3 * 3600),
                next_wake_at="event", cadence_seconds=0, context="no doorbell declared")
        log = self._sweep()
        q_text = "\n".join(l for l in log.splitlines() if "role=q" in l)
        self.assertNotIn("would resume", q_text, log)
        self.assertIn("WARN", q_text, log)
        self.assertIn("doorbell", q_text, log)


class HeartbeatWriterDoorbellTests(unittest.TestCase):
    """The Stop-hook writer rewrites the cadence file every turn-end; it must carry `doorbell:` through."""

    def _writer(self):
        if WRITER_RENDERED.is_file():
            body = WRITER_RENDERED.read_text(encoding="utf-8")
            if "INERT in this project" in body:
                # Solo-tier renders ship the writer as a declared no-op; identified by its
                # own text, never by a silent outcome.
                raise unittest.SkipTest("heartbeat writer is the declared inert render")
            return body
        if WRITER_TEMPLATE.is_file():
            text = WRITER_TEMPLATE.read_text(encoding="utf-8")
            # Template layout: take the cluster branch between the jinja `if` and `else` lines.
            lines = text.splitlines(keepends=True)
            # Markers are built at runtime so this file never carries a literal template
            # opener (the render matrix scans rendered projects for leaked openers).
            opener = "{" + "% "
            start = next(i for i, l in enumerate(lines) if l.startswith(opener + "if "))
            end = next(i for i, l in enumerate(lines) if l.startswith(opener + "else"))
            return "".join(lines[:start] + lines[start + 1:end])
        raise unittest.SkipTest("heartbeat writer not present in this project")

    def _assert_writer_preserves_standby(self, body):
        """Run a writer body once against a seeded standby record and assert the live-writer contract."""
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "heartbeat-writer.sh"
            script.write_text(body, encoding="utf-8")
            cad = Path(tmp) / "cadence"
            cad.mkdir()
            stale = _iso(3600)
            _record(cad / "w.txt", state="standby", role="w", heartbeat_at=stale,
                    next_wake_at="event", wake_count=3, cadence_seconds=0, doorbell="mailbox:w",
                    context="event-driven pause")
            before = (cad / "w.txt").read_text(encoding="utf-8")
            env = dict(os.environ)
            env.update(PACEMAKER_CADENCE_DIR=str(cad), JUSTINVENTIT_ROLE="w")
            proc = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=30, cwd=tmp)
            self.assertEqual(proc.returncode, 0, "a Stop action must exit 0: " + proc.stdout + proc.stderr)
            after = (cad / "w.txt").read_text(encoding="utf-8")
            self.assertNotEqual(after, before, "live writer must rewrite the cadence file at turn-end")
            fields = dict(l.split(": ", 1) for l in after.splitlines() if ": " in l)
            self.assertEqual(fields.get("state"), "standby", after)
            self.assertEqual(fields.get("next_wake_at"), "event", after)
            self.assertEqual(fields.get("doorbell"), "mailbox:w", after)
            self.assertNotEqual(fields.get("heartbeat_at"), stale, "heartbeat must be re-stamped")

    def test_doorbell_survives_turn_end(self):
        self._assert_writer_preserves_standby(self._writer())

    def test_broken_writer_is_a_failure_not_a_skip(self):
        # Causal fixtures for the check itself: a writer that exits non-zero, and one that exits 0
        # but never rewrites the record, must both FAIL this contract rather than pass silently.
        for name, body in (
            ("nonzero-exit", "#!/bin/bash\nexit 42\n"),
            ("silent-no-write", "#!/bin/bash\nexit 0\n"),
        ):
            with self.subTest(writer=name), self.assertRaises(AssertionError):
                self._assert_writer_preserves_standby(body)


if __name__ == "__main__":
    unittest.main()

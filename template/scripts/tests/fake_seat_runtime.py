#!/usr/bin/env python3
"""Offline W-C2 provider fixture; invoked only with an explicit scratch root.

This creates synthetic CLI evidence, never invokes a provider or reads real auth.
The test owns expected tuples separately from the launcher's arguments.
"""
import fcntl
import json
import os
from pathlib import Path
import sys
import time
import uuid


root = Path(os.environ["JV_LAUNCH_FIXTURE"])
cfg = json.loads(Path(os.environ["JV_LAUNCH_FIXTURE_CONFIG"]).read_text())
provider = Path(sys.argv[0]).name
args = sys.argv[1:]
epoch = int(os.environ["JV_LAUNCH_FIXTURE_EPOCH"])
kind = "version" if "--version" in args else "probe" if "exec" in args else "interactive"
event = {"provider": provider, "kind": kind, "args": args, "cwd": os.getcwd(),
         "project_id": os.environ.get("JV_PROJECT_ID"), "role": os.environ.get("JV_ROLE"),
         "source_role": os.environ.get("JA" + "UTO_ROLE")}
with (root / "calls.jsonl").open("a") as out:
    fcntl.flock(out, fcntl.LOCK_EX)
    out.write(json.dumps(event) + "\n")
    out.flush()


def stop(message, code):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def barrier(label):
    gate = cfg.get(label)
    if not gate:
        return
    p = Path(gate)
    p.with_suffix(".entered").write_text("entered")
    deadline = time.monotonic() + 8
    while not p.exists():
        if time.monotonic() > deadline:
            stop("fixture barrier expired", 90)
        time.sleep(0.01)


def rollout(thread, *, phase, model=None, effort=None, context=True, cwd=None):
    history = Path(os.environ["CODEX_HOME"]) / "sessions" / "synthetic"
    history.mkdir(parents=True, exist_ok=True)
    path = history / ("rollout-fixture-" + thread + ".jsonl")
    data = [{"type": "session_meta", "payload": {"id": thread, "cwd": cwd or os.getcwd(),
                                                "originator": "codex-tui" if phase == "interactive" else "codex-exec"}}]
    if context:
        data.append({"type": "turn_context", "payload": {
            "model": cfg.get("model", "fixture-model") if model is None else model,
            "effort": cfg.get("effort", "xhigh") if effort is None else effort}})
    path.write_text("".join(json.dumps(row) + "\n" for row in data))
    # Deterministic launch clock: preflight precedes launch, TUI follows it.
    stamp = epoch - 2 if phase == "probe" else epoch + 1
    os.utime(path, (stamp, stamp))
    return path


if kind == "version":
    if cfg.get("version_fail"):
        stop("fixture binary cannot run", 71)
    print("codex fixture-only" if provider == "codex" else "claude fixture-only")
    raise SystemExit(0)

if provider == "codex" and kind == "probe":
    active = root / "probe-active"
    try:
        fd = os.open(active, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        (root / "probe-overlap").write_text("concurrent probes")
        stop("fixture observed unserialized probes", 72)
    try:
        barrier("probe_barrier")
        if cfg.get("probe_fail"):
            stop("fixture probe failed", 73)
        thread = str(uuid.uuid4())
        if not cfg.get("no_thread"):
            print(json.dumps({"type": "thread.started", "thread_id": cfg.get("probe_thread_id", thread)}))
        if cfg.get("extra_thread_event"):
            print(json.dumps({"type": "thread.started", "thread_id": str(uuid.uuid4())}))
        workdir = args[args.index("-C") + 1]
        if not cfg.get("no_rollout"):
            own = rollout(thread, phase="probe", cwd=workdir,
                    model=cfg.get("probe_model"), effort=cfg.get("probe_effort"),
                    context=not cfg.get("no_context"))
            if cfg.get("duplicate_probe_rollout"):
                own.with_name("rollout-duplicate-" + thread + ".jsonl").write_bytes(own.read_bytes())
        if cfg.get("foreign_rollout"):
            foreign = rollout(str(uuid.uuid4()), phase="probe",
                              cwd=workdir if cfg.get("foreign_same_workdir") else str(root / "foreign-workdir"))
            os.utime(foreign, (epoch + 50, epoch + 50))
    finally:
        os.close(fd)
        active.unlink()
    raise SystemExit(0)

barrier("interactive_barrier")
if provider == "codex":
    # Simulated human /rename input is independently supplied by the test.
    # Never derive it from the environment: that would hide a bad printed prompt.
    name = cfg["rename_to"]
    index_path = Path(os.environ["CODEX_HOME"]) / "fixture-names.json"
    names = json.loads(index_path.read_text()) if index_path.exists() else {}
    if args and args[0] == "resume":
        wanted = args[1]
        if names.get(wanted, 0) > 1:
            stop("ambiguous thread name: more than one matching thread", 23)
    else:
        names[name] = names.get(name, 0) + 1
        index_path.write_text(json.dumps(names))
    if not cfg.get("post_missing"):
        rollout(str(uuid.uuid4()), phase="interactive", model=cfg.get("post_model"),
                effort=cfg.get("post_effort"), context=not cfg.get("post_no_context"))
        if cfg.get("post_ambiguous"):
            rollout(str(uuid.uuid4()), phase="interactive")
raise SystemExit(cfg.get("exit", 0))

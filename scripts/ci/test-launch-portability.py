#!/usr/bin/env python3
"""W-C2: real Copier consumers, offline launch/schema checks, retained evidence.

The fixture calibration proves only the fake-provider protocol. Generated RED
on missing production scripts is reported separately, never as a guard proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--copier", default="copier")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    template = args.template.resolve()
    evidence = args.evidence.resolve() if args.evidence else Path(tempfile.mkdtemp(prefix="jv-launch-evidence-"))
    if args.evidence:
        evidence.mkdir(parents=True, exist_ok=False)
    scratch = evidence / "scratch"; scratch.mkdir()
    results = []

    def run(label, command, **kwargs):
        command = [str(x) for x in command]
        r = subprocess.run(command, capture_output=True, text=True, **kwargs)
        (evidence / (label + ".stdout")).write_text(r.stdout)
        (evidence / (label + ".stderr")).write_text(r.stderr)
        results.append({"label": label, "argv": command, "status": r.returncode})
        print(label + ": exit " + str(r.returncode), flush=True)
        return r

    copier = shutil.which(args.copier)
    if not copier:
        raise SystemExit("Copier 9.17.1 is required")
    v = run("copier-version", [copier, "--version"])
    if v.returncode or v.stdout.strip() != "copier 9.17.1":
        raise SystemExit("This gate requires Copier 9.17.1")
    git_source = (template / ".git").exists()
    if git_source:
        r = run("source-head", ["git", "-C", template, "rev-parse", "HEAD"])
        if r.returncode:
            raise SystemExit("Cannot pin source HEAD")
    projects = []
    for name, tier in (("alpha", "cluster"), ("beta", "solo")):
        project = scratch / ("consumer " + name)
        r = run("render-" + name,
                [copier, "copy", "--defaults", "--trust", *(["--vcs-ref=HEAD"] if git_source else []),
                 "-d", "project_name=Launch " + name, "-d", "orchestration_tier=" + tier,
                 "-d", "database=none", "-d", "db_adapter=none", "-d", "testing=none", template, project], timeout=120)
        if r.returncode:
            break
        projects.append(project)
    if len(projects) == 2:
        fixture = projects[0] / "scripts/tests/fake_seat_runtime.py"
        calibration = scratch / "fixture-calibration"; calibration.mkdir()
        home = calibration / "home"; home.mkdir()
        codex_home = home / ".codex"; codex_home.mkdir()
        capture = calibration / "capture"; capture.mkdir()
        cfg = calibration / "config.json"; cfg.write_text(json.dumps({"model": "calibrated-model", "effort": "medium"}))
        fake = calibration / "codex"; shutil.copyfile(fixture, fake); fake.chmod(0o755)
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "CODEX_HOME": str(codex_home),
               "JV_PROJECT_ID": "calibration", "JV_ROLE": "A", "JV_LAUNCH_FIXTURE": str(capture),
               "JV_LAUNCH_FIXTURE_CONFIG": str(cfg), "JV_LAUNCH_FIXTURE_EPOCH": "1800000000",
               "PYTHONDONTWRITEBYTECODE": "1"}
        run("fixture-version", [fake, "--version"], env=env, cwd=calibration, timeout=5)
        probe = run("fixture-probe", [fake, "exec", "--json", "-p", "calibration-doing", "-s", "read-only", "-C", calibration],
                    env=env, cwd=calibration, timeout=5)
        thread = json.loads(probe.stdout)["thread_id"]
        rollouts = list(codex_home.rglob("*" + thread + ".jsonl"))
        assert len(rollouts) == 1, "fixture must attribute the probe's own thread"
        context = [json.loads(x) for x in rollouts[0].read_text().splitlines()][1]
        assert context["payload"] == {"model": "calibrated-model", "effort": "medium"}
        for n in (1, 2):
            run("fixture-fresh-" + str(n), [fake, "--profile", "calibration-doing"], env=env, cwd=calibration, timeout=5)
        ambiguous = run("fixture-ambiguous-resume", [fake, "resume", "calibration-a", "--profile", "calibration-doing"],
                        env=env, cwd=calibration, timeout=5)
        assert ambiguous.returncode == 23 and "ambiguous thread name" in ambiguous.stderr
        results[-1].update(status=0, observed_status=23, expected_status=23, scope="fixture only")
        run("generated-launch-tests", [sys.executable, projects[0] / "scripts/tests/test_launch.py"],
            env={**os.environ, "JV_LAUNCH_PROJECT": str(projects[0]), "JV_LAUNCH_PEER": str(projects[1]),
                 "PYTHONDONTWRITEBYTECODE": "1"}, cwd=projects[0], timeout=600)
        hashes = {str(p.relative_to(scratch)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for project in projects for p in project.rglob("*") if p.is_file()}
        (evidence / "rendered-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    else:
        results.append({"label": "both-consumers-rendered", "status": 1})
    (evidence / "commands.json").write_text(json.dumps(results, indent=2) + "\n")
    failed = [r["label"] for r in results if r["status"]]
    print(json.dumps({"evidence": str(evidence), "failed": failed}, indent=2))
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())

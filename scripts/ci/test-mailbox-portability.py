#!/usr/bin/env python3
"""W-C1 I7: render two real consumers and run the extracted CLI witnesses.

No product stack, database or live HTTP request. Evidence directories are new
and retained for review; the caller seals them only after the run completes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


COUPLING = re.compile(r"/home/justi\b|customer-portal|\bjauto\b|\bJAuto\b|[a-z]{20}\.supabase\.(?:co|com)")
SECRET = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-proj-[A-Za-z0-9_-]{20,}|\bsb_secret_[A-Za-z0-9_-]{16,}|\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")


def scan(paths):
    findings = []
    for p in paths:
        if not p.is_file():
            findings.append({"file": str(p), "check": "missing"})
            continue
        for n, line in enumerate(p.read_text().splitlines(), 1):
            for name, regex in (("coupling", COUPLING), ("secret", SECRET)):
                if regex.search(line):
                    # Never emit the possible secret value.
                    findings.append({"file": str(p), "line": n, "check": name})
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--copier", default="copier")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    template = args.template.resolve()
    evidence = args.evidence.resolve() if args.evidence else Path(tempfile.mkdtemp(prefix="jv-mailbox-evidence-"))
    if args.evidence:
        evidence.mkdir(parents=True, exist_ok=False)
    scratch = evidence / "scratch"
    scratch.mkdir()
    results = []

    def run(label, argv, **kwargs):
        r = subprocess.run([str(x) for x in argv], capture_output=True, text=True, **kwargs)
        (evidence / (label + ".stdout")).write_text(r.stdout)
        (evidence / (label + ".stderr")).write_text(r.stderr)
        results.append({"label": label, "argv": [str(x) for x in argv], "status": r.returncode})
        print(f"{label}: exit {r.returncode}", flush=True)
        return r

    copier = shutil.which(args.copier)
    if not copier:
        raise SystemExit("Copier executable is required")
    version = run("copier-version", [copier, "--version"])
    if version.returncode or version.stdout.strip() != "copier 9.17.1":
        raise SystemExit("This gate requires Copier 9.17.1")
    git_source = (template / ".git").exists()
    if git_source:
        head = run("source-head", ["git", "-C", template, "rev-parse", "HEAD"])
        if head.returncode:
            raise SystemExit("Could not pin source HEAD")
    projects = []
    for name, tier in (("alpha", "cluster"), ("beta", "solo")):
        project = scratch / ("consumer " + name)
        projects.append(project)
        cmd = [copier, "copy", "--defaults", "--trust", *(["--vcs-ref=HEAD"] if git_source else []),
               "-d", "project_name=Mailbox " + name, "-d", "orchestration_tier=" + tier,
               "-d", "database=none", "-d", "db_adapter=none", "-d", "testing=none", str(template), str(project)]
        rendered = run("render-" + name, cmd, timeout=120)
        if rendered.returncode:
            break
    if len(projects) == 2 and all(p.is_dir() for p in projects):
        env = {**os.environ, "JV_MSG_SCRIPT": str(projects[0] / "scripts/msg.sh"),
               "JV_MSG_PEER_SCRIPT": str(projects[1] / "scripts/msg.sh")}
        run("generated-mailbox-tests", [sys.executable, projects[0] / "scripts/tests/test_msg.py"],
            env=env, cwd=projects[0], timeout=300)
        # I7 scan positive and refusal control, outside all consumer files.
        seeds = evidence / "scanner-seeds"
        seeds.mkdir()
        (seeds / "coupling.txt").write_text("/home/" + "justi/dev/" + "customer-portal\n")
        (seeds / "secret.txt").write_text("ghp_" + "X" * 32 + "\n")
        seeded = scan(list(seeds.iterdir()))
        assert {x["check"] for x in seeded} == {"coupling", "secret"}, "scanner refusal control failed"
        operating = [p / rel for p in projects for rel in
                     ("scripts/msg.sh", "scripts/tests/test_msg.py", "docs/CLUSTER.md", "docs/PLAYBOOK.md")]
        findings = scan(operating)
        (evidence / "scan.json").write_text(json.dumps({"seeded_checks": seeded, "operating_findings": findings,
                                                        "files": [str(x) for x in operating]}, indent=2) + "\n")
        results.append({"label": "coupling-secret-scan", "status": int(bool(findings))})
        for project in projects:
            cli = project / "scripts/msg.sh"
            if cli.exists():
                results.append({"label": "rendered-cli-sha256", "project": str(project),
                                "sha256": hashlib.sha256(cli.read_bytes()).hexdigest(), "status": 0})
    else:
        results.append({"label": "both-consumers-rendered", "status": 1})
    (evidence / "commands.json").write_text(json.dumps(results, indent=2) + "\n")
    failures = [r["label"] for r in results if r["status"]]
    print(json.dumps({"evidence": str(evidence), "failed": failures}, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())

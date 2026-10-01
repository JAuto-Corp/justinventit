#!/usr/bin/env python3
"""W-C3 F5/I6: bounded pre-execution checks, not a hostile-code sandbox.

Copier materializes release files as DATA with tasks disabled; runtime findings
never authorize running them. Every candidate invocation/mutant rechecks its
whole known liveness closure. Findings print locations/kinds, never values.
"""
from pathlib import Path
import re

CLOSURE = ('scripts/cadence.sh', 'scripts/heartbeat-hook.sh', 'scripts/stall-watchdog.sh',
           'scripts/pacemaker.sh', 'scripts/lib/jv-project.sh', '.claude/hooks/lib/utils.sh',
           'scripts/lib/jv-liveness.py', 'scripts/lib/jv-liveness.sh')
# The delivered GREEN helpers are mandatory; no missing executable is a gate pass.
OPTIONAL_HELPERS = ()
COUPLING = re.compile(r'/home/' + r'justi\b|customer' + r'-portal|\bJA' + r'UTO_ROLE\b|\.jauto-|\bjauto\b', re.I)
SECRET = re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-proj-[A-Za-z0-9_-]{20,}|\bsb_secret_[A-Za-z0-9_-]{16,}')
COMMAND = re.compile(r'(?:^|[;&|()]|\b(?:if|elif|then|do|while|until|else))\s*(?:!\s*)?(?:(?:builtin|command|exec)\s+)?[\"\']?(?:/[^\s\"\']*/)?(?:kill|killall|pkill|pgrep|tmux|curl|wget|ssh|scp|sftp|nc|ncat|netcat|claude|codex|crontab|systemctl|notify-send|osascript)\b')
PY_EFFECT = re.compile(r'\b(?:os\.(?:kill|killpg|system|popen)|subprocess\.|pty\.|ctypes\.)')
DYNAMIC_EFFECT = re.compile(r'^\s*"?\$\{?(?:RESPAWN_HOOK|PACEMAKER_SMS_CMD|WATCHDOG_WT)\b')
HOST_PROC = re.compile(r'(?<![A-Za-z_])/proc(?:/|[\s\"\'])')


def runtime_findings(root):
    root = Path(root)
    findings = []
    paths = [*CLOSURE, *(p for p in OPTIONAL_HELPERS if (root / p).exists())]
    wrapper = '.claude/hooks/stop/actions/heartbeat-writer.sh'
    if (root / wrapper).exists():
        paths.append(wrapper)
    elif (root / (wrapper + '.jinja')).exists():
        paths.append(wrapper + '.jinja')
    for rel in paths:
        p = root / rel
        if p.is_symlink() or not p.is_file():
            findings.append({'file': rel, 'check': 'missing-or-alias'})
            continue
        for n, line in enumerate(p.read_text().splitlines(), 1):
            for name, regex in (('coupling', COUPLING), ('secret', SECRET)):
                if regex.search(line):
                    findings.append({'file': rel, 'line': n, 'check': name})
            # Comments are data, but code and literal shell commands are not.
            if line.lstrip().startswith('#'):
                continue
            for name, regex in (('external-effect', COMMAND), ('python-effect', PY_EFFECT),
                                ('dynamic-effect', DYNAMIC_EFFECT), ('host-proc', HOST_PROC)):
                if regex.search(line):
                    findings.append({'file': rel, 'line': n, 'check': name})
    return findings


def render_findings(config):
    """Permit only data rendering: caller must additionally pass --skip-tasks.

    No custom extensions, migrations or task definitions are in the pinned
    template. A future addition needs a reviewed render boundary, not a skip.
    """
    findings = []
    for n, line in enumerate(config.splitlines(), 1):
        if re.match(r'^_(?:tasks|migrations|jinja_extensions)\s*:', line):
            findings.append({'file': 'copier.yml', 'line': n, 'check': 'executable-render-config'})
        if COUPLING.search(line) or SECRET.search(line):
            findings.append({'file': 'copier.yml', 'line': n, 'check': 'coupling-or-secret'})
    return findings

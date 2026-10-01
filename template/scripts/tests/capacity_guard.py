"""W-C4 I6/I7: bounded source checks before every render/runtime child."""
from pathlib import Path
import re

from liveness_guard import COUPLING, SECRET, COMMAND, PY_EFFECT, render_findings

CLOSURE = ('scripts/build-lock.sh', 'scripts/build-guarded.sh', 'scripts/lib/jv-project.sh')
# R1: fail closed on additional executable dependencies, including a helper
# launched rather than sourced. The only permitted edges are literal peers.
EDGES = {
    CLOSURE[0]: 'source "$SCRIPT_DIR/lib/jv-project.sh"',
    CLOSURE[1]: 'exec bash "$SCRIPT_DIR/build-lock.sh" run "$@"',
}
DEPENDENCY = re.compile(r'(?:^|[;&|()]|\b(?:then|do|else))\s*(?:(?:env|command|exec)\s+)*(?:source|\.|bash|sh)\s+')
WRAPPED_EFFECT = re.compile(r'(?<![\w-])(?:kill|killall|pkill|pgrep|tmux|curl|wget|ssh|scp|sftp|nc|ncat|netcat|claude|codex|crontab|systemctl|notify-send|osascript)(?![\w-])')
# R2: literal host-root fallbacks and HOME/cwd-derived paths are never admitted
# to runtime. This is bounded source inspection, not an arbitrary-shell sandbox.
HOST_PATH = re.compile(r'/(?:tmp|var|run|home|root|mnt|media|srv|etc|opt|dev/shm)(?:/|[\s"\']|$)|\$\{?(?:HOME|TMPDIR|PWD)\b')


def runtime_findings(root):
    findings = []
    for rel in CLOSURE:
        path = Path(root) / rel
        if path.is_symlink() or not path.is_file():
            findings.append({'file': rel, 'check': 'missing-or-alias'})
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for name, regex in (('coupling', COUPLING), ('secret', SECRET)):
                if regex.search(line):
                    findings.append({'file': rel, 'line': n, 'check': name})
            if line.lstrip().startswith('#'):
                continue
            if DEPENDENCY.search(line) and line.strip() != EDGES.get(rel):
                findings.append({'file': rel, 'line': n, 'check': 'undeclared-dependency'})
            if HOST_PATH.search(line):
                findings.append({'file': rel, 'line': n, 'check': 'host-path-open'})
            for name, regex in (('external-effect', COMMAND), ('python-effect', PY_EFFECT)):
                if regex.search(line):
                    findings.append({'file': rel, 'line': n, 'check': name})
            if WRAPPED_EFFECT.search(line):
                findings.append({'file': rel, 'line': n, 'check': 'external-effect'})
            # These two local observations are the admitted source interface:
            # memory availability and this process's own inherited descriptor.
            checked = re.sub(r'/proc/(?:meminfo|self/fd/[A-Za-z0-9_$\{\}]+)', '', line)
            if re.search(r'/proc(?:/|[\s"\'])', checked):
                findings.append({'file': rel, 'line': n, 'check': 'host-process-scan'})
    return findings

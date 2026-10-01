"""W-C4 I6/I7: bounded source checks before every render/runtime child."""
from pathlib import Path
import re

from liveness_guard import COUPLING, SECRET, COMMAND, PY_EFFECT, render_findings

CLOSURE = ('scripts/build-lock.sh', 'scripts/build-guarded.sh', 'scripts/lib/jv-project.sh')


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
            for name, regex in (('external-effect', COMMAND), ('python-effect', PY_EFFECT)):
                if regex.search(line):
                    findings.append({'file': rel, 'line': n, 'check': name})
            # These two local observations are the admitted source interface:
            # memory availability and this process's own inherited descriptor.
            checked = re.sub(r'/proc/(?:meminfo|self/fd/[A-Za-z0-9_$\{\}]+)', '', line)
            if re.search(r'/proc(?:/|[\s"\'])', checked):
                findings.append({'file': rel, 'line': n, 'check': 'host-process-scan'})
    return findings

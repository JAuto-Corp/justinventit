"""W-C5 reviewed-code accident boundary; see SPEC threat model.

Committed guard and adjacent policy are reviewed authority. A candidate that
rewrites policy or self-registers an image is out of scope, including a child
loading its own policy. This is not hostile-code isolation. New bypass classes
go to o for disposition. Unsafe calibration seeds are data, never executed.
"""
import hashlib
import json
from pathlib import Path

from liveness_guard import render_findings

CLOSURE = ('scripts/pace.sh', 'scripts/usage-hook.sh', 'scripts/disk-watch.sh',
           'scripts/lib/jv-observability.sh', 'scripts/lib/jv-observability.py',
           'scripts/lib/jv-project.sh')
POLICY = json.loads(Path(__file__).with_name('observability_allowlist.json').read_text())
assert POLICY['schema'] == 1 and set(POLICY['programs']) == set(CLOSURE)


def runtime_findings(root):
    root = Path(root).absolute()
    findings = []
    for rel in CLOSURE:
        path = root / rel
        chain = (path, *[p for p in path.parents if p == root or root in p.parents])
        if any(p.is_symlink() for p in chain) or not path.is_file():
            findings.append({'file': rel, 'check': 'missing-or-alias'})
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            findings.append({'file': rel, 'check': 'unreadable'})
            continue
        if digest not in {image['sha256'] for image in POLICY['programs'][rel]['images']}:
            findings.append({'file': rel, 'check': 'unknown-image'})
    return findings

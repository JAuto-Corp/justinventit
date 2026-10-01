"""W-C4 closed-world execution admission for the three reviewed shell programs.

The adjacent, committed allowlist pins COMPLETE program bytes, including each
command's arguments, substitutions, control flow and helper edges. Its readable
edge inventory explains those pins. Unknown bytes never gain admission from a
command-name regex, a candidate-local policy, an environment flag, or a source
scan that generates its own allowlist. Even harmless edits need an explicit pin
update. Finite mutation images are declared separately and only touch fixture
resources; this gate is an experiment boundary, not a hostile-code sandbox.

No Python interpreter/helper edge is admitted. Thus Python signal/pidfd/exec/
subprocess forms, like arbitrary shell prefixes or dynamic dispatch, cannot
enter the operating closure. The pinned wrappers' caller-argv forwarding is the
one declared workload edge, supplied by the trusted fixture during these tests.
A new bypass class means STOP and escalate to o, not another guard patch.
"""
import hashlib
import json
from pathlib import Path

from liveness_guard import render_findings

CLOSURE = ('scripts/build-lock.sh', 'scripts/build-guarded.sh', 'scripts/lib/jv-project.sh')
# Read beside the trusted guard, NEVER from the candidate root under inspection.
POLICY = json.loads(Path(__file__).with_name('capacity_allowlist.json').read_text())
assert POLICY['schema'] == 1 and set(POLICY['programs']) == set(CLOSURE)


def runtime_findings(root):
    findings = []
    root = Path(root).absolute()
    for rel in CLOSURE:
        path = root / rel
        parts = (path, *[p for p in path.parents if p == root or root in p.parents])
        if any(p.is_symlink() for p in parts) or not path.is_file():
            findings.append({'file': rel, 'check': 'missing-or-alias'})
            continue
        try:
            body = path.read_bytes()
        except OSError:
            findings.append({'file': rel, 'check': 'unreadable'})
            continue
        permitted = {item['sha256'] for item in POLICY['programs'][rel]['images']}
        digest = hashlib.sha256(body).hexdigest()
        if digest not in permitted:
            findings.append({'file': rel, 'check': 'undeclared-executable-image'})
    return findings

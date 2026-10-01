"""W-C4 closed-world execution admission for the three reviewed shell programs.

The adjacent, committed allowlist pins COMPLETE program bytes, including each
command's arguments, substitutions, control flow and helper edges. Its readable
edge inventory explains those pins. With the reviewed guard and policy fixed,
unknown bytes refuse. Even harmless edits need an explicit reviewed pin update.
Finite mutation images are declared separately and only touch fixture resources.
This is an accident boundary for reviewed code, not an adversarial sandbox.

Authority is the committed guard plus adjacent policy, maintained through diff
review. Generated children load their own adjacent, candidate-supplied policy.
File or in-memory self-registration is outside this boundary; the 2026-10-01
narrow review's pidfd self-registration seed is an accepted limitation under
o's ruling 01M3WEG3R9Y9W6YR6MBWXF50Q8. See SPEC I7; no runtime isolation here.

No Python interpreter/helper edge is admitted. Thus Python signal/pidfd/exec/
subprocess forms, like arbitrary shell prefixes or dynamic dispatch, refuse
under the fixed reviewed policy. The wrappers' caller-argv forwarding is the
one declared workload edge, supplied by the trusted fixture during these tests.
A new bypass class means STOP and escalate to o, not another guard patch.
"""
import hashlib
import json
from pathlib import Path

from liveness_guard import render_findings

CLOSURE = ('scripts/build-lock.sh', 'scripts/build-guarded.sh', 'scripts/lib/jv-project.sh')
# Adjacent policy is reviewed authority; a generated child loads its own copy.
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

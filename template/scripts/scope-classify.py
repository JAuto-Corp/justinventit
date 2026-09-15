#!/usr/bin/env python3
"""Classify a change's scope from its changed paths and an authored config; never decide acceptance.

Usage:
  scope-classify.py [--config FILE] [--repo DIR] [--json] [--red-recorded REF] BASE..HEAD
  scope-classify.py [--config FILE] [--repo DIR --head REF] [--json] --paths-from FILE

Prints one line `class=<Quick|Quick(tooling)|Standard+> reason=<trace>` (plus JSON with --json).
Classes, decided by what the changed files do (TDD_GATE §2 "Scope classes"):
  Standard+       any authored trigger, the file-count threshold, or an executable-class file;
                  also any change that CLAIMS tooling but fails a tooling rule (the refusal is named)
  Quick(tooling)  every changed path is an inventoried helper/test pair (or the config plus the
                  pairs it newly lists, all added), nothing in the denylist, no symlink involved,
                  nothing outside the inventory references a changed path directly or through
                  other inventoried files (module spellings included), no product import, and
                  each changed helper's sibling test is added/modified in the same change (or
                  --red-recorded names the RED evidence the reviewer will check)
  Quick           everything else
v1 INVARIANT (bounded on purpose): Quick(tooling) is established only for what this engine can
PROVE. Anything ambiguous is Standard+ by rule, never resolved further: any deleted path; a
dynamic import (importlib, __import__); a relative import that does not resolve to an inventory
member; a bare import that resolves to a non-member sibling or repository module; ANY textual
reference to a changed path (path, basename, dotted module, `from pkg import`, `import pkg`) from a
non-prose file outside the inventory — refused without confirmation; a sibling in the changed path's
package whose imports cannot be resolved. The resolver is deliberately not a dependency analyzer.
Rule 5 of §2 — the PR declaration and the reviewer's attestation (no product command executed,
no product/shared state written) — is human work; the trace names what was checked mechanically.
--paths-from statuses are caller-supplied: the reviewer verifies them against the real diff.
Without a repository and --head, consumer/import/symlink checks cannot run and tooling is
refused as unverifiable (never reported as passed). Exit 0 when classified; exit 2 cannot-evaluate.
The config (default: scope-classes.json beside this script) is project-owned: its VALUES are the
project's; this engine and the rule order are the framework's.
INERT BY DEFAULT: the rendered config ships tooling.inventory = [] so Quick(tooling) cannot fire until
the project authors pairs. Known v1 limit: the consumer search is `git grep -I`, which honours binary
attributes; a textual reference in a file .gitattributes marks binary is not seen.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

STANDARD, TOOLING, QUICK = "Standard+", "Quick(tooling)", "Quick"
STATUS = {"A": "added", "D": "deleted", "M": "modified", "T": "modified"}


def refuse(message):
    raise ValueError(message)


def git(repo, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1")
    return subprocess.check_output(["git", "-c", "core.fsmonitor=false", "-c", "core.quotePath=false",
                                    "-C", str(repo), *args], env=env, stderr=subprocess.PIPE, timeout=60)


def parse_config(raw, where):
    try:
        cfg = json.loads(raw)
    except ValueError as exc:
        refuse("config is not JSON: %s (%s)" % (where, exc))
    if not isinstance(cfg, dict) or cfg.get("schema_version") != 1:
        refuse("config schema_version must be 1: " + where)

    def rx(value, name, flags=0):
        if not isinstance(value, str):
            refuse("%s must be a string pattern" % name)
        try:
            return re.compile(value, flags)
        except re.error as exc:
            refuse("bad pattern in %s: %s (%s)" % (name, value, exc))

    for key, kind in (("standard_triggers", list), ("executable_class", dict), ("tooling", dict), ("file_count_threshold", int)):
        if not isinstance(cfg.get(key), kind) or isinstance(cfg.get(key), bool):
            refuse("config.%s must be a %s" % (key, kind.__name__))
    if cfg["file_count_threshold"] < 1:
        refuse("config.file_count_threshold must be >= 1")
    triggers = []
    for i, t in enumerate(cfg["standard_triggers"]):
        if not isinstance(t, dict) or not isinstance(t.get("name"), str) or not t.get("name") or not isinstance(t.get("pattern"), str):
            refuse("standard_triggers[%d] needs string name and pattern" % i)
        if t.get("status", "any") not in ("any", "added", "modified", "deleted"):
            refuse("standard_triggers[%d].status must be any|added|modified|deleted" % i)
        triggers.append((t["name"], rx(t["pattern"], "standard_triggers." + t["name"]), t.get("status", "any")))
    ex, tooling = cfg["executable_class"], cfg["tooling"]
    if not isinstance(ex.get("pattern"), str):
        refuse("config.executable_class.pattern must be a string")
    inventory = []
    if not isinstance(tooling.get("inventory", []), list):
        refuse("tooling.inventory must be a list")
    for i, pair in enumerate(tooling.get("inventory", [])):
        if not isinstance(pair, dict) or not isinstance(pair.get("helper"), str) or not isinstance(pair.get("test"), str):
            refuse("tooling.inventory[%d] needs string helper and test" % i)
        inventory.append((pair["helper"], pair["test"]))
    roots = tooling.get("consumer_roots", [])
    if not isinstance(roots, list) or not all(isinstance(r, str) and r for r in roots):
        refuse("tooling.consumer_roots must be a list of pathspecs")
    pats = tooling.get("product_import_patterns", [])
    if not isinstance(pats, list) or not all(isinstance(x, str) for x in pats):
        refuse("tooling.product_import_patterns must be a list of string patterns")
    if not isinstance(tooling.get("config_path", "scripts/scope-classes.json"), str):
        refuse("tooling.config_path must be a string")
    return {
        "triggers": triggers,
        "threshold": cfg["file_count_threshold"],
        "exec": rx(ex["pattern"], "executable_class.pattern"),
        "exec_exclude": rx(ex.get("exclude_pattern", "\\.md$"), "executable_class.exclude_pattern"),
        "denylist": rx(tooling.get("denylist", "$^"), "tooling.denylist"),
        "inventory": inventory,
        "config_path": tooling.get("config_path", "scripts/scope-classes.json"),
        "consumer_roots": roots,
        "import_patterns": [rx(p, "tooling.product_import_patterns", re.M) for p in pats],
    }


def load_config(path):
    try:
        raw = Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        refuse("config unreadable: %s (%s)" % (path, exc))
    return parse_config(raw, str(path))


def resolve(repo, ref):
    try:
        return git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode("ascii").strip()
    except subprocess.CalledProcessError:
        refuse("unresolved revision: " + ref)


def changed_from_git(repo, rng):
    if ".." in rng:
        base, head = rng.split("..", 1)
    else:
        parts = rng.split()
        if len(parts) != 2:
            refuse("range must be BASE..HEAD or 'BASE HEAD'")
        base, head = parts
    base, head = resolve(repo, base), resolve(repo, head)
    fields = git(repo, "diff", "--name-status", "-z", "--no-renames", base, head).split(b"\0")
    changed = {}
    i = 0
    while i + 1 < len(fields) and fields[i]:
        status = fields[i].decode("ascii")[:1]
        changed[os.fsdecode(fields[i + 1])] = STATUS.get(status, "modified")
        i += 2
    return changed, base, head


def changed_from_file(path):
    changed = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 1:
            changed[parts[0]] = "modified"
        elif parts[0][:1] in ("R", "C") and len(parts) == 3:
            if parts[0][:1] == "R":
                changed[parts[1]] = "deleted"
            changed[parts[2]] = "added"
        elif len(parts) == 2:
            changed[parts[1]] = STATUS.get(parts[0].strip()[:1], "modified")
        else:
            refuse("unparseable --paths-from line: " + repr(line))
    return changed


def blob(repo, rev, path):
    try:
        return git(repo, "show", "%s:%s" % (rev, path)).decode("utf-8", "replace")
    except subprocess.CalledProcessError:
        return None


PY_IMPORT = re.compile(r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+([^\n#]+)|import\s+([\w.]+))", re.M)
JS_IMPORT = re.compile(r"(?:\bfrom\s+|\bimport\s+|\brequire\(\s*)['\"]([^'\"]+)['\"]")
JS_EXT = ("", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", "/index.js", "/index.ts", "/index.mjs", "/__init__.py")


def tree_at(repo, rev):
    """All paths at REV (files only) and the set of top-level names (directories, files, file stems)."""
    files = set()
    for record in git(repo, "ls-tree", "-r", "-z", "--name-only", rev).split(b"\0"):
        if record:
            files.add(os.fsdecode(record))
    top = set()
    for f in files:
        head = f.split("/", 1)[0]
        top.add(head)
        if "/" not in f:
            top.add(Path(f).stem)
    return files, top


def resolve_import(spec, importer, files, top_names):
    """Return the repository path an import statement resolves to, or None when it is external."""
    if spec.startswith("."):                      # relative (python dots or JS ./ ../)
        if spec.startswith("./") or spec.startswith("../"):
            target = os.path.normpath(os.path.join(os.path.dirname(importer), spec))
        else:
            dots = len(spec) - len(spec.lstrip("."))
            base = Path(importer).parent
            for _ in range(dots - 1):
                base = base.parent
            rest = spec.lstrip(".").replace(".", "/")
            target = os.path.normpath(str(base / rest)) if rest else str(base)
    elif "/" in spec:                             # JS bare path into the repo, e.g. 'src/x' or '@/x'
        head = spec.split("/", 1)[0]
        target = spec if head in top_names else None
        if target is None:
            return None
    else:                                         # dotted python module or bare JS package
        root = spec.split(".", 1)[0]
        sibling = os.path.normpath(os.path.join(os.path.dirname(importer), spec.replace(".", "/")))
        for ext in (".py", "/__init__.py"):       # a script's own directory is on sys.path when it runs
            if sibling + ext in files:
                return sibling + ext
        if root not in top_names:
            return None
        target = spec.replace(".", "/")
    if target.startswith("../") or target == "..":
        return None
    for ext in JS_EXT:
        cand = os.path.normpath(target + ext) if ext else os.path.normpath(target)
        if cand in files:
            return cand
    prefix = os.path.normpath(target) + "/"
    if any(f.startswith(prefix) for f in files):   # a package/directory inside the repository
        return prefix
    return None


def import_specs(path, content):
    """(spec, names) pairs for every import statement; Python via ast (regex fallback), JS via regex."""
    specs = []
    if path.endswith((".py", ".pyi")):
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    specs.extend((a.name, []) for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    specs.append(("." * node.level + (node.module or ""), [a.name for a in node.names]))
            return specs
    for m in PY_IMPORT.finditer(content):
        if m.group(3) is not None:
            specs.extend((x.strip().split(" as ")[0].strip(), []) for x in m.group(3).split(","))
        else:
            names = [n.strip().split(" as ")[0].strip() for n in m.group(2).strip().strip("()").split(",")]
            specs.append((m.group(1), [n for n in names if n]))
    for m in JS_IMPORT.finditer(content):
        specs.append((m.group(1), []))
    return specs


DYNAMIC_IMPORT = re.compile(r"\b(importlib\b|__import__\s*\()")


def resolved_imports(path, content, files, top_names):
    """({target: spec}, ambiguous) — repository targets PATH's imports resolve to, and whether any import
    could not be settled (dynamic import, or a relative import that resolves to nothing)."""
    targets, ambiguous = {}, bool(DYNAMIC_IMPORT.search(content))
    for spec, names in import_specs(path, content):
        if not spec and not names:
            continue
        resolved_any = False
        for name in names:
            if name == "*":
                continue
            full = spec + ("" if spec.endswith(".") or not spec else ".") + name
            t = resolve_import(full, path, files, top_names)
            if t:
                resolved_any = True
                targets.setdefault(t, full)
        if not resolved_any and spec:
            if names and spec.startswith("."):        # relative names that resolve to nothing: unprovable
                ambiguous = True
                continue
            t = resolve_import(spec, path, files, top_names)
            if t:
                targets.setdefault(t, spec)
            elif spec.startswith("."):
                ambiguous = True
    return targets, ambiguous


def repo_imports(repo, head, path, content, members, files, top_names):
    """(spec, target) for imports resolving outside MEMBERS (own directory excluded); ('<ambiguous>', reason) when unprovable."""
    own = os.path.dirname(path) + "/"
    found, ambiguous = resolved_imports(path, content, files, top_names)
    hits = sorted((found[t], t) for t in found if t not in members and t != path and t != own)
    if ambiguous:
        hits.append(("<ambiguous>", "dynamic-or-unresolved-relative-import"))
    return hits


PARSEABLE = (".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")


def symlinks_at(repo, rev):
    out = {}
    for record in git(repo, "ls-tree", "-r", "-z", rev).split(b"\0"):
        if record:
            meta, name = record.split(b"\t", 1)
            if meta.split()[0] == b"120000":
                out[os.fsdecode(name)] = blob(repo, rev, os.fsdecode(name)) or ""
    return out


def needles(path):
    p = Path(path)
    stem = p.stem
    out = {path, p.name}
    no_ext = path[: -len(p.suffix)] if p.suffix else path
    if "/" in no_ext:                            # module spellings: scripts.helper, from scripts import …, import scripts
        dotted = no_ext.replace("/", ".")
        for d in {dotted, dotted.replace("-", "_")}:
            out.add(d)
            pkg = d.rpartition(".")[0]
            out.add("from %s import" % pkg)
            out.add("import %s" % pkg)
    return sorted(n for n in out if len(n) >= 3)


def grep_consumers(repo, rev, paths, cfg, exclude):
    """Files under consumer_roots at REV that mention any of PATHS (any spelling), minus EXCLUDE."""
    if not cfg["consumer_roots"]:
        return {}
    args = ["grep", "-z", "-l", "-I", "--fixed-strings"]
    for p in paths:
        for n in needles(p):
            args += ["-e", n]
    args += [rev, "--"] + cfg["consumer_roots"]
    try:
        out = git(repo, *args)
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1:
            return {}
        raise
    hits = {}
    for rec in out.split(b"\0"):
        if not rec:
            continue
        f = os.fsdecode(rec)
        f = f.split(":", 1)[1] if f.startswith(rev + ":") else f
        if f not in exclude:
            hits[f] = True
    return hits


def tooling_trace(changed, cfg, repo, base, head, red_recorded):
    paths = sorted(changed)
    out = {"ok": False, "refused": None, "trace": []}
    denied = [p for p in paths if cfg["denylist"].search(p)]
    if denied:
        out["refused"] = "denylist:" + ",".join(denied)
        return out
    if repo is None or head is None:
        out["refused"] = "unverifiable:no-repository-head (consumer, import and symlink checks need --repo and --head)"
        return out
    deleted = [p for p in paths if changed[p] == "deleted"]
    if deleted:                                   # v1 invariant: a deletion is never tooling
        out["refused"] = "deletion-not-tooling:" + ",".join(deleted)
        return out
    helpers = dict(cfg["inventory"])
    tests = {t: h for h, t in cfg["inventory"]}
    # Config edits: allowed only as pure inventory additions/removals whose files are added/deleted here.
    new_pairs = []
    if cfg["config_path"] in paths:
        if base is None:
            out["refused"] = "config-changed:unverifiable-without-base"
            return out
        old_raw, new_raw = blob(repo, base, cfg["config_path"]), blob(repo, head, cfg["config_path"])
        if old_raw is None or new_raw is None:
            out["refused"] = "config-changed:added-or-deleted"
            return out
        try:
            old_parsed, new_parsed = parse_config(old_raw, "BASE:" + cfg["config_path"]), parse_config(new_raw, "HEAD:" + cfg["config_path"])
            old_cfg, new_cfg = json.loads(old_raw), json.loads(new_raw)
        except ValueError as exc:
            out["refused"] = "config-changed:invalid:" + str(exc)
            return out
        old_inv, new_inv = old_parsed["inventory"], new_parsed["inventory"]
        strip = lambda c: json.dumps({**c, "tooling": {**c["tooling"], "inventory": None}}, sort_keys=True)
        if strip(old_cfg) != strip(new_cfg):
            out["refused"] = "config-changed:beyond-inventory"
            return out
        new_pairs = [p for p in new_inv if p not in old_inv]
        if [p for p in old_inv if p not in new_inv]:
            out["refused"] = "config-changed:inventory-removal-not-tooling"
            return out
        for h, t in new_pairs:
            if changed.get(h) != "added" or changed.get(t) != "added":
                out["refused"] = "config-changed:new-pair-files-not-added:%s" % h
                return out
    known = set(helpers) | set(tests) | {cfg["config_path"]}
    unknown = [p for p in paths if p not in known]
    if unknown:
        out["refused"] = "not-in-inventory:" + ",".join(unknown)
        return out
    out["trace"].append("inventory:new-pair(%s)" % ",".join(h for h, _ in new_pairs) if new_pairs else "inventory:%d/%d" % (len(paths), len(paths)))
    # Symlinks anywhere in the story are refused: changed paths, inventory members, or links naming them.
    links = symlinks_at(repo, head)
    for p in paths:
        if p in links:
            out["refused"] = "symlink:" + p
            return out
    for member in sorted(set(helpers) | set(tests)):
        if member in links:
            out["refused"] = "symlink-inventory-member:" + member
            return out
    # Consumers: transitive through inventoried files (text references AND symlinks naming them);
    # anything outside the inventory refuses. Candidates = grep hits over the consumer roots plus every
    # parseable file in a changed path's own directory tree (relative imports name nothing greppable).
    # A deleted path is resolved against the BASE tree, where it still existed.
    files, top_names = tree_at(repo, head)
    exclude = set(paths) | {cfg["config_path"]}
    frontier, seen = list(paths), set(paths)
    while frontier:
        nxt = []
        for p in frontier:
            for link, target in sorted(links.items()):
                if link not in seen and any(n in target for n in needles(p)):
                    out["refused"] = "symlink-consumer:%s->%s" % (link, target)
                    return out
            pkg_prefix = os.path.dirname(p) + "/" if os.path.dirname(p) else ""
            grep_hits = set(grep_consumers(repo, head, [p], cfg, exclude | seen))
            siblings = {f for f in files if pkg_prefix and f.startswith(pkg_prefix) and f.endswith(PARSEABLE) and f not in (exclude | seen)}
            for f in sorted(grep_hits | siblings):
                if f in helpers or f in tests:
                    if f not in seen:
                        seen.add(f)
                        nxt.append(f)
                    continue
                if f not in grep_hits:                        # sibling with no textual reference: only a relative
                    content = blob(repo, head, f) or ""       # import (or an unprovable one) can reach the path
                    targets, ambiguous = resolved_imports(f, content, files, top_names)
                    if p not in targets and pkg_prefix not in targets and not ambiguous:
                        continue
                # v1 invariant: any textual reference from outside the inventory refuses — no confirmation step.
                out["refused"] = "consumer:%s<-%s" % (p, f)
                return out
        frontier = nxt
    out["trace"].append("consumers:none")
    members = set(helpers) | set(tests) | {cfg["config_path"]}
    for p in paths:
        if changed[p] == "deleted":
            continue
        content = blob(repo, head, p) or ""
        for spec, target in repo_imports(repo, head, p, content, members, files, top_names):
            out["refused"] = "product-import:%s:%s->%s" % (p, spec[:40], target)
            return out
        for pat in cfg["import_patterns"]:
            m = pat.search(content)
            if m:
                out["refused"] = "product-import:%s:%s" % (p, m.group(0).strip()[:40])
                return out
    out["trace"].append("product-import:none")
    evidence = []
    for h, t in helpers.items():
        hs, ts = changed.get(h), changed.get(t)
        if hs is None and ts is None:
            continue
        if hs is None:
            evidence.append("test-only:" + t)
        elif ts in ("added", "modified"):
            evidence.append("test-in-change:" + h)
        elif red_recorded:
            evidence.append("red-recorded:%s(%s)" % (h, red_recorded))
        else:
            out["refused"] = "test-not-in-change:" + h
            return out
    out["trace"].append("test-in-change" if all(e.startswith("test-in-change:") for e in evidence) and evidence else ";".join(evidence))
    out["ok"] = True
    return out


def classify(changed, cfg, repo=None, base=None, head=None, red_recorded=None):
    paths = sorted(changed)
    trace = {"class": None, "reasons": [], "paths": paths, "tooling": None}
    if not paths:
        trace["class"], trace["reasons"] = QUICK, ["no-changes"]
        return trace
    reasons = []
    for name, pattern, status in cfg["triggers"]:
        if any(pattern.search(p) and (status == "any" or changed[p] == status) for p in paths):
            reasons.append(name)
    executable = [p for p in paths if cfg["exec"].search(p) and not cfg["exec_exclude"].search(p)]
    if executable:
        reasons.append("executable-class")
    if len(paths) >= cfg["threshold"]:
        reasons.append("files-%d" % len(paths))
    members = {h for h, _ in cfg["inventory"]} | {t for _, t in cfg["inventory"]} | {cfg["config_path"]}
    # Tooling is evaluated when nothing but the executable class objects, and either an executable
    # file or an inventory member is involved — so a stray scripts/ file gets a named refusal.
    claims_tooling = reasons in ([], ["executable-class"]) and (bool(executable) or any(p in members for p in paths))
    if claims_tooling:
        t = tooling_trace(changed, cfg, repo, base, head, red_recorded)
        trace["tooling"] = t
        if t["ok"]:
            trace["class"], trace["reasons"] = TOOLING, t["trace"]
            return trace
        reasons.append("tooling-refused:" + t["refused"])
    if reasons:
        trace["class"], trace["reasons"] = STANDARD, reasons
    else:
        trace["class"], trace["reasons"] = QUICK, ["quick-by-heuristic"]
    return trace


def one_line(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("range", nargs="?", help="BASE..HEAD (git)")
    parser.add_argument("--paths-from", type=Path, help="file of changed paths (optional 'A\\tpath' / 'R100\\told\\tnew' prefixes); statuses are caller-supplied")
    parser.add_argument("--head", help="with --paths-from: the revision to run consumer/import/symlink checks against")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().with_name("scope-classes.json"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--red-recorded", metavar="REF", help="RED evidence reference for a helper whose test is unchanged (reviewer-verified)")
    args = parser.parse_args()
    try:
        cfg = load_config(args.config)
        base = None
        if args.paths_from:
            changed = changed_from_file(args.paths_from)
            repo, head = (args.repo, resolve(args.repo, args.head)) if args.head else (None, None)
        elif args.range:
            changed, base, head = changed_from_git(args.repo, args.range)
            repo = args.repo
        else:
            refuse("give BASE..HEAD or --paths-from FILE")
        trace = classify(changed, cfg, repo, base, head, args.red_recorded)
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError) as exc:
        detail = exc.stderr.decode("utf-8", "replace").strip() if getattr(exc, "stderr", None) else str(exc)
        print("CANNOT-EVALUATE", one_line(detail))
        return 2
    print("class=%s reason=%s" % (trace["class"], ",".join(one_line(r) for r in trace["reasons"])))
    if args.json:
        print(json.dumps(trace, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

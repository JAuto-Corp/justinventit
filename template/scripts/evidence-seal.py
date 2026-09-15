#!/usr/bin/env python3
"""Regenerate or verify a packet's SHA256SUMS; never append, edit or decide acceptance.

seal <dir> [--reseal]   regenerate SHA256SUMS from the directory (coreutils format,
                        canonical relative POSIX paths, byte order, atomic replace).
                        Refuses when an existing manifest no longer verifies unless
                        --reseal, which prints the entry-level delta before writing.
                        Prints the manifest digest and, inside a repository, the commit
                        HEAD (rev-parse only: no status, diff or content filters ever run).
verify <dir>            exit 0 every listed entry matches and nothing is unlisted;
                        exit 1 an entry CHANGED or is MISSING (each named);
                        exit 3 only UNLISTED files exist (each named);
                        exit 2 cannot evaluate (unreadable tree, malformed manifest,
                        undeclared symlink or special file, empty packet, unsealable name).
Exclusions are declared in <dir>/.sealignore (one relative path prefix per line,
'#' comments). The ignore file is always sealed and can never exclude itself.
A packet containing .git must declare it. The filesystem root is refused.
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

MANIFEST = "SHA256SUMS"
IGNORE = ".sealignore"
HEX = frozenset("0123456789abcdef")
UNSEALABLE = ("\n", "\r", "\\")
GIT_SELECTORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")


def canonical(rel):
    parts = rel.split("/")
    return (rel and rel != "-" and not rel.endswith("/") and not any(c in rel for c in UNSEALABLE)
            and all(p not in ("", ".", "..") for p in parts) and rel.isprintable())


def refuse(message):
    raise ValueError(message)


def ignores(root):
    path = root / IGNORE
    if path.is_symlink():
        refuse("symlink refused: " + IGNORE)
    if not path.exists():
        return []
    if not path.is_file():
        refuse("unsupported file type refused: " + IGNORE)
    rules = [line.strip(" \t").rstrip("/") for line in path.read_bytes().decode("utf-8").split("\n")]
    rules = [r for r in rules if r and not r.startswith("#") and r != IGNORE]
    for rule in rules:
        if not canonical(rule):
            refuse("non-canonical rule in " + IGNORE + ": " + repr(rule))
    return rules


def ignored(rel, rules):
    return rel != IGNORE and any(rel == r or rel.startswith(r + "/") for r in rules)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files(root):
    rules = ignores(root)
    if (root / ".git").exists() and not ignored(".git", rules):
        refuse("packet contains .git; declare '.git/' in " + IGNORE + " or seal a packet directory")
    out = {}

    def onerror(exc):
        raise exc

    for base, dirs, names in os.walk(root, onerror=onerror, followlinks=False):
        rel_base = Path(base).relative_to(root).as_posix()
        prefix = "" if rel_base == "." else rel_base + "/"
        # Declared exclusions are skipped before anything else is judged, so an ignored
        # symlink or subtree never blocks the seal; an undeclared symlink always does.
        dirs[:] = sorted(d for d in dirs if not ignored(prefix + d, rules))
        for name in dirs + sorted(names):
            rel = prefix + name
            path = Path(base) / name
            if rel == MANIFEST or ignored(rel, rules):
                continue
            if path.is_symlink():
                refuse("symlink refused: " + rel)
            if name in names:
                if not canonical(rel):
                    refuse("unsealable name (newline, CR, backslash, unprintable or '-'): " + repr(rel))
                if not path.is_file():
                    refuse("unsupported file type refused (declare it or remove it): " + rel)
                out[rel] = digest(path)
    return out


def parse(root):
    entries = {}
    for n, line in enumerate((root / MANIFEST).read_bytes().decode("utf-8").split("\n"), 1):
        if not line:
            continue
        hexd, sep, rel = line.partition("  ")
        if sep != "  " or len(hexd) != 64 or not HEX.issuperset(hexd) or rel.startswith("/") \
                or not canonical(rel) or rel in entries:
            refuse("%s:%d malformed or non-canonical entry" % (MANIFEST, n))
        entries[rel] = hexd
    if not entries:
        refuse(MANIFEST + " is empty")
    return entries


def render(entries):
    return "".join("%s  %s\n" % (entries[rel], rel) for rel in sorted(entries, key=str.encode))


def compare(listed, actual):
    changed = sorted(r for r in listed if r in actual and actual[r] != listed[r])
    missing = sorted(r for r in listed if r not in actual)
    unlisted = sorted(r for r in actual if r not in listed)
    return changed, missing, unlisted


def git_head(root):
    """Commit HEAD via rev-parse only: status/diff would run repository content filters."""
    if any(key in os.environ for key in GIT_SELECTORS):
        return "none"
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1",
               GIT_NO_REPLACE_OBJECTS="1", GIT_ALLOW_PROTOCOL="")
    cmd = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(root)]
    try:
        head = subprocess.check_output(cmd + ["rev-parse", "--verify", "HEAD"], env=env,
                                       stderr=subprocess.DEVNULL, timeout=20).decode("ascii").strip()
        return head if len(head) in (40, 64) and HEX.issuperset(head) else "none"
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return "none"


def verify(root):
    listed = parse(root)
    changed, missing, unlisted = compare(listed, files(root))
    for rel in changed:
        print("CHANGED", rel)
    for rel in missing:
        print("MISSING", rel)
    for rel in unlisted:
        print("UNLISTED", rel)
    if changed or missing:
        return 1
    if unlisted:
        return 3
    print("OK entries=%d" % len(listed))
    return 0


def seal(root, reseal):
    actual = files(root)
    if not actual:
        refuse("empty packet: nothing to seal")
    if (root / MANIFEST).exists():
        changed, missing, unlisted = compare(parse(root), actual)
        if changed or missing or unlisted:
            if not reseal:
                print("REFUSED existing manifest no longer verifies (changed=%d missing=%d unlisted=%d); "
                      "rerun with --reseal to regenerate and print the delta"
                      % (len(changed), len(missing), len(unlisted)))
                return 1
            for rel in changed:
                print("DELTA changed", rel)
            for rel in missing:
                print("DELTA removed", rel)
            for rel in unlisted:
                print("DELTA added", rel)
    text = render(actual)
    fd, tmp = tempfile.mkstemp(prefix="." + MANIFEST + ".", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, root / MANIFEST)
    except BaseException:
        os.unlink(tmp)
        raise
    print("SEALED entries=%d manifest_sha256=%s git_head=%s"
          % (len(actual), hashlib.sha256(text.encode("utf-8")).hexdigest(), git_head(root)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("seal")
    s.add_argument("dir", type=Path)
    s.add_argument("--reseal", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("dir", type=Path)
    args = parser.parse_args()
    try:
        root = args.dir.resolve(strict=True)
        if not root.is_dir():
            refuse("not a directory: " + str(args.dir))
        if root == Path(root.anchor):
            refuse("filesystem root refused")
        manifest = root / MANIFEST
        if manifest.is_symlink():
            refuse("symlink refused: " + MANIFEST)
        if manifest.exists() and not manifest.is_file():
            refuse("unsupported file type refused: " + MANIFEST)
        if args.verb == "verify" and not manifest.exists():
            refuse("no " + MANIFEST + " in " + str(args.dir))
        return seal(root, args.reseal) if args.verb == "seal" else verify(root)
    except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
        print("CANNOT-EVALUATE", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())

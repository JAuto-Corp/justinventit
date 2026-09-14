#!/usr/bin/env python3
"""Report changed committed inputs; never decide acceptance or authorization."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def git(repo, *args):
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1",
               GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_ALLOW_PROTOCOL="")
    # No diff/status (which can run content filters), optional writes, or fetches.
    return subprocess.check_output(
        ["git", "-c", "core.fsmonitor=false", "-C", str(repo), *args],
        env=env, stderr=subprocess.PIPE, timeout=20)


def tree(repo, revision):
    commit = git(repo, "rev-parse", "--verify", "--end-of-options",
                 revision + "^{commit}").decode("ascii").strip()
    entries = {}
    for record in git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if record:
            meta, name = record.split(b"\t", 1)
            mode, kind, oid = meta.decode("ascii").split()
            entries[os.fsdecode(name)] = {"mode": mode, "type": kind, "object": oid}
    return commit, entries


def compare(repo, before, after, inputs):
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_NAMESPACE", "GIT_SHALLOW_FILE"):
        if key in os.environ:
            raise ValueError("Repository selection is ambiguous; unset " + key + " before comparing.")
    old_commit, old = tree(repo, before)
    new_commit, new = tree(repo, after)
    names = set(old) | set(new)
    inputs = sorted(set(inputs))
    selected = set()
    for path in inputs:
        if not path or path.startswith("/") or any(p in ("", ".", "..") for p in path.split("/")):
            raise ValueError("Inputs must be literal repository-relative files/directories: " + path)
        matches = {name for name in names if name == path or name.startswith(path + "/")}
        if not matches:
            raise ValueError("Input is absent from both committed trees: " + path)
        selected.update(matches)
    if not inputs:
        selected = names
    for name in sorted(selected):
        for entry in (old.get(name), new.get(name)):
            if entry and entry["mode"] not in ("100644", "100755"):
                raise ValueError("Selected symlink/submodule or unsupported file mode: " + name)
    changes = [{"path": name, "before": old.get(name), "after": new.get(name)}
               for name in sorted(names) if old.get(name) != new.get(name)]
    input_changes = [change for change in changes if change["path"] in selected]
    return {
        "repository_git_dir": os.fsdecode(git(repo, "rev-parse", "--absolute-git-dir")).removesuffix("\n"),
        "before": old_commit,
        "after": new_commit,
        "scope": "explicit_inputs" if inputs else "whole_tree",
        "inputs": inputs,
        "assessment": "committed_inputs_changed" if input_changes else "committed_inputs_unchanged",
        "all_changes": changes,
        "input_changes": input_changes,
        "worktree_has_changes": None,
        "worktree_state": "not_inspected",
        "limits": [
            "Committed tree identities only; no new test run, acceptance or authorization.",
            "Blob identity does not establish tested checkout bytes (attributes, filters, EOL or LFS).",
            "Input completeness and evidence applicability require the existing lead's decision.",
            "Staged, unstaged, untracked, ignored and external inputs are not inspected.",
            "Runtime, submodule worktrees and material findings are not verified.",
            "Live resource/target checks, mandatory audits and exact-head integration gates still apply.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", help="local Git revision carrying the earlier evidence")
    parser.add_argument("after", help="local Git revision to compare")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--input", action="append", default=[], help="literal tracked file or directory; repeatable")
    args = parser.parse_args()
    try:
        result = compare(args.repo, args.before, args.after, args.input)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else "Requested local Git data is unavailable."
        print(json.dumps({"error": message, "assessment": "unavailable"}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

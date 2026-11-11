#!/usr/bin/env python3
"""Encoding gate: every tracked text file is UTF-8, decodable and BOM-free.

`AGENTS.md` requires "UTF-8 without BOM" for all sources and documents, but
nothing enforced it.  This is the gate used by `.github/workflows/verify.yml`;
it uses the standard library only, needs no network, and checks the files git
tracks (so `__pycache__`, `.pytest_cache` and `.ruff_cache` cannot make it
pass or fail by accident).

Checks per file:

  * no UTF-8 BOM  (`EF BB BF` at offset 0);
  * no UTF-16/32 BOM (`FF FE` / `FE FF`), which would also not decode as UTF-8;
  * strict UTF-8 decode of the whole byte string;
  * no NUL byte outside the known-binary suffix list.

Usage:
    python tools/check_repo_encoding.py
    python tools/check_repo_encoding.py --verbose

Exit codes: 0 = every checked file is clean; 1 = at least one problem.
"""

import argparse
import os
import subprocess
import sys

BOM_UTF8 = b"\xef\xbb\xbf"
BOM_UTF16_LE = b"\xff\xfe"
BOM_UTF16_BE = b"\xfe\xff"

# Files that are legitimately binary.  None are tracked today; the list keeps a
# future paper PDF or screenshot from turning this gate into noise.
BINARY_SUFFIXES = (
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".zip", ".gz", ".bz2", ".xz", ".7z", ".whl",
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".olean",
)

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}


def tracked_files(root):
    """Return repo-relative paths of tracked files, or a filesystem walk."""
    try:
        result = subprocess.run(
            ["git", "-C", root, "ls-files", "-z"],
            capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return walked_files(root)
    names = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    return sorted(names)


def walked_files(root):
    found = []
    for parent, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in names:
            full = os.path.join(parent, name)
            found.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(found)


def check_file(root, rel):
    """Return a list of problems for one file (empty when clean)."""
    if rel.lower().endswith(BINARY_SUFFIXES):
        return []
    path = os.path.join(root, rel.replace("/", os.sep))
    with open(path, "rb") as handle:
        blob = handle.read()
    problems = []
    if blob.startswith(BOM_UTF8):
        problems.append("UTF-8 BOM at offset 0 (must be BOM-free)")
    if blob.startswith(BOM_UTF16_LE) or blob.startswith(BOM_UTF16_BE):
        problems.append("UTF-16/32 BOM at offset 0 (not UTF-8)")
    if b"\0" in blob:
        problems.append("NUL byte in a text file")
    try:
        blob.decode("utf-8")
    except UnicodeDecodeError as error:
        problems.append("not valid UTF-8: %s" % error)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--verbose", action="store_true",
                        help="print every checked path, not just the failures")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    files = tracked_files(root)
    if not files:
        print("encoding: no files found under %s" % root, file=sys.stderr)
        return 1

    failures = []
    for rel in files:
        problems = check_file(root, rel)
        if problems:
            failures.append((rel, problems))
        elif args.verbose:
            print("ok   %s" % rel)

    checked = len(files)
    print("encoding: %d file(s) checked, %d UTF-8 without BOM, %d problem(s)"
          % (checked, checked - len(failures), len(failures)))
    for rel, problems in failures:
        for problem in problems:
            print("FAIL %s: %s" % (rel, problem), file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

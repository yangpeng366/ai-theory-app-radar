#!/usr/bin/env python3
"""Fetch the family-378 (ETH disproof) review set from openai/math without cloning the repo.

The upstream repository is ~900 MB and the full Lean tree is tens of thousands of
files.  A statement-level review needs neither: every file below is required to
decide whether the formalised bound matches the manuscript, and the whole set
is ~1.7 MB.

Files are fetched per channel, in order of preference:

  1. cdn.jsdelivr.net/gh/openai/math@main/<path>   (fast, refuses > 20 MB)
  2. raw.githubusercontent.com/openai/math/main/<path>   (authoritative, flaky)
  3. api.github.com/repos/openai/math/git/blobs/<sha>  (base64 fallback)

Usage:
    python3 fetch-sources.py --out ./family378-sources
    python3 fetch-sources.py --out ./family378-sources --no-paper   # skip the PDF
    python3 fetch-sources.py --out ./f378 --no-include-imports      # seed list only

FILES is a statement-level list: it names the files a reviewer must read, not a
set that compiles.  By default the script therefore keeps the set but closes it
under `import OAI.*` (--include-imports, capped by --max-modules), so the same
run produces a tree whose OAI imports resolve inside the fetched subset.

It writes a `_manifest.json` next to the fetched tree with the sha256 of every
fetched file, and a `_closure.json` describing how the import walk ended, so
the review can be re-run against a pinned copy.

Exit codes: 0 = every fetch succeeded and the closure is complete;
1 = at least one fetch failed (partial closure, or partial seed list);
2 = the import walk was cut short by --max-modules.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

REPO = "openai/math"
REF = "main"
CDN = "https://cdn.jsdelivr.net/gh/{repo}@{ref}/".format(repo=REPO, ref=REF)
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/".format(repo=REPO, ref=REF)
API = "https://api.github.com/repos/{repo}".format(repo=REPO)

# (remote path, local path relative to --out)
FILES = [
    ("CONTENTS.md", "CONTENTS.md"),
    ("history.md", "history.md"),
    ("lean/lean-toolchain", "lean/lean-toolchain"),
    ("lean/formalization.yaml", "lean/formalization.yaml"),
    ("lean/docs/378.md", "lean/docs/378.md"),
    ("lean/ComparatorChallenges/SubexponentialSAT.lean",
     "lean/ComparatorChallenges/SubexponentialSAT.lean"),
    ("lean/ComparatorChallenges/SubexponentialSAT.json",
     "lean/ComparatorChallenges/SubexponentialSAT.json"),
    ("lean/OAI/Algorithms/SubexponentialSAT/Main.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/Main.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SAT.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SAT.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/Encoding.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/Encoding.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/Computation.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/Computation.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/BinaryArithmetic.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/BinaryArithmetic.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SqrtLog/StatementScale.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SqrtLog/StatementScale.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SqrtLog/StatementCanonical.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SqrtLog/StatementCanonical.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Statement.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Statement.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Asymptotics.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Asymptotics.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/EncodingBounds.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/EncodingBounds.lean"),
    ("lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Final.lean",
     "lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Final.lean"),
]

PAPER = ("preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf",
         "preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf")


def _get(url, timeout=240, tries=4):
    last = None
    for index in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ai-theory-app-radar"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001 - network errors are expected here
            last = error
            time.sleep(1.5 * (index + 1))
    raise last


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_one(remote, local, out_dir, timeout=240, tries=4):
    target = os.path.join(out_dir, local.replace("/", os.sep))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    quoted = urllib.parse.quote(remote)
    errors = []
    for channel, url in (("jsdelivr", CDN + quoted), ("raw", RAW + quoted)):
        try:
            blob = _get(url, timeout=timeout, tries=tries)
            with open(target, "wb") as handle:
                handle.write(blob)
            return {"remote": remote, "local": local, "bytes": len(blob),
                    "sha256": sha256_of(target), "channel": channel}
        except Exception as error:  # noqa: BLE001
            errors.append("%s: %s" % (channel, str(error)[:120]))
    return {"remote": remote, "local": local, "bytes": None,
            "sha256": None, "channel": None, "errors": errors}


DEFAULT_MAX_MODULES = 400

# Lean accepts `import A B`, `public import A`, `meta import A` and
# `import all A`; all four forms bind modules that the closure needs.
IMPORT_RE = re.compile(r"^[ \t]*(?:(?:public|private|meta)[ \t]+)*import[ \t]+(.+?)[ \t]*$", re.M)
BLOCK_COMMENT_RE = re.compile(r"/-.*?-/", re.S)
MODULE_NAME_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.]*")


def parse_imports(text):
    """Return every module name bound by an ``import`` line in Lean source."""
    text = BLOCK_COMMENT_RE.sub(" ", text)
    modules = []
    for body in IMPORT_RE.findall(text):
        body = body.split("--", 1)[0]
        for token in body.split():
            if token == "all":
                continue
            if MODULE_NAME_RE.fullmatch(token):
                modules.append(token)
    return modules


def lean_modules(out_dir):
    """Map every fetched Lean module name to its path under ``lean/``."""
    root = os.path.join(out_dir, "lean")
    found = {}
    for parent, _dirs, names in os.walk(root):
        for name in names:
            if not name.endswith(".lean"):
                continue
            rel = os.path.relpath(os.path.join(parent, name), root).replace(os.sep, "/")
            found[rel[:-len(".lean")].replace("/", ".")] = rel
    return found


def module_imports(out_dir, rel):
    path = os.path.join(out_dir, "lean", rel.replace("/", os.sep))
    with open(path, encoding="utf-8") as handle:
        return parse_imports(handle.read())


def _log(message):
    print(message, flush=True)


def close_imports(out_dir, manifest, *, max_modules=DEFAULT_MAX_MODULES,
                  timeout=240, tries=4, log=_log):
    """Fetch the OAI import closure of what is already on disk.

    A statement-level set cannot satisfy C11: the statements import execution
    modules the seed list never names. Walking the imports turns that hand-
    maintained list into a derived one, and every added file lands in the same
    manifest, so the closure stays pinned and reviewable.

    Only successful fetches are appended to ``manifest`` (a failed record would
    point at a file that does not exist and break manifest verification);
    failures are named in the returned ``failed`` list instead.  The walk is
    breadth-first and de-duplicated by module name, so each module is fetched
    at most once and every added module is scanned for further imports.

    Returns a dict with ``added``, ``failed``, ``remaining`` (queued but not
    fetched, non-empty only on truncation), ``truncated`` and ``complete``.
    """
    fetched = lean_modules(out_dir)
    tried = set()
    queue = []
    imported_by = {}

    def enqueue(module, importer):
        if not module.startswith("OAI.") or module in fetched:
            return
        imported_by.setdefault(module, set()).add(importer)
        if module not in tried and module not in queue:
            queue.append(module)

    for module, rel in sorted(fetched.items()):
        for name in module_imports(out_dir, rel):
            enqueue(name, module)

    added = 0
    failed = []
    truncated = False
    while queue:
        if added >= max_modules:
            truncated = True
            log("closure truncated at --max-modules=%d; %d import(s) not fetched"
                % (max_modules, len(queue)))
            break
        module = queue.pop(0)
        tried.add(module)
        rel = module.replace(".", "/") + ".lean"
        remote = "lean/" + rel
        record = fetch_one(remote, remote, out_dir, timeout=timeout, tries=tries)
        record.update({"origin": "import", "module": module,
                       "imported_by": sorted(imported_by.get(module, ()))})
        if record["channel"] is None:
            failed.append({"module": module, "remote": remote,
                           "imported_by": record["imported_by"],
                           "errors": record.get("errors", [])})
            log("FAILED    %s" % remote)
            continue
        manifest.append(record)
        added += 1
        fetched[module] = rel
        log("%-9s %8s  %s" % (record["channel"], record["bytes"], remote))
        for name in module_imports(out_dir, rel):
            enqueue(name, module)

    return {"added": added, "failed": failed, "remaining": list(queue),
            "truncated": truncated,
            "complete": not failed and not truncated and not queue}


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch the family-378 review set, optionally closed under import OAI.*")
    parser.add_argument("--out", default="./family378-sources")
    parser.add_argument("--no-paper", action="store_true",
                        help="skip paper.pdf (the PDF bound can be read from lean/docs/378.md)")
    parser.add_argument("--include-imports", dest="include_imports", action="store_true",
                        default=True,
                        help="also fetch the OAI import closure (default: on)")
    parser.add_argument("--no-include-imports", dest="include_imports", action="store_false",
                        help="stop at the statement-level seed list (19 files, does not compile)")
    parser.add_argument("--max-modules", type=int, default=DEFAULT_MAX_MODULES,
                        help="cap on files added by the import walk (default: %d)" % DEFAULT_MAX_MODULES)
    parser.add_argument("--timeout", type=int, default=240, help="per-request timeout in seconds")
    parser.add_argument("--tries", type=int, default=4, help="attempts per channel")
    args = parser.parse_args(argv)

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    jobs = list(FILES)
    if not args.no_paper:
        jobs.append(PAPER)

    manifest = []
    seed_failed = []
    for remote, local in jobs:
        record = fetch_one(remote, local, out_dir,
                           timeout=args.timeout, tries=args.tries)
        record["origin"] = "seed"
        manifest.append(record)
        print("%-9s %8s  %s" % (record["channel"] or "FAILED",
                                record["bytes"] if record["bytes"] is not None else "-",
                                remote), flush=True)
        if record["channel"] is None:
            seed_failed.append(local)
            print("   errors: %s" % record.get("errors"), flush=True)

    seed_ok = len(jobs) - len(seed_failed)
    print("seed: %d/%d files" % (seed_ok, len(jobs)), flush=True)

    manifest_path = os.path.join(out_dir, "_manifest.json")
    # Pin what we have before the (long) walk, so an interrupted run still
    # leaves a verifiable manifest instead of nothing.
    write_json(manifest_path, manifest)

    closure = None
    if args.include_imports:
        print("closing imports (--max-modules=%d, timeout=%ss, tries=%d)"
              % (args.max_modules, args.timeout, args.tries), flush=True)
        closure = close_imports(out_dir, manifest, max_modules=args.max_modules,
                                timeout=args.timeout, tries=args.tries)

    write_json(manifest_path, manifest)

    if closure is None:
        status = "skipped"
        summary = ("closure: skipped (--no-include-imports); set covers the seed list only, "
                   "OAI imports are not closed")
    elif closure["complete"]:
        status = "complete"
        summary = ("closure: complete (%d file(s) added, every OAI import resolves "
                   "inside the fetched subset)" % closure["added"])
    elif closure["truncated"]:
        status = "truncated"
        summary = ("closure: PARTIAL (truncated at --max-modules=%d: %d added, "
                   "%d import(s) left unfetched, %d failed)"
                   % (args.max_modules, closure["added"], len(closure["remaining"]),
                      len(closure["failed"])))
    else:
        status = "partial"
        summary = ("closure: PARTIAL (%d added, %d failed, %d import(s) left unfetched)"
                   % (closure["added"], len(closure["failed"]),
                      len(closure["remaining"])))
    print(summary, flush=True)

    closure_path = os.path.join(out_dir, "_closure.json")
    write_json(closure_path, {
        "include_imports": args.include_imports,
        "max_modules": args.max_modules,
        "timeout": args.timeout,
        "tries": args.tries,
        "status": status,
        "seed_files": len(jobs),
        "seed_fetched": seed_ok,
        "imported_files": closure["added"] if closure else 0,
        "failed": closure["failed"] if closure else [],
        "not_fetched": closure["remaining"] if closure else [],
        "complete": bool(closure and closure["complete"]),
    })

    total = sum(r["bytes"] or 0 for r in manifest)
    ok = sum(1 for r in manifest if r["channel"] is not None)
    print("fetched %d/%d files, %d bytes total -> %s" % (ok, len(manifest), total, manifest_path))
    print("closure status: %s -> %s" % (status, closure_path), flush=True)

    if seed_failed or (closure and closure["failed"]):
        return 1
    if closure and closure["truncated"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

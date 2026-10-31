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

It writes a `_manifest.json` next to the fetched tree with the sha256 of every
file, so the review can be re-run against a pinned copy.
"""

import argparse
import hashlib
import json
import os
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


def fetch_one(remote, local, out_dir):
    target = os.path.join(out_dir, local.replace("/", os.sep))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    quoted = urllib.parse.quote(remote)
    errors = []
    for channel, url in (("jsdelivr", CDN + quoted), ("raw", RAW + quoted)):
        try:
            blob = _get(url)
            with open(target, "wb") as handle:
                handle.write(blob)
            return {"remote": remote, "local": local, "bytes": len(blob),
                    "sha256": sha256_of(target), "channel": channel}
        except Exception as error:  # noqa: BLE001
            errors.append("%s: %s" % (channel, str(error)[:120]))
    return {"remote": remote, "local": local, "bytes": None,
            "sha256": None, "channel": None, "errors": errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="./family378-sources")
    parser.add_argument("--no-paper", action="store_true",
                        help="skip paper.pdf (the PDF bound can be read from lean/docs/378.md)")
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    jobs = list(FILES)
    if not args.no_paper:
        jobs.append(PAPER)

    manifest = []
    for remote, local in jobs:
        record = fetch_one(remote, local, out_dir)
        manifest.append(record)
        print("%-9s %8s  %s" % (record["channel"] or "FAILED",
                                record["bytes"] if record["bytes"] is not None else "-",
                                remote))
        if record["channel"] is None:
            print("   errors: %s" % record.get("errors"))

    manifest_path = os.path.join(out_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True, ensure_ascii=False)

    total = sum(r["bytes"] or 0 for r in manifest)
    ok = sum(1 for r in manifest if r["channel"] is not None)
    print("fetched %d/%d files, %d bytes total -> %s" % (ok, len(manifest), total, manifest_path))
    return 0 if ok == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())

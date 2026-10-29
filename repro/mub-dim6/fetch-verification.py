#!/usr/bin/env python3
"""Fetch the MUB d=6 verification package from openai/math without cloning the repo.

The upstream repository is ~900 MB, so a full clone is wasteful. This script pulls
only the files needed to re-run the published numerical consistency check.

Sources, in order of preference per file:
  1. jsDelivr CDN mirror of the GitHub repo (fast, but refuses files > 20 MB)
  2. raw.githubusercontent.com (authoritative, occasionally unreachable)
  3. GitHub git-blob API (base64; used for large files such as fine.bin)

Usage:
    python3 fetch-verification.py --out ./mub-dim6-verification

It prints a JSON manifest with sha256 of every file it wrote.
"""

import argparse
import base64
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = "openai/math"
REF = "main"
ROOT = (
    "preprints/"
    "The-maximum-number-of-mutually-unbiased-bases-in-dimension-six-September-24-2026/"
    "verification/saved-run"
)
SUBDIRS = ["execution/data", "execution/results", "compiled-build/source"]
CDN = "https://cdn.jsdelivr.net/gh/{repo}@{ref}/"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/"
API = "https://api.github.com/repos/{repo}"


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


def list_dir(path):
    url = "{}/contents/{}".format(API.format(repo=REPO), urllib.parse.quote(path))
    payload = json.loads(_get(url, timeout=90).decode("utf-8", "ignore"))
    return [(item["name"], item.get("size"), item.get("sha")) for item in payload]


def fetch_one(job, out_dir):
    subdir, name, size, sha = job
    target = os.path.join(out_dir, name)
    if os.path.exists(target) and size is not None and os.path.getsize(target) == size:
        return {"name": name, "size": size, "sha256": sha256_of(target), "status": "cached"}
    remote = "{}{}/{}".format(ROOT, subdir, name)
    errors = []
    for url in (CDN.format(repo=REPO, ref=REF) + urllib.parse.quote(remote),
                RAW.format(repo=REPO, ref=REF) + urllib.parse.quote(remote)):
        try:
            blob = _get(url)
            if size is not None and len(blob) != size:
                errors.append("size mismatch {} != {}".format(len(blob), size))
                continue
            with open(target, "wb") as handle:
                handle.write(blob)
            return {"name": name, "size": len(blob), "sha256": sha256_of(target), "status": "ok"}
        except Exception as error:  # noqa: BLE001
            errors.append(str(error)[:120])
    if sha:
        try:
            blob = json.loads(_get("{}/git/blobs/{}".format(API.format(repo=REPO), sha), timeout=600))
            data = base64.b64decode(blob["content"]) if blob.get("encoding") == "base64" else b""
            with open(target, "wb") as handle:
                handle.write(data)
            return {"name": name, "size": len(data), "sha256": sha256_of(target), "status": "ok-blob"}
        except Exception as error:  # noqa: BLE001
            errors.append(str(error)[:120])
    return {"name": name, "size": size, "sha256": None, "status": "failed", "errors": errors}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="./mub-dim6-verification")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    jobs = []
    for subdir in SUBDIRS:
        for name, size, sha in list_dir("{}/{}".format(ROOT, subdir)):
            jobs.append((subdir, name, size, sha))
    print("files to fetch: {}".format(len(jobs)))

    manifest = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for record in pool.map(lambda job: fetch_one(job, out_dir), jobs):
            manifest.append(record)
            if record["status"] == "failed":
                print("FAILED {}: {}".format(record["name"], record.get("errors")))

    manifest_path = os.path.join(out_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)

    ok = sum(1 for record in manifest if record["status"] != "failed")
    print("fetched {}/{} -> {}".format(ok, len(manifest), manifest_path))
    return 0 if ok == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())

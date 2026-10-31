#!/usr/bin/env python3
"""Fetch the MUB d=6 verification package from openai/math without cloning the repo.

The upstream repository is ~900 MB, so a full clone is wasteful.  This script
pulls only the files needed to re-run the published numerical consistency check
and it *preserves the upstream directory layout*, because the upstream
validator (`execution/check_records.py`) reads its inputs by relative path
(`execution/data/...`, `execution/commands.json`, `execution/results/...`).

Upstream layout that is fetched (verified against the GitHub contents API):

    verification/saved-run/
      VERIFY.md
      execution/check_records.py
      execution/commands.json
      execution/data/            19 files + batches/ (177 files)
      execution/results/         100 files
      compiled-build/build.sh
      compiled-build/source/     8 C++ files

Download channels, in order of preference per file:
  1. jsDelivr CDN mirror of the GitHub repo (fast, but refuses files > 20 MB)
  2. raw.githubusercontent.com (authoritative, occasionally unreachable)
  3. GitHub git-blob API (base64; used for large files such as fine.bin)
  4. gh-proxy.com with HTTP Range requests (chunked; used for files > 20 MB)

Usage:
    python3 fetch-verification.py --out ./mub-dim6-verification

It prints a JSON manifest with the sha256 of every file it wrote.
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
# Directories that are walked recursively, relative to ROOT.
DIRS = [
    "execution/data",
    "execution/data/batches",
    "execution/results",
    "compiled-build/source",
]
# Individual files that live directly in ROOT or in one of the directories above.
FILES = [
    "VERIFY.md",
    "execution/check_records.py",
    "execution/commands.json",
    "compiled-build/build.sh",
]
CDN = "https://cdn.jsdelivr.net/gh/{repo}@{ref}/"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/"
API = "https://api.github.com/repos/{repo}"
PROXY = "https://gh-proxy.com/https://raw.githubusercontent.com/{repo}/{ref}/"
JSDELIVR_MAX = 20 * 1024 * 1024
CHUNK = 2 * 1024 * 1024


def _get(url, timeout=240, tries=4, extra_headers=None):
    last = None
    for index in range(tries):
        try:
            request = urllib.request.Request(url, headers=extra_headers or {"User-Agent": "ai-theory-app-radar"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001 - network errors are expected here
            last = error
            time.sleep(1.5 * (index + 1))
    raise last


def _get_range(url, start, end, timeout=240, tries=4):
    """Fetch bytes [start, end] inclusive; returns None when unsupported."""
    last = None
    for index in range(tries):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "ai-theory-app-radar",
                             "Range": "bytes=%d-%d" % (start, end)})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                blob = response.read()
            if blob:
                return blob
        except Exception as error:  # noqa: BLE001
            last = error
            time.sleep(1.5 * (index + 1))
    raise last


def list_dir(path):
    """List one upstream directory through the GitHub contents API."""
    url = "%s/contents/%s" % (API.format(repo=REPO), urllib.parse.quote(path))
    payload = json.loads(_get(url, timeout=90).decode("utf-8", "ignore"))
    files, dirs = [], []
    for item in payload:
        if item.get("type") == "dir":
            dirs.append(item["name"])
        else:
            files.append((item["name"], item.get("size")))
    return files, dirs


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_via_blob_api(remote, target, size):
    """Download through the GitHub git-blob API (base64 encoded)."""
    url = "%s/git/blobs/%s" % (API.format(repo=REPO), urllib.parse.quote(remote))
    payload = json.loads(_get(url, timeout=600).decode("utf-8", "ignore"))
    blob = base64.b64decode(payload["content"])
    if size is not None and len(blob) != size:
        raise IOError("size mismatch %d != %d" % (len(blob), size))
    with open(target, "wb") as handle:
        handle.write(blob)


def fetch_via_chunks(remote, target, size):
    """Download a large file in Range chunks through a Range-capable mirror."""
    url = PROXY.format(repo=REPO, ref=REF) + urllib.parse.quote(remote)
    total = size if size is not None else 0
    with open(target, "wb") as handle:
        start = 0
        while start < total:
            end = min(start + CHUNK, total) - 1
            blob = _get_range(url, start, end)
            if len(blob) != end - start + 1:
                raise IOError("short chunk at %d: %d bytes" % (start, len(blob)))
            handle.write(blob)
            start = end + 1
    if size is not None and os.path.getsize(target) != size:
        raise IOError("final size mismatch")


def fetch_one(job, out_dir):
    remote, size = job
    # The package root is the upstream `verification/saved-run` directory; files
    # are stored relative to it, exactly as the upstream validator expects.
    relative = remote[len(ROOT) + 1:]
    target = os.path.join(out_dir, relative.replace("/", os.sep))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    record = {"local": relative, "size": size, "remote": remote}
    if os.path.exists(target) and size is not None and os.path.getsize(target) == size:
        record["sha256"] = sha256_of(target)
        record["status"] = "cached"
        return record

    errors = []
    channels = []
    large = size is not None and size > JSDELIVR_MAX
    if not large:
        channels.append(CDN.format(repo=REPO, ref=REF) + urllib.parse.quote(remote))
        channels.append(RAW.format(repo=REPO, ref=REF) + urllib.parse.quote(remote))
    for url in channels:
        try:
            blob = _get(url)
            if size is not None and len(blob) != size:
                errors.append("size mismatch %d != %d" % (len(blob), size))
                continue
            with open(target, "wb") as handle:
                handle.write(blob)
            record["sha256"] = sha256_of(target)
            record["status"] = "ok"
            record["channel"] = url.split("/")[2]
            return record
        except Exception as error:  # noqa: BLE001
            errors.append("%s: %s" % (url.split("/")[2], error))

    # Large files: chunked Range download through the mirror.
    if large:
        try:
            fetch_via_chunks(remote, target, size)
            record["sha256"] = sha256_of(target)
            record["status"] = "ok"
            record["channel"] = "gh-proxy:range"
            return record
        except Exception as error:  # noqa: BLE001
            errors.append("gh-proxy:range: %s" % error)

    # Last resort: the git-blob API.
    try:
        fetch_via_blob_api(remote, target, size)
        record["sha256"] = sha256_of(target)
        record["status"] = "ok"
        record["channel"] = "api:blob"
        return record
    except Exception as error:  # noqa: BLE001
        errors.append("api:blob: %s" % error)

    record["status"] = "failed"
    record["errors"] = errors
    return record


def collect_jobs():
    """Enumerate every file that has to be fetched."""
    jobs = []
    for name in FILES:
        jobs.append((ROOT + "/" + name, None))
    for directory in DIRS:
        files, _dirs = list_dir("%s/%s" % (ROOT, directory))
        for name, size in files:
            jobs.append(("%s/%s/%s" % (ROOT, directory, name), size))
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="./mub-dim6-verification",
                        help="output directory (keeps the upstream layout)")
    parser.add_argument("--jobs", type=int, default=8,
                        help="parallel downloads (default 8)")
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    jobs = collect_jobs()
    print("files to fetch: %d -> %s" % (len(jobs), out_dir))

    manifest = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for record in pool.map(lambda job: fetch_one(job, out_dir), jobs):
            manifest.append(record)
            if record["status"] == "failed":
                print("FAILED %s: %s" % (record["local"], record.get("errors")))
            else:
                print("ok %-46s %9s bytes  %s"
                      % (record["local"], record["size"], record.get("channel", "-")))

    manifest_path = os.path.join(out_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)

    ok = sum(1 for record in manifest if record["status"] != "failed")
    print("fetched %d/%d -> %s" % (ok, len(manifest), manifest_path))
    return 0 if ok == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())

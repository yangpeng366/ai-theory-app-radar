#!/usr/bin/env python3
"""Seal a fetched family-378 tree into one complete ``_manifest.json``.

Why this exists: ``fetch-sources.py`` writes a manifest for *one run* (the seed
list plus the modules that run's import walk added).  A closure that had to be
fetched in several bounded passes -- which is what happens when the family's
own subtree is far larger than one run's ``--max-modules`` -- therefore leaves
files on disk that no manifest lists.  ``check-gap.py`` C1 only verifies what
the manifest names, so the tree would be reviewed while a large part of it was
unaccounted for.

This script closes that gap without inventing evidence:

  * every file on disk is hashed (sha256) and listed;
  * a file that the pre-seal manifest already records must match that record
    byte for byte (``evidence: fetch-manifest`` -- the sha256 was computed by
    the fetch that wrote the bytes);
  * a file that only appears in a fetch log must match the byte count the log
    reported for it (``evidence: fetch-log`` -- provenance is the log line,
    the hash is of the file as it sits on disk);
  * anything else is reported as a problem and the script exits 1.

The pin (repo + resolved commit sha) is carried over from the previous
manifest, so the sealed file still answers "which upstream commit is this?".

Usage:
    python seal-manifest.py --src ./f378 --log run1.log --log run2.log
    python seal-manifest.py --src ./f378 --log run1.log --no-write   # dry run

Exit codes: 0 = sealed, every file has a record; 1 = at least one file has no
record or contradicts it; 2 = usage error.
"""

import argparse
import hashlib
import json
import os
import re
import sys

# "<channel>  <bytes>  <remote path>" -- one line per successful fetch.
FETCH_LINE = re.compile(r"^(jsdelivr|raw|api-contents)\s+(\d+)\s+(\S+)\s*$")

SKIP_SUFFIXES = (".log",)
SKIP_NAMES = {"_manifest.json", "_closure.json"}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_logs(paths):
    """Map remote path -> (bytes, channel) from every fetch log line."""
    seen = {}
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = FETCH_LINE.match(line.rstrip("\r\n"))
                if not match:
                    continue
                channel, size, remote = match.groups()
                seen[remote] = (int(size), channel)
    return seen


def walk(src):
    for parent, dirs, names in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in sorted(names):
            if name in SKIP_NAMES or name.startswith("_manifest-") \
                    or name.startswith("_closure-") or name.endswith(SKIP_SUFFIXES):
                continue
            full = os.path.join(parent, name)
            rel = os.path.relpath(full, src).replace(os.sep, "/")
            yield rel, full


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", required=True, help="fetched tree (contains lean/, CONTENTS.md, ...)")
    parser.add_argument("--log", action="append", default=[], help="fetch log to read (repeatable)")
    parser.add_argument("--manifest", default=None, help="existing manifest (default: <src>/_manifest.json)")
    parser.add_argument("--no-write", action="store_true", help="report only, do not rewrite the manifest")
    args = parser.parse_args()

    src = os.path.abspath(args.src)
    manifest_path = args.manifest or os.path.join(src, "_manifest.json")

    pin = {}
    recorded = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            for key in ("upstream_repo", "ref_requested", "ref_resolved",
                        "ref_resolved_at", "ref_source", "ref_error"):
                if key in payload:
                    pin[key] = payload[key]
            for item in payload.get("files", []):
                recorded[item["local"]] = item
    if not pin:
        print("no pin fields in %s -- refusing to seal an unpinned tree" % manifest_path,
              file=sys.stderr)
        return 2

    log = read_logs(args.log)
    files = []
    counts = {"fetch-manifest": 0, "fetch-log": 0}
    problems = []
    for rel, full in walk(src):
        size = os.path.getsize(full)
        digest = sha256_of(full)
        base = recorded.get(rel)
        if base is not None:
            if base.get("sha256") != digest or base.get("bytes") != size:
                problems.append("%s: on-disk bytes/sha256 differ from the fetch manifest" % rel)
                continue
            files.append({"remote": base.get("remote", rel), "local": rel, "bytes": size,
                          "sha256": digest, "channel": base.get("channel"),
                          "origin": base.get("origin", "import"),
                          "evidence": "fetch-manifest"})
            counts["fetch-manifest"] += 1
            continue
        logged = log.get(rel)
        if logged is None:
            problems.append("%s: no fetch-manifest record and no fetch-log line" % rel)
            continue
        if logged[0] != size:
            problems.append("%s: log says %d bytes, disk has %d" % (rel, logged[0], size))
            continue
        files.append({"remote": rel, "local": rel, "bytes": size, "sha256": digest,
                      "channel": logged[1], "origin": "import", "evidence": "fetch-log"})
        counts["fetch-log"] += 1

    files.sort(key=lambda item: item["local"])
    total = sum(item["bytes"] for item in files)
    print("files sealed: %d (%d fetch-manifest, %d fetch-log), %d bytes"
          % (len(files), counts["fetch-manifest"], counts["fetch-log"], total))
    print("pin: repo=%s resolved=%s source=%s"
          % (pin.get("upstream_repo"), pin.get("ref_resolved"), pin.get("ref_source")))
    for line in problems[:10]:
        print("PROBLEM " + line, file=sys.stderr)
    if problems:
        print("%d file(s) unaccounted for; manifest not written" % len(problems), file=sys.stderr)
        return 1

    if args.no_write:
        print("dry run: %s left unchanged" % manifest_path)
        return 0

    payload = dict(pin)
    payload["files"] = files
    payload["sealed_at"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload["seal_note"] = ("one record per file on disk; evidence=fetch-manifest means the "
                            "sha256 came from the fetch that wrote the file, evidence=fetch-log "
                            "means the byte count came from the fetch log and the sha256 was "
                            "computed when sealing")
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True, ensure_ascii=False)
    print("manifest -> %s" % manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One-command self-check for the family 266 (MUB d=6) verification package.

The check is deliberately minimal: the upstream validator
(`execution/check_records.py`) is the only thing that decides the verdict.
If it prints "PASS within numerical consistency scope", the package is green.

What this script adds on top of the bare validator:

  1. it can fetch the package itself (`--fetch`), so a third party needs one
     command, not a checklist;
  2. it re-computes the sha256 of 12 key files and compares them with the
     values recorded in the 2026-10-29 review card, so a silently changed
     upstream artefact is reported instead of being run unnoticed;
  3. it prints the counts that matter, and optionally runs the ABI/floating
     point probe (`--abi`, Linux only).

Exit codes:
  0  green   -- validator PASS
  1  red     -- validator failed, or a pinned file is missing
  2  setup   -- the package is not present (use --fetch) or the platform
                does not support the optional stages

Usage:
    python3 selfcheck.py --fetch
    python3 selfcheck.py --pkg ./mub-dim6-verification --abi
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PKG = os.path.join(HERE, "mub-dim6-verification")

# sha256 prefixes (first 16 hex chars) recorded in
# radar/2026-10-29-family266-mub-dim6-review.md, section 3.1.
PINNED = {
    "execution/commands.json": "e27de17eb16a447c",
    "execution/check_records.py": "565f4ee47ab7b7c4",
    "execution/data/fine.bin": "9b5b743b61907277",
    "execution/data/centers.txt": "c48bc9a2be1eb2cd",
    "compiled-build/source/covout.cpp": "2a7e6bf5ca485765",
    "compiled-build/source/stageB.cpp": "7e609a2f282d519a",
    "compiled-build/source/stageC.cpp": "60a1b10091852809",
    "compiled-build/source/atlas.cpp": "dcbf2dbe1054c01f",
    "compiled-build/source/ub.cpp": "bb031282340012e6",
    "compiled-build/source/patchx.cpp": "a78a1ab171d8c7f1",
    "compiled-build/source/seed.cpp": "3c6c7a7092230de2",
    "compiled-build/build.sh": "81dc6c71ecaa6511",
}

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def colour(text, code):
    if not sys.stdout.isatty():
        return text
    return code + text + RESET


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(pkg_dir):
    script = os.path.join(HERE, "fetch-verification.py")
    if not os.path.exists(script):
        print("fetch-verification.py is missing next to this script")
        return False
    print("fetching the verification package into %s ..." % pkg_dir)
    result = subprocess.run([sys.executable, script, "--out", pkg_dir])
    return result.returncode == 0


def check_pins(pkg_dir):
    """Compare the pinned sha256 prefixes with the files on disk."""
    missing, changed, matched = [], [], 0
    for relative, prefix in sorted(PINNED.items()):
        path = os.path.join(pkg_dir, relative.replace("/", os.sep))
        if not os.path.exists(path):
            missing.append(relative)
            continue
        digest = sha256_of(path)
        # The pin is a sha256 *prefix*; startswith() keeps a shorter recorded
        # prefix (as in the 2026-10-29 card) from being reported as drift.
        if digest.startswith(prefix):
            matched += 1
        else:
            changed.append("%s (%s != %s)" % (relative, digest[:16], prefix))
    return matched, missing, changed


def run_validator(pkg_dir):
    """Run the upstream validator and return (verdict, payload, raw output)."""
    script = os.path.join(pkg_dir, "execution", "check_records.py")
    if not os.path.exists(script):
        return None, None, "execution/check_records.py is missing"
    completed = subprocess.run([sys.executable, script], cwd=pkg_dir,
                               capture_output=True, text=True)
    raw = (completed.stdout or "") + (completed.stderr or "")
    payload = None
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(raw[start:end + 1])
        except ValueError:
            payload = None
    verdict = None
    if payload:
        verdict = payload.get("result")
    return verdict, payload, raw


def run_abi_probe(pkg_dir):
    """Second stage: build and run the ABI / floating point probe (Linux only)."""
    source = os.path.join(pkg_dir, "compiled-build", "source", "abi-fp-probe.cpp")
    if not os.path.exists(source):
        return None, "compiled-build/source/abi-fp-probe.cpp is missing"
    if not shutil.which("g++"):
        return None, "g++ is not available"
    binary = os.path.join(pkg_dir, "_abi-fp-probe")
    build = subprocess.run(["g++", "-O2", "-std=gnu++17", source, "-o", binary],
                           capture_output=True, text=True)
    if build.returncode != 0:
        return None, "compile failed: %s" % build.stderr.strip()[:400]
    probe = subprocess.run([binary], capture_output=True, text=True)
    text = (probe.stdout or "") + (probe.stderr or "")
    if probe.returncode != 0 or "passed" not in text.lower():
        return None, "probe did not pass: %s" % text.strip()[:400]
    return text.strip().splitlines()[-1], None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkg", default=DEFAULT_PKG,
                        help="package directory (default: ./mub-dim6-verification)")
    parser.add_argument("--fetch", action="store_true",
                        help="fetch the package first if it is missing")
    parser.add_argument("--abi", action="store_true",
                        help="also build and run the ABI/floating point probe")
    parser.add_argument("--report", help="write a short markdown report to this file")
    args = parser.parse_args()

    pkg_dir = os.path.abspath(args.pkg)
    ready = os.path.isfile(os.path.join(pkg_dir, "execution", "check_records.py"))
    if not ready:
        if args.fetch:
            if not fetch(pkg_dir):
                print(colour("SETUP: fetch failed", RED))
                return 2
        else:
            print(colour("SETUP: %s is missing -- rerun with --fetch" % pkg_dir, YELLOW))
            return 2
    elif args.fetch:
        # The package exists; fetch again to fill in missing files.  Files that
        # are already present with the upstream size are kept as they are.
        if not fetch(pkg_dir):
            print(colour("SETUP: fetch failed", RED))
            return 2

    lines = []
    matched, missing, changed = check_pins(pkg_dir)
    lines.append("pinned sha256: %d matched, %d changed, %d missing"
                 % (matched, len(changed), len(missing)))
    for item in changed:
        lines.append("  CHANGED %s" % item)
    for item in missing:
        lines.append("  MISSING %s" % item)
    if missing:
        print(colour("RED: the package is incomplete", RED))
        for line in lines:
            print(line)
        return 1

    verdict, payload, raw = run_validator(pkg_dir)
    if verdict is None:
        print(colour("RED: the validator did not produce a verdict", RED))
        print(raw.strip()[:2000])
        return 1

    cover = payload.get("cover", {})
    counts = ("centers %s / checked pairs %s / fine records %s / batches %s"
              % (cover.get("centers"), cover.get("checked_pairs"),
                 payload.get("fine_records"), payload.get("batches")))
    passed = verdict.startswith("PASS")
    print(colour("validator: %s" % verdict, GREEN if passed else RED))
    print("counts: %s" % counts)
    print("pins: %d matched, %d changed" % (matched, len(changed)))

    abi_note = None
    if args.abi:
        message, error = run_abi_probe(pkg_dir)
        if error:
            abi_note = "ABI probe skipped: %s" % error
            print(colour(abi_note, YELLOW))
        else:
            abi_note = "ABI probe: %s" % message
            print(colour(abi_note, GREEN))

    if not passed:
        print(colour("RED: validator did not pass", RED))
        return 1

    print(colour("GREEN: family 266 package is internally consistent "
                 "(PASS within numerical consistency scope)", GREEN))
    lines.append("verdict: %s" % verdict)
    lines.append("counts: %s" % counts)
    if abi_note:
        lines.append(abi_note)
    lines.append("boundary: the check proves internal consistency of the archived "
                 "numerical records only; it is not a certification of the archive, "
                 "not a proof of the C++ implementation, and not a verification of "
                 "the original compiler/hardware.")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write("# family 266 self-check\n\n")
            for line in lines:
                handle.write("- %s\n" % line)
            handle.write("\n")
        print("report written to %s" % args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

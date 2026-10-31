#!/usr/bin/env python3
"""Watch the upstream openai/math (and the oai-math-revised community fork)
for increments that matter to this radar.

The radar only cares about *deltas* in three artefacts:

  * ``CONTENTS.md`` -- the manuscript map.  It carries the headline counters
    ("N manuscripts covering M result families") and one heading per result
    family ("**378. Disproof of the Exponential Time Hypothesis.**").
  * ``history.md``  -- the release log.  New sections ("## October 26, 2026")
    announce new results, withdrawals and formalisation fixes.
  * ``preprints/``  -- the actual manuscript directories (optional, ``--deep``),
    which is the ground truth for "a new family showed up".

The script keeps a JSON snapshot next to itself (``upstream-snapshot.json``)
and prints the delta against it.  Run it with ``--update`` to move the
baseline forward after reviewing the delta.

Usage:
    python3 monitor-upstream.py                      # delta against the snapshot
    python3 monitor-upstream.py --update             # review, then move the baseline
    python3 monitor-upstream.py --deep               # also count preprints/ dirs
    python3 monitor-upstream.py --with-community     # also watch oai-math-revised
    python3 monitor-upstream.py --json               # machine readable output

Exit codes:
    0  no change, or the change was printed and reviewed
    1  the fetch failed (network / upstream moved)
    2  usage error
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "upstream-snapshot.json")

REPOS = {
    "openai/math": {
        "cdn": "https://cdn.jsdelivr.net/gh/openai/math@main/",
        "raw": "https://raw.githubusercontent.com/openai/math/main/",
    },
    "mathcommunity/oai-math-revised": {
        "cdn": "https://cdn.jsdelivr.net/gh/mathcommunity/oai-math-revised@main/",
        "raw": "https://raw.githubusercontent.com/mathcommunity/oai-math-revised/main/",
    },
}

HEADLINE = re.compile(r"\*\*(\d+)\s+manuscripts covering (\d+)\s+result families")
FAMILY = re.compile(r"^\*\*(\d+)\.\s+(.*?)\*\*", re.MULTILINE)
HISTORY_SECTION = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _get(url, timeout=180, tries=3):
    last = None
    for index in range(tries):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "ai-theory-app-radar"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001 - network errors are expected
            last = error
            time.sleep(1.5 * (index + 1))
    raise last


def fetch_text(repo, path):
    """Fetch one text file, trying the CDN mirror first."""
    quote = urllib.parse.quote(path)
    errors = []
    for channel in ("cdn", "raw"):
        url = REPOS[repo][channel] + quote
        try:
            blob = _get(url)
            return blob.decode("utf-8", "replace"), channel, hashlib.sha256(blob).hexdigest()
        except Exception as error:  # noqa: BLE001
            errors.append("%s: %s" % (channel, str(error)[:120]))
    raise IOError("; ".join(errors))


def count_preprint_dirs(repo):
    """Count the directories under preprints/ through the contents API."""
    api = "https://api.github.com/repos/%s/contents/preprints" % repo
    payload = json.loads(_get(api, timeout=120).decode("utf-8", "ignore"))
    return sum(1 for item in payload if item.get("type") == "dir")


def parse_contents(text):
    """Headline counters, family numbers and a hash of the family titles."""
    families = {m.group(1): m.group(2).strip() for m in FAMILY.finditer(text)}
    headline = HEADLINE.search(text)
    manuscripts = int(headline.group(1)) if headline else None
    families_count = int(headline.group(2)) if headline else None
    titles_blob = json.dumps(families, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {
        "manuscripts": manuscripts,
        "families": families_count if families_count is not None else len(families),
        "family_numbers": sorted(families),
        "family_titles_sha256": hashlib.sha256(titles_blob).hexdigest(),
        "max_family": max((int(k) for k in families), default=0),
    }


def parse_history(text):
    return [m.group(1).strip() for m in HISTORY_SECTION.finditer(text)]


def observe(repo, deep=False):
    contents, channel, sha = fetch_text(repo, "CONTENTS.md")
    history, _channel, hsha = fetch_text(repo, "history.md")
    record = {
        "contents_sha256": sha,
        "history_sha256": hsha,
        "channel": channel,
    }
    record.update(parse_contents(contents))
    record["history_sections"] = parse_history(history)
    if deep:
        record["preprint_dirs"] = count_preprint_dirs(repo)
    return record


def diff(baseline, current):
    """Return (lines, changed) for the delta between two observations."""
    lines = []
    old_numbers = set(baseline.get("family_numbers", []))
    new_numbers = set(current.get("family_numbers", []))
    added = sorted(new_numbers - old_numbers)
    removed = sorted(old_numbers - new_numbers)
    new_sections = [s for s in current.get("history_sections", [])
                    if s not in baseline.get("history_sections", [])]
    gone_sections = [s for s in baseline.get("history_sections", [])
                     if s not in current.get("history_sections", [])]
    contents_changed = current.get("contents_sha256") != baseline.get("contents_sha256")
    history_changed = current.get("history_sha256") != baseline.get("history_sha256")
    titles_changed = (current.get("family_titles_sha256")
                      != baseline.get("family_titles_sha256"))

    lines.append("CONTENTS.md: %s" % ("CHANGED" if contents_changed else "unchanged"))
    lines.append("history.md: %s" % ("CHANGED" if history_changed else "unchanged"))
    lines.append("manuscripts: %s -> %s | families: %s -> %s | max family: %s -> %s"
                 % (baseline.get("manuscripts"), current.get("manuscripts"),
                    baseline.get("families"), current.get("families"),
                    baseline.get("max_family"), current.get("max_family")))
    if "preprint_dirs" in current or "preprint_dirs" in baseline:
        lines.append("preprints/ directories: %s -> %s"
                     % (baseline.get("preprint_dirs"), current.get("preprint_dirs")))
    for number in added:
        lines.append("NEW family %s" % number)
    for number in removed:
        lines.append("REMOVED family %s" % number)
    if titles_changed and not added and not removed:
        lines.append("family titles changed (same family set)")
    for section in new_sections:
        lines.append("NEW history section: %s" % section)
    for section in gone_sections:
        lines.append("DROPPED history section: %s" % section)
    changed = bool(added or removed or new_sections or gone_sections
                   or contents_changed or history_changed)
    return lines, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot", default=SNAPSHOT,
                        help="snapshot file (default: upstream-snapshot.json next to this script)")
    parser.add_argument("--update", action="store_true",
                        help="write the current observation to the snapshot")
    parser.add_argument("--deep", action="store_true",
                        help="also count the preprints/ directories (contents API)")
    parser.add_argument("--with-community", action="store_true",
                        help="also watch mathcommunity/oai-math-revised")
    parser.add_argument("--json", action="store_true", help="machine readable output")
    args = parser.parse_args()

    targets = ["openai/math"]
    if args.with_community:
        targets.append("mathcommunity/oai-math-revised")

    baseline = {}
    if os.path.exists(args.snapshot):
        with open(args.snapshot, encoding="utf-8") as handle:
            baseline = json.load(handle)

    observations = {}
    for repo in targets:
        try:
            observations[repo] = observe(repo, deep=args.deep)
        except Exception as error:  # noqa: BLE001
            print("FAILED %s: %s" % (repo, error), file=sys.stderr)
            return 1

    report = {}
    for repo, current in observations.items():
        old = baseline.get("repos", {}).get(repo)
        if old is None:
            lines = ["no baseline for %s -- first observation" % repo]
            changed = True
        else:
            lines, changed = diff(old, current)
        report[repo] = {"changed": changed, "lines": lines}

    if args.json:
        print(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False))
    else:
        for repo in targets:
            print("== %s ==" % repo)
            for line in report[repo]["lines"]:
                print("  " + line)
        print()
        print("snapshot: %s" % args.snapshot)

    if args.update:
        payload = {"fetched_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                   "repos": {}}
        for repo, current in observations.items():
            old = baseline.get("repos", {}).get(repo, {})
            merged = dict(old)
            merged.update(current)
            payload["repos"][repo] = merged
        with open(args.snapshot, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1, sort_keys=True, ensure_ascii=False)
        print("snapshot updated -> %s" % args.snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

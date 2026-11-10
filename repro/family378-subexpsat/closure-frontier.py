#!/usr/bin/env python3
"""List the import frontier of a partially fetched family-378 tree, with sizes.

`check-gap.py` C11 fails closed: any `import OAI.*` that the fetched subset does
not contain is reported, and on a partial tree that number alone does not say
whether the remaining modules exist upstream.  This script answers exactly that
question for every missing module, without downloading it:

    GET <cdn>/gh/openai/math@<ref>/lean/<path>.lean      Range: bytes=0-0
    -> 206 + `Content-Range: bytes 0-0/<total>`          (size, no body)

A 200 means the server ignored Range and would have sent the whole file, so the
request is repeated against raw.githubusercontent.com; a 404 means the module
name in the `import` line does not exist at that commit, which is a different
defect (in the import text) and is marked as such in the report.

Output is a TSV (module, remote path, bytes, status, channel, url) so the
frontier can be quoted verbatim as a blocker list and re-probed later:

    python closure-frontier.py --src ./f378 --ref <40-hex sha> --tsv frontier.tsv

Exit codes: 0 = every missing module resolved to a size; 1 = at least one probe
failed (404 / timeout / bad range), listed on stderr; 2 = usage error.
"""

import argparse
import concurrent.futures
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

IMPORT_RE = re.compile(r"^[ \t]*(?:(?:public|private|meta)[ \t]+)*import[ \t]+(.+?)[ \t]*$", re.M)
BLOCK = re.compile(r"/-.*?-/", re.S)
MOD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.]*")
RANGE = re.compile(r"bytes\s+\d+-\d+/(\d+)")


def lean_imports(text):
    body = BLOCK.sub(" ", text)
    names = []
    for clause in IMPORT_RE.findall(body):
        for token in clause.split("--", 1)[0].split():
            if token == "all" or not MOD.fullmatch(token):
                continue
            names.append(token)
    return names


def fetched_modules(src):
    root = os.path.join(src, "lean")
    found = {}
    for parent, _dirs, names in os.walk(root):
        for name in names:
            if name.endswith(".lean"):
                rel = os.path.relpath(os.path.join(parent, name), root).replace(os.sep, "/")
                found[rel[:-len(".lean")].replace("/", ".")] = rel
    return found


def missing_modules(src):
    found = fetched_modules(src)
    edges = []
    for module, rel in sorted(found.items()):
        with open(os.path.join(src, "lean", rel.replace("/", os.sep)),
                  encoding="utf-8", errors="replace") as handle:
            for imported in lean_imports(handle.read()):
                if imported.startswith("OAI.") and imported not in found:
                    edges.append((module, imported))
    return found, edges, sorted({imported for _m, imported in edges})


def probe(module, ref, timeout):
    """Return (bytes, status, channel, url) for one module, using Range."""
    remote = "lean/" + module.replace(".", "/") + ".lean"
    quoted = urllib.parse.quote(remote)
    channels = (
        ("jsdelivr", "https://cdn.jsdelivr.net/gh/openai/math@%s/%s" % (ref, quoted)),
        ("raw", "https://raw.githubusercontent.com/openai/math/%s/%s" % (ref, quoted)),
    )
    last = (None, "ERR", "-", channels[0][1])
    for channel, url in channels:
        request = urllib.request.Request(url, headers={
            "User-Agent": "ai-theory-app-radar", "Range": "bytes=0-0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                header = response.headers.get("Content-Range", "")
                match = RANGE.search(header)
                total = int(match.group(1)) if match else None
                if total is None:
                    length = response.headers.get("Content-Length")
                    if status == 200 and length:
                        total = int(length)
                response.read(1)
                if total is None:
                    last = (None, "NO-SIZE(%d)" % status, channel, url)
                    continue
                return total, str(status), channel, url
        except urllib.error.HTTPError as error:
            last = (None, "HTTP %d" % error.code, channel, url)
            if error.code == 404:
                continue
        except Exception as error:  # noqa: BLE001 - timeouts are expected
            last = (None, type(error).__name__, channel, url)
    return last


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", required=True, help="partially fetched tree")
    parser.add_argument("--ref", required=True, help="pinned 40-hex commit sha")
    parser.add_argument("--tsv", default=None, help="write the frontier table here")
    parser.add_argument("--limit", type=int, default=0, help="probe at most N modules (0 = all)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    if not os.path.isdir(os.path.join(args.src, "lean")):
        print("no lean/ under %s" % args.src, file=sys.stderr)
        return 2

    found, edges, missing = missing_modules(args.src)
    targets = missing[:args.limit] if args.limit else missing
    print("fetched modules: %d | unresolved imports: %d | distinct missing modules: %d"
          % (len(found), len(edges), len(missing)))
    print("probing %d module(s) for size through the Range channel" % len(targets))

    rows = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe, module, args.ref, args.timeout): module
                   for module in targets}
        for future in concurrent.futures.as_completed(futures):
            module = futures[future]
            size, status, channel, url = future.result()
            rows.append((module, size, status, channel, url))
            if size is None:
                failures.append((module, status, url))

    rows.sort(key=lambda row: row[0])
    total = sum(row[1] for row in rows if row[1] is not None)
    print("sizes resolved: %d/%d, %.1f KiB total"
          % (len(rows) - len(failures), len(rows), total / 1024.0))
    for module, status, url in failures[:10]:
        print("  FAILED %-28s %s %s" % (status, module, url), file=sys.stderr)

    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("module\tbytes\tstatus\tchannel\turl\n")
            for module, size, status, channel, url in rows:
                handle.write("%s\t%s\t%s\t%s\t%s\n"
                             % (module, "" if size is None else size, status, channel, url))
        print("frontier table -> %s" % args.tsv)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

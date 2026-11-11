#!/usr/bin/env python3
"""Contract gate for the family-378 review set (C1..C24 + the ref pin).

Three things are checked here, none of which a reader of `radar/` could verify
before:

1. **The check numbers are real.**  `check-gap.py` is parsed (AST, no import,
   no fetched sources) and every `record("C<n> ...")` site is collected.  The
   ids must be exactly 1..24, one name per id, and each stage function must own
   the range that the documents claim (stage1 C1-C11, stage2 C12-C19,
   stage3 C20-C24).

2. **The documents only cite checks that exist.**  Every `C<n>` in
   `README.md`, `CONTRIBUTING.md`, `docs/`, `progress/`, `radar/` and the
   `repro/` READMEs must name a defined check.  A citation of `C25` is a
   failure, not a typo to be discovered later.

3. **The fetch is pinned, not assumed.**  `fetch-sources.py` is loaded and
   driven offline (`fetch_one` and the HTTP helpers are replaced): a 40-hex
   `--ref` must come back as `ref_source=arg-sha` with zero commits-API calls,
   while `--ref main --no-resolve` must record `ref_resolved=null`.  The commit
   that the review set was taken from must also be named in the docs.

Usage:
    python tools/check_check_contract.py
    python tools/check_check_contract.py --quiet     # table only on failure

Exit codes: 0 = every contract holds; 1 = at least one violation.
"""

import argparse
import ast
import contextlib
import glob
import importlib.util
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CHECK_GAP = os.path.join(ROOT, "repro", "family378-subexpsat", "check-gap.py")
FETCH = os.path.join(ROOT, "repro", "family378-subexpsat", "fetch-sources.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "verify.yml")

# The stage layout the documents promise (radar/2026-10-30-family378-formalization-gap.md,
# repro/family378-subexpsat/README.md): stage 1 C1-C11, stage 2 C12-C19, stage 3 C20-C24.
EXPECTED_STAGES = {
    "stage1": list(range(1, 12)),
    "stage2": list(range(12, 20)),
    "stage3": list(range(20, 25)),
}

# A helper called by stage2 also records a check (C14, C16), so it belongs there.
HELPER_STAGE = {"check_encoding_bounds": "stage2",
                "check_exponent_gap": "stage2"}

# openai/math commit the 2026-11-11 review set was fetched from; recorded as
# ref_resolved / ref_source=arg-sha in the run logs quoted under radar/.
PINNED_COMMIT = "4eaee87548250b2682affda7d05d947c05554bae"
PIN_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "repro/family378-subexpsat/README.md",
]

DOC_PATTERNS = [
    "README.md",
    "CONTRIBUTING.md",
    "docs/*.md",
    "progress/*.md",
    "radar/*.md",
    "repro/*.md",
    "repro/**/*.md",
]

CHECK_ID_RE = re.compile(r"^C(\d{1,2})\s+(.+)$")
REFERENCE_RE = re.compile(r"(?<![A-Za-z0-9_])C(\d{1,2})(?![0-9])")


def collect_checks():
    """Return {id: {"name": str, "stage": str, "sites": int}} from check-gap.py."""
    with open(CHECK_GAP, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=CHECK_GAP)

    found = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        function = node.name
        stage = function if function in EXPECTED_STAGES else HELPER_STAGE.get(function)
        if stage is None:
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            if getattr(call.func, "id", None) != "record" or not call.args:
                continue
            literal = call.args[0]
            if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
                continue
            match = CHECK_ID_RE.match(literal.value)
            if not match:
                continue
            number, name = int(match.group(1)), match.group(2).strip()
            entry = found.setdefault(number, {"name": name, "stage": stage, "sites": 0})
            if entry["name"] != name:
                entry["conflict"] = name
            if entry["stage"] != stage:
                entry["stage_conflict"] = stage
            entry["sites"] += 1
    return found


def doc_files():
    seen = []
    for pattern in DOC_PATTERNS:
        for path in sorted(glob.glob(os.path.join(ROOT, pattern), recursive=True)):
            if os.path.isfile(path) and path not in seen:
                seen.append(path)
    return seen


def scan_references(defined):
    """Return (files_scanned, reference_count, unknown, radar_count, per_id)."""
    known = set(defined)
    unknown = []
    total = 0
    radar_total = 0
    per_id = {}
    files = doc_files()
    for path in files:
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        with open(path, encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                for match in REFERENCE_RE.finditer(line):
                    ident = int(match.group(1))
                    total += 1
                    per_id[ident] = per_id.get(ident, 0) + 1
                    if rel.startswith("radar/"):
                        radar_total += 1
                    if ident not in known:
                        unknown.append((rel, number, match.group(0),
                                        line.strip()[:100]))
    return files, total, unknown, radar_total, per_id


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_pin(problems):
    """Drive fetch-sources.py offline and assert the pin semantics."""
    module = load_module(FETCH, "fetch_sources_contract")

    def no_network(*_args, **_kwargs):
        raise AssertionError("network access attempted during the offline pin check")

    module._api_get = no_network
    module._get = no_network
    module.urllib.request.urlopen = no_network

    seed = "lean/OAI/Contract.lean"

    def fake_fetch(remote, local, out_dir, timeout=240, tries=4, ref=None):
        return {"remote": remote, "local": local, "bytes": 1, "sha256": "0" * 64,
                "channel": "fake", "via": ["fake -> ok"]}

    module.fetch_one = fake_fetch
    module.FILES = [(seed, seed)]

    if not module.SHA_RE.match(PINNED_COMMIT):
        problems.append("fetch-sources.py SHA_RE rejects the documented commit %s"
                        % PINNED_COMMIT)
    for bad in ("4eaee87548250b2682affda7d05d947c05554ba",
                "4eaee87548250b2682affda7d05d947c05554bae0",
                "main"):
        if module.SHA_RE.match(bad):
            problems.append("fetch-sources.py SHA_RE accepts %r as a commit sha" % bad)

    def run(argv):
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            code = module.main(argv)
        return code, captured.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "sha")
        code, text = run(["--out", out, "--no-paper", "--no-include-imports",
                          "--ref", PINNED_COMMIT, "--tries", "1"])
        if code != 0:
            problems.append("pinned fetch run exited %d" % code)
        with open(os.path.join(out, "_manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest.get("ref_source") != "arg-sha":
            problems.append("40-hex --ref recorded ref_source=%r (expected 'arg-sha')"
                            % manifest.get("ref_source"))
        if manifest.get("ref_resolved") != PINNED_COMMIT:
            problems.append("40-hex --ref recorded ref_resolved=%r"
                            % manifest.get("ref_resolved"))
        if "source=arg-sha" not in text:
            problems.append("the pinned run did not print 'source=arg-sha'")

        out = os.path.join(tmp, "branch")
        code, text = run(["--out", out, "--no-paper", "--no-include-imports",
                          "--ref", "main", "--no-resolve", "--tries", "1"])
        if code != 0:
            problems.append("--no-resolve fetch run exited %d" % code)
        with open(os.path.join(out, "_manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest.get("ref_source") != "no-resolve":
            problems.append("--no-resolve recorded ref_source=%r"
                            % manifest.get("ref_source"))
        if manifest.get("ref_resolved") is not None:
            problems.append("--no-resolve claimed a resolved sha %r"
                            % manifest.get("ref_resolved"))

    for rel in PIN_DOCS:
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(path):
            problems.append("pin document missing: %s" % rel)
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            if PINNED_COMMIT not in handle.read():
                problems.append("%s does not name the pinned upstream commit %s"
                                % (rel, PINNED_COMMIT))


def check_workflow(problems):
    if not os.path.exists(WORKFLOW):
        problems.append(".github/workflows/verify.yml is missing")
        return
    with open(WORKFLOW, encoding="utf-8") as handle:
        text = handle.read()
    for needle in ("python -m pytest", "check_repo_encoding.py",
                   "check_check_contract.py", "ruff check", "compileall"):
        if needle not in text:
            problems.append("verify.yml does not run %r" % needle)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quiet", action="store_true",
                        help="print the check table only when it is wrong")
    args = parser.parse_args(argv)

    problems = []
    defined = collect_checks()

    if sorted(defined) != list(range(1, 25)):
        problems.append("check-gap.py defines ids %s; expected exactly C1..C24"
                        % (sorted(defined),))
    for number, entry in sorted(defined.items()):
        if "conflict" in entry:
            problems.append("C%d is recorded under two names: %r / %r"
                            % (number, entry["name"], entry["conflict"]))
        if "stage_conflict" in entry:
            problems.append("C%d is recorded from two stages (%s / %s)"
                            % (number, entry["stage"], entry["stage_conflict"]))
    for stage, expected in EXPECTED_STAGES.items():
        actual = sorted(n for n, e in defined.items() if e["stage"] == stage)
        if actual != expected:
            problems.append("%s owns %s; documents promise C%d..C%d"
                            % (stage, actual, expected[0], expected[-1]))

    files, total, unknown, radar_total, per_id = scan_references(defined)
    for rel, number, token, line in unknown:
        problems.append("%s:%d cites %s, which check-gap.py does not define: %s"
                        % (rel, number, token, line))
    unmentioned = [n for n in sorted(defined) if n not in per_id]

    prove_pin(problems)
    check_workflow(problems)

    if not args.quiet or problems:
        print("checks defined in check-gap.py: %d" % len(defined))
        for number, entry in sorted(defined.items()):
            print("  C%-2d %-22s %-7s %d record site(s)"
                  % (number, entry["name"], entry["stage"], entry["sites"]))
    print("documents: %d file(s), %d reference(s), %d in radar/, %d unknown id(s)"
          % (len(files), total, radar_total, len(unknown)))
    if unmentioned:
        print("note: never cited by any document: %s"
              % ", ".join("C%d" % n for n in unmentioned))
    print("pin: %s @ %s (ref_source=arg-sha, no commits API call)"
          % ("openai/math", PINNED_COMMIT))

    if problems:
        print("")
        for problem in problems:
            print("FAIL " + problem, file=sys.stderr)
        print("%d contract violation(s)" % len(problems), file=sys.stderr)
        return 1
    print("contract: C1..C24 map one-to-one to check-gap.py; every citation exists; "
          "the fetch is pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

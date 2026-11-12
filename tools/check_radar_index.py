#!/usr/bin/env python3
"""Gate: `radar/index.json` still describes the cards in `radar/`.

`scripts/build-radar-index.py` writes the index; this is the gate that keeps the
committed file honest.  It rebuilds the index in memory (no writes, no network,
no subprocess) and compares it with the file on disk, so any of these go red:

  * a card was added but the index was not regenerated (extra card);
  * a card was deleted or renamed and the index still lists it (missing card);
  * a card's title, tags, labels, families, pointers, size or hash changed;
  * a hand edit of `radar/index.json` that no card supports.

The comparison is by value, then by bytes: if the JSON says the right thing but
is formatted differently (key order, indentation, trailing newline), that is
also a failure, because it means someone edited the file instead of rebuilding
it.  The message for every failure names the command that fixes it.

Structural properties are checked on the stored file as well, so a hand-written
index cannot pass by agreeing with itself: required fields present, ids unique,
`path` equal to `radar/<id>.md`, cards ordered by (date, id), every pointer
repository-relative and resolving inside the clone.

Usage:
    python tools/check_radar_index.py
    python tools/check_radar_index.py --quiet    # table only on failure

Exit codes: 0 = the index matches `radar/`; 1 = at least one difference.
"""

import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "scripts", "build-radar-index.py")
INDEX = os.path.join(ROOT, "radar", "index.json")
REBUILD = "python scripts/build-radar-index.py"

ROOT_FIELDS = ("schema", "schema_version", "source", "card_count")
CARD_FIELDS = ("id", "path", "date", "topic", "slug", "title", "tags", "labels",
               "families", "repro", "docs", "related_cards", "bytes", "sha256")
POINTER_FIELDS = ("repro", "docs", "related_cards")
POINTER_PREFIXES = {"repro": ("repro/",), "docs": ("docs/", "progress/"),
                    "related_cards": ("radar/",)}

CARD_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_build_module():
    spec = importlib.util.spec_from_file_location("build_radar_index", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def short(value, limit=100):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) > limit:
        text = text[:limit - 1] + "…"
    return text


def read_stored(problems):
    if not os.path.exists(INDEX):
        problems.append("%s does not exist; run `%s`"
                        % (os.path.relpath(INDEX, ROOT).replace(os.sep, "/"), REBUILD))
        return None, None
    with open(INDEX, "rb") as handle:
        blob = handle.read()
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError as error:
        problems.append("radar/index.json is not UTF-8: %s" % error)
        return None, None
    try:
        return json.loads(text), text
    except ValueError as error:
        problems.append("radar/index.json is not valid JSON: %s" % error)
        return None, None


def check_structure(stored, problems):
    """Structural properties of the stored index, independent of the rebuild."""
    for field in ROOT_FIELDS:
        if field not in stored:
            problems.append("radar/index.json has no %r field" % field)
    cards = stored.get("cards")
    if not isinstance(cards, list):
        problems.append("radar/index.json: 'cards' is not a list")
        return
    if stored.get("card_count") != len(cards):
        problems.append("card_count is %r but the file lists %d card(s)"
                        % (stored.get("card_count"), len(cards)))

    seen = {}
    order = []
    for position, card in enumerate(cards):
        if not isinstance(card, dict):
            problems.append("cards[%d] is not an object" % position)
            continue
        ident = card.get("id")
        if not isinstance(ident, str) or not ident:
            problems.append("cards[%d] has no usable id" % position)
            continue
        if ident in seen:
            problems.append("id %r appears twice (cards[%d] and cards[%d])"
                            % (ident, seen[ident], position))
        seen[ident] = position
        for field in CARD_FIELDS:
            if field not in card:
                problems.append("card %r has no %r field" % (ident, field))
        expected_path = "radar/%s.md" % ident
        if card.get("path") != expected_path:
            problems.append("card %r has path %r, expected %r"
                            % (ident, card.get("path"), expected_path))
        if not CARD_DATE_RE.match(str(card.get("date", ""))):
            problems.append("card %r has date %r, expected YYYY-MM-DD"
                            % (ident, card.get("date")))
        for field in POINTER_FIELDS:
            values = card.get(field)
            if not isinstance(values, list):
                problems.append("card %r: %r is not a list" % (ident, field))
                continue
            for pointer in values:
                if not isinstance(pointer, str):
                    problems.append("card %r: %r holds a non-string" % (ident, field))
                    continue
                if pointer.startswith("/") or ".." in pointer.split("/"):
                    problems.append("card %r: %r is not repository-relative: %r"
                                    % (ident, field, pointer))
                    continue
                if not pointer.startswith(POINTER_PREFIXES[field]):
                    problems.append("card %r: %r points outside its lane: %r"
                                    % (ident, field, pointer))
                    continue
                target = os.path.join(ROOT, pointer.replace("/", os.sep))
                if not os.path.exists(target):
                    problems.append("card %r: %r points at a missing path: %r"
                                    % (ident, field, pointer))
        order.append((card.get("date"), ident))

    if order != sorted(order):
        problems.append("cards are not ordered by (date, id); run `%s`" % REBUILD)


def diff_cards(stored, expected, problems):
    stored_cards = {card.get("id"): card for card in stored.get("cards", [])
                    if isinstance(card, dict) and card.get("id")}
    expected_cards = {card["id"]: card for card in expected["cards"]}

    for ident in sorted(set(stored_cards) - set(expected_cards)):
        problems.append("%s: listed in the index but not a card under radar/ "
                        "(stale entry); run `%s`"
                        % (stored_cards[ident].get("path", ident), REBUILD))
    for ident in sorted(set(expected_cards) - set(stored_cards)):
        problems.append("%s: card exists but is missing from the index; run `%s`"
                        % (expected_cards[ident]["path"], REBUILD))

    for ident in sorted(set(expected_cards) & set(stored_cards)):
        have, want = stored_cards[ident], expected_cards[ident]
        for field in CARD_FIELDS:
            if field not in have:
                continue  # already reported by check_structure
            if have[field] != want[field]:
                problems.append("%s: %r is %s in the index but %s in the card; "
                                "run `%s`" % (want["path"], field, short(have[field]),
                                              short(want[field]), REBUILD))


def diff_root(stored, expected, problems):
    for field in ROOT_FIELDS:
        if field in stored and stored[field] != expected[field]:
            problems.append("radar/index.json: %r is %s, expected %s; run `%s`"
                            % (field, short(stored[field]), short(expected[field]),
                               REBUILD))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quiet", action="store_true",
                        help="print the summary only when there is a problem")
    args = parser.parse_args(argv)

    problems = []
    module = load_build_module()
    expected = module.build_index(ROOT)
    stored, stored_text = read_stored(problems)

    if stored is not None:
        if not isinstance(stored, dict):
            problems.append("radar/index.json is not a JSON object")
        else:
            check_structure(stored, problems)
            diff_root(stored, expected, problems)
            diff_cards(stored, expected, problems)
        if stored_text is not None and module.render(stored) != stored_text:
            problems.append("radar/index.json is not in the generated form "
                            "(key order, indentation or trailing newline differ); "
                            "run `%s`" % REBUILD)

    checked = len(expected["cards"])
    if not args.quiet or problems:
        print("cards under radar/: %d" % checked)
        for card in expected["cards"]:
            print("  %s  %-32s %s"
                  % (card["date"], card["id"], ",".join(card["tags"]) or "-"))
    print("radar-index: %d card(s) checked, %d problem(s)" % (checked, len(problems)))

    if problems:
        print("")
        for problem in problems:
            print("FAIL " + problem, file=sys.stderr)
        print("%d radar index violation(s)" % len(problems), file=sys.stderr)
        return 1
    print("index: radar/index.json matches radar/, %d card(s), pointers resolve"
          % checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

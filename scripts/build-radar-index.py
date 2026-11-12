#!/usr/bin/env python3
"""Build `radar/index.json`, the machine-readable index of the candidate cards.

One card is one markdown file named `radar/<date>-<topic>-<slug>.md` (see
README, "For agents").  Reading nine cards to find out what the repo tracks is
wasteful for a downstream agent, so this script reduces the directory to a
single JSON file: metadata plus pointers only.  No conclusions, no summaries of
the statements, no numbers that are not already in the file name or the card's
own metadata block.

Per card:

  * `id`            file name without the `.md` suffix, unique per card;
  * `path`          repository-relative path (`radar/<id>.md`);
  * `date`          the `YYYY-MM-DD` prefix of the file name;
  * `topic`, `slug` the remaining `-`-separated segments: topic is the first
                    one, slug is the rest joined back with `-`;
  * `title`         the first `# ` heading;
  * `tags`          card kinds found in the title and the metadata block
                    (the lines before the first `---`), from a fixed
                    vocabulary -- see `TAG_RULES` below;
  * `labels`        the `Label: value` lines of that same metadata block,
                    verbatim, so nothing is lost by not shipping the prose;
  * `families`      `openai/math` family numbers cited as 族/家族/family <n>;
  * `repro`, `docs` repository-relative pointers to `repro/**` and
                    `docs/**` + `progress/**`;
  * `related_cards` other cards under `radar/` this one links to;
  * `bytes`, `sha256`  of the card as committed, so the gate can prove that
                    the index describes the current text.

Determinism is a requirement, not a nicety: the same `radar/` must produce the
same bytes, otherwise the gate would flap.  There is no generation timestamp,
no absolute path, no filesystem order, and the JSON is dumped with sorted keys,
two-space indent, `ensure_ascii=False` and one trailing newline.

Usage:
    python scripts/build-radar-index.py
    python scripts/build-radar-index.py --stdout
    python scripts/build-radar-index.py --out /tmp/radar-index.json

Exit codes: 0 = index written; 1 = `radar/` is unusable (see the message).
"""

import argparse
import hashlib
import json
import os
import re
import sys

SCHEMA = "ai-theory-app-radar/radar-index"
SCHEMA_VERSION = 1
CARD_DIR = "radar"
INDEX_NAME = "index.json"

CARD_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$")
LABEL_RE = re.compile(r"^\**([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_/-]{0,11})\**\s*[：:]\s*(.*?)\s*$")
# "族 378" / "家族 266" / "family-378".  Spaces and tabs only: a newline would
# turn a sentence ending in 族 in front of an ordered list item into family 1.
FAMILY_RE = re.compile(r"(?:家族|族|family)[ \t_-]*(\d{1,3})(?![0-9])", re.IGNORECASE)
ROUND_RE = re.compile(r"第[一二三四五六七八九十]+轮")

# Card kinds, matched against the title plus the metadata block.  The list is
# deliberately short: it answers "what sort of card is this", which is what a
# downstream agent needs in order to pick a card, not "what does it conclude".
TAG_RULES = (
    ("executable-recheck", ("可执行复核",)),
    ("statement-card", ("陈述卡",)),
    ("formalization-gap", ("形式化缺口", "形式化差距")),
    ("draft", ("草稿",)),
    ("round-log", ()),  # special-cased: ROUND_RE on the title
)

# A pointer is only a pointer when it starts at a path boundary: `repro/x` in
# prose is one, `lean/docs/378.md` (an upstream path inside a card) is not, and
# neither is `../repro/x` pretending to be its own directory.  The lookbehind
# rejects a match that continues a longer path, the optional `../` chain lets a
# card link to `../repro/...` the way it does from inside `radar/`.
_POINTER_PREFIX = r"(?<![A-Za-z0-9._~/-])(?:\.\./)*("
POINTER_RES = {
    "repro": re.compile(_POINTER_PREFIX + r"repro/[A-Za-z0-9._~/-]+)"),
    "docs": re.compile(_POINTER_PREFIX + r"(?:docs|progress)/[A-Za-z0-9._~/-]+)"),
    "related_cards": re.compile(_POINTER_PREFIX + r"radar/[A-Za-z0-9._~/-]+\.md)"),
}

TRAILING_JUNK = ".,;:)]}>,、。；：）】`'\"*_"
TOP_DIRS = {"repro", "docs", "progress", "radar"}


def card_files(root):
    """Return the sorted card file names under `radar/`."""
    directory = os.path.join(root, CARD_DIR)
    if not os.path.isdir(directory):
        return []
    names = [name for name in os.listdir(directory)
             if name.endswith(".md") and CARD_NAME_RE.match(name)]
    return sorted(names)


def read_card(root, name):
    path = os.path.join(root, CARD_DIR, name)
    with open(path, "rb") as handle:
        blob = handle.read()
    return blob, blob.decode("utf-8")


def metadata_block(text):
    """Return the lines before the first horizontal rule or level-two heading.

    The metadata block is whatever precedes the body.  Most cards separate the
    two with `---`; a few start their body with `## 一、...` and have no rule at
    all, so both markers end the block.  Without the second one, a card without
    a rule would report every `Key: value` line in its body as metadata.
    """
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("---", "***", "___") or stripped.startswith("## "):
            break
        lines.append(line)
    return lines


def split_name(name):
    stem = name[:-len(".md")]
    match = CARD_NAME_RE.match(name)
    date = match.group(1)
    rest = match.group(2)
    parts = rest.split("-")
    topic = parts[0]
    slug = "-".join(parts[1:])
    return stem, date, topic, slug


def clean_pointer(raw):
    pointer = raw.rstrip(TRAILING_JUNK).rstrip("/")
    if not pointer or pointer in TOP_DIRS:
        return None
    if pointer.startswith("/") or ".." in pointer.split("/"):
        return None
    return pointer


def collect_pointers(root, kind, text, self_path):
    """Return the sorted repository-relative pointers of one kind.

    Only paths that exist in this clone are recorded: a card also quotes paths
    that belong to an *upstream* repository (`lean/docs/378.md`, the community
    repo's `docs/SPARSE_CHECKOUT.md`), and those are not pointers from here.
    """
    found = set()
    for match in POINTER_RES[kind].finditer(text):
        pointer = clean_pointer(match.group(1))
        if pointer is None:
            continue
        if kind == "related_cards" and pointer == self_path:
            continue
        target = os.path.join(root, pointer.replace("/", os.sep))
        if not os.path.exists(target):
            continue
        found.add(pointer)
    return sorted(found)


def collect_tags(head):
    tags = []
    for tag, needles in TAG_RULES:
        if tag == "round-log":
            if ROUND_RE.search(head):
                tags.append(tag)
            continue
        if any(needle in head for needle in needles):
            tags.append(tag)
    return sorted(tags)


def collect_labels(block):
    labels = {}
    for line in block:
        match = LABEL_RE.match(line.strip())
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if not value:
            continue
        if key in labels:
            labels[key] = labels[key] + " | " + value
        else:
            labels[key] = value
    return labels


def describe_card(root, name):
    blob, text = read_card(root, name)
    stem, date, topic, slug = split_name(name)
    path = "%s/%s" % (CARD_DIR, name)
    block = metadata_block(text)

    title = ""
    for line in block:
        match = TITLE_RE.match(line)
        if match:
            title = match.group(1)
            break

    head = title + "\n" + "\n".join(block)
    families = sorted({int(n) for n in FAMILY_RE.findall(text) if 0 < int(n) < 1000})

    return {
        "id": stem,
        "path": path,
        "date": date,
        "topic": topic,
        "slug": slug,
        "title": title,
        "tags": collect_tags(head),
        "labels": collect_labels(block),
        "families": families,
        "repro": collect_pointers(root, "repro", text, path),
        "docs": collect_pointers(root, "docs", text, path),
        "related_cards": collect_pointers(root, "related_cards", text, path),
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def build_index(root):
    """Return the index dict for the cards currently under `root/radar/`."""
    cards = [describe_card(root, name) for name in card_files(root)]
    cards.sort(key=lambda card: (card["date"], card["id"]))
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source": "%s/*.md" % CARD_DIR,
        "card_count": len(cards),
        "cards": cards,
    }


def render(index):
    return json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--out", default=None,
                        help="output path (default: <root>/radar/index.json)")
    parser.add_argument("--stdout", action="store_true",
                        help="print the index instead of writing a file")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    if not card_files(root):
        print("radar-index: no card named %s/<date>-<topic>-<slug>.md under %s"
              % (CARD_DIR, root), file=sys.stderr)
        return 1

    index = build_index(root)
    text = render(index)

    if args.stdout:
        sys.stdout.write(text)
        return 0

    out = args.out or os.path.join(root, CARD_DIR, INDEX_NAME)
    out = os.path.abspath(out)
    parent = os.path.dirname(out)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    print("radar-index: %d card(s) -> %s"
          % (index["card_count"], display_path(out, root)))
    return 0


def display_path(path, root):
    """Shorten `path` for the log line, without failing across drives.

    `os.path.relpath` raises ValueError on Windows when the two paths sit on
    different drives; `--out` is allowed to point anywhere, so fall back to the
    absolute path instead of crashing after a successful write.
    """
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())

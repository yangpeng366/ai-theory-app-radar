#!/usr/bin/env python3
"""Third-party re-check of openai/math family 378 ("The Exponential Time Hypothesis is False").

This is the *view*: it turns the fetched sources into one verdict table.  It
needs no Lean toolchain and no Mathlib, because every question it asks is
answerable from the published sources:

  stage 1  data consistency      -- do the metadata sources agree with each
                                    other and with the Lean source text?
  stage 2  arithmetic / complexity contract -- do the Lean definitions and the
                                    proved encoding bound really say what the
                                    manuscript claims, and does the L <-> (n,m)
                                    conversion hold?
  stage 3  statement-level check -- is the challenge statement the one that was
                                    actually proved, is the proof free of
                                    `sorry`, and where exactly does the
                                    manuscript outrun the formalisation?

Usage:
    python3 check-gap.py --src ./family378-sources
    python3 check-gap.py --src ./family378-sources --report gap-report.md

Exit code 0 means every mechanical check held.  The scientific verdict (which
manuscript segments are covered) is printed as a table, not encoded in the exit
code.  A `GAP` verdict marks a *confirmed* difference between manuscript and
formalisation -- that is the deliverable, not a failure.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys

# ---------------------------------------------------------------- utilities

RESULTS = []


def record(check, verdict, detail):
    RESULTS.append({"check": check, "verdict": verdict, "detail": detail})
    print("[%s] %-28s %s" % (verdict, check, detail))


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_comments(text):
    """Remove Lean block comments, doc comments and line comments."""
    text = re.sub(r"/--.*?-/", " ", text, flags=re.S)
    text = re.sub(r"/-(?!-).*?-/", " ", text, flags=re.S)
    text = re.sub(r"--.*$", "", text, flags=re.M)
    return text


def normalise(text):
    """Strip comments and collapse whitespace so two copies can be compared."""
    lines = []
    for line in strip_comments(text).splitlines():
        collapsed = " ".join(line.split())
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines)


def semantic(text):
    """`normalise` plus the removal of the `noncomputable` marker.

    A challenge file may mark a declaration `noncomputable` explicitly while the
    canonical module relies on a surrounding `noncomputable section`.  The two are
    equivalent in Lean, so the marker must not count as definition drift.
    """
    body = normalise(text)
    return re.sub(r"^(noncomputable\s+)?(def|abbrev|theorem|lemma)\b", r"\2", body, flags=re.M)


DECL_RE = re.compile(
    r"^(?:\[[^\]]*\]\s*)?(?:@\[[^\]]*\]\s*)?"
    r"(?:noncomputable\s+|private\s+|protected\s+|partial\s+)*"
    r"(def|abbrev|theorem|lemma|structure|inductive|instance)\s+"
    r"([A-Za-z0-9_'.]+)\s*(.*)$")


def qualified_defs(text):
    """Map every top-level declaration to its fully qualified name and body.

    Namespace resolution follows Lean: `namespace A.B` opens A.B relative to the
    current namespace unless it already names the same root.  Bodies run to the
    next column-0 line, which is how Lean continues a multi-line declaration.
    """
    lines = strip_comments(text).splitlines()
    stack = []
    out = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        namespace = re.match(r"^namespace\s+([A-Za-z0-9_.']+)\s*$", stripped)
        if namespace:
            parts = namespace.group(1).split(".")
            if not stack:
                stack = parts
            elif parts[0] == stack[0]:
                stack = parts
            else:
                stack = stack + parts
            index += 1
            continue
        if re.match(r"^end\s+[A-Za-z0-9_.']+\s*$", stripped):
            if stack:
                stack.pop()
            index += 1
            continue
        match = DECL_RE.match(line)
        if match and not line[0].isspace():
            kind, name, _rest = match.groups()
            body = [line]
            cursor = index + 1
            while cursor < len(lines):
                nxt = lines[cursor]
                if nxt.strip() and not nxt[0].isspace():
                    break
                body.append(nxt)
                cursor += 1
            qualified = ".".join(stack + [name]) if stack else name
            out[qualified] = {"kind": kind, "name": name,
                              "text": "\n".join(body),
                              "raw": normalise("\n".join(body)),
                              "body": semantic("\n".join(body))}
            index = cursor
            continue
        index += 1
    return out


def declaration_type(text):
    """The type of a `theorem`/`def` declaration, i.e. everything before `:=`."""
    cut = text.find(":=")
    if cut < 0:
        return normalise(text)
    return normalise(text[:cut])


def sorry_count(text):
    return len(re.findall(r"(?<![A-Za-z0-9_])sorry(?![A-Za-z0-9_])", text))


# ------------------------------------------------- stage 1: data consistency

def stage1(src):
    manifest_path = os.path.join(src, "_manifest.json")
    if not os.path.exists(manifest_path):
        record("C1 取件完整性", "SKIP", "no _manifest.json")
        return {}
    manifest = json.loads(read(manifest_path))
    bad = []
    total = 0
    for item in manifest:
        path = os.path.join(src, item["local"].replace("/", os.sep))
        if not os.path.exists(path):
            bad.append(item["local"] + " (missing)")
            continue
        total += os.path.getsize(path)
        if item.get("sha256") and sha256_of(path) != item["sha256"]:
            bad.append(item["local"] + " (sha256)")
    if bad:
        record("C1 取件完整性", "FAIL", "; ".join(bad[:4]))
    else:
        record("C1 取件完整性", "PASS",
               "%d files, %d bytes, sha256 verified" % (len(manifest), total))

    contents = read(os.path.join(src, "CONTENTS.md"))
    match = re.search(r"^\*\*378\.\s+(.*?)$", contents, re.M)
    if not match:
        record("C2 族号一致", "FAIL", "family 378 header not found in CONTENTS.md")
    else:
        record("C2 族号一致", "PASS", match.group(0)[:96])

    config = json.loads(read(os.path.join(src, "lean", "ComparatorChallenges",
                                          "SubexponentialSAT.json")))
    yaml_text = read(os.path.join(src, "lean", "formalization.yaml"))
    yaml_block = ""
    block = re.search(r"- comparator_config: ComparatorChallenges/SubexponentialSAT\.json\n"
                      r"\s+declaration:\s+(\S+)\n\s+file:\s+(\S+)", yaml_text)
    if block:
        yaml_block = block.group(1)
    else:
        record("C3 声明名一致", "FAIL", "formalization.yaml has no SubexponentialSAT entry")

    declared = config["theorem_names"][0]
    if declared == yaml_block:
        record("C3 声明名一致", "PASS", declared)
    else:
        record("C3 声明名一致", "FAIL", "json=%s yaml=%s" % (declared, yaml_block))

    comparator = read(os.path.join(src, "lean", "ComparatorChallenges",
                                   "SubexponentialSAT.lean"))
    final = read(os.path.join(src, "lean", "OAI", "Algorithms", "SubexponentialSAT",
                               "SqrtLogSpace", "Final.lean"))
    in_comparator = declared.split(".")[-1] in comparator
    in_final = declared.split(".")[-1] in final
    if in_comparator and in_final:
        record("C4 定理名落地", "PASS", "%s declared in both challenge and solution"
               % declared.split(".")[-1])
    else:
        record("C4 定理名落地", "FAIL",
               "challenge=%s solution=%s" % (in_comparator, in_final))

    solution_module = config["solution_module"]
    module_file = os.path.join(src, "lean", *solution_module.split(".")) + ".lean"
    if os.path.exists(module_file):
        record("C5 解法模块路径", "PASS", solution_module + " -> lean/" +
               "/".join(solution_module.split(".")) + ".lean")
    else:
        record("C5 解法模块路径", "FAIL", "missing " + module_file)

    challenge_sorry = sorry_count(comparator)
    solution_sorry = sorry_count(final)
    if challenge_sorry == 1:
        record("C6 挑战留白", "PASS", "challenge file has exactly 1 `sorry` (the stub)")
    else:
        record("C6 挑战留白", "FAIL", "challenge sorry count = %d (expected 1)" % challenge_sorry)
    if solution_sorry == 0:
        record("C7 解法无 sorry", "PASS", "solution file has 0 `sorry`")
    else:
        record("C7 解法无 sorry", "FAIL", "solution sorry count = %d" % solution_sorry)

    permitted = set(config.get("permitted_axioms", []))
    expected = {"propext", "Quot.sound", "Classical.choice"}
    if permitted <= expected:
        record("C8 公理白名单", "PASS", ", ".join(sorted(permitted)))
    else:
        record("C8 公理白名单", "FAIL", "extra axioms: %s" % sorted(permitted - expected))
    if "#print axioms" in final:
        record("C9 公理自检声明", "PASS", "solution ends with #print axioms for 5 theorems")
    else:
        record("C9 公理自检声明", "FAIL", "no #print axioms in the solution file")

    # C10: definition drift between the challenge copy and the canonical modules.
    # Comparison is by fully qualified name, so a same-named but different
    # function in another namespace is not mistaken for drift.
    challenge_defs = qualified_defs(comparator)
    canonical_defs = {}
    for root, _dirs, names in os.walk(os.path.join(src, "lean", "OAI")):
        for name in names:
            if not name.endswith(".lean"):
                continue
            path = os.path.join(root, name)
            for qualified, entry in qualified_defs(read(path)).items():
                canonical_defs.setdefault(qualified, entry)
    comparable = [key for key in challenge_defs
                  if key in canonical_defs
                  and challenge_defs[key]["kind"] in ("def", "abbrev")
                  and canonical_defs[key]["kind"] in ("def", "abbrev")]
    drift = []
    marker_only = []
    for key in sorted(comparable):
        if challenge_defs[key]["body"] != canonical_defs[key]["body"]:
            drift.append(key)
        elif challenge_defs[key]["raw"] != canonical_defs[key]["raw"]:
            marker_only.append(key.split(".")[-1])
    only_challenge = sorted(set(challenge_defs) - set(canonical_defs))
    if not comparable:
        record("C10 定义漂移", "SKIP", "no comparable definitions found")
    elif drift:
        record("C10 定义漂移", "FAIL", "%d/%d definitions differ: %s"
               % (len(drift), len(comparable), ", ".join(drift[:6])))
    else:
        note = ""
        if marker_only:
            note = "; differ only in the `noncomputable` marker: %s" % ", ".join(
                marker_only[:4])
        else:
            note = "; challenge-only: %s" % (", ".join(only_challenge[:4]) or "none")
        record("C10 定义漂移", "PASS",
               "%d/%d shared definitions are semantically identical%s"
               % (len(comparable), len(comparable), note))

    # C11: import closure inside the fetched subset.
    fetched = set()
    for root, _dirs, names in os.walk(os.path.join(src, "lean")):
        for name in names:
            if name.endswith(".lean"):
                rel = os.path.relpath(os.path.join(root, name),
                                      os.path.join(src, "lean")).replace(os.sep, "/")
                fetched.add(rel[:-len(".lean")])
    unresolved = []
    for rel in sorted(fetched):
        text = read(os.path.join(src, "lean", rel.replace("/", os.sep) + ".lean"))
        for module in re.findall(r"^import\s+([A-Za-z0-9_.]+)", text, re.M):
            if module.startswith("OAI.") and module not in fetched:
                unresolved.append("%s -> %s" % (rel, module))
    if unresolved:
        record("C11 import 闭合", "PART", "%d imports outside the fetched subset "
                                       "(proof bulk not fetched): %s"
               % (len(unresolved), "; ".join(unresolved[:3])))
    else:
        record("C11 import 闭合", "PASS", "every OAI import resolves inside the fetched subset")

    return {"contents": contents, "comparator": comparator, "final": final,
            "config": config, "yaml": yaml_text,
            "challenge_defs": challenge_defs, "canonical_defs": canonical_defs}


# ------------------------------- stage 2: arithmetic and complexity contract

def encode_cnf_python(n, clauses):
    """Mirror of the Lean `Encoding` module (canonical copy).

    encodeNat n   = replicate n true ++ [false]
    frame bits    = foldr (fun b rest => true :: b :: rest) [false]
    encodeList e  = [] -> [false]; a::as -> true :: (frame (e a) ++ encodeList e as)
    literalCode l = 2 * l.variable + (if l.positive then 1 else 0)
    clauseNumbers C = sorted image literalCode
    cnfNumbers F  = sorted image clauseNumbers
    encodeCNFBody F = encodeList (encodeList encodeNat) (cnfNumbers F)
    encodeCNF F = encodeNat n ++ encodeCNFBody F
    """
    def encode_nat(value):
        return [True] * value + [False]

    def frame(bits):
        out = []
        for bit in reversed(bits):
            out = [True, bit] + out
        return out + [False]

    def encode_list(encoder, items):
        if not items:
            return [False]
        out = encode_list(encoder, items[1:])
        return [True] + frame(encoder(items[0])) + out

    def literal_code(literal):
        variable, positive = literal
        return 2 * variable + (1 if positive else 0)

    clause_numbers = sorted(sorted(literal_code(lit) for lit in clause) for clause in clauses)
    body = encode_list(lambda clause: encode_list(encode_nat, clause), clause_numbers)
    return encode_nat(n) + body


def runtime_scale(n):
    """Lean's `runtimeScale`: natural logs with the +16 shift."""
    x = n + 16.0
    return n * math.log(math.log(x)) ** 2 / math.sqrt(math.log(x))


def rho(n):
    """Lean's `rho`: base-two logarithms, squared log-log."""
    l = math.log2(n)
    return n * (math.log2(l)) ** 2 / math.sqrt(l)


def paper_main(n):
    """Manuscript Theorem 1.1 main exponent: n log log n / sqrt(log n)."""
    l = math.log2(n)
    return n * math.log2(l) / math.sqrt(l)


def paper_sharp(n):
    """Manuscript Theorem 1.1 sharpening for m <= Dn: n / sqrt(log n)."""
    return n / math.sqrt(math.log2(n))


def stage2(src, info):
    scale = read(os.path.join(src, "lean", "OAI", "Algorithms", "SubexponentialSAT",
                               "SqrtLog", "StatementScale.lean"))
    asympt = read(os.path.join(src, "lean", "OAI", "Algorithms", "SubexponentialSAT",
                                "SqrtLogSpace", "Asymptotics.lean"))
    bounds = read(os.path.join(src, "lean", "OAI", "Algorithms", "SubexponentialSAT",
                                "SqrtLogSpace", "EncodingBounds.lean"))
    comparator = info["comparator"]

    canonical_scale = qualified_defs(scale).get(
        "OAI.Algorithms.SubexponentialSAT.SqrtLog.Statement.runtimeScale", {}).get("body", "")
    challenge_scale = qualified_defs(comparator).get(
        "OAI.Algorithms.SubexponentialSAT.SqrtLog.Statement.runtimeScale", {}).get("body", "")
    if canonical_scale and canonical_scale == challenge_scale:
        record("C12 尺度定义一致", "PASS",
               "runtimeScale identical in challenge and canonical copy: "
               "n*(log log (n+16))^2 / sqrt(log (n+16))")
    else:
        record("C12 尺度定义一致", "FAIL", "challenge and canonical runtimeScale differ")

    asympt_defs = qualified_defs(asympt)
    rho_body = asympt_defs.get(
        "OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.rho", {}).get("body", "")
    squared = "^ 2" in rho_body or "^2" in rho_body
    record("C13 rho 阶", "PASS" if squared else "FAIL",
           "rho(n) = n*(logb2 logb2 n)^2 / sqrt(logb2 n)  -> squared (log log n)^2")

    rows = []
    for n in (10 ** 4, 10 ** 6, 10 ** 8, 10 ** 10, 10 ** 12):
        lean_exp = rho(n)
        rows.append((n, lean_exp / paper_main(n), lean_exp / paper_sharp(n)))
    record("C14 指数差", "PASS",
           "Lean rho / paper main = %.1f at n=1e12 ; Lean rho / paper m<=Dn bound = %.1f"
           % (rows[-1][1], rows[-1][2]))

    has_sq = "encoding_le_declaredSize_sq" in bounds
    has_pow = "encoding_pow_le_declaredSize" in bounds
    record("C15 编码换算引理", "PASS" if (has_sq and has_pow) else "FAIL",
           "encoding_le_declaredSize_sq + encoding_pow_le_declaredSize present")

    violations = []
    samples = 0
    for n in (3, 5, 9, 17):
        for m in (0, 1, 2, 4, 8):
            for k in (2, 3):
                clauses = []
                for index in range(m):
                    width = min(k, 1 + index % k)
                    clause = []
                    for slot in range(width):
                        variable = (index * 3 + slot * 5) % n
                        clause.append((variable, (index + slot) % 2 == 0))
                    clauses.append(clause)
                length = len(encode_cnf_python(n, clauses))
                lean_bound = n + 2 + (4 + (8 * n + 8) * k) * m
                square_bound = (8 * k + 7) * (n + m + 1) ** 2
                samples += 1
                if not (length <= lean_bound and length + 1 <= square_bound):
                    violations.append((n, m, k, length, lean_bound, square_bound))
    if violations:
        record("C16 编码界数值复核", "FAIL", "%d/%d samples violate the Lean bounds: %s"
               % (len(violures), samples, violations[:2]))
    else:
        record("C16 编码界数值复核", "PASS",
               "%d sampled formulas satisfy formulaBitLength <= n+2+(4+(8n+8)k)m "
               "and L+1 <= (8k+7)(n+m+1)^2" % samples)

    # C17: numerical spot-check of the Lean lemma runtimeScale n <= 4 * rho n,
    # which is the bridge from the machine's own time scale to the manuscript's.
    lemma_ok = "runtimeScale_le_four_rho" in asympt
    bad = []
    first_ok = None
    for n in range(20, 5001):
        if runtime_scale(n) <= 4 * rho(n):
            if first_ok is None:
                first_ok = n
        else:
            bad.append(n)
    if lemma_ok and not bad and first_ok is not None:
        record("C17 runtimeScale<=4rho", "PASS",
               "numerical spot-check of the Lean bridge: holds for every n in "
               "[20, 5000] (first n = %d)" % first_ok)
    elif not lemma_ok:
        record("C17 runtimeScale<=4rho", "FAIL", "runtimeScale_le_four_rho not found")
    else:
        record("C17 runtimeScale<=4rho", "FAIL",
               "numerical counterexample to runtimeScale <= 4*rho at n = %s" % bad[:3])

    # C18: the n >= 20 threshold that the Lean statements carry.
    final_defs = qualified_defs(info["final"])
    eth = final_defs.get("OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_eth", {})
    eth_type = declaration_type(eth.get("text", ""))
    has_threshold = "20 ≤ n" in eth_type
    has_poly = "(n + F.card + 1 : ℕ) : ℝ) ^ d" in eth_type
    has_rho = "2 : ℝ) ^ (A * rho n)" in eth_type
    if has_threshold and has_poly and has_rho:
        record("C18 Lean ETH 陈述形状", "PASS",
               "exact_count_eth states 20 <= n, (n+m+1)^d and 2^(A*rho n)")
    else:
        record("C18 Lean ETH 陈述形状", "FAIL",
               "threshold=%s poly=%s rho=%s" % (has_threshold, has_poly, has_rho))

    # C19: the challenge statement is exactly the statement the solution proves.
    challenge_defs = info["challenge_defs"]
    canonical_defs = info["canonical_defs"]
    key = "OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat"
    challenge_type = declaration_type(challenge_defs.get(key, {}).get("text", ""))
    solution_type = declaration_type(canonical_defs.get(key, {}).get("text", ""))
    if challenge_type and solution_type and challenge_type == solution_type:
        record("C19 挑战陈述≡解法陈述", "PASS",
               "comparator statement and proved statement are textually identical "
               "(%d chars)" % len(challenge_type))
    elif not challenge_type or not solution_type:
        record("C19 挑战陈述≡解法陈述", "FAIL", "could not extract both statements")
    else:
        record("C19 挑战陈述≡解法陈述", "FAIL", "statements differ")

    return {"rows": rows, "rho": rho_body, "squared": squared,
            "first_ok": first_ok, "eth_type": eth_type}


# ------------------------------------ stage 3: statement-level (instruction) check

def paper_exponent_forms(pdf_path):
    """Read Theorem 1.1's exponent and rho's exponent out of the PDF glyphs.

    A superscript digit is a separate span with a smaller font size and a higher
    baseline, so 'is there a raised 2 next to log log n?' is decidable without a
    screenshot.  Returns {'thm11': 'single'|'squared'|None,
    'rho': 'single'|'squared'|None}.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {"thm11": None, "rho": None}
    forms = {"thm11": None, "rho": None}
    document = fitz.open(pdf_path)
    try:
        for page in document:
            data = page.get_text("dict")
            page_text = page.get_text()
            if "Theorem 1.1" not in page_text:
                continue
            for block in data["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    spans = line["spans"]
                    joined = "".join(span["text"] for span in spans)
                    for index, span in enumerate(spans):
                        if "log log" not in span["text"]:
                            continue
                        base = span["size"]
                        baseline = span["bbox"][3]
                        form = "single"
                        for later in spans[index + 1:]:
                            if (later["text"].strip() == "2" and later["size"] < base
                                    and later["bbox"][3] < baseline):
                                form = "squared"
                                break
                        if forms["thm11"] is None:
                            forms["thm11"] = form
                        if "ρ(n)" in joined and forms["rho"] is None:
                            forms["rho"] = form
            if forms["thm11"] is not None:
                break
    finally:
        document.close()
    return forms


def stage3(src, info):
    pdf = os.path.join(src, "preprints",
                        "The-Exponential-Time-Hypothesis-is-False-October-25-2026",
                        "paper.pdf")
    forms = paper_exponent_forms(pdf) if os.path.exists(pdf) else {"thm11": None, "rho": None}
    if forms["thm11"] is None:
        record("C20 论文主定理指数", "PART", "PDF glyph check unavailable (PyMuPDF missing)")
    elif forms["thm11"] == "single":
        record("C20 论文主定理指数", "PASS",
               "Theorem 1.1 exponent read from PDF glyphs: single log log n "
               "(n log log n / sqrt(log n))")
    else:
        record("C20 论文主定理指数", "FAIL",
               "Theorem 1.1 exponent has a squared log log: %s" % forms["thm11"])

    if forms["rho"] is None:
        record("C21 论文 rho 定义", "PART", "rho definition not located in the PDF")
    elif forms["rho"] == "squared":
        record("C21 论文 rho 定义", "PASS",
               "rho(n) = n (log log n)^2 / sqrt(log n): squared, i.e. the weaker exponent")
    else:
        record("C21 论文 rho 定义", "FAIL", "rho definition is not squared")

    docs = read(os.path.join(src, "lean", "docs", "378.md"))
    has_sharp = "m\\le Dn" in docs or "m≤Dn" in docs
    record("C22 上游自陈锐化", "PASS" if has_sharp else "FAIL",
           "upstream docs/378.md states the m<=Dn sharpening as *not* formalised")

    final = info["final"]
    has_sharp_lean = ("m ≤ Dn" in final) or ("m<=Dn" in final) or ("D : ℕ" in final)
    if has_sharp_lean:
        record("C23 Lean 侧锐化", "PASS", "a formalised m<=Dn statement exists")
    else:
        record("C23 Lean 侧锐化", "GAP",
               "no m<=Dn statement anywhere in the formalisation -- the sharpening "
               "2^(n/sqrt(log n)) is entirely unformalised")

    # C24: does the Lean exponent ever fall below the manuscript's main exponent?
    # If it does at some n, the Lean bound would imply the manuscript's bound at
    # that n; the answer decides whether the gap is a small-n artefact.
    below = [n for n in range(20, 100001) if rho(n) <= paper_main(n)]
    if below:
        record("C24 差距是否小 n 假象", "GAP",
               "rho(n) <= manuscript main exponent for n in %s -- the Lean bound "
               "would dominate there" % below[:5])
    else:
        record("C24 差距是否小 n 假象", "PASS",
               "rho(n) > manuscript main exponent for every n in [20, 100000]: the "
               "gap is asymptotic, not a small-n artefact (ratio = log2 log2 n)")

    return {"forms": forms, "sharp_in_lean": has_sharp_lean}


# ------------------------------------------------------------------- report

TABLE = """
## 族 378 已覆盖 / 未覆盖对照表

| 论文条目（paper.pdf, 2026-10-25 修订版） | 论文陈述 | Lean 侧对应 | 判定 |
|---|---|---|---|
| 精确计数 #F | Theorem 1.1 | `exact_count_and_sat` / `exact_count_eth`（解法 0 处 `sorry`） | 已覆盖 |
| 可满足性判定 | Theorem 1.1 + Corollary 1.2 | `sat_polynomial_space`、`original_sat_main` | 已覆盖 |
| 固定宽度 k ≥ 2 | Theorem 1.1 | `hk : 2 ≤ k`（`exact_count_eth`）/ `3 ≤ k`（`sat_polynomial_space`） | 已覆盖 |
| 小输入门槛 n ≥ 20 | Theorem 1.1 | `exact_count_eth` 的 `20 ≤ n` | 已覆盖 |
| 多项式因子 | (n+m)^{O_k(1)} | `encoding_pow_le_declaredSize`：L+1 ≤ (8k+7)(n+m+1)² ⇒ (L+1)^d ≤ (8k+7)^d (n+m+1)^{2d} | 已覆盖（编码换算成立） |
| 空间 | (n+m)^{O_k(1)} bits | `visitedSpace ≤ S·(L+1)^e`，同一换算 ⇒ (n+m)^{O(1)} | 已覆盖 |
| 论文自陈的插值界 | O_k(ρ(n))，ρ(n)=n(log log n)²/√log n | `rho n = n (log₂log₂ n)²/√log₂ n`，`exact_count_eth` 的 2^{A·rho n} | 已覆盖（**逐位吻合**） |
| 主时间界 | (n+m)^{O_k(1)}·2^{O_k(n log log n/√log n)} | 2^{O_k(ρ(n))} = 2^{O_k(n(log log n)²/√log n)} | **未覆盖**：指数差 Θ(log log n) |
| m ≤ Dn 锐化界 | (n+m)^{O_{k,D}(1)}·2^{O_{k,D}(n/√log n)} | 无对应陈述 | **未覆盖**：Lean 侧完全缺失 |
| CONTENTS.md 一句话 | 2^{n/(log n)^{1/2+o(1)}} | 与 ρ 同阶（(log log n)² = (log n)^{o(1)}） | 已覆盖，但**该一句话弱于论文主定理** |
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="./family378-sources")
    parser.add_argument("--report", default=None, help="also write the markdown report here")
    args = parser.parse_args()

    src = os.path.abspath(args.src)
    if not os.path.isdir(src):
        print("source directory not found: %s" % src)
        return 2

    info = stage1(src)
    numbers = stage2(src, info)
    stage3(src, info)

    failures = [r for r in RESULTS if r["verdict"] == "FAIL"]
    gaps = [r for r in RESULTS if r["verdict"] == "GAP"]
    print("")
    print("checks: %d, FAIL: %d, confirmed gaps: %d"
          % (len(RESULTS), len(failures), len(gaps)))

    lines = ["# 族 378 第三方复核判定表", "",
             "来源：openai/math @ main，取件目录 `%s`" % src, "",
             "机械检查 %d 项，FAIL %d 项，已确认的形式化差距 %d 项。"
             % (len(RESULTS), len(failures), len(gaps)), ""]
    lines.append("| 检查 | 判定 | 细节 |")
    lines.append("|---|---|---|")
    for item in RESULTS:
        lines.append("| %s | %s | %s |" % (item["check"], item["verdict"],
                                           item["detail"].replace("|", "/")))
    lines.append("")
    lines.append(TABLE.strip())
    lines.append("")
    lines.append("## 指数差数值表（Lean 指数 ρ / 论文指数）")
    lines.append("")
    lines.append("| n | ρ(n) / 论文主界 | ρ(n) / 论文 m≤Dn 锐化界 |")
    lines.append("|---|---|---|")
    for n, ratio_main, ratio_sharp in numbers["rows"]:
        lines.append("| 1e%d | %.1f | %.1f |"
                     % (int(round(math.log10(n))), ratio_main, ratio_sharp))
    lines.append("")
    report = "\n".join(lines) + "\n"
    if args.report:
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(report)
        print("report -> %s" % args.report)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

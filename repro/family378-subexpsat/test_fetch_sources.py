"""Offline tests for the import-closure part of fetch-sources.py.

No network: ``fetch_one`` is replaced by a fake that serves an in-memory dict of
Lean sources and records every request, so recursion, de-duplication, prefix
filtering, the --max-modules cap and failure reporting are all observable.

Run from the repository root:
    python -m pytest repro/family378-subexpsat -q
"""

import base64
import datetime
import hashlib
import http.client
import importlib.util
import io
import json
import os
import urllib.error

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "fetch-sources.py")


def _load():
    spec = importlib.util.spec_from_file_location("fetch_sources", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fs = _load()


# --------------------------------------------------------------- test helpers

def write_lean(root, module, text):
    rel = module.replace(".", "/") + ".lean"
    path = os.path.join(root, "lean", rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return "lean/" + rel


def install_fake(monkeypatch, sources, calls, fail=()):
    """Replace fetch_one with an offline fake; sources maps remote path -> text."""

    def _fetch(remote, local, out_dir, timeout=240, tries=4, ref=None):
        calls.append(remote)
        target = os.path.join(out_dir, local.replace("/", os.sep))
        if remote in fail or remote not in sources:
            return {"remote": remote, "local": local, "bytes": None,
                    "sha256": None, "channel": None,
                    "errors": ["fake: 404"]}
        blob = sources[remote].encode("utf-8")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(blob)
        return {"remote": remote, "local": local, "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(), "channel": "fake"}

    monkeypatch.setattr(fs, "fetch_one", _fetch)


def quiet(*_args):
    return None


# ------------------------------------------------------------- import parsing

def test_parse_imports_handles_lean_variants():
    text = (
        "import OAI.A OAI.B\n"
        "public import OAI.C\n"
        "meta import all OAI.D\n"
        "import Mathlib.Tactic -- trailing note\n"
        "/- import OAI.Ghost -/\n"
        "def x := 1\n"
    )
    assert fs.parse_imports(text) == [
        "OAI.A", "OAI.B", "OAI.C", "OAI.D", "Mathlib.Tactic"]


# ------------------------------------------------------------ closure walking

def test_closure_fetches_second_level_dependency(tmp_path, monkeypatch):
    root = str(tmp_path)
    write_lean(root, "OAI.A", "import OAI.B\n")
    sources = {"lean/OAI/B.lean": "import OAI.C\n", "lean/OAI/C.lean": "def c := 1\n"}
    calls = []
    install_fake(monkeypatch, sources, calls)
    manifest = []

    result = fs.close_imports(root, manifest, max_modules=10, timeout=1, tries=1,
                              log=quiet)

    assert calls == ["lean/OAI/B.lean", "lean/OAI/C.lean"]
    assert result["added"] == 2
    assert result["failed"] == []
    assert result["remaining"] == []
    assert result["truncated"] is False
    assert result["complete"] is True
    assert [record["module"] for record in manifest] == ["OAI.B", "OAI.C"]
    assert [record["origin"] for record in manifest] == ["import", "import"]
    assert manifest[0]["imported_by"] == ["OAI.A"]
    assert manifest[1]["imported_by"] == ["OAI.B"]
    assert os.path.exists(os.path.join(root, "lean", "OAI", "C.lean"))


def test_closure_does_not_refetch_modules_already_on_disk(tmp_path, monkeypatch):
    root = str(tmp_path)
    write_lean(root, "OAI.A", "import OAI.B\n")
    write_lean(root, "OAI.B", "import OAI.C\n")  # already a seed file
    sources = {"lean/OAI/C.lean": "def c := 1\n"}
    calls = []
    install_fake(monkeypatch, sources, calls)

    result = fs.close_imports(root, [], max_modules=10, timeout=1, tries=1,
                              log=quiet)

    assert calls == ["lean/OAI/C.lean"]
    assert result["added"] == 1
    assert result["complete"] is True


def test_closure_ignores_non_oai_prefixes(tmp_path, monkeypatch):
    root = str(tmp_path)
    write_lean(root, "OAI.A", "import Mathlib.Tactic\nimport Lean.Elab.Command\n"
                             "import OAI.B\n")
    sources = {"lean/OAI/B.lean": "def b := 1\n"}
    calls = []
    install_fake(monkeypatch, sources, calls)

    result = fs.close_imports(root, [], max_modules=10, timeout=1, tries=1,
                              log=quiet)

    assert calls == ["lean/OAI/B.lean"]
    assert result["added"] == 1


def test_closure_truncation_is_visible(tmp_path, monkeypatch):
    root = str(tmp_path)
    write_lean(root, "OAI.A", "import OAI.B OAI.C OAI.D\n")
    sources = {name: "def x := 1\n" for name in
               ("lean/OAI/B.lean", "lean/OAI/C.lean", "lean/OAI/D.lean")}
    calls = []
    install_fake(monkeypatch, sources, calls)

    result = fs.close_imports(root, [], max_modules=1, timeout=1, tries=1,
                              log=quiet)

    assert result["added"] == 1
    assert result["truncated"] is True
    assert result["complete"] is False
    assert result["remaining"] == ["OAI.C", "OAI.D"]
    assert len(calls) == 1


def test_closure_failures_land_in_failed_list(tmp_path, monkeypatch):
    root = str(tmp_path)
    write_lean(root, "OAI.A", "import OAI.B\nimport OAI.C\n")
    sources = {}
    calls = []
    install_fake(monkeypatch, sources, calls,
                 fail=("lean/OAI/B.lean", "lean/OAI/C.lean"))
    manifest = []

    result = fs.close_imports(root, manifest, max_modules=10, timeout=1, tries=1,
                              log=quiet)

    assert [entry["module"] for entry in result["failed"]] == ["OAI.B", "OAI.C"]
    assert result["failed"][0]["errors"] == ["fake: 404"]
    assert result["added"] == 0
    assert result["complete"] is False
    assert result["remaining"] == []
    assert manifest == []  # failed fetches never claim a file in the manifest
    assert not os.path.exists(os.path.join(root, "lean", "OAI", "B.lean"))


# ------------------------------------------------------- CLI wiring / exit code

def test_main_default_runs_closure_and_writes_manifest(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    sources = {seed: "import OAI.B\n", "lean/OAI/B.lean": "def b := 1\n"}
    install_fake(monkeypatch, sources, [])
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-resolve"])
    text = capsys.readouterr().out

    assert code == 0
    assert "seed: 1/1 files" in text
    assert "closure: complete (1 file(s) added" in text
    assert "fetched 2/2 files" in text
    manifest = json.load(open(os.path.join(out, "_manifest.json"), encoding="utf-8"))
    assert [record["origin"] for record in manifest["files"]] == ["seed", "import"]
    assert manifest["files"][0]["local"] == seed
    closure = json.load(open(os.path.join(out, "_closure.json"), encoding="utf-8"))
    assert closure["status"] == "complete"
    assert closure["complete"] is True
    assert closure["imported_files"] == 1


def test_main_truncation_exits_2(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    sources = {seed: "import OAI.B\nimport OAI.C\n",
               "lean/OAI/B.lean": "def b := 1\n",
               "lean/OAI/C.lean": "def c := 1\n"}
    install_fake(monkeypatch, sources, [])
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--max-modules", "1", "--no-resolve"])
    text = capsys.readouterr().out

    assert code == 2
    assert "closure: PARTIAL (truncated at --max-modules=1" in text
    closure = json.load(open(os.path.join(out, "_closure.json"), encoding="utf-8"))
    assert closure["status"] == "truncated"
    assert closure["not_fetched"] == ["OAI.C"]
    # the file that was fetched is still pinned in the manifest
    manifest = json.load(open(os.path.join(out, "_manifest.json"), encoding="utf-8"))
    assert [record["origin"] for record in manifest["files"]] == ["seed", "import"]


def test_main_failed_import_exits_1(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    sources = {seed: "import OAI.B\n"}
    install_fake(monkeypatch, sources, [], fail=("lean/OAI/B.lean",))
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-resolve"])
    text = capsys.readouterr().out

    assert code == 1
    assert "closure: PARTIAL" in text
    assert "FAILED    lean/OAI/B.lean" in text
    closure = json.load(open(os.path.join(out, "_closure.json"), encoding="utf-8"))
    assert closure["status"] == "partial"
    assert [entry["module"] for entry in closure["failed"]] == ["OAI.B"]


def test_main_seed_only_is_flagged_as_skipped(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    sources = {seed: "import OAI.B\n"}
    calls = []
    install_fake(monkeypatch, sources, calls)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports", "--no-resolve"])
    text = capsys.readouterr().out

    assert code == 0
    assert calls == [seed]
    assert "closure: skipped" in text
    closure = json.load(open(os.path.join(out, "_closure.json"), encoding="utf-8"))
    assert closure["status"] == "skipped"
    assert closure["complete"] is False


# ------------------------------------------- channels (jsdelivr -> raw -> api)

LEAN = b"import OAI.B\n\ntheorem t : True := trivial\n"
HTML_PAGE = (b"<!DOCTYPE html><html><head><title>429 Too Many Requests</title>"
             b"</head><body>rate limited</body></html>")


class FakeResponse:
    """Just enough of http.client.HTTPResponse for urlopen's context protocol."""

    def __init__(self, body, headers=None, status=200):
        self._body = body
        self.headers = headers or {"X-RateLimit-Remaining": "55"}
        self.status = status

    def read(self, amount=None):
        return self._body if amount is None else self._body[:amount]

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def close(self):
        return None


class TruncatedResponse(FakeResponse):
    """A 200 whose body stops before Content-Length; urllib raises IncompleteRead."""

    def __init__(self, partial_bytes, expected):
        FakeResponse.__init__(self, b"")
        self._partial = b"x" * partial_bytes
        self._expected = expected

    def read(self, amount=None):
        raise http.client.IncompleteRead(self._partial, self._expected)


def install_transport(monkeypatch, handler):
    """Monkeypatch urllib.request.urlopen and record every request."""
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append({"url": request.full_url,
                      "accept": request.get_header("Accept"),
                      "auth": request.get_header("Authorization")})
        result = handler(request.full_url, request.get_header("Accept"))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(fs.urllib.request, "urlopen", fake_urlopen)
    return calls


def contents_payload(blob, size=None, encoding="base64"):
    return json.dumps({
        "type": "file",
        "size": len(blob) if size is None else size,
        "encoding": encoding,
        "content": base64.b64encode(blob).decode("ascii") if blob else "",
        "sha": "0" * 40,
    }).encode("utf-8")


def channel_of(url):
    if "cdn.jsdelivr.net" in url:
        return "jsdelivr"
    if "raw.githubusercontent.com" in url:
        return "raw"
    if "api.github.com" in url:
        return "api-contents"
    raise AssertionError("unexpected url %s" % url)


def test_three_channel_degradation_jsdelivr_timeout_raw_404_api_ok(tmp_path, monkeypatch):
    remote = "lean/OAI/A.lean"

    def handler(url, _accept):
        where = channel_of(url)
        if where == "jsdelivr":
            return TimeoutError("timed out")
        if where == "raw":
            return urllib.error.HTTPError(url, 404, "Not Found", {},
                                          io.BytesIO(b"404: Not Found"))
        return FakeResponse(contents_payload(LEAN))

    calls = install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    assert [channel_of(call["url"]) for call in calls] == [
        "jsdelivr", "raw", "api-contents"]
    assert record["channel"] == "api-contents"
    assert record["bytes"] == len(LEAN)
    assert record["via"][0].startswith("jsdelivr -> TimeoutError")
    assert record["via"][1].startswith("raw -> HTTPError")
    assert record["via"] == [record["via"][0], record["via"][1], "api-contents -> ok"]
    saved = open(os.path.join(str(tmp_path), "lean", "OAI", "A.lean"), "rb").read()
    assert saved == LEAN
    assert record["sha256"] == hashlib.sha256(LEAN).hexdigest()


@pytest.mark.parametrize("bad", ["jsdelivr", "raw", "api-contents"])
def test_html_error_page_is_rejected_on_any_channel(tmp_path, monkeypatch, bad):
    remote = "lean/OAI/A.lean"

    def handler(url, _accept):
        where = channel_of(url)
        if where == bad:
            page = HTML_PAGE
        elif bad == "api-contents":
            return urllib.error.HTTPError(url, 404, "Not Found", {},
                                          io.BytesIO(b"404"))
        else:
            page = LEAN
        if where == "api-contents":
            return FakeResponse(contents_payload(page))
        return FakeResponse(page)

    install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    if bad == "api-contents":
        assert record["channel"] is None
        assert "疑似错误页" in record["errors"][-1]
        assert "first 80 bytes=b'<!DOCTYPE html>" in record["errors"][-1]
        assert not os.path.exists(os.path.join(str(tmp_path), "lean", "OAI", "A.lean"))
    else:
        assert record["channel"] not in (None, bad)
        saved = open(os.path.join(str(tmp_path), "lean", "OAI", "A.lean"), "rb").read()
        assert saved == LEAN


def test_all_three_html_error_pages_fail_closed(tmp_path, monkeypatch):
    remote = "lean/docs/378.md"

    def handler(url, _accept):
        if channel_of(url) == "api-contents":
            return FakeResponse(contents_payload(HTML_PAGE))
        return FakeResponse(HTML_PAGE)

    install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    assert record["channel"] is None
    assert record["bytes"] is None
    assert len(record["errors"]) == 3
    assert all("疑似错误页" in error for error in record["errors"])
    assert [via.split(" -> ")[0] for via in record["via"]] == [
        "jsdelivr", "raw", "api-contents"]
    assert not os.path.exists(os.path.join(str(tmp_path), "lean", "docs", "378.md"))


def test_validate_content_shapes():
    # .lean: UTF-8 and not HTML
    fs.validate_content("lean/OAI/A.lean", "theorem t : True := trivial\n".encode())
    with pytest.raises(fs.ChannelError) as error:
        fs.validate_content("lean/OAI/A.lean", b"\xff\xfe\x00bad utf-8")
    assert "非 UTF-8" in str(error.value)
    with pytest.raises(fs.ChannelError) as error:
        fs.validate_content("lean/OAI/A.lean", HTML_PAGE)
    assert "疑似错误页" in str(error.value)

    # .json: must json.loads
    fs.validate_content("lean/ComparatorChallenges/SubexponentialSAT.json", b'{"a": 1}')
    with pytest.raises(fs.ChannelError) as error:
        fs.validate_content("lean/ComparatorChallenges/SubexponentialSAT.json",
                            b'{"a": 1,}')
    assert "json.loads" in str(error.value)

    # .pdf: must start with %PDF-
    fs.validate_content("p/paper.pdf", b"%PDF-1.7\n%\xd0\xd4\n")
    with pytest.raises(fs.ChannelError) as error:
        fs.validate_content("p/paper.pdf", b"<html>not a pdf</html>")
    assert "%PDF-" in str(error.value)

    # .md / _toolchain / .yaml: non-empty and not HTML
    fs.validate_content("lean/docs/378.md", b"# The Exponential Time Hypothesis\n")
    fs.validate_content("lean/lean-toolchain", b"leanprover/lean4:v4.20.0\n")
    fs.validate_content("lean/formalization.yaml", b"# yaml-language-server: $schema=x\n")
    with pytest.raises(fs.ChannelError) as error:
        fs.validate_content("lean/formalization.yaml", b"")
    assert "empty body" in str(error.value)
    with pytest.raises(fs.ChannelError) as error:
        fs.validate_content("lean/docs/378.md", b"\n  <!doctype html><html></html>")
    assert "疑似错误页" in str(error.value)


def test_api_403_is_recognisable_and_never_leaks_the_token(tmp_path, monkeypatch):
    remote = "lean/OAI/A.lean"
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_SECRET_SENTINEL_123")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    body = b'{"message":"API rate limit exceeded for 1.2.3.4"}'

    def handler(url, _accept):
        where = channel_of(url)
        if where == "api-contents":
            return urllib.error.HTTPError(url, 403, "rate limit exceeded",
                                          {"X-RateLimit-Remaining": "0"},
                                          io.BytesIO(body))
        return TimeoutError("timed out")

    calls = install_transport(monkeypatch, handler)
    monkeypatch.setattr(fs.time, "sleep", lambda *_: None)  # tries=4 must not stall the suite
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=4)

    api_calls = [call for call in calls if channel_of(call["url"]) == "api-contents"]
    assert len(api_calls) == 1  # 403 is not retried
    assert api_calls[0]["auth"] == "Bearer ghp_SECRET_SENTINEL_123"
    assert record["channel"] is None
    message = record["errors"][-1]
    assert "403" in message and "GITHUB_TOKEN" in message
    assert "60 requests/hour" in message
    assert "X-RateLimit-Remaining=0" in message
    assert "ghp_SECRET_SENTINEL_123" not in json.dumps(record, ensure_ascii=False)


def test_api_contents_over_1mb_switches_to_raw_media_type(tmp_path, monkeypatch):
    remote = "preprints/paper.pdf"
    size = 1_500_000
    pdf = b"%PDF-1.7\n" + b"0" * (size - len(b"%PDF-1.7\n"))

    def handler(url, accept):
        if channel_of(url) != "api-contents":
            return urllib.error.HTTPError(url, 404, "Not Found", {},
                                          io.BytesIO(b"404"))
        if accept.endswith("application/vnd.github.raw"):
            return FakeResponse(pdf)
        # 1 MB+: GitHub returns the object form with no inline content
        return FakeResponse(contents_payload(b"", size=size, encoding="none"))

    calls = install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    accepts = [call["accept"] for call in calls if channel_of(call["url"]) == "api-contents"]
    assert len(accepts) == 2
    assert accepts[0] == "application/vnd.github+json"
    assert accepts[1] == "application/vnd.github.raw"
    assert record["channel"] == "api-contents"
    assert record["bytes"] == size
    saved = open(os.path.join(str(tmp_path), "preprints", "paper.pdf"), "rb").read()
    assert saved.startswith(b"%PDF-") and len(saved) == size


def test_api_contents_inline_640kb_text_is_decoded_without_second_request(tmp_path, monkeypatch):
    remote = "CONTENTS.md"
    blob = b"# Mathematics\n" + b"x" * 640_900

    def handler(url, _accept):
        if channel_of(url) != "api-contents":
            return TimeoutError("timed out")
        return FakeResponse(contents_payload(blob))

    calls = install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    api_calls = [call for call in calls if channel_of(call["url"]) == "api-contents"]
    assert len(api_calls) == 1  # 640 KB < 1 MB stays inline
    assert record["channel"] == "api-contents"
    assert record["bytes"] == len(blob)


def test_api_truncated_body_is_retried_then_succeeds(tmp_path, monkeypatch):
    remote = "CONTENTS.md"
    blob = b"# Mathematics\n" + b"x" * 1000
    state = {"api": 0}

    def handler(url, _accept):
        if channel_of(url) != "api-contents":
            return TimeoutError("timed out")
        state["api"] += 1
        if state["api"] == 1:
            return TruncatedResponse(500, 500)
        return FakeResponse(contents_payload(blob))

    install_transport(monkeypatch, handler)
    monkeypatch.setattr(fs.time, "sleep", lambda *_: None)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=2)

    assert state["api"] == 2  # the truncated 200 was retried, not written
    assert record["channel"] == "api-contents"
    assert record["bytes"] == len(blob)


def test_api_truncated_body_reports_bytes_read(tmp_path, monkeypatch):
    remote = "CONTENTS.md"

    def handler(url, _accept):
        if channel_of(url) != "api-contents":
            return TimeoutError("timed out")
        return TruncatedResponse(500, 500)

    install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    assert record["channel"] is None
    assert "truncated body: 500 of 1000 bytes read" in record["errors"][-1]
    assert not os.path.exists(os.path.join(str(tmp_path), "CONTENTS.md"))


def test_api_contents_size_mismatch_is_a_failed_hop(tmp_path, monkeypatch):
    remote = "lean/OAI/A.lean"

    def handler(url, _accept):
        if channel_of(url) != "api-contents":
            return TimeoutError("timed out")
        return FakeResponse(contents_payload(LEAN, size=len(LEAN) + 7))

    install_transport(monkeypatch, handler)
    record = fs.fetch_one(remote, remote, str(tmp_path), timeout=1, tries=1)

    assert record["channel"] is None
    assert "size mismatch" in record["errors"][-1]
    assert not os.path.exists(os.path.join(str(tmp_path), "lean", "OAI", "A.lean"))


def test_manifest_records_api_channel_and_via(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])

    def handler(url, _accept):
        if channel_of(url) == "api-contents":
            return FakeResponse(contents_payload(b"def a := 1\n"))
        return TimeoutError("timed out")

    install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports", "--tries", "1"])

    assert code == 0
    manifest = json.load(open(os.path.join(out, "_manifest.json"), encoding="utf-8"))
    assert manifest["files"][0]["channel"] == "api-contents"
    assert [entry.split(" -> ")[0] for entry in manifest["files"][0]["via"]] == [
        "jsdelivr", "raw", "api-contents"]
    assert manifest["files"][0]["via"][-1] == "api-contents -> ok"


# ----------------------------------------------- ref pinning (--ref / --no-resolve)

SHA = "0123456789abcdef0123456789abcdef01234567"
COMMITS_PREFIX = "https://api.github.com/repos/openai/math/commits/"


def commit_payload(sha=SHA):
    return json.dumps({"sha": sha, "commit": {"message": "m"}}).encode("utf-8")


def read_manifest(out):
    with open(os.path.join(out, "_manifest.json"), encoding="utf-8") as handle:
        return json.load(handle)


def test_arg_sha_is_used_verbatim_on_all_three_channels(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])

    def handler(url, _accept):
        assert not url.startswith(COMMITS_PREFIX), "a 40-hex sha must not be resolved"
        if channel_of(url) == "api-contents":
            return FakeResponse(contents_payload(LEAN))
        return TimeoutError("timed out")

    calls = install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports",
                    "--ref", SHA, "--tries", "1"])

    assert code == 0
    text = capsys.readouterr().out
    assert "ref: requested=%s resolved=%s source=arg-sha" % (SHA, SHA) in text
    urls = [call["url"] for call in calls]
    assert "cdn.jsdelivr.net/gh/openai/math@%s/" % SHA in urls[0]
    assert "raw.githubusercontent.com/openai/math/%s/" % SHA in urls[1]
    assert "?ref=%s" % SHA in urls[2]
    manifest = read_manifest(out)
    assert manifest["ref_requested"] == SHA
    assert manifest["ref_resolved"] == SHA
    assert manifest["ref_source"] == "arg-sha"
    assert manifest["ref_error"] is None


def test_branch_ref_resolves_once_and_all_files_use_the_sha(tmp_path, monkeypatch, capsys):
    seeds = ["lean/OAI/A.lean", "lean/OAI/B.lean", "lean/OAI/C.lean"]
    monkeypatch.setattr(fs, "FILES", [(seed, seed) for seed in seeds])

    def handler(url, _accept):
        if url.startswith(COMMITS_PREFIX):
            return FakeResponse(commit_payload())
        return FakeResponse(LEAN)

    calls = install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports",
                    "--ref", "main", "--tries", "1"])

    assert code == 0
    commits = [call for call in calls if call["url"].startswith(COMMITS_PREFIX)]
    assert len(commits) == 1  # one resolution, reused for every file
    assert commits[0]["url"] == COMMITS_PREFIX + "main"
    served = [call["url"] for call in calls if "cdn.jsdelivr.net" in call["url"]]
    assert len(served) == 3
    assert all("@%s/" % SHA in url for url in served)
    manifest = read_manifest(out)
    assert manifest["ref_source"] == "api-commit"
    assert manifest["ref_resolved"] == SHA
    assert manifest["ref_requested"] == "main"
    assert len(manifest["files"]) == 3


def test_resolution_403_warns_falls_back_and_records_unresolved(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    body = b'{"message":"API rate limit exceeded for 1.2.3.4"}'

    def handler(url, _accept):
        if url.startswith(COMMITS_PREFIX):
            return urllib.error.HTTPError(url, 403, "rate limit exceeded",
                                          {"X-RateLimit-Remaining": "0"},
                                          io.BytesIO(body))
        return FakeResponse(LEAN)

    calls = install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports",
                    "--ref", "main", "--tries", "4"])
    text = capsys.readouterr().out

    assert code == 0  # the fallback still fetches; the run just is not pinned
    assert len([c for c in calls if c["url"].startswith(COMMITS_PREFIX)]) == 1  # 403 not retried
    assert "WARNING" in text
    assert "NOT byte-pinned" in text
    assert "403" in text
    assert "resolved=null" in text
    # fell back to the requested branch name on every channel
    fetched = [call["url"] for call in calls if not call["url"].startswith(COMMITS_PREFIX)]
    assert all("@main/" in url or "/main/" in url or "?ref=main" in url for url in fetched)
    manifest = read_manifest(out)
    assert manifest["ref_source"] == "unresolved"
    assert manifest["ref_resolved"] is None
    assert manifest["ref_requested"] == "main"
    assert "403" in manifest["ref_error"]
    assert manifest["files"][0]["channel"] is not None  # bytes still arrived


@pytest.mark.parametrize("body,needle", [
    (HTML_PAGE, "not JSON"),
    (b'{"commit": {"message": "no sha here"}}', "no 40-hex"),
    (b'["not", "an", "object"]', "no 40-hex"),
])
def test_resolution_bad_payload_is_a_reported_error(tmp_path, monkeypatch, body, needle):
    def handler(url, _accept):
        assert url.startswith(COMMITS_PREFIX)
        return FakeResponse(body)

    install_transport(monkeypatch, handler)

    resolved, source, error = fs.resolve_ref("main", timeout=1, tries=1)

    assert resolved is None  # never a guessed sha
    assert source == "unresolved"
    assert needle in error


def test_manifest_ref_fields_are_complete_and_the_timestamp_parses(tmp_path, monkeypatch):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])

    def handler(url, _accept):
        if url.startswith(COMMITS_PREFIX):
            return FakeResponse(commit_payload())
        return FakeResponse(LEAN)

    install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports",
                    "--ref", "main", "--tries", "1"])

    assert code == 0
    manifest = read_manifest(out)
    for field in ("upstream_repo", "ref_requested", "ref_resolved",
                  "ref_resolved_at", "ref_source"):
        assert field in manifest, field
    assert manifest["upstream_repo"] == "openai/math"
    stamp = manifest["ref_resolved_at"]
    assert stamp.endswith("Z")
    parsed = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert parsed.utcoffset() == datetime.timedelta(0)
    now = datetime.datetime.now(datetime.timezone.utc)
    assert abs((now - parsed).total_seconds()) < 300
    assert "ref_error" in manifest


def test_token_is_sent_as_a_header_and_never_reaches_manifest_or_warning(
        tmp_path, monkeypatch, capsys):
    token = "ghp_SECRET_SENTINEL_999"
    monkeypatch.setenv("GITHUB_TOKEN", token)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    # The worst case: the response body echoes the credential back at us.
    body = ('{"message":"Bad credentials for %s"}' % token).encode("utf-8")

    def handler(url, _accept):
        if url.startswith(COMMITS_PREFIX):
            return urllib.error.HTTPError(url, 403, "Bad credentials",
                                          {"X-RateLimit-Remaining": "0"},
                                          io.BytesIO(body))
        return FakeResponse(LEAN)

    calls = install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports",
                    "--ref", "main", "--tries", "1"])
    text = capsys.readouterr().out

    assert code == 0
    commits = [call for call in calls if call["url"].startswith(COMMITS_PREFIX)]
    assert commits[0]["auth"] == "Bearer " + token
    assert all(token not in call["url"] for call in calls)
    assert token not in text
    assert "***" in text
    with open(os.path.join(out, "_manifest.json"), encoding="utf-8") as handle:
        raw = handle.read()
    assert token not in raw
    manifest = json.loads(raw)
    assert token not in json.dumps(manifest.get("ref_error"), ensure_ascii=False)
    assert manifest["ref_source"] == "unresolved"


def test_no_resolve_skips_the_commits_api(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])

    def handler(url, _accept):
        assert not url.startswith(COMMITS_PREFIX), "--no-resolve must not call /commits"
        return FakeResponse(LEAN)

    calls = install_transport(monkeypatch, handler)
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports",
                    "--ref", "main", "--no-resolve", "--tries", "1"])
    text = capsys.readouterr().out

    assert code == 0
    assert "no-resolve" in text
    assert "@main/" in calls[0]["url"]
    manifest = read_manifest(out)
    assert manifest["ref_source"] == "no-resolve"
    assert manifest["ref_requested"] == "main"
    assert manifest["ref_resolved"] is None  # nothing was proven to be a sha
    assert manifest["ref_error"] is None
    assert manifest["files"][0]["channel"] == "jsdelivr"

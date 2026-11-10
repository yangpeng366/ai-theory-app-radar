"""Offline tests for the import-closure part of fetch-sources.py.

No network: ``fetch_one`` is replaced by a fake that serves an in-memory dict of
Lean sources and records every request, so recursion, de-duplication, prefix
filtering, the --max-modules cap and failure reporting are all observable.

Run from the repository root:
    python -m pytest repro/family378-subexpsat -q
"""

import hashlib
import importlib.util
import json
import os

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

    def _fetch(remote, local, out_dir, timeout=240, tries=4):
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

    code = fs.main(["--out", out, "--no-paper"])
    text = capsys.readouterr().out

    assert code == 0
    assert "seed: 1/1 files" in text
    assert "closure: complete (1 file(s) added" in text
    assert "fetched 2/2 files" in text
    manifest = json.load(open(os.path.join(out, "_manifest.json"), encoding="utf-8"))
    assert [record["origin"] for record in manifest] == ["seed", "import"]
    assert manifest[0]["local"] == seed
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

    code = fs.main(["--out", out, "--no-paper", "--max-modules", "1"])
    text = capsys.readouterr().out

    assert code == 2
    assert "closure: PARTIAL (truncated at --max-modules=1" in text
    closure = json.load(open(os.path.join(out, "_closure.json"), encoding="utf-8"))
    assert closure["status"] == "truncated"
    assert closure["not_fetched"] == ["OAI.C"]
    # the file that was fetched is still pinned in the manifest
    manifest = json.load(open(os.path.join(out, "_manifest.json"), encoding="utf-8"))
    assert [record["origin"] for record in manifest] == ["seed", "import"]


def test_main_failed_import_exits_1(tmp_path, monkeypatch, capsys):
    seed = "lean/OAI/A.lean"
    monkeypatch.setattr(fs, "FILES", [(seed, seed)])
    sources = {seed: "import OAI.B\n"}
    install_fake(monkeypatch, sources, [], fail=("lean/OAI/B.lean",))
    out = str(tmp_path / "out")

    code = fs.main(["--out", out, "--no-paper"])
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

    code = fs.main(["--out", out, "--no-paper", "--no-include-imports"])
    text = capsys.readouterr().out

    assert code == 0
    assert calls == [seed]
    assert "closure: skipped" in text
    closure = json.load(open(os.path.join(out, "_closure.json"), encoding="utf-8"))
    assert closure["status"] == "skipped"
    assert closure["complete"] is False

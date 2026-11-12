# Contributing

This repo tracks an open pipeline: listen to AI math/theory outputs, filter verifiable results, then map them to cryptography, physics, materials, complex networks, and engineering.

## What to contribute

- Radar notes under `radar/` (one candidate family / paper / repo per file preferred)
- Progress logs under `progress/`
- Pipeline improvements in `docs/pipeline.md`
- Statement cards for a single theorem/algorithm (assumptions, claim, verification status, spillover)

## Rules

1. Prefer foundational theory that an AI agent can argue or formalize
2. Mark verification status clearly: `lean-build` / `algorithm` / `insight` / `unverified`
3. Do not present news headlines as theorems
4. Materials / glass-ceramics / networks are spillover mappings only unless you bring checkable math
5. UTF-8 without BOM; keep secrets out of the repo

## Verify your change

Every change runs through [`.github/workflows/verify.yml`](.github/workflows/verify.yml). Run the same five gates locally before opening a PR — each one can fail on its own:

```bash
python -m pytest repro/family378-subexpsat -q     # offline self-test
python tools/check_repo_encoding.py               # UTF-8, no BOM, whole repo
ruff check repro tools                            # static check ...
python -m compileall -q repro tools                # ... plus a byte-compile
python tools/check_check_contract.py              # C1..C24 + pinned ref
python tools/check_radar_index.py                  # radar/index.json vs radar/
```

Adding or editing a card under `radar/` also means regenerating the index with `python scripts/build-radar-index.py`; `tools/check_radar_index.py` compares it with the cards field by field, so a stale or hand-edited `radar/index.json` fails instead of silently drifting.

`tools/check_check_contract.py` is the one that guards the contract: the ids in `check-gap.py` must be exactly C1..C24, the stage split must stay C1-C11 / C12-C19 / C20-C24, and every `C<n>` cited under `radar/`, `docs/`, `progress/` and the READMEs must name a check that exists. Adding a check means adding it to `check-gap.py`, naming it in a radar note, and keeping the count contiguous.

### No network needed

The suite stubs `urllib.request.urlopen` (and `fetch_one` for the closure walk) and `repro/family378-subexpsat/conftest.py` refuses any non-loopback socket or DNS access. `test_offline_guard.py` checks that the guard itself is active. If a new case needs an upstream response, serve it from an in-memory fake or a loopback `http.client` stub — never from `openai/math`.

### Upstream commit behind the review set

The 2026-11-11 family-378 review set corresponds to **`openai/math` @ `4eaee87548250b2682affda7d05d947c05554bae`** (`ref_source: arg-sha`). Pin it with `--ref <40-hex sha>`: a sha is used verbatim and costs no commits-API request, a branch is resolved to a sha once and the sha is written to the manifest as `ref_resolved`; a failed resolution is reported as `unresolved` with `ref_resolved: null` rather than silently treated as pinned. Quote `ref_resolved` plus the per-file `sha256` values whenever you compare two runs.

## Suggested first PR

Add a statement card for `openai/math` family 102 (Unique Games / approximation thresholds), or an independently verified nearby result with links.
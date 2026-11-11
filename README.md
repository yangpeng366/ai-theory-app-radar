# AI Theory → Application Radar

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Open collaboration board for turning AI-produced mathematics / theory into follow-ups in cryptography, physics, materials, complex networks, and engineering.

中文要点：监听 AI 数学与理论产出 → 过滤可验证结果 → 映射到应用 → 最小成本复现。优先基础理论、AI agent 好论证的对象；应用后挂。

## Why

AI math output is arriving faster than human review. Chasing every repo is wasteful. This project keeps a reusable pipeline and a triage log that others can extend.

## Pipeline

```text
listen → filter verifiable results → map to application problems → minimal reproduction
```

Intake buckets:

1. **Lean-checkable proofs**
2. **New algorithms**
3. **New understanding** (counterexamples, exposed gaps, restated assumptions)

## For agents

Most downstream users are LLM agents, so compatibility stops at the interface level:

- one candidate card per file in `radar/`, named `radar/<date>-<topic>-<slug>.md`
- machine checks live in
 `tools/` and `repro/`, and each gate exits non-zero on its own failure (see **Verify the review tooling**)
- progress notes append to `progress/`, one dated file per round

Read `AGENTS.md` for the handoff rules (encoding, where to write, what not to claim) before editing.

## Repo layout

| Path | Role |
|---|---|
| `docs/pipeline.md` | Pipeline + selection principles |
| `progress/` | Chronological progress |
| `radar/` | Triage notes and statement cards |
| `repro/` | Reproduction scripts and protocols for third-party re-checks |
| `AGENTS.md` | Notes for coding agents working in this repo |

## Current focus (2026-10-29)

- Primary sandbox: [`openai/math`](https://github.com/openai/math) family **102** (Unique Games / optimal approximation thresholds) — statement card done
- Active execution track: family **266** (N(6)=3, mutually unbiased bases) — third-party executable re-check **passed**; see [`radar/2026-10-29-family266-mub-dim6-review.md`](radar/2026-10-29-family266-mub-dim6-review.md)
- Next attack: family **378** (ETH refuted) — quantify the gap between the Lean bound and the manuscript bound
- Side tracks only as interface translations: percolation / Voronoi / expanders → materials & networks
- Feishu project row: `recvwuSTYb28w0` (private tracker); this GitHub repo is the public collaboration surface

## Review lane (added 2026-10-29)

AI math output arrives faster than human review. The gap is no longer solving, it is digesting: explaining key steps, answering colleagues, following up on problems found. This repo therefore tracks a fourth intake bucket — **executable re-check** — plus a fifth step, **review and extend**:

1. numerical consistency of the archived records
2. arithmetic / ABI contract of the published programs
3. instruction-level check that key expressions use separately rounded binary64 operations

Reproduction scripts live in [`repro/`](repro/); conclusions always ship with the upstream scope statement attached.

## Verify the review tooling

CI is [`.github/workflows/verify.yml`](.github/workflows/verify.yml). It runs four independent gates, each of which can fail on its own, and none of them fetch the upstream review set:

| Gate | Command (local) | What it proves |
|---|---|---|
| offline self-test | `python -m pytest repro/family378-subexpsat -q` | the fetch/closure/C14/C16 logic still behaves, including the C14 red cases and the C20/C21 SKIP policy (43 cases, 0 network) |
| encoding | `python tools/check_repo_encoding.py` | every tracked file is UTF-8 and BOM-free, per `AGENTS.md` |
| static | `ruff check repro tools` and `python -m compileall -q repro tools` | no syntax error, no undefined name |
| contract | `python tools/check_check_contract.py` | C1..C24 map one-to-one to `check-gap.py`, every cited id exists, the fetch is pinned |

Run all four from the repository root; the whole set takes about a second. The review scripts use the standard library only, so `pytest` and `ruff` are the only installs (the workflow pins their versions).

### Verify without network access

`repro/family378-subexpsat/conftest.py` refuses every non-loopback socket connect and DNS lookup for the duration of each test, and `test_offline_guard.py` proves the guard bites. So "the tools are verifiable offline" is enforced, not promised: a test that starts reaching for `cdn.jsdelivr.net` fails instead of downloading. `fetch-sources.py` itself never runs in CI; its transport is replaced by in-memory fakes, and `--no-resolve` is what the tests use to keep the ref from moving.

### Upstream commit behind the review set

The 2026-11-11 family-378 review set was taken from **`openai/math` @ `4eaee87548250b2682affda7d05d947c05554bae`** (`refs/heads/main` at that time). That sha, not `main`, is what makes the conclusions reproducible:

- `--ref <40-hex sha>` is used verbatim on all three channels and never sent to the commits API; the manifest records `ref_source: arg-sha` and `ref_resolved: <that sha>`.
- `--ref <branch>` resolves once to a sha before any file is fetched (`ref_source: api-commit`), and every file uses the resolved sha.
- If resolution fails, the run prints `WARNING: ... NOT byte-pinned`, keeps fetching with the raw ref, and records `ref_resolved: null` + `ref_error` — it does not pretend to be pinned.
- `--no-resolve` skips the API entirely (`ref_source: no-resolve`, `ref_resolved: null`); it is for mirrors and tests, not for conclusions.

So two manifests are the same source only when `ref_resolved` is equal **and** `files[].sha256` match file by file. `tools/check_check_contract.py` re-proves the `arg-sha` path offline on every run and fails if this section stops naming the commit.

## Listen sources

- [openai/math](https://github.com/openai/math)
- [VibeMathed](https://vibemathed.com/) / [mrconter1/vibemathed](https://github.com/mrconter1/vibemathed)
- [frenzymath/HolomorphicAnosov](https://github.com/frenzymath/HolomorphicAnosov)
- [MechMath/MechMath-agent-team](https://github.com/MechMath/MechMath-agent-team)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Before opening a PR, run the four gates listed under [Verify the review tooling](#verify-the-review-tooling). Small radar notes and statement cards are the best first PRs.

## License

MIT

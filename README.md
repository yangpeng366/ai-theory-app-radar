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

## Listen sources

- [openai/math](https://github.com/openai/math)
- [VibeMathed](https://vibemathed.com/) / [mrconter1/vibemathed](https://github.com/mrconter1/vibemathed)
- [frenzymath/HolomorphicAnosov](https://github.com/frenzymath/HolomorphicAnosov)
- [MechMath/MechMath-agent-team](https://github.com/MechMath/MechMath-agent-team)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Small radar notes and statement cards are the best first PRs.

## License

MIT
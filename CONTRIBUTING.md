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

## Suggested first PR

Add a statement card for `openai/math` family 102 (Unique Games / approximation thresholds), or an independently verified nearby result with links.
---
name: ai-theory-app-radar
description: "AI 理论→应用（理论到应用）的 research radar：把 AI 产出的数学/理论结果（密码学、形式化验证、Lean4）筛成可复现的应用候选，并做候选分诊。当 agent 要找「某理论能否落到应用」的候选、给研究方向排优先级，或要一条复现路径时，用这个 agent skill。"
---

# AI 理论 → 应用雷达

本仓把 AI 产出的数学 / 理论结果筛成「可复现的应用候选」：监听 → 过滤可验证结果 → 映射到应用问题 → 最小成本复现（口径见 `docs/pipeline.md`）。仓内既有 `radar/` 候选卡片与机器可读索引 `radar/index.json`，也有 `repro/` 复现脚本、`tools/` 校验闸门。

## 何时用

- 要回答「某条 AI 理论 / 定理能不能落到应用」（密码、物理、材料、复杂网络、工程），或要一份候选清单；
- 要给研究方向排优先级，决定下一轮跟进哪一族；
- 要一条最小成本复现路径：哪个脚本、哪个上游 commit、哪条检查。

不适用：想要「已证定理」的最终答案。雷达条目是**候选**，不是已接受事实。

## 怎么用

1. 先读 `radar/index.json` —— 一个 JSON 就是全仓候选清单，不必遍历 `radar/*.md`：
   - 顶层：`schema`、`schema_version`、`source`（`radar/*.md`）、`card_count`、`cards[]`；
   - 每张卡：`id`、`path`（`radar/<id>.md`）、`date`、`topic`、`slug`、`title`、`tags`、`labels`、`families`（`openai/math` 族号）、`repro` / `docs` / `related_cards`（仓内相对路径指针）、`bytes`、`sha256`；
   - `tags` 只说明卡的种类（`statement-card` / `executable-recheck` / `formalization-gap` / `draft` / `round-log`），`labels` 是卡片自己的元数据原文。索引只放元信息与指针，**不含结论**——结论在卡片正文里。
2. 再按 `path` 打开真正要用的那几张卡（`radar/<date>-<topic>-<slug>.md`），读它的结论与适用边界。
3. 要复现就沿卡里的 `repro` 指针进 `repro/`；要背景再读 `docs/pipeline.md`、`docs/lean-toolchain-setup.md`。
4. 引用时结论与边界同句，不替上游扩大结论；材料 / 网络只作接口翻译，不写工艺结论（`AGENTS.md`）。

## 输出什么

每次分诊输出三行：

```text
动作：<挑哪个候选 / 下一步做什么>
理由：<引哪张卡的哪条结论、哪个族号、什么验证状态>
是否人工介入：<是 / 否> —— <人工要做哪一步，或为何可自动>
```

- 验证状态按仓内口径记：`lean-build` / `algorithm` / `insight` / `unverified`（`CONTRIBUTING.md`）。
- 未过 `lake build` + 人工审读的条目只是「雷达命中」（候选），不能当已证事实（`radar/2026-10-21-first-pass.md`）。
- 外发（投稿、改稿、对外发布）需人工授权，未授权前不外发（`radar/2026-11-11-sixth-pass.md`）。

## 自检

改了本仓就在仓库根目录跑，五道闸门各自能独立红：

```bash
python -m pytest repro/family378-subexpsat -q   # 离线自测，不联网
python tools/check_repo_encoding.py             # UTF-8 无 BOM，全仓
ruff check repro tools                          # 静态检查
python tools/check_check_contract.py            # C1..C24、引用、取件 pin
python tools/check_radar_index.py               # radar/index.json 与卡片一致
```

动了 `radar/` 下的卡片就必须重建索引，否则索引闸门会红：

```bash
python scripts/build-radar-index.py             # 重建 radar/index.json
```

其他约束（`AGENTS.md`）：源码与文档一律 UTF-8 无 BOM；取件钉到 40 位 sha；索引只放元信息与指针，结论留在卡片正文。

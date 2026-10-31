# 第三轮：族 378 形式化差距复核（第三次可执行复核）+ 族 266 一键自检（绿卡）

日期：2026-10-30  
仓库：[yangpeng366/ai-theory-app-radar](https://github.com/yangpeng366/ai-theory-app-radar)（公开仓，`main`）  
飞书行：`recvwuSTYb28w0`（AI理论→密码/物理/材料/网络应用雷达）  
本轮定位：**openai/math 仓的第三次可执行复核**（族 378，24 项机械检查）+ **族 266 最小自检补齐** + **上游/社区辖区差异实测**

---

## 一、一句话结论

> 族 378 的形式化差距是**闭式、可复算、可提交**的：上游 Lean 证明的指数恰是论文自陈的**较弱一档** `rho(n)`，
> 与论文主界差 `log2 log2 n` 倍、与 `m ≤ Dn` 锐化界差 `(log2 log2 n)^2` 倍；
> 差距在 `n ∈ [20, 10^5]` 上**逐点成立**，不是小 `n` 假象。
> 本轮把这套判定固化成**一条命令可复跑**的核查脚本（24 项检查 / FAIL 0 / 确证 1 处差距），
> 并把族 266 的复跑路径补成**绿灯自检**。

---

## 二、第三次可执行复核：族 378 三段核查

脚本：`repro/family378-subexpsat/check-gap.py`（不需 Lean 工具链、不需 Mathlib）。取件：`fetch-sources.py`（19 文件 / 1 728 710 字节，逐文件 sha256）。

```bash
python3 fetch-sources.py --out ./f378
python3 check-gap.py --src ./f378
```

| 段 | 覆盖 | 检查项 | 实测 |
|---|---|---|---|
| 一、数据一致性 | 取件与「论文 ↔ Lean ↔ 挑战」三者对得上 | C1–C11 | 10 PASS + 1 PART（import 闭合，取件范围所致） |
| 二、算术与复杂度契约 | 指数、编码换算、时间尺度桥 | C12–C19 | 8 PASS |
| 三、陈述级核查 | 论文主定理与 Lean 侧覆盖范围 | C20–C24 | 4 PASS + **1 GAP** |

**汇总：24 项检查，FAIL 0，确证形式化差距 1 项。**

三项值得单独记的结果：

- **C19（挑战陈述 ≡ 解法陈述）**：挑战文件与解法文件中的 `exact_count_and_sat` 类型部分**逐字相同**（1 124 字符）。
  这是**文本等价**，尚未升级为**编译等价**（Lean 工具链仍在装，见第五节）。
- **C10（定义漂移）**：挑战副本与规范模块共有的 25 个定义语义完全一致，唯二差异是 `runtimeScale` / `runtimeBound` 的
  `noncomputable` 标记位置（等价）。初版检查器误报「6/17 漂移」，已改为命名空间感知 + 语义归一。
- **C20 / C21**：用 **PDF 字形几何**判定（上标是更小字号、更高基线的独立 span），机器可判定地确认论文两档指数的差别，
  不依赖截图肉眼。

### 差距的闭式（第五节详述）

设 `rho(n) = n(log2 log2 n)^2 / sqrt(log2 n)`（Lean 所证）、`beta(n) = n log2 log2 n / sqrt(log2 n)`（论文主界）、`gamma(n) = n / sqrt(log2 n)`（`m ≤ Dn` 锐化界）：

```text
rho(n) = beta(n) * log2 log2 n      rho(n) = gamma(n) * (log2 log2 n)^2
```

`n ≥ 16` 时 `log2 log2 n > 1`，故 Lean 界**在任何** `n ≥ 20`（论文门槛）都不蕴含论文主界；且 `m ≤ Dn` 锐化界在取件范围内**无任何对应陈述**。

逐项对照表（论文条目 ↔ Lean 实体 ↔ 判定）见 [`2026-10-30-family378-formalization-gap.md`](2026-10-30-family378-formalization-gap.md) 第四节。

---

## 三、绿卡：族 266 一键自检

上一轮复核卡承诺「把复跑规程固化进 `repro/mub-dim6/`，供他人一键复跑」。本轮补齐，并修掉一个**真缺陷**：

| 项 | 旧状态（已提交） | 本轮状态 |
|---|---|---|
| `fetch-verification.py` | 把目录**拍平**写入目标目录；漏取 `commands.json`、`check_records.py`、`build.sh`、`batches/` | **保留上游目录结构**，取件清单 19 + 177 + 100 + 8 + 4 个文件 |
| 复跑方式 | README 让人跑 `python3 execution/check_records.py`（因树被拍平，必然找不到输入） | `python3 selfcheck.py --fetch`：取件 → 哈希比对 → 校验器实跑 → **绿灯判定** |
| 上游漂移 | 无检测 | 12 个关键文件的 sha256 前 16 位与复核卡取值逐一比对，上游改动会报 `CHANGED` |

即：旧脚本按 README 的用法是**跑不起来的**，本轮把它修成能用。

---

## 四、上游与社区辖区差异（实测，取代旧说法）

上一轮记的「openai/math 719 篇 / 372 族 vs oai-math-revised 721 篇 / 373 族，差 2 篇 1 族，未定位」——**本轮已作废**。2026-10-30 实测：

| 仓 | `preprints/` 目录数 | `CONTENTS.md` 族号数 | 目录集合差异 | 族号集合差异 |
|---|---|---|---|---|
| `openai/math` | 751 | 373（最大族号 378） | — | — |
| `mathcommunity/oai-math-revised` | 751 | 373（最大族号 378） | **0** | **0** |

即两仓的 preprint 目录与族号**完全一致**，先前的「2 篇 1 族」缺口已被社区补齐（或两侧同步增长）。同时，
`openai/math` 相对 2026-10-29 记录的 719 个目录**增长了 32 个**——这正是下一轮要跟的增量信号。

---

## 五、边界声明（必随结论同读）

1. 本轮**未运行** Lean 工具链、**未 `lake build`** 任何 Lean 文件；所有 Lean 侧判断来自**源码文本**的机器核对，**不是**编译通过或证明正确性的证明。
2. 本轮**未重跑**论文的数值实验，也**未验证**其正确性；族 378 不提供数值可执行包（族 266 才有）。
3. 论文侧断言取自 `paper.pdf`（2026-10-25 修订版）的字形与文本抽取，**未**与更早版本比对，故不能排除版本间主张已变化。
4. 「Lean 只证到 `rho`」的依据是上游 `lean/docs/378.md` 自陈 + 本轮源码核对（二者一致）；本轮**未**独立证明 `rho` 与论文主界**不等**，给出的是闭式反例族。
5. 「`m ≤ Dn` 锐化未形式化」按「**取件范围内未发现**」记账，**不是**「上游绝无」。
6. 族 266 的绿灯只说明**存档数值记录内部自洽**，**不是**历史归档的认证，**不是** C++ 实现的证明，**不是**原编译器/硬件行为的验证。
7. 第四节的目录/族号计数取自 GitHub contents API 与两仓 `CONTENTS.md`，是**当日快照**，上游会继续增长。

---

## 六、本轮产出

| 文件 | 性质 |
|---|---|
| `radar/2026-10-30-family378-formalization-gap.md` | 族 378 形式化差距说明（逐项量化 + 已覆盖/未覆盖对照表） |
| `radar/2026-10-30-oai-math-revised-review-draft.md` | 投 `mathcommunity/oai-math-revised` 的修订意见草稿（**尚未提交 PR**） |
| `repro/family378-subexpsat/` | 取件脚本 + 24 项核查脚本 + 复跑说明 |
| `repro/mub-dim6/selfcheck.py` | 族 266 一键绿灯自检 |
| `repro/mub-dim6/fetch-verification.py` | 取件脚本（**修**：保留目录结构、补齐清单） |
| `docs/lean-toolchain-setup.md` | Lean 工具链落盘与环境说明（含已踩的坑） |
| `radar/2026-10-30-third-pass.md` | 本文（第三轮纪要） |

---

## 七、下一步（自推）

1. **提交社区 PR**：把族 378 稿投 `mathcommunity/oai-math-revised`（先读其 `AGENTS.md`；以「追加节」姿态，不替换 PR #60 的 `NOTES.md`）。
2. **补齐取件**：把执行层模块（`SqrtLogSpace/NativeLargeEntry`、`ExecutionNativeFinal` 等）纳入 `fetch-sources.py`，消除 C11 的 PART 与边界第 5 条。
3. **Lean 工具链**：后台下载中（约 180 KB/s，580 MB 需约 1 小时），装好后做 `lake build` 单模块冒烟，把 C19 升级为编译等价；Mathlib olean 缓存是下一道成本。
4. **下一轮巡检重点**：跟 `openai/math` 的 `history.md` / `CONTENTS.md` **增量**（新增 32 个目录的族号与标题），并继续比对社区辖区差异是否再度出现。

## 八、2026-11-01 附注（补记，勿据本文第三节判定绿灯已成立）

- 第三节所称「绿卡」在 10-30 当轮**并未真正跑通**：取件在 `execution/data/fine.bin` 处被中断，
  落地 25 165 824 字节（上游真实 33 746 388 字节，缺 8.58 MB），校验器读到**残缺记录仍报 PASS**。
  绿灯是 2026-11-01 补齐取件（gh-proxy Range 分块重取，sha256 逐位对上 10-29 复核卡）后才成立的。
- 10-29 复核卡 `atlas.cpp` 的 sha256 前缀**少记末位一位**（15 位），使 `selfcheck.py` 的上游漂移检测
  恒误报 1 处 `CHANGED`；卡片已更正，比对改为 `startswith()`。
- 族 378 的 24 项复跑于 11-01 离线复现，结果与本文一致（24 项 / FAIL 0 / 确证 1 处差距）。
- 详见 [`2026-11-01-fourth-pass.md`](2026-11-01-fourth-pass.md)。

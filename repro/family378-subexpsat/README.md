# 复现：族 378「证伪 ETH」的形式化差距核查

本目录给出复跑路径，不搬运上游 Lean 源码与论文 PDF。  
详细结论见 [`radar/2026-10-30-family378-formalization-gap.md`](../../radar/2026-10-30-family378-formalization-gap.md)，
面向社区的投稿草稿见 [`radar/2026-10-30-oai-math-revised-review-draft.md`](../../radar/2026-10-30-oai-math-revised-review-draft.md)。

## 一、取件

```powershell
python fetch-sources.py --out ./f378
```

**取件量 = 种子清单 + `import OAI.*` 闭包（动态）。** 种子清单是 18 个 Lean/文本文件加 1 个论文 PDF
（共 19 个；2026-11-11 复核仍为 1 728 710 字节），只是**陈述级人工清单**，够读声明、不够编译：
上游 `preprints/…/paper.pdf`，`lean/OAI/Algorithms/SubexponentialSAT/` 下 12 个模块，
`lean/ComparatorChallenges/SubexponentialSAT.{lean,json}`，`lean/docs/378.md`，`lean/formalization.yaml`，
`lean/lean-toolchain`，以及仓根 `CONTENTS.md` 与 `history.md`。

默认还会按源码里的 `import` 递归补齐闭包，因此**最终文件数不写死**：它随上游改动和 `--max-modules` 变化，
以脚本末行 `fetched x/y files` 与 `_closure.json` 为准。

| 参数 | 默认 | 语义 |
|---|---|---|
| `--include-imports` / `--no-include-imports` | **开** | 是否递归拉齐 `import OAI.*` 闭包。默认开：种子清单缺证明主体模块，关掉后树不可编译、C11 必然是 PART |
| `--max-modules` | 400 | 闭包**新增**文件数上限，防止失控拉取；触顶时打印并记为 `truncated`。2026-11-11 实测该族闭包至少 348 个模块（含证明主体），200 会截断，故默认 400 |
| `--timeout` | 240 | 单请求超时（秒），两个通道各自计时 |
| `--tries` | 4 | 每通道尝试次数 |
| `--no-paper` | 关 | 跳过 `paper.pdf` |

通道按可用性降级：`cdn.jsdelivr.net` → `raw.githubusercontent.com`。脚本写两个 JSON：

- `_manifest.json`：逐文件 `remote`/`local`/`bytes`/`sha256`/`channel`，另加 `origin`。
  `origin="seed"` 表示种子清单里的文件；`origin="import"` 表示闭包新增，这类记录还带 `module`（Lean 模块名）
  与 `imported_by`（哪些模块 import 了它），所以闭包可复现、可追责。**只有成功取到的文件进 manifest**，
  失败项不进（否则指向不存在的文件会破坏 C1 校验）。
- `_closure.json`：`status` ∈ `complete` / `partial` / `truncated` / `skipped`，`complete` 布尔，`seed_files`、
  `seed_fetched`、`imported_files`、`failed`（模块名 + 通道错误 + 谁 import 的）、`not_fetched`（被 `--max-modules` 截住的剩余队列）。

退出码：`0` 全成功且闭包完整；`1` 有取件失败（种子或闭包，闭包因此不完整）；`2` 被 `--max-modules` 截断；
失败与截断同时出现按 `1` 报。**部分闭包不会静默成功**。

中断与重跑：manifest 只登记**本次运行**取到的文件，`--out` 里已有但未登记的旧文件不会被重新计入；
中断后建议换空目录重跑。种子清单在闭包开始前就先写一次 `_manifest.json`，
所以长闭包被中断时至少留下种子部分的 sha256。

### 取件脚本的离线测试

```powershell
python -m pytest repro/family378-subexpsat -q
python -m py_compile repro/family378-subexpsat/fetch-sources.py
```

`test_fetch_sources.py` 用 monkeypatch 替掉 `fetch_one`，不联网，覆盖：二级依赖递归、已在盘模块不重拉、
非 `OAI.` 前缀不拉、`--max-modules` 截断可见、失败进 `failed`、`import` 四种语法变体，
以及 `--include-imports` 开/关与退出码 `0/1/2`。

## 二、一键核查

```powershell
python check-gap.py --src ./f378
```

不需要 Lean 工具链，不需要 Mathlib，全部结论可由已发布源件回答。脚本分三段共 24 项检查：

| 段 | 检查项 | 判据 |
|---|---|---|
| 一、数据一致性 | C1–C11 | 取件 sha256、族号、声明名、定理落地、`sorry` 分布、公理白名单、定义漂移、import 闭合 |
| 二、算术与复杂度契约 | C12–C19 | 尺度定义、`rho` 阶、指数差、编码换算引理、编码界数值复核、`runtimeScale ≤ 4ρ` 数值复核、ETH 陈述形状、挑战陈述 ≡ 解法陈述 |
| 三、陈述级核查 | C20–C24 | 论文主定理指数、论文 `rho` 定义、上游自陈锐化、Lean 侧锐化缺失、差距是否小 `n` 假象 |

退出码 0 表示全部机械检查成立；**科学判定（哪些论文段落被覆盖）以表格打印，不写进退出码**——本族的预期发现就是「确有一处差距」。

2026-10-30 实测：`checks: 24, FAIL: 0, confirmed gaps: 1`（C23）。

## 三、怎么读结果

- **PASS** = 机械检查成立（文本、字形、哈希、数值层面的可复算事实）。
- **PART** = 结论受取件范围所限（如 C11：用 `--no-include-imports` 只取种子清单时，import 无法在子集内闭合）。
  默认开着闭包取件时，C11 应在闭包完整时 PASS；若 `_closure.json` 是 `partial`/`truncated`，C11 仍可能是 PART。
- **GAP** = 确认为形式化差距（C23：`m ≤ Dn` 锐化界 `2^{O(n/√log n)}` 在取件范围内无任何对应陈述）。

C19「挑战陈述 ≡ 解法陈述」目前是**文本等价**：挑战文件与解法文件中 `exact_count_and_sat` 的类型部分逐字相同（1 124 字符）。
它是文本事实，**不是**编译事实——Lean 工具链尚未在本机装好（见 [`docs/lean-toolchain-setup.md`](../../docs/lean-toolchain-setup.md)）。

## 四、边界（复跑时同读）

1. 本轮**未运行** Lean 工具链，**未 `lake build`** 任何 Lean 文件；所有 Lean 侧判断来自**源码文本**的机器核对，**不是**编译通过或证明正确性的证明。
2. 本轮**未重跑**论文的数值实验，也**未验证**其正确性；本族不提供数值可执行包（对比族 266 的 `repro/mub-dim6/`）。
3. 论文侧断言取自 `paper.pdf`（2026-10-25 修订版）的字形与文本抽取，**未**与更早版本比对。
4. 「Lean 只证到 `rho`」的判断依据是上游 `lean/docs/378.md` 的自陈与本轮源码核对，二者一致；本轮**未**独立证明 `rho` 与论文主界**不等**——给出的是闭式反例族 `rho(n)/beta(n) = log2 log2 n > 1`（`n ≥ 16`）。
5. 「`m ≤ Dn` 锐化未形式化」按「**取件范围内未发现**」记账，而非「上游绝无」。

## 五、许可与出处

上游 openai/math 为 Apache-2.0。本目录只含自写取件脚本与核查脚本；论文 PDF 与 Lean 源码均从上游按原样取用，版权归 OpenAI。

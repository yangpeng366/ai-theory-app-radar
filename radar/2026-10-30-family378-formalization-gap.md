# 族 378：证伪 ETH 的形式化差距说明（Lean 界 vs 论文界）

日期：2026-10-30  
来源：[openai/math](https://github.com/openai/math) `preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/`（2026-10-25 修订版）  
飞书行：`recvwuSTYb28w0`（AI理论→密码/物理/材料/网络应用雷达）  
性质：**可执行复核（陈述级）** + **形式化差距（逐项量化）**  
复跑脚本：[`repro/family378-subexpsat/`](../repro/family378-subexpsat/README.md)

---

## 一、一句话结论

> 族 378 的 Lean 形式化**恰好证明了论文自己称为「较弱指数」的那一档** $\rho(n)=n(\log\log n)^2/\sqrt{\log n}$；
> 论文主定理的 $n\log\log n/\sqrt{\log n}$ 与 $m\le Dn$ 情形的 $n/\sqrt{\log n}$ **两档都未被形式化**，
> 且差距是**闭式的**：$\rho(n)$ 恰为主界指数的 $\log_2\log_2 n$ 倍，恰为锐化界指数的 $(\log_2\log_2 n)^2$ 倍。
> 差距**不是**小 $n$ 假象：在 $n\in[20,10^5]$ 的每个 $n$ 上 Lean 指数都严格大于论文主界指数。

---

## 二、论文侧原文（取自 `paper.pdf` 第 2 页，逐字）

> **Theorem 1.1.** For each fixed $k \ge 2$, there exists a deterministic algorithm that, given a $k$-CNF $F$ on $n \ge 20$ declared variables with $m$ clauses, computes $\#F$ as defined in (1.1) in
> $$ (n+m)^{O_k(1)}\,2^{O_k(n\log\log n/\sqrt{\log n})} $$
> bit operations and $(n+m)^{O_k(1)}$ bits of space. For each fixed $D>0$, its running time on inputs with $m \le Dn$ is
> $$ (n+m)^{O_{k,D}(1)}\,2^{O_{k,D}(n/\sqrt{\log n})}. $$
> The rational interpolation argument in Section 6.4 gives the weaker exponent $O_k(\rho(n))$, where
> $$ \rho(n)=\frac{n(\log\log n)^2}{\sqrt{\log n}}=\frac{n}{(\log n)^{1/2+o(1)}}. $$
> Appendix D proves both bounds in Theorem 1.1 by tensor contraction.

**这段自陈就是本轮全部结论的锚点**：论文自己把 $\rho(n)$ 称为 *weaker*（较弱）的指数。而 Lean 形式化的指数**正是 $\rho(n)$**，一位不差。

上游 `lean/docs/378.md` 亦自陈同一件事（Scope 段）：

> For fixed $k\ge2$, Lean proves that a deterministic machine exactly counts satisfying assignments of a canonically encoded $k$-CNF on $n$ variables in time $(L+1)^{O_k(1)}2^{O_k(n(\log\log n)^2/\sqrt{\log n})}$, where $L$ is the encoding's bit length. […] For $m$ clauses, the October 25 manuscript gives the sharper time bound $(n+m)^{O_k(1)}2^{O_k(n\log\log n/\sqrt{\log n})}$. When $m\le Dn$ for fixed $D>0$, this improves to $(n+m)^{O_{k,D}(1)}2^{O_{k,D}(n/\sqrt{\log n})}$.

---

## 三、Lean 侧实测（本轮取件实读，非转述）

取件：`lean/OAI/Algorithms/SubexponentialSAT/` 下 12 个 Lean 模块 + `lean/ComparatorChallenges/SubexponentialSAT.lean` + `lean/docs/378.md` + `paper.pdf`，共 19 文件 / 1 728 710 字节，sha256 全部校验通过。

| Lean 实体 | 内容 | 位置 |
|---|---|---|
| `rho` | `n * (Real.logb 2 (Real.logb 2 n))^2 / Real.sqrt (Real.logb 2 n)` | `SqrtLogSpace/Asymptotics.lean:10` |
| `runtimeScale` | `n * (Real.log (Real.log (n+16)))^2 / Real.sqrt (Real.log (n+16))` | `SqrtLog/StatementScale.lean:18` |
| `runtimeScale_le_four_rho` | `runtimeScale n ≤ 4 * rho n`（需 `20 ≤ n`） | `SqrtLogSpace/Asymptotics.lean` |
| `encoding_le_declaredSize_sq` | `formulaBitLength F + 1 ≤ (8k+7) * (n + F.card + 1)^2` | `SqrtLogSpace/EncodingBounds.lean` |
| `encoding_pow_le_declaredSize` | `(L+1)^d ≤ (8k+7)^d * (n+m+1)^{2d}` | 同上 |
| `runtimeBound_le_eth` | `runtimeBound C A d L n ≤ (C(8k+7)^d)(n+m+1)^{2d} 2^{(4A)·rho n}` | `SqrtLogSpace/Statement.lean` |
| `exact_count_eth` | `time ≤ C·(n+F.card+1)^d · 2^{A·rho n}`，前提 `20 ≤ n` | `SqrtLogSpace/Final.lean` |
| `exact_count_and_sat` | 挑战陈述与解法陈述**逐字相同**（1 124 字符） | 挑战文件 vs `Final.lean` |

**编码换算（$L \leftrightarrow (n,m)$）是否成立？——成立，且已形式化。** 链条完整：

$$ L+1 \le (8k+7)(n+m+1)^2 \;\Longrightarrow\; (L+1)^d \le (8k+7)^d (n+m+1)^{2d}, $$

即 Lean 的 $(L+1)^{O_k(1)}$ 项**就是**论文的 $(n+m)^{O_k(1)}$ 项。本轮另以 40 组采样公式独立数值复核该界（`check-gap.py` C16）全部成立。

---

## 四、已覆盖 / 未覆盖 对照表

| 论文条目（paper.pdf, 2026-10-25） | 论文陈述 | Lean 侧对应 | 判定 |
|---|---|---|---|
| 精确计数 $\#F$ | Theorem 1.1 | `exact_count_and_sat` / `exact_count_eth`（解法 0 处 `sorry`） | **已覆盖** |
| 可满足性判定 | Theorem 1.1 + Corollary 1.2 | `sat_polynomial_space`（`hk : 3 ≤ k`）、`original_sat_main` | **已覆盖** |
| 固定宽度 $k\ge2$ | Theorem 1.1 | `hk : 2 ≤ k` | **已覆盖** |
| 小输入门槛 $n\ge20$ | Theorem 1.1 | `exact_count_eth` 的 `20 ≤ n` | **已覆盖** |
| 多项式因子 | $(n+m)^{O_k(1)}$ | `encoding_pow_le_declaredSize`（$L+1\le(8k+7)(n+m+1)^2$） | **已覆盖**（换算成立） |
| 空间 | $(n+m)^{O_k(1)}$ bits | `visitedSpace ≤ S·(L+1)^e`，同一换算 ⇒ $(n+m)^{O(1)}$ | **已覆盖** |
| 论文自陈的插值界 | $O_k(\rho(n))$，$\rho(n)=n(\log\log n)^2/\sqrt{\log n}$ | `rho n`（逐字同式）+ `2^{A·rho n}` | **已覆盖（逐位吻合）** |
| **主时间界** | $(n+m)^{O_k(1)}\,2^{O_k(n\log\log n/\sqrt{\log n})}$ | $2^{O_k(\rho(n))}=2^{O_k(n(\log\log n)^2/\sqrt{\log n})}$ | **未覆盖**：指数差 $\Theta(\log\log n)$ |
| **$m\le Dn$ 锐化界** | $(n+m)^{O_{k,D}(1)}\,2^{O_{k,D}(n/\sqrt{\log n})}$ | 无任何对应陈述 | **未覆盖**：Lean 侧完全缺失 |
| CONTENTS.md 一句话 | $2^{n/(\log n)^{1/2+o(1)}}$ | 与 $\rho$ 同阶（$(\log\log n)^2=(\log n)^{o(1)}$） | 已覆盖，但**该一句话弱于论文主定理** |

---

## 五、差距的量化（闭式，非渐近记号）

设
$$\rho(n)=\frac{n(\log_2\log_2 n)^2}{\sqrt{\log_2 n}},\quad
  \beta(n)=\frac{n\log_2\log_2 n}{\sqrt{\log_2 n}},\quad
  \gamma(n)=\frac{n}{\sqrt{\log_2 n}} .$$

则**恒等式**（本轮数值验证，误差 $<10^{-9}$）：

$$\boxed{\ \rho(n)=\beta(n)\cdot\log_2\log_2 n\ },\qquad
\boxed{\ \rho(n)=\gamma(n)\cdot(\log_2\log_2 n)^2\ }$$

| $n$ | $\log_2\log_2 n$ | $\rho/\beta$ | $\rho/\gamma$ |
|---|---|---|---|
| $10^{4}$ | 3.73 | 3.73 | 13.93 |
| $10^{6}$ | 4.32 | 4.32 | 18.64 |
| $10^{8}$ | 4.73 | 4.73 | 22.39 |
| $10^{10}$ | 5.05 | 5.05 | 25.54 |
| $10^{12}$ | 5.32 | 5.32 | 28.27 |

**含义**：

1. 从 Lean 界到论文主界，只需把指数里的 $(\log\log n)^2$ 换成 $\log\log n$，即在指数上再除一个 $\log\log n$（**一次** $\Theta(\log\log n)$ 的改进）。
2. 从 Lean 界到 $m\le Dn$ 锐化界，则要在指数上再除一个 $(\log\log n)^2$（**两次**）。
3. 这两档差距**不是**「$O(\cdot)$ 记号吞掉了」——两者的指数只差**可分离的闭式因子**，因此「Lean 证到了弱一档」是严格意义的判断，不是记号游戏。

---

## 六、「$n$ 情形化简」核对（$n\ge20$ 门槛与对数基换算）

Lean 侧有两处「$n$ 情形」容易误读，本轮逐项核对：

| 项 | Lean 陈述 | 核对结果 |
|---|---|---|
| 论文主界在 $\log_2$ 下 | $\beta(n)=n\log_2\log_2 n/\sqrt{\log_2 n}$ | 与 $\rho$ 的差别**仅**是 $\log\log n$ 与 $(\log\log n)^2$（见第五节恒等式） |
| Lean 机器自己的时间尺度 | `runtimeScale n = n(\ln\ln(n+16))^2/\sqrt{\ln(n+16)}$` | 用**自然对数**且带 **$+16$ 位移**，与论文的 $\log_2$ 不同基 |
| 两者之间的桥 | `runtimeScale_le_four_rho : runtimeScale n ≤ 4·rho n`（需 `20 ≤ n`） | 本轮对 $n\in[20,5000]$ **逐个数值复核成立**（首个成立点即 $n=20$）；常数 4 与「$+16$ 位移」正是换基与处理小 $n$ 的代价 |
| 门槛为何是 20 | 证明内部用到 `four_le_logb : 4 ≤ log₂ n`（即 $n\ge16$）与 `sparsifyNu_pos` | 门槛 20 是**证明自身**所需（$n\ge16$ 另留余量），**不是**为了迁就某个 $n$ 情形 |

**「交点」问题**：是否存在某个 $n$，使 Lean 指数不大于论文主界指数（那样 Lean 界就能蕴含论文界）？本轮对 $n\in[20,10^5]$ 逐点检查：**不存在**。比值恒为 $\log_2\log_2 n>1$。故差距是**渐近的**，不是小 $n$ 效应。

---

## 七、第三方复核实测结果（本轮实跑，24 项机械检查）

脚本：`repro/family378-subexpsat/check-gap.py`（不需 Lean 工具链、不需 Mathlib，全部问题可由已发布源件回答）。

| 段 | 检查 | 结果 |
|---|---|---|
| 第一段 数据一致性 | C1 取件 sha256 / C2 族号 / C3 声明名（json↔yaml）/ C4 定理名落地 / C5 解法模块路径 / C6 挑战恰 1 处 `sorry` / C7 解法 0 处 `sorry` / C8 公理白名单 / C9 `#print axioms` / C10 定义漂移 / C11 import 闭合 | **10 PASS**，C11 为 PART（取件子集外 21 个 import 属正常：证明主体未取） |
| 第二段 算术与复杂度契约 | C12 尺度定义一致 / C13 $\rho$ 阶 / C14 指数差 / C15 编码换算引理 / C16 编码界数值复核 / C17 `runtimeScale ≤ 4ρ` 数值复核 / C18 Lean ETH 陈述形状 / C19 挑战陈述≡解法陈述 | **8 PASS** |
| 第三段 陈述级核查 | C20 论文主定理指数（PDF 字形）/ C21 论文 $\rho$ 定义（PDF 字形）/ C22 上游自陈锐化 / C23 Lean 侧锐化缺失 / C24 差距是否小 $n$ 假象 | **4 PASS + 1 GAP** |

**汇总：24 项检查，FAIL 0，已确认的形式化差距 1 项。**

两处值得单独记的实测结果：

- **C19（挑战陈述 ≡ 解法陈述）**：挑战文件 `ComparatorChallenges/SubexponentialSAT.lean` 里 `exact_count_and_sat` 的**类型部分**与 `SqrtLogSpace/Final.lean` 中被证明的同名定理**逐字相同**（1 124 字符）。即 Comparator 量到的确实是「所证的那一条」，不是别的。
- **C10（定义漂移）**：挑战副本与规范模块共有的 25 个定义**语义完全一致**；唯二的文本差异是 `runtimeScale` / `runtimeBound` 的 `noncomputable` 标记位置（挑战文件显式标注，规范模块用 `noncomputable section`），在 Lean 中等价。**初版检查器把这一项误报为「6/17 定义漂移」，已修正为命名空间感知 + 语义归一。**

**C20 / C21 用 PDF 字形几何判定**（不是截图肉眼看）：上标数字是字号更小、基线更高的独立 span。Theorem 1.1 主界的 `log log` 之后**无**上标 `2` ⇒ 单次 $\log\log$；$\rho(n)=n(\log\log n)2/\sqrt{\log n}$ 行的 `log log` 之后**有**上标 `2` ⇒ 平方。据此**机器可判定**地确认了论文两档指数的差别。

---

## 八、边界声明（必随结论同读）

1. 本轮**未运行** Lean 工具链，**未 `lake build`** 任何 Lean 文件；所有 Lean 侧判断来自**源码文本**的机器核对（定义、类型、引理陈述、字面量），**不是**编译通过或证明正确性的证明。
2. 本轮**未重跑**论文的数值实验，也**未验证**其正确性；本族不提供数值可执行包（对比族 266）。
3. 论文侧断言取自 `paper.pdf`（2026-10-25 修订版）的字形与文本抽取；**未**与更早版本（10-06 首版）比对，故不能排除版本间主张已变化。
4. 「Lean 只证到 $\rho$」这一判断的**依据**是上游自己的 `lean/docs/378.md` Scope 段与本轮对 Lean 源码的核对，二者一致；本轮**未**独立证明 $\rho$ 与论文主界**不等**——这里给出的是**闭式反例族**：$\rho(n)/\beta(n)=\log_2\log_2 n>1$ 对一切 $n\ge16$ 成立。
5. 「$m\le Dn$ 锐化未形式化」的判定范围是**本轮取件的 12 个 Lean 模块 + 挑战文件**；若上游在未取件模块（如 `SqrtLogSpace/NativeLargeEntry` 等执行层）另有等价陈述，本轮不会看到。故此条按「**取件范围内未发现**」记账，而非「上游绝无」。
6. 社区已有第三方对同族另有贡献（`chelsinchaos`，PR #60，2026-10-28）：其内容是 §2.3–2.7 的**玩具规模可执行模型**与结构性评注；与本卡的**形式化差距**侧互不重叠。

---

## 九、下一步（本轮已排定，自推）

1. **投稿**：把本卡第七节 + 第四节整理成 `oai-math-revised` 的 `NOTES.md` 补充与 `checks/` 脚本（草稿见 [`2026-10-30-oai-math-revised-review-draft.md`](2026-10-30-oai-math-revised-review-draft.md)）。**注意**：社区已有一份同族 `NOTES.md`，本稿须以「补充」而非「替换」姿态，并显式致谢其覆盖范围。
2. **补齐取件**：把 `SqrtLogSpace/NativeLargeEntry`、`ExecutionNativeFinal` 等执行层模块纳入取件清单，消除 C11 的 PART 与边界第 5 条。
3. **Lean 工具链**：`elan` 已装；`leanprover/lean4:v4.34.1` **工具链尚未装完**（2026-10-30 实测 `/root/.elan/toolchains` 仅有 lock 文件，下载约 180 KB/s，580 MB 需约 1 小时，后台续跑）。装好后做 `lake build` 单模块冒烟，验证 C19 的陈述一致性不是文本巧合而是编译事实；另需 Mathlib olean 缓存（GB 量级）。详见 [`docs/lean-toolchain-setup.md`](../docs/lean-toolchain-setup.md)。
4. **下一轮巡检触发器**：以 `openai/math` 的 `history.md` / `CONTENTS.md` 增量为主，并继续盯 `mathcommunity/oai-math-revised` 的辖区差异（**2026-10-30 实测：两仓 preprint 目录均为 751 个、族号均为 373 个，集合差异为 0**，先前的「差 2 篇 1 族」已作废；`openai/math` 较 2026-10-29 记录的 719 个目录增长了 32 个）。

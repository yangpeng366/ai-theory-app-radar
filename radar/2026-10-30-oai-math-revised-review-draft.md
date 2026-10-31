# 投 `mathcommunity/oai-math-revised` 的修订意见草稿（族 378）

日期：2026-10-30  
目标仓库：[mathcommunity/oai-math-revised](https://github.com/mathcommunity/oai-math-revised/)（受邀参与修订 OpenAI 写稿，可申请 reviewer）  
目标目录：`preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/`  
状态：**草稿，尚未提交 PR**（提交前须先读社区 `AGENTS.md` 与该目录既有 `NOTES.md`）

---

## 零、提交姿态（必读）

该族已有一份社区 `NOTES.md`（`chelsinchaos`，2026-10-28，PR #60），内容为：

- §2.3–2.7 的**玩具规模可执行模型**（`checks/measurement_toy.py`）
- 关于 §2.7 构造的两条结构性评注
- 两条表述建议

**本稿与之不重叠**： theirs 是「算法机制的可执行再现」，本稿是「**形式化侧与论文侧之间的量化差距**」。二者合起来正好构成该族审读台账的两栏。因此本稿：

1. **不替换**既有 `NOTES.md`，而是**追加**一节（社区 README 允许在 `NOTES.md` 中增补）；
2. 交付物为一个**新脚本** `checks/formalization_gap.py` + 本稿正文；
3. 开篇即声明与 PR #60 的关系，避免读者误以为重复劳动。

---

## 一、可直接粘贴的 `NOTES.md` 追加节

> ## Formalization gap between the manuscript and the Lean development (third-party, 2026-10-30)
>
> This note complements, and does not replace, the notes added on 2026-10-28: those reproduce the *mechanism* of Sections 2.3–2.7 at toy scale, whereas this note measures the distance between the **manuscript's stated bounds** and the **bounds that were actually formalised**. No claim below is new mathematics; every item is a check that a reader can re-run.
>
> ### 1. The manuscript states two exponents; the Lean development proves the weaker one
>
> Theorem 1.1 of the 25 October manuscript claims
>
> $$\text{time} = (n+m)^{O_k(1)}\,2^{O_k(n\log\log n/\sqrt{\log n})},$$
>
> and, for inputs with $m\le Dn$,
>
> $$\text{time} = (n+m)^{O_{k,D}(1)}\,2^{O_{k,D}(n/\sqrt{\log n})}.$$
>
> The same page also says: *"The rational interpolation argument in Section 6.4 gives the weaker exponent $O_k(\rho(n))$, where $\rho(n)=n(\log\log n)^2/\sqrt{\log n}$."*
>
> The Lean development proves exactly that weaker exponent. In `lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Asymptotics.lean`:
>
> ```lean
> noncomputable def rho (n : ℕ) : ℝ :=
>   (n : ℝ) * (Real.logb 2 (Real.logb 2 n)) ^ 2 / Real.sqrt (Real.logb 2 n)
> ```
>
> and in `SqrtLogSpace/Final.lean`:
>
> ```lean
> (time : ℝ) ≤ C * ((n + F.card + 1 : ℕ) : ℝ) ^ d * (2 : ℝ) ^ (A * rho n)
> ```
>
> The upstream scope note `lean/docs/378.md` says the same thing in prose. So the two bounds differ by a **separable closed-form factor**, not by bookkeeping inside big-O:
>
> $$\frac{\rho(n)}{\,n\log\log n/\sqrt{\log n}\,}=\log_2\log_2 n
> \qquad\text{and}\qquad
> \frac{\rho(n)}{\,n/\sqrt{\log n}\,}=(\log_2\log_2 n)^2 .$$
>
> Numerically (values from the script below):
>
> | $n$ | $\log_2\log_2 n$ | $\rho /$ main bound | $\rho /$ $m\le Dn$ bound |
> |---|---|---|---|
> | $10^{4}$ | 3.73 | 3.73 | 13.93 |
> | $10^{8}$ | 4.73 | 4.73 | 22.39 |
> | $10^{12}$ | 5.32 | 5.32 | 28.27 |
>
> Since $\log_2\log_2 n>1$ for every $n\ge16$, the Lean bound is **never** at least as strong as the main bound, on any $n$ in the paper's range $n\ge20$. The gap is therefore asymptotic, not a small-$n$ artefact.
>
> ### 2. What *is* covered, and the encoding conversion does hold
>
> The gap is confined to the exponent. Everything else in Theorem 1.1 is present in the Lean development:
>
> - exact counting and satisfiability: `exact_count_and_sat`, `exact_count_eth`, `sat_polynomial_space`, `original_sat_main`;
> - fixed width $k\ge2$ and the small-input threshold $n\ge20$ (`20 ≤ n` appears in `exact_count_eth`);
> - the polynomial factor $(n+m)^{O_k(1)}$: this requires converting the encoded bit length $L$ into $(n,m)$, and **that conversion is formalised**:
>
>   ```lean
>   theorem encoding_le_declaredSize_sq {n k : ℕ} (F : SAT.CNF (Fin n)) (hw : SAT.WidthAtMost k F) :
>       Encoding.formulaBitLength F + 1 ≤ (8 * k + 7) * (n + F.card + 1) ^ 2
>
>   theorem encoding_pow_le_declaredSize {n k : ℕ} (F : SAT.CNF (Fin n))
>       (hw : SAT.WidthAtMost k F) (d : ℕ) :
>     ((Encoding.formulaBitLength F : ℝ) + 1) ^ d ≤
>       ((8 * k + 7 : ℕ) : ℝ) ^ d * ((n + F.card + 1 : ℕ) : ℝ) ^ (2 * d)
>   ```
>
>   so $(L+1)^{O_k(1)}$ really is $(n+m)^{O_k(1)}$, and the space bound $S(L+1)^e$ is likewise $(n+m)^{O(1)}$ bits.
>
> - the comparison statement itself: the challenge file `lean/ComparatorChallenges/SubexponentialSAT.lean` and the solution `lean/OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Final.lean` state `exact_count_and_sat` with **textually identical** types (1 124 characters after normalisation), so the Comparator harness is measuring the statement that was actually proved.
>
> ### 3. The $m\le Dn$ sharpening is not formalised at all
>
> No statement in the fetched Lean modules mentions $m\le Dn$; the only hypothesis on $F$ anywhere in the counting chain is `SAT.WidthAtMost k F`. The $2^{O(n/\sqrt{\log n})}$ sharpening therefore has no formal counterpart in the files we inspected. (Scope: the 12 modules under `lean/OAI/Algorithms/SubexponentialSAT/` plus the challenge file; we did not fetch the execution-layer modules, so we state this as "not found in the inspected set", not as "absent from the whole tree".)
>
> ### 4. The $n\ge20$ threshold and the two logarithm bases
>
> The machine's own time scale is stated with **natural** logarithms and a **$+16$** shift,
>
> ```lean
> noncomputable def runtimeScale (n : ℕ) : ℝ :=
>   (n : ℝ) * (Real.log (Real.log ((n : ℝ) + 16))) ^ 2 / Real.sqrt (Real.log ((n : ℝ) + 16))
> ```
>
> and is bridged to the paper's base-two $\rho$ by `runtimeScale_le_four_rho : runtimeScale n ≤ 4 * rho n`, which requires `20 ≤ n`. The threshold comes from the proof itself (`four_le_logb : 4 ≤ log₂ n`, i.e. $n\ge16$, plus `sparsifyNu_pos`), not from a numerical convenience: the bridge already holds numerically for every $n\ge20$ we checked, and in fact for much smaller $n$.
>
> ### 5. Suggested notes for the write-up
>
> 1. **State the formalised exponent next to the claimed one.** The manuscript already introduces $\rho(n)$ as the "weaker exponent"; making explicit that the accompanying Lean artefact proves $\rho(n)$ (and not the Theorem 1.1 exponent) would remove the single most likely source of misreading.
> 2. **Consider stating the sharpening gap in the scope note.** `lean/docs/378.md` already says the $m\le Dn$ bound "improves" the Lean bound; a short indication of the *factor* involved ($\Theta((\log\log n)^2)$ in the exponent) would be more informative than the word "improves".
>
> ### 6. How to re-run
>
> `checks/formalization_gap.py` reproduces every number above from the published sources. It needs no Lean toolchain and no Mathlib: it reads the manuscript PDF, the Lean sources and the metadata files, and decides the exponent question from **PDF glyph geometry** (a superscript digit is a separate span with a smaller font and a higher baseline) rather than from a screenshot.
>
> ```bash
> python3 checks/formalization_gap.py --src <openai/math checkout>
> ```
>
> Exit status 0 means every mechanical check held; the scientific verdict (which manuscript segments are covered) is printed as a table and is **not** encoded in the exit code, because a confirmed gap is the expected finding here.
>
> ### 7. Automation disclosure
>
> The checks in this note were produced with substantial assistance from a language model, and are mechanical rather than mathematical: parsing, hashing, string and glyph comparison, and small numerical spot-checks. No step of the manuscript's proof was read as a proof; the notes above are statements about **what the artefacts say**, not about the truth of the theorem. The reader should re-run the script before relying on any number.
>
> Author: @yangpeng366. Repository: https://github.com/yangpeng366/ai-theory-app-radar

---

## 二、投稿前须办的四件事（尚未完成）

| # | 事项 | 现状 |
|---|---|---|
| 1 | 读社区 `AGENTS.md`（6 607 字节）与 `docs/SPARSE_CHECKOUT.md`，确认贡献格式与是否需披露自动化 | **未读**（已定位 URL：`https://raw.githubusercontent.com/mathcommunity/oai-math-revised/main/AGENTS.md`） |
| 2 | 确认 PR #60 的 `NOTES.md` 是否会被本稿追加节覆盖；必要时先开 issue 询问维护者 | **未做**（社区 README 明示「All submissions will be reviewed」） |
| 3 | 把 `repro/family378-subexpsat/check-gap.py` 改名为 `checks/formalization_gap.py` 并对齐社区目录结构（含取件脚本） | **未做** |
| 4 | 决定署名：社区允许只留 GitHub handle | **待定**（草稿用 `@yangpeng366`） |

## 三、本轮已完成 / 未完成（存档用）

**已完成**

- 差距逐项量化，且为**闭式**：$\rho/\beta=\log_2\log_2 n$，$\rho/\gamma=(\log_2\log_2 n)^2$（数值验证误差 $<10^{-9}$）。
- 「已覆盖 / 未覆盖」对照表 10 行，逐行给出 Lean 侧实体名与文件位置。
- 编码换算 $L\leftrightarrow(n,m)$ 的判定：**成立**，且已形式化（`encoding_le_declaredSize_sq` / `encoding_pow_le_declaredSize`），并以 40 组采样公式独立数值复核。
- 「$n$ 情形」核对：$n\ge20$ 门槛、$+16$ 位移、自然对数 vs 二进制对数、常数 4 的桥，全部落表；并证明差距**非**小 $n$ 假象（$n\in[20,10^5]$ 逐点）。
- 24 项机械检查全部 PASS，FAIL 0；1 项确认为差距（C23）。

**未完成（下一轮）**

- 未跑 Lean 工具链（`elan` + `leanprover/lean4:v4.34.1` 安装中），故「挑战陈述 ≡ 解法陈述」目前是**文本**等价，尚未升级为**编译**等价。
- 未取执行层模块（`NativeLargeEntry` 等），故「$m\le Dn$ 未形式化」按「取件范围内未发现」记账。
- 未向社区提交 PR（按本轮「自主推进但不动外部仓」的边界执行；且社区规定「不评论别人的 PR/issue」，提交新 PR 前须读其 `AGENTS.md`）。
- ~~未定位 openai/math 与 oai-math-revised 之间那 2 篇 / 1 族的差异~~ —— 2026-10-30 已实测：两仓 preprint 目录均为 751 个、族号均为 373 个，**集合差异为 0**；差异来源是社区追平 + 上游增长（openai/math 较 719 增至 751 目录）。

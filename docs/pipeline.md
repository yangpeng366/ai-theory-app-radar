# AI 理论 → 密码 / 物理 / 工程：雷达流水线

更新：2026-10-21  
仓库：本目录（F:\github\ai-theory-app-radar）
关联表：[项目方向](https://my.feishu.cn/base/Vb6pb5SJ4aWpEpsqPxvcR5Tqnte?table=tbl2XGd8bO10NBY5&view=vewK5iifVn)

## 1. 方向判断

## 1.1 选型原则：先基础、理论，且 AI agent 好论证

应用桶（密码 / 物理 / 材料 / 网络 / 工程）只作**外溢映射**，入池与开沙盒优先满足：

1. **陈述可机器检查**：定理 / 反例 / 复杂度陈述，能写成 Lean statement 或可复现算法规约
2. **假设边界清楚**：敌手模型、图类、概率空间、函数空间写得清
3. **agent 友好**：生成—报错—修正闭环短；少依赖实验装置与工艺参数
4. **外溢可后挂**：先站稳基础结果，再翻译到微晶玻璃 / 复杂网络 / 工程，不反过来用应用倒逼未证结论

**优先理论对象（agent 好啃）**

- 图与随机图：着色硬度、匹配、expander、阈值、Weisfeiler–Leman
- 近似与复杂度：UGC、Max-Cut、Vertex Cover、SDP 间隙
- 分析与 PDE 陈述：Vlasov–Maxwell 整体存在、Fourier 收敛（有 Comparator 者优先）
- 统计力学玩具模型：渗流、Ising / 自旋玻璃（当数学对象，不当材料配方）

**暂缓**

- 需要中试炉、显微表征、牌号工艺窗口才能「证伪」的材料命题
- 无 Lean / 无清晰算法规约、只靠新闻标题的「AI 证明」


AI 数学产出速度已超过人类审稿速度。跟进重点不是追每一个新仓库，而是跑通：

```text
监听产出 → 过滤可验证结果 → 映射到应用问题 → 最小成本复现 / 吸收新理解
```

「新产出」包括三类，任一即可入池：

1. **可编译形式化**：Lean 4 证明 / 形式化陈述
2. **新算法**：近似比、复杂度、构造、采样 / 计数方案
3. **新理解**：反例、阈值暴露、阈值/敌手模型重述、接口重组

已有本地资产可复用：`PNT_concepts/`、`宇宙学接口化闭环研究.md`、`D:\gitAll\cosmology-closed-loop`。

## 2. 流水线四步

### 2.1 监听

| 源 | 用途 |
|---|---|
| [openai/math](https://github.com/openai/math) | 规模最大的 AI 数学手稿库（719 篇 / 372 族，约 42% 顶线结果有 Lean） |
| [VibeMathed](https://vibemathed.com/) / [mrconter1/vibemathed](https://github.com/mrconter1/vibemathed) | 社区策展的 AI 参与数学结果清单 |
| [frenzymath/HolomorphicAnosov](https://github.com/frenzymath/HolomorphicAnosov) | 研究级猜想 + 完整形式化范本 |
| [MechMath/MechMath-agent-team](https://github.com/MechMath/MechMath-agent-team) | NL-Prover / FL-Prover / KB-Manager 模板 |
| arXiv 关键词 | `autoformalization` / `Lean 4` / `automated theorem proving` / `QKD formal proof` |

预警词（标题出现则优先点开）：

- 密码：branch number / S-box / MDS / lattice / SVP / NP-hardness
- 量子密码：QKD / BB84 / LOCC / entropic bound
- 控制与物理：Lyapunov / region of attraction / Vlasov–Maxwell / Heisenberg
- 工程算法：matrix multiplication / edit distance / bin packing / sparsest cut

### 2.2 过滤（30 秒）

1. 有 Lean 目录，还是只有 PDF？
2. 声称「证明」时：`lake build` 能否过？（本机未装齐时先看 formalization.yaml / Comparator）
3. 依赖 mathlib 还是自造公理？
4. 有 history / revisions 吗？（openai/math 有 history.md）
5. 完整证明还是 lemma 片段？
6. 许可：Apache-2.0 / MIT 优先
7. **无 Lean 也可入池**：若贡献是新算法或新理解，单独标 `type=algorithm|insight`，不冒充「已验证定理」

> 口诀：不能编译的当灵感；能编译的才当结论候选。新算法 / 新理解单独记账，不混进「已证」桶。

### 2.3 映射（扩展）

| 桶 | 映射问题 | 本地衔接 |
|---|---|---|
| 密码 / 复杂度 | UGC、Max-Cut / Vertex Cover、格覆盖、SDP 间隙、后量子归约 | — |
| 物理 / 宇宙学 | Vlasov–Maxwell、自旋玻璃、Heisenberg、渗流 | `宇宙学闭环` / cosmology-closed-loop |
| 材料 / 微晶玻璃 | 相变、玻璃化 / 晶化、渗流团簇、随机几何、第一性原理硬度 | 研究生微晶玻璃背景；优先「相变 + 显微结构网络」表述 |
| 复杂网络 | 渗流、expander、Ramanujan 图、随机图阈值、匹配 / 着色 | 已有 `networkx` 贡献线（recvriLOrYiTkY） |
| 工程算法 | 矩阵乘、编辑距离、装箱、Fourier 电路 | — |

材料线注意：AI 数学仓库很少直接写「微晶玻璃」。要翻译成可检索对象：

- glass / amorphous / crystallization / nucleation
- percolation / cluster / porous media
- phase transition / Ising / spin glass（作统计力学类比，不当材料结论）
- Voronoi / random geometry（显微组织几何）

复杂网络线注意：可与 networkx 贡献并行——雷达出定理/算法 → 评估能否变成 networkx issue / docs / 测试用例。

工程侧原则：**选一个本来就想证/想用的不等式或稳定条件**，不要从「AI 数学」倒推问题。

### 2.4 最小成本复现

1. 只抽 1 个最小定理 / 算法陈述
2. 先写清 statement（暴露隐藏假设）
3. 再补 proof / 复现实验
4. 失败路径也入库（对齐 MechMath KB-Manager）

本机暂不强制全量 `lake build` openai/math（仓库约 800MB+）。默认策略：

- 元数据与 `CONTENTS.md` / `formalization.yaml` 雷达扫描
- 只对入选条目做稀疏检出 / 单定理复现

## 3. 周常

- 周一：VibeMathed + arXiv + openai/math history
- 周三：挑 1 个仓库/条目，检查 Lean 或算法可复现性
- 周五：映射到密码 / Lyapunov / 安全归约 / 工程算法，写入本目录筛查笔记

## 4. 首轮结论摘要

详见 `radar/2026-10-21-first-pass.md`。

优先跟进三条（可立即开沙盒）：

1. **复杂度 / 密码邻域**：family 102 Unique Games + Max-Cut / Vertex Cover 硬度（有 Lean 标注）
2. **物理**：family 362 relativistic Vlasov–Maxwell（有 Lean）
3. **工程算法**：family 107 matrix multiplication ω≤9/4 或 121 edit-distance 近似（有 Lean）

旁路监听：HolomorphicAnosov（范本）、MechMath（生成-验证模板）、准 RH / Jacobsthal（衔接本地 PNT 线）。
# AI 理论 → 应用 · 首轮筛查（2026-10-21）

数据源：`openai/math` CONTENTS.md（719 手稿 / 372 族）+ lean/formalization.yaml（约 173 条 source 登记）。  
过滤口径：标题/摘要含硬度、SDP、格、流体、自旋、矩阵乘、编辑距离、量子电路等，且优先带 `[Lean]` 标注。

> 重要：下列条目是「候选」，不是已接受数学事实。openai/math README 写明验证覆盖不完全（约 42% 顶线结果形式化），未过 `lake build` + 人工审读前，只作雷达命中。

## A. 密码 / 复杂度（优先）

| 族 | Lean | 摘要 | 应用映射 |
|---|---|---|---|
| 102 Unique Games + 最优近似阈值 | YES | 声称证明 UGC；并给出 Max-Cut / Vertex Cover 等最优硬度 | 密码友好归约、近似算法上限、后量子/格邻域对照入口 |
| 105 2-to-1 Games 完美完备性 | YES | Khot 2-to-1 猜想（完美完备） | PCP / 硬度放大工具箱 |
| 106 三色图着色硬度 | YES | 三色图任意固定色数着色 NP-hard | 组合优化下界 |
| 117 Uniform Sparsest Cut | YES | 任意常数近似 NP-hard；SDP 间隙逼近已知上界 | 图分割、谱方法上限 |
| 118 Bin packing LP 间隙 | YES | 否定 modified integer round-up；加性常数近似 NP-hard | 调度 / 装箱工程界 |
| 092 凸体覆盖密度 Θ(n log n) | YES | 格与平移覆盖最优阶 | 格几何 / 覆盖码邻域 |
| 126 完美匹配 SDP 指数复杂度 | YES | 完美匹配多面体精确 SDP lift 需指数 | 凸优化表示极限 |

## B. 物理

| 族 | Lean | 摘要 | 应用映射 |
|---|---|---|---|
| 362 relativistic Vlasov–Maxwell | YES | 三维单物种大初值整体光滑 | 等离子体 / 带电粒子工程模型 |
| 221 Mézard–Parisi 稀释自旋玻璃 | YES | 分层腔公式 | 统计物理 / 优化景观 |
| 271 Heisenberg 铁磁 Bloch 定律 | YES | T^{3/2} 与格修正 | 量子磁体 |
| 268 / 邻域 Haldane gap | 部分 | 自旋一反铁磁链能隙 | 凝聚态 |
| 274 Parity ∉ QAC⁰ | YES | Moore 奇偶猜想（测量输出模型） | 量子电路下界 |
| 275 连续 Coulomb 能 QMA-hard | YES | 电子库仑能量近似 QMA-hard | 量子化学硬度 |
| 213–214 临界渗流 | YES | Benjamini–Schramm 临界 / 非唯一性 | 网络渗流、可靠性 |

## C. 工程算法

| 族 | Lean | 摘要 | 应用映射 |
|---|---|---|---|
| 107 矩阵乘 ω≤9/4 | YES | 复数域矩阵乘指数上界 | 数值线性代数内核 |
| 121 编辑距离几乎线性近似 | YES | (1+ε) 近似，N^{1+o(1)} | 文本 / DNA / 日志对齐 |
| 099 编辑距离 ℓ1 嵌入扭曲 | YES | 最优指数阶扭曲 | 度量嵌入 |
| 075 L log L Fourier 收敛 | YES | 经典 Fourier 充分性猜想 | 信号处理理论底座 |

## D. 与本地线衔接

| 族 | Lean | 为何衔接 |
|---|---|---|
| 003 准 Riemann 假设（零点自由 Re s>7/8） | YES | 直接接到 `PNT_concepts/` / 素数定理形式化线 |
| 021 Jacobsthal 二次界 | YES | 素数间隙 / 筛法显式界 |

## E. 工具仓快检（GitHub API，2026-10-21）

| 仓库 | stars | 最近推送 | 观察 |
|---|---|---|---|
| openai/math | 15312 | 2026-10-12 | Apache-2.0；有 lean/、history.md、formalization.yaml；体量大，宜稀疏跟进 |
| frenzymath/HolomorphicAnosov | 10 | 2026-10-13 | 含 lakefile / Comparator，适合当形式化范本 |
| MechMath/MechMath-agent-team | 10 | 2026-09-11 | nl-prover / fl-prover / kb-manager 目录齐全，可抄生成-验证循环 |
| mrconter1/vibemathed | 31 | 2026-10-15 | MIT；社区策展站源码，作监听入口 |

## F. 本轮决策

本周只开 **一个** 最小沙盒，避免并行发散：

1. **首选**：family **102**（UGC / Max-Cut 硬度）— 密码与近似算法外溢最大  
2. **备选物理**：family **362** Vlasov–Maxwell  
3. **备选工程**：family **107** 或 **121**

下一步动作：

1. 稀疏检出 openai/math 中 102 对应 Lean 文件与 Comparator 配置  
2. 写 1 页「陈述卡」：假设、结论、对密码/近似算法的可迁移点、未验证风险  
3. 若本机 Lean 环境未就绪，先完成陈述卡 + 依赖清单，不硬跑全量 build  
4. 同步扫 Ax-Prover / QKD 形式化文献，单列「密码专用」跟进清单（后量子 vs 对称，待用户点选）
## G. 材料 / 微晶玻璃 & 复杂网络（扩口径）

用户背景：研究生阶段做过**微晶玻璃**；同时可关注物理材料与复杂网络。AI 数学产出不会直接写材料牌号，需做「关键词翻译」。

### 材料可映射命中（openai/math 首轮）

| 族 | Lean | 摘要 | 微晶玻璃 / 材料翻译 |
|---|---|---|---|
| 213–214 临界渗流 / 非唯一性 | YES | 准传递图上 Benjamini–Schramm 猜想 | 晶化连通团簇、连通临界点类比（作数学模型，不作工艺结论） |
| 212 平面 first-passage 无双无穷测地线 | YES | 首达渗流几何 | 生长前沿 / 最短路径显微结构 |
| 221 / 234 自旋玻璃公式 | YES | Mézard–Parisi 等 | 无序能量景观类比（玻璃态统计力学） |
| 211 随机平面图几何相图 | YES | FK 平面图 → LQG / CRT | 随机介质几何 |
| 224 Poisson–Voronoi 渗流普适性 | no/部分 | Cardy 公式等 | Voronoi 晶粒几何 ↔ 显微组织 |

### 复杂网络可映射命中

| 族 | Lean | 摘要 | networkx / 网络线 |
|---|---|---|---|
| 177 bounded-degree coboundary expanders | YES | 高维 expander 构造 | 扩展性 / 鲁棒性文档或实验 |
| 178 非二分 Ramanujan 图 | no | 固定度确定性构造 | 谱图算法对照 |
| 113 / 120 匹配计数与近线性匹配 | 部分 | FPRAS / 近线性精确匹配 | 可评估是否值得提 networkx 性能/测试议题 |
| 131 graph switch 快速混合 | YES | 给定度序列随机图采样 | 配置模型采样 |
| 175–176 Kahn–Kalai / 期望阈值 | YES | 随机图出现阈值 | 阈值现象笔记 |

### 扩口径后的跟进优先级（仍只开 1 个主沙盒）

1. 主沙盒仍建议 **102**（外溢面最大）
2. **材料旁路**：用 213 渗流 + Voronoi 条目写「微晶玻璃可读卡片」——只翻译接口，不宣称材料新发现
3. **网络旁路**：把 177/131 与现有 `networkx` 行对照，能落 issue/docs 再动

## H. 收口：基础理论优先（AI agent 好论证）

按用户补充：多从基础、理论切入；应用（含微晶玻璃、复杂网络）后挂。

本周主沙盒仍是 **family 102**（UGC + 最优近似阈值）——纯理论、陈述清晰、Lean 标注有、外溢面大。

材料 / 网络不另开主沙盒：只在雷达里保留「可翻译接口」；真要写材料卡片，也先写渗流 / Voronoi / 自旋玻璃的**数学陈述卡**，再写一句「可能对应显微组织网络的何种接口」，禁止写成工艺结论。

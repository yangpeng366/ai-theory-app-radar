# Progress

按时间倒序追加。每轮最少写：做了什么、证据、下一步。

## 2026-10-29 · 第二轮雷达：可执行复核跑通 + 形式化差距量化

- 触发：头条《我们完了，奥特曼曝数学家5天心路反转，陶哲轩：英雄时代退场》→ 定位第 48 条（`recvwuSTYb28w0`）
- 核实 openai/math：16 879★，719 篇 / 372 族；10/06 首版 722 篇，10/07 撤回 3 篇、修订 14 篇；10/26 新增族 378（证伪 ETH）与族 079（波方程局部光滑性）
- 外部通道：Simons 基金会 1500 万美元计划（公开提案流程，OpenAI 出 500 万）；`mathcommunity/oai-math-revised` 社区仓库（可申请 reviewer）
- 过滤口径扩为四桶，新增「可执行复核」与「形式化差距」
- 产出：`radar/2026-10-29-second-pass.md`、`radar/2026-10-29-family266-mub-dim6-review.md`、`repro/mub-dim6/`（取件脚本 + 复核规程）
- 证据：族 266 第三方复核三段全过——数值一致性 PASS（249 878 中心 / 151 744 086 对 / 22 379 fine / 88 批 / 163→1 127→0）、ABI 契约探针 PASS×2、`coverSeeds::run` 两处 `pow(...,2)` 指令级核查为六步独立舍入 binary64 运算
- 边界：未重跑全量数值；未验证归档与历史运行一致性（包内无哈希清单与机器记录）；Lean 仍只证「至多 5 个族」，论文「至多 3 个」未形式化
- 下一步：族 378 形式化差距说明（Lean 界 vs 论文界、编码换算）；投 `oai-math-revised` 修订意见；申请 Lean 工具链
- 取件经验：整仓 900MB 不克隆；jsDelivr 拒发 >20MB，`gh-proxy.com` 支持 Range 可分块；`raw`/`codeload` 当日时断时续，`api` 可达

## 2026-10-21 · 建仓 + 首轮雷达

- 新建本仓库，迁入流水线文档与首轮筛查
- 飞书行 `recvwuSTYb28w0` 已建；口径：基础理论优先、应用后挂
- 监听快检：openai/math / VibeMathed / HolomorphicAnosov / MechMath
- 下一步：family 102 陈述卡（假设 / 结论 / 风险 / 外溢）
## 2026-10-21 · 开源到 GitHub

- 补 LICENSE (MIT) / CONTRIBUTING / 公开 README
- 目标远程：https://github.com/yangpeng366/ai-theory-app-radar
- 用途：网络协作推进雷达、陈述卡与流水线

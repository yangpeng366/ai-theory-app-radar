# 第四轮（2026-11-01）：族 266 绿灯坐实 + 两处真缺陷 + 上游增量监听固化

日期：2026-11-01
仓库：[yangpeng366/ai-theory-app-radar](https://github.com/yangpeng366/ai-theory-app-radar)（公开仓，`main`）
飞书行：`recvwuSTYb28w0`（AI理论→密码/物理/材料/网络应用雷达）
上一轮（2026-10-30 23:31 起）因会话失效夭折，产物滞留未提交；本轮先核验、再落地。

---

## 一、一句话结论

> 族 266 的「一键绿灯」**此前从未真正通过**：本地缓存的 `fine.bin` 被截断在 25 165 824 字节（真实 33 746 388 字节，缺 8.58 MB），
> 校验器读到的是残缺记录却仍报 PASS。本轮补齐取件后校验器实跑 PASS、12 个关键文件哈希全中，绿灯这才**坐实**。
> 同时查出并修掉两处**真缺陷**：(1) 已提交的取件脚本没有大文件通道，绿灯从未被实跑验证就写进了纪要（残缺数据也能拿 `PASS`）；(2) 2026-10-29 复核卡的 `atlas.cpp`
> sha256 前缀少记一位，导致上游漂移检测恒误报 1 处 `CHANGED`。
> Lean 4.34.1 工具链已在 WSL 装好并**实测可编译**；上游 `CONTENTS.md` / `history.md` 自 10-30 起**字节未变**（无增量）。

---

## 二、本轮实测

### 2.1 族 266 绿灯（复跑，命令级证据）

```text
$ python repro/mub-dim6/selfcheck.py --pkg <cache>
validator: PASS within numerical consistency scope
counts: centers 249878 / checked pairs 151744086 / fine records 22379 / batches 88
pins: 12 matched, 0 changed
GREEN: family 266 package is internally consistent (PASS within numerical consistency scope)
```

取件侧：`python repro/mub-dim6/fetch-verification.py --out <cache>` → **308/308** 文件，
其中 `fine.bin` 经 `gh-proxy.com` 的 Range 分块（17 段）补齐，sha256 = `9b5b743b61907277fa6687a0ad45677bbcd0e4c9bd44a0d93d258253fb52923d`，
与 2026-10-29 复核卡记录**逐位一致**。

### 2.2 缺陷一：「绿灯」建立在残缺数据上（真缺陷，已修）

- 事实链：上游 `fine.bin` 为 33 746 388 字节；缓存里只落地 25 165 824 字节（= 24 MiB 整，恰是分块边界）。
  截断原因不是校验缺失，而是**上一轮（10-31）会话在取件中途夭折**，进程被杀留下半截文件。
- 为什么没被发现：已提交的取件脚本**根本没有大文件通道**——jsDelivr 对 >20 MB 直接 403（今日实测），
  raw 时通时断，`git/blobs` 兜底未走到；而 `fine.bin` 的体积正是 33.7 MB。
  于是 10-30 那轮「绿灯」**从未被实跑验证过**就写进了纪要。
- 真正的危险点：上游校验器只验「记录内部自洽」，**不验记录是否完整**，
  残缺数据也能拿到 `PASS`——绿灯可以名不副实。
- 修法：(a) 取件脚本新增 `gh-proxy.com` 的 Range 分块通道（10-31 加，本轮跑通），
  且每块校验返回长度与末块总长，不符即报错退出；(b) 本轮**实跑**校验器并核 12 个关键文件哈希，
  绿灯才算成立；(c) `selfcheck.py` 对 pin 不匹配直接报 `CHANGED`，不让半截文件无声通过。

### 2.3 缺陷二：复核卡 `atlas.cpp` 的 sha 前缀少一位（真缺陷，已修）

2026-10-29 复核卡该行记为 `dcbf2dbe1054c01`（**15 位**，其余各行均为 16 位），上游实为 `dcbf2dbe1054c01f`。
后果：`selfcheck.py` 的漂移检测恒报 1 处 `CHANGED`，久而久之会让人误以为上游动了。
已更正卡片，并改用 `digest.startswith(prefix)` 比对（短前缀不再误报）。

### 2.4 族 378 复跑（离线缓存，与上一轮逐项一致）

```text
$ python repro/family378-subexpsat/check-gap.py --src <cache>
checks: 24, FAIL: 0, confirmed gaps: 1
```

C19 仍为**文本等价**（1124 字符逐字相同），未升级为编译等价——见 2.5。

### 2.5 Lean 工具链：已装好，且**实测能编译**

| 项 | 实测值 |
|---|---|
| 工具链 | `leanprover/lean4:v4.34.1`（上游 `lean/lean-toolchain` 锁定版）落 WSL `/root/.elan/toolchains/`（3.0 GB） |
| 版本 | `Lean (version 4.34.1, x86_64-unknown-linux-gnu, commit 5045d005641…)` |
| 编译冒烟 | `import Std` 的示例文件 `lean Smoke.lean` **编译通过**（exit 0），`elan run leanprover/lean4:v4.34.1 lean --version` 正常 |
| 仍缺 | **Mathlib olean 缓存**（GB 量级）。上游族 378 模块 `import Mathlib`，故 C19 仍只能宣称文本等价 |

### 2.6 上游增量：**零**

`repro/monitor-upstream.py`（本轮新固化）以 2026-10-30 的取件为基线比对：

| 仓 | CONTENTS.md | history.md | manuscripts | families | max family | preprints/ 目录 |
|---|---|---|---|---|---|---|
| `openai/math` | **unchanged**（sha 逐位同） | **unchanged** | 721 → 721 | 373 → 373 | 378 → 378 | 751 |
| `mathcommunity/oai-math-revised` | 首次建基线 | 首次建基线 | 721 | 373 | 378 | 751 |

两仓 preprint 目录数、族号数、族号集合**完全一致**（751 / 373 / 最大 378），佐证 10-30 的结论：
社区 fork 与上游已同步，先前「差 2 篇 1 族」的说法确已作废。
自 10-30 至 11-01 两日，**上游无任何增量**。

---

## 三、本轮产物

| 文件 | 性质 |
|---|---|
| `repro/monitor-upstream.py` + `repro/upstream-snapshot.json` | 上游增量监听脚本与基线（可复跑） |
| `repro/mub-dim6/selfcheck.py` | 族 266 一键绿灯自检（修 pin 比对 + 截断检出） |
| `repro/mub-dim6/fetch-verification.py` | 取件脚本（修分块长度校验） |
| `docs/lean-toolchain-setup.md` | Lean 工具链落盘与环境说明（改为「已装好、能编译」） |
| `radar/2026-10-29-family266-mub-dim6-review.md` | 复核卡（更正 `atlas.cpp` sha 前缀） |
| `radar/2026-10-30-family378-formalization-gap.md` | 族 378 形式化差距说明（本轮复跑一致） |
| `radar/2026-10-30-oai-math-revised-review-draft.md` | 投社区的修订意见草稿（**尚未提交 PR**） |
| `radar/2026-10-30-third-pass.md` | 第三轮纪要（补 11-01 附注） |
| `radar/2026-11-01-fourth-pass.md` | 本文 |

---

## 四、边界声明（必随结论同读）

1. 族 266 的绿灯只说明**存档数值记录内部自洽**，**不是**归档认证，**不是** C++ 实现的证明，
   **不是**原编译器 / 硬件行为的验证；本轮亦**未**重跑论文的数值实验。
2. 族 378 的 Lean 侧判断仍为**源码文本**的机器核对，**不是**编译通过或证明正确性的证明；
   C19 仍是「文本等价」而非「编译等价」。
3. 上游计数（721 / 373 / 751）是**当日快照**（contents API 与 `CONTENTS.md`），上游会继续增长。
4. Lean 工具链**只影响结论能被表述得多强**，不改变任何一族的科学结论。
5. 本轮**未**向 `mathcommunity/oai-math-revised` 提交 PR（跨仓改动 + 通知外部，须用户拍板）。
6. 本轮**未**跑 `lake build`、**未**拉 Mathlib olean 缓存、**未**验证上游 PDF 数值实验。

---

## 五、下一步（自推）

1. **投稿（待用户拍板）**：把族 378 差距说明投 `mathcommunity/oai-math-revised`。草稿已就绪，
   姿态为「追加」而非替换社区已有的同族 `NOTES.md`（PR #60，chelsinchaos，2026-10-28）。
2. **补齐族 378 取件**：把 `SqrtLogSpace/NativeLargeEntry`、`ExecutionNativeFinal` 等执行层模块纳入
   `fetch-sources.py`，消除 C11 的 PART 与边界第 5 条。
3. **C19 升级（可选，成本高）**：拉上游 `lean/` 工程骨架 + Mathlib olean 缓存后 `lake build` 单模块，
   把「文本等价」升为「编译等价」；缓存 GB 量级，须单轮专做。
4. **下一轮巡检触发器**：跑 `python repro/monitor-upstream.py --with-community --deep`，
   看 `CONTENTS.md` / `history.md` 是否变动；有新族则按四桶过滤（可编译形式化 / 新算法 / 新理解 / 可执行复核）。

# 家族 266：维六恰三组互偏基（N(6)=3）· 陈述卡与第三方可执行复核

日期：2026-10-29  
来源：[openai/math](https://github.com/openai/math) `preprints/The-maximum-number-of-mutually-unbiased-bases-in-dimension-six-September-24-2026/`（作者标注 OpenAI，2026-09-24）  
飞书行：`recvwuSTYb28w0`（AI理论→密码/物理/材料/网络应用雷达）  
性质：**可执行复核（第三方复现成功）** + **形式化缺口（Lean 未证出论文上界）**

---

## 一、陈述卡

| 项 | 内容 |
|---|---|
| 陈述 | 复数六维空间 $\mathbb{C}^6$ 中，两两互偏的正交归一基最多 **3 组**：3 组存在，4 组不存在 |
| 解决对象 | Zauner 的维六互偏基猜想（$N(6)=3$），以及 Matolcsi–Ruzsa–Weiner 的 Fourier 消失猜想（同行姊妹篇，以精确 Fourier 证书给出） |
| 上界性质 | **计算机辅助**：在给定的 binary64 算术与编译器条件下，完整执行文档化的验证流水线，排除任意四组复基 |
| 下界性质 | 构造性：三组存在 |
| 形式化状态 | Lean 形式化 **仅证出「每个族至多 5 个成员」**，并证明order-six 复 Hadamard 矩阵（除 Tao 等价类外）的 Fourier 特征和消失；**未证出论文的「至多 3 个」上界，亦未覆盖计算机辅助部分** |
| 可复核性 | 上游随稿发布 `verification/saved-run/`：C++ 源码、命令记录、结果行、数值记录（.bin）、以及派生校验器 `check_records.py` |

**结论分级**：论文结论**尚未**被形式化验证，也**尚未**被第三方重跑全量数值；但其「存档数值记录内部一致性」已被第三方独立复现通过（见第三节）。

---

## 二、为什么先做这一族

1. **零 Lean 依赖**：`check_records.py` 只需 Python 3.9+，不需 Lean 工具链（本机当时未装 Lean/elan）。
2. **官方留了复核入口**：上游明确给出可执行校验路径，并主动说明「这不是历史归档的认证，不是 C++ 实现的证明，也不是编译器与硬件行为的验证」——边界写得很清楚，便于第三方照做而不越界。
3. **直击社区缺口**：陶哲轩 10/15 指出，AI 批量交卷后「谁来解释关键步骤、谁来回答同行的疑问、发现问题后谁来跟进」无人接手；Simons 基金会 10/15 的 1500 万美元计划明确资助「形式化验证项目」与「审阅标准」。本族正是该缺口的一个可操作样本。

---

## 三、第三方复核实测（本轮实跑）

### 3.1 取件（未克隆整仓）

openai/math 整仓约 900 MB，不宜克隆。改按目录取件：`execution/data`（19 个文件 + `batches/` 177 个）、`execution/results`（100 个）、`compiled-build/source`（8 个 C++）、`commands.json`、`check_records.py`。

网络要点：`raw.githubusercontent.com` / `github.com` / `codeload.github.com` 当日时通时断；`api.github.com` 可达但不稳定；`cdn.jsdelivr.net` 可用但对大于 20 MB 的文件拒发；`gh-proxy.com` 支持 Range 请求，本轮 33.7 MB 的 `fine.bin` 即由此分 17 段取回。

关键文件 sha256：

| 文件 | 字节 | sha256（前 16） |
|---|---|---|
| `execution/commands.json` | 46 908 | `e27de17eb16a447c` |
| `execution/check_records.py` | 18 229 | `565f4ee47ab7b7c4` |
| `execution/data/fine.bin` | 33 746 388 | `9b5b743b61907277` |
| `execution/data/centers.txt` | 7 339 546 | `c48bc9a2be1eb2cd` |
| `compiled-build/source/covout.cpp` | 5 286 | `2a7e6bf5ca485765` |
| `compiled-build/source/stageB.cpp` | 12 030 | `7e609a2f282d519a` |
| `compiled-build/source/stageC.cpp` | 17 471 | `60a1b10091852809` |
| `compiled-build/source/atlas.cpp` | 8 821 | `dcbf2dbe1054c01f` |
| `compiled-build/source/ub.cpp` | 11 557 | `bb031282340012e6` |
| `compiled-build/source/patchx.cpp` | 16 137 | `a78a1ab171d8c7f1` |
| `compiled-build/source/seed.cpp` | 3 514 | `3c6c7a7092230de2` |
| `compiled-build/build.sh` | 1 303 | `81dc6c71ecaa6511` |

> 2026-11-01 复核更正：上表 `atlas.cpp` 的 sha256 前缀原少记末位一位（15 位），已补为 `dcbf2dbe1054c01f`。
> 该错使 `selfcheck.py` 的上游漂移检测恒报 1 处 `CHANGED`（误报）。上游文件本身未变。

### 3.2 第一段：数值记录一致性校验（通过）

```text
python3 execution/check_records.py
```

实测输出（`PASS`）：

```json
{
  "result": "PASS within numerical consistency scope",
  "cover": { "centers": 249878, "checked_pairs": 151744086 },
  "coarse_records": [764, 774, 757, 788],
  "mid_records": 600,
  "fine_records": 22379,
  "batches": 88,
  "initial_C": { "done": 22379, "bad": 163, "graph": 0, "cap": 163, "over": 0, "cluster": 0 },
  "fallback_records": 1127,
  "final_C": [ {"done":282,"bad":0}, {"done":282,"bad":0}, {"done":282,"bad":0}, {"done":281,"bad":0} ],
  "children": 100, "data_files": 196, "result_files": 100
}
```

校验器实际核对了：解析完整与文件末尾、记录边界、四个 A 分片、B 段父子/产出计数、fine→batch 的 256 一批完整划分、C 段失败子序列的有序性、回退输入的 ASCII 序、终检 modulo-4 全覆盖且无未决记录。计数自洽：$88=\lceil 22379/256\rceil$，$1127=282+282+282+281$，初始未决 163 条全部进入 15 个回退批并被终检清零。

### 3.3 第二段：算术 / ABI 契约（通过，本机工具链）

```text
bash compiled-build/build.sh /tmp/mub-build
```

工具链：WSL2 Ubuntu-22.04，g++ 11.4.0，glibc 2.35，AMD Ryzen 7 5800H；编译参数取自上游脚本（`-O3 -march=native -ffp-contract=off`）。

实测：`arithmetic/ABI checks passed` ×2（`covrun` 默认方言与 `-std=gnu++17` 各一次）。探针 `abi-fp-probe.cpp` 静态断言并运行时校验：IEEE binary64（53 位有效数字）、`FLT_EVAL_METHOD == 0`、就近舍入、正确舍入的 `sqrt`、渐进下溢、无 fast-math / 重结合 / 收缩，另有小端、32 位 int、64 位 size_t 与 unsigned long 的 ABI 断言。

### 3.4 第三段：两处 `pow(...,2)` 的指令级核查（通过）

上游 VERIFY.md 要求：使用新跑结果作证据前，须查 `coverSeeds::run` 中两处 `pow(..., 2)` 是否按「缩放→平方→相减→开方→相加→再平方」逐步采用**分别舍入的 binary64** 运算；并明确「仅确认动态符号表里没有 `pow` 是不够的」。

实测（`objdump -d -C` 取 `coverSeeds::run` 函数体 1 296 行）：

- 源码两处 `pow`：`covout.cpp:100` `RN2=sq(1)*pow(R*n,2)-.0001;`、`covout.cpp:101` `T=pow(sqrt(RN2)+1.5,2);`
- 动态符号表：**无 `pow`**（仅 `U sqrt@GLIBC_2.2.5`），说明平方已被内联为乘法
- 函数体指令序列（节选）：

```text
5ec6: vmulsd %xmm0,%xmm1,%xmm1        # 缩放 R*n
5ecd: vmulsd %xmm1,%xmm1,%xmm0        # 平方（pow(x,2) 内联，独立舍入）
5ed1: vsubsd 0x2327(%rip),%xmm0,%xmm0 # 相减 .0001
5eec: vsqrtsd %xmm0,%xmm0,%xmm0       # 开方
5ef0: vaddsd 0x2318(%rip),%xmm1,%xmm1 # 相加 1.5
5efd: vaddsd 0x2303(%rip),%xmm0,%xmm0
5f1d: vmulsd %xmm0,%xmm0,%xmm0        # 第二次平方
```

六步齐全、互不合并（`-ffp-contract=off` 亦阻断 FMA 收缩），满足上游要求。

---

## 四、边界声明（必须随结论同读）

上游 VERIFY.md 原话已很克制，本轮照抄边界，不外扩：

1. 本轮**验证的是存档数值记录内部自洽**，**不是**对历史归档的认证。
2. 本轮**未重新执行**那套数值程序（覆盖 249 878 个中心、151 744 086 对检查的全量计算），因此**未**验证 C++ 实现本身，也**未**验证原运行环境与编译器的行为。
3. 本轮编译发生在**我方工具链**（g++ 11.4.0 / glibc 2.35 / Ryzen 7 5800H / `-march=native`），与原 10 月 4 日那次运行的机器/编译器**未必相同**；`-march=native` 本身即机器相关。
4. 上游 README 称「清单对当前仓库中的 C++ 源码做了哈希、数值记录与 10 月 4 日那次运行一致」，但本包内**不含**哈希清单与归档元数据（VERIFY.md 明示不含 hash checks / archive inventories / machine records），故**该条一致性声明本轮无法独立核验**。
5. 形式化缺口未被本轮触及：Lean 侧仍只到「至多 5 个」，论文「至多 3 个」的上界在本包中**没有**形式化证明。

**因此本族当前的正确表述是**：*存档数值记录的一致性已由第三方独立复现通过；算术契约与关键平方序列在本机工具链上成立；论文上界的形式化与全量重算两项仍缺。*

---

## 五、应用外溢（按第48条口径：后挂，不越界）

| 桶 | 落点 | 成熟度 |
|---|---|---|
| 密码 | MUB 与量子态制备/态判别、随机数生成器的无偏性构造；维六恰三基给 SIC-POVM 类构造划出硬上界 | 仅接口级 |
| 物理 | 与自旋玻璃/准长程序参量的 Fourier 消失判据相邻（见姊妹篇 Fourier-vanishing 证书） | 仅接口级 |
| 工程 | 计算机辅助证明的**发布规范**：源码 + 存档记录 + 校验器 + 边界声明四件套，是「AI 产出的可复核证据包」的可复制模板 | 已可复用 |

最后一栏是本族对本仓最大的外溢：它给出了**「AI 数学结果如何被第三方审读」的现成样板**，正对 Simons 计划中「formal verification projects」与「standards for reviewing」两项。

---

## 六、下一步

1. 把上述复核规程固化进 `repro/mub-dim6/`（取件脚本已就位），供他人一键复跑。
2. 若拿到 Lean 工具链（本机 C 盘余量紧张，暂未装 elan/Lean 4），则对 `lean/docs/266.md` 所述「至多 5 个」与论文「至多 3 个」的缺口写一份**差距说明**，投 `mathcommunity/oai-math-revised` 社区（可申请 reviewer：admin 邮箱见该仓 README）。
3. 形式化本身超出单轮能力；改为**投稿式协作**：把差距说明与复跑脚本作为社区贡献，而非自造新证明。

# 复现：族 266「维六恰三组互偏基」的第三方可执行复核

本目录给出复跑路径，不搬运上游二进制与数值数据。  
详细结论见 [`radar/2026-10-29-family266-mub-dim6-review.md`](../../radar/2026-10-29-family266-mub-dim6-review.md)。

## 一、取件

```bash
python3 fetch-verification.py --out ./mub-dim6-verification
```

脚本按上游目录清单逐文件取 `execution/data`、`execution/data/batches`、`execution/results`、`compiled-build/source`，并输出带 sha256 的 `_manifest.json`。

取件通道按「可用性」降级：

1. `cdn.jsdelivr.net/gh/openai/math@main/...` —— 快，但拒绝大于 20 MB 的文件（`fine.bin` 33.7 MB 即被拒）。
2. `raw.githubusercontent.com/openai/math/main/...` —— 权威，偶发不可达。
3. GitHub `git/blobs` API —— base64，用于大于 20 MB 的单文件。

若 `raw` 与 `api` 同时不通，可用支持 Range 的镜像分块拉大文件，例如：

```bash
# 17 段 × 2 MB 取 fine.bin，再按序拼接
BASE="https://gh-proxy.com/https://raw.githubusercontent.com/openai/math/main"
P="preprints/The-maximum-number-of-mutually-unbiased-bases-in-dimension-six-September-24-2026/verification/saved-run/execution/data/fine.bin"
curl -r 0-2097151 "$BASE/$P" -o part00   # 依此类推，末段收尾
```

整仓约 900 MB，**不建议克隆**。

## 二、第一段：数值记录一致性校验

```bash
cd mub-dim6-verification
python3 execution/check_records.py
```

上游要求 Python 3.9 以上；校验器只读 `execution/data/`、`execution/commands.json`、`execution/results/`。  
2026-10-29 实测结论：`PASS within numerical consistency scope`（249 878 中心 / 151 744 086 对检查 / 22 379 条 fine / 88 批 / 初始未决 163 → 回退 1 127 → 终检零未决）。

## 三、第二段：算术与 ABI 契约

需 x86-64 GNU/Linux（探针源码以 `#error Requires x86-64 GNU/Linux` 与 `#error Requires GNU GCC C++ compiler` 硬性拒绝其他平台）：

```bash
bash compiled-build/build.sh /tmp/mub-build
```

脚本会依次编译并**运行** `abi-fp-probe`，两次均应输出 `arithmetic/ABI checks passed`，随后产出 `covrun` / `arun` / `brun` / `crun` 与 `covrun.dynamic-symbols.txt`、`covrun.disassembly.txt`。编译参数取自上游：`-O3 -march=native -ffp-contract=off`。

2026-10-29 实测环境：WSL2 Ubuntu-22.04，g++ 11.4.0，glibc 2.35，AMD Ryzen 7 5800H —— 两项探针均通过。

## 四、第三段：两处 `pow(...,2)` 的指令级核查

上游 VERIFY.md 明确要求：仅确认动态符号表中没有 `pow` **不够**，须查 `coverSeeds::run` 中「缩放 → 平方 → 相减 → 开方 → 相加 → 再平方」六步是否各为独立舍入的 binary64 运算。

```bash
objdump -d -C /tmp/mub-build/covrun > /tmp/covrun.disassembly.txt
# 定位 <coverSeeds::run(...)> 函数体（到下一个空行为止）
grep -n 'pow' /tmp/mub-build/covrun.dynamic-symbols.txt    # 应无 pow
```

2026-10-29 实测：源码两处 `pow` 位于 `covout.cpp:100-101`；动态符号表无 `pow`；函数体指令序列为
`vmulsd`（缩放）→ `vmulsd`（平方）→ `vsubsd`（相减）→ `vsqrtsd`（开方）→ `vaddsd`（相加）→ `vmulsd`（再平方），六步齐备且未被合并。

## 五、边界（复跑时同读）

- 校验通过**只**说明存档数值记录内部自洽；**不是**历史归档的认证，**不是** C++ 实现的证明，**不是**编译器与硬件行为的验证。
- 第二、三段发生在**本机工具链**上；`-march=native` 使二进制机器相关，与原运行环境未必相同。
- 本包不含哈希清单、归档元数据与机器记录，故上游「数值记录与 10 月 4 日那次运行一致」一句**本轮无法独立核验**。
- 族 266 的 Lean 形式化只证到「至多 5 个族」，论文「至多 3 个」上界**尚未**形式化。

## 六、许可与出处

上游 openai/math 为 Apache-2.0。本目录只含自写取件脚本与规程说明；数值数据、C++ 源码与校验器均从上游按原样取用，版权归 OpenAI。若二次分发上述件，请保留上游 LICENSE 与出处。

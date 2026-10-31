# 复现：族 266「维六恰三组互偏基」的第三方可执行复核

本目录给出复跑路径，不搬运上游二进制与数值数据。  
详细结论见 [`radar/2026-10-29-family266-mub-dim6-review.md`](../../radar/2026-10-29-family266-mub-dim6-review.md)。

## 零、一键自检（绿卡）

```bash
python3 selfcheck.py --fetch
```

一条命令完成取件 → 哈希比对 → 上游校验器实跑 → 绿灯判定：

```text
validator: PASS within numerical consistency scope
counts: centers 249878 / checked pairs 151744086 / fine records 22379 / batches 88
pins: 12 matched, 0 changed
GREEN: family 266 package is internally consistent
```

退出码：`0` 绿灯（校验器 PASS）/ `1` 红灯（校验器失败或关键文件缺失）/ `2` 环境未就绪。
`selfcheck.py` 另做一件校验器不做的事：把 12 个关键文件（`commands.json`、`check_records.py`、`fine.bin`、`centers.txt`、6 个 `.cpp`、`build.sh`）
的 sha256 前 16 位与 2026-10-29 复核卡记录的取值逐一比对，上游若已改动会直接报 `CHANGED` 而不是无声跑过。
加 `--abi` 可在 Linux 上顺手编译并运行 `abi-fp-probe`（第二段的算术/ABI 契约）。

> **2026-11-01 复核更正（两条真缺陷，勿据旧记录判读）**
>
> 1. `atlas.cpp` 的 sha256 前缀原少记末位一位（15 位），已更正为 `dcbf2dbe1054c01f`；
>    比对改为 `digest.startswith(prefix)`，短前缀不再被误报成上游漂移。
> 2. 2026-10-30 那轮取件在 `fine.bin` 处被中断，落地 25 165 824 字节（上游真实 33 746 388 字节，缺 8.58 MB）。
>    上游校验器只验「记录内部自洽」，**不验记录是否完整**，故残缺数据也能拿到绿灯。
>    取件脚本现已校验每个 Range 分块的返回长度与末块总长，不符即报错退出。
>
> 修好后的一次实测（2026-11-01）：
>
> ```text
> validator: PASS within numerical consistency scope
> counts: centers 249878 / checked pairs 151744086 / fine records 22379 / batches 88
> pins: 12 matched, 0 changed
> GREEN: family 266 package is internally consistent
> ```

## 一、取件

```bash
python3 fetch-verification.py --out ./mub-dim6-verification
```

脚本按上游目录清单逐文件取 `execution/data`、`execution/data/batches`、`execution/results`、`compiled-build/source`，并输出带 sha256 的 `_manifest.json`。
  2026-10-30 修订：旧版脚本把目录**拍平**写入目标目录、且漏取 `execution/commands.json`、`execution/check_records.py`、`compiled-build/build.sh` 与 `batches/`，
  导致按 README 运行的 `python3 execution/check_records.py` 必然找不到输入。现版**保留上游目录结构**，取件清单为 19 + 177 + 100 + 8 + 4 个文件。

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

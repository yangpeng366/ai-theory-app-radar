# Lean 工具链落盘与环境说明（族 266 / 族 378 的「编译级」结论）

日期：2026-10-30（2026-11-01 更新）
状态：**工具链已装好且实测可编译**；**Mathlib olean 缓存仍缺**，故本仓现有全部 Lean 侧结论仍是**文本级**，不是编译级。

## 一、为什么需要它

族 266 与族 378 的形式化差距判定，目前依赖对上游 Lean 源码的**文本核对**（定义、类型、引理陈述、字面量、字形几何）。
要把「挑战陈述 ≡ 解法陈述」从**文本等价**升级为**编译等价**，并为族 266「至多 5 个 vs 至多 3 个」的上界缺口准备边界填充，必须有 Lean 工具链。

## 二、目标版本与来源

| 项 | 值 |
|---|---|
| 目标工具链 | `leanprover/lean4:v4.34.1`（由上游 `lean/lean-toolchain` 锁定） |
| 发行包 | `lean-4.34.1-linux.tar.zst`（580 432 872 字节） |
| 官方地址 | `https://releases.lean-lang.org/lean4/v4.34.1/lean-4.34.1-linux.tar.zst` |
| 落盘位置 | WSL2 `Ubuntu-22.04` 的 `/root/.elan/`（`\\wsl$\Ubuntu-22.04\root\.elan`） |
| 物理落盘 | WSL 的 ext4.vhdx 位于 `F:\wsl\ubuntu2204\ext4.vhdx`，故工具链实际占 **F 盘**，不占 C 盘 |
| 安装脚本 | [`repro/lean-toolchain/fetch-lean-toolchain.sh`](../repro/lean-toolchain/fetch-lean-toolchain.sh)（分块拉取 + 解压落盘，幂等可续跑） |

## 三、当前状态（2026-11-01 实测）

```text
$ /root/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean --version
Lean (version 4.34.1, x86_64-unknown-linux-gnu, commit 5045d0056413266e57c625dcd7c365b10e377c52, Release)

$ /root/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lake --version
Lake version 5.0.0-src+5045d00 (Lean version 4.34.1)

$ du -sh /root/.elan/toolchains/leanprover--lean4---v4.34.1
3.0G

$ ls /root/.elan/toolchains/leanprover--lean4---v4.34.1/lib/lean | head
Init  Init.olean  Lake  Lake.olean  Lean  Lean.olean  ...
```

**编译冒烟（2026-11-01 实跑，`import Std`）：**

```text
$ cd /root/lean-smoke && lean Smoke.lean
2            # #eval (1 : Nat) + 1
exit=0
```

即：**核心库与 Std 可用，Lean 源码能被编译**；缺的只是 Mathlib。

**调用方式（两个坑）：**

1. **elan 没有生成 shim**：`/root/.elan/bin/` 下只有 `elan` 本身（因为工具链目录是手工落盘的，
   `elan toolchain install` 从未跑过，elan 不认为需要建 shim）。
   可用 `elan run leanprover/lean4:v4.34.1 lean --version`（实测可用），
   或直接用绝对路径 `/root/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean`。
2. **`$PATH` 被 pwsh 吃掉**：`wsl -e bash -lc "export PATH=...:$PATH"` 中 `$PATH` 会被 **PowerShell** 先展开为空，
   导致 WSL 内只剩 `/root/.elan/bin`，`tail`、`cat` 等全部 `command not found`。
   正确写法是**外层用单引号**：`wsl -e bash -lc 'export PATH=/root/.elan/bin:$PATH; ...'`。

## 四、已踩的坑

1. **`nohup` 不存在**：本机 WSL 镜像（Ubuntu-22.04）精简，`nohup` 报 `command not found`。改用 `bash -lc '... &'` 后台化。
2. **elan 的自定义 URL 参数被忽略**：`elan toolchain install <name> <url>` 仍按发行版默认源下载（`releases.lean-lang.org`），
   并不会走 `gh-proxy.com` 镜像。因此若要走镜像，得改 `ELAN_DIST_SERVER` 或直接手工分块下载后落盘。
3. **不能用 tar 包路径直接 `elan toolchain install`**：`elan toolchain install /path/xxx.tar.zst` 会失败，elan 要的是**已解压的目录**
   （含 `bin/lean`）。可行路径是：解压到 `/root/.elan/toolchains/leanprover--lean4---v4.34.1`，再 `elan default leanprover/lean4:v4.34.1`。
4. **官方源太慢**：走 `releases.lean-lang.org` 实测约 180 KB/s，580 MB 需约 1 小时；
   改用 `gh-proxy.com` 的 Range 分块（4 MB/段）实测可用，见安装脚本。
5. **`tar --zstd` 需要 `zstd` 二进制**：脚本里 `apt-get install -y zstd` 失败也要继续（末尾有 `|| echo` 兜底），
   否则整个安装会挂在解包那一步。

## 五、工具链装好之后还差什么

`lean/OAI/Algorithms/SubexponentialSAT/` 下的模块 `import Mathlib`（例：`ComparatorChallenges/SubexponentialSAT.lean` 第一行即 `import Mathlib`）。
因此「编译级」结论还需要 **Mathlib 的 olean 缓存**：

```bash
cd <openai/math 的 lean 目录>
lake exe cache get      # 拉取已编译的 Mathlib olean
lake build              # 或只构建目标模块
```

该缓存体积在 GB 量级，是把「文本级」升级为「编译级」的主要成本，也是本项尚未完成的部分。
另需把上游 `lean/` 的工程骨架（`lakefile.lean` / `lake-manifest.json`）一并取回，当前取件清单不含它们。

## 六、本轮结论（边界声明）

1. 本仓目前**仍然没有**任何「Lean 编译通过上游族 266 / 族 378 模块」的结论；已验证的只是**核心库 + Std 可编译**。
2. 族 378 的 C19 检查目前只能宣称「挑战陈述与解法陈述**逐字相同**」，**不能**宣称「二者编译为同一陈述」。
3. 工具链安装属环境准备，**不改变**任何一族的科学结论；它只决定结论能被表述得多强。

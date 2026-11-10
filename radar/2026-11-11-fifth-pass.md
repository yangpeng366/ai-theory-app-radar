# 第五轮（2026-11-11）：C11 判定缺陷修复 + 族 378 执行层取件到 2088 个模块

日期：2026-11-11
基线：`a95e622 feat(fetch): pin the upstream ref to a commit sha in the manifest`（工作区干净）
上游：`openai/math` @ `4eaee87548250b2682affda7d05d947c05554bae`（`refs/heads/main`，与本轮 manifest 的 `ref_resolved` 一致）

## 一、三句话结论

1. **上游零增量**：`openai/math` 与 `mathcommunity/oai-math-revised` 的 `CONTENTS.md`、`history.md` 均 `unchanged`（721 篇 / 373 族 / 预印本目录 751），快照无需更新。
2. **C11 的 PART 有一个结构性缺陷**：判定把「已取模块集合」存成斜杠路径、却用点号模块名去比较，两者永不相等，**任何有 `OAI.*` import 的树都必然 PART**；本轮已修（`check-gap.py:320-347`）。
3. 修好之后 C11 的真实状态是 **BLOCKED（预算内取不完）**：2088 个已取模块里仍有 330 条未解析 import、290 个缺失模块（**全部在族内子树**，族外 0 条），290 个模块经 Range 探测**全部存在**（HTTP 206，合计 2 402 523 字节），不是 URL 失效；按实测收敛率补齐还需约 1700 个模块、50–60 分钟连续取件，超出本轮单命令 10 分钟预算。

## 二、monitor-upstream：两仓无增量

```text
$ python repro/monitor-upstream.py --with-community --deep
== openai/math ==
  CONTENTS.md: unchanged
  history.md: unchanged
  manuscripts: 721 -> 721 | families: 373 -> 373 | max family: 378 -> 378
  preprints/ directories: 751 -> 751
== mathcommunity/oai-math-revised ==
  CONTENTS.md: unchanged
  history.md: unchanged
  manuscripts: 721 -> 721 | families: 373 -> 373 | max family: 378 -> 378
  preprints/ directories: 751 -> 751

snapshot: D:\gitAll\ai-theory-app-radar\repro\upstream-snapshot.json
exit=0 elapsed=19.9s
```

两仓基线来自 2026-11-01 第四轮。**无变化即不写快照**（`--update` 未执行），
所以 `repro/upstream-snapshot.json` 本轮未改动。

## 三、C11 判定来自哪里

- 文件：`D:\gitAll\ai-theory-app-radar\repro\family378-subexpsat\check-gap.py`
- 判定块：**第 320–347 行**（`# C11: import closure inside the fetched subset.` 到 `PASS`/`PART` 两支）
- 关键行：**第 330 行** `fetched[rel[:-len(".lean")].replace("/", ".")] = rel`（修复后）；修复前是
  `fetched.add(rel[:-len(".lean")])`，存的是 `OAI/Algorithms/.../Final`，而第 335 行拿
  `import OAI.Algorithms....Final` 去 `in fetched`，**点号名与斜杠路径永不相等**。
- 取件清单不在 check-gap 里，而在 `repro/family378-subexpsat/fetch-sources.py` 的 `FILES`（19 个种子文件）；
  C11 判的是「已落盘树」的闭合性，与 manifest 无关。

修复前后的同一棵树（2095 文件 / 2088 个 `.lean`）：

| 版本 | C11 输出 |
|---|---|
| 修复前 | `5394 imports outside the fetched subset` — 即**所有** `OAI.*` import 边都被判为未解析 |
| 修复后 | `330 unresolved imports over 2088 fetched modules (290 distinct missing modules)` |

修复同时把 `import A B`、`public import`、`meta import`、`import all` 的整行多模块写法纳入解析
（新增 `lean_imports()`，`check-gap.py:169-187`）；旧的 `^import\s+(\S+)` 只取该行第一个模块名。

## 四、执行层取件：从 19 个种子到 2088 个模块

命令（钉版 sha，三跳通道 + 失败即跳过该文件，不整仓 clone）：

```powershell
python repro/family378-subexpsat/fetch-sources.py --out D:\_tmp\f378-20261111 `
  --ref 4eaee87548250b2682affda7d05d947c05554bae --max-modules 400 --timeout 30 --tries 1
```

| 轮次 | 新增模块 | 本轮回执字节 | 结束状态 |
|---|---|---|---|
| 种子 | 19/19 | 1 728 710 | 截断（`--max-modules 0` 建档） |
| 1 | 400 | 6 867 019 | 截断，余 253 |
| 2 | ~686（被中断，未写 manifest） | — | 余 357–396 |
| 3 | 150 | 2 957 659 | 截断，余 396 |
| 4 | 220 | 3 201 330 | 截断，余 379 |
| 5 | 220 | 3 351 138 | 截断，余 357 |
| 6 | 400 | 5 494 812 | 截断，余 290 |

最终树：**2095 个文件 / 21 173 358 字节**（含 `paper.pdf` 887 884 B、`CONTENTS.md` 640 943 B），
其中 `.lean` 模块 **2088 个**；累计下载约 31 MB（含每轮重取的 19 个种子），**远低于 300 MB 上限**。

第 2 轮在中途被杀（manifest 未写），因此本轮新增 `repro/family378-subexpsat/seal-manifest.py`：
它把落盘树逐文件 sha256 封存成一份完整 `_manifest.json`，优先沿用取件时写下的记录
（`evidence: fetch-manifest`，419 条），其余按取件日志的字节数交叉核对后补录
（`evidence: fetch-log`，1676 条），任何对不上或无从追溯的文件直接报错退出。封存结果：

```text
files sealed: 2095 (419 fetch-manifest, 1676 fetch-log), 21173358 bytes
pin: repo=openai/math resolved=4eaee87548250b2682affda7d05d947c05554bae source=arg-sha
```

于是 C1 从「只核 19 个种子 / 本轮 419 条」升级为「核全树 2095 个文件」，不再有大片未登记的文件。

## 五、C11 结论：BLOCKED（取件规模超出本轮预算）

- 已取：2088 个模块；未解析 import 330 条，缺失模块 290 个，**全部位于 `OAI.Algorithms.SubexponentialSAT.*`**，
  族外缺失 0 条 —— 说明树对外是闭合的，缺口是族自身实现库的深层依赖。
- Bitable 点名的执行层模块已在树内：`SqrtLogSpace/NativeLargeEntry.lean`（7 119 B）、
  `SqrtLog/ExecutionNativeFinal.lean`（1 737 B）、`SqrtLogSpace/NativeLeaf.lean`、`SqrtLog/ExecutionClosure.lean` 等。
- 阻塞清单：`repro/family378-subexpsat/c11-frontier-20261111.tsv`，290 行，字段
  `module / bytes / status / channel / url`，合计 2 402 523 字节。
  探测方式是最省的 Range 通道 `GET .../lean/<path>.lean` + `Range: bytes=0-0`，读 `Content-Range` 取总长，
  **不下载正文**：290/290 返回 `206`，无 404、无超时 —— 即 URL 与钉版都有效，**不是取件不可行，是取不完**。
- 收敛率实测：取 400 个模块，缺口只从 357 降到 290（每取 1 个只补掉 0.17 个缺口）。
  按此外推，补齐 290 个缺口仍需约 1700 个模块、50–60 分钟连续取件；单命令 10 分钟上限
  （本轮最长一条 809 s 已触顶并如实记录）之下无法完成，故**不把状态写成 PASS 或 FAIL**。

复跑（一条命令，续跑式：从落盘树继续，已取模块不重取）：

```powershell
python repro/family378-subexpsat/fetch-sources.py --out D:\_tmp\f378-20261111 `
  --ref 4eaee87548250b2682affda7d05d947c05554bae --max-modules 400 --timeout 30 --tries 1
python repro/family378-subexpsat/seal-manifest.py --src D:\_tmp\f378-20261111 --log <本批日志>
python repro/family378-subexpsat/check-gap.py --src D:\_tmp\f378-20261111
```

仍然取不完时，`closure-frontier.py` 会重新给出带 URL 与字节数的阻塞清单，C11 会稳定报 PART 并给出缺口数。

## 六、其余 23 项复核（同一棵树，`checks: 24, FAIL: 0, confirmed gaps: 1`）

`C1 PASS 2095 files / 21 173 358 bytes`、`C7 解法 0 处 sorry`、`C10 30/30 定义语义一致`、
`C19 挑战陈述 ≡ 解法陈述（1124 字符）`、`C23 GAP（`m ≤ Dn` 锐化仍无对应陈述）` 等**均与第四轮一致**，
取件面扩大后没有出现新的 FAIL，说明前几轮的陈述级结论不是「没取到才看不出来」。

## 七、本轮改动

| 文件 | 性质 |
|---|---|
| `repro/family378-subexpsat/check-gap.py` | 修 C11 判定缺陷（斜杠路径 vs 点号模块名）+ 完整 import 语法解析 |
| `repro/family378-subexpsat/seal-manifest.py` | 新增：把多轮取件封存成整树 manifest（逐文件 sha256 + 取件日志字节核对） |
| `repro/family378-subexpsat/closure-frontier.py` | 新增：算出缺失模块清单，用 Range 探测大小与可达性，输出 TSV |
| `repro/family378-subexpsat/c11-frontier-20261111.tsv` | 新增：本轮阻塞清单（290 行） |
| `repro/family378-subexpsat/README.md` | 更新 C11 语义、实测数字与新脚本用法 |
| `radar/2026-11-11-fifth-pass.md` | 本文 |

## 八、边界（必随结论同读）

1. C11 是**取件闭合性**检查，不是编译检查；本轮仍未 `lake build`、未拉 Mathlib olean，C19 仍只是文本等价。
2. C11 = PART / 工作项 = BLOCKED 只说明「族实现库未取全」，**不说明**上游缺少这些模块：290 个缺失模块全部探测到 206。
3. `seal-manifest.py` 的 1676 条记录里，字节数来自取件日志、sha256 在封存时计算；C1 对这部分是
   「树内一致性 + 与日志字节数一致」，强度低于取件时即写下的 419 条（`evidence: fetch-manifest`）。
4. 第 2 轮取件被中断，manifest 由封存脚本补齐，取件本身未重跑；若要求「一次运行一份 manifest」，需重取约 21 MB（约 1 小时）。
5. 上游计数（721 / 373 / 751）是 2026-11-11 当日快照，上游会继续增长。

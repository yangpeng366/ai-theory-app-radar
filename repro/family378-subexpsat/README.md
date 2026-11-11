# 复现：族 378「证伪 ETH」的形式化差距核查

本目录给出复跑路径，不搬运上游 Lean 源码与论文 PDF。  
详细结论见 [`radar/2026-10-30-family378-formalization-gap.md`](../../radar/2026-10-30-family378-formalization-gap.md)，
面向社区的投稿草稿见 [`radar/2026-10-30-oai-math-revised-review-draft.md`](../../radar/2026-10-30-oai-math-revised-review-draft.md)。

## 一、取件

```powershell
# 推荐：钉住 commit sha（同一份 manifest 跨天可字节级复现）
python fetch-sources.py --out ./f378 --ref 4eaee87548250b2682affda7d05d947c05554bae

# 日常：给分支名，脚本先解析成 sha 再取件
python fetch-sources.py --out ./f378 --ref main

# 离线 / 内网镜像：不调 commits API，--ref 原值直接使用
python fetch-sources.py --out ./f378 --ref main --no-resolve
```

**只有钉 sha 才能复现。** `main` 是会动的；同一份 manifest 昨天取、今天取，字节不同也无法证明「不是同一份上游」。
所以脚本把 `--ref` 解析成一个 commit sha（`GET /repos/openai/math/commits/<ref>`，整轮只解析一次），
之后**三条通道全部用这个 sha**：`@<sha>` / `/<sha>/` / `?ref=<sha>`。sha 写进 manifest 的 `ref_resolved`，
两次运行的 `ref_resolved` 相同且 `files[].sha256` 逐条相同，才叫同源。

- 传 40 位十六进制 sha：直接使用，**不发解析请求**（`ref_source: arg-sha`）。
- 传分支/tag：解析成功即用 sha（`ref_source: api-commit`）。
- 解析失败（网络错误 / 403 / 404 / 响应非 JSON / 缺 `sha` 字段）：打印 `WARNING: ... NOT byte-pinned`，
  **退回用户给的原值继续取件**，manifest 记 `ref_resolved: null` + `ref_error` + `ref_source: unresolved`。
  不静默：这种运行看起来成功，但它**不是**钉版，不能拿去跟别的 manifest 比字节。
- `--no-resolve`：完全不碰 commits API，`--ref` 原值直接用于三通道，记 `ref_source: no-resolve`；
  供离线测试和内网镜像使用，`ref_resolved` 为 null（没有 sha 可证）。

**2026-11-11 验证过的 sha：`4eaee87548250b2682affda7d05d947c05554bae`（openai/math `refs/heads/main`）。**
该 sha 下种子清单 19/19、**1 728 710 字节**，与 9cb9d8c 那次实测的总字节数**逐字节相同**；
`--ref main`（`ref_source: api-commit`）与 `--ref 4eaee...`（`ref_source: arg-sha`）两轮取件的
19 条 `sha256` 集合完全一致，这就是「钉版生效」的可观测证据。

**取件量 = 种子清单 + `import OAI.*` 闭包（动态）。** 种子清单是 18 个 Lean/文本文件加 1 个论文 PDF
（共 19 个；2026-11-11 复核仍为 1 728 710 字节），只是**陈述级人工清单**，够读声明、不够编译：
上游 `preprints/…/paper.pdf`，`lean/OAI/Algorithms/SubexponentialSAT/` 下 12 个模块，
`lean/ComparatorChallenges/SubexponentialSAT.{lean,json}`，`lean/docs/378.md`，`lean/formalization.yaml`，
`lean/lean-toolchain`，以及仓根 `CONTENTS.md` 与 `history.md`。

默认还会按源码里的 `import` 递归补齐闭包，因此**最终文件数不写死**：它随上游改动和 `--max-modules` 变化，
以脚本末行 `fetched x/y files` 与 `_closure.json` 为准。

2026-11-11 两条实测回执（同一台 Windows 机器）：

- 三跳正常：`--max-modules 0 --timeout 30 --tries 1`，19/19、1 728 710 字节、64.2 s；其中 4 个文件 jsdelivr 失败后由 raw 补齐。
- 强制只走第三跳（前两跳指向关闭端口）：`--max-modules 0 --timeout 30 --tries 3`，19/19、1 728 710 字节、428.9 s；
  期间 `CONTENTS.md` 遇到一次 `IncompleteRead`（855 172/883 815 字节）被重试成功。该轮 API 侧明显偏慢，不能当基准。
  两次都是退出码 2——`--max-modules 0` 按设计把闭包截断，不是取件失败。
- 钉版两轮（`--max-modules 0 --timeout 30 --tries 1`）：`--ref 4eaee…` 34.1 s、`--ref main`（现解析成同一 sha）
  同样 19/19、1 728 710 字节，19 条 `sha256` 完全一致。两轮也都是退出码 2。

| 参数 | 默认 | 语义 |
|---|---|---|
| `--include-imports` / `--no-include-imports` | **开** | 是否递归拉齐 `import OAI.*` 闭包。默认开：种子清单缺证明主体模块，关掉后树不可编译、C11 必然是 PART |
| `--max-modules` | 400 | 闭包**新增**文件数上限，防止失控拉取；触顶时打印并记为 `truncated`。2026-11-11 实测该族闭包至少 348 个模块（含证明主体），200 会截断，故默认 400 |
| `--timeout` | 240 | 单请求超时（秒），三个通道各自计时 |
| `--tries` | 4 | 每通道尝试次数（403/404 不重试） |
| `--ref` | `main` | 取件的上游 git ref：分支名、tag 或 40 位 commit sha。给 sha 直接使用、不发解析请求；给分支/tag 先解析成 sha 再取件。**跨天复现必须给 sha** |
| `--no-resolve` | 关 | 跳过 commits API 解析，`--ref` 原值直接用于三通道（离线测试、内网镜像）。此时 `ref_resolved` 为 null，**不构成钉版** |
| `--no-paper` | 关 | 跳过 `paper.pdf` |

通道按可用性三跳降级，**每跳都要先过内容形状校验才写盘**。下表的 `<ref>` 是**解析后的钉版值**
（通常就是 commit sha；只有解析失败或 `--no-resolve` 时才是分支名）：

1. `cdn.jsdelivr.net/gh/openai/math@<ref>/<path>`（快，> 20 MB 拒收）
2. `raw.githubusercontent.com/openai/math/<ref>/<path>`（权威，易超时）
3. `api.github.com/repos/openai/math/contents/<path>?ref=<ref>`

**为什么第三跳是 contents 而不是 `git/blobs/<sha>`。** 2026-11-11 实测
`GET /repos/openai/math/git/trees/main?recursive=1` 返回 `truncated: true`（55 173 项、15.1 MB、16.6 s），
19 个种子里有 4 个（`lean/lean-toolchain`、`lean/formalization.yaml`、`lean/docs/378.md`、`paper.pdf`）
**不在 tree 里**，所以「路径 → sha」缓存无法覆盖种子清单；`git/blobs/<sha>` 这条路在本仓不成立。
contents 端点按路径直接解析，19 个种子全覆盖，含 887 884 字节 PDF 与 640 943 字节 `CONTENTS.md`。

**1 MB 边界。** contents 只在 1 MB 以下内联 base64；1–100 MB 返回 `encoding: "none"` + 空 `content`，
脚本用同一路径加 `Accept: application/vnd.github.raw` 重取原始字节。> 100 MB 没有 API 通路
（blobs 也止于 100 MB），直接报错而不是写半截文件；响应声明的 `size` 与实际字节不符同样按该通道失败。

**限流。** 未认证 `api.github.com` 为 60 次/小时，一次运行约 19+N 次请求（每个文件 1 次，> 1 MB 的文件 2 次；
本仓没有 > 1 MB 的种子，所以种子部分正好 19 次）。若 `--ref` 给的是分支名，**另加 1 次**解析请求（整轮只解析一次、
所有文件复用）；给 40 位 sha 或 `--no-resolve` 时为 0 次。403/429 **立即失败不重试**，错误里写明
`X-RateLimit-Remaining` 并提示设置 `GITHUB_TOKEN`。token 只作为 `Authorization` 头发送，
不进 URL、不进日志、不进 manifest。传输层截断（`IncompleteRead`）算可重试错误，报
`truncated body: N of M bytes read`，所以无 token 时建议 `--tries 2` 以上。

**内容校验（fail-closed）。** 200 不等于成功：jsDelivr 与 raw 都会用 200 返回 HTML 错误页/限流页。
脚本按**请求路径的扩展名**断言真实形状，不通过即视为该通道失败并继续下一跳，错误里带
「疑似错误页」与前 80 字节：

| 扩展名 | 断言 |
|---|---|
| `.lean` | 严格 UTF-8 解码成功，且不含 `<!DOCTYPE`/`<html>` |
| `.json` | 能 `json.loads` |
| `.pdf` | 以 `%PDF-` 开头 |
| `.md` / `.yaml` / `lean-toolchain` | 非空且非 HTML |

空响应一律拒绝；未知扩展名按「非空且非 HTML」处理。脚本写两个 JSON：

- `_manifest.json`：**顶层是钉版信息，`files` 是逐文件记录**。

  顶层字段：

  | 字段 | 含义 |
  |---|---|
  | `upstream_repo` | 固定 `openai/math` |
  | `ref_requested` | `--ref` 的原值（分支名、tag 或 sha） |
  | `ref_resolved` | 实际用于三通道的 40 位 commit sha。**只有真正拿到 sha 时才非空**：`--no-resolve` 与解析失败都是 null |
  | `ref_resolved_at` | 解析/记录钉版的时间，ISO 8601、UTC、`Z` 后缀（如 `2026-11-11T02:32:15Z`） |
  | `ref_source` | `arg-sha`（传的就是 sha）/ `api-commit`（commits API 解析而来）/ `no-resolve`（未解析）/ `unresolved`（解析失败，已退回原值） |
  | `ref_error` | 解析失败原因（已按 token 脱敏：token 一律替换为 `***`）；成功时为 null |

  `files[]` 每条：`remote`/`local`/`bytes`/`sha256`/`channel`，另加 `origin` 与 `via`。
  `channel` 是实际供字节的那一跳（`jsdelivr` / `raw` / `api-contents`）；`via` 按尝试顺序记录每一跳的结果
  （如 `jsdelivr -> URLError: ...`、`raw -> HTTPError: ...`、`api-contents -> ok`），失败记录也留 `via`，
  用来区分「超时」与「取到 HTML 被拒」。
  `origin="seed"` 表示种子清单里的文件；`origin="import"` 表示闭包新增，这类记录还带 `module`（Lean 模块名）
  与 `imported_by`（哪些模块 import 了它），所以闭包可复现、可追责。**只有成功取到的文件进 manifest**，
  失败项不进（否则指向不存在的文件会破坏 C1 校验）。
- `_closure.json`：`status` ∈ `complete` / `partial` / `truncated` / `skipped`，`complete` 布尔，`seed_files`、
  `seed_fetched`、`imported_files`、`failed`（模块名 + 通道错误 + 谁 import 的）、`not_fetched`（被 `--max-modules` 截住的剩余队列）。

退出码：`0` 全成功且闭包完整；`1` 有取件失败（种子或闭包，闭包因此不完整）；`2` 被 `--max-modules` 截断；
失败与截断同时出现按 `1` 报。**部分闭包不会静默成功**。

中断与重跑：manifest 只登记**本次运行**取到的文件，`--out` 里已有但未登记的旧文件不会被重新计入；
中断后建议换空目录重跑。种子清单在闭包开始前就先写一次 `_manifest.json`，
所以长闭包被中断时至少留下种子部分的 sha256。

### 取件脚本的离线测试

```powershell
python -m pytest repro/family378-subexpsat -q
python -m py_compile repro/family378-subexpsat/fetch-sources.py
```

`test_fetch_sources.py` 用 monkeypatch 替掉 `fetch_one` 或 `urllib.request.urlopen`，不联网，**共 32 例**。覆盖：二级依赖递归、已在盘模块不重拉、
非 `OAI.` 前缀不拉、`--max-modules` 截断可见、失败进 `failed`、`import` 四种语法变体，
以及 `--include-imports` 开/关与退出码 `0/1/2`；通道侧覆盖三跳降级顺序（jsdelivr 超时 → raw 404 → api 成功）、
任一通道返回 HTML 错误页被拒、PDF/JSON/Lean/文本四种形状校验、无 token 时 403 提示且 token 不落 manifest、
> 1 MB 改走 raw 媒体类型、截断体重试与字节数报错、`size` 不符判失败，以及 manifest 里的 `channel`/`via`。

钉版这一层占其中 9 例：传 40 位 sha 时**一次解析请求都不发**且三条通道 URL 里都是该 sha；传 `main` 时
**整轮只解析 1 次**并被所有文件复用；解析 403 时出 `WARNING`、退回原分支名、manifest 记 `unresolved`；
响应非 JSON / 缺 `sha` / 非对象时的错误路径；manifest 五个 ref 字段齐全且 `ref_resolved_at` 可解析为 UTC；
token 只出现在 `Authorization` 头、**不进 manifest 也不进 WARNING**（响应体回显 token 的极端情况也被脱敏）；
`--no-resolve` 不碰 commits API 且记 `no-resolve`。

整个目录另由 `conftest.py` 兜底：任何非 loopback 的 socket 连接与 DNS 查询在测试期间都被拒绝，
`test_offline_guard.py` 用 2 例证明这道闸门本身有效；加上 `test_check_gap.py` 的 9 例
（C16 两支 + C14 的 1 正 4 反 + C20/C21 的 SKIP 口径），`python -m pytest repro/family378-subexpsat -q` 共 43 例。

## 二、一键核查

```powershell
python check-gap.py --src ./f378
```

不需要 Lean 工具链，不需要 Mathlib，全部结论可由已发布源件回答。脚本分三段共 24 项检查：

| 段 | 检查项 | 判据 |
|---|---|---|
| 一、数据一致性 | C1–C11 | 取件 sha256、族号、声明名、定理落地、`sorry` 分布、公理白名单、定义漂移、import 闭合 |
| 二、算术与复杂度契约 | C12–C19 | 尺度定义、`rho` 阶、指数差、编码换算引理、编码界数值复核、`runtimeScale ≤ 4ρ` 数值复核、ETH 陈述形状、挑战陈述 ≡ 解法陈述 |
| 三、陈述级核查 | C20–C24 | 论文主定理指数、论文 `rho` 定义、上游自陈锐化、Lean 侧锐化缺失、差距是否小 `n` 假象 |

退出码 0 表示**没有 FAIL**；`SKIP` 与 `GAP` 不进退出码，但都出现在汇总行——有 SKIP 时行尾追加
`, skipped: N`，并多打一行 `incomplete: ...`。**科学判定（哪些论文段落被覆盖）以表格打印，不写进退出码**——本族的预期发现就是「确有一处差距」。

C11 的数字**取自当前这棵树**，不是常量：判据是 `check-gap.py` 打印的
`every OAI import resolves inside the fetched subset (N modules)` / `K unresolved imports over N fetched modules`，
`N` 由脚本现场数 `.lean` 文件得到，随闭包完整度变化。两个有记录的快照（同一上游 sha `4eaee875…`）：

| 快照 | 取件树 | C11 输出 | 判读 |
|---|---|---|---|
| 2026-11-11 第五轮 | 2088 个 `.lean`；`_closure.json` `status=truncated`、`not_fetched=290` | `330 unresolved imports over 2088 fetched modules (290 distinct missing modules)` | PART：闭包被 `--max-modules` 截断 |
| 2026-11-11 第六轮 | 3092 个 `.lean`；`_closure.json` `status=complete`、`not_fetched=0`、`failed=0`；manifest 99 文件 / 2 300 424 字节 | `every OAI import resolves inside the fetched subset (3092 modules)` | PASS：闭包闭合 |

复算方式（第二条打印出来的模块数就是上表数字的唯一来源，不要从文档抄）：

```powershell
python fetch-sources.py --out <cache> --ref 4eaee87548250b2682affda7d05d947c05554bae --max-modules 3000
python check-gap.py --src <cache>
```

判定顺序是「先看闭包状态，再看 C11 行」：`_closure.json` 的 `complete` / `not_fetched` 说明树是否被截断，
C11 行给出该树的未解析条数。**「3092」是第六轮缓存（`status=complete`）的读数**，缓存不在仓库内，
重建后数字可以不同（上游改动或 `--max-modules` 变小都会变），所以它是快照值而不是常量。
该轮完整回执见 [`radar/2026-11-11-sixth-pass.md`](../../radar/2026-11-11-sixth-pass.md)；
第五轮的 290 模块阻塞清单 `c11-frontier-20261111.tsv` 是那一轮的取证记录，闭包补齐后它描述的是
「当时缺什么」，不是当前缺口。

### C14/C20/C21 的判据细则

- **C14 指数差**（此前是无条件 PASS）：先从取件树读出 `SqrtLogSpace/rho` 的定义体，断言它仍是
  `n*(log2 log2 n)^2 / sqrt(log2 n)`（定义漂移即红）；再在 n=1e4…1e12 五个采样点上断言
  `rho(n)/论文主界 = log2 log2 n`（相对误差 1e-9）、`rho(n)/论文 m≤Dn 锐化 = 该比值的平方`、
  比值严格递增且 n=1e12 处 ≥ 5（Θ(log log n) 而不是 Θ(1)）。任一断言不成立即 FAIL；
  自测里 4 个反例分别打掉：Lean 定义丢平方、`rho` 退化成论文指数（无差距）、差距退化成常数、锐化列不再平方。
- **C20/C21（论文侧字形核查）**：PyMuPDF 是**硬依赖**，但缺依赖判 **SKIP** 而不是 FAIL/PART——
  缺的是工具而不是证据，判 FAIL 会把环境问题说成上游问题；SKIP 会写清原因并计入汇总行的
  `skipped: N` / `incomplete:` 提示，因此不会被误读成 24 项全过。缺 `paper.pdf`（例如 `--no-paper`
  或只取了种子的一部分）同样是 SKIP。PDF 能读、但定位不到 `Theorem 1.1` 的指数或 `rho` 的定义时判
  **FAIL**：那是来源不支持该断言（或抽取规则要人工过目），不是环境问题。补依赖：
  `python -m pip install pymupdf`。

多轮取件另有两个辅助脚本（不参与核对项计数，属取件与取证侧）：
`seal-manifest.py` 把落盘树逐文件 sha256 封存成一份完整 `_manifest.json`（C1 由“本轮取件”升为“全树”）；
`closure-frontier.py` 列出缺失模块，用 `Range: bytes=0-0` 探测 URL 与字节数，输出可引用的阻塞清单 TSV。

## 三、怎么读结果

- **PASS** = 机械检查成立（文本、字形、哈希、数值层面的可复算事实）。
- **PART** = 结论受取件范围所限，现在只有 C11 会这样判：它逐条核对 `import OAI.*` 是否落在已落盘树内，
  树被 `--max-modules` 截断（`_closure.json` 的 `status ∈ truncated/partial`）时必然有未解析 import。
  2026-11-11 之前的实现把已取集合存成 `OAI/.../Final` 斜杠路径、却用 `OAI.Algorithms...Final` 点号名比较，
  两者永不相等，于是**任何树都是 PART**，与取多少件无关；修复后（`check-gap.py` C11 段）缺口数字才有意义。
  第六轮闭包取完，C11 为 **PASS（3092 模块，`_closure.json` `status=complete`）**；用第五轮那棵截断的树复跑，
  它仍会如实报 PART 并给出 330/2088 的缺口数。
- **SKIP** = 这项检查在本机跑不起来（缺 `paper.pdf` 或缺 PyMuPDF），原因写在该检查行里，并计入汇总行的
  `skipped: N` 与 `incomplete:` 提示。**SKIP 既不是通过也不是 FAIL**：它声明「这轮不是完整的 24 项判定」。
- **GAP** = 确认为形式化差距（C23：`m ≤ Dn` 锐化界 `2^{O(n/√log n)}` 在取件范围内无任何对应陈述）。

C19「挑战陈述 ≡ 解法陈述」目前是**文本等价**：挑战文件与解法文件中 `exact_count_and_sat` 的类型部分逐字相同（1 124 字符）。
它是文本事实，**不是**编译事实——Lean 工具链尚未在本机装好（见 [`docs/lean-toolchain-setup.md`](../../docs/lean-toolchain-setup.md)）。

## 四、边界（复跑时同读）

1. 本轮**未运行** Lean 工具链，**未 `lake build`** 任何 Lean 文件；所有 Lean 侧判断来自**源码文本**的机器核对，**不是**编译通过或证明正确性的证明。
2. 本轮**未重跑**论文的数值实验，也**未验证**其正确性；本族不提供数值可执行包（对比族 266 的 `repro/mub-dim6/`）。
3. 论文侧断言取自 `paper.pdf`（2026-10-25 修订版）的字形与文本抽取，**未**与更早版本比对。
4. 「Lean 只证到 `rho`」的判断依据是上游 `lean/docs/378.md` 的自陈与本轮源码核对，二者一致；本轮**未**独立证明 `rho` 与论文主界**不等**——给出的是闭式反例族 `rho(n)/beta(n) = log2 log2 n > 1`（`n ≥ 16`）。
5. 「`m ≤ Dn` 锐化未形式化」按「**取件范围内未发现**」记账，而非「上游绝无」。

## 五、许可与出处

上游 openai/math 为 Apache-2.0。本目录只含自写取件脚本与核查脚本；论文 PDF 与 Lean 源码均从上游按原样取用，版权归 OpenAI。

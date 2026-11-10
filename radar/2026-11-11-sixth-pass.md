# 第六轮（2026-11-11）：import 闭包取完，C11 由 PART 转 PASS

日期：2026-11-11
基线：`902fe70 fix(family378): report C16 violations and add regression tests`（工作区干净）
上游：`openai/math` @ `4eaee87548250b2682affda7d05d947c05554bae`（与本轮 manifest 的 `ref_resolved` 一致，`ref_source=arg-sha`）

## 一、三句话结论

1. **C11 由 PART 转 PASS**：`every OAI import resolves inside the fetched subset (3092 modules)`。
   第五轮里「点号名比斜杠路径」的结构性缺陷修好之后，C11 的真实状态是 BLOCKED（预算内取不完）；
   本轮把剩下的 import 取完，闭包闭合。
2. **闭包是完整的，不是取到上限就停**：`_closure.json` 报 `complete=true`、`not_fetched=0`、`failed=0`、
   `status=complete`。前一轮的 `truncated`（撞 `--max-modules` 上限）本轮已消除。
3. **C23 仍是真实 GAP，且不该靠取件消除**：Lean 侧的 `m<=Dn` 锐化至今没有任何陈述。
   闭包取完也不会让它长出来——这是研究缺口，不是取件缺口。

## 二、怎么取完的（承接同一份缓存，不重下已落盘的文件）

```text
$ python fetch-sources.py --out <cache> --ref 4eaee87548250b2682affda7d05d947c05554bae --max-modules 800
seed: 19/19 files
closing imports (--max-modules=800, timeout=240s, tries=4)
...
closure status: truncated -> _closure.json
closure: complete=False imported=800 not_fetched=22 failed=0

$ python fetch-sources.py --out <cache> --ref 4eaee87548250b2682affda7d05d947c05554bae --max-modules 3000
seed: 19/19 files
closing imports (--max-modules=3000, timeout=240s, tries=4)
...
fetched 99/99 files, 2300424 bytes total -> _manifest.json
pin: repo=openai/math requested=4eaee87548250b2682affda7d05d947c05554bae resolved=4eaee87548250b2682affda7d05d947c05554bae source=arg-sha
closure status: complete -> _closure.json
closure: complete=True imported=80 not_fetched=0 failed=0
```

两轮的差别只有上限：第一次 `--max-modules 800` 新增 800 个模块后仍余 22 条（撞上限，`truncated`）；
第二次把上限放到 3000，新增 80 条后 `not_fetched` 归零，`status=complete`。
`close_imports()` 从**已落盘**的模块起算，所以两轮都没有重下已取过的文件。

落盘规模：`.lean` 文件 **3092** 个；manifest 记录 **99** 个文件、**2 300 424** 字节，通道
`jsdelivr=98 / raw=1`；manifest 的 `ref_resolved` 与 `ref_source=arg-sha` 说明取件钉在
`4eaee87548250b2682affda7d05d947c05554bae` 这一个 commit 上。

## 三、C11 复算（check-gap，24 项）

```text
$ python check-gap.py --src <cache> --report <report>.md
[PASS] C1 取件完整性                     99 files, 2300424 bytes, sha256 verified
[PASS] C10 定义漂移                     30/30 shared definitions are semantically identical ...
[PASS] C11 import 闭合                  every OAI import resolves inside the fetched subset (3092 modules)
[PASS] C16 编码界数值复核                40 sampled formulas satisfy formulaBitLength <= n+2+(4+(8n+8)k)m and L+1 <= (8k+7)(n+m+1)^2
[GAP]  C23 Lean 侧锐化                  no m<=Dn statement anywhere in the formalisation -- the sharpening 2^(n/sqrt(log n)) is entirely unformalised
...
checks: 24, FAIL: 0, confirmed gaps: 1
```

`FAIL: 0` 与上一轮相同；变化只有 C11 从 PART 变 PASS，`confirmed gaps` 仍是 1（C23）。

## 四、C23 为什么仍然是 GAP（诚实条款）

- 上游 `lean/docs/378.md` 自陈 `m<=Dn` 锐化**尚未形式化**（C22 PASS 复核的是这句话本身）。
- 形式化侧全文检索不到 `m<=Dn` 的任何陈述：C23 GAP。
- 这与取件无关：把 3092 个模块全部取到本地，并不会让上游多出一个定理。
  本轮的进展是「**取件缺口关闭**」，不是「**研究缺口关闭**」；两者不可混为一谈。
- 若要推进 C23，可行的只有两条：向上游提 PR 形式化该锐化；或在本地写一个不依赖上游的
  独立证明并纳入本仓复核集。两者都不是本轮做的事。

## 五、本轮改了什么

- 代码：**无改动**。本轮只做取件与复算，`repro/family378-subexpsat/` 下的脚本一行未动。
- 记录：本文件（第六轮）。
- 缓存（不入库，`.artifacts` 之外的本地临时目录）：`_manifest.json` 99 文件 / 2 300 424 字节，
  `_closure.json` `complete=true`。

## 六、仍然待办

1. **外发授权**：族 378 复核草稿要外发，仍需用户署名身份与邮箱授权；未授权前不外发。
2. **C23**：见上，需要的是形式化工作，不是取件工作。
3. **上游监控**：第五轮已确认 `openai/math` 与 `mathcommunity/oai-math-revised` 零增量，
   本轮未重复监控（取件钉在同一 commit，无新 commit 可取）。

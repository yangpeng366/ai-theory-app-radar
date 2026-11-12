# AGENTS

- 源码与文档一律 UTF-8 无 BOM
- 优先改 `docs/`、`progress/`、`radar/`；不要把 Obsidian 整库拷进来
- 进展写入 `progress/`；筛查与陈述卡写入 `radar/`
- 飞书「项目方向」回写：先改本仓，再更新 `外部成就` / `下一步`
- 主沙盒未切换前，默认跟进 openai/math family 102
- 材料 / 网络只做接口翻译，不写工艺结论

## 实践与调试

以下每条都是在本仓实跑撞出来的，按「症状 → 原因 → 对策」记。

### 1. sha256 与「重建索引逐字节 diff」被 CRLF 打红

- 症状：同一张 `radar/*.md`，Windows 工作区和 CI 里算出的 `sha256`、`bytes` 不一样，`radar-index` job 把没人动过的卡判成改动（真实踩过：run 43125137704 红）。
- 原因：`core.autocrlf=true` 时 Windows 工作区是 CRLF、Linux 检出是 LF，同一份文本两种字节序列。
- 对策：先做 CRLF/CR → LF 归一，再对归一后的文本取哈希与字节数；比两份 manifest 也先归一再比。

### 2. 取件必须 pin 到 sha

- 症状：隔几天复跑，同一个 `--ref` 拿到的文件变了。
- 原因：分支会移动，`main` 不是 pin。
- 对策：`--ref` 传 40 位 sha；传分支则先解析成 sha 再取文件。解析失败要落 `ref_source` / `ref_resolved` / `ref_error`，不假装已 pin。`tools/check_check_contract.py` 每次重证 `arg-sha` 这条路径。

### 3. 契约脚本全绿 ≠ 判据有效

- 症状：`python tools/check_check_contract.py` 全绿，某一项检查却是无条件 PASS。
- 原因：它证的是编号一一对应、引用不悬空（实测 135 处引用、0 个未知编号），并不证每项判据能失败——C14 曾经只打印比值就 PASS。
- 对策：新增判据必须能判红。先构造反例、确认脚本退出码变 1，再算写完。

### 4. 离线自测靠 conftest 拦截

- 症状（也是保证）：测试若偷偷联网会直接失败，而不是偷偷下载。
- 原因：`repro/family378-subexpsat/conftest.py` 拒绝一切非回环 socket / DNS，`test_offline_guard.py` 反过来证拦截真的生效。
- 对策：新用例喂内存假响应或回环 `http.client` 桩；测试链路上用 `--no-resolve`，不要真去打上游。

### 5. 编码闸门覆盖全仓

- 症状：新加的 `tools/`、`scripts/` 文件以为自己不在检查范围，BOM 混进去才发现。
- 原因：闸门按 git 跟踪清单扫全仓（现 39 个文件），不只扫 `repro/`。
- 对策：改完先跑 `python tools/check_repo_encoding.py`；文件落盘时就写成 UTF-8 无 BOM。
- 补充：若它报 `no files found` 而手跑 `git ls-files` 正常，是 git 的 stdout 在管道里被吞（沙箱问题），不是仓库真没文件。

### 6. 改卡片必须重建索引

- 症状：`python tools/check_radar_index.py` 报红，说 `title` / `sha256` 与卡片不一致。
- 原因：`radar/index.json` 记了每张卡的大小与 sha256，改卡即过期。
- 对策：先 `python scripts/build-radar-index.py`（输出确定，同输入同字节），再跑门禁。

### 7. 索引只放元信息与指针

- 症状：有人想把「这条已复核成功」写进 `index.json`，说下游好读。
- 原因：结论属于卡片正文；索引一旦带判断，就多了一份没人复核的结论副本。
- 对策：索引只写 date / topic / slug / title / tags / labels / families 与 `repro/`、`docs/`、关联卡指针，结论留在卡里。

### 本地自测怎么跑

仓库根目录依次跑，五项各自能独立红：

```bash
python -m pytest repro/family378-subexpsat -q   # 离线自测，43 例，0 网络
python tools/check_repo_encoding.py             # UTF-8 无 BOM，全仓
ruff check repro tools                          # 静态检查
python tools/check_check_contract.py            # C1..C24、引用、取件 pin
python tools/check_radar_index.py               # radar/index.json 与卡片一致
```
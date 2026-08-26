# 分阶段 Copilot 指令

配套代码在 `handoff/`,规格书见 `handoff/HANDOFF.md`。

**规则:一个阶段一次提交,每个阶段结束必须跑通验收命令才进入下一个。**
阶段 2 需要先拿到内网 API 文档,阶段 1 现在就能开始。

---

## 阶段 0 — 你自己在终端跑(不给 Copilot)

```bash
unzip doceval-handoff.zip && cd handoff
git init && git add -A && git commit -m "baseline: DocIR pipeline + gate v2, 101 pages verified"
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install pymupdf pyyaml
# 只有要处理 docx/xlsx/pptx/html 才装这一行(约 280 MB,无 torch)
pip install "docling-slim[format-docx]" openpyxl python-pptx beautifulsoup4 marko lxml pypdfium2
# 确认基线能跑通,必须输出「结论:通过」
python run_eval.py testdata/arxiv
```

跑不通就不要往下走,先解决环境问题。

---

## 阶段 1 — P0:零 API 成本的修复

复制下面整段给 Copilot:

```text
这是一个已经用 101 页真实 arXiv 论文验证过的文档解析代码库。请先完整阅读
HANDOFF.md,重点是第 4 节(任务清单)、第 6 节(明确不要做的事)、第 7 节(已知坑)。

【硬性约束,违反任何一条都算失败】
- 不要重新设计架构,不要重写现有文件,只做增量修改。
- 不要新增任何 .py 文件,除了任务里明确要求的。
- 不要新增规则算子(if/正则分支)。解析不准的处理方式是交给闸门升级,不是加 if。
- 不要给 DocIR 的 Block 加字段,除了任务 1 明确要求的 figure_text。
- 不要写切分、embedding、索引、检索相关的任何代码。
- baseline_arxiv101.json 是只读的回归基线,不许修改它。

【本阶段只做这三件事】

任务 1:实现 parse.keep_figure_text
  现状:docir_pipeline.py 的 _figure_rects() 检出图区后,parse_page() 把落在图区内的
  文本行整块丢弃。后果是 101 页里有 9 页字符覆盖率掉到 0.97 以下,被闸门误判为需要
  调 OCR API —— 但那些文字本来就在 PDF 文本层里,根本不需要 OCR。
  改法:图区内的文本不丢弃,收集起来写入该 figure block 的新字段 figure_text(str)。
  不要为图内文字新增 block。行为由配置项 parse.keep_figure_text 控制,默认 true。
  验收:OCR_PAGE 从 9 页降到 <= 2 页,其他判定项都不能变差。

任务 2:阈值外置到 config.yaml
  把 gate.py 里的 TH 字典、docir_pipeline.py 里的魔法数字(merge_same_row 的 max_gap=40
  和 y_tol、_figure_rects 的 min_w/min_h、_detect_columns 的 0.18 比例)全部改成从
  config.yaml 读取,键名沿用 config.example.yaml 里已有的结构,缺失时回退到当前硬编码值。
  不要改变任何默认值 —— 这一步是纯重构,跑分结果必须和改之前完全一致。

任务 3:给 run_eval.py 补 Office/HTML 支持
  现在 run_eval.py 只扫 *.pdf。扩展成也扫 testdata/office/ 下的 docx/xlsx/pptx/html,
  走 route_a_office.py 的 parse_office(),输出 block 数和表格的 rowspan 是否保留。
  Office 文件没有页码和坐标,不要为它们跑闸门(闸门的指标依赖 PDF 文本层)。

【验收命令,必须全部通过】
  python run_eval.py testdata/arxiv       # 必须输出「结论:通过」,且 OCR_PAGE <= 2
  python route_a_office.py testdata/office/sop_hard.docx testdata/office/sample.xlsx

如果 PASS 数下降,或 TABLE_API_REGION / OCR_PAGE / VLM_PAGE 任何一项上升,
回退你的改动重做,不要试图改基线文件或放宽阈值来让测试通过。

做完请报告:改了哪些文件的哪些函数、跑分前后对比表、以及你没做但认为该做的事(只列出,不要动手)。
```

---

## 阶段 2 — P1:接三个公司 API

等拿到 API 文档后再用。

**开始前必须准备好:** 三个 API 的真实请求/响应示例(curl + JSON),
填好 config.yaml 里的 endpoint,导出 `TABLE_API_KEY / OCR_API_KEY / VLM_API_KEY`。

**没有真实响应示例就不要开这个阶段**,Copilot 只能编一个假格式出来。

```text
继续上一阶段的代码库。本阶段实现 adapters.py 里三个 NotImplementedError。
先重读 HANDOFF.md 第 4 节 P1 和第 7 节。

【硬性约束】
- 不要修改 PageCtx 和 Block 的结构定义,契约已定。
- 不要修改 gate.py 的升级路由逻辑(归因合并 / 孤证降级 / 级联三条原则是实测调出来的)。
- adapter 只做「输入页或区域 -> 输出 list[Block]」,不许在 adapter 里做路由判断。
- 所有 endpoint、key、超时、并发、重试都从 config.yaml 读,不许硬编码。
- 新增 adapter 数量为 0(就实现现有这三个),不要加第四个。

【三个 API 的真实请求响应格式】
(把 curl 示例和 JSON 响应样例贴在这里)

【实现要求】

TableApiAdapter(预算 10%,区域级调用)
- 输入是 ctx.region 指定区域的裁剪图,不是整页。
- 输出一个 type='table' 的 Block,html 必须带 rowspan/colspan。合并单元格丢了等于没解析。
- ctx.hint 里有 prev_page_table_header 时,把它作为表头拼到返回表格的最前面。
- 表格整体 bbox 必填,且必须换算回 PDF 点坐标(用 BaseAdapter.to_pdf_bbox)。

OcrApiAdapter(预算 9%,整页调用)
- 每个 Block 必须带换算回 PDF 点坐标的 bbox,没有 bbox 就是断了溯源,不许提交。
- OCR 结果只用来补文本层缺失的区域,不许覆盖已经解析出来的可信文本层内容。
- type 只允许 para / title / table / figure。

VlmApiAdapter(预算 <= 3%,整页调用,最贵)
- temperature 必须是 0,model 版本必须写进 Block.extractor,否则解析不可复现。
- 必须实现坐标回锚:把返回文本逐段回锚到 PDF 文本层或 OCR 行,锚不上的判定为幻觉,
  丢弃该段并把整页标记 needs_human。回锚率写进 Block.confidence,< 0.95 视为超标。
  anchor_back() 已有一个字符级实现,可以改进但不能删掉这个检查。
- 用 adapters.py 里的 VLM_PROMPT,不要自己重写 prompt。

【级联执行】
在 run_eval.py 里加一个 --escalate 开关:闸门判 ESCALATE 时按 escalate_to 调对应 adapter,
拿到新 blocks 后重跑闸门(第二跳)。最多两跳(config.budget.max_escalation_hops),
第二跳仍不过则标 needs_human。统计每一跳的调用次数和耗时。

【验收命令】
  python run_eval.py testdata/arxiv --escalate

必须满足:
  - VLM 实际调用页数 / 总页数 <= 0.03
  - 原来 10 个 TABLE_API_REGION 页里,表格结构合法性全部变为 1.0
  - 原来 9 个(修复后 <=2 个)OCR_PAGE 页,char_coverage 升到 >= 0.97
  - 所有新产生的 Block 都有非零 bbox 和 extractor 版本号
  - 升级跳数上限生效,日志里能看到每跳的调用统计

做完请报告:三个 API 的实际调用次数、耗时分位数(p50/p95)、以及被判为幻觉丢弃的段落数量。
```

---

## 阶段 3 — P2:兼容层与收口

阶段 2 通过后再用。

```text
继续上一阶段的代码库。本阶段做 HANDOFF.md 第 4 节 P2 的两件事。

【硬性约束】
- 现有下游代码一行都不许改。
- 不要做后台管理系统、不要加 web 框架、不要加数据库 ORM。

任务 1:写 shim.py
  提供 load(path: str) -> str,返回 markdown 字符串,签名与现有 loader 完全一致。
  内部实现是 render_markdown(parse(path))。
  parse() 要按扩展名分派:PDF 走 docir_pipeline 的 Route A,
  docx/xlsx/pptx/html 走 route_a_office.parse_office,图片走 OcrApiAdapter。
  同时提供 load_docir(path) -> DocIR 给愿意用结构化输出的下游。
  加一个 config.output.render_markdown_shim 开关和一个按文件类型灰度的白名单
  (config.shim.enabled_extensions),这样可以一个类型一个类型地切。

任务 2:needs_human 队列
  一张 sqlite 表 + 三个函数就够:enqueue(doc_id, page, reason, evidence)、
  list_pending(limit)、mark_resolved(id, note)。
  不要做 web UI,不要做通知,不要做 worker。

【验收命令】
  python -c "import shim; print(shim.load('testdata/arxiv/1512.03385v1.pdf')[:500])"
  python -c "import shim; print(shim.load('testdata/office/sop_hard.docx')[:500])"
  python run_eval.py testdata/arxiv --escalate     # 回归不能变差

做完请报告:shim 输出与旧 loader 输出的 diff 摘要(挑 3 个文件对比),以及 needs_human 队列里的条目数。
```

---

## 每个阶段之后你自己做的检查

1. `git diff --stat` —— 改动文件数超过 5 个就要问 Copilot 为什么。
2. 三个膨胀警报:后处理算子 > 3 个 / DocIR 字段 > 12 个 / adapter > 4 个,任一触发就退回。
3. `python run_eval.py testdata/arxiv` 输出「结论:通过」才 commit。

## 不要交给 Copilot 的四件事

| 事 | 为什么 |
| --- | --- |
| 填 endpoint / API KEY | 凭证不进代码库,也不进 prompt |
| 拿三个 API 的真实请求响应示例 | 没有它 Copilot 只能编格式 |
| 准备档二数据(20–30 份,含扫描件和图片) | 只有你能拿到真实文档 |
| 标档三金标集(30–50 页) | 人工标注,是所有模型对比的唯一依据 |

# Copilot Prompt — 文档解析方案 A/B 证据级对比报告

> **用法**:在 VS Code 打开 `parser-ab-eval/` 工作区,把本文件**整段**贴进 Copilot Chat
> (建议 Agent / Edits 模式)。按 STAGE 顺序推进,**每个 STAGE 跑通并经我确认后再进下一个**。

---

## ROLE

你是文档智能评测工具的实现者。目标不是"算出指标",而是**让每一个指标数字都能下钻到具体证据实例**。
如果一个指标无法下钻到实例,这个指标就不要输出。

## 背景

对比两套文档解析方案,输出都是 markdown:

- **A = Azure Document Intelligence** `prebuilt-layout` — 有版面分析,返回 bbox
- **B = Local Loader** — markitdown / python-docx / python-pptx 路线,无 bbox

评测集 11 个文件(docx / pdf / pptx 混合),其中 3 个有人工复核 GT。

现有报告是「每文件一张指标表 + 附一张整页截图」。指标粒度是"文件 × 指标",证据粒度是"整页",
两者对不上,读者无法从 `数字 Recall 17.5%` 定位到"具体漏了哪些、在页面哪里、A/B 各输出成了什么"。

**核心改法:引入 anchor(证据锚点)层。所有指标都定义为 anchor 集合上的聚合函数。**

---

## 🔒 冻结边界 —— 先读这一节

工作区里有两个**冻结文件**,你不要修改:

| 文件 | 状态 | 说明 |
|---|---|---|
| `templates/report_shell.html` | 🔒 冻结 | 全部 CSS / JS / 骨架。不要改任何 CSS 规则、class 名、颜色变量、JS 逻辑。 |
| `tools/render_report.py` | 🔒 冻结 | 渲染层。视图模型 dict → HTML。不要改已有函数的 HTML 结构或 class。 |
| `tools/_demo_data.py` | 📖 只读参考 | 假数据。它就是**视图模型的 schema 活文档**,照着这个形状产数据。 |

先跑一次确认环境正常:

```bash
python tools/render_report.py --demo -o report.PREVIEW.html
```

打开 `report.PREVIEW.html`,你看到的就是最终报告的样子。**你的任务是把假数据换成真数据,不是重做界面。**

如果你认为某处样式必须改,先在 chat 里说明原因,等我同意,不要直接动手。
需要新的卡片形态时,在 `render_report.py` 里**新增** `build_*` 函数,不要改已有的。

---

## 输入目录

```
eval/
  sources/   # 原始文件:GOP_R11_v9.3.docx / .pdf / Model_Approval.pptx ...
  out_a/     # A 的 markdown,与 sources 同名 .md
  out_b/     # B 的 markdown,与 sources 同名 .md
  gt/        # 人工 GT,同名 .json,schema 见 eval/gt/SCHEMA.md
```

## 你要写的文件

```
tools/build_anchors.py    # STAGE 1  → eval/anchors.jsonl
tools/match.py            # STAGE 2  → eval/results.jsonl
tools/render_crops.py     # STAGE 3  → eval/crops/*.png
tools/build_report.py     # STAGE 4  → 调 render_report.render(),出 report.html
```

## 硬约束

- **纯离线**。公司网络受限,不要用任何 CDN、在线字体、外部 JS 库。
- Python 依赖只允许:`pymupdf`(fitz)、`python-docx`、`python-pptx`、`rapidfuzz`、`lxml`、`Pillow`。
  装不上就降级,不要引入新的。
- 最终 HTML 单文件自包含,图片 base64 内嵌(`render_report.py` 已实现)。
- 中间产物一律 JSONL,方便我手工 diff 和抽查。
- 路径全走 `pathlib`,不要硬编码分隔符。

---

## STAGE 1 — 构建 anchor 表

`tools/build_anchors.py`:从**源文件原生结构**抽 anchor,**不从 A 或 B 的输出抽**。

### anchor schema(每行一条 → `eval/anchors.jsonl`)

```json
{
  "anchor_id": "GOP_R11_v9.3.pdf#a0031",
  "file": "GOP_R11_v9.3.pdf",
  "page": 4,
  "bbox": [212, 486, 1018, 512],
  "bbox_status": "ok | unresolved",
  "type": "number | table | block | heading",
  "gt_text": "2019",
  "gt_context": "1.2 | July 2019 | Annual review and feedback",
  "gt_order": 12,
  "gt_table": {"rows": 6, "cols": 3, "cells": [["Edition", "Publication date", "Details"]]},
  "source": "docx_xml | pptx_xml | manual_gt"
}
```

### 各格式抽取方式

| 格式 | 库 | 阅读顺序 GT | 表格 GT | bbox |
|---|---|---|---|---|
| docx | python-docx | `document.element.body` 子元素文档流顺序 | `table._tbl` 的 `tr/tc`,含 `gridSpan`/`vMerge` | 无 → 转 PDF 反查 |
| pptx | python-pptx | shape 按 `(top, left)` 空间排序,同带内按 left | `GraphicFrame.table` | shape 的 `left/top/width/height`,EMU ÷ 12700 → pt |
| pdf | — | 读 `gt/*.json` | 同左 | GT 直接给 |

**⚠ docx 必须混合遍历 `w:p` 和 `w:tbl`。** 用 `document.paragraphs` 再 `document.tables` 是最常见的坑,
阅读顺序 GT 会直接错。参考:

```python
from docx.table import Table
from docx.text.paragraph import Paragraph
for child in document.element.body.iterchildren():
    if child.tag.endswith('}p'):
        yield Paragraph(child, document)
    elif child.tag.endswith('}tbl'):
        yield Table(child, document)
```

**⚠ 页眉页脚必须排除。** docx 用 `section.header/footer`,pptx 用 placeholder type,pdf 用 GT 标注。
A 走 OCR 会把页码当正文,这个差异要能被测出来,而不是被 GT 噪声掩盖。

### 数字抽取

```python
NUM = re.compile(r'(?<![A-Za-z0-9._-])'
                 r'(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)'
                 r'\s*(?:%|bps|days?|hrs?)?'
                 r'(?![A-Za-z0-9._-])')
```

排除:行首纯序号(`1.` `2.`)、版本号内部段(`v9.3` 整体算一个 token)、页码。
每个数字 anchor 带 ±40 字符上下文。

### bbox 反查(docx / pptx)

1. `soffice --headless --convert-to pdf` 转 PDF。公司机器若无 LibreOffice,降级用 `win32com`;
   两者都不可用时,**跳过 crop,证据卡走纯文本模式**(`render_report.py` 已支持 `crop.kind="none"`)。
2. `fitz.Page.search_for(gt_context)` 拿 `Rect`。
3. 命中 0 次或 > 3 次 → `bbox_status: "unresolved"`,`bbox: null`。
   **不要猜 bbox。** unresolved 的 anchor 照样进证据卡,只是不带截图。

**STAGE 1 验收**:打印每文件的 anchor 数按 type 分布 + `bbox_status` 分布,
随机抽 5 条打印 `gt_text / gt_context / bbox_status`。等我确认。

---

## STAGE 2 — 匹配 A / B 输出

`tools/match.py`:读 `anchors.jsonl` + `out_a/*.md` + `out_b/*.md` → `eval/results.jsonl`

```json
{
  "anchor_id": "...",
  "a": {"status": "hit|miss|wrong", "text": "2019", "md_line": 142, "note": ""},
  "b": {"status": "miss", "text": "", "md_line": 98, "note": "年份被合入页眉行"},
  "verdict": "A | B | tie | both_fail"
}
```

### 各 type 的匹配规则

**type=number**
- 用 `gt_context` 做 `rapidfuzz.fuzz.partial_ratio` 定位窗口(阈值 ≥ 75)
- 窗口内查 `gt_text` 是否作为完整 token 出现
- **三分类,不要只算 recall**:`hit` / `miss`(完全没有) / `wrong`(位置对但值不同,如 2019→2013)
- `wrong` 比 `miss` 危害大得多,报告里单独列

**type=table**
- 按表头文本定位表块 → 解析 GFM 表格为二维数组
- `TEDS-struct`(行列数 + 合并模式)与 `TEDS-content`(单元格文本归一化后比对)分开算
- 输出 **cell 级判定矩阵** `cell_status[i][j] ∈ {match, wrong, missing, extra}` —— 热力图的数据源
- 候选侧无表格块(退化成纯文本)→ 整表 missing,TEDS = 0

**type=block(阅读顺序)**
- 每页取所有 block anchor,在候选 markdown 中模糊定位行号 → 候选顺序序列
- 与 `gt_order` 比 **Kendall tau-b**,同时输出逆序对列表(图上要标哪两个块交叉)

**markdown 语法**(不挂 anchor,按文件计)
至少检这四条,每条记 `{file, side, line, rule, severity, snippet}`:
- `table_col_mismatch` — 表头/分隔行/数据行列数不等 · **high**(整表渲染回退)
- `unclosed_fence` — ``` 未闭合 · high
- `broken_heading` — `#` 后无空格 · medium
- `orphan_pipe` — 行首/尾多余 `|` · low

### verdict

```
a.hit && !b.hit  -> "A"
!a.hit && b.hit  -> "B"
both hit         -> "tie"
neither          -> "both_fail"
```

**STAGE 2 验收**:打印按 type 的 verdict 分布矩阵,以及 `both_fail` 的**全部**条目
(这些通常是 GT 本身有问题,我要人工确认)。

---

## STAGE 3 — 生成裁剪图

`tools/render_crops.py`:

- `fitz` 打开 PDF → `page.get_pixmap(clip=Rect, dpi=150)`
- **bbox 上下各外扩 40px、左右扩到整行宽**。只裁一个词的图没法看。
- 用 Pillow 在裁剪图上画红色虚线框标出 anchor 本体位置
- 存 `eval/crops/{anchor_id}.png`,长边限 900px,PNG 优化
- `bbox_status == "unresolved"` 的跳过

---

## STAGE 4 — 生成报告

`tools/build_report.py`:把 `results.jsonl` 转成视图模型 dict,调 `render_report.render(REPORT)`。

**照抄 `tools/_demo_data.py` 的数据形状。** 那份假数据里每种卡片形态都有一个样例:
- `c01` 三栏 + svg crop(真实运行时换 `{"kind":"img","path":...}`)
- `c04` 三栏 + `crop.kind="none"`(语法错误,不挂 bbox)
- `c05` 三栏 + unresolved crop
- `c03` 双栏 + 阅读顺序折线 SVG
- `c06` 双栏 + 表格 cell 热力图 SVG

### 卡片渲染规则(重要,别漏)

1. **只渲染 `verdict != "tie"` 的卡。** number anchor 有 400+,全铺开没法看。
   tie 的数量汇总进该组的 `tie_count`,由模板渲染成一行统计。
2. **按文件分组**。每组一个 `groups[]` 元素。组数 > 3 时,把 `open` 逻辑交给模板,
   你只管填 `file` / `tie_count` / `cards`。
3. `both_fail` 的卡 `fail="both"`,verdict 文案写 `共同失败 · 待复核 GT`,
   并在报告末尾单列一节(可用一个额外的 group,file 写 `⚠ 待人工复核 GT`)。
4. `a` / `b` 的 `snippet` 字段是**已经带 `<mark>` 的 HTML**。
   用 `render_report.word_diff(gt_context, candidate_text, focus=gt_text)` 生成,不要自己拼。
5. 上下文只留目标 token 前后各一行,不要贴整段。

### L0 失效模式的自动聚类

对 `verdict != "tie"` 的 result 按 `(失败方, type, 源文件扩展名)` 分组;
组内实例数 ≥ 3 且覆盖文件数 ≥ 2 的,升级为一条失效模式。
标题模板:`{失败方} 在 {扩展名} 上 {type 的中文现象名}`。
`refs` 取该组内前 2 个 card id。允许我在 config 里手工覆盖文案。

### SVG 生成

阅读顺序折线和表格热力图的 SVG 生成函数,参考 `_demo_data.py` 里的
`_order_svg()` 和 `_heat()`,把它们从假数据里提出来放进 `build_report.py`,接真数据。

---

## 验收标准

1. 从 L1 的任意一个数字,**2 次点击内**能到达支撑它的具体证据卡。
2. 随便挑一张证据卡,不看别的内容也能独立判断"A 和 B 谁对、错在哪"。
3. `report.html` **断网双击**能正常打开,所有图正常显示。
4. 报告里**不出现任何无法下钻的聚合数字**。
5. `both_fail` 条目单独成节,标注"待人工复核 GT"。
6. `templates/report_shell.html` 与 `tools/render_report.py` 的 git diff 为空。

## 不要做的事

- ❌ 不要输出加权总分或"综合得分"。选型靠看失效模式,不靠算总分。
- ❌ 不要用 A 的输出当 B 的参照,反之亦然。参照只能来自 STAGE 1 的 anchor。
- ❌ 不要在 bbox 反查失败时用近似位置糊弄,老实标 unresolved。
- ❌ 不要为了报告好看隐藏 A 失败的案例。A 失败的卡和 B 失败的一样要列全。
- ❌ 不要改冻结文件。

---

## 执行顺序

**先只实现 STAGE 1**,跑通并打印验收信息,等我确认后再继续。
每个 STAGE 结束时告诉我:产出了什么文件、多少条记录、有哪些异常需要我看。

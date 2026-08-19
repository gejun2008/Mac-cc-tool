# doceval-fin：金融文档转换服务 — 实现规格书 v2

> 本文档是交给 Copilot 的实现规格。请**完整实现**，不要简化、不要用 mock 代替真实逻辑。
> 若某处规格与你的默认做法冲突，**以本文档为准**。
> 第 12 节「禁止事项」是硬约束，任何情况下不得违反。
>
> v2 变更：新增格式路由层，覆盖 pdf / 图片 / docx / pptx / xlsx；LLM 从可选旁路改为按任务分级的默认能力；新增 LLM 自洽性置信度机制。

---

## 0. 给 Copilot 的启动指令

```
请根据本规格书实现 doceval-fin 服务。要求：
- Python 3.11+，使用 uv 管理依赖
- 代码注释用英文，README/文档用中文
- 每个模块配单元测试，测试必须用真实 fixture 而非 mock 数据
- 严格遵守第 12 节禁止事项
- 按第 13 节顺序实施，M1 跑通后再往下
```

---

## 1. 背景、目标与定位

为 RAG team 提供统一的文档转换服务。输入任意常见格式文档，输出两层结果：

- **第一层：内容** — markdown + 锚点索引（每段内容可回溯到原文位置）
- **第二层：校验** — 机器可读的质量判定，供下游决定是否入库、是否可举证

### 1.1 业务场景

受监管金融机构的文档处理场景。核心关注：**数字、金额、签名**。数字错一位是实质性错误。

设计原则：

> **可溯源性与数字正确性，优先于转换结果的"好看程度"。**

### 1.2 两个必须区分的概念

实现和讨论中最易混淆的一点，先定义：

| 概念 | 比较对象 | 运行时可测？ | 期望值 |
|---|---|---|---|
| **渲染保真度** `render_fidelity` | 输出 markdown ↔ 底本字符串 | 可以，纯字符串比对 | **恒为 1.0** |
| **抽取准确率** | 底本 ↔ 物理文档原件 | **不可以**，无 ground truth | 未知 |

`FAIL` 判定只针对**渲染保真度**——输出由 IR 渲染、IR 由底本解析，数字不一致在数学上不应发生。**这是渲染器/LLM 回退失效的绊线，不是文档质量闸门。** 若频繁触发，应修代码而非放宽阈值。

抽取准确率无法运行时测量，只能通过间接信号发现，均触发 `REVIEW` 而非 `FAIL`：
- cross-foot 算术不平
- 引擎置信度低（DI 有；LLM 无，需人为构造，见第 8 节）
- 多引擎交叉不一致

真实抽取准确率只能离线测：人工标注 GT 语料跑 `scripts/benchmark.py`（第 11.3 节）。

### 1.3 方案定位

**确定性抽取为底本，LLM 为结构与语义增强。**

```
底本层：确定性引擎（DI layout / OOXML / openpyxl）→ 逐字文本 + 锚点 + 置信度
增强层：LLM（默认开启，按任务分级）→ 结构规范化、图语义
校验层：verbatim 断言 + cross-foot + 置信度 + 自洽性  ← 本方案的核心价值
```

LLM 全部关闭时服务必须仍可用，仅结构质量与图语义覆盖度下降。这保证第三方模型未过审或数据分域受限时方案仍可落地。

---

## 2. 格式覆盖与路由

### 2.1 路由矩阵

| 输入格式 | 底本来源 | 图的来源 | 表的来源 | LLM 任务 |
|---|---|---|---|---|
| PDF（数字原生） | DI `prebuilt-layout` | DI `figures` | DI `tables` | T1 T2 T3 |
| PDF（扫描件） | DI `prebuilt-layout` | 整页栅格 | DI `tables` | T1 T2 T3 |
| 图片 (jpg/png/tiff) | DI `prebuilt-layout` | 整图 | DI `tables` | T1 T3 |
| **docx** | **OOXML 直读** | `word/media/` + 形状边表 | `w:tbl` | T3 |
| **pptx** | **OOXML 直读** | `ppt/media/` + 形状边表 | `a:tbl` | T3 T4 |
| **xlsx** | **openpyxl** | — | 单元格即结构 | 几乎不需要 |

### 2.2 为什么 Office 格式不走 DI

DI 虽然接受 docx/pptx 作为输入，但：

1. **对 Office 原生格式不返回 figures**（设计如此，非缺陷）——图片信息完全丢失
2. **docx/pptx 没有"页"的概念**，分页是渲染期产物，取决于字体与渲染器；拿不到稳定的页码锚点
3. XML 里本来就是明文：文字、表结构、图片文件、形状连接关系、alt text，全部可确定性读取

**原则：OOXML 是天花板，OCR 是地板。** 对 Office 格式，DI 是严格更差的选择。

### 2.3 格式分类器

`engines/router.py`

```python
def classify(path: str, content: bytes) -> DocumentProfile:
    """
    1. magic bytes + extension -> container format
       - PK\x03\x04 + [Content_Types].xml -> OOXML, check part names for docx/pptx/xlsx
       - %PDF -> pdf
       - image magic -> image
    2. For PDF: extract text layer per page (pdfminer or PyMuPDF).
       chars_per_page < 50  -> 'scanned'
       otherwise            -> 'digital'
       Mixed documents: classify PER PAGE, not per document.
    3. Return route + per-page routing table.
    """
```

**混合 PDF 必须按页路由**——扫描件插页在金融文档里非常常见（签署页、补充材料）。

---

## 3. 硬约束

| # | 约束 | 理由 |
|---|---|---|
| C1 | 逐字底本必须来自确定性引擎，不得来自 LLM | 可举证 |
| C2 | 每个 chunk 必须携带 anchor | 可举证 |
| C3 | 数字字符必须逐字精确匹配底本，不允许模糊匹配 | 数字正确性 |
| C4 | 签名只输出 signed/unsigned + 裁片，绝不输出签名人姓名 | 防幻觉 |
| C5 | LLM 生成内容必须标 `generated=true` + 模型快照版本 | 可审计 |
| C6 | DI 调用 `stringIndexType` 必须为 `unicodeCodePoint` | Python 侧偏移一致 |
| C7 | 相同输入 + 相同引擎版本，底本层输出必须字节一致 | 可复现 |
| C8 | LLM 输出必须经结构校验，失败则回退底本 | 防污染 |

---

## 4. 架构与数据流

```
输入文档
   │
   ▼
[router] 格式分类 + 按页路由
   │
   ├─ pdf/图片 ─→ [DI prebuilt-layout] ──┐
   │              words/tables/figures    │
   │              + confidence            │
   │                                      │
   ├─ docx ────→ [ooxml_docx] ───────────┤
   │              段落/表/media/形状边表   │
   │                                      │
   ├─ pptx ────→ [ooxml_pptx] ───────────┤
   │              slide/形状/备注/边表     │
   │                                      │
   └─ xlsx ────→ [xlsx_reader] ──────────┤
                  单元格/公式/合并          │
                                          ▼
                                  ┌─────────────┐
                                  │  IR: Block  │  逐字底本 + anchor
                                  └─────────────┘
                                          │
                        ┌─────────────────┼─────────────────┐
                        ▼                 ▼                 ▼
                  [LLM T1/T2]       [LLM T3/T4]      [签名检测]
                  表结构规范化       图语义/叙事      DI 自训练模型
                  generated=false   generated=true    signed/unsigned
                        │                 │                 │
                        └────────┬────────┴─────────────────┘
                                 ▼
                         [校验层 validation]
                         · verbatim 断言
                         · cross-foot 算术校验
                         · 置信度（DI 原生 / LLM 自洽性）
                                 │
                                 ▼
                    输出：content + validation
```

---

## 5. 目录结构

```
doceval-fin/
├── pyproject.toml
├── README.md
├── src/doceval_fin/
│   ├── models.py
│   ├── engines/
│   │   ├── router.py           # 格式分类与路由
│   │   ├── di_client.py        # DI REST 客户端
│   │   ├── di_parser.py        # AnalyzeResult -> IR
│   │   ├── ooxml_common.py     # 共用：zip 解包/rels/形状边表
│   │   ├── ooxml_docx.py
│   │   ├── ooxml_pptx.py
│   │   └── xlsx_reader.py
│   ├── llm/
│   │   ├── client.py
│   │   ├── tasks.py            # T1-T4 任务定义与 prompt
│   │   ├── validator.py        # 输出结构校验与回退
│   │   └── consistency.py      # 自洽性置信度
│   ├── validation/
│   │   ├── numbers.py
│   │   ├── aligner.py
│   │   ├── crossfoot.py
│   │   └── verdict.py
│   ├── signature.py
│   ├── renderer.py             # IR -> markdown
│   ├── chunker.py
│   └── api.py
├── tests/
│   ├── fixtures/
│   └── test_*.py
└── scripts/
    └── benchmark.py
```

---

## 6. 数据模型

全部 `@dataclass`，金额一律 `Decimal`（**不得用 float**）。

```python
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional

# ---------- Anchor ----------

@dataclass
class SpatialAnchor:
    """PDF / images. Coordinates from DI."""
    kind: Literal["spatial"] = "spatial"
    page: int = 0
    polygon: list[float] = field(default_factory=list)   # 8 floats, inch
    offset: int = 0                                      # unicodeCodePoint
    length: int = 0

@dataclass
class StructuralAnchor:
    """docx / pptx. The XML path IS the anchor - no coordinates needed."""
    kind: Literal["structural"] = "structural"
    part: str = ""          # "/word/document.xml" | "/ppt/slides/slide3.xml"
    path: str = ""          # "body/p[142]/r[3]"
    ordinal: int = 0        # global block sequence, for range queries
    slide_index: Optional[int] = None    # pptx only, 1-based
    media: Optional[str] = None

@dataclass
class CellAnchor:
    """xlsx. Sheet + cell reference."""
    kind: Literal["cell"] = "cell"
    sheet: str = ""
    ref: str = ""           # "B12" or "B12:D18" for merged
    ordinal: int = 0

Anchor = SpatialAnchor | StructuralAnchor | CellAnchor

# ---------- Table ----------

@dataclass
class Cell:
    row_index: int
    col_index: int
    row_span: int = 1
    col_span: int = 1
    kind: str = "content"               # content | columnHeader | rowHeader
    raw_text: str = ""                  # verbatim from source
    numeric: Optional[Decimal] = None
    is_negative_paren: bool = False
    confidence: Optional[float] = None
    formula: Optional[str] = None       # xlsx only, e.g. "=SUM(B2:B10)"
    anchor: Optional[Anchor] = None

@dataclass
class Table:
    block_id: str
    row_count: int
    col_count: int
    cells: list[Cell]
    unit_hint: Optional[str] = None     # "thousands" | "millions" | None
    continued_from: Optional[str] = None  # block_id of previous part (cross-page)
    anchor: Optional[Anchor] = None

# ---------- Graph (shape-drawn diagrams) ----------

@dataclass
class ShapeNode:
    node_id: str
    text: str
    shape_type: str          # "rect" | "diamond" | "ellipse" | ...
    x_emu: int = 0
    y_emu: int = 0

@dataclass
class ShapeGraph:
    """Deterministically extracted from OOXML connector elements.
    This is ground truth, NOT model-generated."""
    nodes: list[ShapeNode]
    edges: list[tuple[str, str]]        # (from_node_id, to_node_id)

# ---------- Block ----------

@dataclass
class Block:
    block_id: str            # stable: "p_0142", "tb_0007", "sl_003", "fig_005"
    kind: Literal["paragraph", "heading", "table", "figure", "shape_graph",
                  "signature", "selection_mark", "slide", "speaker_notes",
                  "sheet"]
    text: str = ""           # verbatim from source engine
    anchor: Optional[Anchor] = None
    table: Optional[Table] = None
    graph: Optional[ShapeGraph] = None
    alt_text: Optional[str] = None      # author-written; evidence-grade
    media_uri: Optional[str] = None
    confidence: Optional[float] = None
    generated: bool = False
    generator: Optional[dict] = None    # {"model":..., "version":..., "task":"T3"}
    llm_consistency: Optional[float] = None   # see section 8.3

# ---------- Signature ----------

@dataclass
class SignatureRecord:
    block_id: str
    status: Literal["signed", "unsigned"]
    anchor: Anchor
    crop_uri: Optional[str] = None
    signatory_name: None = None         # ALWAYS None. Do not populate.
    name_from_adjacent_field: Optional[dict] = None
    # {"value": "...", "anchor": {...}} -- printed text only, separate anchor

# ---------- Validation ----------

@dataclass
class CrossFootResult:
    table_block_id: str
    axis: Literal["row", "column", "formula"]
    index: int
    expected: Optional[Decimal]
    actual: Optional[Decimal]
    status: Literal["balanced", "imbalanced", "not_applicable"]
    tolerance: Decimal = Decimal("0")
    source: Literal["inferred", "formula"] = "inferred"

@dataclass
class ValidationReport:
    verdict: Literal["PASS", "REVIEW", "FAIL"]
    # Both measure output-vs-source fidelity (see 1.2).
    # They do NOT measure extraction accuracy against the physical document.
    render_fidelity: float
    digit_render_fidelity: float        # expected 1.0
    crossfoot: list[CrossFootResult] = field(default_factory=list)
    low_confidence_blocks: list[str] = field(default_factory=list)
    llm_unstable_blocks: list[str] = field(default_factory=list)
    signatures: list[SignatureRecord] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)   # see 10
    issues: list[dict] = field(default_factory=list)
```

---

## 7. 引擎适配器规格

### 7.1 `engines/di_client.py`（PDF / 图片）

```
POST {endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze
  ?api-version=2024-11-30
  &stringIndexType=unicodeCodePoint     ← 必须显式设置
  &outputContentFormat=text             ← 用 text，不用 markdown
  &output=figures                       ← 需要图裁片时
```

**为何不用 `outputContentFormat=markdown`：**
1. markdown 装饰字符不属于任何 element 的 span，存在"无主字符"，破坏锚点覆盖
2. v4.0 GA 起表格在 markdown 中渲染为 HTML table，切分器需额外处理
3. 无显式页边界；原文无页脚时无法从 markdown 反推页码

markdown 由本服务从 IR 自行渲染（第 9 节）。DI 只提供底本 + 结构 + 坐标 + 置信度。

**实现要求：**
- 异步轮询，指数退避，超时可配
- 完整保存原始 `AnalyzeResult` JSON，路径写入 `engine.raw_result_uri`（审计需要）
- 认证支持 API Key 与 Managed Identity，配置切换
- 日志中**不得**输出文档内容
- 设置 `output=figures` 时，通过 `/analyzeResults/{resultId}/figures/{figureId}` 取裁片

> Python SDK 方法签名在版本间有变化，以安装版本实际签名为准；上述 REST 参数名稳定。

### 7.2 `engines/di_parser.py`

`AnalyzeResult` → `list[Block]`

| DI 对象 | Block.kind |
|---|---|
| `paragraphs[]` role=`title`/`sectionHeading` | `heading` |
| `paragraphs[]` 其他 | `paragraph` |
| `tables[]` | `table` |
| `figures[]` | `figure` |
| `selectionMarks[]` | `selection_mark` |

**关键点：**
1. **去重** — 表内文字同时出现在 `paragraphs` 中。用 span 区间判断，被 table span 覆盖的 paragraph 不单独产出，否则内容重复
2. **底本** — 保留完整 `analyzeResult.content` 为 `source_content`，所有 offset 指向它
3. **word 级索引** — 额外构建 `words` 列表（text/offset/length/polygon/confidence/page），供数字级锚定与置信度判定
4. **block_id 稳定** — `{prefix}_{index:04d}`，同一文档重复处理必须得到相同 id

### 7.3 `engines/ooxml_docx.py`

解包 zip，按序遍历 `word/document.xml` 的 body 子元素。

**图片提取：**
```xml
<w:drawing><wp:inline>
  <wp:docPr id="7" name="图片 7" descr="季度收入构成"/>   ← alt text，证据级
  <a:graphic>...<a:blip r:embed="rId7"/>...</a:graphic>
</wp:inline></w:drawing>
```
`rId7` → 查 `word/_rels/document.xml.rels` → `word/media/image3.png`

**必须处理的两个坑：**
- `w:pict` + `v:imagedata`（VML，旧格式）与 `w:drawing`（DrawingML）并存，都要解析——从 .doc 转来的文档常见
- `wp:anchor`（浮动图）与 `wp:inline`（嵌入图）锚定段落不同；浮动图锚定其挂靠段落，不是视觉最近段落

**`descr`（alt text）必须抓取**，写入 `Block.alt_text`，`generated=False`。这是作者手写的，证据级，价值高于任何模型生成的描述。

### 7.4 `engines/ooxml_pptx.py`

pptx 与 docx 结构差异很大，**不要复用 docx 的遍历逻辑**。

**1. 单元是 slide，不是文档流。**
每个 slide 产出一个 `slide` block 作为容器，内部 shape 为子 block。chunk 天然以 slide 为单位。

**2. 阅读顺序必须自行推导。**
XML 中 shape 的顺序是 z-order（叠放次序），**不是逻辑阅读顺序**。必须按位置排序：

```python
# Band shapes into rows by vertical position, then sort left-to-right within band.
# EMU: 914400 per inch. Band tolerance ~ 0.15 inch = 137160 EMU.
BAND_TOLERANCE_EMU = 137160
```

**3. 演讲者备注必须提取。**
`ppt/notesSlides/notesSlideN.xml` → `speaker_notes` block。金融演示中备注常含关键假设与免责说明，**绝大多数 pipeline 直接丢弃**。

**4. 占位符继承。**
文字可能定义在 `slideLayout` / `slideMaster` 中而非 slide 本身。需沿 `slide -> layout -> master` 解析占位符，否则标题会丢。

**5. 形状绘制的图 → 确定性边表。**
和 docx 同理，连接关系在 XML 中是明文：

```xml
<p:cxnSp>
  <p:nvCxnSpPr><p:cNvCxnSpPr>
    <a:stCxn id="5" idx="2"/>    <!-- 起点：形状 5 -->
    <a:endCxn id="8" idx="0"/>   <!-- 终点：形状 8 -->
  </p:cNvCxnSpPr></p:nvCxnSpPr>
</p:cxnSp>
```

产出 `ShapeGraph`，`generated=False`。**LLM 只把边表翻译成可读描述，几何与拓扑是确定的。**

**6. 三类"图"分治：**

| 类型 | 判定 | 处理 |
|---|---|---|
| ① 嵌入位图 | `a:blip` 有 `r:embed` | 取 media 文件，送 LLM T3 |
| ② 形状绘制 | `p:sp` + `p:cxnSp` 组合 | 产出边表，LLM 仅翻译 |
| ③ 需渲染 | SmartArt / chart / 嵌入 OLE | 见下 |

③ 的处理：SmartArt 有 `ppt/diagrams/data1.xml`，图表有 `ppt/charts/chartN.xml`，存的是**数据点而非像素**，优先直读。仅当直读失败才退回渲染路径（LibreOffice headless → PDF）。

> **引入渲染器是有成本的**：渲染器版本成为 pipeline 的一部分，需固定版本并纳入验证范围。先用统计数据确认 ③ 的实际占比再决定是否实现——很可能 ①+② 已覆盖 90%。

**7. 一张 slide 可能只有一张图和三个字。**
这是 LLM T3/T4 真正不可替代的场合。此类 slide 若无 LLM，几乎无可索引内容。在 `coverage` 中单独统计此类 slide 占比。

### 7.5 `engines/xlsx_reader.py`

用 `openpyxl`。**xlsx 不需要 DI，不需要 OCR，不需要 LLM。**

**1. 公式是精确的算术 ground truth。**
```python
wb_formula = load_workbook(path, data_only=False)  # formulas
wb_values  = load_workbook(path, data_only=True)   # cached computed values
```

`=SUM(B2:B10)` 直接给出精确的求和关系，**不需要靠关键词猜"合计行"**。cross-foot 在 xlsx 上从"推断"升级为"验证"，`CrossFootResult.source = "formula"`。

**2. 显示值 ≠ 存储值 —— 金融场景的大坑。**
单元格存储 `1234.5678`，数字格式 `#,##0` 显示为 `1,235`。

- `Cell.raw_text` = **显示值**（人在文档上看到的，用于 verbatim 举证）
- `Cell.numeric` = **存储值**（用于 cross-foot 计算）
- 两者必须都保留，不可只留一个

**3. 其他必须处理：**
- 多 sheet：每个 sheet 一个 `sheet` block；隐藏 sheet 也要读，但标记 `hidden=true`
- 合并单元格：`ws.merged_cells.ranges` → 填充 `row_span`/`col_span`
- 隐藏行列：读取但标记
- 空白分隔的多张逻辑表：一个 sheet 内可能有多个独立表格，按连续非空区域切分
- 外部链接公式：记录但不解析

---

## 8. LLM 层

### 8.1 任务分级

**LLM 不是一个开关，是按任务类型分级的能力。**

| 任务 | 内容 | 默认 | 输出标记 | 可举证 |
|---|---|---|---|---|
| **T1** | 表格结构规范化（多级表头合并、行列归位） | 开 | `generated=false` | 是 |
| **T2** | 跨页表接续判定 | 开 | `generated=false` | 是 |
| **T3** | 图 / 流程图语义描述 | 开 | `generated=true` | 否 |
| **T4** | slide 叙事摘要（pptx 专用） | 开 | `generated=true` | 否 |
| **T5** | 数字转录 | **永不** | — | — |
| **T6** | 签名解读 | **永不** | — | — |

**T1/T2 标 `generated=false` 的前提**：输出的字符集合与输入完全一致，只是结构重排。必须校验（8.2）。任一字符变化 → 回退底本，不得标 false。

### 8.2 输出校验与回退（不可省略）

`llm/validator.py`

```python
def validate_llm_output(input_blocks, output_blocks, task) -> ValidationOutcome:
    """
    Checks, in order. Any failure -> discard LLM output, fall back to L0.
    """
    # 1. block id set must be identical (no additions, no omissions)
    # 2. For T1/T2: the multiset of digit characters must be IDENTICAL
    #    between input and output. Not similar. Identical.
    # 3. For T1/T2: the multiset of non-whitespace text characters must
    #    be identical (structure may change, content may not)
    # 4. For T3/T4: output must not contain any digit sequence longer than
    #    3 chars that does not appear in the input block's source text
    #    (prevents fabricated figures in descriptions)
    # 5. For T3/T4: output must not contain personal name patterns when the
    #    input block is a signature region
```

第 4 条很重要：图描述里出现"营收增长 23.7%"但原图数据里没有这个数——这是最典型的图表幻觉。

### 8.3 为 LLM 构造置信度

`llm/consistency.py`

**GPT-5.6 不返回置信度。低置信度可以设阈值，没有置信度则无法区分稳定输出与编造输出。** 因此人为构造：

**自洽性采样（self-consistency）：**

```python
def measure_consistency(block, task, n_samples: int = 3) -> float:
    """
    Run the same task n times with different seeds.
    Return agreement score in [0, 1].

    T1/T2 (structural): agreement = exact match rate of the output structure
                        (cell grid shape + cell content mapping).
                        Structural tasks should be near-deterministic;
                        disagreement is a strong signal of ambiguity.

    T3/T4 (semantic):   agreement = pairwise semantic similarity
                        (embedding cosine). Descriptions vary in wording
                        legitimately, so threshold is lower.
    """
```

**阈值与动作：**

| 任务 | 一致性阈值 | 低于阈值时 |
|---|---|---|
| T1 / T2 | 1.0（必须完全一致） | 回退底本结构，记入 `llm_unstable_blocks` |
| T3 / T4 | 0.75 | 保留输出但标 `llm_consistency` 低，`REVIEW` |

**成本控制：** 自洽性采样使成本翻 n 倍。因此：
- 默认只对 `kind == "table"` 与 `kind in ("figure","shape_graph")` 的 block 采样
- 正文段落不走 LLM，无需采样
- `n_samples` 可配，默认 3；生产可降为 2

**这是本方案对"LLM 无置信度"问题的答案。** 不完美，但把一个不可观测的量变成了可观测的量。

### 8.4 输入构造

按文档流交错组装消息，**图必须插在它在文档流中的位置**：

```
[text]  <!-- blk:p_0140 --> ...正文...
[text]  <!-- blk:fig_003 --> [FIGURE PLACEHOLDER]
[image] <图片字节>
[text]  <!-- blk:p_0143 --> ...正文...
```

> 把所有图堆到消息末尾会导致模型无法把「如图3所示」对应到具体图片。这是最常见的静默失败模式，且失败时输出看起来完全正常。

pptx 的输入单元是 slide：一次一张 slide（含其全部 shape + 备注 + 上一张 slide 的标题作为上下文）。

**配置：**
- `model_snapshot: str` — 必须是带日期的快照 ID，**不接受浮动别名**
- 所有 T3/T4 产物标 `generated=True` + `generator={"model":..., "version":..., "task":...}`

---

## 9. 校验层与渲染

### 9.1 `validation/numbers.py`

`normalize_number(raw: str, locale_hint: str = "en") -> Optional[Decimal]`

每条一个单元测试：

```
"1,234.56"      -> Decimal("1234.56")
"1.234,56"      -> Decimal("1234.56")   # locale_hint="eu"
"(1,234)"       -> Decimal("-1234")     # 括号负数
"1,234-"        -> Decimal("-1234")     # 尾随负号
"$1,234.56"     -> Decimal("1234.56")
"USD 1,234"     -> Decimal("1234")
"1,234¹"        -> Decimal("1234")      # 剥离脚注上标
"1,234*"        -> Decimal("1234")
"１２３４"       -> Decimal("1234")       # 全角转半角
"-"             -> None                 # 财报空值占位
"N/A"           -> None
"壹万贰仟叁佰"   -> Decimal("12300")      # 中文大写，独立解析器
```

**单位提示**：从表头/表注匹配 `单位：千元` / `in thousands` / `人民币百万元`，记入 `Table.unit_hint`。

> **不得自动缩放数值。** 只记录提示，缩放由下游业务决定。服务层擅自乘 1000 是危险的。

### 9.2 `validation/aligner.py`

```python
def assert_verbatim(block_text, source_content, search_window) -> tuple[bool, float]:
    """
    Normalization applied to BOTH sides:
      - collapse consecutive whitespace
      - full-width -> half-width for ASCII range
      - strip markdown decoration
    """
```

1. 双侧归一化
2. `search_window` 内最长公共子串匹配 → `match_ratio`
3. `match_ratio >= 0.95` → 初判 verbatim
4. **数字复核（关键）**：提取双侧数字字符序列，**逐位完全一致**。任何一位不同 → `False`，无视 `match_ratio`

> 第 4 步是本模块存在的全部意义。模糊匹配绝不能抹平数字差异。

### 9.3 `validation/crossfoot.py`

```python
def crossfoot(table: Table) -> list[CrossFootResult]:
```

**xlsx 路径（精确）：** 若 `Cell.formula` 存在，解析 `SUM`/`+` 等关系，直接验证。`source="formula"`，容差为 0。

**推断路径（PDF/Office）：**
1. 展开 `row_span`/`col_span` 构建网格
2. 识别合计行/列（任一命中）：
   - 关键词 `合计|总计|小计|总额|Total|Subtotal|Sum|Grand Total`（大小写不敏感）
   - 位置：最后一个数据行/列
3. 对候选合计行的每一数值列，求上方明细之和，与合计比对
4. 列方向同理
5. 容差：
   ```
   tolerance = Decimal("0.5") * (10 ** -decimals) * n_terms
   ```
6. 数值单元格 < 2 或合计非数值 → `not_applicable`

**输出必须含 expected 与 actual**，人工复核要能直接看到差多少。

### 9.4 `renderer.py`

- 标题按 level 渲染 `#`
- 表格渲染为 **HTML `<table>`**（需 `rowspan`/`colspan`，GFM 管道表做不到）
- 每个 block 前置锚点注释：`<!-- blk:p_0142 -->`
- 图：`<figure blk="fig_003" generated="true|false">...</figure>`
- pptx：每张 slide 渲染为一个 `## Slide N` 段落，备注渲染为 `<aside blk="notes_003">`
- **切分硬规则：绝不在 `<figure>` / `<table>` / `<aside>` 内部切分**

### 9.5 `validation/verdict.py`

规则写死，**不做成可配置**：

```python
def compute_verdict(r) -> Literal["PASS", "REVIEW", "FAIL"]:
    # FAIL: output does not faithfully reproduce the source.
    # This is a RENDERER / LLM-FALLBACK BUG tripwire, not a quality gate.
    # Expected to fire ~never in normal operation (see 1.2).
    if r.digit_render_fidelity < 1.0:
        return "FAIL"

    # REVIEW: possible extraction error. Document is still indexed, flagged.
    if any(x.status == "imbalanced" for x in r.crossfoot):
        return "REVIEW"
    if r.low_confidence_blocks:          # DI confidence < 0.90 on digits
        return "REVIEW"
    if r.llm_unstable_blocks:            # LLM self-consistency below threshold
        return "REVIEW"
    if r.render_fidelity < 0.95:
        return "REVIEW"

    return "PASS"
```

| verdict | 含义 | 下游行为 |
|---|---|---|
| `PASS` | 无异常信号 | 正常入库，chunk 可举证 |
| `REVIEW` | 可能存在抽取错误 | **照常入库**，chunk 带 flag，人工抽检 |
| `FAIL` | 服务自身产出不可信 | 阻塞，报警，查代码 |

`REVIEW` 不阻塞。若上线后 `REVIEW` 比例异常高（>30%），优先排查 cross-foot 容差与合计行识别逻辑，不要先归因于抽取质量。

### 9.6 `chunker.py`

- PDF/docx：按 heading 层级切分，chunk 保留标题链
- pptx：**以 slide 为单位**，备注并入同一 chunk
- xlsx：以逻辑表为单位，sheet 名 + 表头并入
- chunk 携带其覆盖的全部 anchor 与 `verbatim` 标记
- **绝不在 `<table>` / `<figure>` / `<aside>` 内部切分**；超长表整体成 chunk 并标 `oversized=true`
- chunk 级 `verbatim` = 其所有 block `verbatim` 的逻辑与

---

## 10. 输出契约

```json
{
  "doc_id": "sha256:abc123...",
  "source_uri": "blob://.../deck.pptx",
  "format": "pptx",
  "route": "ooxml_pptx",
  "engine": {
    "l0": {"name": "ooxml_pptx", "version": "0.3.1"},
    "l0_signature": null,
    "llm": {"model": "gpt-5.6-<snapshot>", "tasks": ["T3", "T4"],
            "consistency_samples": 3}
  },

  "content": {
    "markdown": "<!-- blk:sl_001 -->\n## Slide 1\n...",
    "source_content": "...",
    "anchors": [
      {
        "block_id": "fig_003",
        "kind": "figure",
        "verbatim": false,
        "generated": true,
        "llm_consistency": 0.88,
        "anchor": {"kind": "structural", "part": "/ppt/slides/slide3.xml",
                   "path": "spTree/pic[2]", "ordinal": 47,
                   "slide_index": 3, "media": "/ppt/media/image5.png"}
      }
    ]
  },

  "validation": {
    "verdict": "REVIEW",
    "render_fidelity": 0.998,
    "digit_render_fidelity": 1.0,
    "crossfoot": [
      {"table_block_id": "tb_0007", "axis": "column", "index": 3,
       "expected": "45231.00", "actual": "45230.00",
       "status": "imbalanced", "tolerance": "0.50", "source": "inferred"}
    ],
    "low_confidence_blocks": ["p_0233"],
    "llm_unstable_blocks": [],
    "signatures": [],
    "coverage": {
      "blocks_total": 312,
      "blocks_with_anchor": 312,
      "figures_total": 18,
      "figures_described": 16,
      "figures_needing_render": 2,
      "image_only_slides": 4
    },
    "issues": []
  }
}
```

**下游使用方式（写进 README）：**

```python
if result["validation"]["verdict"] == "FAIL":
    alert(); return                       # service bug, do not index

for chunk in chunks:
    if chunk["verbatim"] and not chunk["generated"]:
        index_as_citable(chunk)           # 可作为引用证据
    else:
        index_as_recall_only(chunk)       # 仅参与召回，不可举证
```

---

## 11. 测试要求

### 11.1 单元测试
- `numbers.py`：9.1 每条规则一个用例
- `crossfoot.py`：平衡表、不平衡表、含四舍五入表、无合计行表、xlsx 公式表
- `aligner.py`：**必须有"整体相似度 0.99 但有一位数字不同"的用例，断言返回 False**
- `llm/validator.py`：**必须有"LLM 输出改动了一个数字"的用例，断言触发回退**
- `ooxml_pptx.py`：z-order 与阅读顺序不一致的 slide，断言排序正确

### 11.2 集成测试 fixture

`tests/fixtures/` 覆盖：
1. 多级表头财务报表（数字原生 PDF）
2. 扫描件 PDF（含签名页）
3. 混合 PDF（数字页 + 扫描插页）
4. 含合并单元格与跨页续表的报表
5. docx：含 VML 旧格式图 + 浮动图 + alt text
6. pptx：形状绘制流程图 + 纯图 slide + 演讲者备注 + SmartArt
7. xlsx：多 sheet + 公式 + 合并单元格 + 显示值≠存储值
8. 括号负数 + 千分位 + 单位声明（千元）
9. 中文大写金额
10. 劣质扫描件（低对比度）

### 11.3 `scripts/benchmark.py`

**这是第一个应该跑起来的东西。**

**必须先人工标注 20-30 份文档的 ground truth**（只标数字与关键字段即可，一到两天工作量）。没有 GT，本服务的抽取准确率对所有人都是未知数。

对照维度：

```
doc_id | 格式 | 路由 | 数字准确率 | 签名检出率 | 图覆盖率 | 用时 | 成本 | 错误样例
```

对照组：
- A：DI only（LLM 全关）
- B：DI + LLM（本方案默认）
- C：LLM 直出（不带底本）——用于量化"不做锚定"的代价

分层统计：印刷体数字 / 手写数字 / 表内数字 / 正文数字 / 各输入格式。

---

## 12. 禁止事项

以下任一条不得违反，即使能让代码更简洁：

1. **禁止**让 LLM 生成或修改任何数字字符
2. **禁止**填充 `signatory_name`，即使模型"看起来能读出来"
3. **禁止**用 `float` 表示金额，一律 `Decimal`
4. **禁止**在 verbatim 校验中对数字做模糊匹配
5. **禁止**根据 `unit_hint` 自动缩放数值
6. **禁止**使用浮动模型别名，必须用带日期的快照 ID
7. **禁止**在日志中输出文档内容或客户信息
8. **禁止**把 `verdict` 判定规则做成可配置项
9. **禁止**在 `<table>` / `<figure>` / `<aside>` 内部切分 chunk
10. **禁止**用 DI 的 `outputContentFormat=markdown` 作为底本
11. **禁止**把 docx/pptx 送 DI 处理（DI 对其不返回 figures，见 2.2）
12. **禁止**跳过 LLM 输出校验直接采用结果
13. **禁止**用 z-order 作为 pptx 的阅读顺序
14. **禁止**在 xlsx 中只保留显示值或只保留存储值

---

## 13. 实施顺序

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| **M0** | GT 标注（20-30 份，仅数字与关键字段） | 有可用的 ground truth 集 |
| **M1** | router + di_client + di_parser + numbers + crossfoot | 一份真实财报输出 IR；cross-foot 能发现人为注入的错误 |
| **M2** | aligner + verdict + renderer + api | 完整两层 response；FAIL 判定能触发 |
| **M3** | xlsx_reader | 公式路径 cross-foot 精确验证；显示值/存储值双保留 |
| **M4** | ooxml_docx + ooxml_pptx | 形状边表正确产出；pptx 阅读顺序正确；备注不丢 |
| **M5** | llm 层（T1-T4 + validator + consistency） | LLM 全关时服务功能不受影响；改数字必触发回退 |
| **M6** | signature（需先训练自定义模型，≥5 样本） | 签名正确检出；输出中无姓名字段 |
| **M7** | chunker + benchmark | 三组对照实验出报表 |

**M0 先做。** 没有 GT，M1 之后所有关于"准确率够不够"的讨论都是猜测。

---

## 14. 部署前置条件

本规格书只覆盖工程实现。落地前需在组织内部确认下列事项，具体条款与负责人记录在本仓库之外的内部文档中：

1. 第三方 AI 服务的使用授权状态
2. 数据驻留与跨域调用的合规边界
3. 文档中个人信息的脱敏与授权链路
4. 模型版本登记与验证证据的留存要求
5. 云服务资源的部署区域限制
6. LLM 自洽性采样使推理成本翻 2-3 倍，预算确认

上述任一项未确认前，不建议进入 M5（LLM 层）。M0-M4 为纯确定性实现，不涉及第三方模型调用，可先行推进。

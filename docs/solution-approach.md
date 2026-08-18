# 分类处理思路与 POC 计划

针对 [coverage-checklist.md](coverage-checklist.md) 中的八类问题给出处理思路。
不限定 Azure OCR,开源库、LLM/VLM、原生格式直读均在候选范围内。

## 三条总原则

1. **原生格式优先直读,OCR 只是兜底。** docx/pptx/xlsx 的表格、公式、图表
   数值、连接关系在 XML 中本就是结构化的,直读准确率上限 100%;把它们
   渲染成像素再识别,是把已知信息先丢掉再猜回来。
2. **校验层独立于引擎。** 数字保真、漏失、截断、重复这类问题不靠换引擎解决,
   靠一层与引擎无关的自动校验。任何引擎接入都复用同一层。
3. **先有测试集,再做 POC。** 没有已知真值,POC 的结论只是印象。

## 一、先构造测试集(所有 POC 的前置)

**核心设计:一份源文档 → 三种输入形态,真值完全相同。**

```
构造源文档(docx/pptx/xlsx) ──► 真值 JSON(构造时直接产出)
        │
        ├─► 原生 Office 文件
        ├─► LibreOffice 转 PDF(有文本层)
        └─► PDF 渲染为图像(模拟扫描件,可加噪声/倾斜)
```

同一真值下对比三种形态,可以直接量化「转 PDF 损失多少」「扫描损失多少」,
这是拿真实语料无法干净得到的结论。

**真值 by construction**:生成时同步写出表格行列与单元格内容、公式 LaTeX、
图形节点与边、全部数字 token 列表——**无需人工标注**。

**两个额外好处**:合成数据不含业务信息,**可以入库**,直接作为回归测试集
(真实语料受红线约束不能入库);且不依赖业务方提供文档,立刻可以开工。

**工具**:`python-docx` / `python-pptx` / `openpyxl` 生成;SmartArt、OMML 公式
这类库不支持的,用模板文件 + 直接改 XML(现有 `tests/make_fixtures.py` 即
此思路);`soffice --headless --convert-to pdf` 转换;`pdf2image`/PyMuPDF 渲染。

**规模**:每类特性 5–10 个 case,合计 50–80 个文档即可,不必求大。

**边界**:合成文档比真实文档干净。它测的是**能力边界**(某特性支不支持),
真实难度仍需真实语料抽样补测。两者都要,合成的先做。

## 二、分类处理思路

| 类别 | 处理思路 | 候选方案 |
| --- | --- | --- |
| **表格结构** | 原生 Office 走 OOXML 直读拿 `gridSpan/vMerge`;PDF 有文本层的靠字符坐标做列聚类(x 投影)重建拓扑;扫描件走版面模型。跨页合并用表头指纹 + 列数一致性判定,而非位置相邻 | `pdfplumber`、`camelot`(lattice/stream)、PyMuPDF、Table Transformer、PP-Structure、`marker`、VLM 直出(强在无边框表,弱在长表截断) |
| **公式与数字字符** | docx 走 OMML → MathML → LaTeX 确定性转换(**pandoc 可一步到位**);PDF 走公式检测 + 专用数学 OCR。**数字保真是校验问题不是识别问题**:正则抽数字 token 做集合对账,用 `Decimal` 保精度,禁止 float | OMML2MML.XSL、`pandoc`、MinerU(MFD+MFR)、`pix2tex`、`texify`、Nougat、Azure DI formula add-on(**先查开关**) |
| **图片与图形** | Office 图片从 OOXML 的 media 直接取二进制 + 锚点定位;**chart 数值直读 `c:numCache`/`c:strCache`,零误差**;流程图用 `p:cxnSp` 的 `stCxn/endCxn` 指向 shape id 确定性建图 → mermaid。图片型 chart/流程图才交给 VLM | OOXML 直读(首选)、VLM chart-to-table、DePlot、Azure CU 图表转数据、`mermaid-cli` 校验语法 |
| **版面与阅读顺序** | PDF 先做版面分析再定序:XY-cut 递归切分对双栏足够且确定;页眉页脚用**跨页重复文本检测**剔除;标题层级用字号 + 加粗 + 编号模式聚类映射 | XY-cut、`unstructured`(hi_res)、PP-StructureV3、DocLayout-YOLO、LayoutReader |
| **内容完整性** | 纯校验层,不换引擎:字符/段落数与源对账(原生 Office 有真值);末尾句中断开 + 长度与页数比例异常 → 判截断;n-gram 连续重复率 → 判复读;同文档跑 2–3 次算差异率 → 判稳定性 | 自研校验层(`doceval check`),零依赖 |
| **文档形态与格式** | **xlsx 根本不该走 OCR**,`openpyxl` 直读,重点处理合并单元格、公式 vs 值、多 sheet、隐藏行列;老二进制 `.doc/.xls/.ppt` 用 LibreOffice 批量转 OOXML;修订痕迹 `w:ins/w:del`、批注、PPT 备注页均可直读,按需保留或剔除 | `openpyxl`、`soffice --convert-to`、OOXML 直读 |
| **下游可用性** | 表头展平按 `rowSpan/colSpan` 做笛卡尔展开,父子列名用分隔符连接;单元格内容转义 `|`、`*`;超宽表转置或拆分;分块保证表格不跨 chunk,每块携带 `(file, page, bbox)` 回链 | 自研后处理层 |
| **工程与可复现** | 引擎版本固定,生成式引擎 `temperature=0` 并跑两次比对;记录每引擎的页费、时延、页数上限,形成成本基线 | 自研评测脚手架 |

## 三、POC 批次

每批只回答一个问题,做完看结果再决定下一批。

| 批次 | 验证问题 | 大致投入 |
| --- | --- | --- |
| B0 | 测试集构造 + 真值自动产出跑通 | 3–5 天 |
| B1 | OOXML 直读能否解决 Office 的表格/公式/chart/流程图(预期上限最高) | 5 天 |
| B2 | 校验层能否自动发现数字错误、漏失、截断、重复 | 3 天 |
| B3 | PDF 表格:坐标重建 vs 开源版面模型 vs VLM,三者对比 | 1–2 周 |
| B4 | PDF 公式与阅读顺序:MinerU / marker / Nougat 对照 | 1 周 |

B1、B2 优先:确定性、零外部依赖、不花页费,且覆盖面最大。

> 开源工具迭代快,上表工具名与能力以实际拉取版本的文档为准。

# parser-ab-eval

文档解析方案 A/B 的**证据级**对比评测工作区。

A = Azure Document Intelligence `prebuilt-layout` · B = Local Loader(markitdown 路线)

---

## 这个包解决什么问题

现有评测报告是「每文件一张指标表 + 附一张整页截图」。
指标粒度是"文件 × 指标",证据粒度是"整页",两者对不上——
看到 `数字 Recall 17.5%` 时没法知道**具体漏了哪些、在页面哪里、A/B 各输出成了什么**。

本包引入 **anchor(证据锚点)层**:所有指标都定义成 anchor 集合上的聚合函数,
于是每个指标数字都能下钻到具体证据实例。

报告分四层:

```
L0  失效模式   跨文件聚合的现象   ← 汇报看这层就够
L1  总览记分卡  实例级净胜负
L2  逐文件表    每格挂实例编号
L3  证据卡      一个 anchor = 一张卡,原文裁剪 + A 输出 + B 输出
```

---

## 先看效果

双击打开 **`report.PREVIEW.html`**。这是用假数据渲染的最终报告样子。
重点看三种卡片形态:

| 卡 | 形态 | 看点 |
|---|---|---|
| `#01` | 三栏 | 原文裁剪 + A/B 片段,差异三色标记 |
| `#03` | 双栏 | 阅读顺序折线——交叉本身就是证据,τ 值只是数字化 |
| `#06` | 双栏 | 表格 cell 热力图——TEDS 0.62 是抽象的,"红块集中在第 3 列"是具体的 |
| `#05` | 三栏 | **A 失败**的案例。报告不能只列 B 的问题 |

顶部筛选器可用,试试「仅 A 失败」。

---

## 目录

```
parser-ab-eval/
├── README.md                    ← 你在看的这个
├── PROMPT_FOR_COPILOT.md        ← 整段贴给 Copilot 的实现说明
├── report.PREVIEW.html          ← 假数据渲染的效果预览
│
├── templates/
│   └── report_shell.html        🔒 冻结:全部 CSS / JS / 骨架
├── tools/
│   ├── render_report.py         🔒 冻结:视图模型 → HTML
│   ├── _demo_data.py            📖 只读:假数据 = 视图模型的 schema 活文档
│   ├── build_anchors.py         ✍ Copilot 写:STAGE 1
│   ├── match.py                 ✍ Copilot 写:STAGE 2
│   ├── render_crops.py          ✍ Copilot 写:STAGE 3
│   └── build_report.py          ✍ Copilot 写:STAGE 4
└── eval/
    ├── sources/                 放原始文件
    ├── out_a/                   放 A 的 markdown(与 sources 同名 .md)
    ├── out_b/                   放 B 的 markdown
    ├── gt/SCHEMA.md             人工 GT 的格式说明
    └── crops/                   STAGE 3 产物
```

🔒 = 不要让 Copilot 改 · 📖 = 只读参考 · ✍ = Copilot 要写

---

## 使用步骤

### 0. 环境

```bash
pip install pymupdf python-docx python-pptx rapidfuzz lxml Pillow
```

自检——这一步必须先跑通:

```bash
python tools/render_report.py --demo -o report.PREVIEW.html
```

看到 `wrote report.PREVIEW.html (34 KB, 6 cards)` 就说明模板管线正常。

### 1. 放数据

```
eval/sources/GOP_R11_v9.3.docx
eval/out_a/GOP_R11_v9.3.md      ← Azure 的输出
eval/out_b/GOP_R11_v9.3.md      ← Local Loader 的输出
```

文件名必须对齐(扩展名不同、主干名相同)。

### 2. 交给 Copilot

在 VS Code 打开本目录,把 `PROMPT_FOR_COPILOT.md` **整段**贴进 Copilot Chat
(建议 Agent / Edits 模式)。

它会分四个 STAGE 实现。**每个 STAGE 跑通、你确认过再让它进下一个。**
prompt 里每个 STAGE 末尾都写了验收信息要打印什么。

### 3. 出报告

```bash
python tools/build_anchors.py
python tools/match.py
python tools/render_crops.py
python tools/build_report.py -o report.html
```

`report.html` 是单文件自包含的,断网双击可开,可以直接发给评审。

---

## 关键设计约束(别让 Copilot 绕过)

1. **anchor 从源文件原生结构抽,不从 A 或 B 的输出抽。**
   用 A 当 B 的参照就是让 A 给自己判卷。
2. **docx 必须混合遍历 `w:p` 和 `w:tbl`。**
   `document.paragraphs` 再 `document.tables` 是最常见的坑,阅读顺序 GT 会直接错。
3. **页眉页脚必须在 GT 里排除。**
   A 走 OCR 会把页码当正文——这是个真实差异,不排除就会被当成噪声掩盖掉。
4. **bbox 查不到就标 unresolved,不许猜。** 证据卡支持无截图的纯文本模式。
5. **不输出加权总分。**
   加权分会把"按文档形态分流"这个真结论压掉——docx 上 B 反而在数字上更好,
   因为它直读 XML;pdf/pptx 上 A 明显更好,因为它有版面分析。
   这个结论比"整体选谁"有用得多。
6. **A 失败的案例和 B 失败的一样要列全。**

---

## 已知的前置风险

**STAGE 3 需要把 docx/pptx 转 PDF 才能裁图。**
公司机器大概率没装 LibreOffice。降级路径是 `win32com`,但要求本机装了桌面版 Office
(纯 Web 版不行)。跑之前先确认:

```bash
soffice --version          # 或
python -c "import win32com.client; print('ok')"
```

两条都不通也没关系——全部走纯文本证据卡,信息不丢,只是没有截图。
`render_report.py` 已经支持 `crop.kind="none"` 的降级形态,见预览里的 `#04` 和 `#05`。

**GT 质量决定一切。**
STAGE 1 那个"随机抽 5 条人工核对"的验收点不要跳过。
GT 抽错了,后面再漂亮的卡片也只是在精确地展示错误结论。

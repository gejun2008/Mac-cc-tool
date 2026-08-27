# -*- coding: utf-8 -*-
"""
_demo_data.py — 假数据。

两个用途:
  1. 让 render_report.py --demo 能跑通,证明模板管线完整
  2. 作为「视图模型 schema」的活文档 —— build_report.py 要产出的就是这个形状

数据全部是编造的,不要引用其中任何数字。
"""

# ---- 内联 SVG 素材(真实运行时,三栏卡的 crop 换成 {"kind":"img","path":...}) ----

CROP_NUM = """<svg viewBox="0 0 320 92" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="原文区域裁剪">
<rect width="320" height="92" fill="#F1F2EE"/>
<rect x="10" y="8" width="240" height="4" rx="2" fill="#D2D5CE"/>
<rect x="10" y="18" width="190" height="4" rx="2" fill="#D2D5CE"/>
<rect x="8" y="34" width="304" height="26" fill="none" stroke="#A83232" stroke-width="1.5" stroke-dasharray="4 2"/>
<text x="14" y="52" font-family="monospace" font-size="11" fill="#191C18">1.2 · July 2019 · Annual review and</text>
<rect x="10" y="68" width="215" height="4" rx="2" fill="#D2D5CE"/>
<rect x="10" y="78" width="160" height="4" rx="2" fill="#D2D5CE"/></svg>"""

CROP_TABLE = """<svg viewBox="0 0 320 108" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="表格区域裁剪">
<rect width="320" height="108" fill="#F1F2EE"/>
<rect x="8" y="6" width="304" height="96" fill="none" stroke="#A83232" stroke-width="1.5" stroke-dasharray="4 2"/>
<rect x="14" y="12" width="292" height="14" fill="#C9CDC4"/>
<text x="18" y="22" font-family="monospace" font-size="8">Edition   Publication date       Details of changes</text>
<g font-family="monospace" font-size="8" fill="#3A3F38">
<rect x="14" y="28" width="292" height="13" fill="#E4E7DF"/>
<text x="18" y="37">1.0       September 2016       Creation of draft GOP</text>
<text x="18" y="51">1.1       June 2018            Updated draft from GTRF</text>
<rect x="14" y="56" width="292" height="13" fill="#E4E7DF"/>
<text x="18" y="65">1.2       July 2019            Annual review</text>
<text x="18" y="79">2.0       June 2021            Annual Renewal, FIM</text>
<rect x="14" y="84" width="292" height="13" fill="#E4E7DF"/>
<text x="18" y="93">3.0       May 2022             Appendix 3 added</text></g></svg>"""


def _order_svg(color, pts, labels, cross=False):
    boxes = """<g fill="#EDEFE9" stroke="#D2D5CE">
<rect x="16" y="12" width="268" height="24"/>
<rect x="16" y="48" width="80" height="46"/><rect x="110" y="48" width="80" height="46"/><rect x="204" y="48" width="80" height="46"/>
<rect x="16" y="106" width="80" height="46"/><rect x="110" y="106" width="80" height="46"/><rect x="204" y="106" width="80" height="46"/>
<rect x="16" y="164" width="268" height="16"/></g>"""
    poly = " ".join(f"{x},{y}" for x, y in pts)
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="8" fill="{color}"/>'
        f'<text x="{x-3}" y="{y+3}">{lb}</text>'
        for (x, y), lb in zip(pts, labels)
    )
    return (
        f'<svg viewBox="0 0 300 190" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="阅读顺序折线">'
        f'<rect width="300" height="190" fill="#FCFDFA"/>{boxes}'
        f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.6" opacity=".85"/>'
        f'<g font-family="monospace" font-size="9" fill="#fff">{nodes}</g></svg>'
    )


ORDER_A = _order_svg("#1F4E8C",
                     [(150, 24), (56, 71), (150, 71), (244, 71),
                      (56, 129), (150, 129), (244, 129), (150, 172)],
                     "12345678")
ORDER_B = _order_svg("#8F5E0E",
                     [(56, 71), (244, 129), (150, 24), (56, 129),
                      (244, 71), (150, 172), (150, 129)],
                     "1234567")


def _heat(cells):
    """cells: 5x4 状态矩阵,取值 match/wrong/missing/extra"""
    fill = {"match": "#E4F0E9", "wrong": "#F6EDD8", "missing": "#F8E8E6", "extra": "#EDEEEA"}
    r = []
    for i, row in enumerate(cells):
        for j, st in enumerate(row):
            r.append(f'<rect x="{14+j*68}" y="{10+i*22}" width="68" height="22" fill="{fill[st]}"/>')
    return (
        '<svg viewBox="0 0 300 130" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="单元格判定热力图"><rect width="300" height="130" fill="#FCFDFA"/>'
        f'<g stroke="#C9CDC4" stroke-width="1">{"".join(r)}</g></svg>'
    )


HEAT_A = _heat([
    ["match"] * 4,
    ["match", "match", "wrong", "match"],
    ["match"] * 4,
    ["match", "missing", "match", "match"],
    ["match", "match", "match", "wrong"],
])
HEAT_B = (
    '<svg viewBox="0 0 300 130" xmlns="http://www.w3.org/2000/svg" role="img" '
    'aria-label="B 方案全部缺失"><rect width="300" height="130" fill="#FCFDFA"/>'
    '<rect x="14" y="10" width="272" height="110" fill="#F8E8E6" stroke="#C9CDC4"/>'
    '<text x="150" y="68" text-anchor="middle" font-family="monospace" font-size="10" '
    'fill="#A83232">无表格结构 · 20/20 缺失</text></svg>'
)

# --------------------------------------------------------------------------

REPORT = {
    "meta": {
        "title": "解析方案 A/B 对比报告",
        "items": [
            ("A", "Azure Layout OCR (prebuilt-layout)"),
            ("B", "Local Loader (markitdown)"),
            ("样本", "11 文件 / 展示 3"),
            ("GT", "3 文件人工复核"),
            ("状态", "DEMO · 数据为假"),
        ],
    },

    "modes": [
        {"loses": "b", "title": "B 在版面型文档上丢表格",
         "desc": "pptx / 扫描版 pdf 中,B 把表格降级为无分隔符的连续文本行,markdown 表格结构完全丢失。docx 上不出现。",
         "scope": "5/5 版面文件 · 12/12 张表", "refs": ["c02", "c06"]},
        {"loses": "a", "title": "A 在流式 docx 上漏正文数字",
         "desc": "A 走 OCR 路径,页眉页脚与正文混排处出现数字吞并;B 直读 XML 不受影响。",
         "scope": "3/6 docx · 19 个数字", "refs": ["c05"]},
        {"loses": "b", "title": "B 阅读顺序按 shape 索引而非视觉流",
         "desc": "pptx 多列版面下 B 按 XML 中 shape 出现顺序输出,与人读顺序交叉。",
         "scope": "Kendall τ · A 0.94 / B 0.38", "refs": ["c03"]},
        {"loses": "b", "title": "B 输出的 markdown 表格列数不一致",
         "desc": "分隔行与数据行列数不匹配,导致渲染器整表回退为纯文本,下游 chunking 会把整张表当一段。",
         "scope": "9 处 / 3 文件", "refs": ["c04"]},
    ],

    "scorecard": [
        {"metric": "数字 Recall", "n": 412, "a_win": 88, "b_win": 61, "both_fail": 23,
         "note": "另有 240 个 anchor 两侧一致", "drill": "c01"},
        {"metric": "关键表格缺失", "n": 31, "a_win": 12, "b_win": 0, "both_fail": 1,
         "note": "B 无独胜项", "drill": "c02"},
        {"metric": "表格内容质量 (TEDS)", "n": 18, "a_win": 14, "b_win": 1, "both_fail": 3,
         "note": "均值 A 0.82 / B 0.31", "drill": "c06"},
        {"metric": "阅读顺序 (Kendall τ)", "n": 27, "a_win": 19, "b_win": 2, "both_fail": 0,
         "note": "均值 A 0.94 / B 0.38", "drill": "c03"},
        {"metric": "Markdown 语法", "n": 11, "a_win": 8, "b_win": 1, "both_fail": 0,
         "note": "错误数 A 3 / B 27", "drill": "c04"},
    ],

    "files": {
        "cols": ["文件", "参照", "数字 Recall", "表格缺失", "TEDS", "阅读顺序 τ", "MD 语法", "结论"],
        "rows": [
            ["GOP R11 v9.3<b>.docx</b>", "<span class='num'>GT</span>",
             "<span class='win-b'>B 65/68</span> · A 61/68 <a class='drill' href='#c05'>#05</a>",
             "<span class='win-a'>A 0</span> · B 0", "<span class='win-a'>.91</span> / .88",
             "<span class='tie'>1.00 / 1.00</span>", "<span class='tie'>0 / 0</span>",
             "<span class='win-b'>B 胜 (+4 数字)</span>"],
            ["GOP R11 v9.3<b>.pdf</b>", "<span class='num'>GT</span>",
             "<span class='win-a'>A 66/68</span> · B 44/68 <a class='drill' href='#c01'>#01</a>",
             "<span class='win-a'>A 0</span> · B 3 <a class='drill' href='#c02'>#02</a>",
             "<span class='win-a'>.84</span> / .29", "<span class='win-a'>.96</span> / .61",
             "0 / <span class='win-b'>7</span> <a class='drill' href='#c04'>#04</a>",
             "<span class='win-a'>A 胜 (全指标)</span>"],
            ["Model Approval<b>.pptx</b>", "<span class='num'>GT</span>",
             "A 7/40 · <span class='win-b'>B 13/40</span>",
             "<span class='win-a'>A 0</span> · B 4 <a class='drill' href='#c06'>#06</a>",
             "<span class='win-a'>.62</span> / .00",
             "<span class='win-a'>.89</span> / .21 <a class='drill' href='#c03'>#03</a>",
             "1 / <span class='win-b'>12</span>", "<span class='win-a'>A 胜 (表格+顺序)</span>"],
        ],
        "note": "docx 行 B 在数字上反超,不是噪声,是路径差异(B 直读 OOXML,A 走 OCR)。"
                "结论应写成「按文档形态分流」,而非「整体选 A」。",
    },

    "groups": [
        {
            "file": "GOP R11 v9.3.pdf",
            "tie_count": 138,
            "cards": [
                {
                    "id": "c01", "kind": "number", "kind_label": "数字缺失", "fail": "b",
                    "verdict": "A 胜", "loc": "GOP R11 v9.3.pdf · p4 · bbox [212,486,1018,512]",
                    "crop": {"kind": "svg", "svg": CROP_NUM},
                    "crop_cap": "bbox 上下外扩 40px · 红框为 anchor 本体",
                    "gt": "1.2 / July 2019",
                    "a": {"snippet": "| 1.2 | July <mark class=\"hit\">2019</mark> | Annual review and\nfeedback from region and country SMEs |",
                          "flag": ("ok", "✓ 命中 2/2")},
                    "b": {"snippet": "1.2 July <mark class=\"gap\">2019</mark> Annual review and\nfeedback from region and country SMEs",
                          "flag": ("no", "✗ 丢 1/2 · 年份被合入上一行页眉")},
                    "foot": [("打开原页", "#"), ("A md L142", "#"), ("B md L98", "#")],
                    "footnote": "anchor 0xA31F · type=number · source=manual_gt",
                },
                {
                    "id": "c02", "kind": "table", "kind_label": "表格退化", "fail": "b",
                    "verdict": "A 胜", "loc": "GOP R11 v9.3.pdf · p4 · Version history 6×3",
                    "crop": {"kind": "svg", "svg": CROP_TABLE},
                    "crop_cap": "表格 bbox 整体裁剪", "gt": "6 行 × 3 列,含表头",
                    "a": {"snippet": "| Edition | Publication date | Details |\n|---|---|---|\n| 1.0 | September 2016 | Creation... |\n| 1.1 | June 2018 | Updated draft... |\n| 1.2 | July 2019 | Annual review... |\n| 2.0 | June 2021 | Annual Renewal... |\n| 3.0 | May 2022 | Appendix 3 added |",
                          "flag": ("ok", "✓ 6×3 结构完整 · TEDS 0.94")},
                    "b": {"snippet": "<mark class=\"gap\">Edition Publication date Details of\nchanges 1.0 September 2016 Creation\nof draft GOP, Global instructions 1.1\nJune 2018 Updated draft from GTRF\nServices and TRM Feedback 1.2 July\n2019 Annual review and feedback...</mark>",
                          "flag": ("no", "✗ 结构完全丢失 · TEDS 0.00 · 行列边界不可恢复")},
                    "foot": [("打开原页", "#"), ("A md L88", "#"), ("B md L61", "#")],
                    "footnote": "anchor 0xB702 · rows=6 cols=3",
                },
                {
                    "id": "c04", "kind": "syntax", "kind_label": "MD 语法", "fail": "b",
                    "verdict": "A 胜", "loc": "GOP R11 v9.3.pdf · B 输出 L61–66",
                    "crop": {"kind": "none", "why": "语法错误不挂 bbox,证据为输出片段本身"},
                    "gt": "GFM 要求 表头列数 == 分隔行列数 == 数据行列数",
                    "a": {"snippet": "| Edition | Date | Details |\n|---|---|---|\n| 1.0 | Sep 2016 | Creation |",
                          "flag": ("ok", "✓ 3 / 3 / 3 列一致")},
                    "b": {"snippet": "| Edition | Date | Details |\n<mark class=\"wrong\">|---|---|</mark>\n| 1.0 | Sep 2016 | Creation | <mark class=\"wrong\">|</mark>",
                          "flag": ("no", "✗ 3 / 2 / 4 列 · 整表降级为纯文本")},
                    "foot": [("B md L61", "#")],
                    "footnote": "rule=table_col_mismatch · severity=high",
                },
            ],
        },
        {
            "file": "GOP R11 v9.3.docx",
            "tie_count": 61,
            "cards": [
                {
                    "id": "c05", "kind": "number", "kind_label": "数字缺失", "fail": "a",
                    "verdict": "B 胜", "loc": "GOP R11 v9.3.docx · §3.2 · 页眉混排区",
                    "crop": {"kind": "none", "why": "bbox unresolved — search_for 命中 4 次,拒绝猜测位置"},
                    "gt": "SDC must advise within 5 business days",
                    "a": {"snippet": "Page <mark class=\"wrong\">7</mark> SDC must advise within\n<mark class=\"gap\">5</mark> business days",
                          "flag": ("no", "✗ 页眉页码被当正文,正文数字被吞")},
                    "b": {"snippet": "SDC must advise within <mark class=\"hit\">5</mark>\nbusiness days",
                          "flag": ("ok", "✓ 直读 XML,页眉天然分离")},
                    "foot": [("A md L317", "#"), ("B md L241", "#")],
                    "footnote": "该模式在 docx 上系统性出现 · 见 L0 第 2 条",
                },
            ],
        },
        {
            "file": "Model Approval Framework.pptx",
            "tie_count": 27,
            "cards": [
                {
                    "id": "c03", "kind": "order", "kind_label": "阅读顺序", "fail": "b",
                    "layout": "duo", "verdict": "A 胜",
                    "loc": "Model Approval Framework.pptx · slide 3 · 9 blocks",
                    "legend": [("#1F4E8C", "A 输出顺序"), ("#8F5E0E", "B 输出顺序"),
                               ("#D2D5CE", "block bbox")],
                    "a": {"lab": "A · τ = 0.89", "svg": ORDER_A,
                          "cap": "标题 → 逐行从左到右 → 页脚。逆序对 2。"},
                    "b": {"lab": "B · τ = 0.21", "svg": ORDER_B,
                          "cap": "按 shape XML 索引输出,交叉 11 次,标题排第 3 位。"},
                    "foot": [("打开原页", "#"), ("A md L204", "#"), ("B md L155", "#")],
                    "footnote": "inversions A 2 / B 11 · n=9",
                },
                {
                    "id": "c06", "kind": "table", "kind_label": "表格内容质量", "fail": "b",
                    "layout": "duo", "verdict": "A 胜",
                    "loc": "Model Approval Framework.pptx · slide 6 · 5×4 表 · 20 cells",
                    "legend": [("#E4F0E9", "正确"), ("#F6EDD8", "内容错"),
                               ("#F8E8E6", "缺失"), ("#EDEEEA", "多出")],
                    "a": {"lab": "A · TEDS 0.62 · 17/20 正确", "svg": HEAT_A,
                          "cap": "3 处偏差集中在第 3 列合并单元格附近"},
                    "b": {"lab": "B · TEDS 0.00 · 0/20 正确", "svg": HEAT_B,
                          "cap": "B 输出为 18 行纯文本,无法与 GT 网格对齐"},
                    "foot": [("打开原页", "#"), ("A md L402", "#"), ("B md L288", "#")],
                    "footnote": "TEDS-struct A 0.71 / B 0.00 · TEDS-content A 0.62 / B 0.00",
                },
            ],
        },
    ],

    "footer": "DEMO 渲染 · 所有数字为假,仅用于验证模板管线",
}

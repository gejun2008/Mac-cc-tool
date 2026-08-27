> ⚠ 作废。GT 实际为 markdown 格式,见 AMENDMENT-001-gt-format-and-bbox.md

# 人工 GT 文件格式

每个需要人工 GT 的源文件对应一个同名 `.json`:
`eval/sources/GOP_R11_v9.3.pdf` → `eval/gt/GOP_R11_v9.3.json`

docx / pptx 的 GT 由 `build_anchors.py` 从 OOXML 自动抽取,**不需要写这个文件**。
只有 pdf(以及自动抽取结果需要人工修正的文件)才需要。

```json
{
  "file": "GOP_R11_v9.3.pdf",
  "reviewed_by": "jun",
  "reviewed_at": "2026-08-27",
  "blocks": [
    {
      "order": 1,
      "page": 4,
      "bbox": [212, 180, 1018, 210],
      "type": "heading",
      "text": "Document history"
    },
    {
      "order": 2,
      "page": 4,
      "bbox": [212, 290, 1018, 570],
      "type": "table",
      "text": "Edition | Publication date | Details of changes",
      "table": {
        "rows": 6,
        "cols": 3,
        "cells": [
          ["Edition", "Publication date", "Details of changes"],
          ["1.0", "September 2016", "Creation of draft GOP, Global instructions"],
          ["1.1", "June 2018", "Updated draft from GTRF Services and TRM Feedback"],
          ["1.2", "July 2019", "Annual review and feedback from region and country SMEs"],
          ["2.0", "June 2021", "Annual Renewal, FIM changes and TT required updates"],
          ["3.0", "May 2022", "Appendix 3 - Sustainable Trade Instruments added"]
        ],
        "merges": []
      }
    }
  ],
  "excluded_regions": [
    {"page": "*", "bbox": [0, 0, 1224, 120], "why": "页眉"},
    {"page": "*", "bbox": [0, 1500, 1224, 1584], "why": "页脚含页码"}
  ]
}
```

## 字段说明

- `order` — 人读顺序,从 1 起,全文件连续。阅读顺序指标的唯一参照。
- `bbox` — `[x0, y0, x1, y1]`,PDF 点坐标(72dpi),原点左上。
- `type` — `heading | block | table`。数字 anchor 由 `build_anchors.py` 从 `text` / `cells`
  里正则抽取,**不要手工列数字**。
- `merges` — 合并单元格,`[{"r":1,"c":2,"rowspan":2,"colspan":1}]`,无则空数组。
- `excluded_regions` — 页眉页脚等不计入评测的区域,`page:"*"` 表示所有页。
  **这项很关键**:A 走 OCR 会把页码当正文,不排除的话这个真实差异会被当成 GT 噪声。

## 标注建议

- 先跑一遍 `build_anchors.py` 出草稿 JSON,人工在此基础上改,比从零标快得多。
- 表格只标"关键表格"(下游真正要用的),装饰性表格不必标。
- 标完随机抽 5 条回原文核对,再进 STAGE 2。

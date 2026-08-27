# parser-ab-eval 精简执行计划

配套工作区在 `docs/design/parser-ab-eval.zip`,提示词全文在包内的
`PROMPT_FOR_COPILOT.md`。

## 可合并

| 原 | 合并后 | 理由 |
| --- | --- | --- |
| STAGE 1 + 2 | 一轮 | 都是纯数据处理,无外部依赖;STAGE 2 的 both_fail 本身就能暴露 STAGE 1 的 GT 问题 |
| STAGE 3 + 4 | 一轮 | 3 只出图,4 只消费图,失败模式独立 |

4 轮 → 2 轮,验收点从 4 个减到 2 个。

---

## 你做(一次)

```bash
pip install pymupdf python-docx python-pptx rapidfuzz lxml Pillow
soffice --version || python -c "import win32com.client"
cd parser-ab-eval
python tools/render_report.py --demo -o report.PREVIEW.html
```

必须输出 6 cards。

放数据(主干名三处一致):

```
eval/sources/<name>.pdf
eval/out_a/<name>.md
eval/out_b/<name>.md
```

---

## 轮 1 — 给 Copilot

VS Code 打开目录,Agent 模式,贴 `PROMPT_FOR_COPILOT.md` 全文,末尾加:

```text
本轮只做 STAGE 1 和 STAGE 2,不要碰 3 和 4。
完成后一次性跑通两步并打印:
(a) 每文件 anchor 数按 type 分布
(b) bbox_status 的 ok / unresolved 计数
(c) 随机 5 条 anchor 的 gt_text / gt_context
(d) 按 type 的 verdict 分布矩阵
(e) both_fail 的全部条目
```

验收:

- (c) 那 5 条回原文核对 → 错就打回
- (e) 数量 > 总量 10% → GT 有问题,打回

通过后回:`通过,继续 STAGE 3+4`

---

## 轮 2 — 给 Copilot

环境检查两条都失败时,先加一句:

```text
跳过 STAGE 3,STAGE 4 全部用 crop.kind="none"
```

验收:

```bash
git diff --stat templates/ tools/render_report.py   # 必须为空
python tools/build_report.py -o report.html
```

断网双击 `report.html`:

- 图能显示
- 筛选器能点
- L1 数字点两下到证据卡
- 有 A 失败的卡
- 无加权总分

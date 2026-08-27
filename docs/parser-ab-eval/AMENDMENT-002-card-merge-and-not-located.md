# AMENDMENT 002 — 证据卡按 block 合并、定位失败标 not_located

**状态:生效中。本文件优先于 `PROMPT_FOR_COPILOT.md` 中冲突的部分。**

适用:`tools/match.py`(STAGE 2)、`tools/build_report.py`(STAGE 4)

前置:`AMENDMENT-001` 已生效并跑通(blocks=826,anchors=1469,bbox ok=811)。
本文的阈值与卡片数估算全部基于 `prompts/004` 的实测分布,不是拍的。

---

## 实测依据

verdict 分布(1,469 条 anchor):

| type | A | B | tie | both_fail |
| --- | --- | --- | --- | --- |
| heading | 7 | 2 | 25 | 2 |
| number | 290 | 1 | 347 | 5 |
| para | 7 | 4 | 750 | 3 |
| table | 16 | 0 | 3 | 7 |
| 合计 | 320 | 7 | 1,125 | 17 |

`best_context_score` 分布(**仅 number miss 子集**):

| Side | N | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- | --- |
| A | 4 | 99.93 | 99.97 | 100.00 | 100.00 | 100.00 |
| B | 241 | 20.80 | 24.20 | 30.00 | 41.50 | 64.30 |

含 number anchor 的 block:183。

---

## 改动 0(前置)— 统一分数字段

当前代码只在 number **miss** 时写入 `best_context_score`,命中或错误项写的是
`context_score`。两个字段并存会让下面的阈值判断在命中项上读到空值。

改为:**所有 number anchor 一律写 `best_context_score`**,语义统一为
「该 anchor 所属 block 在该侧输出中的最佳定位得分」,与判定结果(hit/miss/wrong)无关。
`context_score` 保留或删除均可,但不要再被下游读取。

这一步先做,否则改动 2 的阈值只对 miss 项生效,命中项会被误判成 `not_located`。

---

## 改动 1 — 证据卡按 block 合并

**判定粒度不变,只改渲染粒度。** recall 等指标仍按 number 逐个统计,数字不变。

`build_report.py` 里,证据卡的单位从 anchor 改成 block:

- 同一 `(file, block_id)` 下的所有 number anchor 合并成一张卡
- 一张卡 = 一个 block:
  - 左栏:该 block 的整体裁剪图(所有成员 anchor 的 bbox 并集,外扩 40px)
  - 中 / 右栏:该 block 在 A / B 输出中的对应片段,片段里把每个 GT 数字
    逐个标 hit / gap / wrong
- verdict 文案改成 `A 4/5 · B 0/5`,fail 取命中数少的一方
- **只在 A、B 命中数不同时才渲染该卡**;相同则计入 `tie_count`
- 卡片标题的 loc 显示 block 范围,不显示单个 anchor id

`block_id` 由 `AMENDMENT-001` 引入,合并直接按该字段分组。

### 卡片数预期

number 类 A/B 不同的 anchor = 290 + 1 + 5 = 296,分布在 183 个含 number 的
block 中的一部分,所以 number 卡 <= 183。

其余类型不参与 block 合并,按原粒度渲染,且同样只渲染 A/B 不同的:
heading 11、para 14、table 23,合计 48。

**总卡片数上界约 231,预期实际在 150 以内**(改前 436)。跑完打印实际值。

---

## 改动 2 — 定位失败标 not_located,阈值 80

`match.py` 里:`best_context_score < 80` 时不返回窗口文本,标记
`status = "not_located"`。

**阈值取 80 的依据**是 B 侧的直方图,不是估计:

```
[10,20)   4
[20,30) 116  ┐
[30,40)  43  │ 定位失败,212 条
[40,50)  49  ┘
[50,60)   4
[60,70)   5  ┐ 谷底,13 条
[70,80)   4  ┘
[80,90)   0  ← 天然空隙,分界线在此
[90,100] 16    真 miss,16 条
```

`[80,90)` 计数为 0,是数据本身给出的分界。A 侧 4 条全部 >= 99.93,阈值 80
不会误伤 A。原先设想的 60 会把 `[60,80)` 那 9 条一并算作已定位,而它们落在谷里,
归属不明确。

`build_report.py` 里 `not_located` 的一侧:

- snippet 显示 `⚠ 未在该侧输出中定位到此区域(best score=39.1)`
- **不显示任何候选文本**

这本身是更强的结论 —— 说明该侧输出里根本没有这段内容,而不是「内容在但数字丢了」。
两者在报告里必须区分开。

---

## 不在本文范围

- **问题 1(bbox 全部 unresolved)已并入 `AMENDMENT-001` 的「前提 2」**,
  且实测有效:unresolved 从全部降到 15 / 826(1.8%)。旧版问题 1 的表述以
  `gt_context` 为输入,已作废,不要再执行。
- 剩余 15 条 unresolved 中 13 条在 `images.pdf`。若该文件是扫描件,
  无文本层则 `page.get_text("words")` 返回空,策略 3 在结构上失效。
  这是已知能力边界,不要为它改匹配逻辑。

---

## 验收

跑完打印:

- 卡片总数(改前 436 / 改后)
- `not_located` 条数,按 A / B 分
- 合并后 `tie_count`
- `git diff --stat templates/ tools/render_report.py` —— **必须为空**

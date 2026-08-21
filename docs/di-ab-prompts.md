# DI vs 基线 md 对照 —— Copilot 提示词

本次 A/B 对照只用这一个文件。判对错的口径在
[benchmark-metrics.md](benchmark-metrics.md),需要时查;其余 docs 属上一阶段
「Azure 各引擎能力评估」,与本次无关。

> 红线:明细表、原文片段、报告含语料,**只能存内网,不要提交进本仓库**。

## 角色分工(先看这张表)

| 档 | 做什么 | 谁做 | Copilot 的角色 |
| --- | --- | --- | --- |
| 一 | md 结构对比(不需原文) | 脚本 | **写脚本** |
| 二 | OOXML 参照(Office 文档) | 脚本 | **写脚本** |
| 三 | 差异裁决(两边不一致处) | Copilot 出草稿 + 人工复核 | **判官**,逐处判,不算比例 |
| 四 | 汇总报告 | Copilot | 只引用前三档算好的数字 |

**不要直接把两份 md 粘给 Copilot 问「哪个更好」。** 它会给你一段很有说服力
但不可复现、无法回指到具体位置的话。第一二档是确定性计算,交给代码;
Copilot 只在第三档做判断,且只判 0/1。

---

## 提示词 1 —— 第一档:md 结构对比脚本

```text
你是 Python 工程师。写一个脚本 compare_md_struct.py,对比两个目录下的
markdown 文件,输出结构指标对照表。

用法:
  python compare_md_struct.py --baseline DIR_A --candidate DIR_B --out OUTDIR

文件配对:按文件名主干(stem)配对。只在一侧存在的文件单独列出,不参与对比。

对每个 md 文件计算以下指标(两侧各算一遍):

结构完整性(越高越好):
- table_count          合法表格块数。定义:连续 >=2 行,首尾为 |,
                       第二行为 |---|---| 形式的分隔行
- table_parseable      各行列数一致、且能被 pandas 读成 DataFrame 的表数
- cell_count           所有表的数据单元格数(数据行数 x 列数)
- number_token_count   正则 [-+(]?\d[\d,]*\.?\d*\)?%? 匹配到的数字个数
- heading_count        ATX 标题(# 开头)总数
- image_ref_count      ![...](...) 的数量
- image_ref_valid      其中 target 为本地路径、文件存在且大小 > 0 的数量
- formula_block_count  $...$ 与 $$...$$ 的数量,分开计
- char_count           去掉 markdown 语法符号后的正文字符数

结构缺陷(越低越好):
- heading_gap_count    层级跳跃次数(如 h1 直接到 h3)
- broken_table_count   列数不一致、或只有表头无数据行的表数
- noise_line_ratio     噪声行数 / 总非空行数。噪声行定义:长度 < 80 字符
                       且在同一文档中出现 >= 3 次的行
- garbled_char_ratio   (U+FFFD + 除 \n \t 外的 C0 控制字符) / 总字符数
- duplicate_para_ratio 重复段落数 / 总段落数。段落归一化后(去空白、
                       转小写)完全相同视为重复,首次出现不计
- token_count          估算 token 数,按 len(text)/4 取整即可

硬约束:
- 只做计算和统计,不做任何优劣判断,不打分,不加权,不输出结论性文字
- 不要把多个指标合成一个总分
- 任何指标算不出来(文件读取失败、无表格等)写 NA,不要写 0
- 只用标准库 + pandas,不要引入其他依赖
- 代码注释用英文

输出两个 CSV:
1. per_doc.csv   一行一个「文档 x 侧」:
   doc_id, side(baseline/candidate), <每个指标一列>
2. summary.csv   一行一个指标:
   metric, baseline_total, candidate_total, delta, n_docs
   delta = candidate_total - baseline_total,原样输出正负,不做解释

先输出完整脚本,再用 5 行说明怎么跑。不要写单元测试。
```

**看结果时注意**:第一档里 `number_token_count`、`cell_count` 这类「越多
越好」的指标,一个啰嗦或重复输出的引擎也能赢。必须同时看
`duplicate_para_ratio` 和第二档的 `hallucinated_number_ratio`,
两者一起才能说明「多出来的是真内容,不是复读或编造」。

---

## 提示词 2 —— 第二档:OOXML 参照脚本(Office 文档)

```text
你是 Python 工程师。写一个脚本 compare_ooxml_ref.py。
原生 Office 文档(docx/pptx/xlsx)的文本与数字在 XML 里是准确的,
直读出来作为参照真值,用它自动评估两份 md 的召回与保真。

用法:
  python compare_ooxml_ref.py --source DIR_SRC --baseline DIR_A \
      --candidate DIR_B --out OUTDIR

参照真值抽取(用 python-docx / python-pptx / openpyxl):
- 正文段落列表(保留顺序)
- 数字 token 列表(含表格内、含 xlsx 单元格的显示值)
- 表格单元格文本列表

数字匹配用 multiset(按出现次数配对),不要用集合去重 ——
原文有 3 个 100、md 只有 1 个,必须算漏了 2 个。

数字比较分两个口径,分别出数,不要合并:
- strict:      逐字符完全一致
- normalized:  去千分位逗号、(123) 视为 -123、去货币符号后再比

对每份 md 计算:
- number_recall            匹配上的数字数 / 参照数字总数            越高越好
- number_fidelity_strict   strict 一致数 / 匹配上的数字数           越高越好
- number_fidelity_norm     normalized 一致数 / 匹配上的数字数       越高越好
- hallucinated_number_ratio  md 有、参照没有的数字数 / md 数字总数  越低越好
- text_recall              参照段落在 md 中能找到的比例。判定:段落归一化后
                           (去空白、去标点、转小写)子串命中即算召回
- cell_recall              参照单元格文本在 md 表格中命中的比例
- para_order_tau           md 中召回段落的顺序 与 参照顺序 的
                           Kendall tau,衡量阅读顺序

硬约束:
- 只输出数字,不做优劣判断,不打分,不加权,不写结论
- 参照抽取失败的文档整篇跳过,记入 skipped.csv 并写明原因,不要用 0 顶替
- 非 Office 文档直接跳过,不报错
- 代码注释用英文

输出:
1. per_doc.csv   doc_id, side, <每个指标一列>
2. summary.csv   metric, baseline, candidate, delta, n_docs
3. skipped.csv   doc_id, reason

先输出完整脚本,再用 5 行说明怎么跑。
```

**这一档最划算**:全自动、样本量能上千、且直接说明正确性而不只是规整度。
Office 占比高的语料,光这几个指标就够出结论。PDF 无此便利,走第三档。

---

## 提示词 3 —— 第三档:差异裁决(一次一个文档)

用前先做两件事:

1. **脚本先 diff**,只把两侧不一致的片段送进来。一致的地方必然平手,
   看了也是浪费。
2. **匿名并随机交换左右**。用 `A` / `B` 代替引擎名,每份文档随机决定
   谁当 A,映射表人工另存。知道哪边是新方案会系统性偏向新方案。

```text
你是文档解析评估员。下面给你三份材料:【原文档内容】、【A 版 markdown 片段】、
【B 版 markdown 片段】。A 与 B 是同一段内容的两种解析结果,已知两者不一致。

你的任务:逐处对照原文,判断哪一侧正确。只输出表格行,不写任何总结。

硬约束:
- 不要输出任何百分比、比例、计数、平均分或排名
- 不要说「A 整体更好」这类整体性判断,只逐处判
- 只依据我给的材料判断。材料不足以判定的,verdict 记 CANT_TELL
- src / out_A / out_B 三列必须逐字引用,可用 … 截断,不许改写、不许补全
- 某侧出现原文没有的内容,该侧 error_type 记 hallucination
- 某侧完全没有对应内容,该侧 error_type 记 missing
- 一处差异同时涉及多个问题(如数字被改写且格式被吃),
  error_type 用 + 连接,如 digit_wrong+format_eaten

verdict 只能取:
  A          A 侧正确,B 侧错
  B          B 侧正确,A 侧错
  BOTH_OK    两侧都对(仅表述不同,如全角/半角、空格差异)
  BOTH_WRONG 两侧都错
  CANT_TELL  材料不足以判定

error_type 只能取:digit_wrong / sign_lost / precision_truncated /
format_eaten / missing / duplicated / truncated / hallucination /
structure_broken / order_wrong / unrenderable / context_lost。
该侧正确时留空。

输出格式(只输出这张表,不要前后文):
| diff_id | doc_id | doc_type | stratum | locator | src | out_A | out_B | verdict | error_type_A | error_type_B |

diff_id 规则:<doc_id>-D<三位序号>,例 D017-D003
locator 填人能定位的坐标,如「表3-第5列」「第12个数字」「第2页第3段」

本次任务参数:
doc_id:<填>  doc_type:<word/ppt/pdf/xlsx>  stratum:<填>
材料范围:<整篇 / 仅第 X-Y 页>

【原文档内容】
<粘贴原文;含图表的必须附截图,否则无法判定>

【A 版 markdown 片段】
<粘贴>

【B 版 markdown 片段】
<粘贴>
```

**人工复核后才算数。** 复核完的表另存 `明细/<doc_id>-diff.md`,记时间戳,
事后不改。`CANT_TELL` 的行不进分子也不进分母,单独统计占比 ——
这个比例偏高说明材料给得不够,不是引擎的问题。

裁决结果按 `verdict` 计数,得到本次对照的核心三个数(以及第四个):

```
候选对、基线错:  c
基线对、候选错:  b   ← 回归清单,必须逐条列出
两边都对:        BOTH_OK
两边都错:        BOTH_WRONG  ← 这个数大,说明「更好但都不能用」
```

---

## 提示词 4 —— 汇总报告

```text
你是文档解析评估员。下面给你三份材料:【第一档 summary.csv】、
【第二档 summary.csv】、【第三档裁决明细表】。它们是唯一事实来源。

硬约束:
- 只允许引用材料里已有的数字。不许自己重算、估算、改动四舍五入
- 不许把多个指标合成总分或做加权排名
- 每条结论后面必须能回指到具体指标名或 diff_id
- 不许出现材料之外的任何结论
- 「越低越好」的指标(noise_line_ratio、garbled_char_ratio、
  duplicate_para_ratio、broken_table_count、hallucinated_number_ratio)
  不要与「越高越好」的指标混在一起平均或排名
- 裁决计数少于 30 处的维度,不许写成百分比,写成「n 处中有 k 处」

【报告骨架】
# DI 解析方案 vs 现有方案 —— md 质量对照报告

## 0. 测评设置
文档数与构成、两侧 md 的生成时间与版本、材料范围、是否匿名裁决、
裁决表冻结时间。

## 1. 结论(半页)
候选是否优于基线、优在哪、代价是什么、是否存在阻断项。

## 2. 第一档:结构对照表
一行一个指标,列 = 基线 / 候选 / delta。分「完整性」「缺陷」两组。
每组下面用两三句说明 delta 的方向意味着什么。

## 3. 第二档:OOXML 参照对照表
同上格式。number_recall 与 hallucinated_number_ratio 必须并排呈现。

## 4. 第三档:差异裁决
4.1 四个计数(候选对/基线对/都对/都错)
4.2 **回归清单** —— 基线对、候选错的每一处,逐条列 diff_id + src +
    候选输出 + error_type。这一节不许省略、不许只给数量
4.3 改进清单 —— 候选对、基线错的处,按 error_type 归类,每类给 1-2 个例子
4.4 两边都错的处,按 error_type 归类。这部分说明「换了方案仍解决不了什么」

## 5. 已知局限
材料范围限制、CANT_TELL 占比、非 Office 文档缺少自动参照、
裁决样本量、评分者与被测模型的同源风险。

【第一档 summary.csv】
<粘贴>

【第二档 summary.csv】
<粘贴>

【第三档裁决明细表】
<粘贴全部复核后的裁决表>
```

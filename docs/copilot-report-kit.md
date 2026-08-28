# Copilot 评估报告套件

一个文件搞定:使用说明 + 两段提示词 + 两个模板。在工作电脑上打开本文件,
按顺序复制粘贴即可。判定口径与指标定义在
[benchmark-metrics.md](benchmark-metrics.md),核对时对照那份。

> 红线:明细表和报告含语料内容,只能存内网,**不要提交进本仓库**。

## 三条不能破的规矩

**1. 尺子不能是被测对象。** Copilot 只出**草稿**,人工逐行核对后才算数。
若对照组里有 VLM 直出泳道,而 Copilot 与其同代同源,该泳道的判定应全部
人工做,并在报告「已知局限」中声明。

**2. 真值先冻结。** 先看模型输出再定真值,测评就废了。核对完的明细表存盘
并记录时间戳,事后不再改动;确需改动的,记录改了什么、为什么。

**3. 评审时隐藏引擎名。** 把各引擎输出打乱、匿名后再核对。知道「这是 Azure
的」会系统性抬高判分。

## 使用说明(四步)

1. **出草稿**:每次取「一个文档 × 一个引擎」,把【提示词 A】+ 原文档 +
   该引擎生成的 md,一起粘给 Copilot → 得到逐 unit 明细表草稿。
2. **人工核对**:逐行核对判定,改错、补 `error_type` 与备注。核对后另存为
   `明细/<引擎>-<doc_id>.md`。**没核对过的表不能进下一步。**
3. **汇总算分**:把全部明细表按 `metric_key` × `engine` × `stratum` 分组,
   `SUM` 出分子分母,用 benchmark-metrics.md 里的 `wilson()` 算区间,
   得到**指标汇总表**。这一步用 Excel 或脚本做,**不要交给模型**。
4. **出报告**:把【提示词 B】+ 指标汇总表 + 全部明细表粘给 Copilot →
   得到最终《评估报告.md》。通读确认每条结论都能回指到 case_id,定稿。

> **材料范围会决定分母。** 若第 1 步只粘了关键页,则 `CMP-01/02/03`
> (段落召回、重复、截断)的分母只覆盖那几页。提示词 A 里的「材料范围」
> 必须如实填写,并在报告的「已知局限」中列出。

## 提示词 A —— 逐 unit 对照(一次一个文档 × 一个引擎)

```text
你是文档解析评估员。下面给你两份材料:【原文档内容】和【某引擎生成的 markdown】。
你的任务:逐 unit 对照,只输出明细表行,不写任何总结。

硬约束:
- 不要输出任何百分比、比例、平均分或汇总统计。只逐 unit 输出行。
- 一个 unit 一行,judgement 只能是 1(对)/ 0(错)/ NA(该引擎无此能力)。
- 只依据我给的材料判断,材料里没有的不许推测。材料不足以判定的,
  judgement 记 0 且 error_type 记 insufficient_material。
- src 和 out 两列必须逐字引用,可用 … 截断,不许改写、不许补全。
- 输出中出现原文没有的内容,judgement 记 0,error_type 记 hallucination。
- 纯文本引擎(如 azure-read)在表格结构 / 公式 / 流程图维度一律记 NA,不记 0。

unit 的切分口径:
- 数字:原文每一个数字 token(含千分位、货币符号、括号负数)为一个 unit
- 表格列名:展平后每一个列名为一个 unit
- 单元格:每一个数据单元格为一个 unit
- 公式:每一个公式为一个 unit,行内与独立用不同 metric_key
- 图片:每一张图为一个 unit;图的描述另记一个 unit
- 流程图:每一个节点为一个 unit;每一条有向边为一个 unit(方向错记 0)
- 段落:每一个原文段落为一个 unit

metric_key 必须取自指标定义表,原样填写:
  NUM-01 数字逐位  NUM-02 负号  NUM-03 精度  NUM-04 金融格式
  TBL-01 表检出  TBL-02 列名  TBL-03 单元格  TBL-04 误合并
  TBL-05 漏合并  TBL-06 表上下文
  FRM-01 独立公式  FRM-02 行内公式  FRM-03 可渲染  FRM-04 等价  FRM-05 编号
  FIG-01 图检出  FIG-02 图文位置  FIG-03 描述幻觉  FIG-04 图内文字  FIG-05 chart 数据
  DIA-01R/P 节点召回/精确  DIA-02R/P 边召回/精确  DIA-03 mermaid 可渲染  DIA-04 分支条件
  ORD-01 段落错位  ORD-02 标题层级  ORD-03 页眉页脚混入
  CMP-01 段落召回  CMP-02 重复  CMP-03 截断

error_type 只能取:digit_wrong / sign_lost / precision_truncated / format_eaten /
missing / duplicated / truncated / hallucination / structure_broken / order_wrong /
unrenderable / context_lost / insufficient_material。judgement 为 1 时留空。

输出格式(只输出这张表,不要前后文):
| case_id | doc_id | doc_type | stratum | engine | metric_key | unit_id | src | out | judgement | error_type | note |

case_id 规则:<engine>-<doc_id>-<metric_key>-<三位序号>
例:layout-D017-NUM-01-003

本次任务参数:
doc_id:<填>   doc_type:<word/ppt/pdf/xlsx>   stratum:<填>   engine:<填>
材料范围:<整篇 / 仅第 X-Y 页>

【原文档内容】
<粘贴原文;含图的必须附截图,否则 FIG-* 无法判定>

【引擎输出的 markdown】
<粘贴该引擎生成的 md>
```

## 提示词 B —— 汇总报告(汇总表算完之后)

```text
你是文档解析评估员。下面给你两份材料:【指标汇总表】和【逐 unit 明细表】。
它们是唯一事实来源。按骨架生成最终评估报告。

硬约束:
- 只允许引用汇总表里已算好的数字。不许自己重算、不许估算、不许改动四舍五入。
- 每条结论后面必须标 (metric_key, 值, 分子/分母, 95%CI) 并至少给一个 case_id。
- 不许出现汇总表和明细表之外的任何结论。
- 达标判定照抄汇总表的 verdict 列,不许自行改判。
- 分母 n < 30 的指标,不许写成百分比,写成「n 例中出现 k 例」并列出 case_id。
- 「越低越好」的指标(TBL-04/05、FIG-03、ORD-01、ORD-03、CMP-02/03)
  不要与准确率类指标混在一起平均或排名。

【报告骨架】
# 文档解析能力评估报告

## 0. 测评设置
语料规模与分层、引擎与版本、材料范围、真值冻结时间、评审是否匿名。

## 1. 结论(一页)
能 quick resolve 的 / 必须自研的 / 各引擎一句话定位。

## 2. 指标总表
行 = metric_key,列 = 引擎,格 = 值 + 95%CI + 达标判定。按维度分组。

## 3. 分维度分析
每维度一节:数字 + 2-3 个并排证据(原文 vs 各引擎输出)。
证据逐字引用,标 case_id。

## 4. 失败模式清单
逐条写:现象 → error_type → 复现 case_id → 疑似原因 → 建议(自研/换引擎/改配置)。
按 error_type 出现频次排序。

## 5. 已知局限
材料范围限制、分母不足(n<30)的指标、评分者与被测模型同源风险、
insufficient_material 占比。

## 6. 附录
指标汇总表全表 + 逐 unit 明细表全表。

【指标汇总表】
<粘贴>

【逐 unit 明细表】
<粘贴全部核对后的明细表>
```

## 明细表模板(空表,人工核对时用)

```markdown
| case_id | doc_id | doc_type | stratum | engine | metric_key | unit_id | src | out | judgement | error_type | note |
| ------- | ------ | -------- | ------- | ------ | ---------- | ------- | --- | --- | --------- | ---------- | ---- |
```

## 汇总表模板

```markdown
| metric_key | metric_name | engine | stratum | k | n | value | ci_low | ci_high | threshold | verdict |
| ---------- | ----------- | ------ | ------- | - | - | ----- | ------ | ------- | --------- | ------- |
```

## 核对时的注意事项

- **NA 不进分母。** 纯文本引擎的表格维度记 NA,不记 0,否则会被系统性低估。
- **一处错误可能命中多个 metric_key。** `1,234.50` → `1234.5` 在
  NUM-01、NUM-03、NUM-04 三行里各记一次 0,这是设计如此,不是重复计数。
- **公式和 mermaid 的可渲染性不要靠肉眼判。** `FRM-03` 用 KaTeX 实际渲染,
  `DIA-03` 用 mermaid 实际渲染,这两项是全套里少数能完全自动化的,
  先把它们自动化掉,省下的人力用在数字和列名上。
- **`ENG-01` 两次运行一致率要单独跑一轮。** 同一份文档跑两次比对输出,
  与内容核对是两件事。生成式引擎必测。

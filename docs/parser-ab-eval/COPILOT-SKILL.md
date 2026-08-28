# Copilot Internal Skill 源定义 — parser-ab-eval

本文件是 skill 的**唯一源**。在公司电脑上把 repo 拉下来后,把最底部
【安装提示词】整段贴给 Copilot(GPT-5.6, Agent 模式),由它按内部 skill
格式落地。skill 内容以本文件为准,安装时不许改写。

---

## Skill 元信息

- **名称**:parser-ab-eval
- **一句话**:对同一批文档的两套 markdown 解析输出做证据级 A/B 评测,
  产出可下钻到证据卡的对照报告
- **触发场景**:需要证明「解析方案 X 比方案 Y 好/差」;引擎选型;
  解析器升级前的回归验证
- **不适用**:单引擎打分(用 benchmark-metrics.md 口径);端到端 RAG 答题评测

## 输入约定

```
eval/sources/<name>.(pdf|docx|pptx|xlsx)   原始文档
eval/gt/<name>.md                          人工复核的 GT(markdown,无坐标)
eval/out_a/<name>.md                       方案 A 输出
eval/out_b/<name>.md                       方案 B 输出
```

主干名三处一致。GT 在看任何输出之前冻结。

## 工作流(四阶段,一轮一验收)

1. **STAGE 1 — anchor 构建**:GT md 切 block(heading/table/para),
   number anchor 归属 block_id;bbox 从 raw 文件转出的 PDF 四级降级反推
   (最长自然语言片段 search_for → 三词短语 → rapidfuzz 滑窗 → unresolved)。
   验收:block 总数、bbox_status 分布,unresolved 应为个位数百分比
2. **STAGE 2 — 判定**:逐 anchor 判 A/B/tie/both_fail;所有 number anchor
   统一写 best_context_score;低于阈值标 not_located(阈值看直方图空隙定,
   不拍脑袋——本轮实测空隙在 [80,90),取 80)
3. **STAGE 3 — 裁剪图**:按 block 粒度(成员 anchor bbox 并集外扩 40px);
   无 Word/PowerPoint 环境时降级 crop.kind="none"
4. **STAGE 4 — 报告**:判定粒度 anchor、渲染粒度 block;只渲染 A/B 命中数
   不同的卡;not_located 一侧显示「未定位到此区域」而非候选文本。
   验收:断网可开、筛选器可用、L1 可下钻、有 A 失败的卡、无加权总分

## 硬规则(违反任何一条 = 本轮作废)

1. 尺子不是被测对象:模型只逐 unit 判 0/1,比例由 SUM 得出,模型不算百分比
2. GT 先冻结,后看输出;改 GT 必须留记录
3. 冻结文件(templates/、render_report.py)一行不许动
4. 阈值必须从实测分布导出,写明依据
5. n < 30 的维度不写百分比,写「n 例中 k 例」并列 case_id
6. 语料、GT、结果只存内网,不进公共仓库
7. 与既定 prompt 冲突的修正走 AMENDMENT-NNN 文件,优先级高于原 prompt
8. 发给模型的每条指令原样归档进 prompts/NNN-<slug>.md,不事后修饰

## 随包引用文件(同目录)

| 文件 | 用途 |
| --- | --- |
| PROMPT_FOR_COPILOT.md | 四阶段的完整执行提示词 |
| AMENDMENT-001 / 002 | 已生效的修正,优先于上者 |
| prompts/ | 指令日志范例(README 含格式约定) |
| ../benchmark-metrics.md | 判对错口径、Wilson 区间、样本量表 |

## 环境前置

- Python 3.10+:`pymupdf python-docx python-pptx rapidfuzz lxml Pillow`
- 裁剪图:Windows + pywin32(Word/PowerPoint 可用)或 soffice;
  都没有则声明降级
- Copilot Agent 模式(GPT-5.x),接受一轮一验收的用法

---

## 【安装提示词】—— 在公司电脑上整段贴给 Copilot

```text
读取仓库中 docs/parser-ab-eval/COPILOT-SKILL.md。把它注册为一个内部
skill/自定义指令,按本环境实际支持的机制落地(prompt file、chatmode、
内部 skill 框架,选其一并说明选了哪种、文件放在哪)。

要求:
- skill 的指令内容 = 该文件「工作流」+「硬规则」+「输入约定」三节,
  原文保留,不许改写、压缩或润色
- 触发描述用「Skill 元信息」一节
- 「随包引用文件」表中的文件作为 skill 的附属资源一并挂上
- 不要执行评测本身,本次只做注册
- 完成后打印:落地格式、生成的文件路径、以及一句如何触发
```

# 评估方案

## 背景与关键技术结论

场景:金融信息科技,语料为受控的内部金融文档(金融表格分析、图表 chart、
公式为主)。目标:判断 Azure 现成能力(纯 LLM 直出、无 pre/post process)
能 quick resolve 哪些问题,哪些必须自研。两类问题:合并表头 → markdown;
流程图 / chart → 有语义的 md。

1. **DI ≠ CU ≠ Vision Read。** Document Intelligence 是确定性版面分析
   (cell 级 JSON,无 LLM);Content Understanding 是 DI + 托管 LLM
   (图表转数据、figure 描述),必须自己接 Foundry 上的 gpt-5.2 + embedding
   部署,双重计费;Vision Read 纯 OCR,直接排除。
2. **原生 Office 的 diagram 不能走 OCR。** DI 对 docx/pptx 不渲染、不返回
   figures,这是设计如此。SmartArt/图表/形状组合在 XML 里本来就有层级、
   缓存数值和连接关系——OOXML 直读是上限,OCR 是下限。
3. **DI 的价值不在识字准确率**(那一项 VLM 更优),而在确定性的
   `rowSpan/columnSpan/kind` 结构和坐标溯源。表头展平算法必须建立在
   可编程结构上,不能建在可能幻觉的 markdown 字符串上。

## 三条泳道

同一批文档跑三条泳道:

- **A = DI + 自研 post-process**(表格基线);
- **B = CU 托管**(验证省下的工程量值不值页费);
- **C = VLM 对照组**(中文场景需纳入中文强的模型)。

另设 **OOXML 直读** 作为原生 Office 文档的上界参考。

## 执行顺序(不可颠倒)

1. 普查分层(`doceval scan` → `files.csv` 的 `stratum` 列);
2. 分层抽样,标注真值并**冻结**;
3. 跑三条泳道;
4. 打分。

先看模型输出再定真值,测评就废了。Copilot 可出真值**草稿**——它的角色是尺子
(标注草稿)不是被量的东西(待测结果),草稿必须人工逐格核对后才能冻结。

## 指标

- TEDS-Struct / TEDS;
- 表头准确率**单列统计**(不混进 TEDS 被正文稀释);
- 跨页合并召回率与误合并率;
- 下游 QA:表格、diagram 各 50 题。

## 通过线

- 表头展平列名准确率 **≥ 95%**;
- 跨页误合并 **≤ 2%**。

## 下一步(阶段二)

- 按 `stratum` 自动分层抽样,导出待标注清单;
- 把表头展平草稿和 mermaid 草稿的提示词固化成脚本(Copilot 出草稿,
  人工逐格核对后冻结为 ground truth);
- 金融语料中公式常见,普查可补充 OMML(`m:oMath`)公式检测信号。

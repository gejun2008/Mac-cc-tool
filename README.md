# doceval — 文档解析评估:语料普查工具

评估 Azure 文档解析能力在两类问题上的边界:

1. **Office 文档表格处理**:合并表头 → markdown(表头展平);
2. **Diagram 语义化**:流程图 / chart → 有语义的 markdown / mermaid。

场景为**gmp**,语料为受控的内部文档,以**表格分析、
图表(chart)、公式**为主。当前阶段(阶段一)交付 `doceval scan`:
纯 stdlib、零第三方依赖、完全确定性的 OOXML 语料普查工具,产出分层抽样依据。

## 安全红线(必读)

- **仓库保持 private**。
- **凭据只进 `.env`**,仓库里只有 `.env.example`。
- **原始文档绝不入库**。语料放内网路径,经 `DOCEVAL_CORPUS_DIR` 引用。
- **Ground truth 与原文同级敏感,同样不入库**。
- 普查产出的 CSV 含语料文件名(可能含业务信息),已被 `.gitignore`
  排除,**不要强行添加**。
- 误提交要**改历史**(如 `git filter-repo`)而非新增删除提交。

## 使用

```bash
uv sync
cp .env.example .env          # 填入内网语料路径
uv run doceval scan "$DOCEVAL_CORPUS_DIR" -o out/inventory
```

无 uv 时可直接用系统 Python(≥3.9,零依赖):

```bash
PYTHONPATH=src python3 -m doceval.cli scan "$DOCEVAL_CORPUS_DIR" -o out/inventory
```

测试(自动生成 OOXML 夹具,不需要任何真实语料):

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 检测依据

| 信号 | 含义 |
| --- | --- |
| `w:gridSpan` | 水平合并;出现在表头区 → 多级表头 |
| `w:vMerge` | 垂直合并 → 行分组 |
| `w:tblHeader` | 表头跨页重复标记 → 跨页表 |
| `a:graphicData/@uri` | 图的真实类型(SmartArt / chart / picture / OLE) |
| `p:cxnSp` + `a:prstGeom flowChart*` | 幻灯片手绘流程图(连接线 + 流程图形状) |

## 输出

`files.csv` — 每文件一行,含各特征计数与:

- **`stratum`**:特征标签的确定性组合(如
  `table_crosspage+table_merged+table_multiheader+diagram_smartart`),
  直接作为分层抽样依据;解析失败的文件记 `unreadable` 并保留错误信息。
- **`native_structure`**:该文件图形对象的原生结构上限——
  `full`(SmartArt/chart,XML 里有完整层级与缓存数值,OOXML 直读是上界)、
  `partial`(形状 + 连接线,几何与连接关系在 XML 里,语义需推断)、
  `none`(纯图片/OLE,只能走 VLM)。
  **这一列决定 diagram 泳道该投多少资源在 OOXML 直读、多少在 VLM。**

`objects.csv` — 每对象一行(表格 / 图形 / 连接线组),含行列数、合并单元格
计数、表头行数、graphicData URI、所在位置(正文 / slideN)。

## 评估方案

三泳道设计、执行顺序、指标与通过线见 [docs/eval-plan.md](docs/eval-plan.md)。

## OCR 对照报告(Copilot 辅助)

在工作电脑上用 Copilot 出对照明细表和最终评估报告:打开
[docs/copilot-report-kit.md](docs/copilot-report-kit.md),按三步走
(提示词 A 出草稿 → 人工逐格核对 → 提示词 B 汇总)。
明细表与报告含语料内容,只存内网,不入库。

## 不支持项修复计划

六项「不支持」问题的分阶段修复计划、优先级原则与决策门见
[docs/fix-plan.md](docs/fix-plan.md)。当前处于阶段 0(底数与开关调研)。

## 约定

Python + uv;代码注释英文,文档中文。

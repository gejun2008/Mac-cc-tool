---
date: 2026-08-27
stage: STAGE 2 + STAGE 3 + STAGE 4
target: tools/match.py, tools/build_report.py
depends: AMENDMENT-002-card-merge-and-not-located.md
---

读 AMENDMENT-002-card-merge-and-not-located.md,按它改 match.py 和 build_report.py。
它优先于 PROMPT_FOR_COPILOT.md 里冲突的部分。

改代码按文件里的顺序做:先改动 0(统一 best_context_score 字段),再改动 1(证据卡
按 block 合并),再改动 2(not_located 阈值 80)。改动 0 不先做,改动 2 会在命中项上
读到空值。

templates/ 和 tools/render_report.py 是冻结文件,一行都不许改。

改完把 STAGE 2、3、4 依次跑通,一次跑完:

- STAGE 2:match.py 改了,results.jsonl 必须重出
- STAGE 3:裁剪图的粒度从 anchor 改成 block(成员 anchor 的 bbox 并集,外扩 40px),
  旧的 anchor 级 crops 全部作废,必须重新生成。pywin32 已装且
  Word.Application / PowerPoint.Application 均可用,正常跑,不要走
  crop.kind="none" 的降级路径
- STAGE 4:build_report.py 出 report.html

跑完打印:
- 卡片总数(改前 436 / 改后)
- not_located 条数,按 A / B 分
- 合并后 tie_count
- 重新生成的 crop 数量
- git diff --stat templates/ tools/render_report.py

---
date: 2026-08-27
stage: STAGE 2
target: 无(只跑,不改代码)
depends: prompts/003-rerun-stage1-with-amendment.md
---

STAGE 1 已按 AMENDMENT-001 重跑完成:blocks=826,bbox ok=811 / unresolved=15,
anchors=1469。旧的 STAGE 2 结果基于旧 anchor,已作废,现在用新 anchors.jsonl 重跑。

本轮不要改任何代码,只跑 STAGE 2 并打印统计。不要碰 STAGE 3 及之后。

跑完打印:

(a) 按 type 的 verdict 分布矩阵
(b) both_fail 的全部条目
(c) best_context_score 的分位数:p10 / p25 / p50 / p75 / p90,A / B 分开统计
(d) best_context_score 的直方图,按 10 分一档,A / B 分开
(e) 若按 block_id 合并同一 block 下的所有 number anchor,
    A、B 命中数不同的 block 有多少个(只统计数量,不要改渲染代码)

(c)(d) 用于确定 not_located 的阈值,(e) 用于估算合并后的卡片数。
这两项只出数,不要据此改任何逻辑。

# AMENDMENT 001 — GT 格式与 bbox 反推

**状态:生效中。本文件优先于 `PROMPT_FOR_COPILOT.md` 中冲突的部分。**

适用:`tools/build_anchors.py`(STAGE 1)

轮 1 跑完后发现两条前提与原 prompt 不符,需先按本文校正,再做 `AMENDMENT-002`
的三个修复。

---

## 前提 1 — GT 是 markdown,不是 JSON,无 bbox

`eval/gt/<name>.md` 是人工复核的 markdown。原 prompt 里 `eval/gt/SCHEMA.md`
描述的 JSON 格式作废。

`build_anchors.py` 改为:

- 解析 GT md,按 block 切分:标题(`#` 开头)、表格(GFM 表)、段落(空行分隔)
- 每个 block 按出现顺序赋 `gt_order`,这就是阅读顺序 GT
- 表格 block 解析成 `cells` 二维数组,这就是表格结构 GT
- 数字 anchor 从 block 文本里正则抽,归属到所属 `block_id`
- `gt_context` 不要用 `" | "` 拼接后截断。表格行取该行所有单元格文本用单空格
  连接的完整串;段落取该数字前后各 40 字符的原始文本

anchor 新增字段:

```json
{
  "block_id": "GOP_R11_v9.3#b007",
  "block_type": "heading | table | para",
  "block_text": "该 block 的完整文本"
}
```

---

## 前提 2 — bbox 只能从 raw file 反推

GT 里没有坐标,bbox 必须靠在 raw file 转出的 PDF 里搜索定位。
这是纯文本坐标计算,不需要图像理解。

在 `build_anchors.py` 里实现四级降级,输入是 `block_text` 而非 `gt_context`:

1. 从 `block_text` 取最长的连续自然语言片段(>=4 个词,不含表格分隔符),
   `page.search_for(片段)`
2. 失败 → 取 `gt_text` 及前后各一个词组成三词短语,`search_for`
3. 失败 → `page.get_text("words")` 拿全页词表(每项含 rect),
   用 rapidfuzz 对 `block_text` 做滑动窗口模糊匹配,
   取最高分窗口内所有 word 的 rect 并集作为 block bbox
4. 仍失败 → `bbox_status = "unresolved"`

策略 3 是主力,应该能兜住绝大多数。跨页的 block 取首页部分即可。

**bbox 存在 block 上,不存在单个 number anchor 上** —— 这与 `AMENDMENT-002`
里的卡片合并改动是一致的。

---

## 验收

跑完打印:

- block 总数
- `bbox_status` 的 ok / unresolved 分布

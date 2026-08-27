#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_report.py — 冻结的渲染层。

职责边界(重要):
  本文件只做「视图模型 dict → HTML 字符串」。
  它不读 anchors.jsonl,不读 markdown,不算任何指标。
  Copilot 的工作是写 tools/build_report.py,把 results.jsonl 转成
  下面 REPORT 视图模型的形状,然后调用 render(REPORT)。

  不要修改本文件的 HTML 结构或 class 名。
  需要新的卡片形态时,新增一个 build_* 函数,不要改已有的。

自检:
  python tools/render_report.py --demo -o report.PREVIEW.html
"""

from __future__ import annotations

import argparse
import base64
import difflib
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SHELL = ROOT / "templates" / "report_shell.html"


# --------------------------------------------------------------------------
# 视图模型 schema(build_report.py 必须产出这个形状)
# --------------------------------------------------------------------------
#
# REPORT = {
#   "meta":  {"title": str, "items": [(label, value), ...]},
#   "modes": [{"loses": "a"|"b", "title": str, "desc": str,
#              "scope": str, "refs": [card_id, ...]}, ...],
#   "scorecard": [{"metric": str, "n": int, "a_win": int, "b_win": int,
#                  "both_fail": int, "note": str, "drill": card_id}, ...],
#   "files": {"cols": [str, ...], "rows": [[cell_html, ...], ...]},
#   "groups": [{"file": str, "tie_count": int, "cards": [CARD, ...]}, ...],
#   "footer": str,
# }
#
# CARD(三栏) = {
#   "id": "c01", "kind": "number"|"table"|"syntax",
#   "fail": "a"|"b"|"both"|"none", "verdict": "A 胜",
#   "loc": "file · p4 · bbox[...]",
#   "crop": {"kind":"img","path":Path} | {"kind":"svg","svg":str}
#           | {"kind":"none","why":str},
#   "crop_cap": str, "gt": str,
#   "a": {"snippet": str_html, "flag": ("ok"|"no"|"mid", str)},
#   "b": {...},
#   "foot": [(text, href), ...], "footnote": str,
# }
#
# CARD(双栏) = {..., "layout":"duo", "legend":[(color_css, label), ...],
#                "a":{"lab":str,"svg":str,"cap":str}, "b":{...}}
# --------------------------------------------------------------------------


def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def word_diff(target: str, candidate: str, focus: str = "") -> str:
    """按词做 diff,输出带 <mark> 的 HTML。

    target    参照文本(GT 或上下文)
    candidate 候选侧输出
    focus     重点 token(如某个数字);命中标 .hit,缺失标 .gap
    """
    tw = re.findall(r"\S+|\s+", target)
    cw = re.findall(r"\S+|\s+", candidate)
    sm = difflib.SequenceMatcher(None, tw, cw, autojunk=False)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(esc("".join(cw[j1:j2])))
        elif tag == "delete":
            seg = "".join(tw[i1:i2])
            if seg.strip():
                out.append(f'<mark class="gap">{esc(seg)}</mark>')
        elif tag == "insert":
            out.append(esc("".join(cw[j1:j2])))
        else:  # replace
            old, new = "".join(tw[i1:i2]), "".join(cw[j1:j2])
            if new.strip():
                out.append(f'<mark class="wrong">{esc(new)}</mark>')
            elif old.strip():
                out.append(f'<mark class="gap">{esc(old)}</mark>')
    s = "".join(out)
    if focus:
        f = esc(focus)
        if f in s and "<mark" not in s:
            s = s.replace(f, f'<mark class="hit">{f}</mark>', 1)
    return s


def snip(inner_html: str) -> str:
    """长片段容器:超高自动折叠,JS 会隐藏不需要的展开按钮。"""
    return (
        '<div class="snip"><pre class="snippet">'
        + inner_html
        + '</pre><div class="fade"></div>'
        + '<button class="more" type="button">展开全部</button></div>'
    )


def _b64_img(path: Path) -> str:
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{data}" alt="原文区域裁剪">'


def _crop(crop: dict, cap: str) -> str:
    k = crop.get("kind")
    if k == "img":
        body = _b64_img(crop["path"])
    elif k == "svg":
        body = crop["svg"]
    else:
        why = esc(crop.get("why", "bbox 未能定位,证据以文本形式给出"))
        return f'<div class="crop unresolved"><div class="why">⚠ {why}</div></div>'
    return f'<div class="crop">{body}<div class="crop-cap">{esc(cap)}</div></div>'


# --------------------------------------------------------------------------
# 片段构造
# --------------------------------------------------------------------------

def build_masthead(meta: dict) -> str:
    items = "".join(
        f"<span><b>{esc(k)}</b> {esc(v)}</span>" for k, v in meta.get("items", [])
    )
    return (
        f'<header class="mast"><h1>{esc(meta.get("title", "解析方案 A/B 对比"))}</h1>'
        f'<div class="runmeta">{items}</div></header>'
    )


def build_modes(modes: list[dict]) -> str:
    if not modes:
        return ""
    cells = []
    for m in modes:
        refs = " ".join(f'<a href="#{esc(r)}">#{esc(r)[1:]}</a>' for r in m.get("refs", []))
        cells.append(
            f'<div class="mode loses-{esc(m["loses"])}"><div class="spine"></div><div>'
            f'<h3>{esc(m["title"])}</h3><p>{esc(m["desc"])}</p>'
            f'<div class="ev">{esc(m.get("scope",""))} · 证据 {refs}</div></div></div>'
        )
    return (
        '<section class="sec"><div class="sec-head"><span class="sec-tag">L0</span>'
        '<h2>失效模式</h2><span class="sub">按现象聚合 · 跨文件</span></div>'
        '<p class="note">选型结论由失效模式决定,不由平均分决定。每条下挂具体证据卡,可直接核验。</p>'
        f'<div class="modes">{"".join(cells)}</div></section>'
    )


def build_scorecard(rows: list[dict]) -> str:
    trs = []
    for r in rows:
        n = max(r["n"], 1)
        pa, pb, pn = r["a_win"] / n * 100, r["b_win"] / n * 100, r["both_fail"] / n * 100
        drill = (
            f'<a class="drill" href="#{esc(r["drill"])}">→ 下钻</a>' if r.get("drill") else ""
        )
        trs.append(
            f"<tr><td>{esc(r['metric'])}</td>"
            f"<td class='num'>{r['n']}</td>"
            f"<td class='num win-a'>{r['a_win']}</td>"
            f"<td class='num win-b'>{r['b_win']}</td>"
            f"<td class='num'>{r['both_fail']}</td>"
            f"<td><div class='bar'><i class='a' style='width:{pa:.0f}%'></i>"
            f"<i class='b' style='width:{pb:.0f}%'></i>"
            f"<i class='n' style='width:{pn:.0f}%'></i></div>"
            f"<div class='barlab'>{esc(r.get('note',''))}</div></td>"
            f"<td>{drill}</td></tr>"
        )
    return (
        '<section class="sec"><div class="sec-head"><span class="sec-tag">L1</span>'
        '<h2>总览记分卡</h2><span class="sub">按实例计,非按文件平均</span></div>'
        '<p class="note">平均分会被文件数量结构带偏。这里统计实例级净胜负:同一 anchor 上 A 对 B 错记 A 独胜。</p>'
        '<table class="grid"><thead><tr>'
        "<th>指标</th><th>实例数</th><th>A 独胜</th><th>B 独胜</th>"
        "<th>共同失败</th><th>分布</th><th>下钻</th>"
        f'</tr></thead><tbody>{"".join(trs)}</tbody></table></section>'
    )


def build_files(files: dict) -> str:
    if not files:
        return ""
    th = "".join(f"<th>{esc(c)}</th>" for c in files["cols"])
    tr = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in files["rows"]
    )
    note = files.get("note", "")
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (
        '<section class="sec"><div class="sec-head"><span class="sec-tag">L2</span>'
        '<h2>逐文件</h2><span class="sub">每格挂实例编号</span></div>'
        f'<table class="grid"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'
        f"{note_html}</section>"
    )


def _pane_side(side: str, c: dict) -> str:
    lvl, txt = c["flag"]
    return (
        f'<div class="pane pane-{side}"><div class="pane-lab"><i class="dot"></i>'
        f'{esc(c.get("lab", "A · Azure Layout OCR" if side == "a" else "B · Local Loader"))}</div>'
        + snip(c["snippet"])
        + f'<div class="flag {esc(lvl)}">{esc(txt)}</div></div>'
    )


def build_card(c: dict) -> str:
    vcls = {"a": "v-a", "b": "v-b", "both": "v-both"}.get(c["fail"], "v-tie")
    head = (
        f'<div class="card-head"><span class="cid">#{esc(c["id"])[1:]}</span>'
        f'<span class="kind">{esc(c.get("kind_label", c["kind"]))}</span>'
        f'<span class="loc">{esc(c["loc"])}</span>'
        f'<span class="verdict">{esc(c["verdict"])}</span></div>'
    )

    if c.get("layout") == "duo":
        legend = "".join(
            f'<span><i style="background:{cc}"></i>{esc(lb)}</span>' for cc, lb in c.get("legend", [])
        )
        legend_html = f'<div class="legend">{legend}</div>' if legend else ""
        def side(s, d):
            return (
                f'<div class="pane pane-{s}"><div class="pane-lab"><i class="dot"></i>'
                f'{esc(d["lab"])}</div><div class="crop">{d["svg"]}'
                f'<div class="crop-cap">{esc(d["cap"])}</div></div></div>'
            )
        panes = f'<div class="panes duo">{side("a", c["a"])}{side("b", c["b"])}</div>'
    else:
        left = (
            '<div class="pane"><div class="pane-lab">原文裁剪</div>'
            + _crop(c["crop"], c.get("crop_cap", ""))
            + (f'<div class="gt"><b>GT:</b> {esc(c["gt"])}</div>' if c.get("gt") else "")
            + "</div>"
        )
        panes = f'<div class="panes">{left}{_pane_side("a", c["a"])}{_pane_side("b", c["b"])}</div>'
        legend_html = ""

    links = "".join(f'<a href="{esc(h)}">{esc(t)}</a>' for t, h in c.get("foot", []))
    foot = (
        f'<div class="card-foot">{links}<span>{esc(c.get("footnote",""))}</span></div>'
    )
    return (
        f'<article class="card {vcls}" id="{esc(c["id"])}" '
        f'data-kind="{esc(c["kind"])}" data-fail="{esc(c["fail"])}">'
        f'<div class="spine"></div><div class="card-body">'
        f"{head}{legend_html}{panes}{foot}</div></article>"
    )


def build_cards(groups: list[dict]) -> str:
    filters = [
        ("all", "全部"), ("number", "数字"), ("table", "表格"),
        ("order", "阅读顺序"), ("syntax", "语法"),
        ("a-fail", "仅 A 失败"), ("b-fail", "仅 B 失败"), ("both-fail", "共同失败"),
    ]
    fb = "".join(
        f'<button data-f="{k}" aria-pressed="{"true" if k=="all" else "false"}">{esc(v)}</button>'
        for k, v in filters
    )
    out = []
    for g in groups:
        cards = "".join(build_card(c) for c in g["cards"])
        tie = (
            f'<div class="tiebox">另有 {g["tie_count"]} 个 anchor 两侧一致(tie),未展开。</div>'
            if g.get("tie_count") else ""
        )
        out.append(
            f'<details class="fgroup" open><summary><b>{esc(g["file"])}</b>'
            f'<span class="cnt">{len(g["cards"])} 张差异卡</span></summary>'
            f"{tie}{cards}</details>"
        )
    return (
        '<section class="sec"><div class="sec-head"><span class="sec-tag">L3</span>'
        '<h2>证据卡</h2><span class="sub">一个 anchor = 一张卡</span></div>'
        f'<div class="filters" role="group" aria-label="按类型筛选证据卡">{fb}</div>'
        f'{"".join(out)}</section>'
    )


def render(report: dict) -> str:
    shell = SHELL.read_text(encoding="utf-8")
    parts = {
        "MASTHEAD": build_masthead(report.get("meta", {})),
        "L0_MODES": build_modes(report.get("modes", [])),
        "L1_SCORECARD": build_scorecard(report.get("scorecard", [])),
        "L2_FILES": build_files(report.get("files", {})),
        "L3_CARDS": build_cards(report.get("groups", [])),
        "FOOTER": f'<footer>{esc(report.get("footer",""))}</footer>',
    }
    for k, v in parts.items():
        shell = shell.replace(f"<!--{{{{{k}}}}}-->", v)
    return shell


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="用内置假数据渲染,验证管线")
    ap.add_argument("-i", "--input", type=Path, help="视图模型 JSON")
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "report.html")
    a = ap.parse_args()

    if a.demo:
        from _demo_data import REPORT  # noqa
    elif a.input:
        REPORT = json.loads(a.input.read_text(encoding="utf-8"))
    else:
        ap.error("需要 --demo 或 -i")

    a.output.write_text(render(REPORT), encoding="utf-8")
    n = sum(len(g["cards"]) for g in REPORT.get("groups", []))
    print(f"wrote {a.output}  ({a.output.stat().st_size/1024:.0f} KB, {n} cards)")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()

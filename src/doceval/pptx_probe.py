"""Probe .pptx files: slide tables, connectors (flowcharts), and graphic kinds.

Detection signals (see README):
  p:cxnSp            -> connector shapes; the fingerprint of hand-drawn flowcharts
  a:prstGeom flowChart* -> flowchart node shapes
  a:tc @gridSpan/@rowSpan/@hMerge/@vMerge -> table cell merges
  a:graphicData/@uri -> true type of embedded graphics (SmartArt/chart/...)
"""

import re
import zipfile

from .ooxml import classify_graphic_uri, load_xml, qn

_SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml")


def probe_pptx(path):
    """Return object records (dicts) for one .pptx, in slide order."""
    objects = []
    with zipfile.ZipFile(path) as zf:
        slides = []
        for name in zf.namelist():
            m = _SLIDE_RE.fullmatch(name)
            if m:
                slides.append((int(m.group(1)), name))
        slides.sort()

        for num, name in slides:
            root = load_xml(zf, name)
            loc = "slide%d" % num

            for idx, tbl in enumerate(root.iter(qn("a", "tbl"))):
                objects.append(_table_record(tbl, loc, idx))

            g_idx = 0
            for gd in root.iter(qn("a", "graphicData")):
                kind = classify_graphic_uri(gd.get("uri", ""))
                if kind == "table_frame":
                    continue
                objects.append(
                    {
                        "object_type": kind,
                        "location": loc,
                        "object_index": g_idx,
                        "graphic_uri": gd.get("uri", ""),
                        "native_structure": _native_structure_for(kind),
                    }
                )
                g_idx += 1

            n_conn = sum(1 for _ in root.iter(qn("p", "cxnSp")))
            n_flow = sum(
                1
                for geom in root.iter(qn("a", "prstGeom"))
                if (geom.get("prst") or "").startswith("flowChart")
            )
            if n_conn or n_flow:
                # Geometry and connection endpoints exist in XML, but the
                # process semantics must still be inferred -> partial.
                objects.append(
                    {
                        "object_type": "connector_group",
                        "location": loc,
                        "object_index": 0,
                        "connectors": n_conn,
                        "flowchart_shapes": n_flow,
                        "native_structure": "partial",
                        "detail": "connectors=%d;flowchart_shapes=%d" % (n_conn, n_flow),
                    }
                )
    return objects


def _table_record(tbl, loc, idx):
    rows = tbl.findall(qn("a", "tr"))
    grid = tbl.find(qn("a", "tblGrid"))
    n_cols = len(grid.findall(qn("a", "gridCol"))) if grid is not None else 0

    tblpr = tbl.find(qn("a", "tblPr"))
    # firstRow marks header styling; PPT has no cross-page repeat concept.
    header_rows = 1 if (tblpr is not None and tblpr.get("firstRow") in ("1", "true")) else 0

    gridspan_cells = 0
    vmerge_cells = 0
    gridspan_in_header = 0
    for r_idx, tr in enumerate(rows):
        for tc in tr.findall(qn("a", "tc")):
            h_merged = int(tc.get("gridSpan", "1")) > 1 or tc.get("hMerge") in ("1", "true")
            v_merged = int(tc.get("rowSpan", "1")) > 1 or tc.get("vMerge") in ("1", "true")
            if h_merged:
                gridspan_cells += 1
                if r_idx == 0:
                    gridspan_in_header += 1
            if v_merged:
                vmerge_cells += 1

    return {
        "object_type": "table",
        "location": loc,
        "object_index": idx,
        "rows": len(rows),
        "cols": n_cols,
        "header_rows": header_rows,
        "gridspan_cells": gridspan_cells,
        "vmerge_cells": vmerge_cells,
        "gridspan_in_header": gridspan_in_header,
    }


def _native_structure_for(kind):
    if kind in ("smartart", "chart"):
        return "full"
    if kind in ("shape", "shape_group"):
        return "partial"
    return "none"

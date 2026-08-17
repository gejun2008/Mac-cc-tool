"""Probe .docx files: table merge structure, header marks, and graphic kinds.

Detection signals (see README):
  w:gridSpan   -> horizontal merge; in header rows it implies a multi-level header
  w:vMerge     -> vertical merge; typically row grouping
  w:tblHeader  -> row repeats on every page; marks tables that cross pages
  a:graphicData/@uri -> the true type of a "figure" (SmartArt/chart/picture/...)
"""

import zipfile

from .ooxml import classify_graphic_uri, flag_on, load_xml, qn


def probe_docx(path):
    """Return object records (dicts) for one .docx, in document order."""
    with zipfile.ZipFile(path) as zf:
        root = load_xml(zf, "word/document.xml")

    objects = []
    for idx, tbl in enumerate(root.iter(qn("w", "tbl"))):
        objects.append(_table_record(tbl, idx))

    g_idx = 0
    for gd in root.iter(qn("a", "graphicData")):
        kind = classify_graphic_uri(gd.get("uri", ""))
        if kind == "table_frame":
            continue
        objects.append(
            {
                "object_type": kind,
                "location": "body",
                "object_index": g_idx,
                "graphic_uri": gd.get("uri", ""),
                "native_structure": _native_structure_for(kind),
            }
        )
        g_idx += 1

    # Legacy VML drawings (w:pict) carry no DrawingML structure at all.
    n_vml = sum(1 for _ in root.iter(qn("w", "pict")))
    if n_vml:
        objects.append(
            {
                "object_type": "picture",
                "location": "body",
                "object_index": g_idx,
                "graphic_uri": "vml",
                "native_structure": "none",
                "detail": "vml_count=%d" % n_vml,
            }
        )
    return objects


def _table_record(tbl, idx):
    rows = tbl.findall(qn("w", "tr"))
    grid = tbl.find(qn("w", "tblGrid"))
    n_cols = len(grid.findall(qn("w", "gridCol"))) if grid is not None else 0

    header_rows = 0
    gridspan_cells = 0
    vmerge_cells = 0
    gridspan_in_header = 0
    for r_idx, tr in enumerate(rows):
        trpr = tr.find(qn("w", "trPr"))
        is_header = trpr is not None and flag_on(
            trpr.find(qn("w", "tblHeader")), qn("w", "val")
        )
        if is_header:
            header_rows += 1
        for tc in tr.findall(qn("w", "tc")):
            tcpr = tc.find(qn("w", "tcPr"))
            if tcpr is None:
                continue
            if tcpr.find(qn("w", "gridSpan")) is not None:
                gridspan_cells += 1
                # Header region = rows marked tblHeader, or the first row when
                # the author never marked headers at all.
                if is_header or r_idx == 0:
                    gridspan_in_header += 1
            if tcpr.find(qn("w", "vMerge")) is not None:
                vmerge_cells += 1

    return {
        "object_type": "table",
        "location": "body",
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
    if kind in ("picture", "embedded"):
        return "none"
    return "none"

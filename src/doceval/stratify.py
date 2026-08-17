"""Aggregate per-object records into one file-level record with a stratum label.

The stratum label is the sampling key for annotation: it is a deterministic,
sorted combination of feature tags so that stratified sampling can be done
directly on the files.csv output.
"""

FILE_COLUMNS = [
    "relpath",
    "format",
    "size_bytes",
    "error",
    "n_tables",
    "n_tables_multiheader",
    "n_tables_merged",
    "n_tables_header_marked",
    "n_smartart",
    "n_charts",
    "n_pictures",
    "n_embedded",
    "n_shapes",
    "n_connectors",
    "n_flowchart_shapes",
    "native_structure",
    "stratum",
]


def aggregate_file(relpath, fmt, size_bytes, objects):
    """Fold object records into the files.csv row for one document."""
    tables = [o for o in objects if o["object_type"] == "table"]

    n_multiheader = sum(
        1 for t in tables if t["gridspan_in_header"] > 0 or t["header_rows"] >= 2
    )
    n_merged = sum(
        1 for t in tables if t["gridspan_cells"] > 0 or t["vmerge_cells"] > 0
    )
    # w:tblHeader repeat-marks exist only in Word; they flag cross-page tables.
    n_header_marked = (
        sum(1 for t in tables if t["header_rows"] > 0) if fmt == "docx" else 0
    )

    n_smartart = _count(objects, "smartart")
    n_charts = _count(objects, "chart")
    n_pictures = _count(objects, "picture")
    n_embedded = _count(objects, "embedded")
    n_shapes = _count(objects, "shape") + _count(objects, "shape_group")
    n_connectors = sum(o.get("connectors", 0) for o in objects)
    n_flowchart = sum(o.get("flowchart_shapes", 0) for o in objects)

    if n_smartart or n_charts:
        native = "full"
    elif n_connectors or n_flowchart or n_shapes:
        native = "partial"
    elif n_pictures or n_embedded:
        native = "none"
    else:
        native = ""

    tags = set()
    if n_multiheader:
        tags.add("table_multiheader")
    if n_merged:
        tags.add("table_merged")
    if n_header_marked:
        tags.add("table_crosspage")
    if tables and not tags:
        tags.add("table_simple")
    if n_smartart:
        tags.add("diagram_smartart")
    if n_charts:
        tags.add("diagram_chart")
    if n_connectors or n_flowchart:
        tags.add("diagram_flowchart")
    has_diagram = n_smartart or n_charts or n_connectors or n_flowchart or n_shapes
    if n_pictures and not has_diagram:
        tags.add("picture_only")

    return {
        "relpath": relpath,
        "format": fmt,
        "size_bytes": size_bytes,
        "error": "",
        "n_tables": len(tables),
        "n_tables_multiheader": n_multiheader,
        "n_tables_merged": n_merged,
        "n_tables_header_marked": n_header_marked,
        "n_smartart": n_smartart,
        "n_charts": n_charts,
        "n_pictures": n_pictures,
        "n_embedded": n_embedded,
        "n_shapes": n_shapes,
        "n_connectors": n_connectors,
        "n_flowchart_shapes": n_flowchart,
        "native_structure": native,
        "stratum": "+".join(sorted(tags)) if tags else "plain",
    }


def error_record(relpath, fmt, size_bytes, exc):
    """files.csv row for a document that could not be parsed."""
    rec = {col: "" for col in FILE_COLUMNS}
    rec.update(
        {
            "relpath": relpath,
            "format": fmt,
            "size_bytes": size_bytes,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "stratum": "unreadable",
        }
    )
    return rec


def _count(objects, kind):
    return sum(1 for o in objects if o["object_type"] == kind)

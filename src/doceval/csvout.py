"""CSV writers with fixed column order for deterministic output."""

import csv
from pathlib import Path

from .stratify import FILE_COLUMNS

OBJECT_COLUMNS = [
    "relpath",
    "location",
    "object_index",
    "object_type",
    "rows",
    "cols",
    "header_rows",
    "gridspan_cells",
    "vmerge_cells",
    "gridspan_in_header",
    "connectors",
    "flowchart_shapes",
    "graphic_uri",
    "native_structure",
    "detail",
]


def write_files_csv(out_dir, records):
    return _write(Path(out_dir) / "files.csv", FILE_COLUMNS, records)


def write_objects_csv(out_dir, records):
    return _write(Path(out_dir) / "objects.csv", OBJECT_COLUMNS, records)


def _write(path, columns, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for rec in records:
            writer.writerow([rec.get(col, "") for col in columns])
    return path

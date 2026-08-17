"""Corpus scan orchestrator: walk a directory, probe each document, write CSVs.

Fully deterministic: sorted directory walk, document-order objects, fixed CSV
columns. Parse failures are recorded per file (stratum=unreadable), never fatal.
"""

import os
from pathlib import Path

from .csvout import write_files_csv, write_objects_csv
from .docx_probe import probe_docx
from .pptx_probe import probe_pptx
from .stratify import aggregate_file, error_record

SUPPORTED = {
    ".docx": "docx",
    ".docm": "docx",
    ".pptx": "pptx",
    ".pptm": "pptx",
}


def scan_corpus(corpus_dir, out_dir):
    """Scan corpus_dir, write files.csv/objects.csv to out_dir, return summary text."""
    corpus_dir = Path(corpus_dir)
    file_records = []
    object_records = []

    for path in iter_documents(corpus_dir):
        rel = path.relative_to(corpus_dir).as_posix()
        fmt = SUPPORTED[path.suffix.lower()]
        size = path.stat().st_size
        try:
            objects = probe_pptx(path) if fmt == "pptx" else probe_docx(path)
        except Exception as exc:
            file_records.append(error_record(rel, fmt, size, exc))
            continue
        file_records.append(aggregate_file(rel, fmt, size, objects))
        for obj in objects:
            obj["relpath"] = rel
            object_records.append(obj)

    files_csv = write_files_csv(out_dir, file_records)
    objects_csv = write_objects_csv(out_dir, object_records)
    return _summary(file_records, files_csv, objects_csv)


def iter_documents(corpus_dir):
    """Yield supported documents under corpus_dir in sorted, stable order."""
    for root, dirs, names in os.walk(corpus_dir):
        # Skip hidden directories; sort in place for a deterministic walk.
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(names):
            # ~$foo.docx are Office lock files, not documents.
            if name.startswith("~$") or name.startswith("."):
                continue
            if Path(name).suffix.lower() in SUPPORTED:
                yield Path(root) / name


def _summary(file_records, files_csv, objects_csv):
    by_stratum = {}
    for rec in file_records:
        by_stratum[rec["stratum"]] = by_stratum.get(rec["stratum"], 0) + 1
    lines = ["scanned %d file(s)" % len(file_records)]
    for stratum in sorted(by_stratum):
        lines.append("  %-60s %d" % (stratum, by_stratum[stratum]))
    lines.append("wrote %s" % files_csv)
    lines.append("wrote %s" % objects_csv)
    return "\n".join(lines)

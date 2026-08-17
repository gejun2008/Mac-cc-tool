"""Command-line entry point: `doceval scan <corpus_dir> [-o outdir]`."""

import argparse
import os
import sys
from pathlib import Path

from .scan import scan_corpus


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="doceval",
        description="Deterministic OOXML corpus probe (docx/pptx), stdlib only.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser(
        "scan", help="Scan a corpus directory and write files.csv / objects.csv"
    )
    p_scan.add_argument(
        "corpus",
        nargs="?",
        default=os.environ.get("DOCEVAL_CORPUS_DIR"),
        help="Corpus root (defaults to $DOCEVAL_CORPUS_DIR)",
    )
    p_scan.add_argument(
        "-o", "--out", default="out/inventory", help="Output directory for CSVs"
    )

    args = parser.parse_args(argv)
    if args.command == "scan":
        if not args.corpus:
            parser.error("no corpus directory given and DOCEVAL_CORPUS_DIR is not set")
        corpus = Path(args.corpus)
        if not corpus.is_dir():
            parser.error("not a directory: %s" % corpus)
        print(scan_corpus(corpus, Path(args.out)))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

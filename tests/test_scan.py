"""End-to-end test: build fixtures, scan them, check every detection signal."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from doceval.scan import scan_corpus  # noqa: E402
from make_fixtures import build_all  # noqa: E402


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class ScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        cls.corpus = tmp / "corpus"
        cls.out = tmp / "out"
        build_all(cls.corpus)
        cls.summary = scan_corpus(cls.corpus, cls.out)
        cls.files = {r["relpath"]: r for r in _read_csv(cls.out / "files.csv")}
        cls.objects = _read_csv(cls.out / "objects.csv")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_all_files_scanned(self):
        self.assertEqual(len(self.files), 2)
        self.assertTrue(all(r["error"] == "" for r in self.files.values()))

    def test_docx_table_signals(self):
        rec = self.files["fixture_tables.docx"]
        self.assertEqual(rec["n_tables"], "1")
        self.assertEqual(rec["n_tables_multiheader"], "1")
        self.assertEqual(rec["n_tables_merged"], "1")
        self.assertEqual(rec["n_tables_header_marked"], "1")
        for tag in ("table_multiheader", "table_merged", "table_crosspage"):
            self.assertIn(tag, rec["stratum"])

    def test_docx_graphics(self):
        rec = self.files["fixture_tables.docx"]
        self.assertEqual(rec["n_smartart"], "1")
        self.assertEqual(rec["n_pictures"], "1")
        self.assertEqual(rec["native_structure"], "full")
        self.assertIn("diagram_smartart", rec["stratum"])

    def test_docx_table_object_detail(self):
        tables = [
            o
            for o in self.objects
            if o["relpath"] == "fixture_tables.docx" and o["object_type"] == "table"
        ]
        self.assertEqual(len(tables), 1)
        t = tables[0]
        self.assertEqual((t["rows"], t["cols"]), ("3", "3"))
        self.assertEqual(t["header_rows"], "2")
        self.assertEqual(t["gridspan_cells"], "1")
        self.assertEqual(t["gridspan_in_header"], "1")
        self.assertEqual(t["vmerge_cells"], "2")

    def test_pptx_flowchart_signals(self):
        rec = self.files["fixture_flowchart.pptx"]
        self.assertEqual(rec["n_connectors"], "1")
        self.assertEqual(rec["n_flowchart_shapes"], "2")
        self.assertIn("diagram_flowchart", rec["stratum"])
        # Drawn shapes without SmartArt/chart => geometry only, semantics inferred.
        self.assertEqual(rec["native_structure"], "partial")

    def test_pptx_table_signals(self):
        rec = self.files["fixture_flowchart.pptx"]
        self.assertEqual(rec["n_tables"], "1")
        self.assertEqual(rec["n_tables_multiheader"], "1")
        self.assertEqual(rec["n_tables_merged"], "1")
        tables = [
            o
            for o in self.objects
            if o["relpath"] == "fixture_flowchart.pptx" and o["object_type"] == "table"
        ]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["gridspan_cells"], "2")
        self.assertEqual(tables[0]["location"], "slide1")

    def test_summary_mentions_strata(self):
        self.assertIn("scanned 2 file(s)", self.summary)


if __name__ == "__main__":
    unittest.main()

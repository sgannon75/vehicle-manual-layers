import importlib.util
import tempfile
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

SCRIPT = Path(__file__).resolve().parents[1] / "skills/vehicle-manual-layers/scripts/extract_manual.py"
spec = importlib.util.spec_from_file_location("extract_manual", SCRIPT)
manual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manual)


class ExtractionTests(unittest.TestCase):
    def test_end_to_end_and_extraction_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pdf, out = root / "manual.pdf", root / "references"
            writer = PdfWriter()
            for _ in range(5):
                page = writer.add_blank_page(width=300, height=300)
                stream = DecodedStreamObject()
                stream.set_data(b"BT (WARNING: Stop.) Tj ET")
                page[NameObject("/Contents")] = writer._add_object(stream)
            writer.write(pdf)
            arguments = [str(SCRIPT), "--pdf", str(pdf), "--out", str(out),
                         "--max-pages", "2", "--edition", "Test", "--market", "US"]
            with patch.object(sys, "argv", arguments):
                manual.main()
            state = json.loads((out / ".vehicle-manual-generated.json").read_text())
            self.assertEqual(state["edition"], "Test")
            self.assertEqual(state["market"], "US")
            self.assertEqual(len(state["sha256"]), 64)
            chapters = [p for p in out.glob("*.md") if p.name != "00-manifest.md"]
            self.assertEqual(len(chapters), 3)
            self.assertEqual(sum(p.read_text(encoding="utf-8").count("<!-- pdf-page") for p in chapters), 5)
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            with patch.object(sys, "argv", arguments), patch.object(manual, "extract_range", side_effect=RuntimeError("failed extraction")):
                with self.assertRaises(RuntimeError):
                    manual.main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})

    def test_coverage_and_limit(self):
        cases = [[], [{"title": "Driving", "page": 3, "children": [
            {"title": "Long subsection", "page": 5, "children": []}]}],
            [{"title": "Later", "page": 100, "children": []},
             {"title": "First", "page": 0, "children": []},
             {"title": "Duplicate", "page": 0, "children": []}]]
        for tops in cases:
            jobs = manual.jobs_from_outline(tops, 250, 30)
            self.assertEqual([p for _, _, s, e in jobs for p in range(s, e)], list(range(250)))
            self.assertTrue(all(e - s <= 30 for _, _, s, e in jobs))

    def test_bad_limit(self):
        with self.assertRaises(ValueError):
            manual.jobs_from_outline([], 5, 0)

    def test_blank_pdf_and_short_warning(self):
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blank.pdf"
            writer.write(path)
            text = manual.extract_range(PdfReader(path), 0, 1)
            self.assertIn("pdf-page 1", text)
            self.assertIn("OCR may be needed", text)
        class Page:
            def extract_text(self):
                return "WARNING: Stop."
        class Reader:
            pages = [Page()]
        self.assertIn("WARNING: Stop.", manual.extract_range(Reader(), 0, 1))

    def test_preserve_notes_and_edited_generated_file(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "notes.md").write_text("mine")
            manual.publish(out, {"01.md": "old"}, {})
            manual.publish(out, {"02.md": "new"}, {})
            self.assertFalse((out / "01.md").exists())
            self.assertEqual((out / "notes.md").read_text(), "mine")
            (out / "02.md").write_text("edited")
            with self.assertRaises(ValueError):
                manual.publish(out, {"02.md": "replacement"}, {})
            self.assertEqual((out / "02.md").read_text(), "edited")

    def test_collision_and_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "01.md").write_text("user data")
            with self.assertRaises(ValueError):
                manual.publish(out, {"01.md": "generated"}, {})
            manual.publish(out, {"02.md": "original"}, {})
            original_replace = manual.os.replace
            calls = 0
            def fail_once(src, dst):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected publication failure")
                return original_replace(src, dst)
            with patch.object(manual.os, "replace", side_effect=fail_once):
                with self.assertRaises(OSError):
                    manual.publish(out, {"02.md": "changed", "03.md": "new"}, {})
            self.assertEqual((out / "02.md").read_text(), "original")
            self.assertFalse((out / "03.md").exists())


if __name__ == "__main__":
    unittest.main()

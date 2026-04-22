"""Whitebox coverage for ``scripts/utilities/pdf_converter.py``.

Trimmed to the key platform-dispatch + output paths: Windows uses docx2pdf,
Linux uses LibreOffice via subprocess, plus image->PDF and PDF-merge.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities import pdf_converter as pc


@pytest.fixture
def conv():
    return pc.PDFConverter()


class TestDocxToPdf:
    def test_windows_branch_invokes_docx2pdf(self, conv):
        conv.system = "Windows"
        fake_docx2pdf = MagicMock()
        with patch.dict(sys.modules, {"docx2pdf": fake_docx2pdf}):
            conv.docx_to_pdf("in.docx", "out.pdf")
        fake_docx2pdf.convert.assert_called_once_with("in.docx", "out.pdf")

    def test_linux_branch_invokes_soffice(self, conv, capsys):
        conv.system = "Linux"
        with patch.object(pc.subprocess, "run") as run:
            conv.docx_to_pdf("in.docx", "/tmp/out")
        run.assert_called_once()
        assert "LibreOffice" in capsys.readouterr().out


class TestImagesToPdf:
    def test_iterates_and_writes(self, conv, tmp_path):
        from PIL import Image
        p1 = tmp_path / "a.png"
        p2 = tmp_path / "b.png"
        Image.new("RGB", (10, 10), "red").save(p1)
        Image.new("RGB", (10, 10), "blue").save(p2)
        out = tmp_path / "out.pdf"

        fake_pdf = MagicMock()
        with patch.object(pc, "FPDF", return_value=fake_pdf):
            conv.images_to_pdf([str(p1), str(p2)], str(out))

        assert fake_pdf.add_page.call_count == 2
        assert fake_pdf.image.call_count == 2
        fake_pdf.output.assert_called_once_with(str(out), "F")


class TestMergePdfs:
    def test_merges_inputs(self, conv, tmp_path):
        merger = MagicMock()
        with patch.object(pc, "PdfMerger", return_value=merger):
            conv.merge_pdfs(["a.pdf", "b.pdf"], str(tmp_path / "out.pdf"))
        assert merger.append.call_count == 2
        merger.write.assert_called_once()
        merger.close.assert_called_once()

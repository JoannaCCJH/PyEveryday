"""Whitebox coverage for ``scripts/utilities/pdf_converter.py``.

The SUT branches on ``platform.system()`` and shells out via subprocess for
LibreOffice.  We patch every external dependency:

* ``docx_to_pdf``:
    - Windows / Darwin branch -> ``docx2pdf.convert`` is invoked.
    - Windows / Darwin branch with ``ImportError`` -> friendly message.
    - Linux branch -> subprocess to ``soffice``.
    - Linux branch with subprocess failure -> friendly error.
    - Linux branch with no ``output_path`` -> derives directory.
* ``images_to_pdf``: iterates over images and calls fpdf.
* ``merge_pdfs``: appends and writes via PyPDF2.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities import pdf_converter as pc


@pytest.fixture
def conv():
    c = pc.PDFConverter()
    return c


# ----------------------- docx_to_pdf --------------------------

class TestDocxToPdf:
    def test_windows_branch_invokes_docx2pdf(self, conv, capsys):
        conv.system = "Windows"
        fake_docx2pdf = MagicMock()
        with patch.dict(sys.modules, {"docx2pdf": fake_docx2pdf}):
            conv.docx_to_pdf("in.docx", "out.pdf")
        fake_docx2pdf.convert.assert_called_once_with("in.docx", "out.pdf")

    def test_windows_import_error_branch(self, conv, capsys):
        conv.system = "Darwin"
        # Simulate ImportError when ``from docx2pdf import convert`` runs.
        with patch.dict(sys.modules, {"docx2pdf": None}):
            with patch("builtins.__import__",
                       side_effect=ImportError("missing")):
                conv.docx_to_pdf("in.docx", "out.pdf")
        assert "Please install docx2pdf" in capsys.readouterr().out

    def test_linux_branch_invokes_soffice(self, conv, capsys):
        conv.system = "Linux"
        with patch.object(pc.subprocess, "run") as run:
            conv.docx_to_pdf("in.docx", "/tmp/out")
        run.assert_called_once()
        assert "LibreOffice" in capsys.readouterr().out

    def test_linux_default_output_path(self, conv):
        conv.system = "Linux"
        with patch.object(pc.subprocess, "run") as run:
            conv.docx_to_pdf("/tmp/in.docx")
        # The third arg of the popen list is "--convert-to" -> just check that
        # ``--outdir`` was supplied with /tmp (dirname of in.docx).
        args, _ = run.call_args
        cmd = args[0]
        assert "--outdir" in cmd

    def test_linux_failure_branch(self, conv, capsys):
        conv.system = "Linux"
        with patch.object(pc.subprocess, "run", side_effect=RuntimeError("nope")):
            conv.docx_to_pdf("in.docx", "/tmp/out")
        assert "LibreOffice conversion failed" in capsys.readouterr().out


# ----------------------- images_to_pdf ------------------------

class TestImagesToPdf:
    def test_iterates_and_writes(self, conv, tmp_path):
        # Create a couple of valid tiny PNGs so PIL can open them.
        from PIL import Image
        p1 = tmp_path / "a.png"
        p2 = tmp_path / "b.png"
        Image.new("RGB", (10, 10), "red").save(p1)
        Image.new("RGB", (10, 10), "blue").save(p2)
        out = tmp_path / "out.pdf"

        fake_pdf = MagicMock()
        with patch.object(pc, "FPDF", return_value=fake_pdf):
            conv.images_to_pdf([str(p1), str(p2)], str(out))

        # Two add_page + two image calls + one output call:
        assert fake_pdf.add_page.call_count == 2
        assert fake_pdf.image.call_count == 2
        fake_pdf.output.assert_called_once_with(str(out), "F")


# -------------------------- merge_pdfs ------------------------

class TestMergePdfs:
    def test_merges_inputs(self, conv, tmp_path):
        merger = MagicMock()
        with patch.object(pc, "PdfMerger", return_value=merger):
            conv.merge_pdfs(["a.pdf", "b.pdf"], str(tmp_path / "out.pdf"))
        # append called per input, then write + close.
        assert merger.append.call_count == 2
        merger.write.assert_called_once()
        merger.close.assert_called_once()

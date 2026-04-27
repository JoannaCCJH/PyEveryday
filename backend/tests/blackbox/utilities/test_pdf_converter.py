from unittest.mock import MagicMock, patch

import pytest

from PIL import Image

from PyPDF2 import PdfReader, PdfWriter

from scripts.utilities.pdf_converter import PDFConverter

pytestmark = pytest.mark.blackbox


# Provides the conv fixture.
@pytest.fixture
def conv():
    return PDFConverter()


# Defines the make_png helper.
def _make_png(path, size=(10, 10), color=(255, 0, 0)):
    Image.new("RGB", size, color).save(path)
    return path


# Defines the make_pdf helper.
def _make_pdf(path, text=b"%PDF-1.4\n% a minimal pdf\n"):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(path, "wb") as f:
        writer.write(f)
    return path


class TestImagesToPdfEP:
    # Tests single image produces pdf.
    def test_single_image_produces_pdf(self, conv, tmp_path):
        img = _make_png(tmp_path / "a.png")
        out = tmp_path / "out.pdf"
        conv.images_to_pdf([str(img)], str(out))
        assert out.exists()
        assert len(PdfReader(str(out)).pages) == 1

    # Tests multiple images produce multi page pdf.
    def test_multiple_images_produce_multi_page_pdf(self, conv, tmp_path):
        imgs = [str(_make_png(tmp_path / f"{i}.png")) for i in range(3)]
        out = tmp_path / "out.pdf"
        conv.images_to_pdf(imgs, str(out))
        assert len(PdfReader(str(out)).pages) == 3


class TestMergePdfsEP:
    # Tests merge two pdfs.
    def test_merge_two_pdfs(self, conv, tmp_path):
        p1 = _make_pdf(tmp_path / "a.pdf")
        p2 = _make_pdf(tmp_path / "b.pdf")
        out = tmp_path / "merged.pdf"
        conv.merge_pdfs([str(p1), str(p2)], str(out))
        assert len(PdfReader(str(out)).pages) == 2

    # Tests merge single pdf.
    def test_merge_single_pdf(self, conv, tmp_path):
        p1 = _make_pdf(tmp_path / "only.pdf")
        out = tmp_path / "merged.pdf"
        conv.merge_pdfs([str(p1)], str(out))
        assert len(PdfReader(str(out)).pages) == 1


class TestDocxToPdfEP:
    # Tests windows darwin uses docx2pdf.
    def test_windows_darwin_uses_docx2pdf(self, conv, tmp_path, monkeypatch):
        monkeypatch.setattr(conv, "system", "Darwin")
        fake_convert = MagicMock()
        fake_mod = MagicMock(convert=fake_convert)
        with patch.dict("sys.modules", {"docx2pdf": fake_mod}):
            conv.docx_to_pdf("in.docx", str(tmp_path / "out.pdf"))
        fake_convert.assert_called_once_with("in.docx", str(tmp_path / "out.pdf"))

    # Tests linux uses soffice subprocess.
    def test_linux_uses_soffice_subprocess(self, conv, tmp_path, monkeypatch):
        monkeypatch.setattr(conv, "system", "Linux")
        with patch("scripts.utilities.pdf_converter.subprocess.run") as mock_run:
            conv.docx_to_pdf("in.docx", str(tmp_path))
        assert mock_run.called
        args = mock_run.call_args.args[0]
        assert "soffice" in args
        assert "--convert-to" in args
        assert "pdf" in args


class TestBoundaries:
    # Tests images to pdf empty list produces empty pdf.
    def test_images_to_pdf_empty_list_produces_empty_pdf(self, conv, tmp_path):
        out = tmp_path / "empty.pdf"
        conv.images_to_pdf([], str(out))
        assert out.exists()

    # Tests merge three pdfs.
    def test_merge_three_pdfs(self, conv, tmp_path):
        pdfs = [str(_make_pdf(tmp_path / f"{i}.pdf")) for i in range(3)]
        out = tmp_path / "out.pdf"
        conv.merge_pdfs(pdfs, str(out))
        assert len(PdfReader(str(out)).pages) == 3


class TestErrorGuessing:
    # Tests docx to pdf missing docx2pdf package prints install hint.
    def test_docx_to_pdf_missing_docx2pdf_package_prints_install_hint(self, conv, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(conv, "system", "Windows")

        # Defines the fake_import helper.
        def fake_import(name, *args, **kwargs):
            if name == "docx2pdf":
                raise ImportError("no module")
            return __import__(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=fake_import):
            conv.docx_to_pdf("in.docx")
        assert "pip install docx2pdf" in capsys.readouterr().out

    # Tests docx to pdf linux subprocess error is caught.
    def test_docx_to_pdf_linux_subprocess_error_is_caught(self, conv, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(conv, "system", "Linux")
        with patch(
            "scripts.utilities.pdf_converter.subprocess.run",
            side_effect=RuntimeError("soffice missing"),
        ):
            conv.docx_to_pdf("in.docx", str(tmp_path))
        assert "LibreOffice conversion failed" in capsys.readouterr().out

    # Tests platform initialization.
    def test_platform_initialization(self):
        with patch("scripts.utilities.pdf_converter.platform.system", return_value="FakeOS"):
            c = PDFConverter()
        assert c.system == "FakeOS"

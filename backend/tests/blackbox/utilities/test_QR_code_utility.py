from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities.QR_code_utility import QR_Toolkit

pytestmark = pytest.mark.blackbox


# Provides the qr fixture.
@pytest.fixture
def qr():
    return QR_Toolkit()


class TestGenerateQrEP:
    # Tests generate qr writes file to default name.
    def test_generate_qr_writes_file_to_default_name(self, qr, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        qr.generate_qr("https://example.com")
        assert (tmp_path / "QR_code.png").exists()

    # Tests generate qr custom filename.
    def test_generate_qr_custom_filename(self, qr, tmp_path):
        out = tmp_path / "my_qr.png"
        qr.generate_qr("hello", filename=str(out))
        assert out.exists()

    # Tests generate qr swallows library errors.
    def test_generate_qr_swallows_library_errors(self, qr, tmp_path, capsys):
        with patch("scripts.utilities.QR_code_utility.qr.make", side_effect=RuntimeError("bad")):
            qr.generate_qr("x", filename=str(tmp_path / "out.png"))
        out = capsys.readouterr().out
        assert "Error generating QR code" in out


class TestScanQrEP:
    # Tests scan nonexistent file prints and returns none.
    def test_scan_nonexistent_file_prints_and_returns_none(self, qr, tmp_path, capsys):
        result = qr.scan_qr(str(tmp_path / "nope.png"))
        assert result is None
        assert "does not exist" in capsys.readouterr().out

    # Tests scan returns decoded data on success.
    def test_scan_returns_decoded_data_on_success(self, qr, tmp_path, monkeypatch):
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")
        fake_cv2 = MagicMock()
        fake_cv2.imread.return_value = MagicMock()
        detector = MagicMock()
        detector.detectAndDecode.return_value = ("hello world", [[0]], None)
        fake_cv2.QRCodeDetector.return_value = detector
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)
        assert qr.scan_qr(str(img_path)) == "hello world"

    # Tests scan unreadable image prints and returns none.
    def test_scan_unreadable_image_prints_and_returns_none(self, qr, tmp_path, monkeypatch, capsys):
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")
        fake_cv2 = MagicMock()
        fake_cv2.imread.return_value = None
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)
        result = qr.scan_qr(str(img_path))
        assert result is None
        assert "Could not read image" in capsys.readouterr().out

    # Tests scan no qr in image.
    def test_scan_no_qr_in_image(self, qr, tmp_path, monkeypatch, capsys):
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")
        fake_cv2 = MagicMock()
        fake_cv2.imread.return_value = MagicMock()
        detector = MagicMock()
        detector.detectAndDecode.return_value = ("", None, None)
        fake_cv2.QRCodeDetector.return_value = detector
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)
        assert qr.scan_qr(str(img_path)) is None
        assert "No QR code found" in capsys.readouterr().out


class TestBoundaries:
    # Tests generate qr empty string still creates file.
    def test_generate_qr_empty_string_still_creates_file(self, qr, tmp_path):
        out = tmp_path / "empty.png"
        qr.generate_qr("", filename=str(out))
        assert out.exists()

    # Tests generate qr very long input.
    def test_generate_qr_very_long_input(self, qr, tmp_path):
        out = tmp_path / "long.png"
        qr.generate_qr("a" * 2000, filename=str(out))
        assert out.exists()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestScanQrBA:
    def test_scan_with_points_none_treats_as_no_qr(self, qr, tmp_path, monkeypatch, capsys):
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")

        fake_cv2 = MagicMock()
        fake_cv2.imread.return_value = MagicMock()
        detector = MagicMock()
        detector.detectAndDecode.return_value = ("ghost data", None, None)
        fake_cv2.QRCodeDetector.return_value = detector
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)

        assert qr.scan_qr(str(img_path)) is None
        assert "No QR code found" in capsys.readouterr().out


class TestErrorGuessing:
    # Tests scan exception in cv2 is swallowed.
    def test_scan_exception_in_cv2_is_swallowed(self, qr, tmp_path, monkeypatch, capsys):
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")
        fake_cv2 = MagicMock()
        fake_cv2.imread.side_effect = RuntimeError("boom")
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)
        qr.scan_qr(str(img_path))
        assert "Failed to scan" in capsys.readouterr().out

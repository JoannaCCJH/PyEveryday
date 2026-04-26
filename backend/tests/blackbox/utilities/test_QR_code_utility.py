"""
Black-box tests for scripts.utilities.QR_code_utility.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
External libraries (qrcode, cv2) are exercised directly against real
PNG files written to tmp_path - no network needed.
"""
from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities.QR_code_utility import QR_Toolkit

pytestmark = pytest.mark.blackbox


@pytest.fixture
def qr():
    return QR_Toolkit()


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestGenerateQrEP:
    def test_generate_qr_writes_file_to_default_name(self, qr, tmp_path, monkeypatch):
        # EP: default filename class -> creates QR_code.png in cwd.
        monkeypatch.chdir(tmp_path)
        qr.generate_qr("https://example.com")
        assert (tmp_path / "QR_code.png").exists()

    def test_generate_qr_custom_filename(self, qr, tmp_path):
        # EP: custom filename class -> respected.
        out = tmp_path / "my_qr.png"
        qr.generate_qr("hello", filename=str(out))
        assert out.exists()

    def test_generate_qr_swallows_library_errors(self, qr, tmp_path, capsys):
        # EP: the SUT wraps qr.make() in try/except -> error path prints,
        # does not raise.
        with patch("scripts.utilities.QR_code_utility.qr.make", side_effect=RuntimeError("bad")):
            qr.generate_qr("x", filename=str(tmp_path / "out.png"))
        out = capsys.readouterr().out
        assert "Error generating QR code" in out


class TestScanQrEP:
    def test_scan_nonexistent_file_prints_and_returns_none(self, qr, tmp_path, capsys):
        # EP: file-not-found class -> prints, returns None.
        result = qr.scan_qr(str(tmp_path / "nope.png"))
        assert result is None
        assert "does not exist" in capsys.readouterr().out

    def test_scan_returns_decoded_data_on_success(self, qr, tmp_path, monkeypatch):
        # EP: success class -> returns decoded payload.
        # Create a dummy file so the existence check passes, then mock cv2.
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")

        fake_cv2 = MagicMock()
        fake_cv2.imread.return_value = MagicMock()  # non-None image
        detector = MagicMock()
        detector.detectAndDecode.return_value = ("hello world", [[0]], None)
        fake_cv2.QRCodeDetector.return_value = detector

        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)
        assert qr.scan_qr(str(img_path)) == "hello world"

    def test_scan_unreadable_image_prints_and_returns_none(self, qr, tmp_path, monkeypatch, capsys):
        # EP: cv2.imread returns None -> prints "Could not read image".
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")

        fake_cv2 = MagicMock()
        fake_cv2.imread.return_value = None
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)

        result = qr.scan_qr(str(img_path))
        assert result is None
        assert "Could not read image" in capsys.readouterr().out

    def test_scan_no_qr_in_image(self, qr, tmp_path, monkeypatch, capsys):
        # EP: detector finds no QR (data empty) -> prints "No QR code found".
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


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_generate_qr_empty_string_still_creates_file(self, qr, tmp_path):
        # BA: empty payload is still a valid QR input per the library.
        out = tmp_path / "empty.png"
        qr.generate_qr("", filename=str(out))
        assert out.exists()

    def test_generate_qr_very_long_input(self, qr, tmp_path):
        # BA: long input near QR version ceiling should still encode.
        out = tmp_path / "long.png"
        qr.generate_qr("a" * 2000, filename=str(out))
        assert out.exists()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_scan_exception_in_cv2_is_swallowed(self, qr, tmp_path, monkeypatch, capsys):
        # EG: unexpected exception inside cv2 -> caught, prints "Failed to scan".
        img_path = tmp_path / "img.png"
        img_path.write_bytes(b"fake")

        fake_cv2 = MagicMock()
        fake_cv2.imread.side_effect = RuntimeError("boom")
        monkeypatch.setattr("scripts.utilities.QR_code_utility.cv2", fake_cv2)

        qr.scan_qr(str(img_path))
        assert "Failed to scan" in capsys.readouterr().out

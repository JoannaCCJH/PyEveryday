"""Targeted whitebox coverage for ``scripts/utilities/QR_code_utility.py``.

Slim — direct tests for ``generate_qr`` and ``scan_qr`` so the method
bodies are covered (CLI tests run with no real input image).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities import QR_code_utility as qrutil


@pytest.fixture
def tool():
    return qrutil.QR_Toolkit()


class TestGenerateQr:
    def test_success_calls_save(self, tool, tmp_path):
        fake_img = MagicMock()
        with patch.object(qrutil, "qr") as q:
            q.make.return_value = fake_img
            tool.generate_qr("https://example.com", filename=str(tmp_path / "x.png"))
        q.make.assert_called_once_with("https://example.com")
        fake_img.save.assert_called_once()


class TestScanQr:
    def test_decoded_branch(self, tool, tmp_path, capsys):
        p = tmp_path / "x.png"
        p.write_bytes(b"\x00")
        detector = MagicMock()
        detector.detectAndDecode.return_value = ("payload", "points", None)
        with patch.object(qrutil, "cv2") as cv:
            cv.imread.return_value = "img"
            cv.QRCodeDetector.return_value = detector
            out = tool.scan_qr(str(p))
        assert out == "payload"
        assert "Decoded QR Data: payload" in capsys.readouterr().out

    def test_missing_file_short_circuits(self, tool, tmp_path, capsys):
        out = tool.scan_qr(str(tmp_path / "missing.png"))
        assert out is None
        assert "File does not exist" in capsys.readouterr().out

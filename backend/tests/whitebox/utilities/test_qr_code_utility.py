"""Whitebox coverage for ``scripts/utilities/QR_code_utility.py``.

We mock the third-party libraries (``qrcode`` and ``cv2``) so the SUT's own
control flow is what we measure.

Branches exercised in ``QR_Toolkit``:

* ``generate_qr``: success and exception arms.
* ``scan_qr``: missing file early return; ``cv2.imread`` returns ``None``;
  detector finds data; detector returns blank; exception arm.
* Module-level ``print_usage`` smoke.
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

    def test_failure_branch(self, tool, capsys):
        with patch.object(qrutil, "qr") as q:
            q.make.side_effect = RuntimeError("boom")
            tool.generate_qr("anything")
        assert "Error generating QR code" in capsys.readouterr().out


class TestScanQr:
    def test_missing_file_short_circuits(self, tool, tmp_path, capsys):
        out = tool.scan_qr(str(tmp_path / "missing.png"))
        assert out is None
        assert "File does not exist" in capsys.readouterr().out

    def test_unreadable_image_branch(self, tool, tmp_path, capsys):
        p = tmp_path / "x.png"
        p.write_bytes(b"\x00")
        with patch.object(qrutil, "cv2") as cv:
            cv.imread.return_value = None
            out = tool.scan_qr(str(p))
        assert out is None
        assert "Could not read image" in capsys.readouterr().out

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

    def test_no_qr_branch(self, tool, tmp_path, capsys):
        p = tmp_path / "x.png"
        p.write_bytes(b"\x00")
        detector = MagicMock()
        detector.detectAndDecode.return_value = ("", None, None)
        with patch.object(qrutil, "cv2") as cv:
            cv.imread.return_value = "img"
            cv.QRCodeDetector.return_value = detector
            out = tool.scan_qr(str(p))
        assert out is None
        assert "No QR code found" in capsys.readouterr().out

    def test_exception_branch(self, tool, tmp_path, capsys):
        p = tmp_path / "x.png"
        p.write_bytes(b"\x00")
        with patch.object(qrutil, "cv2") as cv:
            cv.imread.side_effect = RuntimeError("bad")
            tool.scan_qr(str(p))
        assert "Failed to scan QR code" in capsys.readouterr().out


class TestPrintUsage:
    def test_prints_usage(self, capsys):
        qrutil.print_usage()
        out = capsys.readouterr().out
        assert "Usage" in out and "Commands" in out

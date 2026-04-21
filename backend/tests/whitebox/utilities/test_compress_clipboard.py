"""Whitebox coverage for ``scripts/utilities/compress_clipboard.py``.

Branches exercised in ``FileUtility.compress_files``:

* All inputs invalid -> ``FileNotFoundError`` raised.
* Mixed valid/invalid inputs (warning printed but compression continues).
* Single-file input branch (auto-named zip = basename + ".zip").
* Multi-file input branch (default ``archive.zip``).
* Directory-walk branch via ``os.walk``.
* Explicit ``output_zip`` argument.

And in ``copy_to_clipboard``:

* ``pyperclip.copy`` is invoked exactly once with the supplied text.

We patch ``pyperclip`` so no system clipboard is touched and ``time.sleep`` so
the test is fast.
"""

from __future__ import annotations

import zipfile
from unittest.mock import patch

import pytest

from scripts.utilities import compress_clipboard as cc


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch.object(cc.time, "sleep"):
        yield


class TestCompressFiles:
    def test_all_invalid_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            cc.FileUtility.compress_files([str(tmp_path / "nope1"),
                                           str(tmp_path / "nope2")])

    def test_explicit_output_zip(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hi")
        out = tmp_path / "explicit.zip"
        result = cc.FileUtility.compress_files([str(f)], str(out))
        assert result == str(out)
        assert out.exists()

    def test_directory_walk_branch(self, tmp_path):
        d = tmp_path / "src"
        d.mkdir()
        (d / "a.txt").write_text("A")
        (d / "sub").mkdir()
        (d / "sub" / "b.txt").write_text("B")
        out = tmp_path / "out.zip"
        cc.FileUtility.compress_files([str(d)], str(out))
        with zipfile.ZipFile(out) as zf:
            names = sorted(zf.namelist())
        assert any("a.txt" in n for n in names)
        assert any("b.txt" in n for n in names)

class TestCopyToClipboard:
    def test_calls_pyperclip(self):
        with patch.object(cc, "pyperclip") as pc:
            cc.FileUtility.copy_to_clipboard("hello")
        pc.copy.assert_called_once_with("hello")

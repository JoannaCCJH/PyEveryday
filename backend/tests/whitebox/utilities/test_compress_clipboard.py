from __future__ import annotations

import zipfile

from unittest.mock import patch

import pytest

from scripts.utilities import compress_clipboard as cc


# Provides the no_sleep fixture.
@pytest.fixture(autouse=True)
def _no_sleep():
    with patch.object(cc.time, "sleep"):
        yield


class TestCompressFiles:
    # Tests all invalid raises.
    def test_all_invalid_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            cc.FileUtility.compress_files([str(tmp_path / "nope1"),
                                           str(tmp_path / "nope2")])

    # Tests explicit output zip with file.
    def test_explicit_output_zip_with_file(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("hi")
        out = tmp_path / "explicit.zip"
        result = cc.FileUtility.compress_files([str(f)], str(out))
        assert result == str(out)
        assert out.exists()

    # Tests directory walk branch.
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

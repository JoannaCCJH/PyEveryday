"""
Black-box tests for scripts.utilities.compress_clipboard.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
pyperclip is mocked so the test runner doesn't touch the real clipboard.
"""
import os
import zipfile
from unittest.mock import patch

import pytest

from scripts.utilities.compress_clipboard import FileUtility

pytestmark = pytest.mark.blackbox


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestCompressFilesEP:
    def test_single_file_creates_named_zip(self, tmp_path, monkeypatch):
        # EP: single valid file class -> output zip named "<stem>.zip".
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "notes.txt"
        f.write_text("hello")
        out = FileUtility.compress_files([str(f)])
        assert out == "notes.zip"
        assert (tmp_path / "notes.zip").exists()

    def test_multiple_files_default_archive_zip_name(self, tmp_path, monkeypatch):
        # EP: multiple valid files -> default "archive.zip".
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        out = FileUtility.compress_files([str(tmp_path / "a.txt"), str(tmp_path / "b.txt")])
        assert out == "archive.zip"
        assert (tmp_path / "archive.zip").exists()

    def test_explicit_output_name_is_used(self, tmp_path, monkeypatch):
        # EP: explicit output name class -> honored exactly.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("a")
        out = FileUtility.compress_files([str(tmp_path / "a.txt")], output_zip="custom.zip")
        assert out == "custom.zip"
        assert (tmp_path / "custom.zip").exists()

    def test_no_valid_paths_raises(self, tmp_path):
        # EP: all invalid paths class -> FileNotFoundError.
        with pytest.raises(FileNotFoundError):
            FileUtility.compress_files(
                [str(tmp_path / "nope1"), str(tmp_path / "nope2")]
            )

    def test_zip_contains_expected_entries(self, tmp_path, monkeypatch):
        # EP: archive content class - confirms the zip actually contains the
        # input files by their basenames.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("A")
        (tmp_path / "b.txt").write_text("B")
        out = FileUtility.compress_files([str(tmp_path / "a.txt"), str(tmp_path / "b.txt")])
        with zipfile.ZipFile(tmp_path / out) as zf:
            assert set(zf.namelist()) == {"a.txt", "b.txt"}


class TestCompressDirectoryEP:
    def test_directory_walked_recursively(self, tmp_path, monkeypatch):
        # EP: directory input class -> walks files recursively.
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "src"
        d.mkdir()
        (d / "a.txt").write_text("a")
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("b")

        out = FileUtility.compress_files([str(d)], output_zip="x.zip")
        with zipfile.ZipFile(tmp_path / out) as zf:
            names = set(zf.namelist())
        assert any("a.txt" in n for n in names)
        assert any("b.txt" in n for n in names)


class TestCopyToClipboardEP:
    def test_copy_passes_text_to_pyperclip(self):
        # EP: text is forwarded verbatim to pyperclip.copy.
        with patch("scripts.utilities.compress_clipboard.pyperclip") as mock_clip:
            FileUtility.copy_to_clipboard("hello")
        mock_clip.copy.assert_called_once_with("hello")


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_single_empty_file_compresses(self, tmp_path, monkeypatch):
        # BA: zero-byte file still compresses.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "empty.txt").write_bytes(b"")
        out = FileUtility.compress_files([str(tmp_path / "empty.txt")])
        with zipfile.ZipFile(tmp_path / out) as zf:
            info = zf.getinfo("empty.txt")
            assert info.file_size == 0

    def test_mix_of_valid_and_invalid_paths_compresses_valid_only(self, tmp_path, monkeypatch, capsys):
        # BA: partial-valid class - warning printed for invalid, zip built.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "ok.txt").write_text("x")
        out = FileUtility.compress_files(
            [str(tmp_path / "ok.txt"), str(tmp_path / "nope.txt")]
        )
        captured = capsys.readouterr().out
        assert "Path not found" in captured
        assert (tmp_path / out).exists()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_copy_empty_string(self):
        # EG: empty string is still forwarded (not short-circuited).
        with patch("scripts.utilities.compress_clipboard.pyperclip") as mock_clip:
            FileUtility.copy_to_clipboard("")
        mock_clip.copy.assert_called_once_with("")

    def test_output_zip_overwrites_existing(self, tmp_path, monkeypatch):
        # EG: pre-existing zip at the target path is overwritten (zipfile 'w').
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("new")
        target = tmp_path / "x.zip"
        target.write_bytes(b"leftover")
        FileUtility.compress_files([str(tmp_path / "a.txt")], output_zip=str(target))
        with zipfile.ZipFile(target) as zf:
            assert "a.txt" in zf.namelist()

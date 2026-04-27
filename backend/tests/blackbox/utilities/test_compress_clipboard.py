import os

import zipfile

from unittest.mock import patch

import pytest

from scripts.utilities.compress_clipboard import FileUtility

pytestmark = pytest.mark.blackbox


class TestCompressFilesEP:
    # Tests single file creates named zip.
    def test_single_file_creates_named_zip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "notes.txt"
        f.write_text("hello")
        out = FileUtility.compress_files([str(f)])
        assert out == "notes.zip"
        assert (tmp_path / "notes.zip").exists()

    # Tests multiple files default archive zip name.
    def test_multiple_files_default_archive_zip_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        out = FileUtility.compress_files([str(tmp_path / "a.txt"), str(tmp_path / "b.txt")])
        assert out == "archive.zip"
        assert (tmp_path / "archive.zip").exists()

    # Tests explicit output name is used.
    def test_explicit_output_name_is_used(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("a")
        out = FileUtility.compress_files([str(tmp_path / "a.txt")], output_zip="custom.zip")
        assert out == "custom.zip"
        assert (tmp_path / "custom.zip").exists()

    # Tests no valid paths raises.
    def test_no_valid_paths_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FileUtility.compress_files(
                [str(tmp_path / "nope1"), str(tmp_path / "nope2")]
            )

    # Tests zip contains expected entries.
    def test_zip_contains_expected_entries(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("A")
        (tmp_path / "b.txt").write_text("B")
        out = FileUtility.compress_files([str(tmp_path / "a.txt"), str(tmp_path / "b.txt")])
        with zipfile.ZipFile(tmp_path / out) as zf:
            assert set(zf.namelist()) == {"a.txt", "b.txt"}


class TestCompressDirectoryEP:
    # Tests directory walked recursively.
    def test_directory_walked_recursively(self, tmp_path, monkeypatch):
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
    # Tests copy passes text to pyperclip.
    def test_copy_passes_text_to_pyperclip(self):
        with patch("scripts.utilities.compress_clipboard.pyperclip") as mock_clip:
            FileUtility.copy_to_clipboard("hello")
        mock_clip.copy.assert_called_once_with("hello")


class TestBoundaries:
    # Tests single empty file compresses.
    def test_single_empty_file_compresses(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "empty.txt").write_bytes(b"")
        out = FileUtility.compress_files([str(tmp_path / "empty.txt")])
        with zipfile.ZipFile(tmp_path / out) as zf:
            info = zf.getinfo("empty.txt")
            assert info.file_size == 0

    # Tests mix of valid and invalid paths compresses valid only.
    def test_mix_of_valid_and_invalid_paths_compresses_valid_only(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "ok.txt").write_text("x")
        out = FileUtility.compress_files(
            [str(tmp_path / "ok.txt"), str(tmp_path / "nope.txt")]
        )
        captured = capsys.readouterr().out
        assert "Path not found" in captured
        assert (tmp_path / out).exists()


class TestErrorGuessing:
    # Tests copy empty string.
    def test_copy_empty_string(self):
        with patch("scripts.utilities.compress_clipboard.pyperclip") as mock_clip:
            FileUtility.copy_to_clipboard("")
        mock_clip.copy.assert_called_once_with("")

    # Tests output zip overwrites existing.
    def test_output_zip_overwrites_existing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.txt").write_text("new")
        target = tmp_path / "x.zip"
        target.write_bytes(b"leftover")
        FileUtility.compress_files([str(tmp_path / "a.txt")], output_zip=str(target))
        with zipfile.ZipFile(target) as zf:
            assert "a.txt" in zf.namelist()

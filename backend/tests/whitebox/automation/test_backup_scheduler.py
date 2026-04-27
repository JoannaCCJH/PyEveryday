from __future__ import annotations

import os

import time

import zipfile

from unittest.mock import patch

import pytest

from scripts.automation import backup_scheduler as bs


# Defines the mkfile helper.
def _mkfile(path, content="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestBackupDirectory:
    # Tests missing source.
    def test_missing_source(self, tmp_path, capsys):
        result = bs.backup_directory(str(tmp_path / "nope"), str(tmp_path / "out"))
        assert result is False
        assert "does not exist" in capsys.readouterr().out

    # Tests creates backup dir and copies.
    def test_creates_backup_dir_and_copies(self, tmp_path):
        src = tmp_path / "src"
        _mkfile(src / "f.txt", "hello")
        dest = tmp_path / "backups"
        assert bs.backup_directory(str(src), str(dest)) is True
        copied = next(dest.rglob("f.txt"))
        assert copied.read_text() == "hello"


class TestBackupAndCompress:
    # Tests zip contains walked files.
    def test_zip_contains_walked_files(self, tmp_path):
        src = tmp_path / "src"
        _mkfile(src / "a.txt", "A")
        _mkfile(src / "sub" / "b.txt", "B")
        dest = tmp_path / "backups"
        assert bs.backup_and_compress(str(src), str(dest)) is True
        zips = list(dest.glob("*.zip"))
        assert len(zips) == 1
        with zipfile.ZipFile(zips[0]) as zf:
            names = sorted(zf.namelist())
        assert "a.txt" in names
        assert any(n.endswith("b.txt") for n in names)


class TestCleanupOldBackups:
    # Tests keeps recent removes old file.
    def test_keeps_recent_removes_old_file(self, tmp_path):
        d = tmp_path / "backups"
        d.mkdir()
        recent = d / "recent.zip"
        recent.write_text("r")
        old = d / "old.zip"
        old.write_text("o")
        ancient = time.time() - (30 * 24 * 60 * 60)
        os.utime(old, (ancient, ancient))
        bs.cleanup_old_backups(str(d), days_to_keep=7)
        assert recent.exists()
        assert not old.exists()

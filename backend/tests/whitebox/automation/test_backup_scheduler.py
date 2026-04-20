"""Whitebox coverage for ``scripts/automation/backup_scheduler.py``.

The module mixes filesystem ops with the ``schedule`` library and an infinite
``while True`` loop in CLI mode.  We test every branch of the four pure
functions and avoid the CLI loop entirely by importing only the functions.

Targeted branches:

* ``backup_directory``: missing source, success, ``copytree`` exception.
* ``backup_and_compress``: missing source, success, ``ZipFile`` exception.
* ``cleanup_old_backups``: missing dir; recent file kept; old file (dir vs
  regular) removed; remove exception.
* ``scheduled_backup``: ``compress=True`` and ``compress=False`` branches and
  the cleanup-skip-on-failure branch.
"""

from __future__ import annotations

import os
import shutil
import time
import zipfile
from unittest.mock import patch

import pytest

from scripts.automation import backup_scheduler as bs


def _mkfile(path, content="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestBackupDirectory:
    def test_missing_source(self, tmp_path, capsys):
        result = bs.backup_directory(str(tmp_path / "nope"), str(tmp_path / "out"))
        assert result is False
        assert "does not exist" in capsys.readouterr().out

    def test_creates_backup_dir_and_copies(self, tmp_path):
        src = tmp_path / "src"
        _mkfile(src / "f.txt", "hello")
        dest = tmp_path / "backups"

        assert bs.backup_directory(str(src), str(dest)) is True

        # exactly one backup directory was created under dest
        children = list(dest.iterdir())
        assert len(children) == 1
        copied = next(children[0].rglob("f.txt"))
        assert copied.read_text() == "hello"

    def test_copytree_failure(self, tmp_path):
        src = tmp_path / "src"
        _mkfile(src / "f.txt")
        dest = tmp_path / "backups"

        with patch.object(bs.shutil, "copytree", side_effect=OSError("boom")):
            assert bs.backup_directory(str(src), str(dest)) is False


class TestBackupAndCompress:
    def test_missing_source(self, tmp_path, capsys):
        result = bs.backup_and_compress(str(tmp_path / "nope"), str(tmp_path / "out"))
        assert result is False
        assert "does not exist" in capsys.readouterr().out

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
        # arcname is computed relative to source
        assert "a.txt" in names
        assert any(n.endswith("b.txt") for n in names)

    def test_zip_failure_branch(self, tmp_path):
        src = tmp_path / "src"
        _mkfile(src / "a.txt")
        dest = tmp_path / "backups"

        with patch.object(bs.zipfile, "ZipFile", side_effect=OSError("disk full")):
            assert bs.backup_and_compress(str(src), str(dest)) is False


class TestCleanupOldBackups:
    def test_missing_dir_is_noop(self, tmp_path):
        bs.cleanup_old_backups(str(tmp_path / "nope"))  # must not raise

    def test_keeps_recent_removes_old_file(self, tmp_path):
        d = tmp_path / "backups"
        d.mkdir()
        recent = d / "recent.zip"
        recent.write_text("r")
        old = d / "old.zip"
        old.write_text("o")
        # Force `old` to be older than the cutoff:
        ancient = time.time() - (30 * 24 * 60 * 60)
        os.utime(old, (ancient, ancient))

        bs.cleanup_old_backups(str(d), days_to_keep=7)

        assert recent.exists()
        assert not old.exists()

    def test_removes_old_directory_branch(self, tmp_path):
        d = tmp_path / "backups"
        d.mkdir()
        old_dir = d / "old_backup"
        old_dir.mkdir()
        (old_dir / "x.txt").write_text("x")
        ancient = time.time() - (30 * 24 * 60 * 60)
        os.utime(old_dir, (ancient, ancient))

        bs.cleanup_old_backups(str(d), days_to_keep=7)
        assert not old_dir.exists()

    def test_remove_failure_is_caught(self, tmp_path, capsys):
        d = tmp_path / "backups"
        d.mkdir()
        f = d / "old.zip"
        f.write_text("o")
        ancient = time.time() - (30 * 24 * 60 * 60)
        os.utime(f, (ancient, ancient))

        with patch.object(bs.os, "remove", side_effect=PermissionError("no")):
            bs.cleanup_old_backups(str(d), days_to_keep=7)

        assert "Error removing" in capsys.readouterr().out


class TestScheduledBackup:
    def test_compress_true_calls_compress_then_cleanup(self, tmp_path):
        with patch.object(bs, "backup_and_compress", return_value=True) as mb, \
             patch.object(bs, "backup_directory") as md, \
             patch.object(bs, "cleanup_old_backups") as mc:
            bs.scheduled_backup("src", "dst", compress=True)
        mb.assert_called_once_with("src", "dst")
        md.assert_not_called()
        mc.assert_called_once_with("dst")

    def test_compress_false_calls_directory_then_cleanup(self, tmp_path):
        with patch.object(bs, "backup_directory", return_value=True) as md, \
             patch.object(bs, "backup_and_compress") as mb, \
             patch.object(bs, "cleanup_old_backups") as mc:
            bs.scheduled_backup("src", "dst", compress=False)
        md.assert_called_once_with("src", "dst")
        mb.assert_not_called()
        mc.assert_called_once_with("dst")

    def test_failure_skips_cleanup(self, tmp_path):
        with patch.object(bs, "backup_and_compress", return_value=False), \
             patch.object(bs, "cleanup_old_backups") as mc:
            bs.scheduled_backup("src", "dst", compress=True)
        mc.assert_not_called()

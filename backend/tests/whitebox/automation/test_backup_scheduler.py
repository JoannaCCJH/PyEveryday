"""Whitebox coverage for ``scripts/automation/backup_scheduler.py``.

Tightened to the essential branches:

* ``backup_directory``: missing source, success.
* ``backup_and_compress``: zip is built from walked files.
* ``cleanup_old_backups``: recent kept / old removed, and remove-exception arm.
* ``scheduled_backup``: compress=True wiring.
"""

from __future__ import annotations

import os
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
        children = list(dest.iterdir())
        assert len(children) == 1
        copied = next(children[0].rglob("f.txt"))
        assert copied.read_text() == "hello"


class TestBackupAndCompress:
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
    def test_compress_true_calls_compress_then_cleanup(self):
        with patch.object(bs, "backup_and_compress", return_value=True) as mb, \
             patch.object(bs, "backup_directory") as md, \
             patch.object(bs, "cleanup_old_backups") as mc:
            bs.scheduled_backup("src", "dst", compress=True)
        mb.assert_called_once_with("src", "dst")
        md.assert_not_called()
        mc.assert_called_once_with("dst")

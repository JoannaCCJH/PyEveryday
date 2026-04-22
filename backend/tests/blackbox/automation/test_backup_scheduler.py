"""
Black-box tests for scripts.automation.backup_scheduler.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
Uses tmp_path for real filesystem isolation. The `schedule` library is
only used in __main__ - no scheduling is exercised here.
"""
import os
import time
import zipfile

import pytest

from scripts.automation.backup_scheduler import (
    backup_and_compress,
    backup_directory,
    cleanup_old_backups,
)

pytestmark = pytest.mark.blackbox


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestBackupDirectoryEP:
    def test_source_missing_returns_false(self, tmp_path, capsys):
        # EP: invalid-source class -> False, prints error.
        result = backup_directory(str(tmp_path / "nope"), str(tmp_path / "bk"))
        assert result is False
        assert "does not exist" in capsys.readouterr().out

    def test_successful_backup_copies_tree(self, tmp_path):
        # EP: valid source class -> True, directory copied.
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bk = tmp_path / "bk"
        assert backup_directory(str(src), str(bk)) is True
        # Exactly one backup_* subfolder should exist under bk.
        dirs = list(bk.iterdir())
        assert len(dirs) == 1
        assert dirs[0].name.startswith("backup_")
        assert (dirs[0] / "a.txt").read_text() == "hello"

    def test_backup_dir_created_if_missing(self, tmp_path):
        # EP: backup dir does not pre-exist -> created by backup_directory.
        src = tmp_path / "src"
        src.mkdir()
        (src / "x.txt").write_text("x")
        bk = tmp_path / "new_bk"
        assert not bk.exists()
        backup_directory(str(src), str(bk))
        assert bk.exists()


class TestBackupAndCompressEP:
    def test_successful_compression_creates_zip(self, tmp_path):
        # EP: valid source -> .zip created.
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bk = tmp_path / "bk"
        assert backup_and_compress(str(src), str(bk)) is True
        zips = list(bk.glob("backup_*.zip"))
        assert len(zips) == 1
        with zipfile.ZipFile(zips[0]) as zf:
            assert "a.txt" in zf.namelist()

    def test_missing_source_returns_false(self, tmp_path, capsys):
        # EP: invalid-source class -> False.
        assert backup_and_compress(str(tmp_path / "nope"), str(tmp_path / "bk")) is False
        assert "does not exist" in capsys.readouterr().out


class TestCleanupEP:
    def test_old_backups_removed(self, tmp_path):
        # EP: old-file class -> removed.
        bk = tmp_path / "bk"
        bk.mkdir()
        old = bk / "backup_old"
        old.mkdir()
        (old / "f.txt").write_text("x")
        # Force mtime to 30 days ago.
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        os.utime(old, (thirty_days_ago, thirty_days_ago))

        cleanup_old_backups(str(bk), days_to_keep=7)
        assert not old.exists()

    def test_recent_backups_preserved(self, tmp_path):
        # EP: recent-file class -> preserved.
        bk = tmp_path / "bk"
        bk.mkdir()
        fresh = bk / "backup_fresh"
        fresh.mkdir()
        cleanup_old_backups(str(bk), days_to_keep=7)
        assert fresh.exists()

    def test_nonexistent_backup_dir_is_silent(self, tmp_path):
        # EP: missing-dir class -> no-op, no raise.
        cleanup_old_backups(str(tmp_path / "nope"))  # must not raise


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_cleanup_just_inside_cutoff_preserves(self, tmp_path):
        # BA: file mtime slightly newer than cutoff -> preserved.
        bk = tmp_path / "bk"
        bk.mkdir()
        item = bk / "backup_boundary"
        item.mkdir()
        # Set mtime 10s newer than the 1-day cutoff.
        new_time = time.time() - (1 * 24 * 60 * 60) + 10
        os.utime(item, (new_time, new_time))
        cleanup_old_backups(str(bk), days_to_keep=1)
        assert item.exists()

    def test_empty_source_backup_is_empty_zip(self, tmp_path):
        # BA: empty source directory -> empty zip.
        src = tmp_path / "empty"
        src.mkdir()
        bk = tmp_path / "bk"
        assert backup_and_compress(str(src), str(bk)) is True
        zips = list(bk.glob("*.zip"))
        with zipfile.ZipFile(zips[0]) as zf:
            assert zf.namelist() == []


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_backup_directory_collision_returns_false(self, tmp_path, monkeypatch):
        # EG: shutil.copytree raises when destination exists; caught -> False.
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("x")
        bk = tmp_path / "bk"
        # Pre-create the destination the SUT is about to generate by fixing
        # the timestamp.
        import scripts.automation.backup_scheduler as bs_module

        class _FixedDateTime:
            @classmethod
            def now(cls):
                class _T:
                    @staticmethod
                    def strftime(fmt):
                        return "fixed"
                return _T()

        monkeypatch.setattr(bs_module.datetime, "datetime", _FixedDateTime)
        bk.mkdir()
        (bk / "backup_fixed").mkdir()  # collision target exists
        result = backup_directory(str(src), str(bk))
        assert result is False

    def test_backup_preserves_nested_structure(self, tmp_path):
        # EG: nested dirs replicated by copytree.
        src = tmp_path / "src"
        sub = src / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "deep.txt").write_text("deep")
        bk = tmp_path / "bk"
        backup_directory(str(src), str(bk))
        dirs = list(bk.iterdir())
        assert (dirs[0] / "a" / "b" / "deep.txt").read_text() == "deep"

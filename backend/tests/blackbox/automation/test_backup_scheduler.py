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


class TestBackupDirectoryEP:
    # Tests source missing returns false.
    def test_source_missing_returns_false(self, tmp_path, capsys):
        result = backup_directory(str(tmp_path / "nope"), str(tmp_path / "bk"))
        assert result is False
        assert "does not exist" in capsys.readouterr().out

    # Tests successful backup copies tree.
    def test_successful_backup_copies_tree(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bk = tmp_path / "bk"
        assert backup_directory(str(src), str(bk)) is True
        dirs = list(bk.iterdir())
        assert len(dirs) == 1
        assert dirs[0].name.startswith("backup_")
        assert (dirs[0] / "a.txt").read_text() == "hello"

    # Tests backup dir created if missing.
    def test_backup_dir_created_if_missing(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "x.txt").write_text("x")
        bk = tmp_path / "new_bk"
        assert not bk.exists()
        backup_directory(str(src), str(bk))
        assert bk.exists()


class TestBackupAndCompressEP:
    # Tests successful compression creates zip.
    def test_successful_compression_creates_zip(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        bk = tmp_path / "bk"
        assert backup_and_compress(str(src), str(bk)) is True
        zips = list(bk.glob("backup_*.zip"))
        assert len(zips) == 1
        with zipfile.ZipFile(zips[0]) as zf:
            assert "a.txt" in zf.namelist()

    # Tests missing source returns false.
    def test_missing_source_returns_false(self, tmp_path, capsys):
        assert backup_and_compress(str(tmp_path / "nope"), str(tmp_path / "bk")) is False
        assert "does not exist" in capsys.readouterr().out


class TestCleanupEP:
    # Tests old backups removed.
    def test_old_backups_removed(self, tmp_path):
        bk = tmp_path / "bk"
        bk.mkdir()
        old = bk / "backup_old"
        old.mkdir()
        (old / "f.txt").write_text("x")
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        os.utime(old, (thirty_days_ago, thirty_days_ago))
        cleanup_old_backups(str(bk), days_to_keep=7)
        assert not old.exists()

    # Tests recent backups preserved.
    def test_recent_backups_preserved(self, tmp_path):
        bk = tmp_path / "bk"
        bk.mkdir()
        fresh = bk / "backup_fresh"
        fresh.mkdir()
        cleanup_old_backups(str(bk), days_to_keep=7)
        assert fresh.exists()

    # Tests nonexistent backup dir is silent.
    def test_nonexistent_backup_dir_is_silent(self, tmp_path):
        cleanup_old_backups(str(tmp_path / "nope"))


class TestBoundaries:
    # Tests cleanup just inside cutoff preserves.
    def test_cleanup_just_inside_cutoff_preserves(self, tmp_path):
        bk = tmp_path / "bk"
        bk.mkdir()
        item = bk / "backup_boundary"
        item.mkdir()
        new_time = time.time() - (1 * 24 * 60 * 60) + 10
        os.utime(item, (new_time, new_time))
        cleanup_old_backups(str(bk), days_to_keep=1)
        assert item.exists()

    # Tests empty source backup is empty zip.
    def test_empty_source_backup_is_empty_zip(self, tmp_path):
        src = tmp_path / "empty"
        src.mkdir()
        bk = tmp_path / "bk"
        assert backup_and_compress(str(src), str(bk)) is True
        zips = list(bk.glob("*.zip"))
        with zipfile.ZipFile(zips[0]) as zf:
            assert zf.namelist() == []


class TestErrorGuessing:
    # Tests backup directory collision returns false.
    def test_backup_directory_collision_returns_false(self, tmp_path, monkeypatch):
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("x")
        bk = tmp_path / "bk"

        import scripts.automation.backup_scheduler as bs_module

        class _FixedDateTime:
            # Defines the now helper.
            @classmethod
            def now(cls):
                class _T:
                    # Defines the strftime helper.
                    @staticmethod
                    def strftime(fmt):
                        return "fixed"
                return _T()
        monkeypatch.setattr(bs_module.datetime, "datetime", _FixedDateTime)
        bk.mkdir()
        (bk / "backup_fixed").mkdir()
        result = backup_directory(str(src), str(bk))
        assert result is False

    # Tests backup preserves nested structure.
    def test_backup_preserves_nested_structure(self, tmp_path):
        src = tmp_path / "src"
        sub = src / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "deep.txt").write_text("deep")
        bk = tmp_path / "bk"
        backup_directory(str(src), str(bk))
        dirs = list(bk.iterdir())
        assert (dirs[0] / "a" / "b" / "deep.txt").read_text() == "deep"

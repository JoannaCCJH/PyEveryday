"""Whitebox coverage for ``scripts/automation/file_organizer.py``.

We exercise both organize-by-extension and organize-by-date functions across
every internal branch:

    * missing directory short-circuit.
    * file with no extension (``no_extension`` bucket).
    * file with extension (typical happy path).
    * subdirectory items (skipped because not ``isfile``).
    * ``shutil.move`` raises (exception branch).

For ``organize_files_by_date`` we mock ``os.stat`` to return a deterministic
``st_ctime`` so the date bucket is stable.
"""

from __future__ import annotations

import datetime as _dt
import os
from unittest.mock import patch

import pytest

from scripts.automation import file_organizer


def _stat_with_ctime(ctime: float):
    """Return an ``os.stat`` replacement that keeps the real ``st_mode`` etc.

    The SUT calls ``os.path.isfile`` (which itself calls ``os.stat`` and reads
    ``st_mode``) *before* it reads ``st_ctime``.  If we return a bare
    ``SimpleNamespace(st_ctime=...)``, ``os.path.isfile`` blows up.  Instead we
    delegate to the real ``os.stat`` and only override ``st_ctime`` via a
    lightweight proxy.
    """
    real_stat = os.stat

    class _StatProxy:
        def __init__(self, real):
            self._real = real
            self.st_ctime = ctime

        def __getattr__(self, name):
            return getattr(self._real, name)

    def _fake(path, *a, **kw):
        return _StatProxy(real_stat(path, *a, **kw))

    return _fake


class TestOrganizeByExtension:
    def test_missing_directory(self, tmp_path, capsys):
        file_organizer.organize_files_by_extension(str(tmp_path / "missing"))
        assert "does not exist" in capsys.readouterr().out

    def test_files_with_and_without_extension(self, tmp_path):
        (tmp_path / "a.TXT").write_text("1")  # uppercase => still goes to 'txt'
        (tmp_path / "README").write_text("2")  # no extension
        (tmp_path / "sub").mkdir()  # directory should be skipped

        file_organizer.organize_files_by_extension(str(tmp_path))

        assert (tmp_path / "txt" / "a.TXT").exists()
        assert (tmp_path / "no_extension" / "README").exists()
        # original directory untouched (was not a file)
        assert (tmp_path / "sub").is_dir()

    def test_move_failure_is_logged(self, tmp_path, capsys):
        (tmp_path / "x.dat").write_text("1")

        with patch("scripts.automation.file_organizer.shutil.move",
                   side_effect=PermissionError("locked")):
            file_organizer.organize_files_by_extension(str(tmp_path))

        out = capsys.readouterr().out
        assert "Error moving x.dat" in out


class TestOrganizeByDate:
    def test_missing_directory(self, tmp_path, capsys):
        file_organizer.organize_files_by_date(str(tmp_path / "missing"))
        assert "does not exist" in capsys.readouterr().out

    def test_groups_files_into_year_month_buckets(self, tmp_path):
        (tmp_path / "doc.txt").write_text("1")
        (tmp_path / "sub").mkdir()  # ignored

        ctime = _dt.datetime(2026, 4, 19, 12, 0, 0).timestamp()

        with patch("scripts.automation.file_organizer.os.stat",
                   side_effect=_stat_with_ctime(ctime)):
            file_organizer.organize_files_by_date(str(tmp_path))

        bucket = tmp_path / "2026-04"
        assert (bucket / "doc.txt").exists()
        assert (tmp_path / "sub").is_dir()

    def test_move_failure_is_logged(self, tmp_path, capsys):
        (tmp_path / "doc.txt").write_text("1")

        with patch("scripts.automation.file_organizer.os.stat",
                   side_effect=_stat_with_ctime(0.0)), \
             patch("scripts.automation.file_organizer.shutil.move",
                   side_effect=OSError("disk full")):
            file_organizer.organize_files_by_date(str(tmp_path))

        assert "Error moving doc.txt" in capsys.readouterr().out

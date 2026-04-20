"""Whitebox coverage for ``scripts/automation/file_renamer.py``.

Targets every branch in ``rename_files``:

    * directory does not exist (early return).
    * directory exists, no files match pattern (loop runs but body skipped).
    * directory exists, multiple files match (loop body executed N times).
    * ``os.rename`` raises ``OSError`` (exception arm).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from scripts.automation import file_renamer


class TestRenameFiles:
    def test_returns_when_directory_missing(self, tmp_path, capsys):
        missing = tmp_path / "nope"
        file_renamer.rename_files(str(missing), "old", "new")
        out = capsys.readouterr().out
        assert "does not exist" in out
        assert "Total files renamed" not in out  # short-circuit return

    def test_no_matches_zero_iterations(self, tmp_path, capsys):
        (tmp_path / "alpha.txt").write_text("x")
        (tmp_path / "beta.txt").write_text("y")
        file_renamer.rename_files(str(tmp_path), "ZZZ", "QQQ")
        out = capsys.readouterr().out
        assert "Total files renamed: 0" in out
        assert (tmp_path / "alpha.txt").exists()
        assert (tmp_path / "beta.txt").exists()

    def test_renames_only_matching_files(self, tmp_path, capsys):
        (tmp_path / "log_a.txt").write_text("1")
        (tmp_path / "log_b.txt").write_text("2")
        (tmp_path / "other.txt").write_text("3")

        file_renamer.rename_files(str(tmp_path), "log_", "trace_")

        out = capsys.readouterr().out
        assert (tmp_path / "trace_a.txt").exists()
        assert (tmp_path / "trace_b.txt").exists()
        assert (tmp_path / "other.txt").exists()
        assert not (tmp_path / "log_a.txt").exists()
        assert "Total files renamed: 2" in out

    def test_oserror_path_is_handled(self, tmp_path, capsys):
        (tmp_path / "match_me.txt").write_text("1")

        with patch("scripts.automation.file_renamer.os.rename",
                   side_effect=OSError("permission denied")):
            file_renamer.rename_files(str(tmp_path), "match_", "renamed_")

        out = capsys.readouterr().out
        assert "Error renaming match_me.txt" in out
        assert "Total files renamed: 0" in out  # exception arm => counter not incremented

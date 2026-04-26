"""
Black-box tests for scripts.automation.file_organizer.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
Uses tmp_path for real filesystem isolation (no mocks).
"""
import os

import pytest

from scripts.automation.file_organizer import (
    organize_files_by_date,
    organize_files_by_extension,
)

pytestmark = pytest.mark.blackbox


def _touch(dirpath, name, content="x"):
    p = dirpath / name
    p.write_text(content)
    return p


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestOrganizeByExtensionEP:
    """
    EP partitions for organize_files_by_extension:
      file type:  regular file / subdirectory
      extension:  known / no extension / mixed case / multi-dot
      source:     exists / does not exist
    """

    def test_single_extension_group(self, tmp_path):
        # EP: one file with a standard extension -> moved into `<ext>/`.
        _touch(tmp_path, "a.txt")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "txt" / "a.txt").exists()
        assert not (tmp_path / "a.txt").exists()

    def test_multiple_extensions_get_separate_folders(self, tmp_path):
        # EP: one file per extension class -> one folder per class.
        _touch(tmp_path, "a.txt")
        _touch(tmp_path, "b.csv")
        _touch(tmp_path, "c.json")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "txt" / "a.txt").exists()
        assert (tmp_path / "csv" / "b.csv").exists()
        assert (tmp_path / "json" / "c.json").exists()

    def test_file_without_extension_goes_to_no_extension_folder(self, tmp_path):
        # EP: no-extension class.
        _touch(tmp_path, "README")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "no_extension" / "README").exists()

    def test_subdirectories_are_left_alone(self, tmp_path):
        # EP: non-file class (subdir) must not be organized.
        (tmp_path / "sub").mkdir()
        _touch(tmp_path, "x.txt")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "sub").is_dir()
        assert (tmp_path / "txt" / "x.txt").exists()

    def test_nonexistent_source_is_silent(self, tmp_path, capsys):
        # EP: invalid-source class -> prints and returns, no raise.
        organize_files_by_extension(str(tmp_path / "nope"))
        out = capsys.readouterr().out
        assert "does not exist" in out


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_empty_directory(self, tmp_path):
        # BA: empty collection boundary - nothing moved, no folders created.
        organize_files_by_extension(str(tmp_path))
        # No new folders should have been created.
        assert list(tmp_path.iterdir()) == []

    def test_single_character_extension(self, tmp_path):
        # BA: shortest legal extension (1 char).
        _touch(tmp_path, "x.a")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "a" / "x.a").exists()

    def test_same_name_no_collision_when_unique(self, tmp_path):
        # BA: multiple files of same extension with unique names.
        _touch(tmp_path, "a.txt")
        _touch(tmp_path, "b.txt")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "txt" / "a.txt").exists()
        assert (tmp_path / "txt" / "b.txt").exists()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_multi_dot_filename_uses_last_suffix_only(self, tmp_path):
        # EG: multi-dot behavior: `a.tar.gz` -> suffix == `.gz`.
        _touch(tmp_path, "archive.tar.gz")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "gz" / "archive.tar.gz").exists()
        assert not (tmp_path / "tar.gz").exists()

    def test_mixed_case_extension_normalized_lowercase(self, tmp_path):
        # EG: .lower() is applied -> uppercase extension goes to the
        # lowercase-named folder.
        _touch(tmp_path, "image.JPG")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "jpg" / "image.JPG").exists()

    def test_hidden_dotfile_has_no_extension_per_pathlib(self, tmp_path):
        # EG: pathlib treats `.bashrc` as having no suffix -> no_extension/.
        _touch(tmp_path, ".bashrc")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "no_extension" / ".bashrc").exists()

    def test_collision_on_existing_destination_preserves_existing_file(self, tmp_path):
        # EG / FAULT-HUNTING: when `<ext>/<filename>` already exists at the
        # destination, the expected safe behavior is to preserve the existing
        # file (either skip, or rename the incoming). On some platforms
        # `shutil.move` silently OVERWRITES the existing file, causing
        # data loss. Intended contract: existing file is NOT overwritten.
        # Designed to FAIL on platforms where shutil.move overwrites
        # (see FINDINGS.md FAULT-006).
        (tmp_path / "txt").mkdir()
        existing = tmp_path / "txt" / "a.txt"
        existing.write_text("EXISTING_DATA")
        _touch(tmp_path, "a.txt", content="NEW_DATA")
        organize_files_by_extension(str(tmp_path))
        # The existing file's content must not have been overwritten.
        assert existing.read_text() == "EXISTING_DATA"

    def test_organize_by_date_creates_year_month_folder(self, tmp_path):
        # EG: by_date path creates a YYYY-MM folder derived from ctime.
        _touch(tmp_path, "f.log")
        organize_files_by_date(str(tmp_path))
        # Exactly one new folder should exist with a YYYY-MM name.
        subdirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        assert len(subdirs) == 1
        assert len(subdirs[0].name) == 7
        assert subdirs[0].name[4] == "-"

    def test_organize_by_date_nonexistent_source_is_silent(self, tmp_path, capsys):
        # EG: same invalid-source contract as by_extension.
        organize_files_by_date(str(tmp_path / "nope"))
        assert "does not exist" in capsys.readouterr().out

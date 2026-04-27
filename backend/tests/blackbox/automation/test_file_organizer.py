import os

import pytest

from scripts.automation.file_organizer import (
    organize_files_by_date,
    organize_files_by_extension,
)
pytestmark = pytest.mark.blackbox


# Defines the touch helper.
def _touch(dirpath, name, content="x"):
    p = dirpath / name
    p.write_text(content)
    return p


class TestOrganizeByExtensionEP:
    # Tests single extension group.
    def test_single_extension_group(self, tmp_path):
        _touch(tmp_path, "a.txt")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "txt" / "a.txt").exists()
        assert not (tmp_path / "a.txt").exists()

    # Tests multiple extensions get separate folders.
    def test_multiple_extensions_get_separate_folders(self, tmp_path):
        _touch(tmp_path, "a.txt")
        _touch(tmp_path, "b.csv")
        _touch(tmp_path, "c.json")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "txt" / "a.txt").exists()
        assert (tmp_path / "csv" / "b.csv").exists()
        assert (tmp_path / "json" / "c.json").exists()

    # Tests file without extension goes to no extension folder.
    def test_file_without_extension_goes_to_no_extension_folder(self, tmp_path):
        _touch(tmp_path, "README")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "no_extension" / "README").exists()

    # Tests subdirectories are left alone.
    def test_subdirectories_are_left_alone(self, tmp_path):
        (tmp_path / "sub").mkdir()
        _touch(tmp_path, "x.txt")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "sub").is_dir()
        assert (tmp_path / "txt" / "x.txt").exists()

    # Tests nonexistent source is silent.
    def test_nonexistent_source_is_silent(self, tmp_path, capsys):
        organize_files_by_extension(str(tmp_path / "nope"))
        out = capsys.readouterr().out
        assert "does not exist" in out


class TestBoundaries:
    # Tests empty directory.
    def test_empty_directory(self, tmp_path):
        organize_files_by_extension(str(tmp_path))
        assert list(tmp_path.iterdir()) == []

    # Tests single character extension.
    def test_single_character_extension(self, tmp_path):
        _touch(tmp_path, "x.a")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "a" / "x.a").exists()

    # Tests same name no collision when unique.
    def test_same_name_no_collision_when_unique(self, tmp_path):
        _touch(tmp_path, "a.txt")
        _touch(tmp_path, "b.txt")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "txt" / "a.txt").exists()
        assert (tmp_path / "txt" / "b.txt").exists()


class TestErrorGuessing:
    # Tests multi dot filename uses last suffix only.
    def test_multi_dot_filename_uses_last_suffix_only(self, tmp_path):
        _touch(tmp_path, "archive.tar.gz")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "gz" / "archive.tar.gz").exists()
        assert not (tmp_path / "tar.gz").exists()

    # Tests mixed case extension normalized lowercase.
    def test_mixed_case_extension_normalized_lowercase(self, tmp_path):
        _touch(tmp_path, "image.JPG")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "jpg" / "image.JPG").exists()

    # Tests hidden dotfile has no extension per pathlib.
    def test_hidden_dotfile_has_no_extension_per_pathlib(self, tmp_path):
        _touch(tmp_path, ".bashrc")
        organize_files_by_extension(str(tmp_path))
        assert (tmp_path / "no_extension" / ".bashrc").exists()

    # Tests collision on existing destination preserves existing file.
    def test_collision_on_existing_destination_preserves_existing_file(self, tmp_path):
        (tmp_path / "txt").mkdir()
        existing = tmp_path / "txt" / "a.txt"
        existing.write_text("EXISTING_DATA")
        _touch(tmp_path, "a.txt", content="NEW_DATA")
        organize_files_by_extension(str(tmp_path))
        assert existing.read_text() == "EXISTING_DATA"

    # Tests organize by date creates year month folder.
    def test_organize_by_date_creates_year_month_folder(self, tmp_path):
        _touch(tmp_path, "f.log")
        organize_files_by_date(str(tmp_path))
        subdirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        assert len(subdirs) == 1
        assert len(subdirs[0].name) == 7
        assert subdirs[0].name[4] == "-"

    # Tests organize by date nonexistent source is silent.
    def test_organize_by_date_nonexistent_source_is_silent(self, tmp_path, capsys):
        organize_files_by_date(str(tmp_path / "nope"))
        assert "does not exist" in capsys.readouterr().out

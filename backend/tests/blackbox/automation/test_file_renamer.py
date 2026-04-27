import pytest

from scripts.automation.file_renamer import rename_files

pytestmark = pytest.mark.blackbox


# Defines the touch helper.
def _touch(dirpath, name, content="x"):
    (dirpath / name).write_text(content)


class TestRenameFilesEP:
    # Tests pattern match renames file.
    def test_pattern_match_renames_file(self, tmp_path):
        _touch(tmp_path, "draft_report.txt")
        rename_files(str(tmp_path), "draft_", "final_")
        assert (tmp_path / "final_report.txt").exists()
        assert not (tmp_path / "draft_report.txt").exists()

    # Tests pattern does not match leaves file.
    def test_pattern_does_not_match_leaves_file(self, tmp_path):
        _touch(tmp_path, "readme.md")
        rename_files(str(tmp_path), "draft_", "final_")
        assert (tmp_path / "readme.md").exists()

    # Tests multiple files same pattern.
    def test_multiple_files_same_pattern(self, tmp_path):
        _touch(tmp_path, "draft_a.txt")
        _touch(tmp_path, "draft_b.txt")
        _touch(tmp_path, "unrelated.md")
        rename_files(str(tmp_path), "draft_", "x_")
        assert (tmp_path / "x_a.txt").exists()
        assert (tmp_path / "x_b.txt").exists()
        assert (tmp_path / "unrelated.md").exists()

    # Tests nonexistent directory prints and returns.
    def test_nonexistent_directory_prints_and_returns(self, tmp_path, capsys):
        rename_files(str(tmp_path / "nope"), "a", "b")
        assert "does not exist" in capsys.readouterr().out


class TestBoundaries:
    # Tests empty directory.
    def test_empty_directory(self, tmp_path, capsys):
        rename_files(str(tmp_path), "a", "b")
        assert "Total files renamed: 0" in capsys.readouterr().out

    # Tests empty old pattern matches every filename.
    def test_empty_old_pattern_matches_every_filename(self, tmp_path):
        _touch(tmp_path, "a.txt")
        _touch(tmp_path, "b.txt")
        rename_files(str(tmp_path), "", "new_")
        files = sorted(p.name for p in tmp_path.iterdir())
        assert "a.txt" not in files
        assert "b.txt" not in files

    # Tests pattern equal to replacement is noop.
    def test_pattern_equal_to_replacement_is_noop(self, tmp_path):
        _touch(tmp_path, "draft.txt")
        rename_files(str(tmp_path), "draft", "draft")
        assert (tmp_path / "draft.txt").exists()


class TestErrorGuessing:
    # Tests pattern appears multiple times all replaced.
    def test_pattern_appears_multiple_times_all_replaced(self, tmp_path):
        _touch(tmp_path, "aa_aa.txt")
        rename_files(str(tmp_path), "aa", "bb")
        assert (tmp_path / "bb_bb.txt").exists()

    # Tests subdirectory entries are also iterated.
    def test_subdirectory_entries_are_also_iterated(self, tmp_path):
        (tmp_path / "draft_folder").mkdir()
        rename_files(str(tmp_path), "draft_", "done_")
        assert (tmp_path / "done_folder").exists()

    # Tests unicode filename renamed.
    def test_unicode_filename_renamed(self, tmp_path):
        _touch(tmp_path, "draft_\u00e9t\u00e9.txt")
        rename_files(str(tmp_path), "draft_", "final_")
        assert (tmp_path / "final_\u00e9t\u00e9.txt").exists()

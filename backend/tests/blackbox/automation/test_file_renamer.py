"""
Black-box tests for scripts.automation.file_renamer.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
Uses tmp_path for real filesystem isolation.
"""
import pytest

from scripts.automation.file_renamer import rename_files

pytestmark = pytest.mark.blackbox


def _touch(dirpath, name, content="x"):
    (dirpath / name).write_text(content)


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestRenameFilesEP:
    def test_pattern_match_renames_file(self, tmp_path):
        # EP: filename contains old_pattern -> renamed.
        _touch(tmp_path, "draft_report.txt")
        rename_files(str(tmp_path), "draft_", "final_")
        assert (tmp_path / "final_report.txt").exists()
        assert not (tmp_path / "draft_report.txt").exists()

    def test_pattern_does_not_match_leaves_file(self, tmp_path):
        # EP: filename does NOT contain old_pattern -> untouched.
        _touch(tmp_path, "readme.md")
        rename_files(str(tmp_path), "draft_", "final_")
        assert (tmp_path / "readme.md").exists()

    def test_multiple_files_same_pattern(self, tmp_path):
        # EP: many matches -> all renamed.
        _touch(tmp_path, "draft_a.txt")
        _touch(tmp_path, "draft_b.txt")
        _touch(tmp_path, "unrelated.md")
        rename_files(str(tmp_path), "draft_", "x_")
        assert (tmp_path / "x_a.txt").exists()
        assert (tmp_path / "x_b.txt").exists()
        assert (tmp_path / "unrelated.md").exists()

    def test_nonexistent_directory_prints_and_returns(self, tmp_path, capsys):
        # EP: invalid-directory class -> prints, no raise.
        rename_files(str(tmp_path / "nope"), "a", "b")
        assert "does not exist" in capsys.readouterr().out


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_empty_directory(self, tmp_path, capsys):
        # BA: 0 files -> "Total files renamed: 0".
        rename_files(str(tmp_path), "a", "b")
        assert "Total files renamed: 0" in capsys.readouterr().out

    def test_empty_old_pattern_matches_every_filename(self, tmp_path):
        # BA: empty substring is contained in every string -> every file
        # is renamed by prepending new_pattern.
        _touch(tmp_path, "a.txt")
        _touch(tmp_path, "b.txt")
        rename_files(str(tmp_path), "", "new_")
        # Current algorithm: filename.replace("", "new_") inserts "new_"
        # between every character. Documents the behavior.
        files = sorted(p.name for p in tmp_path.iterdir())
        # Original files are gone.
        assert "a.txt" not in files
        assert "b.txt" not in files

    def test_pattern_equal_to_replacement_is_noop(self, tmp_path):
        # BA: old == new -> file name unchanged, renamed count still >0.
        _touch(tmp_path, "draft.txt")
        rename_files(str(tmp_path), "draft", "draft")
        assert (tmp_path / "draft.txt").exists()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_pattern_appears_multiple_times_all_replaced(self, tmp_path):
        # EG: `str.replace` replaces ALL occurrences.
        _touch(tmp_path, "aa_aa.txt")
        rename_files(str(tmp_path), "aa", "bb")
        assert (tmp_path / "bb_bb.txt").exists()

    def test_subdirectory_entries_are_also_iterated(self, tmp_path):
        # EG: os.listdir includes subdirectory names, and the rename still
        # happens on matching subdirectory names. Documents current behavior.
        (tmp_path / "draft_folder").mkdir()
        rename_files(str(tmp_path), "draft_", "done_")
        assert (tmp_path / "done_folder").exists()

    def test_unicode_filename_renamed(self, tmp_path):
        # EG: unicode filenames should be renamed the same way.
        _touch(tmp_path, "draft_\u00e9t\u00e9.txt")
        rename_files(str(tmp_path), "draft_", "final_")
        assert (tmp_path / "final_\u00e9t\u00e9.txt").exists()

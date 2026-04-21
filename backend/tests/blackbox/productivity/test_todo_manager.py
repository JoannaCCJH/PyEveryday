"""
Black-box tests for scripts.productivity.todo_manager.

Applies EP / BA / EG. Each test is labeled with its technique and goal.

Tests treat the JSON-backed persistence as an external boundary and pass
an explicit tmp_path-based filename so the repo-root todo_list.json is
never touched.
"""
import datetime
import json
import os

import pytest

from scripts.productivity.todo_manager import Priority, TodoItem, TodoManager

pytestmark = pytest.mark.blackbox


def _mgr(tmp_path):
    # Always instantiate AFTER cwd is redirected so default filename lands in tmp.
    return TodoManager(filename=str(tmp_path / "todo_list.json"))


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestAddTaskEP:
    """
    EP partitions for add_task:
      priority: LOW / MEDIUM / HIGH (3 valid classes)
      due_date: None / ISO-date-string
    """

    def test_add_task_default_priority(self, tmp_path):
        # EP: default priority class -> MEDIUM.
        mgr = _mgr(tmp_path)
        mgr.add_task("buy milk")
        assert len(mgr.todos) == 1
        assert mgr.todos[0].priority == Priority.MEDIUM

    @pytest.mark.parametrize("prio", [Priority.LOW, Priority.MEDIUM, Priority.HIGH])
    def test_add_task_each_priority(self, tmp_path, prio):
        # EP: one test per priority class.
        mgr = _mgr(tmp_path)
        mgr.add_task("x", priority=prio)
        assert mgr.todos[0].priority == prio

    def test_add_task_persists_to_disk(self, tmp_path):
        # EP: side effect - the JSON file must exist and contain the task.
        mgr = _mgr(tmp_path)
        mgr.add_task("persist me")
        filepath = tmp_path / "todo_list.json"
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data[0]["task"] == "persist me"


class TestCompleteTaskEP:
    def test_complete_task_marks_completed(self, tmp_path):
        # EP: valid-index class.
        mgr = _mgr(tmp_path)
        mgr.add_task("a")
        mgr.complete_task(0)
        assert mgr.todos[0].completed is True

    def test_complete_invalid_index_is_silent(self, tmp_path, capsys):
        # EP: invalid-index class - no raise, prints "Invalid task index".
        mgr = _mgr(tmp_path)
        mgr.add_task("only one")
        mgr.complete_task(5)
        out = capsys.readouterr().out
        assert "Invalid" in out
        assert mgr.todos[0].completed is False


class TestRemoveTaskEP:
    def test_remove_valid_index(self, tmp_path):
        # EP: valid-index class.
        mgr = _mgr(tmp_path)
        mgr.add_task("a")
        mgr.add_task("b")
        mgr.remove_task(0)
        assert [t.task for t in mgr.todos] == ["b"]

    def test_remove_invalid_index_is_silent(self, tmp_path, capsys):
        # EP: invalid-index class.
        mgr = _mgr(tmp_path)
        mgr.add_task("a")
        mgr.remove_task(99)
        out = capsys.readouterr().out
        assert "Invalid" in out
        assert len(mgr.todos) == 1


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestIndexBoundariesBA:
    """Boundary analysis on task indices: -1, 0, len-1, len."""

    def test_negative_one_is_invalid(self, tmp_path, capsys):
        # BA: index=-1 (one below valid range).
        mgr = _mgr(tmp_path)
        mgr.add_task("a")
        mgr.complete_task(-1)
        assert "Invalid" in capsys.readouterr().out
        assert mgr.todos[0].completed is False

    def test_index_zero_is_valid_when_list_nonempty(self, tmp_path):
        # BA: index=0 (lower valid bound).
        mgr = _mgr(tmp_path)
        mgr.add_task("a")
        mgr.complete_task(0)
        assert mgr.todos[0].completed is True

    def test_index_equal_to_length_is_invalid(self, tmp_path, capsys):
        # BA: index==len (first out-of-bounds value above).
        mgr = _mgr(tmp_path)
        mgr.add_task("a")
        mgr.complete_task(1)
        assert "Invalid" in capsys.readouterr().out

    def test_complete_on_empty_list_is_silent(self, tmp_path, capsys):
        # BA: index=0 when list is empty (len=0 -> no valid index).
        mgr = _mgr(tmp_path)
        mgr.complete_task(0)
        assert "Invalid" in capsys.readouterr().out


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_duplicate_task_text_allowed(self, tmp_path):
        # EG: no uniqueness constraint. Duplicates should coexist.
        mgr = _mgr(tmp_path)
        mgr.add_task("duplicate")
        mgr.add_task("duplicate")
        assert len(mgr.todos) == 2

    def test_empty_task_text_allowed(self, tmp_path):
        # EG: empty string task text. No validation documented -> accepted.
        mgr = _mgr(tmp_path)
        mgr.add_task("")
        assert mgr.todos[0].task == ""

    def test_get_today_tasks_empty_when_no_due_dates(self, tmp_path):
        # EG: tasks without due_date are not "today" tasks.
        mgr = _mgr(tmp_path)
        mgr.add_task("no due")
        assert mgr.get_today_tasks() == []

    def test_get_today_tasks_returns_tasks_with_today_due(self, tmp_path):
        # EG: due_date matching today's ISO date -> in result.
        mgr = _mgr(tmp_path)
        today = datetime.date.today().isoformat()
        mgr.add_task("today", due_date=today)
        mgr.add_task("not today", due_date="1999-01-01")
        today_tasks = mgr.get_today_tasks()
        assert len(today_tasks) == 1
        assert today_tasks[0].task == "today"

    def test_completed_today_tasks_excluded(self, tmp_path):
        # EG: completed tasks are filtered out of today's list.
        mgr = _mgr(tmp_path)
        today = datetime.date.today().isoformat()
        mgr.add_task("done", due_date=today)
        mgr.complete_task(0)
        assert mgr.get_today_tasks() == []

    def test_load_todos_on_missing_file_returns_empty(self, tmp_path):
        # EG: no existing file -> empty list, not a crash.
        mgr = TodoManager(filename=str(tmp_path / "does_not_exist.json"))
        assert mgr.todos == []

    def test_load_todos_round_trip_preserves_fields(self, tmp_path):
        # EG: save/reload contract - priority, task, completed, due_date preserved.
        filepath = str(tmp_path / "rt.json")
        mgr = TodoManager(filename=filepath)
        mgr.add_task("round trip", priority=Priority.HIGH, due_date="2030-01-01")
        mgr.complete_task(0)
        mgr2 = TodoManager(filename=filepath)
        assert mgr2.todos[0].task == "round trip"
        assert mgr2.todos[0].priority == Priority.HIGH
        assert mgr2.todos[0].completed is True
        assert mgr2.todos[0].due_date == "2030-01-01"

    def test_load_corrupt_json_raises(self, tmp_path):
        # EG: load_todos has no try/except - malformed JSON crashes.
        filepath = tmp_path / "bad.json"
        filepath.write_text("this is not json {")
        with pytest.raises(json.JSONDecodeError):
            TodoManager(filename=str(filepath))

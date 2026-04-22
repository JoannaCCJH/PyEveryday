"""
Black-box tests for scripts.automation.folder_monitor.

Applies EP / BA / EG. The watchdog observer loop is NOT exercised
(it's a blocking main-thread poll). Tests focus on the event-handler
class and its subprocess dispatch.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts.automation.folder_monitor import FolderMonitor

pytestmark = pytest.mark.blackbox


def _event(src_path, dest_path=None, is_directory=False):
    return SimpleNamespace(src_path=src_path, dest_path=dest_path, is_directory=is_directory)


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestEventHandlersEP:
    def test_on_modified_on_file_prints_and_executes_action(self, capsys):
        # EP: file event class -> prints AND (if action_script) executes.
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_modified(_event("/tmp/x.txt"))
        assert "modified" in capsys.readouterr().out
        assert mock_run.called

    def test_on_modified_on_directory_is_noop(self, capsys):
        # EP: directory event class -> handler short-circuits.
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_modified(_event("/tmp/subdir", is_directory=True))
        assert capsys.readouterr().out == ""
        mock_run.assert_not_called()

    def test_without_action_script_does_not_exec(self, capsys):
        # EP: no-action-script class -> prints event but does not call subprocess.
        m = FolderMonitor(action_script=None)
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_created(_event("/tmp/new.txt"))
        assert "created" in capsys.readouterr().out
        mock_run.assert_not_called()

    @pytest.mark.parametrize("handler_name, event_label", [
        ("on_modified", "modified"),
        ("on_created", "created"),
        ("on_deleted", "deleted"),
    ])
    def test_handler_passes_action_label_to_script(self, handler_name, event_label):
        # EP: one test per event-type class.
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            getattr(m, handler_name)(_event("/tmp/x.txt"))
        args = mock_run.call_args.args[0]
        assert event_label in args

    def test_on_moved_passes_dest_path_not_src(self):
        # EP: move-event class uses dest_path per SUT.
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_moved(_event("/tmp/old.txt", dest_path="/tmp/new.txt"))
        args = mock_run.call_args.args[0]
        assert "/tmp/new.txt" in args
        assert "moved" in args


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestExecuteActionBA:
    def test_subprocess_non_zero_return_prints_error(self, capsys):
        # BA: CalledProcessError caught -> prints error.
        import subprocess

        m = FolderMonitor(action_script="do.py")
        with patch(
            "scripts.automation.folder_monitor.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "do.py"),
        ):
            m.execute_action("/tmp/x.txt", "modified")
        assert "Error executing action script" in capsys.readouterr().out


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_execute_action_uses_sys_executable(self):
        # EG: the SUT uses sys.executable (so the action script runs in the
        # same Python interpreter). Verify it's passed as argv[0].
        import sys

        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.execute_action("/tmp/x.txt", "modified")
        args = mock_run.call_args.args[0]
        assert args[0] == sys.executable

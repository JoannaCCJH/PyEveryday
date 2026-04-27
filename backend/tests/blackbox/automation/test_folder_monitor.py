from types import SimpleNamespace

from unittest.mock import MagicMock, patch

import pytest

from scripts.automation.folder_monitor import FolderMonitor

pytestmark = pytest.mark.blackbox


# Defines the event helper.
def _event(src_path, dest_path=None, is_directory=False):
    return SimpleNamespace(src_path=src_path, dest_path=dest_path, is_directory=is_directory)


class TestEventHandlersEP:
    # Tests on modified on file prints and executes action.
    def test_on_modified_on_file_prints_and_executes_action(self, capsys):
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_modified(_event("/tmp/x.txt"))
        assert "modified" in capsys.readouterr().out
        assert mock_run.called

    # Tests on modified on directory is noop.
    def test_on_modified_on_directory_is_noop(self, capsys):
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_modified(_event("/tmp/subdir", is_directory=True))
        assert capsys.readouterr().out == ""
        mock_run.assert_not_called()

    # Tests without action script does not exec.
    def test_without_action_script_does_not_exec(self, capsys):
        m = FolderMonitor(action_script=None)
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_created(_event("/tmp/new.txt"))
        assert "created" in capsys.readouterr().out
        mock_run.assert_not_called()

    # Tests handler passes action label to script.
    @pytest.mark.parametrize("handler_name, event_label", [
        ("on_modified", "modified"),
        ("on_created", "created"),
        ("on_deleted", "deleted"),
    ])
    def test_handler_passes_action_label_to_script(self, handler_name, event_label):
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            getattr(m, handler_name)(_event("/tmp/x.txt"))
        args = mock_run.call_args.args[0]
        assert event_label in args

    # Tests on moved passes dest path not src.
    def test_on_moved_passes_dest_path_not_src(self):
        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.on_moved(_event("/tmp/old.txt", dest_path="/tmp/new.txt"))
        args = mock_run.call_args.args[0]
        assert "/tmp/new.txt" in args
        assert "moved" in args


class TestExecuteActionBA:
    # Tests subprocess non zero return prints error.
    def test_subprocess_non_zero_return_prints_error(self, capsys):

        import subprocess

        m = FolderMonitor(action_script="do.py")
        with patch(
            "scripts.automation.folder_monitor.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "do.py"),
        ):
            m.execute_action("/tmp/x.txt", "modified")
        assert "Error executing action script" in capsys.readouterr().out


class TestErrorGuessing:
    # Tests execute action uses sys executable.
    def test_execute_action_uses_sys_executable(self):

        import sys

        m = FolderMonitor(action_script="do.py")
        with patch("scripts.automation.folder_monitor.subprocess.run") as mock_run:
            m.execute_action("/tmp/x.txt", "modified")
        args = mock_run.call_args.args[0]
        assert args[0] == sys.executable

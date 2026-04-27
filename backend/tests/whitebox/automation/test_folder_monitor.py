from __future__ import annotations

import subprocess

from types import SimpleNamespace

from unittest.mock import MagicMock, patch

import pytest

from scripts.automation import folder_monitor as fm


# Defines the evt helper.
def _evt(src, dest=None, is_directory=False):
    e = SimpleNamespace(src_path=src, is_directory=is_directory)
    if dest is not None:
        e.dest_path = dest
    return e


class TestEventCallbacks:
    # Tests file event invokes action.
    def test_file_event_invokes_action(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(handler, "execute_action") as ea:
            handler.on_modified(_evt("/tmp/x.txt"))
            handler.on_created(_evt("/tmp/y.txt"))
            handler.on_deleted(_evt("/tmp/z.txt"))
        assert ea.call_count == 3

    # Tests on moved uses dest path.
    def test_on_moved_uses_dest_path(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(handler, "execute_action") as ea:
            handler.on_moved(_evt("/tmp/old.txt", dest="/tmp/new.txt"))
        ea.assert_called_once_with("/tmp/new.txt", "moved")

    # Tests directory event is ignored.
    def test_directory_event_is_ignored(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(handler, "execute_action") as ea:
            handler.on_modified(_evt("/tmp/dir", is_directory=True))
        ea.assert_not_called()


class TestExecuteAction:
    # Tests calledprocesserror branch.
    def test_calledprocesserror_branch(self, capsys):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(fm.subprocess, "run",
                          side_effect=subprocess.CalledProcessError(1, ["x"])):
            handler.execute_action("/tmp/x.txt", "created")
        assert "Error executing action script" in capsys.readouterr().out


class TestMonitorFolder:
    # Tests normal path starts and joins observer.
    def test_normal_path_starts_and_joins_observer(self, tmp_path):
        observer = MagicMock()
        with (
            patch.object(fm, "Observer", return_value=observer),
            patch.object(fm.time, "sleep", side_effect=KeyboardInterrupt),
        ):
            fm.monitor_folder(str(tmp_path))
        observer.schedule.assert_called_once()
        observer.start.assert_called_once()
        observer.stop.assert_called_once()

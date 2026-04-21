"""Whitebox coverage for ``scripts/automation/folder_monitor.py``.

Tightened: every branch of the three public surfaces (events, action exec,
monitor driver) without the parametrize-3x duplication.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts.automation import folder_monitor as fm


def _evt(src, dest=None, is_directory=False):
    e = SimpleNamespace(src_path=src, is_directory=is_directory)
    if dest is not None:
        e.dest_path = dest
    return e


class TestEventCallbacks:
    def test_file_event_invokes_action(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(handler, "execute_action") as ea:
            handler.on_modified(_evt("/tmp/x.txt"))
        ea.assert_called_once_with("/tmp/x.txt", "modified")

    def test_on_moved_uses_dest_path(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(handler, "execute_action") as ea:
            handler.on_moved(_evt("/tmp/old.txt", dest="/tmp/new.txt"))
        ea.assert_called_once_with("/tmp/new.txt", "moved")

    def test_directory_event_is_ignored(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(handler, "execute_action") as ea:
            handler.on_modified(_evt("/tmp/dir", is_directory=True))
        ea.assert_not_called()


class TestExecuteAction:
    def test_success_runs_subprocess(self):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(fm.subprocess, "run") as run:
            handler.execute_action("/tmp/x.txt", "created")
        run.assert_called_once()

    def test_calledprocesserror_branch(self, capsys):
        handler = fm.FolderMonitor(action_script="action.py")
        with patch.object(fm.subprocess, "run",
                          side_effect=subprocess.CalledProcessError(1, ["x"])):
            handler.execute_action("/tmp/x.txt", "created")
        assert "Error executing action script" in capsys.readouterr().out


class TestMonitorFolder:
    def test_normal_path_starts_and_joins_observer(self, tmp_path):
        observer = MagicMock()
        with patch.object(fm, "Observer", return_value=observer), \
             patch.object(fm.time, "sleep", side_effect=KeyboardInterrupt):
            fm.monitor_folder(str(tmp_path))
        observer.schedule.assert_called_once()
        observer.start.assert_called_once()
        observer.stop.assert_called_once()
        observer.join.assert_called_once()

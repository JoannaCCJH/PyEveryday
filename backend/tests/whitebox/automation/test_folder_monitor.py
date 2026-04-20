"""Whitebox coverage for ``scripts/automation/folder_monitor.py``.

The module wraps watchdog's ``FileSystemEventHandler`` and shells out via
``subprocess`` for action scripts.  We never start a real watchdog observer or
spawn a real process — every dependency is mocked.  We then exercise:

* each ``on_*`` callback for both directory and file events.
* the ``execute_action`` branches (success and ``CalledProcessError``).
* ``monitor_folder``: missing folder short-circuit, normal start/stop loop
  (exited via ``KeyboardInterrupt``).
* the sample-action-script generator.
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
    @pytest.mark.parametrize("method,event_kwargs,expected_action", [
        ("on_modified", {}, "modified"),
        ("on_created", {}, "created"),
        ("on_deleted", {}, "deleted"),
    ])
    def test_file_events_invoke_action(self, method, event_kwargs, expected_action):
        handler = fm.FolderMonitor(action_script="action.py")
        evt = _evt("/tmp/x.txt", **event_kwargs)
        with patch.object(handler, "execute_action") as ea:
            getattr(handler, method)(evt)
        ea.assert_called_once_with("/tmp/x.txt", expected_action)

    def test_on_moved_uses_dest_path(self):
        handler = fm.FolderMonitor(action_script="action.py")
        evt = _evt("/tmp/old.txt", dest="/tmp/new.txt")
        with patch.object(handler, "execute_action") as ea:
            handler.on_moved(evt)
        ea.assert_called_once_with("/tmp/new.txt", "moved")

    @pytest.mark.parametrize("method", ["on_modified", "on_created", "on_deleted"])
    def test_directory_events_are_ignored(self, method):
        handler = fm.FolderMonitor(action_script="action.py")
        evt = _evt("/tmp/dir", is_directory=True)
        with patch.object(handler, "execute_action") as ea:
            getattr(handler, method)(evt)
        ea.assert_not_called()

    def test_no_action_script_no_subprocess(self):
        handler = fm.FolderMonitor(action_script=None)
        evt = _evt("/tmp/x.txt")
        with patch.object(handler, "execute_action") as ea:
            handler.on_modified(evt)
        ea.assert_not_called()  # `if self.action_script` is False


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
    def test_missing_folder_short_circuits(self, tmp_path, capsys):
        fm.monitor_folder(str(tmp_path / "nope"))
        assert "does not exist" in capsys.readouterr().out

    def test_normal_path_starts_and_joins_observer(self, tmp_path):
        observer = MagicMock()
        with patch.object(fm, "Observer", return_value=observer), \
             patch.object(fm.time, "sleep", side_effect=KeyboardInterrupt):
            fm.monitor_folder(str(tmp_path))
        observer.schedule.assert_called_once()
        observer.start.assert_called_once()
        observer.stop.assert_called_once()
        observer.join.assert_called_once()


class TestCreateSampleActionScript:
    def test_writes_expected_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        fm.create_sample_action_script()
        assert (tmp_path / "sample_action.py").exists()
        body = (tmp_path / "sample_action.py").read_text()
        assert "shutil" in body and "backup_texts" in body

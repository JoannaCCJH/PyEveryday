"""CLI smoke tests for automation scripts via ``runpy``.

Drives ``__main__`` blocks to cover the CLI dispatch branches without
launching real schedulers, sending real email, or running watchdog loops.
"""

from __future__ import annotations

import runpy
import sys
from unittest.mock import MagicMock, patch

import pytest


def _run(module_name, argv, **patches):
    ctxs = [patch.object(sys, "argv", list(argv))]
    for target, value in patches.items():
        ctxs.append(patch(target, value))
    for c in ctxs:
        c.__enter__()
    try:
        try:
            runpy.run_module(module_name, run_name="__main__")
        except SystemExit:
            pass
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


# --------------------------- file_renamer -----------------------------------

FR = "scripts.automation.file_renamer"


class TestFileRenamerCLI:
    def test_usage(self, capsys):
        _run(FR, [FR])
        capsys.readouterr()

    def test_renames_files(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        (d / "old_a.txt").write_text("a")
        (d / "old_b.txt").write_text("b")
        _run(FR, [FR, str(d), "old_", "new_"])
        assert (d / "new_a.txt").exists()
        assert (d / "new_b.txt").exists()
        capsys.readouterr()

    def test_missing_dir_prints_message(self, tmp_path, capsys):
        _run(FR, [FR, str(tmp_path / "no"), "x", "y"])
        assert "does not exist" in capsys.readouterr().out


# --------------------------- file_organizer ---------------------------------

FO = "scripts.automation.file_organizer"


class TestFileOrganizerCLI:
    def test_usage(self, capsys):
        _run(FO, [FO])
        capsys.readouterr()

    def test_invalid_type(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        _run(FO, [FO, str(d), "wat"])
        assert "Invalid type" in capsys.readouterr().out

    def test_organize_by_extension(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        (d / "a.txt").write_text("a")
        (d / "b.png").write_text("b")
        _run(FO, [FO, str(d), "extension"])
        capsys.readouterr()

    def test_organize_by_date(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        (d / "a.txt").write_text("a")
        _run(FO, [FO, str(d), "date"])
        capsys.readouterr()


# --------------------------- backup_scheduler -------------------------------

BS = "scripts.automation.backup_scheduler"


class TestBackupSchedulerCLI:
    def test_usage(self, capsys):
        _run(BS, [BS])
        capsys.readouterr()

    def test_manual_backup(self, tmp_path, capsys):
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.txt").write_text("hi")
        backup_dir = tmp_path / "bk"
        _run(BS, [BS, str(src), str(backup_dir), "manual"])
        capsys.readouterr()


# --------------------------- folder_monitor ---------------------------------

FM = "scripts.automation.folder_monitor"


class TestFolderMonitorCLI:
    def test_usage(self, capsys):
        _run(FM, [FM])
        capsys.readouterr()

    def test_create_sample(self, capsys):
        _run(FM, [FM, "create_sample"])
        capsys.readouterr()

    def test_monitor_missing_folder(self, tmp_path, capsys):
        # observer.start() would block; missing-folder branch returns early.
        _run(FM, [FM, str(tmp_path / "absent")])
        assert "does not exist" in capsys.readouterr().out


# --------------------------- auto_email_sender ------------------------------

AE = "scripts.automation.auto_email_sender"


class TestAutoEmailSenderCLI:
    def test_usage(self, capsys):
        _run(AE, [AE])
        capsys.readouterr()

    def test_send_email_failure_path(self, capsys):
        # No SMTP server reachable -> exception branch in send_email.
        _run(AE, [AE, "to@example.com", "subj", "body"],
             **{"scripts.automation.auto_email_sender.smtplib.SMTP":
                MagicMock(side_effect=RuntimeError("net"))})
        out = capsys.readouterr().out
        assert "Error sending email" in out

    def test_send_email_success_path(self, capsys):
        smtp_inst = MagicMock()
        smtp_cls = MagicMock(return_value=smtp_inst)
        _run(AE, [AE, "to@example.com", "subj", "body"],
             **{"scripts.automation.auto_email_sender.smtplib.SMTP": smtp_cls})
        out = capsys.readouterr().out
        assert "successfully" in out

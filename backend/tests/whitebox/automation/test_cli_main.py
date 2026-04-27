from __future__ import annotations

import runpy

import sys

from unittest.mock import MagicMock, patch

import pytest


# Defines the run helper.
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


# Provides the isolate_cwd fixture.
@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
FR = "scripts.automation.file_renamer"


class TestFileRenamerCLI:
    # Tests usage.
    def test_usage(self, capsys):
        _run(FR, [FR])
        capsys.readouterr()

    # Tests renames files.
    def test_renames_files(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        (d / "old_a.txt").write_text("a")
        (d / "old_b.txt").write_text("b")
        _run(FR, [FR, str(d), "old_", "new_"])
        assert (d / "new_a.txt").exists()
        assert (d / "new_b.txt").exists()
        capsys.readouterr()

    # Tests missing dir prints message.
    def test_missing_dir_prints_message(self, tmp_path, capsys):
        _run(FR, [FR, str(tmp_path / "no"), "x", "y"])
        assert "does not exist" in capsys.readouterr().out
FO = "scripts.automation.file_organizer"


class TestFileOrganizerCLI:
    # Tests usage.
    def test_usage(self, capsys):
        _run(FO, [FO])
        capsys.readouterr()

    # Tests invalid type.
    def test_invalid_type(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        _run(FO, [FO, str(d), "wat"])
        assert "Invalid type" in capsys.readouterr().out

    # Tests organize by extension.
    def test_organize_by_extension(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        (d / "a.txt").write_text("a")
        (d / "b.png").write_text("b")
        _run(FO, [FO, str(d), "extension"])
        capsys.readouterr()

    # Tests organize by date.
    def test_organize_by_date(self, tmp_path, capsys):
        d = tmp_path / "d"
        d.mkdir()
        (d / "a.txt").write_text("a")
        _run(FO, [FO, str(d), "date"])
        capsys.readouterr()
BS = "scripts.automation.backup_scheduler"


class TestBackupSchedulerCLI:
    # Tests usage.
    def test_usage(self, capsys):
        _run(BS, [BS])
        capsys.readouterr()

    # Tests manual backup.
    def test_manual_backup(self, tmp_path, capsys):
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.txt").write_text("hi")
        backup_dir = tmp_path / "bk"
        _run(BS, [BS, str(src), str(backup_dir), "manual"])
        capsys.readouterr()
FM = "scripts.automation.folder_monitor"


class TestFolderMonitorCLI:
    # Tests usage.
    def test_usage(self, capsys):
        _run(FM, [FM])
        capsys.readouterr()

    # Tests create sample.
    def test_create_sample(self, capsys):
        _run(FM, [FM, "create_sample"])
        capsys.readouterr()

    # Tests monitor missing folder.
    def test_monitor_missing_folder(self, tmp_path, capsys):
        _run(FM, [FM, str(tmp_path / "absent")])
        assert "does not exist" in capsys.readouterr().out
AE = "scripts.automation.auto_email_sender"


class TestAutoEmailSenderCLI:
    # Tests usage.
    def test_usage(self, capsys):
        _run(AE, [AE])
        capsys.readouterr()

    # Tests send email failure path.
    def test_send_email_failure_path(self, capsys):
        _run(AE, [AE, "to@example.com", "subj", "body"],
             **{"scripts.automation.auto_email_sender.smtplib.SMTP":
                MagicMock(side_effect=RuntimeError("net"))})
        out = capsys.readouterr().out
        assert "Error sending email" in out

    # Tests send email success path.
    def test_send_email_success_path(self, capsys):
        smtp_inst = MagicMock()
        smtp_cls = MagicMock(return_value=smtp_inst)
        _run(AE, [AE, "to@example.com", "subj", "body"],
             **{"scripts.automation.auto_email_sender.smtplib.SMTP": smtp_cls})
        out = capsys.readouterr().out
        assert "successfully" in out

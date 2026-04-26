from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.tests.cli.conftest import pairs


BS = "scripts.automation.backup_scheduler"
AE = "scripts.automation.auto_email_sender"


def _seed(d, names):
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / n).write_text("x")
    return d


@pytest.mark.parametrize("src_state,sched", pairs(
    ["exists", "missing"],
    ["manual", "default"],
))
def test_backup_scheduler_pair(invoke, tmp_path, src_state, sched):
    # Pairs of {source dir exists/missing} x {schedule arg explicit/omitted}.
    src = _seed(tmp_path / "src", ["f.txt"]) if src_state == "exists" else tmp_path / "ghost"
    argv = [str(src), str(tmp_path / "bk")] + (["manual"] if sched == "manual" else [])
    result = invoke(BS, argv)
    assert result.exit_code == 0
    if src_state == "missing":
        assert "does not exist" in result.output


@pytest.mark.parametrize("smtp,attach", pairs(
    ["ok", "boom"],
    ["plain", "with_attach"],
))
def test_auto_email_sender_pair(invoke, tmp_path, smtp, attach):
    # Pairs of {SMTP succeeds/raises} x {plain body / attachment included}.
    argv = ["to@example.com", "subj", "body"]
    if attach == "with_attach":
        f = tmp_path / "a.txt"
        f.write_text("att")
        argv.append(str(f))
    smtp_mock = MagicMock(return_value=MagicMock()) if smtp == "ok" \
        else MagicMock(side_effect=RuntimeError("net"))
    result = invoke(AE, argv,
                    patches={"scripts.automation.auto_email_sender.smtplib.SMTP": smtp_mock})
    assert result.exit_code == 0
    assert ("successfully" if smtp == "ok" else "Error sending email") in result.output

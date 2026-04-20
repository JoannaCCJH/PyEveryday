"""Whitebox coverage for ``scripts/automation/auto_email_sender.py``.

We patch ``smtplib.SMTP`` so the SUT never opens a real socket and we exercise
all branches:

* ``load_config``: existing JSON file vs missing-file default.
* ``send_email``: no attachments, attachments that exist (loop body taken),
  attachments that are missing (loop body skipped), SMTP exception arm.
* ``send_bulk_emails``: success counter is computed from individual results.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.automation.auto_email_sender import EmailSender


@pytest.fixture
def cfg(tmp_path):
    p = tmp_path / "email_config.json"
    p.write_text(json.dumps({
        "smtp_server": "smtp.example.com",
        "smtp_port": 1234,
        "sender_email": "me@example.com",
        "sender_password": "secret",
    }))
    return p


class TestLoadConfig:
    def test_loads_from_existing_file(self, cfg):
        sender = EmailSender(str(cfg))
        assert sender.config["sender_email"] == "me@example.com"

    def test_returns_default_when_missing(self, tmp_path):
        sender = EmailSender(str(tmp_path / "missing.json"))
        assert sender.config["smtp_server"] == "smtp.gmail.com"
        assert sender.config["smtp_port"] == 587
        assert sender.config["sender_email"] == ""


class TestSendEmail:
    def test_success_no_attachments(self, cfg):
        sender = EmailSender(str(cfg))
        smtp_instance = MagicMock()

        with patch("scripts.automation.auto_email_sender.smtplib.SMTP",
                   return_value=smtp_instance) as smtp_cls:
            ok = sender.send_email("dest@example.com", "Hi", "Body")

        assert ok is True
        smtp_cls.assert_called_once_with("smtp.example.com", 1234)
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("me@example.com", "secret")
        smtp_instance.sendmail.assert_called_once()
        smtp_instance.quit.assert_called_once()

    def test_existing_attachment_is_attached(self, cfg, tmp_path):
        attachment = tmp_path / "att.bin"
        attachment.write_bytes(b"binary-payload")
        sender = EmailSender(str(cfg))

        with patch("scripts.automation.auto_email_sender.smtplib.SMTP",
                   return_value=MagicMock()):
            ok = sender.send_email("dest@example.com", "Hi", "Body", [str(attachment)])
        assert ok is True

    def test_missing_attachment_is_silently_skipped(self, cfg, tmp_path):
        sender = EmailSender(str(cfg))
        with patch("scripts.automation.auto_email_sender.smtplib.SMTP",
                   return_value=MagicMock()):
            ok = sender.send_email("dest@example.com", "Hi", "Body",
                                   [str(tmp_path / "nope.bin")])
        # the missing-file branch in the loop is `if os.path.exists(...)`
        # => the if-False branch is taken silently and the email still succeeds.
        assert ok is True

    def test_smtp_failure_branch(self, cfg, capsys):
        sender = EmailSender(str(cfg))
        with patch("scripts.automation.auto_email_sender.smtplib.SMTP",
                   side_effect=OSError("network down")):
            ok = sender.send_email("dest@example.com", "Hi", "Body")
        assert ok is False
        assert "Error sending email" in capsys.readouterr().out


class TestSendBulkEmails:
    def test_counts_only_successful(self, cfg, capsys):
        sender = EmailSender(str(cfg))
        with patch.object(EmailSender, "send_email", side_effect=[True, False, True]):
            sender.send_bulk_emails(["a@x", "b@x", "c@x"], "S", "B")
        assert "Successfully sent 2/3" in capsys.readouterr().out

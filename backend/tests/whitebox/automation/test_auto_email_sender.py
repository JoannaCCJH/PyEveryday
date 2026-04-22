"""Targeted whitebox coverage for ``scripts/automation/auto_email_sender.py``.

Slim — direct tests for ``EmailSender.send_email`` (success + failure)
and ``send_bulk_emails``.  CLI smoke test only hits the failure arm; we
add the success arm here so the bulk loop body is covered too.
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
        smtp_instance.sendmail.assert_called_once()


class TestSendBulkEmails:
    def test_counts_only_successful(self, cfg, capsys):
        sender = EmailSender(str(cfg))
        with patch.object(EmailSender, "send_email", side_effect=[True, False, True]):
            sender.send_bulk_emails(["a@x", "b@x", "c@x"], "S", "B")
        assert "Successfully sent 2/3" in capsys.readouterr().out

"""
Black-box tests for scripts.automation.auto_email_sender.

Applies EP / BA / EG. Each test is labeled with its technique and goal.

Primary SMTP-mock target: all tests patch smtplib.SMTP so no real
SMTP handshake happens.
"""
import json
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from scripts.automation.auto_email_sender import EmailSender

pytestmark = pytest.mark.blackbox


DEFAULT_CONFIG = {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "sender_email": "me@example.com",
    "sender_password": "secret",
}


@pytest.fixture
def sender(tmp_path, monkeypatch):
    # Isolate the default "email_config.json" load by redirecting cwd.
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "email_config.json"
    cfg_file.write_text(json.dumps(DEFAULT_CONFIG))
    return EmailSender(config_file=str(cfg_file))


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestLoadConfigEP:
    def test_existing_config_file_loaded(self, tmp_path):
        # EP: config file exists -> contents returned.
        f = tmp_path / "c.json"
        f.write_text(json.dumps({"smtp_server": "x.example", "smtp_port": 25,
                                 "sender_email": "a@a", "sender_password": "p"}))
        s = EmailSender(config_file=str(f))
        assert s.config["smtp_server"] == "x.example"

    def test_missing_config_file_uses_defaults(self, tmp_path):
        # EP: config file missing -> default gmail dict.
        s = EmailSender(config_file=str(tmp_path / "nope.json"))
        assert s.config["smtp_server"] == "smtp.gmail.com"
        assert s.config["smtp_port"] == 587
        assert s.config["sender_email"] == ""


class TestSendEmailEP:
    """
    EP partitions for send_email:
      result: success -> True
      SMTP exception: auth / recipients-refused / connect -> False
      attachments: None / valid-path / missing-path
    """

    def test_success_returns_true_and_calls_smtp_in_order(self, sender):
        # EP: happy path. Must return True and call SMTP methods in order.
        with patch("smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value
            result = sender.send_email("to@x.com", "s", "b")
        assert result is True
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("me@example.com", "secret")
        instance.sendmail.assert_called_once()
        instance.quit.assert_called_once()

    def test_auth_error_returns_false(self, sender):
        # EP: SMTPAuthenticationError class -> False (swallowed).
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad creds")
            result = sender.send_email("to@x.com", "s", "b")
        assert result is False

    def test_recipients_refused_returns_false(self, sender):
        # EP: SMTPRecipientsRefused class -> False.
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.sendmail.side_effect = smtplib.SMTPRecipientsRefused({"to@x.com": (550, b"no")})
            result = sender.send_email("to@x.com", "s", "b")
        assert result is False

    def test_connect_failure_returns_false(self, sender):
        # EP: connection class - SMTP() raises.
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("down")):
            result = sender.send_email("to@x.com", "s", "b")
        assert result is False


class TestBulkEmailsEP:
    def test_bulk_empty_list_never_calls_smtp(self, sender, capsys):
        # EP: empty-list class - no smtplib call.
        with patch("smtplib.SMTP") as mock_smtp:
            sender.send_bulk_emails([], "s", "b")
        mock_smtp.assert_not_called()
        assert "0/0" in capsys.readouterr().out

    def test_bulk_all_succeed(self, sender, capsys):
        # EP: all-success class - N/N in output.
        with patch("smtplib.SMTP"):
            sender.send_bulk_emails(["a@a", "b@b", "c@c"], "s", "b")
        assert "3/3" in capsys.readouterr().out

    def test_bulk_partial_failure(self, sender, capsys):
        # EP: partial-failure class - success count < total.
        call_count = {"n": 0}

        def _side_effect(server, port):
            call_count["n"] += 1
            instance = MagicMock()
            if call_count["n"] == 2:
                instance.sendmail.side_effect = smtplib.SMTPException("fail")
            return instance

        with patch("smtplib.SMTP", side_effect=_side_effect):
            sender.send_bulk_emails(["a@a", "b@b", "c@c"], "s", "b")
        assert "2/3" in capsys.readouterr().out


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_single_recipient_bulk(self, sender, capsys):
        # BA: smallest non-empty recipient list.
        with patch("smtplib.SMTP"):
            sender.send_bulk_emails(["one@x.com"], "s", "b")
        assert "1/1" in capsys.readouterr().out

    def test_empty_subject_and_body_still_sent(self, sender):
        # BA: empty strings are a natural lower bound.
        with patch("smtplib.SMTP") as mock_smtp:
            result = sender.send_email("to@x.com", "", "")
        assert result is True
        mock_smtp.return_value.sendmail.assert_called_once()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_attachment_missing_path_is_silently_skipped(self, sender):
        # EG / FAULT-HUNTING: missing attachment paths are silently skipped
        # via `if os.path.exists(file_path)`, so the email sends WITHOUT
        # the expected attachment. Users likely expect either an error or
        # a warning. This test documents the current behavior: no error,
        # no crash, email still sent.
        with patch("smtplib.SMTP") as mock_smtp:
            result = sender.send_email(
                "to@x.com", "s", "b", attachments=["/tmp/does_not_exist_xyz.pdf"]
            )
        # Currently: True (email sent, attachment silently dropped).
        # This is arguably a fault; see FINDINGS.md FAULT-005.
        assert result is True
        mock_smtp.return_value.sendmail.assert_called_once()

    def test_attachment_existing_path_is_included(self, sender, tmp_path):
        # EG: attachment path that exists -> included in the MIME payload.
        attach = tmp_path / "a.txt"
        attach.write_text("hello")
        with patch("smtplib.SMTP") as mock_smtp:
            sender.send_email("to@x.com", "s", "b", attachments=[str(attach)])
        # Confirm sendmail received a message containing the attachment filename.
        sent_payload = mock_smtp.return_value.sendmail.call_args.args[2]
        assert "a.txt" in sent_payload

    def test_empty_recipient_still_calls_smtp(self, sender):
        # EG: empty string recipient - MIME accepts; sendmail still called.
        with patch("smtplib.SMTP") as mock_smtp:
            result = sender.send_email("", "s", "b")
        assert result is True
        mock_smtp.return_value.sendmail.assert_called_once()

    def test_config_missing_required_key_returns_false(self, tmp_path):
        # EG: malformed config (missing sender_email) triggers KeyError, which
        # is caught by the generic except Exception -> returns False.
        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"smtp_server": "x", "smtp_port": 25}))
        s = EmailSender(config_file=str(f))
        with patch("smtplib.SMTP"):
            result = s.send_email("to@x.com", "s", "b")
        assert result is False

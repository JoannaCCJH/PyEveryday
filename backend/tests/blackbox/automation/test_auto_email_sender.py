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


# Provides the sender fixture.
@pytest.fixture
def sender(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "email_config.json"
    cfg_file.write_text(json.dumps(DEFAULT_CONFIG))
    return EmailSender(config_file=str(cfg_file))


class TestLoadConfigEP:
    # Tests existing config file loaded.
    def test_existing_config_file_loaded(self, tmp_path):
        f = tmp_path / "c.json"
        f.write_text(json.dumps({"smtp_server": "x.example", "smtp_port": 25,
                                 "sender_email": "a@a", "sender_password": "p"}))
        s = EmailSender(config_file=str(f))
        assert s.config["smtp_server"] == "x.example"

    # Tests missing config file uses defaults.
    def test_missing_config_file_uses_defaults(self, tmp_path):
        s = EmailSender(config_file=str(tmp_path / "nope.json"))
        assert s.config["smtp_server"] == "smtp.gmail.com"
        assert s.config["smtp_port"] == 587
        assert s.config["sender_email"] == ""


class TestSendEmailEP:
    # Tests success returns true and calls smtp in order.
    def test_success_returns_true_and_calls_smtp_in_order(self, sender):
        with patch("smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value
            result = sender.send_email("to@x.com", "s", "b")
        assert result is True
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("me@example.com", "secret")
        instance.sendmail.assert_called_once()
        instance.quit.assert_called_once()

    # Tests auth error returns false.
    def test_auth_error_returns_false(self, sender):
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad creds")
            result = sender.send_email("to@x.com", "s", "b")
        assert result is False

    # Tests recipients refused returns false.
    def test_recipients_refused_returns_false(self, sender):
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.sendmail.side_effect = smtplib.SMTPRecipientsRefused({"to@x.com": (550, b"no")})
            result = sender.send_email("to@x.com", "s", "b")
        assert result is False

    # Tests connect failure returns false.
    def test_connect_failure_returns_false(self, sender):
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("down")):
            result = sender.send_email("to@x.com", "s", "b")
        assert result is False


class TestBulkEmailsEP:
    # Tests bulk empty list never calls smtp.
    def test_bulk_empty_list_never_calls_smtp(self, sender, capsys):
        with patch("smtplib.SMTP") as mock_smtp:
            sender.send_bulk_emails([], "s", "b")
        mock_smtp.assert_not_called()
        assert "0/0" in capsys.readouterr().out

    # Tests bulk all succeed.
    def test_bulk_all_succeed(self, sender, capsys):
        with patch("smtplib.SMTP"):
            sender.send_bulk_emails(["a@a", "b@b", "c@c"], "s", "b")
        assert "3/3" in capsys.readouterr().out

    # Tests bulk partial failure.
    def test_bulk_partial_failure(self, sender, capsys):
        call_count = {"n": 0}

        # Defines the side_effect helper.
        def _side_effect(server, port):
            call_count["n"] += 1
            instance = MagicMock()
            if call_count["n"] == 2:
                instance.sendmail.side_effect = smtplib.SMTPException("fail")
            return instance
        with patch("smtplib.SMTP", side_effect=_side_effect):
            sender.send_bulk_emails(["a@a", "b@b", "c@c"], "s", "b")
        assert "2/3" in capsys.readouterr().out


class TestBoundaries:
    # Tests single recipient bulk.
    def test_single_recipient_bulk(self, sender, capsys):
        with patch("smtplib.SMTP"):
            sender.send_bulk_emails(["one@x.com"], "s", "b")
        assert "1/1" in capsys.readouterr().out

    # Tests empty subject and body still sent.
    def test_empty_subject_and_body_still_sent(self, sender):
        with patch("smtplib.SMTP") as mock_smtp:
            result = sender.send_email("to@x.com", "", "")
        assert result is True
        mock_smtp.return_value.sendmail.assert_called_once()


class TestErrorGuessing:
    # Tests attachment missing path is silently skipped.
    def test_attachment_missing_path_is_silently_skipped(self, sender):
        with patch("smtplib.SMTP") as mock_smtp:
            result = sender.send_email(
                "to@x.com", "s", "b", attachments=["/tmp/does_not_exist_xyz.pdf"]
            )
        assert result is True
        mock_smtp.return_value.sendmail.assert_called_once()

    # Tests attachment existing path is included.
    def test_attachment_existing_path_is_included(self, sender, tmp_path):
        attach = tmp_path / "a.txt"
        attach.write_text("hello")
        with patch("smtplib.SMTP") as mock_smtp:
            sender.send_email("to@x.com", "s", "b", attachments=[str(attach)])
        sent_payload = mock_smtp.return_value.sendmail.call_args.args[2]
        assert "a.txt" in sent_payload

    # Tests empty recipient still calls smtp.
    def test_empty_recipient_still_calls_smtp(self, sender):
        with patch("smtplib.SMTP") as mock_smtp:
            result = sender.send_email("", "s", "b")
        assert result is True
        mock_smtp.return_value.sendmail.assert_called_once()

    # Tests config missing required key returns false.
    def test_config_missing_required_key_returns_false(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"smtp_server": "x", "smtp_port": 25}))
        s = EmailSender(config_file=str(f))
        with patch("smtplib.SMTP"):
            result = s.send_email("to@x.com", "s", "b")
        assert result is False

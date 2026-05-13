"""Unit tests for the email service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_send_verification_email_success():
    from src.services.email import send_verification_email

    mock_send = MagicMock()
    with (
        patch("src.services.email.resend.Emails.send", mock_send),
        patch("src.services.email.settings") as mock_settings,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_settings.frontend_url = "https://app.turboman.io"
        mock_settings.email_from = "Turboman <noreply@turboman.io>"

        result = send_verification_email("user@example.com", "Alice", "tok123")

    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == "user@example.com"
    assert "tok123" in call_args["html"]
    assert "https://app.turboman.io/verify-email?token=tok123" in call_args["html"]
    assert "Alice" in call_args["html"]


def test_send_verification_email_failure_returns_false():
    from src.services.email import send_verification_email

    with (
        patch("src.services.email.resend.Emails.send", side_effect=Exception("API error")),
        patch("src.services.email.settings") as mock_settings,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_settings.frontend_url = "https://app.turboman.io"
        mock_settings.email_from = "Turboman <noreply@turboman.io>"

        result = send_verification_email("user@example.com", "Alice", "tok123")

    assert result is False


def test_verify_url_uses_frontend_url():
    from src.services.email import send_verification_email

    captured = {}

    def capture(payload):
        captured["html"] = payload["html"]

    with (
        patch("src.services.email.resend.Emails.send", side_effect=capture),
        patch("src.services.email.settings") as mock_settings,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_settings.frontend_url = "https://custom.domain.com"
        mock_settings.email_from = "Test <no-reply@custom.domain.com>"

        send_verification_email("x@x.com", "Bob", "abc")

    assert "https://custom.domain.com/verify-email?token=abc" in captured["html"]

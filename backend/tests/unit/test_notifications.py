"""Unit tests for the SMS notifications service."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_sms_success():
    from src.services.notifications import send_sms

    mock_create = MagicMock()
    with patch("src.services.notifications._client") as mock_client:
        mock_client.messages.create = mock_create
        result = await send_sms("+15555550001", "Hello!", "+15555550000")

    assert result is True
    mock_create.assert_called_once_with(
        body="Hello!",
        from_="+15555550000",
        to="+15555550001",
    )


@pytest.mark.asyncio
async def test_send_sms_twilio_failure_returns_false():
    from src.services.notifications import send_sms

    with patch("src.services.notifications._client") as mock_client:
        mock_client.messages.create = MagicMock(side_effect=Exception("Twilio error"))
        result = await send_sms("+15555550001", "Hello!", "+15555550000")

    assert result is False


@pytest.mark.asyncio
async def test_send_sms_never_raises():
    from src.services.notifications import send_sms

    with patch("src.services.notifications._client") as mock_client:
        mock_client.messages.create = MagicMock(side_effect=RuntimeError("boom"))
        # Should not raise
        result = await send_sms("+15555550001", "Hello!", "+15555550000")

    assert result is False


@pytest.mark.asyncio
async def test_send_confirmation_sms_delegates_to_send_sms():
    from src.services.notifications import send_confirmation_sms

    with patch("src.services.notifications.send_sms", new_callable=AsyncMock) as mock_sms:
        mock_sms.return_value = True
        await send_confirmation_sms("+15555550001", "Confirmed!", "+15555550000")

    mock_sms.assert_awaited_once_with("+15555550001", "Confirmed!", "+15555550000")

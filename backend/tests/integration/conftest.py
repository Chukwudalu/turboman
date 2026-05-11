"""Shared fixtures for integration tests that make HTTP requests to the app."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def http_client():
    """FastAPI test client with mocked Redis and background poller.

    Twilio signature validation is skipped because settings.env defaults to
    'development', so no X-Twilio-Signature header is needed in tests.
    """
    from main import app

    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch("main.aioredis.from_url", return_value=mock_redis),
        patch("main._poll_pending_notifications", new_callable=AsyncMock),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client

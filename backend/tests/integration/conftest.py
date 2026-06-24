"""Shared fixtures for integration tests that make HTTP requests to the app."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


class _AsyncChainMock(MagicMock):
    """A MagicMock whose .execute() is always async.

    Every attribute/call that would return a child MagicMock instead returns
    another _AsyncChainMock, so .execute() works at any depth.
    """

    def _get_child_mock(self, /, **kwargs):
        # Ensure children are also _AsyncChainMock so the chain propagates.
        # Exception: 'execute' should be AsyncMock.
        name = kwargs.get("name", "")
        if name == "execute":
            return AsyncMock(**kwargs)
        return _AsyncChainMock(**kwargs)


def make_async_db_mock():
    """Create a MagicMock for db where .execute() is always async."""
    return _AsyncChainMock()


@pytest_asyncio.fixture
async def http_client():
    """FastAPI test client with mocked Redis and background poller.

    Twilio signature validation is skipped because settings.env defaults to
    'development', so no X-Twilio-Signature header is needed in tests.
    """
    from main import app

    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)
    mock_redis.ping = AsyncMock(return_value=True)

    with (
        patch("main.aioredis.from_url", return_value=mock_redis),
        patch("main._poll_pending_notifications", new_callable=AsyncMock),
    ):
        app.state.redis = mock_redis
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client

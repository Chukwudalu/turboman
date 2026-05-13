"""Root conftest — applies to all tests."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable slowapi rate limiting for all tests so rate-limit counts don't bleed between tests."""
    from src.utils.ratelimit import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True

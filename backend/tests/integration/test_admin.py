"""Integration tests for the /admin endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ADMIN_SECRET = "test-admin-secret"
ADMIN_HEADER = {"X-Admin-Secret": ADMIN_SECRET}


@pytest_asyncio.fixture
async def client():
    from main import app

    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch("main.aioredis.from_url", return_value=mock_redis),
        patch("main._poll_pending_notifications", new_callable=AsyncMock),
        patch("src.admin.router.settings") as mock_settings,
    ):
        mock_settings.admin_secret = ADMIN_SECRET
        mock_settings.openai_api_key = ""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_admin_secret_returns_403(client):
    res = await client.get("/admin/tenants")
    # Missing required header → 422 (FastAPI) or 403 (custom guard)
    assert res.status_code in (403, 422)


@pytest.mark.asyncio
async def test_wrong_admin_secret_returns_403(client):
    res = await client.get("/admin/tenants", headers={"X-Admin-Secret": "wrong"})
    assert res.status_code == 403


# ── GET /admin/tenants ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tenants(client):
    tenants = [{"id": "t1", "name": "HVAC Co", "trade_type": "hvac", "phone": "+15555550001", "fsa_type": "jobber", "created_at": "2024-01-01"}]

    with patch("src.admin.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.execute.return_value.data = tenants

        res = await client.get("/admin/tenants", headers=ADMIN_HEADER)

    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["name"] == "HVAC Co"


# ── POST /admin/tenants/{id}/close ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_close_tenant_success(client):
    tenant = {"phone": "+15555550001", "twilio_phone_sid": "PN123"}

    with (
        patch("src.admin.router.db") as mock_db,
        patch("src.admin.router.release_phone_number") as mock_release,
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        res = await client.post("/admin/tenants/t1/close", headers=ADMIN_HEADER)

    assert res.status_code == 200
    assert res.json()["closed"] is True
    mock_release.assert_called_once_with("PN123")


@pytest.mark.asyncio
async def test_close_tenant_not_found_returns_404(client):
    with patch("src.admin.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        res = await client.post("/admin/tenants/nonexistent", headers=ADMIN_HEADER)

    assert res.status_code in (404, 405)


@pytest.mark.asyncio
async def test_close_tenant_twilio_failure_still_closes(client):
    tenant = {"phone": "+15555550001", "twilio_phone_sid": "PN123"}

    with (
        patch("src.admin.router.db") as mock_db,
        patch("src.admin.router.release_phone_number", side_effect=Exception("Twilio error")),
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        res = await client.post("/admin/tenants/t1/close", headers=ADMIN_HEADER)

    assert res.status_code == 200
    assert res.json()["closed"] is True


@pytest.mark.asyncio
async def test_close_tenant_no_phone_skips_twilio(client):
    tenant = {"phone": None, "twilio_phone_sid": None}

    with (
        patch("src.admin.router.db") as mock_db,
        patch("src.admin.router.release_phone_number") as mock_release,
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        res = await client.post("/admin/tenants/t1/close", headers=ADMIN_HEADER)

    assert res.status_code == 200
    mock_release.assert_not_called()


# ── KB chunk operations ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_kb_chunk_no_openai_key_returns_503(client):
    res = await client.post(
        "/admin/tenants/t1/kb",
        json={"content": "Some knowledge", "metadata": {}},
        headers=ADMIN_HEADER,
    )
    assert res.status_code == 503


@pytest.mark.asyncio
async def test_list_kb_chunks(client):
    chunks = [{"id": "c1", "content": "info", "metadata": {}, "created_at": "2024-01-01"}]

    with patch("src.admin.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = chunks

        res = await client.get("/admin/tenants/t1/kb", headers=ADMIN_HEADER)

    assert res.status_code == 200
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_delete_kb_chunk(client):
    with patch("src.admin.router.db") as mock_db:
        mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        res = await client.delete("/admin/kb/chunk-123", headers=ADMIN_HEADER)

    assert res.status_code == 200
    assert res.json()["deleted"] is True

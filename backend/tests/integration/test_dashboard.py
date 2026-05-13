"""Integration tests for the /dashboard endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    from main import app

    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch("main.aioredis.from_url", return_value=mock_redis),
        patch("main._poll_pending_notifications", new_callable=AsyncMock),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c


def _token(tenant_id="t1", role="owner"):
    from src.auth.router import _make_access_token
    return _make_access_token("owner@example.com", tenant_id, role)


def _auth(tenant_id="t1", role="owner"):
    return {"Authorization": f"Bearer {_token(tenant_id, role)}"}


def _mock_tenant(plan="trial", trial_ends_at=None):
    return {"plan": plan, "trial_ends_at": trial_ends_at}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    res = await client.get("/dashboard/summary?tenant_id=t1")
    # FastAPI ≥0.136 returns 401; older versions returned 403
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_expired_trial_returns_402(client):
    from datetime import datetime, timedelta, timezone

    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    tenant = {"plan": "trial", "trial_ends_at": expired}

    with patch("src.dashboard.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant

        res = await client.get("/dashboard/summary?tenant_id=t1", headers=_auth())

    assert res.status_code == 402


# ── GET /dashboard/summary ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_returns_counts(client):
    tenant = _mock_tenant()
    summary_data = [{"count": 5}]

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = summary_data
            m.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = summary_data
            m.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value.data = summary_data
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/summary?tenant_id=t1", headers=_auth())

    assert res.status_code == 200
    body = res.json()
    assert "calls_today" in body
    assert "open_requests" in body


# ── GET /dashboard/calls ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calls_list_returns_data(client):
    tenant = _mock_tenant()
    calls = [
        {"id": "call-1", "status": "completed", "duration_s": 120, "started_at": "2024-01-01T10:00:00Z",
         "ended_at": "2024-01-01T10:02:00Z", "customers": {"name": "Alice", "phone": "+15555550001"}}
    ]

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                q = MagicMock()
                q.execute.return_value.data = calls
                m.select.return_value.eq.return_value.order.return_value.limit.return_value = q
                m.select.return_value.eq.return_value.order.return_value.limit.return_value.gt.return_value = q
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/calls?tenant_id=t1", headers=_auth())

    assert res.status_code == 200
    assert "data" in res.json()


# ── GET /dashboard/calls/{id} ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_detail_not_found_returns_404(client):
    tenant = _mock_tenant()

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                # get_call uses .eq(id).single().execute() — one eq, then single
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/calls/nonexistent", headers=_auth())

    assert res.status_code == 404


# ── GET /dashboard/service-requests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_service_requests_list(client):
    tenant = _mock_tenant()
    requests = [
        {"id": "sr-1", "service_type": "AC repair", "status": "pending",
         "is_emergency": False, "is_after_hours": False, "next_morning_priority": False,
         "scheduled_date": None, "scheduled_time": None, "address": "123 Main St",
         "notes": None, "channel": "phone", "created_at": "2024-01-01T10:00:00Z",
         "customers": {"name": "Alice", "phone": "+15555550001", "email": None},
         "oncall_dispatches": []}
    ]

    with (
        patch("src.dashboard.router.db") as mock_db,
        patch("src.dashboard.router.list_service_requests", AsyncMock(return_value=(requests, None))),
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant

        res = await client.get("/dashboard/service-requests?tenant_id=t1", headers=_auth())

    assert res.status_code == 200


# ── PATCH /dashboard/service-requests/{id} ───────────────────────────────────

@pytest.mark.asyncio
async def test_update_service_request_status(client):
    tenant = _mock_tenant()
    sr = {"id": "sr-1", "status": "pending", "tenant_id": "t1",
          "customers": {"name": "Alice", "phone": "+15555550001", "email": None},
          "oncall_dispatches": []}

    with (
        patch("src.dashboard.router.db") as mock_db,
        patch("src.dashboard.router.update_service_request", AsyncMock(return_value=sr)),
        patch("src.dashboard.router.get_service_request", AsyncMock(return_value=sr)),
    ):
        def table_side(name):
            m = MagicMock()
            m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            return m

        mock_db.table.side_effect = table_side

        res = await client.patch(
            "/dashboard/service-requests/sr-1",
            json={"status": "in_progress"},
            headers=_auth(),
        )

    assert res.status_code == 200


@pytest.mark.asyncio
async def test_update_service_request_invalid_status_returns_400(client):
    tenant = _mock_tenant()

    with patch("src.dashboard.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant

        res = await client.patch(
            "/dashboard/service-requests/sr-1",
            json={"status": "invalid_status"},
            headers=_auth(),
        )

    assert res.status_code == 400


# ── GET /dashboard/customers ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customers_list(client):
    tenant = _mock_tenant()
    customers = [
        {"id": "c1", "name": "Alice", "phone": "+15555550001",
         "created_at": "2024-01-01T10:00:00Z", "last_call_at": None}
    ]

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                q = MagicMock()
                q.execute.return_value.data = customers
                m.select.return_value.eq.return_value.order.return_value.limit.return_value = q
                m.select.return_value.eq.return_value.order.return_value.limit.return_value.gt.return_value = q
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/customers?tenant_id=t1", headers=_auth())

    assert res.status_code == 200
    assert "data" in res.json()


# ── GET /dashboard/settings ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settings(client):
    tenant = {**_mock_tenant(), "id": "t1", "name": "HVAC Co", "phone": "+15555550001",
              "trial_ends_at": None, "business_hours_start": "09:00",
              "business_hours_end": "17:00", "business_timezone": "America/New_York",
              "oncall_escalation_timeout_minutes": 10, "oncall_notification_method": "both",
              "oncall_fallback_delay_minutes": 5, "escalation_phone": None,
              "escalation_phone_after_hours": None, "cartesia_voice_id": None,
              "kb_about": None, "kb_services": None, "kb_hours_description": None,
              "kb_rate_regular": None, "kb_rate_after_hours": None,
              "kb_rate_maintenance": None, "kb_extra": None}

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/settings?tenant_id=t1", headers=_auth())

    assert res.status_code == 200
    assert res.json()["name"] == "HVAC Co"


# ── GET /dashboard/escalations ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_escalations_list(client):
    tenant = _mock_tenant()
    escalations = [
        {"id": "e1", "status": "pending", "summary": "Leak in kitchen",
         "created_at": "2024-01-01T10:00:00Z", "handled_at": None,
         "customers": {"name": "Alice", "phone": "+15555550001"}}
    ]

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                m.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = escalations
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/escalations", headers=_auth())

    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["status"] == "pending"


# ── PATCH /dashboard/escalations/{id} ────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_escalation_handled(client):
    tenant = _mock_tenant()
    escalation = {"id": "e1", "status": "pending", "tenant_id": "t1"}
    updated = {**escalation, "status": "handled", "handled_at": "2024-01-01T11:00:00Z",
               "customers": {"name": "Alice", "phone": "+15555550001"}, "summary": None,
               "created_at": "2024-01-01T10:00:00Z"}

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            elif name == "escalations":
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [escalation]
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = updated
                m.update.return_value.eq.return_value.execute.return_value.data = [updated]
            return m

        mock_db.table.side_effect = table_side

        res = await client.patch(
            "/dashboard/escalations/e1",
            json={"status": "handled"},
            headers=_auth(),
        )

    assert res.status_code == 200


@pytest.mark.asyncio
async def test_mark_escalation_not_found_returns_404(client):
    tenant = _mock_tenant()

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return m

        mock_db.table.side_effect = table_side

        res = await client.patch(
            "/dashboard/escalations/nonexistent",
            json={"status": "handled"},
            headers=_auth(),
        )

    assert res.status_code == 404


# ── POST /dashboard/close-account ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_close_account_owner_succeeds(client):
    tenant_row = {"phone": "+15555550001", "twilio_phone_sid": "PN123"}

    with (
        patch("src.dashboard.router.db") as mock_db,
        patch("src.services.twilio_provision.release_phone_number", MagicMock()),
    ):
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant_row
                m.update.return_value.eq.return_value.execute.return_value.data = []
            else:
                m.update.return_value.eq.return_value.execute.return_value.data = []
            return m

        mock_db.table.side_effect = table_side

        res = await client.post(
            "/dashboard/close-account",
            headers=_auth(role="owner"),
        )

    assert res.status_code == 200
    assert res.json()["closed"] is True


@pytest.mark.asyncio
async def test_close_account_non_owner_returns_403(client):
    res = await client.post(
        "/dashboard/close-account",
        headers=_auth(role="member"),
    )
    assert res.status_code == 403


# ── GET /dashboard/team ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_team_list(client):
    tenant = _mock_tenant()
    members = [
        {"id": "u1", "email": "owner@example.com", "name": "Alice",
         "role": "owner", "active": True, "created_at": "2024-01-01T00:00:00Z"}
    ]

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                # list_team uses .eq(...).order(...).execute()
                m.select.return_value.eq.return_value.order.return_value.execute.return_value.data = members
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/team?tenant_id=t1", headers=_auth())

    assert res.status_code == 200
    assert len(res.json()) == 1


# ── GET /dashboard/kb ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kb_chunks_list(client):
    tenant = _mock_tenant()
    chunks = [
        {"id": "c1", "content": "We offer HVAC services.", "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}
    ]

    with patch("src.dashboard.router.db") as mock_db:
        def table_side(name):
            m = MagicMock()
            if name == "tenants":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
            else:
                q = MagicMock()
                q.execute.return_value.data = chunks
                m.select.return_value.eq.return_value.order.return_value.limit.return_value = q
                m.select.return_value.eq.return_value.order.return_value.limit.return_value.gt.return_value = q
            return m

        mock_db.table.side_effect = table_side

        res = await client.get("/dashboard/kb?tenant_id=t1", headers=_auth())

    assert res.status_code == 200
    assert "data" in res.json()


@pytest.mark.asyncio
async def test_kb_upload_no_openai_key_returns_503(client):
    tenant = _mock_tenant()

    with (
        patch("src.dashboard.router.db") as mock_db,
        patch("src.dashboard.router.settings") as mock_settings,
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = tenant
        mock_settings.openai_api_key = ""

        res = await client.post(
            "/dashboard/kb/upload?tenant_id=t1",
            files={"file": ("test.txt", b"some content", "text/plain")},
            headers=_auth(),
        )

    assert res.status_code == 503


# ── GET /dashboard/health ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

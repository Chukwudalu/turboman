"""Integration tests for the /auth endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ── shared fixtures ───────────────────────────────────────────────────────────

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


def _make_user(
    email="owner@example.com",
    password_hash=None,
    tenant_id="tenant-uuid-1",
    role="owner",
    active=True,
    email_verified=True,
):
    import bcrypt
    if password_hash is None:
        password_hash = bcrypt.hashpw(b"Secure@123", bcrypt.gensalt()).decode()
    return {
        "id": "user-uuid-1",
        "email": email,
        "password_hash": password_hash,
        "tenant_id": tenant_id,
        "role": role,
        "active": active,
        "email_verified": email_verified,
    }


# ── POST /auth/register ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    tenant = {"id": "t1", "name": "Smith HVAC", "trade_type": "hvac", "plan": "trial", "trial_ends_at": None}
    user = {"id": "u1", "email": "owner@smithhvac.com"}

    with (
        patch("src.auth.router.db") as mock_db,
        patch("src.auth.router.provision_phone_number", side_effect=Exception("skip")),
        patch("src.services.email.send_verification_email", return_value=True),
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [tenant, user]

        res = await client.post("/auth/register", json={
            "company_name": "Smith HVAC",
            "trade_type": "hvac",
            "name": "John Smith",
            "email": "owner@smithhvac.com",
            "password": "Secure@123",
        })

    assert res.status_code == 201
    assert "message" in res.json()


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client):
    res = await client.post("/auth/register", json={
        "company_name": "Test Co",
        "trade_type": "hvac",
        "name": "Test User",
        "email": "test@test.com",
        "password": "weakpass",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client):
    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "existing-user"}
        ]
        res = await client.post("/auth/register", json={
            "company_name": "Test Co",
            "trade_type": "hvac",
            "name": "Test User",
            "email": "existing@test.com",
            "password": "Secure@123",
        })
    assert res.status_code == 409


# ── POST /auth/token ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client):
    user = _make_user()

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{"token": "rt"}]

        res = await client.post("/auth/token", json={
            "email": "owner@example.com",
            "password": "Secure@123",
        })

    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    user = _make_user()

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        res = await client.post("/auth/token", json={
            "email": "owner@example.com",
            "password": "WrongPass@1",
        })

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client):
    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        res = await client.post("/auth/token", json={
            "email": "nobody@example.com",
            "password": "Secure@123",
        })

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unverified_email_returns_403(client):
    user = _make_user(email_verified=False)

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        res = await client.post("/auth/token", json={
            "email": "owner@example.com",
            "password": "Secure@123",
        })

    assert res.status_code == 403
    assert "verify" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401(client):
    user = _make_user(active=False)

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        res = await client.post("/auth/token", json={
            "email": "owner@example.com",
            "password": "Secure@123",
        })

    assert res.status_code == 401


# ── GET /auth/verify-email ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_email_success(client):
    user = {"id": "u1", "email_verified": False}

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [user]

        res = await client.get("/auth/verify-email?token=valid-token-abc")

    assert res.status_code == 200
    assert "verified" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_verify_email_invalid_token_returns_400(client):
    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        res = await client.get("/auth/verify-email?token=bad-token")

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_already_verified(client):
    user = {"id": "u1", "email_verified": True}

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        res = await client.get("/auth/verify-email?token=used-token")

    assert res.status_code == 200
    assert "already" in res.json()["message"].lower()


# ── POST /auth/refresh ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_valid_token(client):
    from datetime import datetime, timedelta, timezone
    row = {
        "token": "rt-valid",
        "user_email": "owner@example.com",
        "tenant_id": "t1",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "revoked": False,
    }
    user = {"role": "owner"}

    with patch("src.auth.router.db") as mock_db:
        def table_side_effect(name):
            m = MagicMock()
            if name == "refresh_tokens":
                m.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [row]
            elif name == "users":
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = user
            m.insert.return_value.execute.return_value.data = [{"token": "new-rt"}]
            return m

        mock_db.table.side_effect = table_side_effect

        res = await client.post("/auth/refresh", json={"refresh_token": "rt-valid"})

    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(client):
    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        res = await client.post("/auth/refresh", json={"refresh_token": "bad-token"})

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_expired_token_returns_401(client):
    from datetime import datetime, timedelta, timezone
    row = {
        "token": "rt-expired",
        "user_email": "owner@example.com",
        "tenant_id": "t1",
        "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "revoked": False,
    }

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [row]

        res = await client.post("/auth/refresh", json={"refresh_token": "rt-expired"})

    assert res.status_code == 401


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_revokes_token(client):
    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

        res = await client.post("/auth/logout", json={"refresh_token": "rt-to-revoke"})

    assert res.status_code == 200
    assert res.json() == {"ok": True}


# ── POST /auth/change-password ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password_success(client):
    import bcrypt
    from src.auth.router import _make_access_token

    user = {
        "id": "u1",
        "password_hash": bcrypt.hashpw(b"OldPass@1", bcrypt.gensalt()).decode(),
    }
    token = _make_access_token("owner@example.com", "t1", "owner")

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = user
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [user]

        res = await client.post(
            "/auth/change-password",
            json={"current_password": "OldPass@1", "new_password": "NewPass@123"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 200
    assert res.json() == {"ok": True}


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_401(client):
    import bcrypt
    from src.auth.router import _make_access_token

    user = {
        "id": "u1",
        "password_hash": bcrypt.hashpw(b"OldPass@1", bcrypt.gensalt()).decode(),
    }
    token = _make_access_token("owner@example.com", "t1", "owner")

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = user

        res = await client.post(
            "/auth/change-password",
            json={"current_password": "WrongPass@1", "new_password": "NewPass@123"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_change_password_weak_new_password_returns_422(client):
    from src.auth.router import _make_access_token

    token = _make_access_token("owner@example.com", "t1", "owner")

    res = await client.post(
        "/auth/change-password",
        json={"current_password": "OldPass@1", "new_password": "weak"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_change_password_no_token_returns_403(client):
    res = await client.post(
        "/auth/change-password",
        json={"current_password": "OldPass@1", "new_password": "NewPass@123"},
    )
    assert res.status_code in (401, 403)


# ── POST /auth/invite ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_by_owner_succeeds(client):
    from src.auth.router import _make_access_token

    token = _make_access_token("owner@example.com", "t1", "owner")
    new_user = {"id": "u2", "email": "member@example.com", "name": "Jane", "role": "member", "tenant_id": "t1"}

    with patch("src.auth.router.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [new_user]

        res = await client.post(
            "/auth/invite",
            json={"email": "member@example.com", "name": "Jane", "role": "member"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 201
    assert "temp_password" in res.json()


@pytest.mark.asyncio
async def test_invite_by_member_returns_403(client):
    from src.auth.router import _make_access_token

    token = _make_access_token("member@example.com", "t1", "member")

    res = await client.post(
        "/auth/invite",
        json={"email": "new@example.com", "name": "New", "role": "member"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 403


@pytest.mark.asyncio
async def test_invite_invalid_role_returns_422(client):
    from src.auth.router import _make_access_token

    token = _make_access_token("owner@example.com", "t1", "owner")

    res = await client.post(
        "/auth/invite",
        json={"email": "new@example.com", "name": "New", "role": "superuser"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 422

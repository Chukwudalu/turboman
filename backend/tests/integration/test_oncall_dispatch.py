"""
Integration tests for the on-call dispatch service.

Tests exercise trigger_oncall_dispatch and try_next_tech, mocking all DB
calls and the Twilio client so no network traffic is produced.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.integration.conftest import _AsyncChainMock


@pytest.fixture(autouse=True)
def mock_get_tenant_phone():
    """Prevent _get_tenant_phone from hitting the real DB in every test."""
    with patch(
        "src.services.oncall_dispatch._get_tenant_phone",
        AsyncMock(return_value="+15555550000"),
    ):
        yield


# ── fixtures ──────────────────────────────────────────────────────────────────

TECH_1 = {"id": "tech-1", "name": "Alice", "phone": "+15555550001", "role": "tech", "tenant_id": "t1"}
TECH_2 = {"id": "tech-2", "name": "Bob", "phone": "+15555550002", "role": "tech", "tenant_id": "t1"}
MANAGER = {"id": "mgr-1", "name": "Carol", "phone": "+15555550003", "role": "manager", "tenant_id": "t1"}

_DISPATCH = {"id": "d1", "status": "dispatching"}
_CTX = {
    "tenant_id": "t1",
    "service_type": "AC repair",
    "address": "123 Main St",
    "customer_phone": "+15555550099",
    "notification_method": "sms",
    "is_emergency": True,
    "timeout_minutes": 10,
    "fallback_delay_minutes": 5,
    "customer_fallback_message": None,
    "customer_tech_accepted_message": None,
    "customer_manager_accepted_message": None,
    "voice_timeout_minutes": 5,
    "sms_timeout_minutes": 10,
    "tenant_phone": "+15555550000",
}


# ── trigger_oncall_dispatch ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_dispatches_to_first_tech():
    """With techs available, the dispatch goes to the first tech in the list."""
    dispatch = {"id": "d1"}

    with (
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(return_value=[TECH_1, TECH_2]),
        ),
        patch(
            "src.services.oncall_dispatch.create_dispatch",
            AsyncMock(return_value=dispatch),
        ),
        patch(
            "src.services.oncall_dispatch._dispatch_to_contact", AsyncMock()
        ) as mock_dispatch,
    ):
        from src.services.oncall_dispatch import trigger_oncall_dispatch

        await trigger_oncall_dispatch(
            tenant_id="t1",
            service_request_id="sr-1",
            service_type="AC repair",
            address="123 Main St",
            customer_phone="+15555550099",
            notification_method="sms",
            is_emergency=True,
        )

    mock_dispatch.assert_awaited_once()
    assert mock_dispatch.call_args.args[1] == TECH_1


@pytest.mark.asyncio
async def test_trigger_escalates_to_manager_when_no_techs():
    """No techs configured -> dispatch goes directly to the first manager."""
    dispatch = {"id": "d1"}

    with (
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(side_effect=[[], [MANAGER]]),
        ),
        patch(
            "src.services.oncall_dispatch.create_dispatch",
            AsyncMock(return_value=dispatch),
        ),
        patch(
            "src.services.oncall_dispatch._dispatch_to_contact", AsyncMock()
        ) as mock_dispatch,
    ):
        from src.services.oncall_dispatch import trigger_oncall_dispatch

        await trigger_oncall_dispatch(
            tenant_id="t1",
            service_request_id="sr-1",
            service_type="AC repair",
            address=None,
            customer_phone=None,
            notification_method="sms",
            is_emergency=True,
        )

    mock_dispatch.assert_awaited_once()
    assert mock_dispatch.call_args.args[1] == MANAGER


@pytest.mark.asyncio
async def test_trigger_no_contacts_skips_dispatch():
    """No techs and no managers -> no dispatch created, no notification sent."""
    with (
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(side_effect=[[], []]),
        ),
        patch(
            "src.services.oncall_dispatch.create_dispatch", AsyncMock()
        ) as mock_create,
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {}

        from src.services.oncall_dispatch import trigger_oncall_dispatch

        await trigger_oncall_dispatch(
            tenant_id="t1",
            service_request_id="sr-1",
            service_type="AC repair",
            address=None,
            customer_phone=None,
            notification_method="sms",
            is_emergency=True,
        )

    mock_create.assert_not_awaited()


# ── try_next_tech ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_try_next_tech_moves_to_next_in_list():
    """Current tech unavailable -> dispatches to the next tech in the role group."""
    with (
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
        patch("src.services.oncall_dispatch.get_dispatch_context", AsyncMock(return_value=_CTX)),
        patch("src.services.oncall_dispatch.get_tech_by_id", AsyncMock(return_value=TECH_1)),
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(return_value=[TECH_1, TECH_2]),
        ),
        patch(
            "src.services.oncall_dispatch._dispatch_to_contact", AsyncMock()
        ) as mock_dispatch,
    ):
        # Atomic claim succeeds
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [_DISPATCH]

        from src.services.oncall_dispatch import try_next_tech

        await try_next_tech("d1", "tech-1", declined=False)

    mock_dispatch.assert_awaited_once()
    assert mock_dispatch.call_args.args[1] == TECH_2


@pytest.mark.asyncio
async def test_try_next_tech_escalates_to_managers_after_last_tech():
    """Last tech in list exhausted -> escalates to first manager."""
    with (
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
        patch("src.services.oncall_dispatch.get_dispatch_context", AsyncMock(return_value=_CTX)),
        patch("src.services.oncall_dispatch.get_tech_by_id", AsyncMock(return_value=TECH_2)),
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(side_effect=[[TECH_1, TECH_2], [MANAGER]]),
        ),
        patch(
            "src.services.oncall_dispatch._dispatch_to_contact", AsyncMock()
        ) as mock_dispatch,
    ):
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [_DISPATCH]

        from src.services.oncall_dispatch import try_next_tech

        await try_next_tech("d1", "tech-2", declined=False)

    mock_dispatch.assert_awaited_once()
    assert mock_dispatch.call_args.args[1] == MANAGER


@pytest.mark.asyncio
async def test_try_next_tech_exhausts_all_calls_exhaust_dispatch():
    """Last manager exhausted -> _exhaust_dispatch called with any_declined flag."""
    with (
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
        patch("src.services.oncall_dispatch.get_dispatch_context", AsyncMock(return_value=_CTX)),
        patch("src.services.oncall_dispatch.get_tech_by_id", AsyncMock(return_value=MANAGER)),
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(return_value=[MANAGER]),
        ),
        patch(
            "src.services.oncall_dispatch._exhaust_dispatch", AsyncMock()
        ) as mock_exhaust,
    ):
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [_DISPATCH]

        from src.services.oncall_dispatch import try_next_tech

        await try_next_tech("d1", "mgr-1", declined=True)

    mock_exhaust.assert_awaited_once()
    assert mock_exhaust.call_args.kwargs.get("any_declined") is True


@pytest.mark.asyncio
async def test_try_next_tech_no_managers_exhausts_from_techs():
    """All techs exhausted and no managers -> _exhaust_dispatch called."""
    ctx_no_mgr = {**_CTX, "notification_method": "sms"}

    with (
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
        patch("src.services.oncall_dispatch.get_dispatch_context", AsyncMock(return_value=ctx_no_mgr)),
        patch("src.services.oncall_dispatch.get_tech_by_id", AsyncMock(return_value=TECH_1)),
        patch(
            "src.services.oncall_dispatch.list_oncall_technicians",
            AsyncMock(side_effect=[[TECH_1], []]),
        ),
        patch(
            "src.services.oncall_dispatch._exhaust_dispatch", AsyncMock()
        ) as mock_exhaust,
    ):
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [_DISPATCH]

        from src.services.oncall_dispatch import try_next_tech

        await try_next_tech("d1", "tech-1", declined=False)

    mock_exhaust.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_next_tech_skips_if_dispatch_not_active():
    """Dispatch already resolved -> no escalation, no notification."""
    with (
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
        patch(
            "src.services.oncall_dispatch._dispatch_to_contact", AsyncMock()
        ) as mock_dispatch,
    ):
        # Atomic claim fails (dispatch not in dispatching state)
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        from src.services.oncall_dispatch import try_next_tech

        await try_next_tech("d1", "tech-1")

    mock_dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_try_next_tech_skips_if_dispatch_missing():
    """Dispatch ID not found -> graceful no-op."""
    with (
        patch("src.services.oncall_dispatch.db", new_callable=_AsyncChainMock) as mock_db,
        patch(
            "src.services.oncall_dispatch._dispatch_to_contact", AsyncMock()
        ) as mock_dispatch,
    ):
        # Atomic claim fails (no matching row)
        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        from src.services.oncall_dispatch import try_next_tech

        await try_next_tech("bad-id", "tech-1")

    mock_dispatch.assert_not_awaited()

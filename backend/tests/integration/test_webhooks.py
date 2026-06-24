"""
Integration tests for Twilio webhook endpoints (main.py).

All DB and external-service calls are mocked.  Twilio signature validation is
skipped because settings.env defaults to 'development'.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.integration.conftest import _AsyncChainMock


# ── helpers ───────────────────────────────────────────────────────────────────


def _parse(text: str) -> ET.Element:
    """Strip XML declaration and parse TwiML into an Element tree."""
    if text.lstrip().startswith("<?xml"):
        text = text[text.index("?>") + 2 :].strip()
    return ET.fromstring(text)


# ── /incoming-call ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_incoming_call_regular_caller_gets_ai_stream(http_client):
    """Unknown caller -> WebSocket <Stream> TwiML for the AI agent."""
    with patch("main.db", new_callable=_AsyncChainMock) as mock_db:
        # Tenant lookup by phone
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "t1"}]
        # Tech lookup: not a tech (3 .eq() calls: phone, tenant_id, active)
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        resp = await http_client.post(
            "/incoming-call",
            data={"From": "+15555550001", "To": "+15551234567"},
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    connect = root.find("Connect")
    assert connect is not None, "Expected <Connect> in TwiML"
    stream = connect.find("Stream")
    assert stream is not None
    assert "call-stream" in stream.get("url", "")


@pytest.mark.asyncio
async def test_incoming_call_known_tech_redirects_to_callback(http_client):
    """Active on-call tech calling in -> <Redirect> to /oncall-callback."""
    with patch("main.db", new_callable=_AsyncChainMock) as mock_db, patch("main.settings") as mock_settings:
        mock_settings.env = "development"
        mock_settings.base_url = "https://example.com"
        # Tenant lookup
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "t1"}]
        # Tech lookup: is a tech
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "tech-abc"}]

        resp = await http_client.post(
            "/incoming-call",
            data={"From": "+15555550002", "To": "+15551234567"},
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    redirect = root.find("Redirect")
    assert redirect is not None, "Expected <Redirect> in TwiML"
    assert "oncall-callback" in (redirect.text or "")
    assert "tech-abc" in (redirect.text or "")


# ── /oncall-call-start ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_oncall_call_start_active_dispatch_greets_tech(http_client):
    """Active dispatch for a tech -> <Gather> with personalised greeting."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "company_name": "Acme HVAC",
        "service_type": "AC repair",
        "address": "123 Main St",
        "is_emergency": True,
        "customer_phone": "+15555550003",
        "customer_name": "Alice",
        "tenant_phone": "+15555550000",
    }
    tech = {"name": "Bob Smith", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.cancel_dispatch_timeouts", AsyncMock()),
        patch("main.settings") as mock_settings,
    ):
        mock_settings.env = "development"
        mock_settings.base_url = "https://example.com"

        resp = await http_client.post(
            "/oncall-call-start?dispatch_id=d1&tech_id=tech-1"
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    gather = root.find("Gather")
    assert gather is not None, "Expected <Gather> in TwiML"
    say_text = gather.find("Say").text
    assert "Bob" in say_text
    assert "Acme HVAC" in say_text


@pytest.mark.asyncio
async def test_oncall_call_start_already_handled_hangs_up(http_client):
    """Dispatch already acknowledged -> 'already been handled' message."""
    ctx = {"dispatch_status": "acknowledged", "tenant_id": "t1"}
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
    ):
        resp = await http_client.post(
            "/oncall-call-start?dispatch_id=d1&tech_id=tech-1"
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    say = root.find("Say")
    assert say is not None
    assert "already been handled" in say.text


@pytest.mark.asyncio
async def test_oncall_call_start_missing_context_hangs_up(http_client):
    """No dispatch context (bad ID) -> graceful hangup, no crash."""
    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=None)),
        patch("main.get_tech_by_id", AsyncMock(return_value={"name": "X", "role": "tech", "tenant_id": "t1"})),
    ):
        resp = await http_client.post(
            "/oncall-call-start?dispatch_id=bad&tech_id=bad"
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    assert root.find("Say") is not None or root.find("Hangup") is not None


# ── /oncall-call-response ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_oncall_call_response_yes_asks_for_eta(http_client):
    """Tech says yes -> <Gather> pointed at /oncall-call-eta."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "company_name": "Acme HVAC",
        "service_type": "AC repair",
        "address": "123 Main St",
        "is_emergency": True,
        "customer_phone": "+15555550003",
        "customer_name": "Alice",
        "tenant_phone": "+15555550000",
        "customer_fallback_message": None,
        "customer_tech_accepted_message": None,
        "customer_manager_accepted_message": None,
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.settings") as mock_settings,
    ):
        mock_settings.env = "development"
        mock_settings.base_url = "https://example.com"

        resp = await http_client.post(
            "/oncall-call-response?dispatch_id=d1&tech_id=tech-1",
            data={"SpeechResult": "yes I can make it"},
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    gather = root.find("Gather")
    assert gather is not None
    assert "oncall-call-eta" in gather.get("action", "")


@pytest.mark.asyncio
async def test_oncall_call_response_no_triggers_escalation(http_client):
    """Tech says no -> create_task called with try_next_tech, hangup TwiML."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "company_name": "Acme HVAC",
        "service_type": "AC repair",
        "address": "123 Main St",
        "is_emergency": True,
        "customer_phone": "+15555550003",
        "customer_name": "Alice",
        "tenant_phone": "+15555550000",
        "customer_fallback_message": None,
        "customer_tech_accepted_message": None,
        "customer_manager_accepted_message": None,
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.asyncio") as mock_asyncio,
        patch("main.settings") as mock_settings,
    ):
        mock_settings.env = "development"
        mock_settings.base_url = "https://example.com"

        resp = await http_client.post(
            "/oncall-call-response?dispatch_id=d1&tech_id=tech-1",
            data={"SpeechResult": "no I'm busy tonight"},
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    assert root.find("Hangup") is not None
    mock_asyncio.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_oncall_call_response_no_speech_triggers_escalation(http_client):
    """no_input=1 (no speech captured) -> treated as declined, hangup."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "company_name": "Acme HVAC",
        "service_type": "AC repair",
        "address": "123 Main St",
        "is_emergency": True,
        "customer_phone": "+15555550003",
        "customer_name": "Alice",
        "tenant_phone": "+15555550000",
        "customer_fallback_message": None,
        "customer_tech_accepted_message": None,
        "customer_manager_accepted_message": None,
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.asyncio") as mock_asyncio,
        patch("main.settings") as mock_settings,
    ):
        mock_settings.env = "development"
        mock_settings.base_url = "https://example.com"

        resp = await http_client.post(
            "/oncall-call-response?dispatch_id=d1&tech_id=tech-1&no_input=1",
            data={},
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    assert root.find("Hangup") is not None
    mock_asyncio.create_task.assert_called_once()


# ── /oncall-call-eta ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_oncall_call_eta_acknowledges_and_texts_customer(http_client):
    """Tech gives ETA -> dispatch acknowledged, customer SMS queued."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "service_type": "AC repair",
        "customer_phone": "+15555550009",
        "customer_name": "Alice",
        "tenant_phone": "+15555550000",
        "customer_tech_accepted_message": None,
        "customer_manager_accepted_message": None,
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.acknowledge_dispatch", AsyncMock()) as mock_ack,
        patch("main.send_sms", AsyncMock()) as mock_sms,
    ):
        resp = await http_client.post(
            "/oncall-call-eta?dispatch_id=d1&tech_id=tech-1",
            data={"SpeechResult": "30 minutes"},
        )

    assert resp.status_code == 200
    root = _parse(resp.text)
    assert root.find("Hangup") is not None
    mock_ack.assert_awaited_once_with("d1", eta_text="30 minutes", tech_id="tech-1")
    mock_sms.assert_awaited_once()
    sms_body = mock_sms.call_args.args[1]
    assert "30 minutes" in sms_body


@pytest.mark.asyncio
async def test_oncall_call_eta_no_customer_phone_skips_sms(http_client):
    """No customer phone on record -> dispatch acknowledged, no SMS sent."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "service_type": "AC repair",
        "customer_phone": None,
        "customer_name": None,
        "tenant_phone": "+15555550000",
        "customer_tech_accepted_message": None,
        "customer_manager_accepted_message": None,
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.acknowledge_dispatch", AsyncMock()),
        patch("main.send_sms", AsyncMock()) as mock_sms,
    ):
        resp = await http_client.post(
            "/oncall-call-eta?dispatch_id=d1&tech_id=tech-1",
            data={"SpeechResult": "1 hour"},
        )

    assert resp.status_code == 200
    mock_sms.assert_not_awaited()


# ── /oncall-call-status ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_oncall_call_status_busy_escalates(http_client):
    """CallStatus=busy on an active dispatch -> escalation task created immediately."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "service_type": "AC repair",
        "customer_phone": None,
        "tenant_phone": "+15555550000",
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.asyncio") as mock_asyncio,
    ):
        resp = await http_client.post(
            "/oncall-call-status?dispatch_id=d1&tech_id=tech-1",
            data={"CallStatus": "busy"},
        )

    assert resp.status_code == 204
    mock_asyncio.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_oncall_call_status_no_answer_does_not_escalate(http_client):
    """CallStatus=no-answer -> no immediate escalation (waits for callback/timeout)."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "service_type": "AC repair",
        "customer_phone": None,
        "tenant_phone": "+15555550000",
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.asyncio") as mock_asyncio,
    ):
        resp = await http_client.post(
            "/oncall-call-status?dispatch_id=d1&tech_id=tech-1",
            data={"CallStatus": "no-answer"},
        )

    assert resp.status_code == 204
    mock_asyncio.create_task.assert_not_called()


@pytest.mark.asyncio
async def test_oncall_call_status_completed_no_escalation(http_client):
    """CallStatus=completed -> no escalation task created."""
    ctx = {
        "dispatch_status": "dispatching",
        "tenant_id": "t1",
        "service_type": "AC repair",
        "customer_phone": None,
        "tenant_phone": "+15555550000",
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.asyncio") as mock_asyncio,
    ):
        resp = await http_client.post(
            "/oncall-call-status?dispatch_id=d1&tech_id=tech-1",
            data={"CallStatus": "completed"},
        )

    assert resp.status_code == 204
    mock_asyncio.create_task.assert_not_called()


@pytest.mark.asyncio
async def test_oncall_call_status_no_answer_already_acknowledged(http_client):
    """no-answer but dispatch already resolved -> no escalation."""
    ctx = {
        "dispatch_status": "acknowledged",
        "tenant_id": "t1",
        "service_type": "AC repair",
        "customer_phone": None,
        "tenant_phone": "+15555550000",
    }
    tech = {"name": "Bob", "role": "tech", "tenant_id": "t1"}

    with (
        patch("main.get_dispatch_context", AsyncMock(return_value=ctx)),
        patch("main.get_tech_by_id", AsyncMock(return_value=tech)),
        patch("main.asyncio") as mock_asyncio,
    ):
        resp = await http_client.post(
            "/oncall-call-status?dispatch_id=d1&tech_id=tech-1",
            data={"CallStatus": "no-answer"},
        )

    assert resp.status_code == 204
    mock_asyncio.create_task.assert_not_called()


# ── /sms-incoming ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sms_incoming_known_tech_acknowledges_dispatch(http_client):
    """SMS from a known active tech -> dispatch acknowledged for their tenant."""
    with (
        patch("main.db", new_callable=_AsyncChainMock) as mock_db,
        patch(
            "main.acknowledge_dispatch_for_tenant", AsyncMock(return_value=True)
        ) as mock_ack,
        patch("main.get_dispatch_context", AsyncMock(return_value=None)),
    ):
        # Tech lookup: .select("tenant_id").eq("phone", ...).eq("active", True).limit(1).execute()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"tenant_id": "t1"}]
        # Dispatch lookup for cancelling active call
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        resp = await http_client.post(
            "/sms-incoming",
            data={"From": "+15555550004", "Body": "YES"},
        )

    assert resp.status_code == 200
    mock_ack.assert_awaited_once()
    root = _parse(resp.text)
    assert root.tag == "Response"


@pytest.mark.asyncio
async def test_sms_incoming_unknown_sender_no_action(http_client):
    """SMS from an unrecognised number -> no acknowledgment, valid TwiML returned."""
    with (
        patch("main.db", new_callable=_AsyncChainMock) as mock_db,
        patch(
            "main.acknowledge_dispatch_for_tenant", AsyncMock()
        ) as mock_ack,
    ):
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        resp = await http_client.post(
            "/sms-incoming",
            data={"From": "+15559999999", "Body": "hello?"},
        )

    assert resp.status_code == 200
    mock_ack.assert_not_awaited()

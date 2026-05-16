"""
On-call escalation: technicians first, then management escalation contacts.

Chain per role group:
  1. Dispatch to first tech (role='tech') using configured notification method.
  2. If tech is unavailable (no-answer, says no), move to the next tech.
  3. Once all techs are exhausted, escalate to managers (role='manager').
  4. Same escalation through all managers.
  5. If all managers exhausted → customer fallback SMS.

Notification methods:
  'voice' — outbound call only
  'sms'   — SMS only
  'both'  — SMS immediately + outbound call
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import sentry_sdk
from twilio.rest import Client

from src.config import settings
from src.db import db
from src.db.oncall import (
    create_dispatch,
    fail_dispatch,
    get_dispatch,
    get_dispatch_context,
    get_tech_by_id,
    list_oncall_technicians,
    reject_dispatch,
)
from src.services.notifications import send_sms
from src.utils.logger import logger

_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)




async def _get_tenant_phone(tenant_id: str) -> str | None:
    res = db.table("tenants").select("phone").eq("id", tenant_id).single().execute()
    return res.data.get("phone") if res.data else None


async def trigger_oncall_dispatch(
    *,
    tenant_id: str,
    service_request_id: str,
    service_type: str,
    address: str | None,
    customer_phone: str | None,
    notification_method: str = "both",
    is_emergency: bool = True,
) -> None:
    from_phone = await _get_tenant_phone(tenant_id)
    if not from_phone:
        logger.error("Tenant has no provisioned phone number — on-call dispatch aborted", tenant_id=tenant_id)
        return

    techs = await list_oncall_technicians(tenant_id, role="tech")
    if not techs:
        # No techs — try managers directly
        managers = await list_oncall_technicians(tenant_id, role="manager")
        if not managers:
            logger.warning("No on-call contacts configured at all", tenant_id=tenant_id)
            return
        dispatch = await create_dispatch(tenant_id, service_request_id)
        await _dispatch_to_contact(dispatch["id"], managers[0], method=notification_method,
                                   service_type=service_type, address=address, customer_phone=customer_phone,
                                   is_emergency=is_emergency, from_phone=from_phone)
        return

    dispatch = await create_dispatch(tenant_id, service_request_id)
    await _dispatch_to_contact(dispatch["id"], techs[0], method=notification_method,
                               service_type=service_type, address=address, customer_phone=customer_phone,
                               is_emergency=is_emergency, from_phone=from_phone)


async def try_next_tech(dispatch_id: str, current_tech_id: str, *, declined: bool = False) -> None:
    """
    Called by call webhook endpoints when a contact is unavailable.
    declined=True means the tech answered and said no.
    declined=False means the call went unanswered.
    Moves to the next contact in the same role group, escalates to managers,
    or closes the dispatch as rejected/failed.
    """
    dispatch = await get_dispatch(dispatch_id)
    if not dispatch or dispatch["status"] != "dispatching":
        return

    ctx = await get_dispatch_context(dispatch_id)
    if not ctx:
        return

    current_tech = await get_tech_by_id(current_tech_id)
    current_role = current_tech["role"] if current_tech else "tech"
    method = ctx["notification_method"]

    contacts_in_role = await list_oncall_technicians(ctx["tenant_id"], role=current_role)
    current_idx = next((i for i, t in enumerate(contacts_in_role) if t["id"] == current_tech_id), -1)
    next_idx = current_idx + 1

    is_emergency = ctx.get("is_emergency", True)

    fallback_delay = ctx.get("fallback_delay_minutes", 5)

    from_phone = await _get_tenant_phone(ctx["tenant_id"])
    if not from_phone:
        logger.error("Tenant has no provisioned phone number — on-call dispatch aborted", tenant_id=ctx["tenant_id"])
        return

    if next_idx < len(contacts_in_role):
        await _dispatch_to_contact(
            dispatch_id, contacts_in_role[next_idx], method=method,
            service_type=ctx["service_type"], address=ctx["address"],
            customer_phone=ctx["customer_phone"],
            any_declined=declined, is_emergency=is_emergency, from_phone=from_phone,
        )
    elif current_role == "tech":
        managers = await list_oncall_technicians(ctx["tenant_id"], role="manager")
        if managers:
            logger.info("Escalating to management after techs exhausted", dispatch_id=dispatch_id)
            await _dispatch_to_contact(
                dispatch_id, managers[0], method=method,
                service_type=ctx["service_type"], address=ctx["address"],
                customer_phone=ctx["customer_phone"],
                any_declined=declined, is_emergency=is_emergency, from_phone=from_phone,
            )
        else:
            await _exhaust_dispatch(dispatch_id, customer_phone=ctx["customer_phone"], any_declined=declined, delay_minutes=fallback_delay)
    else:
        await _exhaust_dispatch(dispatch_id, customer_phone=ctx["customer_phone"], any_declined=declined, delay_minutes=fallback_delay)


async def _dispatch_to_contact(
    dispatch_id: str,
    tech: dict,
    *,
    method: str,
    service_type: str,
    address: str | None,
    customer_phone: str | None,
    any_declined: bool = False,
    is_emergency: bool = True,
    from_phone: str | None = None,
) -> None:
    effective_method = method or "both"
    address_str = f" at {address}" if address else ""
    customer_str = f" Customer: {customer_phone}." if customer_phone else ""
    role = tech.get("role", "tech")

    logger.info(
        "Contacting on-call tech",
        name=tech["name"], phone=tech["phone"], method=effective_method, dispatch_id=dispatch_id
    )

    notified = False

    if effective_method in ("sms", "both"):
        label = "EMERGENCY" if is_emergency else "AFTER-HOURS SERVICE"
        if role == "manager":
            sms_body = (
                f"ESCALATION — All on-call technicians were unreachable. "
                f"{label}: {service_type}{address_str}.{customer_str} "
                f"Please contact the customer prior to attending to confirm the visit and service. "
                f"Reply YES to acknowledge. (Turboman)"
            )
        else:
            sms_body = (
                f"{label} — {service_type}{address_str}.{customer_str} "
                f"Please contact the customer prior to attending to confirm the visit and service. "
                f"Reply YES to acknowledge, or answer the incoming call. (Turboman)"
            )
        if await send_sms(tech["phone"], sms_body, from_phone=from_phone):
            notified = True

    if effective_method in ("voice", "both"):
        if not settings.base_url:
            logger.warning("BASE_URL not configured — cannot make oncall outbound call")
        else:
            base = settings.base_url.rstrip("/")
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: _client.calls.create(
                        to=tech["phone"],
                        from_=from_phone,
                        url=f"{base}/oncall-call-start?dispatch_id={dispatch_id}&tech_id={tech['id']}",
                        status_callback=f"{base}/oncall-call-status?dispatch_id={dispatch_id}&tech_id={tech['id']}",
                        status_callback_event=["completed"],
                        timeout=30,
                    ),
                )
                logger.info("Oncall call initiated", name=tech["name"], role=role, dispatch_id=dispatch_id)
                notified = True
            except Exception as e:
                logger.error("Failed to initiate oncall call", name=tech["name"], phone=tech["phone"], error=str(e))

    if not notified:
        sentry_sdk.capture_message(
            "Dispatch notification not sent — no SMS or call reached the tech",
            level="error",
            extras={
                "dispatch_id": dispatch_id,
                "tech_name": tech["name"],
                "phone": tech["phone"],
                "method": effective_method,
            },
        )
        logger.error(
            "Dispatch created but NO notification sent — check tech phone format (must be E.164 e.g. +12025551234) "
            "and Twilio account permissions (trial accounts can only reach verified numbers)",
            tech_name=tech["name"],
            phone=tech["phone"],
            method=effective_method,
            dispatch_id=dispatch_id,
        )

    if effective_method == "sms":
        ctx = await get_dispatch_context(dispatch_id)
        timeout = ctx["timeout_minutes"] if ctx else 10
        escalate_at = datetime.now(timezone.utc) + timedelta(minutes=timeout)
        db.table("dispatch_sms_timeouts").insert({
            "dispatch_id": dispatch_id,
            "tech_id": tech["id"],
            "escalate_at": escalate_at.isoformat(),
        }).execute()


async def _exhaust_dispatch(dispatch_id: str, *, customer_phone: str | None, any_declined: bool = False, delay_minutes: int = 5) -> None:
    if any_declined:
        await reject_dispatch(dispatch_id)
        sentry_sdk.capture_message(
            "On-call dispatch rejected — all contacts declined",
            level="error",
            extras={"dispatch_id": dispatch_id},
        )
        logger.warning("All on-call contacts declined the job", dispatch_id=dispatch_id)
    else:
        await fail_dispatch(dispatch_id)
        sentry_sdk.capture_message(
            "On-call dispatch failed — all contacts unreachable",
            level="error",
            extras={"dispatch_id": dispatch_id},
        )
        logger.warning("All on-call contacts were unreachable", dispatch_id=dispatch_id)

    if not customer_phone:
        return

    send_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    db.table("pending_notifications").insert({
        "phone": customer_phone,
        "message": (
            "We were unable to reach our on-call team tonight. "
            "Your request has been logged and our team will contact you first thing next business day."
        ),
        "send_at": send_at.isoformat(),
        "dispatch_id": dispatch_id,
    }).execute()
    logger.info("Fallback SMS scheduled", dispatch_id=dispatch_id, send_at=send_at.isoformat())

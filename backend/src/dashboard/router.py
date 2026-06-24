"""
Dashboard API — read-only views and status updates for the Turboman dashboard.

All routes require  Authorization: Bearer <jwt>  obtained from POST /auth/token.
Returns JSON — consumed by the Next.js frontend dashboard.
"""
from __future__ import annotations

import asyncio
import io
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src.auth.router import decode_token
from src.config import settings
from src.utils.validators import E164Phone
from src.db import db
from src.db.jobs import get_service_request, list_service_requests, update_service_request
from src.db.oncall import (
    create_oncall_technician,
    delete_oncall_technician,
    list_oncall_technicians,
    update_oncall_technician,
)
from src.db.rag import ingest_chunk
from src.services.notifications import send_confirmation_sms
from src.utils.text import split_text

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_bearer = HTTPBearer()


# ── Auth ───────────────────────────────────────────────────────────────────────

async def _get_tenant_id(request: Request, credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Decode the JWT, enforce trial status, and return the tenant_id."""
    payload = decode_token(credentials.credentials)
    tenant_id = payload.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Token has no tenant scope")

    redis = getattr(request.app.state, "redis", None)
    cache_key = f"trial:{tenant_id}"

    if redis:
        cached = await redis.get(cache_key)
        if cached == "expired":
            raise HTTPException(status_code=402, detail="Trial expired. Please upgrade to continue.")
        if cached == "ok":
            return tenant_id

    tenant = await db.table("tenants").select("plan, trial_ends_at").eq("id", tenant_id).single().execute()
    if tenant.data:
        plan = tenant.data.get("plan", "trial")
        trial_ends_at = tenant.data.get("trial_ends_at")
        if plan == "trial" and trial_ends_at:
            expires = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
            if expires < datetime.now(timezone.utc):
                if redis:
                    await redis.set(cache_key, "expired", ex=300)
                raise HTTPException(status_code=402, detail="Trial expired. Please upgrade to continue.")

    if redis:
        await redis.set(cache_key, "ok", ex=300)

    return tenant_id


# ── Summary ────────────────────────────────────────────────────────────────────

@router.get("/summary")
async def summary(tenant_id: str = Depends(_get_tenant_id)):
    """High-level counts for the dashboard header cards."""
    today = datetime.now(timezone.utc).date().isoformat()

    r_calls, r_escalations, r_bookings, r_open = await asyncio.gather(
        db.table("calls").select("id", count="exact").eq("tenant_id", tenant_id).gte("started_at", today).execute(),
        db.table("calls").select("id", count="exact").eq("tenant_id", tenant_id).eq("status", "escalated").gte("started_at", today).execute(),
        db.table("service_requests").select("id", count="exact").eq("tenant_id", tenant_id).gte("created_at", today).execute(),
        db.table("service_requests").select("id", count="exact").eq("tenant_id", tenant_id).in_("status", ["pending", "scheduled", "in_progress"]).execute(),
    )

    return {
        "calls_today": r_calls.count or 0,
        "bookings_today": r_bookings.count or 0,
        "escalations_today": r_escalations.count or 0,
        "open_requests": r_open.count or 0,
    }


# ── Calls ──────────────────────────────────────────────────────────────────────

@router.get("/calls")
async def list_calls(tenant_id: str = Depends(_get_tenant_id), limit: int = 50, cursor: str | None = None):
    """Recent calls with customer info and status."""
    q = (
        db.table("calls")
        .select("id, status, duration_s, started_at, ended_at, customers(name, phone, email)")
        .eq("tenant_id", tenant_id)
        .order("started_at", desc=True)
    )
    if cursor:
        q = q.lt("started_at", cursor)
    rows = (await q.limit(limit + 1).execute()).data or []
    return {"data": rows[:limit], "next_cursor": rows[limit]["started_at"] if len(rows) > limit else None}


@router.get("/calls/{call_id}")
async def get_call(call_id: str, tenant_id: str = Depends(_get_tenant_id)):
    """Single call with full transcript and all actions taken."""
    result = await (
        db.table("calls")
        .select("*, customers(name, phone, email), call_actions(*)")
        .eq("id", call_id)
        .eq("tenant_id", tenant_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Call not found")
    return result.data


# ── Service requests ───────────────────────────────────────────────────────────

@router.get("/service-requests")
async def get_service_requests(
    tenant_id: str = Depends(_get_tenant_id),
    status: str | None = None,
    is_after_hours: bool | None = None,
    is_emergency: bool | None = None,
    limit: int = 50,
    cursor: str | None = None,
):
    """All service requests, optionally filtered by status, after-hours flag, or emergency flag."""
    include_dispatches = is_after_hours is True
    try:
        data, next_cursor = await list_service_requests(
            tenant_id,
            status=status,
            is_after_hours=is_after_hours,
            is_emergency=is_emergency,
            limit=limit,
            include_dispatches=include_dispatches,
            cursor=cursor,
        )
        return {"data": data, "next_cursor": next_cursor}
    except Exception:
        if include_dispatches:
            data, next_cursor = await list_service_requests(
                tenant_id,
                status=status,
                is_after_hours=is_after_hours,
                is_emergency=is_emergency,
                limit=limit,
                include_dispatches=False,
                cursor=cursor,
            )
            return {"data": data, "next_cursor": next_cursor}
        raise


@router.get("/service-requests/{request_id}")
async def get_service_request_detail(request_id: str, tenant_id: str = Depends(_get_tenant_id)):
    result = await (
        db.table("service_requests")
        .select("*, customers(name, phone, email), calls(twilio_sid, duration_s), oncall_dispatches(status, created_at)")
        .eq("id", request_id)
        .eq("tenant_id", tenant_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Service request not found")
    return result.data


_anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

_SUMMARY_PROMPT = """\
You are summarising a customer service call for an office team at a trade business (HVAC, plumbing, electrical, etc.).
Write 2-4 plain English sentences covering: what the customer needs, any urgency or special details, and the service address if mentioned.
Be concrete and direct — the reader needs to act on this, not admire it.
Do not start with "The customer" every time. Vary your opening.\
"""


@router.get("/service-requests/{request_id}/summary")
async def get_request_summary(request_id: str, tenant_id: str = Depends(_get_tenant_id)):
    result = await (
        db.table("service_requests")
        .select("service_type, notes, address, is_emergency, calls(transcript)")
        .eq("id", request_id)
        .eq("tenant_id", tenant_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Service request not found")

    sr = result.data
    transcript = (sr.get("calls") or {}).get("transcript") or ""

    if transcript:
        content = f"Call transcript:\n{transcript}"
    else:
        parts = [f"Service type: {sr['service_type']}"]
        if sr.get("notes"):
            parts.append(f"Notes: {sr['notes']}")
        if sr.get("address"):
            parts.append(f"Address: {sr['address']}")
        if sr.get("is_emergency"):
            parts.append("Flagged as emergency")
        content = "\n".join(parts)

    response = await _anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=_SUMMARY_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    return {"summary": response.content[0].text}


class StatusUpdate(BaseModel):
    status: str | None = None
    scheduled_date: str | None = None
    scheduled_time: str | None = None
    next_morning_priority: bool | None = None


_VALID_STATUSES = {"pending", "reschedule_requested", "scheduled", "in_progress", "completed", "cancelled"}


@router.patch("/service-requests/{request_id}")
async def update_request_status(request_id: str, body: StatusUpdate, tenant_id: str = Depends(_get_tenant_id)):
    """
    Update a service request from the dashboard.
    When status is set to 'scheduled', an SMS confirmation is automatically sent.
    next_morning_priority can be toggled independently of status.
    """
    updates: dict = {}

    if body.status is not None:
        if body.status not in _VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"status must be one of: {', '.join(sorted(_VALID_STATUSES))}",
            )
        updates["status"] = body.status

    if body.scheduled_date:
        updates["scheduled_date"] = body.scheduled_date
    if body.scheduled_time:
        updates["scheduled_time"] = body.scheduled_time
    if body.next_morning_priority is not None:
        updates["next_morning_priority"] = body.next_morning_priority

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await update_service_request(request_id, updates)

    if body.status == "scheduled":
        request = await get_service_request(request_id)
        if request:
            customer = request.get("customers") or {}
            phone = customer.get("phone")
            if phone:
                tenant_row = await db.table("tenants").select("phone").eq("id", tenant_id).single().execute()
                from_phone = (tenant_row.data or {}).get("phone")
                service = request["service_type"]
                date = body.scheduled_date or request.get("scheduled_date", "")
                time = body.scheduled_time or request.get("scheduled_time", "")
                date_str = f" on {date}" if date else ""
                time_str = f" {time}" if time else ""
                msg = (
                    f"Your {service} appointment has been confirmed{date_str}{time_str}. "
                    "Reply STOP to opt out."
                )
                await send_confirmation_sms(phone, msg, from_phone)

    return updated


# ── Customers ──────────────────────────────────────────────────────────────────

@router.get("/customers")
async def list_customers(tenant_id: str = Depends(_get_tenant_id), limit: int = 50, cursor: str | None = None):
    """All customers for a tenant."""
    q = (
        db.table("customers")
        .select("id, name, phone, created_at, calls(started_at)")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
    )
    if cursor:
        q = q.lt("created_at", cursor)
    rows = (await q.limit(limit + 1).execute()).data or []
    for row in rows:
        calls = row.pop("calls", []) or []
        row["last_call_at"] = max(
            (c["started_at"] for c in calls if c.get("started_at")), default=None
        )
    return {"data": rows[:limit], "next_cursor": rows[limit]["created_at"] if len(rows) > limit else None}


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, tenant_id: str = Depends(_get_tenant_id)):
    """Single customer with their full call and service request history."""
    result = await (
        db.table("customers")
        .select("*, calls(id, status, duration_s, started_at), service_requests(id, service_type, status, created_at)")
        .eq("id", customer_id)
        .eq("tenant_id", tenant_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result.data


# ── Knowledge base ─────────────────────────────────────────────────────────────

@router.get("/kb")
async def list_kb_chunks(tenant_id: str = Depends(_get_tenant_id), limit: int = 50, cursor: str | None = None):
    q = (
        db.table("kb_chunks")
        .select("id, content, metadata, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
    )
    if cursor:
        q = q.lt("created_at", cursor)
    rows = (await q.limit(limit + 1).execute()).data or []
    return {"data": rows[:limit], "next_cursor": rows[limit]["created_at"] if len(rows) > limit else None}


@router.post("/kb/upload")
async def upload_kb_file(tenant_id: str = Depends(_get_tenant_id), file: UploadFile = File(...)):
    """Upload a PDF, .txt, or .md file and ingest it into the knowledge base."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured — cannot embed")

    filename = file.filename or "upload"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ("pdf", "txt", "md"):
        raise HTTPException(status_code=422, detail="Only PDF, .txt, and .md files are supported")
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    if ext == "pdf":
        text = _extract_pdf(raw)
    else:
        text = raw.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the file")

    chunks = split_text(text)
    for chunk in chunks:
        await ingest_chunk(tenant_id, chunk, {"source": filename})

    return {"filename": filename, "chunks_added": len(chunks)}


@router.delete("/kb/{chunk_id}")
async def delete_kb_chunk(chunk_id: str, tenant_id: str = Depends(_get_tenant_id)):
    row = await db.table("kb_chunks").select("tenant_id").eq("id", chunk_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="KB chunk not found")
    if row.data["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.table("kb_chunks").delete().eq("id", chunk_id).execute()
    return {"deleted": True}


# ── Tenant settings ────────────────────────────────────────────────────────────

class TenantSettingsUpdate(BaseModel):
    business_hours_start: str | None = None
    business_hours_end: str | None = None
    business_timezone: str | None = None
    oncall_voice_timeout_minutes: int | None = Field(None, ge=1, le=60)
    oncall_sms_timeout_minutes: int | None = Field(None, ge=1, le=60)
    oncall_notification_method: str | None = Field(None, pattern=r"^(voice|sms|both)$")
    oncall_fallback_delay_minutes: int | None = Field(None, ge=1, le=60)
    escalation_phone: E164Phone | None = None
    escalation_phone_after_hours: E164Phone | None = None
    confirm_name_spelling: bool | None = None
    confirm_address_spelling: bool | None = None
    remember_caller_info: bool | None = None
    customer_fallback_message: str | None = None
    customer_tech_accepted_message: str | None = None
    customer_manager_accepted_message: str | None = None
    cartesia_voice_id: str | None = None
    kb_about: str | None = None
    kb_services: str | None = None
    kb_hours_description: str | None = None
    kb_rate_regular: str | None = None
    kb_rate_after_hours: str | None = None
    kb_rate_maintenance: str | None = None
    kb_extra: str | None = None


@router.get("/settings")
async def get_settings(tenant_id: str = Depends(_get_tenant_id)):
    result = await (
        db.table("tenants")
        .select(
            "id, name, phone, business_hours_start, business_hours_end, business_timezone, "
            "oncall_voice_timeout_minutes, oncall_sms_timeout_minutes, oncall_notification_method, oncall_fallback_delay_minutes, "
            "escalation_phone, escalation_phone_after_hours, confirm_name_spelling, confirm_address_spelling, "
            "customer_fallback_message, customer_tech_accepted_message, customer_manager_accepted_message, "
            "remember_caller_info, cartesia_voice_id, "
            "kb_about, kb_services, kb_hours_description, kb_rate_regular, kb_rate_after_hours, "
            "kb_rate_maintenance, kb_extra, plan, trial_ends_at"
        )
        .eq("id", tenant_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result.data


@router.patch("/settings")
async def update_settings(body: TenantSettingsUpdate, request: Request, tenant_id: str = Depends(_get_tenant_id)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await (
        db.table("tenants")
        .update(updates)
        .eq("id", tenant_id)
        .execute()
    )
    tenant = result.data[0] if result.data else {}

    phone = tenant.get("phone")
    if phone:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            await redis.delete(f"tenant:phone:{phone}")

    return tenant


# ── Voices ─────────────────────────────────────────────────────────────────────

@router.get("/voices")
async def list_voices(tenant_id: str = Depends(_get_tenant_id)):
    """Fetch available English voices from Cartesia and return name + id."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.cartesia.ai/voices",
                headers={
                    "X-API-Key": settings.cartesia_api_key,
                    "Cartesia-Version": "2024-06-10",
                },
            )
            resp.raise_for_status()
            all_voices = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Cartesia voices API error", status=e.response.status_code)
        raise HTTPException(status_code=502, detail="Failed to load voices from Cartesia. Check your API key.")
    except Exception as e:
        logger.error("Cartesia voices request failed", error=str(e))
        raise HTTPException(status_code=502, detail="Could not reach Cartesia voice API.")

    voices = [
        {"id": v["id"], "name": v["name"], "description": v.get("description", "")}
        for v in all_voices
        if v.get("language", "en") == "en" and v.get("is_public", False)
    ]
    voices.sort(key=lambda v: v["name"])
    return voices


# ── Team members ──────────────────────────────────────────────────────────────

@router.get("/team")
async def list_team(tenant_id: str = Depends(_get_tenant_id)):
    result = await (
        db.table("users")
        .select("id, email, name, role, active, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


@router.delete("/team/{user_id}")
async def remove_team_member(user_id: str, tenant_id: str = Depends(_get_tenant_id)):
    result = await db.table("users").select("id, email, role, tenant_id").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    if result.data["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if result.data["role"] == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the account owner")
    await db.table("users").update({"active": False}).eq("id", user_id).execute()
    await db.table("refresh_tokens").update({"revoked": True}).eq("user_email", result.data["email"]).execute()
    return {"ok": True}


# ── On-call technicians ────────────────────────────────────────────────────────

class OncallTechCreate(BaseModel):
    name: str
    phone: E164Phone
    email: str | None = None
    priority: int
    role: str = "tech"  # tech | manager


class OncallTechUpdate(BaseModel):
    name: str | None = None
    phone: E164Phone | None = None
    email: str | None = None
    priority: int | None = None
    active: bool | None = None
    role: str | None = None


@router.get("/oncall-technicians")
async def get_oncall_technicians(tenant_id: str = Depends(_get_tenant_id), role: str = "tech"):
    return await list_oncall_technicians(tenant_id, role=role)


@router.post("/oncall-technicians")
async def add_oncall_technician(body: OncallTechCreate, tenant_id: str = Depends(_get_tenant_id)):
    return await create_oncall_technician(
        tenant_id, body.name, body.phone, body.email, body.priority, role=body.role
    )


@router.patch("/oncall-technicians/{tech_id}")
async def edit_oncall_technician(tech_id: str, body: OncallTechUpdate, tenant_id: str = Depends(_get_tenant_id)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    row = await db.table("oncall_technicians").select("tenant_id").eq("id", tech_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Technician not found")
    if row.data["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await update_oncall_technician(tech_id, updates)


@router.delete("/oncall-technicians/{tech_id}")
async def remove_oncall_technician(tech_id: str, tenant_id: str = Depends(_get_tenant_id)):
    row = await db.table("oncall_technicians").select("tenant_id").eq("id", tech_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Technician not found")
    if row.data["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_oncall_technician(tech_id)
    return {"deleted": True}


# ── Escalations ───────────────────────────────────────────────────────────────

@router.get("/escalations")
async def list_escalations(tenant_id: str = Depends(_get_tenant_id)):
    result = await (
        db.table("escalations")
        .select("*, customers(name, phone), calls(id)")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    rows = result.data or []
    for row in rows:
        row["call_id"] = (row.pop("calls", None) or {}).get("id")
    return rows


class EscalationUpdate(BaseModel):
    status: str  # "handled"


@router.patch("/escalations/{escalation_id}")
async def update_escalation(
    escalation_id: str,
    body: EscalationUpdate,
    tenant_id: str = Depends(_get_tenant_id),
):
    existing = await (
        db.table("escalations")
        .select("id")
        .eq("id", escalation_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Escalation not found")

    update: dict = {"status": body.status}
    if body.status == "handled":
        update["handled_at"] = datetime.now(timezone.utc).isoformat()

    await db.table("escalations").update(update).eq("id", escalation_id).execute()
    result = await (
        db.table("escalations")
        .select("*, customers(name, phone), calls(id)")
        .eq("id", escalation_id)
        .single()
        .execute()
    )
    row = result.data or {}
    row["call_id"] = (row.pop("calls", None) or {}).get("id")
    return row


@router.post("/close-account")
async def close_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only the account owner can close the account")

    tenant_id = payload.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Token has no tenant scope")

    row = await db.table("tenants").select("phone, twilio_phone_sid").eq("id", tenant_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if row.data.get("twilio_phone_sid"):
        try:
            from src.services.twilio_provision import release_phone_number
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: release_phone_number(row.data["twilio_phone_sid"]))
        except Exception as e:
            from src.utils.logger import logger
            logger.error("Failed to release Twilio number on account close", error=str(e))

    redis = getattr(request.app.state, "redis", None)
    if redis and row.data.get("phone"):
        await redis.delete(f"tenant:phone:{row.data['phone']}")

    active_dispatches = await (
        db.table("oncall_dispatches")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("status", "dispatching")
        .execute()
    )
    dispatch_ids = [d["id"] for d in (active_dispatches.data or [])]

    if dispatch_ids:
        await db.table("oncall_dispatches").update({
            "status": "failed",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }).in_("id", dispatch_ids).execute()

        await db.table("dispatch_sms_timeouts").update({
            "processed": True,
        }).eq("processed", False).in_("dispatch_id", dispatch_ids).execute()

    await db.table("tenants").update({
        "plan": "closed",
        "phone": None,
        "twilio_phone_sid": None,
    }).eq("id", tenant_id).execute()

    await db.table("users").update({"active": False}).eq("tenant_id", tenant_id).execute()

    from src.utils.logger import logger
    logger.info("Account closed by owner", tenant_id=tenant_id)
    return {"closed": True}


def _extract_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(status_code=503, detail="pypdf not installed on server")
    reader = PdfReader(io.BytesIO(raw))
    pages = [page.extract_text() for page in reader.pages if page.extract_text()]
    return "\n\n".join(p.strip() for p in pages)

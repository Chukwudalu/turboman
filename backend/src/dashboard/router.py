"""
Dashboard API — read-only views and status updates for the Turboman dashboard.

All routes require  Authorization: Bearer <jwt>  obtained from POST /auth/token.
Returns JSON — consumed by the Next.js frontend dashboard.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

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

def _get_tenant_id(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Decode the JWT and return the tenant_id encoded inside it."""
    payload = decode_token(credentials.credentials)
    tenant_id = payload.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Token has no tenant scope")
    return tenant_id


# ── Summary ────────────────────────────────────────────────────────────────────

@router.get("/summary")
async def summary(tenant_id: str = Depends(_get_tenant_id)):
    """High-level counts for the dashboard header cards."""
    today = datetime.now(timezone.utc).date().isoformat()

    calls_today = (
        db.table("calls")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .gte("started_at", today)
        .execute()
    ).count or 0

    escalations_today = (
        db.table("calls")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .eq("status", "escalated")
        .gte("started_at", today)
        .execute()
    ).count or 0

    bookings_today = (
        db.table("service_requests")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .gte("created_at", today)
        .execute()
    ).count or 0

    open_requests = (
        db.table("service_requests")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .in_("status", ["pending", "scheduled", "in_progress"])
        .execute()
    ).count or 0

    return {
        "calls_today": calls_today,
        "bookings_today": bookings_today,
        "escalations_today": escalations_today,
        "open_requests": open_requests,
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
    rows = q.limit(limit + 1).execute().data or []
    return {"data": rows[:limit], "next_cursor": rows[limit]["started_at"] if len(rows) > limit else None}


@router.get("/calls/{call_id}")
async def get_call(call_id: str, _: str = Depends(_get_tenant_id)):
    """Single call with full transcript and all actions taken."""
    result = (
        db.table("calls")
        .select("*, customers(name, phone, email), call_actions(*)")
        .eq("id", call_id)
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
async def get_service_request_detail(request_id: str, _: str = Depends(_get_tenant_id)):
    result = (
        db.table("service_requests")
        .select("*, customers(name, phone, email), calls(twilio_sid, duration_s), oncall_dispatches(status, created_at)")
        .eq("id", request_id)
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
async def get_request_summary(request_id: str, _: str = Depends(_get_tenant_id)):
    result = (
        db.table("service_requests")
        .select("service_type, notes, address, is_emergency, calls(transcript)")
        .eq("id", request_id)
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
    status: str | None = None   # pending | reschedule_requested | scheduled | in_progress | completed | cancelled
    scheduled_date: str | None = None
    scheduled_time: str | None = None
    next_morning_priority: bool | None = None


_VALID_STATUSES = {"pending", "reschedule_requested", "scheduled", "in_progress", "completed", "cancelled"}


@router.patch("/service-requests/{request_id}")
async def update_request_status(request_id: str, body: StatusUpdate, _: str = Depends(_get_tenant_id)):
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

    # Fire SMS confirmation when the trades company marks a request as scheduled
    if body.status == "scheduled":
        request = await get_service_request(request_id)
        if request:
            customer = request.get("customers") or {}
            phone = customer.get("phone")
            if phone:
                service = request["service_type"]
                date = body.scheduled_date or request.get("scheduled_date", "")
                time = body.scheduled_time or request.get("scheduled_time", "")
                date_str = f" on {date}" if date else ""
                time_str = f" {time}" if time else ""
                msg = (
                    f"Your {service} appointment has been confirmed{date_str}{time_str}. "
                    "Reply STOP to opt out."
                )
                await send_confirmation_sms(phone, msg)

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
    rows = q.limit(limit + 1).execute().data or []
    for row in rows:
        calls = row.pop("calls", []) or []
        row["last_call_at"] = max(
            (c["started_at"] for c in calls if c.get("started_at")), default=None
        )
    return {"data": rows[:limit], "next_cursor": rows[limit]["created_at"] if len(rows) > limit else None}


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, _: str = Depends(_get_tenant_id)):
    """Single customer with their full call and service request history."""
    result = (
        db.table("customers")
        .select("*, calls(id, status, duration_s, started_at), service_requests(id, service_type, status, created_at)")
        .eq("id", customer_id)
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
    rows = q.limit(limit + 1).execute().data or []
    return {"data": rows[:limit], "next_cursor": rows[limit]["created_at"] if len(rows) > limit else None}


@router.post("/kb/upload")
async def upload_kb_file(tenant_id: str = Depends(_get_tenant_id), file: UploadFile = File(...)):
    """Upload a PDF, .txt, or .md file and ingest it into the knowledge base."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured — cannot embed")

    filename = file.filename or "upload"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    raw = await file.read()

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
async def delete_kb_chunk(chunk_id: str, _: str = Depends(_get_tenant_id)):
    db.table("kb_chunks").delete().eq("id", chunk_id).execute()
    return {"deleted": True}


# ── Tenant settings ────────────────────────────────────────────────────────────

class TenantSettingsUpdate(BaseModel):
    business_hours_start: str | None = None
    business_hours_end: str | None = None
    business_timezone: str | None = None
    oncall_escalation_timeout_minutes: int | None = None
    oncall_notification_method: str | None = None  # voice | sms | both
    oncall_fallback_delay_minutes: int | None = None
    escalation_phone: E164Phone | None = None
    escalation_phone_after_hours: E164Phone | None = None


@router.get("/settings")
async def get_settings(tenant_id: str = Depends(_get_tenant_id)):
    result = (
        db.table("tenants")
        .select("id, name, business_hours_start, business_hours_end, business_timezone, oncall_escalation_timeout_minutes, oncall_notification_method, oncall_fallback_delay_minutes, escalation_phone, escalation_phone_after_hours")
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
    result = (
        db.table("tenants")
        .update(updates)
        .eq("id", tenant_id)
        .execute()
    )
    tenant = result.data[0] if result.data else {}

    # PostgREST only returns updated columns, so phone is missing unless it was
    # in the update body. Fetch it explicitly to guarantee the cache key is correct.
    phone_result = db.table("tenants").select("phone").eq("id", tenant_id).single().execute()
    phone = (phone_result.data or {}).get("phone")
    if phone:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            await redis.delete(f"tenant:phone:{phone}")

    return tenant


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
async def edit_oncall_technician(tech_id: str, body: OncallTechUpdate, _: str = Depends(_get_tenant_id)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return await update_oncall_technician(tech_id, updates)


@router.delete("/oncall-technicians/{tech_id}")
async def remove_oncall_technician(tech_id: str, _: str = Depends(_get_tenant_id)):
    await delete_oncall_technician(tech_id)
    return {"deleted": True}


def _extract_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(status_code=503, detail="pypdf not installed on server")
    reader = PdfReader(io.BytesIO(raw))
    pages = [page.extract_text() for page in reader.pages if page.extract_text()]
    return "\n\n".join(p.strip() for p in pages)

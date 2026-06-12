"""
Admin API — tenant management and knowledge base operations.

All routes require the X-Admin-Secret header to match settings.admin_secret.
In production, put this behind your VPN or gateway — it is not caller-facing.
"""
from __future__ import annotations

import asyncio
import json
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.config import settings
from src.utils.validators import E164Phone
from src.db import db
from src.db.rag import ingest_chunk
from src.services.twilio_provision import release_phone_number
from src.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["admin"])

_TENANT_CACHE_TTL = 86_400  # 24 hours


# ── Auth ───────────────────────────────────────────────────────────────────────

def _verify_admin(x_admin_secret: str = Header(alias="X-Admin-Secret")):
    if not settings.admin_secret or not secrets.compare_digest(x_admin_secret, settings.admin_secret):
        raise HTTPException(status_code=403, detail="Invalid admin secret")


# ── Schemas ────────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    trade_type: str          # hvac | plumbing | electrical
    phone: E164Phone         # E.164 Twilio number this tenant owns
    fsa_type: str
    cartesia_voice_id: str = ""


class KBChunkCreate(BaseModel):
    content: str
    metadata: dict = {}


# ── Tenant routes ──────────────────────────────────────────────────────────────

@router.post("/tenants", dependencies=[Depends(_verify_admin)])
async def create_tenant(body: TenantCreate, request: Request):
    """Create a tenant in Supabase and warm the Redis cache."""
    result = await db.table("tenants").insert(body.model_dump()).execute()
    tenant = result.data[0]

    redis = getattr(request.app.state, "redis", None)
    if redis:
        await redis.set(
            f"tenant:phone:{body.phone}",
            json.dumps(tenant),
            ex=_TENANT_CACHE_TTL,
        )
        logger.info("Tenant cached in Redis", phone=body.phone)

    return tenant


@router.get("/tenants", dependencies=[Depends(_verify_admin)])
async def list_tenants():
    result = await db.table("tenants").select("id, name, trade_type, phone, fsa_type, created_at").execute()
    return result.data


@router.delete("/tenants/{tenant_id}", dependencies=[Depends(_verify_admin)])
async def delete_tenant(tenant_id: str, request: Request):
    row = await db.table("tenants").select("phone, twilio_phone_sid").eq("id", tenant_id).single().execute()
    if row.data:
        if row.data.get("twilio_phone_sid"):
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: release_phone_number(row.data["twilio_phone_sid"]))
            except Exception as e:
                logger.error("Failed to release Twilio number on delete", error=str(e))
        redis = getattr(request.app.state, "redis", None)
        if redis and row.data.get("phone"):
            await redis.delete(f"tenant:phone:{row.data['phone']}")

    call_ids = [r["id"] for r in ((await db.table("calls").select("id").eq("tenant_id", tenant_id).execute()).data or [])]
    sr_ids   = [r["id"] for r in ((await db.table("service_requests").select("id").eq("tenant_id", tenant_id).execute()).data or [])]

    if call_ids:
        await db.table("call_actions").delete().in_("call_id", call_ids).execute()
    if sr_ids:
        dispatch_ids = [
            r["id"] for r in ((await db.table("oncall_dispatches").select("id").in_("service_request_id", sr_ids).execute()).data or [])
        ]
        if dispatch_ids:
            await db.table("dispatch_sms_timeouts").delete().in_("dispatch_id", dispatch_ids).execute()
            await db.table("pending_notifications").delete().in_("dispatch_id", dispatch_ids).execute()
        await db.table("oncall_dispatches").delete().in_("service_request_id", sr_ids).execute()

    await db.table("escalations").delete().eq("tenant_id", tenant_id).execute()
    await db.table("service_requests").delete().eq("tenant_id", tenant_id).execute()
    await db.table("calls").delete().eq("tenant_id", tenant_id).execute()
    await db.table("customers").delete().eq("tenant_id", tenant_id).execute()
    await db.table("oncall_technicians").delete().eq("tenant_id", tenant_id).execute()
    await db.table("kb_chunks").delete().eq("tenant_id", tenant_id).execute()
    await db.table("refresh_tokens").delete().eq("tenant_id", tenant_id).execute()
    await db.table("users").delete().eq("tenant_id", tenant_id).execute()
    await db.table("tenants").delete().eq("id", tenant_id).execute()
    return {"deleted": True}


@router.post("/tenants/{tenant_id}/close", dependencies=[Depends(_verify_admin)])
async def close_tenant(tenant_id: str, request: Request):
    """
    Deactivate a tenant — releases their Twilio number, deactivates all users,
    and marks the account as closed. Called on payment failure or cancellation.
    """
    row = await db.table("tenants").select("phone, twilio_phone_sid").eq("id", tenant_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if row.data.get("twilio_phone_sid"):
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: release_phone_number(row.data["twilio_phone_sid"]))
        except Exception as e:
            logger.error("Failed to release Twilio number on close", error=str(e))

    redis = getattr(request.app.state, "redis", None)
    if redis and row.data.get("phone"):
        await redis.delete(f"tenant:phone:{row.data['phone']}")

    await db.table("tenants").update({
        "plan": "closed",
        "phone": None,
        "twilio_phone_sid": None,
    }).eq("id", tenant_id).execute()

    await db.table("users").update({"active": False}).eq("tenant_id", tenant_id).execute()

    logger.info("Tenant closed", tenant_id=tenant_id)
    return {"closed": True}


# ── KB routes ──────────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/kb", dependencies=[Depends(_verify_admin)])
async def add_kb_chunk(tenant_id: str, body: KBChunkCreate):
    """Embed and store a single knowledge-base chunk for this tenant."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured — cannot embed")
    chunk_id = await ingest_chunk(tenant_id, body.content, body.metadata)
    return {"id": chunk_id, "tenant_id": tenant_id, "chars": len(body.content)}


@router.get("/tenants/{tenant_id}/kb", dependencies=[Depends(_verify_admin)])
async def list_kb_chunks(tenant_id: str):
    result = await (
        db.table("kb_chunks")
        .select("id, content, metadata, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/kb/{chunk_id}", dependencies=[Depends(_verify_admin)])
async def delete_kb_chunk(chunk_id: str):
    await db.table("kb_chunks").delete().eq("id", chunk_id).execute()
    return {"deleted": True}

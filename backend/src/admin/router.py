"""
Admin API — tenant management and knowledge base operations.

All routes require the X-Admin-Secret header to match settings.admin_secret.
In production, put this behind your VPN or gateway — it is not caller-facing.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.config import settings
from src.utils.validators import E164Phone
from src.db import db
from src.db.rag import ingest_chunk
from src.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["admin"])

_TENANT_CACHE_TTL = 86_400  # 24 hours


# ── Auth ───────────────────────────────────────────────────────────────────────

def _verify_admin(x_admin_secret: str = Header(alias="X-Admin-Secret")):
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")


# ── Schemas ────────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    trade_type: str          # hvac | plumbing | electrical
    phone: E164Phone         # E.164 Twilio number this tenant owns
    fsa_type: str            # housecallpro | jobber
    fsa_api_key: str
    cartesia_voice_id: str = ""


class KBChunkCreate(BaseModel):
    content: str
    metadata: dict = {}


# ── Tenant routes ──────────────────────────────────────────────────────────────

@router.post("/tenants", dependencies=[Depends(_verify_admin)])
async def create_tenant(body: TenantCreate, request: Request):
    """Create a tenant in Supabase and warm the Redis cache."""
    result = db.table("tenants").insert(body.model_dump()).execute()
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
    result = db.table("tenants").select("id, name, trade_type, phone, fsa_type, created_at").execute()
    return result.data


@router.delete("/tenants/{tenant_id}", dependencies=[Depends(_verify_admin)])
async def delete_tenant(tenant_id: str, request: Request):
    row = db.table("tenants").select("phone").eq("id", tenant_id).single().execute()
    if row.data:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            await redis.delete(f"tenant:phone:{row.data['phone']}")
    db.table("tenants").delete().eq("id", tenant_id).execute()
    return {"deleted": True}


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
    result = (
        db.table("kb_chunks")
        .select("id, content, metadata, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/kb/{chunk_id}", dependencies=[Depends(_verify_admin)])
async def delete_kb_chunk(chunk_id: str):
    db.table("kb_chunks").delete().eq("id", chunk_id).execute()
    return {"deleted": True}

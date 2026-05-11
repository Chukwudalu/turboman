from __future__ import annotations
from src.db import db
from src.utils.logger import logger


async def upsert_customer(tenant_id: str, phone: str, name: str | None = None) -> dict:
    # Only include name in the payload when it's actually provided — omitting it
    # prevents the upsert from overwriting a saved name with NULL on return calls.
    payload: dict = {"tenant_id": tenant_id, "phone": phone}
    if name:
        payload["name"] = name
    res = (
        db.table("customers")
        .upsert(payload, on_conflict="tenant_id,phone")
        .execute()
    )
    return res.data[0]


async def create_call(tenant_id: str, customer_id: str, twilio_sid: str) -> dict:
    res = (
        db.table("calls")
        .insert({"tenant_id": tenant_id, "customer_id": customer_id, "twilio_sid": twilio_sid})
        .execute()
    )
    return res.data[0]


async def end_call(call_id: str, status: str, duration_s: int, transcript: str):
    from datetime import datetime, timezone
    db.table("calls").update({
        "status": status,
        "duration_s": duration_s,
        "transcript": transcript,
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", call_id).execute()


async def log_action(call_id: str, action_type: str, payload: dict, result: dict, success: bool):
    db.table("call_actions").insert({
        "call_id": call_id,
        "type": action_type,
        "payload": payload,
        "result": result,
        "success": success,
    }).execute()


async def get_tenant_by_phone(phone: str) -> dict | None:
    res = (
        db.table("tenants")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


async def get_customer_history(tenant_id: str, phone: str) -> dict | None:
    res = (
        db.table("customers")
        .select("*, calls(status, started_at, call_actions(type, success))")
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .single()
        .execute()
    )
    return res.data

"""
Service request CRUD — Turboman's own job management.
Replaces HousecallPro / Jobber as the system of record.
"""
from __future__ import annotations

from src.db import db


async def create_service_request(
    *,
    tenant_id: str,
    customer_id: str,
    call_id: str | None,
    service_type: str,
    scheduled_date: str | None = None,
    scheduled_time: str | None = None,
    address: str | None = None,
    notes: str | None = None,
    channel: str = "voice",
    is_emergency: bool = False,
    is_after_hours: bool = False,
) -> dict:
    payload: dict = {
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "call_id": call_id,
        "service_type": service_type,
        "status": "pending",
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "address": address,
        "notes": notes,
        "channel": channel,
        "is_emergency": is_emergency,
        "is_after_hours": is_after_hours,
        "next_morning_priority": False,
    }
    try:
        result = db.table("service_requests").insert(payload).execute()
    except Exception as e:
        if "call_id" in str(e):
            # call_id column missing — insert without it (run the migration to fix permanently)
            payload.pop("call_id", None)
            result = db.table("service_requests").insert(payload).execute()
        else:
            raise
    return result.data[0]


async def update_service_request(request_id: str, updates: dict) -> dict:
    result = (
        db.table("service_requests")
        .update(updates)
        .eq("id", request_id)
        .execute()
    )
    return result.data[0]


async def get_service_request(request_id: str) -> dict | None:
    result = (
        db.table("service_requests")
        .select("*, customers(name, phone, email), oncall_dispatches(status, created_at)")
        .eq("id", request_id)
        .single()
        .execute()
    )
    return result.data


async def get_latest_open_request(customer_id: str) -> dict | None:
    """Return the most recent non-closed request for a customer."""
    result = (
        db.table("service_requests")
        .select("*")
        .eq("customer_id", customer_id)
        .in_("status", ["pending", "scheduled", "in_progress"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


async def list_service_requests(
    tenant_id: str,
    status: str | None = None,
    is_after_hours: bool | None = None,
    is_emergency: bool | None = None,
    limit: int = 50,
    include_dispatches: bool = False,
    cursor: str | None = None,
) -> tuple[list[dict], str | None]:
    select = "*, customers(name, phone, email)"
    if include_dispatches:
        select += ", oncall_dispatches(status, created_at, acknowledged_by_tech_id, oncall_technicians(name))"
    query = (
        db.table("service_requests")
        .select(select)
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    if is_after_hours is not None:
        query = query.eq("is_after_hours", is_after_hours)
    if is_emergency is not None:
        query = query.eq("is_emergency", is_emergency)
    if cursor:
        query = query.lt("created_at", cursor)
    rows = query.limit(limit + 1).execute().data or []
    next_cursor = rows[limit]["created_at"] if len(rows) > limit else None
    return rows[:limit], next_cursor

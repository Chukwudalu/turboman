from __future__ import annotations

from datetime import datetime, timezone

from src.db import db


async def list_oncall_technicians(tenant_id: str, role: str = "tech") -> list[dict]:
    result = (
        db.table("oncall_technicians")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("active", True)
        .eq("role", role)
        .order("priority", desc=False)
        .execute()
    )
    return result.data or []


async def get_tech_by_id(tech_id: str) -> dict | None:
    result = (
        db.table("oncall_technicians")
        .select("*")
        .eq("id", tech_id)
        .single()
        .execute()
    )
    return result.data


async def create_oncall_technician(
    tenant_id: str, name: str, phone: str, email: str | None, priority: int, role: str = "tech"
) -> dict:
    result = db.table("oncall_technicians").insert({
        "tenant_id": tenant_id,
        "name": name,
        "phone": phone,
        "email": email,
        "priority": priority,
        "role": role,
    }).execute()
    return result.data[0]


async def update_oncall_technician(tech_id: str, updates: dict) -> dict:
    result = (
        db.table("oncall_technicians")
        .update(updates)
        .eq("id", tech_id)
        .execute()
    )
    return result.data[0]


async def delete_oncall_technician(tech_id: str) -> None:
    db.table("oncall_technicians").delete().eq("id", tech_id).execute()


async def create_dispatch(tenant_id: str, service_request_id: str) -> dict:
    result = db.table("oncall_dispatches").insert({
        "tenant_id": tenant_id,
        "service_request_id": service_request_id,
        "status": "dispatching",
    }).execute()
    return result.data[0]


async def get_dispatch(dispatch_id: str) -> dict | None:
    result = (
        db.table("oncall_dispatches")
        .select("*")
        .eq("id", dispatch_id)
        .single()
        .execute()
    )
    return result.data


async def get_dispatch_context(dispatch_id: str) -> dict | None:
    """
    Returns everything the dispatch service and TwiML endpoints need:
    dispatch status, service details, customer phone, company name,
    timeout, and notification method.
    """
    result = (
        db.table("oncall_dispatches")
        .select(
            "status, tenant_id, "
            "service_requests(service_type, address, is_emergency, "
            "  tenants(name, oncall_escalation_timeout_minutes, oncall_notification_method, oncall_fallback_delay_minutes), "
            "  customers(phone, name))"
        )
        .eq("id", dispatch_id)
        .single()
        .execute()
    )
    if not result.data:
        return None

    d = result.data
    sr = d.get("service_requests") or {}
    tenant = sr.get("tenants") or {}
    customer = sr.get("customers") or {}

    return {
        "dispatch_status": d["status"],
        "tenant_id": d["tenant_id"],
        "company_name": tenant.get("name", "the company"),
        "service_type": sr.get("service_type", "emergency service"),
        "address": sr.get("address"),
        "customer_phone": customer.get("phone"),
        "customer_name": customer.get("name"),
        "timeout_minutes": tenant.get("oncall_escalation_timeout_minutes") or 10,
        "notification_method": tenant.get("oncall_notification_method") or "both",
        "is_emergency": bool(sr.get("is_emergency", True)),
        "fallback_delay_minutes": tenant.get("oncall_fallback_delay_minutes") if tenant.get("oncall_fallback_delay_minutes") is not None else 5,
    }


async def acknowledge_dispatch(
    dispatch_id: str,
    *,
    eta_text: str | None = None,
    tech_id: str | None = None,
) -> None:
    updates: dict = {
        "status": "acknowledged",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    if eta_text:
        updates["eta_text"] = eta_text
    if tech_id:
        updates["acknowledged_by_tech_id"] = tech_id
    db.table("oncall_dispatches").update(updates).eq("id", dispatch_id).execute()


async def acknowledge_dispatch_for_tenant(tenant_id: str) -> bool:
    """Acknowledge the most recent dispatching record for a tenant (SMS reply flow)."""
    result = (
        db.table("oncall_dispatches")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("status", "dispatching")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        await acknowledge_dispatch(result.data[0]["id"])
        return True
    return False


async def reject_dispatch(dispatch_id: str) -> None:
    """At least one tech was reached but declined. No one accepted the job."""
    db.table("oncall_dispatches").update({
        "status": "rejected",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", dispatch_id).execute()


async def fail_dispatch(dispatch_id: str) -> None:
    """Nobody answered — all contacts were unreachable."""
    db.table("oncall_dispatches").update({
        "status": "failed",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", dispatch_id).execute()

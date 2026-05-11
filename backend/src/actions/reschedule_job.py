from src.db.jobs import get_latest_open_request, update_service_request


async def reschedule_job(inputs: dict, *, tenant: dict, customer: dict | None, **_) -> dict:
    request_id = inputs.get("job_id")

    if not request_id:
        if not customer:
            return {"success": False, "message": "I couldn't find an open request on your account."}
        open_request = await get_latest_open_request(customer["id"])
        if not open_request:
            return {"success": False, "message": "I couldn't find an open service request to reschedule."}
        request_id = open_request["id"]

    new_date = inputs["new_date"]
    new_time = inputs.get("new_time", "")
    time_str = f" {new_time}" if new_time else ""

    # Flag the request — the trades company will confirm in their tool and
    # mark it scheduled on the dashboard, which triggers the SMS confirmation.
    await update_service_request(request_id, {
        "status": "reschedule_requested",
        "notes": f"Customer requested reschedule to {new_date}{time_str}.",
    })

    return {
        "success": True,
        "request_id": request_id,
        "message": (
            f"I've noted your request to reschedule to {new_date}{time_str}. "
            "Our team will confirm the new time with you shortly."
        ),
    }

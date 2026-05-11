from src.db.jobs import get_latest_open_request, get_service_request


async def get_status(inputs: dict, *, tenant: dict, customer: dict | None, **_) -> dict:
    request_id = inputs.get("job_id")

    if request_id:
        request = await get_service_request(request_id)
    elif customer:
        request = await get_latest_open_request(customer["id"])
    else:
        request = None

    if not request:
        return {"success": False, "message": "I couldn't find an open service request on your account."}

    status = request["status"]
    service = request["service_type"]
    date = request.get("scheduled_date")
    time = request.get("scheduled_time")

    if date:
        time_str = f" {time}" if time else ""
        detail = f"scheduled for {date}{time_str}"
    else:
        detail = "pending scheduling — our team will be in touch shortly"

    return {
        "success": True,
        "status": status,
        "service_type": service,
        "message": f"Your {service} request is {detail}.",
    }

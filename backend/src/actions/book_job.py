from src.db.jobs import create_service_request
from src.utils.business_hours import is_after_hours
from src.services.oncall_dispatch import trigger_oncall_dispatch
from src.utils.logger import logger


async def book_job(inputs: dict, *, tenant: dict, customer: dict | None, call_id: str | None = None) -> dict:
    if not customer:
        return {"success": False, "message": "I couldn't find your account. Would you like me to transfer you to someone?"}

    service_type = (inputs.get("service_type") or "").strip()
    if not service_type:
        logger.warning("book_job called without service_type", inputs=inputs)
        return {"success": False, "message": "What type of service are you looking to book?"}

    after_hours = is_after_hours(tenant)
    emergency = bool(inputs.get("is_emergency", False))

    logger.info("book_job started", service_type=service_type, after_hours=after_hours, emergency=emergency)

    request = await create_service_request(
        tenant_id=tenant["id"],
        customer_id=customer["id"],
        call_id=call_id,
        service_type=service_type,
        scheduled_date=inputs.get("preferred_date"),
        scheduled_time=inputs.get("preferred_time"),
        address=inputs.get("address"),
        notes=inputs.get("notes"),
        channel="voice",
        is_emergency=emergency,
        is_after_hours=after_hours,
    )
    logger.info("Service request created", request_id=request.get("id"))

    service = service_type
    date_hint = f" for around {inputs['preferred_date']}" if inputs.get("preferred_date") else ""

    # Notify the on-call tech for any after-hours request — emergency or not.
    dispatch_ok = True
    if after_hours:
        try:
            await trigger_oncall_dispatch(
                tenant_id=tenant["id"],
                service_request_id=request["id"],
                service_type=service,
                address=inputs.get("address"),
                customer_phone=customer.get("phone"),
                customer_name=customer.get("name"),
                notification_method=tenant.get("oncall_notification_method") or "both",
                is_emergency=emergency,
            )
        except Exception as e:
            logger.error("Oncall dispatch failed after service request created", error=str(e), request_id=request.get("id"))
            dispatch_ok = False

    if after_hours or emergency:
        if not dispatch_ok:
            return {
                "success": True,
                "message": (
                    f"I've logged your {service} request{date_hint}. "
                    "We're having trouble reaching our on-call team right now — "
                    "someone will follow up with you as soon as possible."
                ),
            }
        return {
            "success": True,
            "message": (
                f"I've logged your {service} request{date_hint}. "
                "Our on-call team has been notified and will be in touch shortly."
            ),
        }

    return {
        "success": True,
        "message": (
            f"I've logged your {service} request{date_hint}. "
            "Someone from our team will be in touch shortly to confirm your appointment."
        ),
    }

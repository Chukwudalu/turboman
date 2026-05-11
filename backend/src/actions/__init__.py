from src.actions.book_job import book_job
from src.actions.reschedule_job import reschedule_job
from src.actions.get_status import get_status
from src.actions.get_quote import get_quote
from src.actions.escalate import escalate
from src.actions.save_customer_info import save_customer_info
from src.db.queries import log_action
from src.utils.logger import logger

_ACTION_MAP = {
    "book_job": book_job,
    "reschedule_job": reschedule_job,
    "get_job_status": get_status,
    "get_quote": get_quote,
    "escalate_to_human": escalate,
    "save_customer_info": save_customer_info,
}


async def route_action(
    tool_name: str,
    inputs: dict,
    *,
    tenant: dict,
    customer: dict | None,
    call_id: str | None = None,
) -> dict:
    handler = _ACTION_MAP.get(tool_name)
    if not handler:
        logger.warn("Unknown tool called", tool=tool_name)
        return {"success": False, "error": "Unknown action"}

    try:
        result = await handler(inputs, tenant=tenant, customer=customer, call_id=call_id)
    except Exception as e:
        logger.error("Action failed", tool=tool_name, error=str(e))
        result = {"success": False, "error": "Action failed — please try again or speak to a human."}

    if call_id:
        try:
            await log_action(call_id, tool_name, inputs, result, bool(result.get("success")))
        except Exception as e:
            logger.error("Failed to log action", tool=tool_name, error=str(e))

    return result

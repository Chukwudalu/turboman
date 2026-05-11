from src.db.queries import upsert_customer


async def save_customer_info(
    inputs: dict, *, tenant: dict, customer: dict | None, call_id: str | None = None
) -> dict:
    if not customer:
        return {"success": False}
    name = inputs.get("name")
    if name:
        await upsert_customer(tenant["id"], customer["phone"], name=name)
    return {"success": True}

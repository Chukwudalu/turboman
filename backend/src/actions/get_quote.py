from src.db.rag import search_kb


async def get_quote(inputs: dict, *, tenant: dict, **_) -> dict:
    """
    Return a price estimate.

    Searches the tenant's knowledge base for pricing info specific to the
    requested service type. Falls back to a diagnostic-visit message when
    no pricing data is found.
    """
    service_type = inputs["service_type"]
    details = inputs.get("details", "")
    query = f"{service_type} {details}".strip()

    # Pull relevant KB chunks for this tenant
    tenant_id = tenant.get("id", "")
    chunks = await search_kb(tenant_id, query, k=3) if tenant_id else []

    if chunks:
        # Claude will receive the KB content and generate the final quote phrasing;
        # here we surface the raw data so the LLM can cite real numbers.
        kb_text = " | ".join(chunks)
        return {
            "success": True,
            "found_pricing": True,
            "pricing_info": kb_text,
            "message": (
                f"Based on our price book for {service_type}: {kb_text}. "
                "Final pricing is confirmed after the technician's on-site assessment."
            ),
        }

    return {
        "success": True,
        "found_pricing": False,
        "message": (
            f"For {service_type}, our pricing depends on the specific issue. "
            "A technician would assess it on-site. Would you like to book a diagnostic visit?"
        ),
    }

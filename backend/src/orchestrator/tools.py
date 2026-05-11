TOOLS = [
    {
        "name": "book_job",
        "description": (
            "Log a new service request from the customer. "
            "The team will review it and schedule — do NOT tell the customer it is confirmed or booked."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service_type": {"type": "string", "description": 'e.g. "AC repair", "burst pipe"'},
                "preferred_date": {"type": "string", "description": "ISO date e.g. 2025-06-15"},
                "preferred_time": {"type": "string", "description": 'e.g. "morning", "9am"'},
                "address": {"type": "string", "description": "Service address if different from account"},
                "notes": {"type": "string", "description": "Additional notes from customer"},
                "is_emergency": {
                    "type": "boolean",
                    "description": (
                        "True if the customer confirmed this is an emergency, or explicitly stated urgency. "
                        "False for all standard service requests."
                    ),
                },
            },
            "required": ["service_type", "is_emergency"],
        },
    },
    {
        "name": "reschedule_job",
        "description": (
            "Log a reschedule request from the customer. "
            "The team will confirm the new time — do NOT tell the customer it is confirmed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Omit to reschedule the most recent open request"},
                "new_date": {"type": "string", "description": "ISO date"},
                "new_time": {"type": "string"},
            },
            "required": ["new_date"],
        },
    },
    {
        "name": "get_job_status",
        "description": "Check the status of a customer's service request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Omit to get the most recent open request"},
            },
        },
    },
    {
        "name": "get_quote",
        "description": "Provide a price estimate for a service based on the company knowledge base.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_type": {"type": "string"},
                "details": {"type": "string"},
            },
            "required": ["service_type"],
        },
    },
    {
        "name": "save_customer_info",
        "description": (
            "Save the customer's name to their account. "
            "Call this silently as soon as the customer provides their name — do not mention it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer's full name as they stated it"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Transfer the call to a human agent. "
            "Use when the customer is upset, the situation is complex, or they explicitly ask for a person."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "summary": {"type": "string", "description": "Brief summary of the conversation so far"},
            },
            "required": ["reason"],
        },
    },
]

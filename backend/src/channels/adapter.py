"""
Channel adapter — normalises all inbound messages to a common shape
before hitting the orchestrator. Adding SMS/email later = new function here,
no changes to orchestrator or actions.

Normalised shape:
{
    "channel":    "voice" | "sms" | "email" | "webchat",
    "customer_id": str,
    "tenant_id":   str,
    "message":     str,
    "metadata":    dict   # channel-specific (call_sid, thread_id, etc.)
}
"""


def from_voice(*, call_sid: str, transcript: str, tenant_id: str, customer_id: str) -> dict:
    return {
        "channel": "voice",
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "message": transcript,
        "metadata": {"call_sid": call_sid},
    }


# Stubs for future channels — same orchestrator handles all of these

def from_sms(*, message_sid: str, body: str, from_: str, tenant_id: str, customer_id: str) -> dict:
    return {
        "channel": "sms",
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "message": body,
        "metadata": {"message_sid": message_sid, "from": from_},
    }


def from_email(*, message_id: str, subject: str, body: str, from_: str, tenant_id: str, customer_id: str) -> dict:
    return {
        "channel": "email",
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "message": f"Subject: {subject}\n\n{body}",
        "metadata": {"message_id": message_id, "from": from_},
    }

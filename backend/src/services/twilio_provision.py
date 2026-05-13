"""
Twilio phone number lifecycle management.

provision_phone_number() — buy a Canadian local number and wire it to this backend.
release_phone_number(sid) — release a number back to Twilio when an account closes.
"""
from __future__ import annotations

from twilio.rest import Client as TwilioClient

from src.config import settings
from src.utils.logger import logger


def _client() -> TwilioClient:
    return TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)


def provision_phone_number() -> tuple[str, str]:
    """
    Purchase an available Canadian local number and configure webhooks.
    Returns (phone_e164, twilio_sid).
    Raises RuntimeError if no numbers are available.
    """
    client = _client()

    available = client.available_phone_numbers("CA").local.list(limit=1)
    if not available:
        raise RuntimeError("No Canadian Twilio phone numbers available in the pool")

    voice_url = f"{settings.base_url}/incoming-call" if settings.base_url else ""

    number = client.incoming_phone_numbers.create(
        phone_number=available[0].phone_number,
        voice_url=voice_url,
        voice_method="POST",
    )

    logger.info("Provisioned Twilio number", phone=number.phone_number, sid=number.sid)
    return number.phone_number, number.sid


def release_phone_number(twilio_sid: str) -> None:
    """Release a Twilio number back to the pool."""
    client = _client()
    client.incoming_phone_numbers(twilio_sid).delete()
    logger.info("Released Twilio number", sid=twilio_sid)

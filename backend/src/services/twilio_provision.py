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


PROVINCE_AREA_CODES: dict[str, dict[str, list[str]]] = {
    "BC": {
        "vancouver": ["604", "778", "236", "672", "257"],
        "victoria": ["250", "778", "236"],
        "kelowna": ["250", "778", "236"],
        "kamloops": ["250", "778", "236"],
        "nanaimo": ["250", "778", "236"],
        "prince george": ["250", "778", "236"],
        "surrey": ["604", "778", "236", "672", "257"],
        "burnaby": ["604", "778", "236", "672", "257"],
        "richmond": ["604", "778", "236", "672", "257"],
        "langley": ["604", "778", "236", "672", "257"],
        "abbotsford": ["604", "778", "236", "672", "257"],
        "coquitlam": ["604", "778", "236", "672", "257"],
        "_default": ["604", "778", "236"],
    },
    "AB": {
        "calgary": ["403", "587", "825"],
        "edmonton": ["780", "587", "825"],
        "red deer": ["403", "587"],
        "lethbridge": ["403", "587"],
        "_default": ["403", "780", "587"],
    },
    "ON": {
        "toronto": ["416", "647", "437"],
        "mississauga": ["905", "289", "365"],
        "brampton": ["905", "289", "365"],
        "hamilton": ["905", "289", "365"],
        "ottawa": ["613", "343"],
        "london": ["519", "226", "548"],
        "kitchener": ["519", "226", "548"],
        "windsor": ["519", "226", "548"],
        "_default": ["416", "647", "905"],
    },
    "QC": {
        "montreal": ["514", "438"],
        "quebec city": ["418", "581", "367"],
        "laval": ["450", "579"],
        "gatineau": ["819", "873"],
        "_default": ["514", "438", "450"],
    },
    "MB": {
        "winnipeg": ["204", "431"],
        "_default": ["204", "431"],
    },
    "SK": {
        "saskatoon": ["306", "639"],
        "regina": ["306", "639"],
        "_default": ["306", "639"],
    },
    "NS": {
        "_default": ["902", "782"],
    },
    "NB": {
        "_default": ["506"],
    },
    "NL": {
        "_default": ["709"],
    },
    "PE": {
        "_default": ["902"],
    },
}


def _area_codes_for(city: str | None, province: str | None) -> list[str]:
    prov = (province or "").strip().upper()
    city_key = (city or "").strip().lower()
    prov_map = PROVINCE_AREA_CODES.get(prov, {})
    codes = prov_map.get(city_key) or prov_map.get("_default", [])
    return codes


def provision_phone_number(city: str | None = None, province: str | None = None) -> tuple[str, str]:
    """
    Purchase an available Canadian local number matching the tenant's city/province
    area codes and configure webhooks. Falls back to any Canadian number.
    Returns (phone_e164, twilio_sid).
    Raises RuntimeError if no numbers are available.
    """
    client = _client()

    area_codes = _area_codes_for(city, province)
    available = None

    for code in area_codes:
        available = client.available_phone_numbers("CA").local.list(
            area_code=code, limit=1
        )
        if available:
            break

    if not available:
        available = client.available_phone_numbers("CA").local.list(limit=1)

    if not available:
        raise RuntimeError("No Canadian Twilio phone numbers available in the pool")

    voice_url = f"{settings.base_url}/incoming-call" if settings.base_url else ""

    number = client.incoming_phone_numbers.create(
        phone_number=available[0].phone_number,
        voice_url=voice_url,
        voice_method="POST",
    )

    logger.info("Provisioned Twilio number", phone=number.phone_number, sid=number.sid, area_codes_tried=area_codes)
    return number.phone_number, number.sid


def release_phone_number(twilio_sid: str) -> None:
    """Release a Twilio number back to the pool."""
    client = _client()
    client.incoming_phone_numbers(twilio_sid).delete()
    logger.info("Released Twilio number", sid=twilio_sid)

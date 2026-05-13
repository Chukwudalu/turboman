import asyncio

from twilio.rest import Client
from src.config import settings
from src.utils.logger import logger

_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def send_sms(to_phone: str, message: str, from_phone: str) -> bool:
    """Send an SMS. Returns True on success, False on failure (never raises)."""
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: _client.messages.create(
                body=message,
                from_=from_phone,
                to=to_phone,
            ),
        )
        logger.info("SMS sent", to=to_phone, from_=from_phone)
        return True
    except Exception as e:
        logger.error("SMS send failed", to=to_phone, error=str(e))
        return False


async def send_confirmation_sms(to_phone: str, message: str, from_phone: str) -> None:
    await send_sms(to_phone, message, from_phone)

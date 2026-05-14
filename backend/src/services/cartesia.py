from __future__ import annotations
from collections.abc import Callable, AsyncGenerator
import httpx
import sentry_sdk
from src.config import settings
from src.utils.logger import logger


async def stream_tts(
    text: str,
    on_audio_chunk: Callable[[bytes], None],
    on_done: Callable[[], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    voice_id: str | None = None,
):
    """
    Stream TTS audio from Cartesia.
    Calls on_audio_chunk(bytes) as each chunk arrives so we pipe
    it straight back to Twilio without buffering the full response.
    """
    if not text or not text.strip():
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            async with client.stream(
                "POST",
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "X-API-Key": settings.cartesia_api_key,
                    "Cartesia-Version": "2024-06-10",
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": settings.cartesia_model,
                    "transcript": text,
                    "voice": {"mode": "id", "id": voice_id or settings.cartesia_voice_id},
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_mulaw",   # matches Twilio 8kHz mulaw
                        "sample_rate": 8000,
                    },
                },
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    on_audio_chunk(chunk)

        if on_done:
            on_done()

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error("Cartesia TTS error", error=str(e))
        if on_error:
            on_error(e)

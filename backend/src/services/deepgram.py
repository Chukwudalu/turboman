from __future__ import annotations
import asyncio
from collections.abc import Callable
import sentry_sdk
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from src.config import settings
from src.utils.logger import logger


class STTStream:
    def __init__(
        self,
        on_transcript: Callable[[str], None],
        on_partial: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ):
        self._on_transcript = on_transcript
        self._on_partial = on_partial
        self._on_error = on_error
        self._connection = None
        self._frame_count = 0

    async def connect(self):
        dg = DeepgramClient(settings.deepgram_api_key)
        self._connection = dg.listen.asyncwebsocket.v("1")

        options = LiveOptions(
            model=settings.deepgram_model,
            language="en-US",
            smart_format=True,
            interim_results=True,
            endpointing=settings.deepgram_endpointing_ms,
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
        )

        self._connection.on(LiveTranscriptionEvents.Transcript, self._handle_transcript)
        self._connection.on(LiveTranscriptionEvents.Error, self._handle_error)

        await self._connection.start(options)
        logger.debug("Deepgram STT stream opened")

    async def _handle_transcript(self, _client=None, result=None, **kwargs):
        # deepgram asynclive emits handler(deepgram_client, result=result) and awaits the coroutine
        if result is None:
            result = kwargs.get("result")
        if result is None:
            return

        alt = result.channel.alternatives[0] if result.channel.alternatives else None
        if not alt:
            logger.info("STT no alternatives in result")
            return
        if not alt.transcript:
            logger.info("STT empty transcript", is_final=result.is_final)
            return

        logger.info("STT transcript", text=alt.transcript, is_final=result.is_final, confidence=getattr(alt, "confidence", None))

        if result.is_final:
            await self._on_transcript(alt.transcript)
        elif self._on_partial:
            self._on_partial(alt.transcript)

    async def _handle_error(self, _client=None, error=None, **kwargs):
        if error is None:
            error = kwargs.get("error", str(kwargs))
        exc = error if isinstance(error, Exception) else Exception(f"Deepgram STT error: {error}")
        sentry_sdk.capture_exception(exc)
        logger.error("Deepgram error", error=str(error))
        if self._on_error:
            self._on_error(error)

    def send(self, audio_bytes: bytes):
        """Send inbound caller audio to Deepgram."""
        if self._connection:
            self._frame_count += 1
            if self._frame_count % 100 == 0:
                logger.info("STT frames sent", count=self._frame_count)
            asyncio.ensure_future(self._connection.send(audio_bytes))

    async def close(self):
        if self._connection:
            await self._connection.finish()
            logger.debug("Deepgram STT stream closed", total_frames=self._frame_count)

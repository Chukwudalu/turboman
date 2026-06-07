"""
    Ignore this file. This is just for practicing the code in __init__.py

"""


from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect
from twilio.rest import Client as TwilioClient

import sentry_sdk

from src.config import settings
from src.db.queries import create_call, create_escalation, end_call, get_tenant_by_phone, upsert_customer
from src.db.rag import search_kb
from src.utils.business_hours import is_after_hours as _is_after_hours
from src.orchestrator import run_turn
from src.services.cartesia import stream_tts
from src.services.deepgram import STTStream
from src.services.notifications import send_confirmation_sms
from src.utils.logger import logger

# Mulaw 8kHz = 1 byte per sample, so bytes / 8000 = seconds of audio
_MULAW_BYTES_PER_SECOND = 8000

# Minimum caller transcript length — skip noise/breathing below this
_MIN_TRANSCRIPT_CHARS = 3

# Minimum word count in a partial transcript to trigger barge-in
_BARGE_IN_WORD_THRESHOLD = 2

# Maximum conversation turns to keep in history (prevents token explosion)
_MAX_HISTORY_MESSAGES = 20

# Phrases that unambiguously signal the caller is ending the conversation
_GOODBYE_KEYWORDS = (
    "bye", "goodbye", "good bye", "farewell",
    "have a good day", "have a great day", "have a nice day",
    "take care", "good night", "goodnight",
    "talk soon", "see you later", "see ya",
)

def _is_goodbye(text:str) -> bool:
    t = text.lower().strip()
    return any(kw in t for kw in _GOODBYE_KEYWORDS)



@dataclass
class CallState:
    call_sid: str=""
    stream_sid: str=""
    tenant: dict = field(default_factory=dict)
    customer: dict = field(default_factory=dict)
    call_record: dict | None = None
    history: list[dict] = field(default_factory=list)
    kb_context: list[str] = field(default_factory=list)
    transcript_lines: list[str] = field(default_factory=list)
    is_speaking: bool = False
    is_escalated: bool = False
    start_time: float = field(default_factory=time.time)
    reprompt_count: int = 0
    silence_task: asyncio.Task | None = None
    #Active LLM+TTS turn -Cancelled on barge-in or new input
    _turn_task: asyncio.Task | None = None
    #Debounce state - accumulates transcripts and fire after a quiet window
    _debounce_task: asyncio.Task | None = None
    _pending_transript: str = ""
    redis_client: any = field(default=None)
    escalate_summary: str = ""


async def handle_call_websocket(websocket: WebSocket, redis_client):
    await websocket.accept()
    state = CallState()
    state.redis_client = redis_client

    async def on_transcript(text: str):
        #Ignore noise/breathing - wait for real words
        if len(text.strip()) < _MIN_TRANSCRIPT_CHARS:
            return
        
        # cancel timer immediately on any real speech
        _cancel_silence_timer(state)
        state.reprompt_count = 0

        # Accumulate - Deepgram can fire multiple is_final events during a
        # Single natural utterance when the speaker has brief mid-sentence pauses
        state._pending_transript = (
            state._pending_transript + " " + text.strip()
        ).strip()

        _cancel_debounce(state)

        async def _fire():
            await asyncio.sleep(settings.transcript_debounce_ms / 1000)

            full_text = state._pending_transript
            state._pending_transript = ""

            #cancel in-flight turn and clear audio buffer
            _cancel_turn(state)
            if state._is_speaking:
                await _stop_speaking(websocket, state)
            
            logger.info("caller said", text=full_text)
            state.transcript_lines.append(f"caller: {full_text}")

            if _is_goodbye(full_text):
                state._turn_task = asyncio.create_task(
                    _end_call_gracefully(websocket, state)
                )
                return
            
            if state.tenant.get("id"):
                state.kb_context = await search_kb(state.tenant["id"], full_text)
            
            state._turn_task = asyncio.create_task(
                _handle_caller_turn(websocket, state, full_text)
            )

        state._debounce_task = asyncio.create_task(_fire())

    
    def on_partial(text: str):
        """Barge-In: Customer started speaking while AI is playing"""
        words = text.strip().split()
        if state.is_speaking and len(words) >= _BARGE_IN_WORD_THRESHOLD:
            _cancel_turn(state)
            _cancel_debounce(state)
            asyncio.ensure_future(_stop_speaking(websocket, state))

    def on_stt_error(e: Exception):
        sentry_sdk.capture_exception(e)
        logger.error("STT error - escalating to human", error=str(e))
        _cancel_turn(state)
        _cancel_debounce(state)
        asyncio.ensure_future(_handle_escalation(websocket, state))


    stt = STTStream(
        on_transcript=on_transcript,
        on_partial=on_partial,
        on_error=on_stt_error
    )

    try:
        await stt.connect()
        logger.info("Deepgram STT Connected")
    except Exception as e:
        logger.error("Deepgram STT connect failed - hanging up", error=str(e))
        await websocket.close()
        return
    
    try:
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            event = msg.get(event)

            if event == "start":
                state.call_sid = msg['start']["callsid"]
                state.stream_sid = msg["start"]["streamSid"]

    except:
        pass
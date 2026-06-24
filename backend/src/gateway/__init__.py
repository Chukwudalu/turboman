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
from src.db.queries import create_call, end_call, get_tenant_by_phone, upsert_customer
from src.db.rag import search_kb
from src.orchestrator import run_turn
from src.services.cartesia import stream_tts
from src.services.deepgram import STTStream
from src.services.notifications import send_confirmation_sms
from src.utils.logger import logger

_twilio = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)

# Mulaw 8kHz = 1 byte per sample, so bytes / 8000 = seconds of audio
_MULAW_BYTES_PER_SECOND = 8000

# Minimum caller transcript length — skip noise/breathing below this
_MIN_TRANSCRIPT_CHARS = 3

# Minimum word count in a partial transcript to trigger barge-in
_BARGE_IN_WORD_THRESHOLD = 3

# Maximum conversation turns to keep in history (prevents token explosion)
_MAX_HISTORY_MESSAGES = 20

# Phrases that unambiguously signal the caller is ending the conversation
_GOODBYE_KEYWORDS = (
    "bye", "goodbye", "good bye", "farewell",
    "have a good day", "have a great day", "have a nice day",
    "take care", "good night", "goodnight",
    "talk soon", "see you later", "see ya",
)


def _is_goodbye(text: str) -> bool:
    t = text.lower().strip()
    return any(kw in t for kw in _GOODBYE_KEYWORDS)


@dataclass
class CallState:
    call_sid: str = ""
    stream_sid: str = ""
    tenant: dict = field(default_factory=dict)
    customer: dict | None = None
    call_record: dict | None = None
    history: list[dict] = field(default_factory=list)
    kb_context: list[str] = field(default_factory=list)
    transcript_lines: list[str] = field(default_factory=list)
    is_speaking: bool = False
    is_ended: bool = False
    should_transfer: bool = False
    start_time: float = field(default_factory=time.time)
    reprompt_count: int = 0
    silence_task: asyncio.Task | None = None
    # Active LLM+TTS turn — cancelled on barge-in or new input
    _turn_task: asyncio.Task | None = None
    # Debounce state — accumulates transcripts and fires after a quiet window
    _debounce_task: asyncio.Task | None = None
    _pending_transcript: str = ""
    redis_client: any = field(default=None)


async def handle_call_websocket(websocket: WebSocket, redis_client):
    await websocket.accept()
    state = CallState()
    state.redis_client = redis_client

    async def on_transcript(text: str):
        # Ignore noise/breathing — wait for real words
        if len(text.strip()) < _MIN_TRANSCRIPT_CHARS:
            return

        # Cancel silence timer immediately on any real speech
        _cancel_silence_timer(state)
        state.reprompt_count = 0

        # Accumulate — Deepgram can fire multiple is_final events during a
        # single natural utterance when the speaker has brief mid-sentence pauses.
        state._pending_transcript = (
            state._pending_transcript + " " + text.strip()
        ).strip()

        # Reset the debounce window on every new transcript
        _cancel_debounce(state)

        async def _fire():
            await asyncio.sleep(settings.transcript_debounce_ms / 1000)

            full_text = state._pending_transcript
            state._pending_transcript = ""

            # Cancel in-flight turn and clear audio buffer
            _cancel_turn(state)
            if state.is_speaking:
                await _stop_speaking(websocket, state)

            logger.info("Caller said", text=full_text)
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
        """Barge-in + silence timer reset: customer started speaking."""
        if text.strip():
            _cancel_silence_timer(state)

        words = text.strip().split()
        if state.is_speaking and len(words) >= _BARGE_IN_WORD_THRESHOLD:
            _cancel_turn(state)
            _cancel_debounce(state)
            asyncio.ensure_future(_stop_speaking(websocket, state))

    def on_stt_error(e: Exception):
        sentry_sdk.capture_exception(e)
        logger.error("STT error", error=str(e))
        _cancel_turn(state)
        _cancel_debounce(state)

    stt = STTStream(
        on_transcript=on_transcript,
        on_partial=on_partial,
        on_error=on_stt_error,
    )
    try:
        await stt.connect()
        logger.info("Deepgram STT connected")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error("Deepgram STT connect failed", error=str(e))
        return

    try:
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                state.call_sid   = msg["start"]["callSid"]
                state.stream_sid = msg["start"]["streamSid"]
                params           = msg["start"].get("customParameters", {})
                try:
                    await _on_call_start(websocket, state, params, redis_client)
                except Exception as e:
                    logger.error("Call setup failed", error=str(e))
                    break
                _start_silence_timer(websocket, state)

            elif event == "media":
                media = msg.get("media", {})
                if media.get("track", "inbound") == "inbound":
                    payload = media.get("payload")
                    if payload:
                        stt.send(base64.b64decode(payload))

            elif event == "stop":
                break

    except (WebSocketDisconnect, RuntimeError):
        logger.info("Call WebSocket disconnected")
    finally:
        _cancel_debounce(state)
        _cancel_turn(state)
        await stt.close()
        _cancel_silence_timer(state)
        if state.call_record and not state.is_ended:
            state.is_ended = True
            duration = int(time.time() - state.start_time)
            transcript = "\n".join(state.transcript_lines)
            await end_call(state.call_record["id"], "completed", duration, transcript)
        sentry_sdk.add_breadcrumb(
            message="Call ended",
            data={
                "call_sid": state.call_sid,
                "duration_s": int(time.time() - state.start_time),
                "turns": len(state.history),
            },
        )


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _on_call_start(
    websocket: WebSocket, state: CallState, params: dict, redis_client
):
    logger.info("Call started", call_sid=state.call_sid)

    called_phone = params.get("to", "")
    tenant_json = await redis_client.get(f"tenant:phone:{called_phone}")
    if tenant_json:
        state.tenant = json.loads(tenant_json)
    else:
        tenant = await get_tenant_by_phone(called_phone)
        if tenant:
            state.tenant = tenant
            await redis_client.set(f"tenant:phone:{called_phone}", json.dumps(tenant), ex=86400)
        else:
            logger.error("No tenant found for phone", phone=called_phone)
            await _speak_and_wait(
                websocket, state,
                "We're sorry, we're unable to connect your call at this time. "
                "Please try again later. Goodbye.",
            )
            await websocket.close()
            return

    caller_phone = params.get("from", "unknown")
    state.customer = await upsert_customer(state.tenant["id"], caller_phone)
    if state.tenant.get("remember_caller_info", True) and state.customer.get("id"):
        from src.db import db as _db
        last_sr = await (
            _db.table("service_requests")
            .select("address")
            .eq("customer_id", state.customer["id"])
            .not_.is_("address", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if last_sr.data:
            state.customer["last_address"] = last_sr.data[0]["address"]
    state.call_record = await create_call(state.tenant["id"], state.customer["id"], state.call_sid)

    sentry_sdk.set_tag("call_sid", state.call_sid)
    sentry_sdk.set_tag("tenant_id", state.tenant.get("id", ""))
    sentry_sdk.set_context("call", {
        "call_sid": state.call_sid,
        "tenant": state.tenant.get("name", "unknown"),
        "customer_phone": caller_phone,
    })

    name = state.customer.get("name")
    if name:
        greeting = (
            f"Hi {name}, thanks for calling {state.tenant['name']}! "
            "Before we get started, could I get the address where you need our services?"
        )
    else:
        greeting = (
            f"Thanks for calling {state.tenant['name']}! "
            "To get started, could I please have your name and service address?"
        )
    # Wait for the greeting to finish playing before the silence timer starts
    await _speak_and_wait(websocket, state, greeting)


async def _handle_caller_turn(websocket: WebSocket, state: CallState, user_input: str):
    try:
        # Track audio bytes and stream time across all sentences so we can
        # calculate remaining Twilio playback time after the LLM is done.
        total_bytes = 0
        total_stream_elapsed = 0.0

        async def on_chunk(chunk: str):
            nonlocal total_bytes, total_stream_elapsed
            # _speak streams each sentence without waiting for playback,
            # allowing the next sentence to be queued in Twilio immediately.
            b, t = await _speak(websocket, state, chunk)
            total_bytes += b
            total_stream_elapsed += t

        async def on_action(action: dict):
            name, result = action["name"], action["result"]
            logger.info("Action taken", name=name, success=result.get("success"))
            if name == "save_customer_info" and result.get("success") and state.customer:
                customer_name = action["input"].get("name")
                if customer_name:
                    state.customer["name"] = customer_name
            if name == "book_job" and result.get("success") and state.customer:
                phone = state.customer.get("phone")
                if phone:
                    await send_confirmation_sms(phone, result["message"], state.tenant.get("phone"))
            if name == "transfer_call" and result.get("transfer"):
                state.should_transfer = True

        try:
            result = await run_turn(
                tenant=state.tenant,
                customer=state.customer,
                kb_context=state.kb_context,
                history=state.history,
                user_input=user_input,
                on_chunk=on_chunk,
                on_action=on_action,
                call_id=state.call_record["id"] if state.call_record else None,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error("LLM turn failed", error=str(e))
            await _speak_and_wait(websocket, state,
                "I'm sorry, I had a technical issue. Your request has been noted and someone from the team will follow up. Thank you for calling.")
            return

        # Keep history bounded to avoid token explosion on long calls
        updated = result["updated_history"]
        if len(updated) > _MAX_HISTORY_MESSAGES:
            updated = updated[-_MAX_HISTORY_MESSAGES:]
            # Always start on a user turn — never leave an orphaned assistant message
            while updated and updated[0]["role"] != "user":
                updated = updated[1:]
        state.history = updated
        state.transcript_lines.append(f"agent: {result['response_text']}")

        if state.should_transfer:
            await _transfer_call(websocket, state)
            return

        # Twilio has the audio queued but hasn't finished playing it yet.
        # Wait for remaining playback before marking as done and starting the
        # silence timer — otherwise the reprompt fires while AI is still audible.

        #NOTE: IMPORTANT - This might be a place 
        audio_duration = total_bytes / _MULAW_BYTES_PER_SECOND
        remaining_playback = max(0.0, audio_duration - total_stream_elapsed) + 0.5
        await asyncio.sleep(remaining_playback)
        state.is_speaking = False

        _start_silence_timer(websocket, state)

    except asyncio.CancelledError:
        state.is_speaking = False
        raise


async def _speak(websocket: WebSocket, state: CallState, text: str) -> tuple[int, float]:
    """
    Stream TTS to Twilio without waiting for playback to complete.
    Returns (bytes_sent, stream_duration_s) so callers can calculate
    remaining Twilio playback time themselves.
    """
    if not text.strip():
        return 0, 0.0
    state.is_speaking = True
    total_bytes = 0

    def on_chunk(audio_bytes: bytes):
        nonlocal total_bytes
        total_bytes += len(audio_bytes)
        if websocket.client_state.value == 1:  # CONNECTED
            asyncio.ensure_future(websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": state.stream_sid,
                "media": {"payload": base64.b64encode(audio_bytes).decode()},
            })))

    def on_tts_error(e: Exception):
        state.is_speaking = False
        logger.error("TTS error during speech", error=str(e))

    voice_id = state.tenant.get("cartesia_voice_id") or None
    t0 = time.monotonic()
    await stream_tts(text, on_audio_chunk=on_chunk, voice_id=voice_id, on_error=on_tts_error)
    return total_bytes, time.monotonic() - t0


async def _speak_and_wait(websocket: WebSocket, state: CallState, text: str):
    """
    Stream TTS and wait for Twilio to finish playing before returning.
    Use for single phrases where the next action depends on playback completing
    (greeting, reprompts, escalation hold message).
    """
    b, elapsed = await _speak(websocket, state, text)
    audio_duration = b / _MULAW_BYTES_PER_SECOND
    remaining = max(0.0, audio_duration - elapsed) + 0.3
    await asyncio.sleep(remaining)
    state.is_speaking = False


async def _stop_speaking(websocket: WebSocket, state: CallState):
    """Tell Twilio to discard its audio buffer (barge-in)."""
    state.is_speaking = False
    try:
        await websocket.send_text(json.dumps({
            "event": "clear",
            "streamSid": state.stream_sid,
        }))
    except Exception:
        pass


async def _end_call_gracefully(websocket: WebSocket, state: CallState):
    """Say a brief farewell and close the call cleanly."""
    _cancel_silence_timer(state)
    await _speak_and_wait(websocket, state, "Thanks for calling! Have a great day. Goodbye!")
    try:
        await websocket.close()
    except Exception:
        pass


def _cancel_turn(state: CallState):
    """Cancel the in-flight LLM+TTS task."""
    if state._turn_task and not state._turn_task.done():
        state._turn_task.cancel()
    state._turn_task = None


def _cancel_debounce(state: CallState):
    """Cancel the pending transcript debounce timer."""
    if state._debounce_task and not state._debounce_task.done():
        state._debounce_task.cancel()
    state._debounce_task = None


def _start_silence_timer(websocket: WebSocket, state: CallState):
    _cancel_silence_timer(state)

    async def _timer():
        await asyncio.sleep(settings.silence_reprompt_ms / 1000)

        if state.reprompt_count >= settings.max_reprompts:
            await _speak_and_wait(websocket, state,
                "It looks like we may have lost you. Thanks so much for calling — "
                "feel free to ring us back anytime. Take care, goodbye!")
            await websocket.close()
            return

        state.reprompt_count += 1
        await _speak_and_wait(websocket, state,
            "Are you still there? Take your time — I'm here whenever you're ready.")
        _start_silence_timer(websocket, state)

    state.silence_task = asyncio.create_task(_timer())


def _cancel_silence_timer(state: CallState):
    if state.silence_task and not state.silence_task.done():
        state.silence_task.cancel()
    state.silence_task = None


async def _transfer_call(websocket: WebSocket, state: CallState):
    """Transfer the active call to the tenant's escalation phone number via Twilio."""
    if state.is_ended:
        return
    state.is_ended = True

    _cancel_silence_timer(state)

    escalation_phone = (
        state.tenant.get("escalation_phone")
        or state.tenant.get("escalation_phone_after_hours")
        or settings.escalation_phone
    )

    import re as _re
    if not escalation_phone or not _re.match(r"^\+[1-9]\d{7,14}$", escalation_phone):
        logger.warning("No valid escalation phone — cannot transfer", tenant_id=state.tenant.get("id"))
        await _speak_and_wait(websocket, state,
            "I'm sorry, I'm unable to transfer you right now. "
            "I've logged your request and someone from the team will call you back as soon as possible.")
        return

    if state.call_record:
        duration = int(time.time() - state.start_time)
        await end_call(state.call_record["id"], "transferred", duration, "\n".join(state.transcript_lines))

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Dial timeout="30">{escalation_phone}</Dial></Response>'
    )
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: _twilio.calls(state.call_sid).update(twiml=twiml))
        logger.info("Call transferred", to=escalation_phone)
    except Exception as e:
        logger.error("Call transfer failed", error=str(e))



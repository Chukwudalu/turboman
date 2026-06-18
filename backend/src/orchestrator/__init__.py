from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import anthropic

from src.config import settings
from src.orchestrator.prompts import build_system_prompt
from src.orchestrator.tools import TOOLS
from src.utils.logger import logger
from src.utils.sanitize import sanitize_caller_input
from src.utils.sentence_boundary import extract_flushable_chunk, is_end_of_response

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def run_turn(
    *,
    tenant: dict,
    customer: dict | None,
    kb_context: list[str],
    history: list[dict],
    user_input: str,
    on_chunk: Callable[[str], Any],
    on_action: Callable[[dict], Any] | None = None,
    call_id: str | None = None,
) -> dict:
    """
    Run one conversation turn.

    Streams LLM output and calls on_chunk() at sentence boundaries so TTS
    can start playing before the full response is generated.

    The system prompt is marked cache_control=ephemeral — it stays identical
    across every turn of a call, so Claude caches it after the first turn,
    cutting per-turn cost by ~70% and latency by ~30ms.

    Returns: { response_text, updated_history }
    """
    clean = sanitize_caller_input(user_input)

    if clean == "[FLAGGED_INPUT]":
        logger.warn("Prompt injection attempt detected")
        msg = "I'm sorry, I didn't quite catch that. Could you rephrase?"
        await on_chunk(msg)
        return {"response_text": msg, "updated_history": history}

    messages = [*history, {"role": "user", "content": clean}]

    # System prompt as a cacheable content block.
    # Claude caches this after the first request in the call; subsequent turns
    # pay only the small cache-read fee instead of full input-token cost.
    system = [
        {
            "type": "text",
            "text": build_system_prompt(tenant, customer, kb_context),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    full_response = ""
    buffer = ""

    # ── Streaming LLM call ─────────────────────────────────────────────────────
    async with client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
        system=system,
        tools=TOOLS,
        messages=messages,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        timeout=45.0,
    ) as stream:
        async for event in stream:
            # Text tokens — flush at sentence boundaries for low-latency TTS
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                buffer += event.delta.text
                full_response += event.delta.text

                chunk, buffer = extract_flushable_chunk(buffer)
                if chunk:
                    await on_chunk(chunk)

            # Flush any dangling text when a content block closes
            if event.type == "content_block_stop" and buffer.strip():
                if is_end_of_response(buffer, False):
                    await on_chunk(buffer.strip())
                    buffer = ""

        # Flush whatever's left after the stream ends
        if buffer.strip():
            await on_chunk(buffer.strip())
            buffer = ""

        final_msg = await stream.get_final_message()
        tool_uses = [b for b in final_msg.content if b.type == "tool_use"]

    # ── Handle tool calls ──────────────────────────────────────────────────────
    if tool_uses:
        from src.actions import route_action

        tool_results = []
        for tool in tool_uses:
            logger.info("Tool invoked", tool=tool.name)
            result = await route_action(tool.name, tool.input, tenant=tenant, customer=customer, call_id=call_id)

            if on_action:
                await on_action({"name": tool.name, "input": tool.input, "result": result})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": json.dumps(result),
            })

        # Continue conversation with tool results (non-streaming — usually 1 sentence)
        continued = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            system=system,
            tools=TOOLS,
            messages=[
                *messages,
                {"role": "assistant", "content": final_msg.content},
                {"role": "user", "content": tool_results},
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            timeout=45.0,
        )
        follow_up = next((b.text for b in continued.content if b.type == "text"), "")
        full_response += follow_up
        if follow_up:
            await on_chunk(follow_up)

    updated_history = [*messages, {"role": "assistant", "content": full_response}]
    return {"response_text": full_response, "updated_history": updated_history}

import re

# Flush to TTS at these boundaries so audio starts before LLM finishes
_BOUNDARY_RE = re.compile(r'[.!?]+[\s"\')\]]*(?:\s|$)|[,;:]\s{1,2}(?=[A-Z])')


def extract_flushable_chunk(buffer: str) -> tuple[str | None, str]:
    """
    Split buffer at the first sentence boundary.
    Returns (chunk_to_speak, remaining_buffer).
    Returns (None, buffer) if no boundary found yet.
    """
    match = _BOUNDARY_RE.search(buffer)
    if not match:
        return None, buffer

    idx = match.end()
    return buffer[:idx].strip(), buffer[idx:]


def is_end_of_response(buffer: str, is_done: bool) -> bool:
    """Flush remaining buffer when the LLM stream is complete."""
    return is_done and bool(buffer.strip())

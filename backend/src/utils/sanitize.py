import re

_INJECTION_PATTERNS = [
    re.compile(r"ignore\b.{0,40}\binstructions\b", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"disregard (your|the|all)", re.I),
    re.compile(r"forget (everything|all|your)", re.I),
]

_HTML_TAG_RE = re.compile(r"<[^>]*>")
MAX_INPUT_LEN = 500


def sanitize_caller_input(text: str | None) -> str:
    """
    Clean caller transcript before it reaches the LLM.
    Returns '[FLAGGED_INPUT]' if prompt injection is detected —
    the orchestrator will escalate these calls.
    """
    if not text:
        return ""

    # Strip any HTML/markup
    clean = _HTML_TAG_RE.sub("", text)

    # Check for injection attempts
    if any(p.search(clean) for p in _INJECTION_PATTERNS):
        return "[FLAGGED_INPUT]"

    return clean[:MAX_INPUT_LEN].strip()

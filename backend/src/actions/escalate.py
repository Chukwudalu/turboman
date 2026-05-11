async def escalate(inputs: dict, **_) -> dict:
    # Signals callHandler to initiate warm transfer
    return {
        "success": True,
        "escalate": True,
        "reason": inputs.get("reason"),
        "summary": inputs.get("summary"),
        "message": "Let me get someone from the team to help you right away. Please hold for just a moment.",
    }

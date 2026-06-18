async def transfer_call(inputs: dict, **_) -> dict:
    return {
        "success": True,
        "transfer": True,
        "reason": inputs.get("reason"),
        "message": "Let me transfer you to a team member. Please hold for just a moment.",
    }

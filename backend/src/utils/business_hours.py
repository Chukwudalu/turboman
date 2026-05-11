from __future__ import annotations

from datetime import datetime
import zoneinfo


def is_after_hours(tenant: dict) -> bool:
    """Return True if the current time is outside the tenant's business hours."""
    tz_str = tenant.get("business_timezone") or "America/New_York"
    start_str = tenant.get("business_hours_start") or "09:00"
    end_str = tenant.get("business_hours_end") or "17:00"

    try:
        tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("America/New_York")

    now = datetime.now(tz)

    # Weekends are always after hours
    if now.weekday() >= 5:
        return True

    try:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
    except (ValueError, AttributeError):
        sh, sm, eh, em = 9, 0, 17, 0

    now_mins = now.hour * 60 + now.minute
    return now_mins < (sh * 60 + sm) or now_mins >= (eh * 60 + em)

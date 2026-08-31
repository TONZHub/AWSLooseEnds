"""Deterministic resolution of explicit timing phrases for Pocket Promise v2.

The Arbiter model identifies the exact timing words from a source message. This
module, not the model, turns supported phrases into timezone-aware datetimes.
Unsupported or vague phrases deliberately resolve to ``None`` rather than
inventing precision.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_TIME_RE = re.compile(
    r"\b(?P<hour>1[0-2]|0?[1-9])(?::(?P<minute>[0-5]\d))?\s*"
    r"(?P<ampm>a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)
_WEEKDAY_RE = re.compile(
    r"\b(?P<next>next\s+)?"
    r"(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)


def _clock_time(text: str) -> time | None:
    lowered = text.casefold()
    if re.search(r"\bnoon\b", lowered):
        return time(12, 0)
    if re.search(r"\bmidnight\b", lowered):
        return time(0, 0)

    match = _TIME_RE.search(text)
    if match is None:
        return None

    hour = int(match.group("hour"))
    minute = int(match.group("minute") or "0")
    ampm = match.group("ampm").replace(".", "").casefold()
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    return time(hour, minute)


def resolve_due_at(
    *,
    time_phrase: str | None,
    occurred_at: datetime,
    timezone_name: str,
) -> datetime | None:
    """Resolve a supported explicit timing phrase relative to its source message.

    Supported date anchors are ``today``, ``tomorrow``, and named weekdays,
    optionally prefixed by ``next``. A concrete clock time (for example 3 PM,
    3:30 p.m., noon, or midnight) is also required. Vague phrases such as
    ``Tuesday evening`` intentionally return ``None``.
    """

    if not time_phrase or not time_phrase.strip():
        return None
    if occurred_at.tzinfo is None:
        raise ValueError("occurred_at must include a UTC offset")

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {timezone_name}") from exc

    local_occurred = occurred_at.astimezone(zone)
    lowered = time_phrase.casefold()

    if re.search(r"\btomorrow\b", lowered):
        target_date = local_occurred.date() + timedelta(days=1)
    elif re.search(r"\btoday\b", lowered):
        target_date = local_occurred.date()
    else:
        weekday_match = _WEEKDAY_RE.search(lowered)
        if weekday_match is None:
            return None
        target_weekday = _WEEKDAYS[weekday_match.group("weekday").casefold()]
        days_ahead = (target_weekday - local_occurred.weekday()) % 7
        if weekday_match.group("next") and days_ahead == 0:
            days_ahead = 7
        target_date = local_occurred.date() + timedelta(days=days_ahead)

    clock = _clock_time(time_phrase)
    if clock is None:
        return None

    return datetime.combine(target_date, clock, tzinfo=zone)

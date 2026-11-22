"""Opt-in, local-wall-clock quiet hours for native fan speed limits.

This module only evaluates settings. Existing controller permissions and quiet
fan adapters determine whether a native command is allowed. No timer, source
state, power permission, or physical output is created by a schedule.
"""
from __future__ import annotations

from datetime import datetime, time
import math
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_CLOCK = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?\Z")


def parse_clock(value: Any) -> time | None:
    """Accept a local HH:MM or HH:MM:SS clock, without dates or time zones."""
    if not isinstance(value, str) or _CLOCK.fullmatch(value) is None:
        return None
    return time.fromisoformat(value)


def active(settings: dict, now_s: float, time_zone: str) -> bool:
    """Evaluate [start, end) in HA's zone, including overnight and DST days.

    Missing/invalid configuration is inert. Equal endpoints are not a hidden
    all-day schedule. Wall-clock evaluation applies the same interval during
    both occurrences of a repeated local hour and follows a skipped hour.
    """
    if not isinstance(settings, dict) or settings.get("quiet_hours_enabled") is not True:
        return False
    beginning = parse_clock(settings.get("quiet_hours_start", "22:00:00"))
    ending = parse_clock(settings.get("quiet_hours_end", "08:00:00"))
    if beginning is None or ending is None or beginning == ending:
        return False
    if isinstance(now_s, bool):
        return False
    try:
        timestamp = float(now_s)
        if not math.isfinite(timestamp) or timestamp < 0:
            return False
        moment = datetime.fromtimestamp(timestamp, ZoneInfo(time_zone)).time()
    except (TypeError, ValueError, OverflowError, OSError, ZoneInfoNotFoundError):
        return False
    if beginning < ending:
        return beginning <= moment < ending
    return moment >= beginning or moment < ending

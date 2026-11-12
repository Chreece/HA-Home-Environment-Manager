"""Explicit automatic or custom freshness limits, never a disabled safety check.

Automatic limits are conservative type-based defaults, *not* proof that a
physical sensor reported a fresh observation: Home Assistant's last_reported
only shows when the integration wrote its state. A same-value report refreshes
last_reported only when the provider actually republishes it.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping

MODES = ("auto", "custom")
DEFAULT_MINUTES = {"environment": 90.0, "home_presence": 240.0, "room_presence": 240.0}
WEATHER_MINUTES = 180.0
# All automatic numeric limits are finite. Change-driven contacts are only
# exempted from inactivity expiration while available and not restored.


class FreshnessLimit(float):
    """Float-compatible boundary so existing scientific consumers retain units."""

    def __new__(cls, minutes: float, *, mode: str, family: str):
        obj = float.__new__(cls, minutes)
        obj.mode = mode
        obj.family = family
        return obj


def configured_limit(config: Mapping | None, *, family: str,
                     minutes_key: str, mode_key: str) -> FreshnessLimit:
    """Fail closed to finite defaults for malformed settings, never unlimited."""
    conf = config if isinstance(config, Mapping) else {}
    default = DEFAULT_MINUTES[family]
    try:
        raw = conf.get(minutes_key, default)
        minute = float(raw) if not isinstance(raw, bool) else float("nan")
    except (ValueError, TypeError, OverflowError):
        minute = float("nan")
    if not math.isfinite(minute) or minute < 1 or minute > 100000:
        minute = default
    mode = conf.get(mode_key, "auto")
    if mode not in MODES:
        mode = "auto"
    return FreshnessLimit(minute, mode=mode, family=family)


def effective_minutes(state: Any, configured: float | None) -> float | None:
    """Return the current limit or None for valid change-driven binary inputs.

    No dynamic timing inference from unrelated state changes; a weather.*
    entity gets 180min, sampled numeric environment gets 90min, and numeric
    occupancy gets 240min. Custom always means an explicit finite timeout,
    except the already-established change-driven presence policy.
    """
    if configured is None:
        return None
    if not isinstance(configured, FreshnessLimit) or configured.mode == "custom":
        return float(configured)
    domain = getattr(state, "domain", "")
    if domain == "binary_sensor":
        # An unchanged room contact can remain authoritative indefinitely,
        # but a whole-home OFF/away binary MUST be fresh before it is allowed
        # to prove that everyone is absent. Positive Home is handled by the
        # presence policy's separate status-specific fast path.
        if configured.family == "home_presence":
            return DEFAULT_MINUTES["home_presence"]
        return None
    if configured.family == "environment":
        return WEATHER_MINUTES if domain == "weather" else DEFAULT_MINUTES["environment"]
    return DEFAULT_MINUTES[configured.family]


def observed_age_seconds(state: Any, *, now: datetime | None = None) -> float | None:
    """Use HA's last_reported even for unchanged values. No fake zero age."""
    timestamp = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        return None
    current = now or datetime.now(timezone.utc)
    age = (current - timestamp).total_seconds()
    return age if math.isfinite(age) and age >= 0 else None

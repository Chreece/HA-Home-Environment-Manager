"""Conservative weather evidence for automatic indoor window shading.

Use only explicitly selected Home Assistant weather entities and their
documented conditions. Clear or partly cloudy may justify solar shade
closure; cloudy/rainy weather does not. Severe or unknown evidence never
authorizes a new shade closure. No forecast guessing or inferred irradiance.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import math

SUN_HEATING = frozenset(("sunny", "partlycloudy"))
NON_SOLAR = frozenset(("cloudy", "fog", "rainy", "pouring", "snowy", "snowy-rainy"))
HAZARDOUS = frozenset(("windy", "windy-variant", "lightning", "lightning-rainy",
                       "hail", "exceptional"))
ALL_KNOWN = SUN_HEATING | NON_SOLAR | HAZARDOUS
MAX_WEATHER_AGE_SECONDS = 3 * 3600


def weather_evidence(hass: Any, settings: dict) -> tuple[str, dict]:
    configured = settings.get("weather_entities", [])
    ids = list(dict.fromkeys(e for e in configured
                             if isinstance(e, str) and e.startswith("weather."))) if isinstance(configured, list) else []
    evidence: dict = {"weather_sources": ids, "weather_conditions": {}}
    if not ids:
        return "weather_not_configured", evidence
    now = datetime.now(timezone.utc)
    states: list[str] = []
    for entity in ids:
        state = hass.states.get(entity)
        if state is None or getattr(state, "state", None) in ("unknown", "unavailable", "", None):
            return "weather_unavailable", evidence
        condition = str(state.state).casefold()
        if condition not in ALL_KNOWN:
            return "weather_unavailable", evidence
        age = getattr(state, "last_updated", None)
        if age is not None and hasattr(age, "astimezone"):
            try:
                delta = (now - age.astimezone(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                return "weather_stale", evidence
            if not math.isfinite(delta) or delta < -120 or delta > MAX_WEATHER_AGE_SECONDS:
                return "weather_stale", evidence
        evidence["weather_conditions"][entity] = condition
        states.append(condition)
    if any(condition in HAZARDOUS for condition in states):
        return "weather_hazard_hold", evidence
    if all(condition in SUN_HEATING for condition in states):
        return "weather_solar", evidence
    if all(condition in NON_SOLAR for condition in states):
        return "weather_no_solar_gain", evidence
    # Conflicting providers: no unsafe inference that the sun is shining.
    return "weather_conflicting", evidence

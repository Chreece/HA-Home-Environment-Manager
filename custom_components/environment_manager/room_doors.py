"""Room-door observations and conservative opt-in Eco eligibility.

An interior door contact proves OPEN/CLOSED, not air tightness or return-air
capacity. Door state is never mixed with window contacts, occupancy sources,
home presence, sleep, or native actuator permissions. No device writes here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Mapping


DOOR_CLASSES = frozenset(("door",))
CLOSED_STABLE_SECONDS = 120
ECO_MAX_RH = 60.0
ECO_MIN_TEMP_C = 16.5
HIGH_CO2_PPM = 1000.0
VERIFIED_VACANCY = frozenset((
    "verified_room_list_unoccupied",
    "all_selected_room_sensors_off",
))


def door_choices(hass: Any, area: str, previous: list[str] | None = None) -> list[dict]:
    """Only native DOOR contacts whose effective HA Area is exactly this room.

    Classless motion, window, garage, opening, locks, and actuators are excluded
    even if their name contains "door". A missing selected entity is retained
    only if its registry record still verifies this area; it stays UNKNOWN.
    """
    from .discovery import entity_area, _device_class
    from .room_sources import native, label
    from homeassistant.helpers import entity_registry as er

    found: dict[str, str] = {}
    for state in hass.states.async_all("binary_sensor"):
        if (entity_area(hass, state.entity_id) == area
                and str(_device_class(hass, state) or "").casefold() in DOOR_CLASSES
                and native(hass, state.entity_id)):
            found[state.entity_id] = label(hass, state.entity_id)
    registry = er.async_get(hass)
    for entity_id in previous if isinstance(previous, list) else ():
        if not isinstance(entity_id, str) or not entity_id.startswith("binary_sensor."):
            continue
        if entity_id in found:
            continue
        item = registry.async_get(entity_id)
        if (item is not None and entity_area(hass, entity_id) == area
                and native(hass, entity_id)):
            state = hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                found[entity_id] = label(hass, entity_id)
    return [{"value": entity_id, "label": name}
            for entity_id, name in sorted(found.items(), key=lambda pair: pair[1].casefold())]


def _numeric(value: Any, low: float, high: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and low <= number <= high else None


def _age_seconds(state: Any, now: datetime) -> float | None:
    changed = getattr(state, "last_changed", None)
    if not isinstance(changed, datetime) or changed.tzinfo is None:
        return None
    try:
        age = (now - changed).total_seconds()
    except (OverflowError, TypeError):
        return None
    return age if 0 <= age <= 3650 * 86400 else None


def observe(hass: Any, area: str, config: Mapping | None, *,
            occupancy: str = "unknown", occupancy_evidence: str = "",
            home: str = "unknown", sleeping: bool | None = None,
            temperature_c: Any = None, humidity_rh: Any = None,
            co2_ppm: Any = None, window_safe: bool = False,
            preparing_arrival: bool = False,
            now: datetime | None = None) -> dict:
    """Read-only door boundary + ventilation warning + guarded Eco decision.

    A stable closed boundary plus verified vacancy is not proof of isolation.
    Unknown/old/foreign contacts fail closed; no assumption from an empty list.
    Eco never bypasses manual presets, device safety, sleep or arrival handling.
    """
    from .discovery import entity_area, _device_class
    from .room_sources import native
    now = now or datetime.now(timezone.utc)
    cfg = config if isinstance(config, Mapping) else {}
    raw = cfg.get("door_sensors", [])
    selected = list(dict.fromkeys(
        eid for eid in raw if isinstance(eid, str)
    )) if isinstance(raw, list) else []
    states = []
    unknown = False
    durations = []
    if not selected:
        boundary = "not_configured"
    else:
        for entity_id in selected:
            state = hass.states.get(entity_id)
            if (not entity_id.startswith("binary_sensor.")
                    or entity_area(hass, entity_id) != area
                    or state is None or not native(hass, entity_id)
                    or str(_device_class(hass, state) or "").casefold() not in DOOR_CLASSES
                    or state.state not in ("on", "off")
                    or (state.attributes or {}).get("restored") is True):
                unknown = True
                continue
            states.append(state.state)
            age = _age_seconds(state, now)
            if age is None:
                unknown = True
            else:
                durations.append(age)
        if "on" in states:
            boundary = "open"
        elif unknown or len(states) != len(selected):
            boundary = "unknown"
        elif durations and min(durations) < CLOSED_STABLE_SECONDS:
            boundary = "settling"
        else:
            boundary = "closed"

    rh = _numeric(humidity_rh, 0, 100)
    temp = _numeric(temperature_c, -40, 65)
    co2 = _numeric(co2_ppm, 0, 50000)
    warning = None
    if boundary == "closed":
        if co2 is not None and co2 >= HIGH_CO2_PPM:
            warning = "closed_door_high_co2"
        elif rh is not None and rh >= ECO_MAX_RH:
            warning = "closed_door_high_humidity"

    enabled = cfg.get("closed_door_eco") is True
    reason = "not_enabled"
    if enabled:
        if boundary != "closed":
            reason = "door_" + boundary
        elif home != "home":
            reason = "home_not_verified"
        elif occupancy != "unoccupied" or occupancy_evidence not in VERIFIED_VACANCY:
            reason = "room_vacancy_not_verified"
        elif sleeping is True:
            reason = "sleep_has_priority"
        elif preparing_arrival:
            reason = "arrival_has_priority"
        elif not window_safe:
            reason = "window_not_verified_closed"
        elif rh is None or rh >= ECO_MAX_RH:
            reason = "humidity_guard"
        elif temp is None or temp < ECO_MIN_TEMP_C:
            reason = "cold_surface_guard"
        else:
            reason = "verified_closed_and_empty"

    return {
        "boundary": boundary,
        "sensor_entities": selected,
        "closed_stable": boundary == "closed",
        "closed_door_eco_enabled": enabled,
        "eco_active": enabled and reason == "verified_closed_and_empty",
        "eco_reason": reason,
        "advisory": warning,
        "temperature_c": temp,
        "humidity_rh": rh,
        "co2_ppm": co2,
        "note": "Closed door does not prove an airtight or balanced ventilation zone",
    }

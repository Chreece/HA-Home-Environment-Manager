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


def contact_options(config: Mapping | None, entity_id: str) -> dict:
    """Normalize optional metadata, without enrolling or reassigning a sensor."""
    config = config if isinstance(config, Mapping) else {}
    profiles = config.get("door_settings", {})
    item = profiles.get(entity_id, {}) if isinstance(profiles, Mapping) else {}
    item = item if isinstance(item, Mapping) else {}
    kind = item.get("kind", "interior")
    kind = kind if kind in ("interior", "fire", "exterior") else "unknown"
    target = item.get("target_area")
    timeout = _numeric(item.get("report_timeout_minutes", 0), 0, 10080)
    coordination = item.get("coordination", "observe")
    meter = item.get("energy_meter")
    return {"coordination": coordination if coordination in ("observe", "conflicts", "shared") else "observe",
            "energy_meter": meter if isinstance(meter, str) and meter.startswith("sensor.") else None,
            "kind": kind,
            "target_area": target if isinstance(target, str) and target else None,
            "report_timeout_minutes": timeout}


def contact_observation(hass: Any, area: str, entity_id: str,
                        config: Mapping | None, now: datetime) -> dict:
    """Distinguish time since a transition from a user-declared heartbeat.

    An event-only contact may stay closed for weeks. That is not stale evidence
    just because last_changed is old. Report expiry is strictly opt-in.
    """
    from .discovery import entity_area, _device_class
    from .room_sources import native
    opts = contact_options(config, entity_id)
    result = {"entity_id": entity_id, **opts, "state": "unknown",
              "health": "unknown", "state_age_seconds": None}
    state = hass.states.get(entity_id)
    if opts["kind"] == "unknown":
        result["health"] = "invalid_kind"
        return result
    if not entity_id.startswith("binary_sensor.") or entity_area(hass, entity_id) != area:
        result["health"] = "wrong_area"
    elif not native(hass, entity_id):
        result["health"] = "not_native"
    elif state is None:
        result["health"] = "missing"
    elif str(_device_class(hass, state) or "").casefold() not in DOOR_CLASSES:
        result["health"] = "wrong_class"
    elif (state.attributes or {}).get("restored") is True:
        result["health"] = "restored"
    elif state.state not in ("on", "off"):
        result["health"] = "unavailable" if state.state == "unavailable" else "unknown"
    else:
        age = _age_seconds(state, now)
        if age is None:
            result["health"] = "invalid_timestamp"
            return result
        timeout = opts["report_timeout_minutes"]
        if timeout is None:
            result["health"] = "invalid_timeout"
            return result
        if timeout > 0:
            stamp = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
            if not isinstance(stamp, datetime) or stamp.tzinfo is None:
                result["health"] = "report_time_unknown"
                return result
            elapsed = (now - stamp).total_seconds()
            result["report_due_epoch"] = stamp.timestamp() + timeout * 60 + 1
            if not 0 <= elapsed <= timeout * 60:
                result["health"] = "report_expired"
                return result
        result.update(state="open" if state.state == "on" else "closed",
                      health="ok", state_age_seconds=age,
                      state_changed_epoch=state.last_changed.timestamp())
    return result


def _vacancy_stable(hass: Any, area: str, config: Mapping,
                    sources: list[str] | None, now: datetime) -> bool:
    """Apply the same local vacancy dwell at planning AND live dispatch."""
    from .discovery import entity_area
    if sources is None:
        sources = config.get("occupancy_sensors")
    if not isinstance(sources, (list, tuple)) or not sources:
        return False
    delay = _numeric(config.get("unoccupied_delay_minutes", 10), 0, 240)
    if delay is None:
        return False
    for entity in sources:
        if not isinstance(entity, str) or entity_area(hass, entity) != area:
            return False
        state = hass.states.get(entity)
        if state is None or (state.attributes or {}).get("restored") is True:
            return False
        if str(state.state).casefold() not in ("off", "0", "0.0", "false"):
            return False
        age = _age_seconds(state, now)
        if age is None or age < delay * 60:
            return False
    return True


def observe(hass: Any, area: str, config: Mapping | None, *,
            occupancy: str = "unknown", occupancy_evidence: str = "",
            occupancy_sources: list[str] | None = None,
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
    now = now or datetime.now(timezone.utc)
    cfg = config if isinstance(config, Mapping) else {}
    raw = cfg.get("door_sensors", [])
    selected = list(dict.fromkeys(
        eid for eid in raw if isinstance(eid, str)
    )) if isinstance(raw, list) else []
    contacts = [contact_observation(hass, area, entity, cfg, now) for entity in selected]
    complete = bool(contacts) and all(item["health"] == "ok" for item in contacts)
    if not contacts:
        boundary = "not_configured"
    elif any(item["state"] == "open" for item in contacts):
        boundary = "open"
    elif not complete:
        boundary = "unknown"
    elif any(item["state_age_seconds"] < CLOSED_STABLE_SECONDS for item in contacts):
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
        elif (occupancy_evidence == "all_selected_room_sensors_off" and
              not _vacancy_stable(hass, area, cfg, occupancy_sources, now)):
            reason = "awaiting_stable_vacancy"
        elif sleeping is not False:
            reason = "sleep_has_priority" if sleeping is True else "sleep_unknown"
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
        "contacts": contacts,
        "contacts_complete": complete,
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

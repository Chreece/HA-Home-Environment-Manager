"""Read current evidence for competing heat sources during a heater OFF episode."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from .shade_weather import ALL_KNOWN, NON_SOLAR

EXTERNAL_HEAT_REASONS = frozenset(("solar_gain_possible", "local_solar_gain_possible",
                                   "warm_outdoors", "heat_transfer_from_room_possible"))


def _areas(settings: dict, area: str) -> set[str]:
    """Without a floor plan, every other monitored room is a possible heat source."""
    areas = set(settings.get("areas") or ())
    areas.update(settings.get("climate_rooms") or {})
    areas.update(settings.get("room_sources") or {})
    areas.discard(area)
    return areas


def _peer_areas(settings: dict, area: str) -> tuple[set[str], bool]:
    """Accept interior links in either direction. A closed door can still pass heat."""
    from .room_doors import contact_options
    neighbors = set()
    incomplete = False
    for owner, cfg in (settings.get("climate_rooms") or {}).items():
        if not isinstance(cfg, Mapping):
            continue
        for entity in cfg.get("door_sensors") or ():
            door = contact_options(cfg, entity)
            peer = door["target_area"]
            if door["kind"] == "exterior" or area not in (owner, peer):
                continue
            if not peer or door["kind"] == "unknown":
                incomplete = True
            elif owner != peer:
                neighbors.add(peer if owner == area else owner)
    if not neighbors or incomplete:
        neighbors.update(_areas(settings, area))
    return neighbors, incomplete


def _valve_travel(state: Any, now: float) -> float | None:
    """Use fresh actual mechanical position only, never a target position or HVAC mode."""
    if state is None or state.state != "off" or state.attributes.get("restored"):
        return None
    travel = state.attributes.get("actual_position")
    stamp = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
    if (type(travel) not in (int, float) or not 0 <= travel <= 100
            or getattr(stamp, "tzinfo", None) is None
            or not 0 <= now - stamp.timestamp() <= 600):
        return None
    return float(travel)


def assess(runtime: Any, spec: Any, state: Any, room_c: float) -> dict:
    """Explain whether the trend can support a guarded heater-specific response."""
    from .room_sources import room_temperature_evidence, selected
    settings, hass = runtime.manager.settings, runtime.hass
    valve = _valve_travel(state, runtime.clock())
    result = {"status": "consistent_with_heater", "reason": "no_observed_external_gain",
              "weather": {}, "peers": {}, "room_light": {}, "actual_valve_position": valve}
    reasons = []
    sun = hass.states.get("sun.sun")
    sun_state = sun.state if sun is not None and not sun.attributes.get("restored") else None
    ids = settings.get("weather_entities") or ()
    if not ids:
        reasons.append("outdoor_conditions_unknown")
    for entity in sorted(set(ids)):
        from .discovery import weather
        obs = weather(hass, entity, 180)
        outside, condition = obs.temperature_c, obs.condition
        result["weather"][entity] = {"condition": condition, "temperature_c": outside}
        if type(outside) not in (float, int) or not isfinite(outside) or not -90 <= outside <= 65:
            reasons.append("outdoor_conditions_unknown")
        elif outside >= room_c - .5:
            reasons.append("warm_outdoors")
        # Even overcast skies admit solar gains. During daylight use a
        # conservative veto for clear/ambiguous sky; never infer local sunshine.
        if condition == "clear-night":
            if sun_state == "above_horizon":
                reasons.append("outdoor_conditions_unknown")
        elif condition not in ALL_KNOWN:
            reasons.append("outdoor_conditions_unknown")
        elif sun_state != "below_horizon" and condition not in NON_SOLAR:
            reasons.append("solar_gain_possible")
    # If configured, the existing shade sensors can see local brightness
    # which a distant or overcast weather station misses.
    covers = ((settings.get("shade_rooms") or {}).get(spec.area_id, {}).get("covers") or {})
    for entity, options in sorted(covers.items()):
        if not isinstance(options, Mapping) or options.get("lux_enabled") is not True:
            continue
        from .shade_cooling import cover_config, lux_evidence
        lux = lux_evidence(hass, settings, spec.area_id, cover_config(settings, spec.area_id, entity))
        result["room_light"][entity] = {
            "source_ids": list(lux["sources"]), "value_lx": lux["value_lx"],
            "threshold_lx": lux["threshold_lx"], "status": lux["status"],
        }
        if lux["status"] == "lux_threshold_met":
            reasons.append("local_solar_gain_possible")
        elif lux["status"] != "lux_below_threshold" or lux["valid_count"] != len(lux["sources"]):
            reasons.append("room_light_unknown")
    neighbors, incomplete = _peer_areas(settings, spec.area_id)
    if incomplete:
        reasons.append("unmapped_room_connection")
    for peer in sorted(neighbors):
        room = (settings.get("climate_rooms") or {}).get(peer, {})
        pinned = None if selected(settings, peer, "temperature") is not None else (
            room.get("temperature_entity") or
            (settings.get("pid_rooms") or {}).get(peer, {}).get("temperature_entity"))
        value, evidence = room_temperature_evidence(hass, settings, peer, pinned=pinned)
        ids = list(evidence.get("entity_ids") or ())
        ready = value is not None and evidence.get("status") == "ready" and not evidence.get("partial")
        result["peers"][peer] = {"temperature_c": value if ready else None, "source_ids": ids}
        if not ready:
            reasons.append("adjacent_room_unknown")
        elif value >= room_c - .5:
            reasons.append("heat_transfer_from_room_possible")
    if reasons:
        result.update(status="unattributed", reason=reasons[0], reasons=list(dict.fromkeys(reasons)))
    if valve is not None and valve > 0:
        # Verified opening is an independent reason to reassert OFF even if
        # sunshine or a neighboring room also contributes to the warming.
        result.update(status="valve_open_while_off", reason="actual_valve_position_positive")
    return result


def signature(evidence: dict) -> tuple:
    """Changing sources, attribution or conflicting explanations starts a new trend."""
    return (evidence["status"], tuple(evidence.get("reasons", ())),
            tuple(sorted(evidence["weather"])),
            tuple((key, tuple(item["source_ids"]), item["threshold_lx"])
                  for key, item in sorted(evidence.get("room_light", {}).items())),
            tuple((key, tuple(item["source_ids"])) for key, item in sorted(evidence["peers"].items())))


def _oldest_room_report(hass: Any, source_ids: tuple[str, ...], now: float) -> float | None:
    """Every member of the independent room mean must have reported."""
    stamps = []
    for entity in source_ids:
        state = hass.states.get(entity)
        stamp = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
        if getattr(stamp, "tzinfo", None) is None or state.attributes.get("restored"):
            return None
        at = stamp.timestamp()
        if not isfinite(at) or at > now:
            return None
        stamps.append(at)
    return min(stamps, default=None)


def external_heat_pending(hass: Any, watch: Any, evidence: dict, *, pending: bool,
                          other_sources_clear: bool, now: float, room_c: float) -> bool:
    """Keep external heating separate from a later independent warming episode."""
    if not other_sources_clear or EXTERNAL_HEAT_REASONS.intersection(evidence.get("reasons", ())):
        watch.reset_settling()
        return True
    if not pending:
        return False
    if evidence["status"] != "consistent_with_heater":
        watch.reset_settling()
        return True
    reported_at = _oldest_room_report(hass, watch.source_ids, now)
    if watch.room_settled(now, reported_at, room_c):
        watch.reset_settling()
        return False
    evidence.update(status="unattributed", reason="residual_external_heat_possible",
                    reasons=["residual_external_heat_possible"])
    return True

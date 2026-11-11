"""Global, room and device occupancy policy.

Only actual Home Assistant states and configured Area Registry IDs are accepted.
Unavailable/ambiguous sources are unknown. Room lists and binary presence
states are change-driven and do not expire simply because nobody moved. An empty
room list (including an empty string) means no rooms are occupied. Configured
whole-home sources take priority; verified Away does not consult room sources.
"""
from __future__ import annotations

import ast
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from collections.abc import Mapping
from typing import Any

from .discovery import entity_area, _device_class


def _fresh(state: Any, max_age_minutes: float | None = 240, *, allow_empty: bool = False) -> bool:
    if state is None or (getattr(state, "attributes", {}) or {}).get("restored") is True:
        return False
    value = str(getattr(state, "state", "")).strip().casefold()
    if value in ("unknown", "unavailable") or not allow_empty and value in ("none", ""):
        return False
    stamp = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
    if not isinstance(stamp, datetime) or stamp.tzinfo is None:
        return False
    age = (datetime.now(timezone.utc) - stamp).total_seconds()
    return age >= 0 and (max_age_minutes is None or age <= max_age_minutes * 60)


def _room_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _area_aliases(hass: Any, identifiers: set[str]) -> dict[str, str]:
    from homeassistant.helpers import area_registry
    registry = area_registry.async_get(hass)
    available = set(identifiers)
    if hasattr(registry, "async_list_areas"):
        available.update(item.id for item in registry.async_list_areas())
    elif hasattr(registry, "areas"):
        available.update(registry.areas)
    candidates: dict[str, set[str]] = {}
    for area in available:
        if not isinstance(area, str) or not area:
            continue
        actual = registry.async_get_area(area)
        names = (area, getattr(actual, "name", None), *(getattr(actual, "aliases", ()) or ()))
        for name in names:
            if isinstance(name, str) and name.strip():
                candidates.setdefault(_room_key(name), set()).add(area)
    # Ambiguous names cannot identify a safe room. Exact IDs still work.
    return {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}


def _tokens(raw: Any, _depth: int = 0) -> list[str] | None:
    """Read explicit template lists/CSV, without executing template content."""
    if _depth > 5:
        return None
    if isinstance(raw, Mapping):
        for key in ("occupied_rooms", "sleep_rooms", "sleeping_areas", "areas", "rooms"):
            if key in raw:
                return _tokens(raw[key], _depth + 1)
        if all(isinstance(k, str) and (type(v) is bool or type(v) is int and v >= 0)
               for k, v in raw.items()):
            return [k for k, v in raw.items() if v]
        return None
    if isinstance(raw, (list, tuple, set, frozenset)):
        return list(raw) if all(isinstance(v, str) and v.strip() for v in raw) else None
    if not isinstance(raw, str) or len(raw) > 8192:
        return None
    value = raw.strip()
    if value.casefold() in ("", "none", "no_rooms"):
        return []
    if value.startswith(("[", "{", "(")):
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError):
            # Jinja/Python-rendered lists commonly use single quotes. Limit
            # AST size first; literal_eval does not execute calls or names.
            try:
                tree = ast.parse(value, mode="eval")
                if sum(1 for _ in ast.walk(tree)) > 512:
                    return None
                decoded = ast.literal_eval(tree)
            except (ValueError, SyntaxError, TypeError, RecursionError):
                return None
        return _tokens(decoded, _depth + 1)
    if any(separator in value for separator in (",", ";", "\n")):
        return [part.strip() for part in re.split(r"[,;\n]", value) if part.strip()]
    return [value]


def configured_rooms(hass: Any, entity_id: str | None, attribute: str | None,
                     known_areas: set[str], *, max_age_minutes: float = 240,
                     ) -> tuple[set[str] | None, str]:
    """Read state/one explicit attribute. Unknown names invalidate the list."""
    if not isinstance(entity_id, str) or not entity_id:
        return None, "not_configured"
    state = hass.states.get(entity_id)
    # A list is a current set, including when stored in a sensor attribute.
    # Keep a stable list through a full night without change notifications.
    if not _fresh(state, None, allow_empty=True):
        return None, "missing_or_stale_rooms_source"
    if isinstance(attribute, str) and attribute.strip() not in ("", "__state__"):
        raw = state.attributes.get(attribute.strip())
    else:
        raw = state.state
    parsed = _tokens(raw)
    if parsed is None:
        return None, "invalid_rooms_format"
    aliases = _area_aliases(hass, known_areas)
    resolved: set[str] = set()
    for name in parsed:
        area = aliases.get(_room_key(name))
        if area is None:
            return None, "unrecognized_room_in_occupancy_source"
        resolved.add(area)
    return resolved, "verified_rooms_list"


def _bool_presence(state: Any, minutes: float = 240, *, room_input: bool = False) -> bool | None:
    # Change-driven room contacts keep ON/OFF until the next transition.
    # Whole-home positives from change-driven trackers also remain positive:
    # a person/device tracker can stay HOME all night without a new report.
    # Negatives must still be recent before they authorize household Away.
    # Missing, restored, invalid and unavailable values never prove presence.
    domain = getattr(state, "domain", None)
    positive_state = "on" if domain == "binary_sensor" else "home"
    if (not room_input and domain in ("person", "device_tracker", "binary_sensor")
            and getattr(state, "state", None) == positive_state):
        return True if _fresh(state, None) else None
    if not _fresh(state, None if room_input and domain == "binary_sensor" else minutes):
        return None
    if state.domain == "binary_sensor":
        if state.state == "on":
            return True
        if state.state == "off":
            return False
    if state.domain in ("number", "input_number", "sensor"):
        # Only explicitly selected numeric occupancy sources reach this path:
        # zero means vacant, positive finite counts mean occupied. Unavailable,
        # NaN, negative and nonnumeric states remain unknown, never vacant.
        try:
            count = float(str(state.state).strip())
        except (TypeError, ValueError, OverflowError):
            return None
        return count > 0 if math.isfinite(count) and count >= 0 else None
    if state.domain in ("person", "device_tracker"):
        if state.state == "home":
            return True
        if state.state not in ("unknown", "unavailable", "none", ""):
            return False
    return None


def _after_away_cooldown(states: list[Any], minutes: Any, reason: str,
                         *, verified_since: Any = None) -> tuple[str, str]:
    try:
        cooldown = max(0.0, min(240.0, float(minutes)))
    except (TypeError, ValueError, OverflowError):
        cooldown = 10.0
    if cooldown <= 0:
        return "away", reason
    now = datetime.now(timezone.utc)
    # An already-observed, source-bound absence survives HA restarts. The
    # built-in last_changed timestamp can reset when entities are restored.
    # Continuity is supplied only after fresh ALL-NEGATIVE revalidation.
    resumed = None
    try:
        stamp = float(verified_since)
        if math.isfinite(stamp) and 0 < stamp <= now.timestamp():
            resumed = datetime.fromtimestamp(stamp, timezone.utc)
    except (ValueError, TypeError, OverflowError):
        pass
    stamps = [getattr(state, "last_changed", None) for state in states if state is not None]
    stamps = [stamp for stamp in stamps if isinstance(stamp, datetime) and stamp.tzinfo is not None]
    if resumed is not None:
        elapsed = (now - resumed).total_seconds()
    elif stamps:
        elapsed = (now - max(stamps)).total_seconds()
    else:
        return "unknown", "away_cooldown_start_unknown"
    if elapsed < 0:
        return "unknown", "away_cooldown_clock_invalid"
    if elapsed < cooldown * 60:
        return "home", "no_occupied_rooms_cooldown"
    return "away", reason


def shared_home_settings(global_settings: Any, rooms: Any) -> dict:
    """Use every explicitly configured household tracker for every room.

    Legacy trackers belong to the whole home even when their room controller
    is disabled. Merge them into a fresh runtime context before continuity is
    evaluated, so planning, arrival controls and live command checks use one
    source signature without changing the user's saved selections.
    """
    shared = dict(global_settings) if isinstance(global_settings, Mapping) else {}
    legacy = []
    for room in rooms.values() if isinstance(rooms, Mapping) else ():
        selected = room.get("away_entities") if isinstance(room, Mapping) else None
        if isinstance(selected, list):
            legacy.extend(entity for entity in selected if isinstance(entity, str))
    if legacy:
        direct = shared.get("home_trackers")
        direct = ([entity for entity in direct if isinstance(entity, str)]
                  if isinstance(direct, list) else [])
        shared["home_trackers"] = list(dict.fromkeys([*direct, *legacy]))
    # The removed Home "room occupancy sensors" selector now lives in each
    # room. Keep aggregating explicitly selected local sensors as positive
    # household evidence when no direct person/tracker is configured.
    # An explicit [] contributes nothing and must remain authoritative.
    local_presence = []
    for room in rooms.values() if isinstance(rooms, Mapping) else ():
        chosen = room.get("occupancy_sensors") if isinstance(room, Mapping) else None
        if isinstance(chosen, list):
            local_presence.extend(
                eid for eid in chosen if isinstance(eid, str)
                and eid.startswith(("binary_sensor.", "sensor.", "number.", "input_number."))
            )
    old = shared.get("room_occupancy_sensors", [])
    old = old if isinstance(old, list) else []
    shared["room_occupancy_sensors"] = list(dict.fromkeys([*old, *local_presence]))
    return shared


def home_presence(hass: Any, global_settings: Mapping,
                  fallback_trackers: list[str] | None = None) -> tuple[str, str, list[str]]:
    """Resolve configured whole-home sources before consulting any room.

    A fresh positive direct source means Home. Otherwise all direct sources
    must be freshly negative to establish Away; a missing/unknown one leaves
    home presence unknown. Room activity cannot override either decision.
    Only installations without direct home sources use room evidence and
    its existing absence cooldown. Return the sources that decided presence,
    so room sensors cannot become home trackers at a later control check.
    """
    global_trackers = global_settings.get("home_trackers", [])
    # Legacy area trackers are explicit sources too: a positive should not
    # disappear merely because the General settings list is also configured.
    combined = [
        *(global_trackers if isinstance(global_trackers, list) else []),
        *(fallback_trackers if isinstance(fallback_trackers, list) else []),
    ]
    allowed = list(dict.fromkeys(
        entity for entity in combined
        if isinstance(entity, str)
        and entity.startswith(("person.", "device_tracker.", "binary_sensor.",
                               "number.", "input_number.", "sensor."))
    ))
    if allowed:
        tracker_values = [_bool_presence(hass.states.get(e), global_settings.get("source_stale_minutes", 240))
                          for e in allowed]
        if any(value is True for value in tracker_values):
            return "home", "any_home_policy", allowed
        if any(value is None for value in tracker_values):
            return "unknown", "unverified_home_trackers", allowed
        # Direct absence has always bypassed the room-motion cooldown. Do
        # not read a stale/empty list or a stuck room sensor to contradict it.
        return "away", "all_selected_home_trackers_away", allowed

    cooldown = global_settings.get("away_cooldown_minutes", 10)
    room_entity = global_settings.get("occupied_rooms_entity")
    room_sources = global_settings.get("room_occupancy_sensors", [])
    allowed_rooms = list(dict.fromkeys(
        entity for entity in (room_sources if isinstance(room_sources, list) else [])
        if isinstance(entity, str) and entity.startswith((
            "binary_sensor.", "number.", "input_number.", "sensor."))
    ))
    all_sources = list(dict.fromkeys([
        *([room_entity] if isinstance(room_entity, str) and room_entity else []),
        *allowed_rooms,
    ]))
    room_values = [_bool_presence(hass.states.get(e), global_settings.get("source_stale_minutes", 240),
                                  room_input=True) for e in allowed_rooms]
    resumed_since = global_settings.get("_verified_absence_since")

    # No whole-home absence is inferred merely from an unconfigured room.
    if any(value is True for value in room_values):
        return "home", "room_sensor_occupied", all_sources

    has_room_list = isinstance(room_entity, str) and bool(room_entity)
    if has_room_list:
        rooms, why = configured_rooms(
            hass, room_entity, global_settings.get("occupied_rooms_attribute"),
            set(), max_age_minutes=global_settings.get("source_stale_minutes", 240))
        if rooms is None:
            return "unknown", why, all_sources
        if rooms:
            return "home", "occupied_rooms_present", all_sources
    if any(value is None for value in room_values):
        return "unknown", "room_presence_evidence_unknown", all_sources

    if has_room_list:
        state = hass.states.get(room_entity)
        # Attribute data may change without changing the entity's state.
        attr = global_settings.get("occupied_rooms_attribute")
        if state is not None and isinstance(attr, str) and attr not in ("", "__state__"):
            state = type("_Stamp", (), {"last_changed": getattr(state, "last_updated", None)})()
        status, reason = _after_away_cooldown(
            [state, *(hass.states.get(e) for e in allowed_rooms)],
            cooldown, "occupied_rooms_empty",
            verified_since=resumed_since,
        )
        return status, reason, all_sources
    if room_values:
        return (*_after_away_cooldown(
            [hass.states.get(e) for e in allowed_rooms], cooldown,
            "all_room_sensors_unoccupied", verified_since=resumed_since,
        ), all_sources)
    return "home", "no_trackers_assume_home", []


def room_sensor_choices(hass: Any, area: str) -> list[str]:
    """Default room occupancy selection from real HA area/device assignments.

    Only binary sensors *explicitly classified* as presence or occupancy are
    candidates. This is a default for legacy/unconfigured rooms, not an
    authorization to override an explicit [] saved by the user.
    """
    return sorted(
        state.entity_id for state in hass.states.async_all("binary_sensor")
        if entity_area(hass, state.entity_id) == area
        and _device_class(hass, state).casefold() in ("occupancy", "presence")
    )


def selected_room_sensors(hass: Any, area: str, settings: Mapping,
                          global_settings: Mapping) -> list[str]:
    """An explicit per-room selection (including []) overrides all defaults."""
    local = settings.get("occupancy_sensors")
    if isinstance(local, list):
        candidates = local
    else:
        global_selected = global_settings.get("room_occupancy_sensors")
        # Preserve explicitly configured legacy global room sensors until
        # each room is saved; new room pickers use per-room settings only.
        candidates = (
            global_selected if isinstance(global_selected, list) and global_selected
            else room_sensor_choices(hass, area)
        )
    result = []
    for eid in candidates:
        if not isinstance(eid, str) or not eid.startswith(("binary_sensor.", "number.", "input_number.", "sensor.")):
            continue
        assigned = entity_area(hass, eid)
        state = hass.states.get(eid)
        if (state is None or state.state in ("unknown", "unavailable") or
                (getattr(state, "attributes", {}) or {}).get("restored") is True):
            # An explicitly selected source that has disappeared is unknown,
            # not permission to infer vacancy from the remaining OFF sources.
            # A known assignment to another room is still excluded.
            if assigned in (None, area):
                result.append(eid)
        elif assigned == area and (not eid.startswith("binary_sensor.") or
                                   _device_class(hass, state).casefold() in ("occupancy", "presence")):
            result.append(eid)
    return list(dict.fromkeys(result))


def room_presence(hass: Any, area: str, settings: Mapping,
                  global_settings: Mapping, *, known_areas: set[str],
                  home_status: str | None = None,
                  ) -> tuple[str, str, list[str]]:
    """Verified home absence, then room list and selected local fallback.

    When the household is verified Away, skip all room-source reads. Callers
    may pass a just-evaluated home status to share one consistent decision.
    Valid list: a room omitted from it is immediately UNoccupied, regardless
    of another sensor's ON reading. Valid empty string/list: all rooms are
    unoccupied. Missing/unavailable list: use the sensors explicitly
    selected for this area; any live ON qualifies, all live OFF is negative.
    Other broken list formats/unknown room names fail UNKNOWN and never
    grant inferred presence or absence. An explicit [] sensor selection is
    honoured even during fallback.
    """
    if home_status is None:
        home_status, _, _ = home_presence(
            hass, global_settings, settings.get("away_entities"),
        )
    if home_status == "away":
        return "unoccupied", "verified_home_away", []
    sensors = selected_room_sensors(hass, area, settings, global_settings)
    entity = global_settings.get("occupied_rooms_entity")
    has_list = isinstance(entity, str) and bool(entity) and entity != "none"
    sources = list(dict.fromkeys(([entity] if has_list else []) + sensors))
    if has_list:
        rooms, reason = configured_rooms(
            hass, entity, global_settings.get("occupied_rooms_attribute"),
            known_areas, max_age_minutes=global_settings.get("source_stale_minutes", 240),
        )
        if rooms is not None:
            if area in rooms:
                return "occupied", "verified_room_occupied", sources
            return "unoccupied", "verified_room_list_unoccupied", sources
        # Only absence of a trustworthy live report authorizes sensor fallback;
        # malformed data and ambiguous area aliases must remain UNKNOWN.
        if reason != "missing_or_stale_rooms_source":
            return "unknown", reason, sources

    values = [
        _bool_presence(hass.states.get(eid),
                       settings.get("occupancy_stale_minutes", 240), room_input=True)
        for eid in sensors
    ]
    if any(value is True for value in values):
        return "occupied", "selected_room_sensor_on", sources
    if values and all(value is False for value in values):
        return "unoccupied", "all_selected_room_sensors_off", sources
    if not sensors and not has_list:
        return "unoccupied", "no_room_presence_sensors", sources
    return "unknown", "room_occupancy_source_unknown", sources


def sleep_presence(hass: Any, area: str, global_settings: Mapping,
                   known_areas: set[str]) -> tuple[bool | None, str]:
    if not global_settings.get("sleep_rooms_entity"):
        return None, "sleep_rooms_not_configured"
    rooms, reason = configured_rooms(
        hass, global_settings.get("sleep_rooms_entity"),
        global_settings.get("sleep_rooms_attribute"),
        known_areas, max_age_minutes=global_settings.get("source_stale_minutes", 240))
    return (area in rooms if rooms is not None else None), reason



def household_sleep_presence(
    hass: Any, global_settings: Mapping, known_areas: set[str], *, home_status: str,
) -> tuple[bool | None, str]:
    """All occupied rooms must be listed as asleep, and at least one occupied.

    Compare the complete HA room lists, including rooms without HEM equipment.
    If occupancy comes from contacts, use explicit room selections (including
    empty selections) before global selections or area-bound discovery.
    """
    if home_status == "away":
        return False, "verified_home_away_no_sleeping_occupants"
    if not global_settings.get("sleep_rooms_entity"):
        return False, "sleep_room_source_not_configured"
    sleeping, why = configured_rooms(hass, global_settings["sleep_rooms_entity"],
                                     global_settings.get("sleep_rooms_attribute"), known_areas)
    if sleeping is None:
        return None, why
    if not sleeping:
        return False, "no_sleeping_rooms"
    occupied, why = configured_rooms(hass, global_settings.get("occupied_rooms_entity"),
                                     global_settings.get("occupied_rooms_attribute"), known_areas)
    if occupied is None:
        if why not in ("not_configured", "missing_or_stale_rooms_source"):
            return None, why
        overrides = global_settings.get("_room_occupancy_selections", {})
        overrides = overrides if isinstance(overrides, Mapping) else {}
        age_limits = global_settings.get("_room_occupancy_stale_minutes", {})
        age_limits = age_limits if isinstance(age_limits, Mapping) else {}
        general = global_settings.get("room_occupancy_sensors")
        if isinstance(general, list) and general:
            candidates = [eid for eid in general if isinstance(eid, str)
                          and eid.startswith(("binary_sensor.", "number.", "input_number.", "sensor."))]
        else:
            candidates = [state.entity_id for state in hass.states.async_all("binary_sensor")
                          if _device_class(hass, state).casefold() in ("occupancy", "presence")]
        by_area: dict[str, list[str]] = {}
        for eid in candidates:
            assigned = entity_area(hass, eid)
            if assigned:
                by_area.setdefault(assigned, []).append(eid)
            elif isinstance(general, list) and eid in general:
                return None, "room_occupancy_source_unknown"
        occupied = set()
        unknown = False
        for candidate in set(known_areas) | set(overrides) | set(by_area):
            selected = overrides.get(candidate, by_area.get(candidate, []))
            status, _, _ = room_presence(
                hass, candidate, {"occupancy_sensors": selected,
                                  "occupancy_stale_minutes": age_limits.get(candidate, 240)},
                global_settings,
                known_areas=known_areas, home_status=home_status,
            )
            if status == "occupied":
                if candidate not in sleeping:
                    return False, "occupied_room_awake"
                occupied.add(candidate)
            elif status == "unknown":
                unknown = True
        if unknown:
            return None, "room_occupancy_source_unknown"
    if not occupied:
        return False, "no_occupied_rooms"
    if occupied <= sleeping:
        return True, "all_occupied_rooms_sleeping"
    return False, "occupied_room_awake"


def controlled_sleep_presence(
    hass: Any, area: str, global_settings: Mapping,
    known_areas: set[str], *, home_status: str,
    local_sleeping: bool | None = False,
    local_reason: str = "sleep_schedule_disabled",
    room_status: str | None = None,
    inherit_household: bool = False,
    now: float | None = None,
) -> tuple[bool | None, str]:
    """One sleep decision for profiles, quiet operation and live write guards."""
    away = home_status == "away"
    if away:
        own, reason = False, "verified_home_away_no_sleeping_occupants"
    elif local_sleeping is True:
        # Sleeping now and an explicitly enabled schedule are deliberate
        # room controls, independent of list-inferred occupancy.
        own, reason = True, local_reason
    elif str(global_settings.get("sleep_rooms_entity") or "").strip().casefold() in (
        "", "none", "unknown", "unavailable"
    ):
        own, reason = False, "sleep_room_source_not_configured"
    elif room_status == "unoccupied":
        own, reason = False, "room_unoccupied"
    else:
        own, reason = sleep_presence(hass, area, global_settings, known_areas)
        if own is True:
            if room_status is None:
                selected = global_settings.get("_room_occupancy_selections") or {}
                age_limits = global_settings.get("_room_occupancy_stale_minutes") or {}
                room_status, _, _ = room_presence(
                    hass, area, {"occupancy_sensors": selected.get(area),
                                 "occupancy_stale_minutes": age_limits.get(area, 240)},
                    global_settings,
                    known_areas=known_areas, home_status=home_status,
                )
            if room_status != "occupied":
                own = False if room_status == "unoccupied" else None
                reason = "room_unoccupied" if own is False else "room_occupancy_source_unknown"

    alarm_configured = bool(global_settings.get("wake_alarm_entity")
                            and global_settings.get("wake_lead_minutes_entity"))
    if alarm_configured:
        from .wake_alarm import wake_override
        if wake_override(hass, global_settings, "room:" + area, own, now=now) and own is True:
            own, reason = False, "wake_before_alarm"
    if inherit_household:
        household, household_reason = household_sleep_presence(
            hass, global_settings, known_areas, home_status=home_status)
        if alarm_configured:
            if wake_override(hass, global_settings, "household", household, now=now) and household is True:
                household, household_reason = False, "wake_before_alarm"
        # Either continuing wake episode suppresses automatic Sleep. A later
        # household transition must not put an already-woken room back to
        # sleep, or vice versa. Observe both scopes first so actual negative
        # sleep evidence still clears the appropriate episode for next night.
        if reason == "wake_before_alarm" or household_reason == "wake_before_alarm":
            return False, "wake_before_alarm"
        if household is True:
            return True, household_reason
    return own, reason


def device_permission(device: Mapping, room_status: str, home_status: str,
                      sleeping: bool | None, *,
                      household_sleeping: bool = False,
                      preparing_arrival: bool = False) -> tuple[str, str]:
    """Prioritize explicit sleep pause over occupancy-triggered power OFF.

    Device controllers must still pass the independent electrical,
    compressor and minimum-run protections. An unknown input is NEVER empty.
    """
    if device.get("auto_control") is not True:
        return "held", "device_auto_control_disabled"
    # This device-wide preference promises OFF while everybody is asleep,
    # independently of its room's Normal / Sleep targets policy. Only fresh,
    # positive household evidence may activate it; a sleeping local room or
    # an unknown/empty home cannot stand in for all occupants being asleep.
    if (device.get("sleep_when_everyone_asleep") is True
            and household_sleeping is True and sleeping is True
            and home_status != "away"):
        return "held", "sleep_room_control_paused"
    sleep = device.get("sleep_behavior", "normal")
    if sleep == "pause":
        if sleeping is True:
            return "held", "sleep_room_control_paused"
        if sleeping is None and home_status != "away":
            return "held", "sleep_room_evidence_unknown"
        # Confirmed whole-house absence means no occupant can be sleeping,
        # even if an optional sleeping-room entity stopped reporting. A live
        # sleep=True above always wins over this derived negative evidence.
    elif sleep == "sleep_targets":
        # Sleep targets are setpoints, not a command to pause heating. If
        # sleeping is unverified, the profile already falls back to Home/Away
        # normal targets. Only an explicit PAUSE policy requires sleep proof.
        pass
    elif sleep != "normal":
        return "held", "invalid_sleep_policy"
    # A cached/manual plan can still contain old room activity. Verified
    # whole-home absence takes priority at the final device-policy boundary.
    if home_status == "away":
        room_status = "unoccupied"
    source = device.get("presence_requirement", "always")
    # A deliberate, still-valid arrival request permits automatic preparation
    # in currently empty rooms. It does not claim anyone is physically present
    # and does not override sleep pause, disabled control, or absent-only rules.
    if preparing_arrival and home_status == "away" and source in ("room", "home", "occupied"):
        return "eligible", "preparing_for_arrival"
    # Legacy room/home semantics are retained for the old room drivers only.
    # The new per-controller UI never offers these values.
    if source == "room":
        if room_status == "unoccupied":
            return "absent", "room_unoccupied"
        if room_status != "occupied":
            return "held", "room_occupancy_unknown"
    elif source == "home":
        if home_status == "away":
            return "absent", "house_unoccupied"
        if home_status != "home":
            return "held", "house_occupancy_unknown"
    elif source == "occupied":
        if room_status == "unoccupied":
            return "held", "room_not_occupied"
        if room_status != "occupied":
            return "held", "room_occupancy_unknown"
    elif source == "absent":
        if room_status == "occupied":
            return "held", "room_not_absent"
        if room_status != "unoccupied":
            return "held", "room_occupancy_unknown"
    elif source != "always":
        return "held", "invalid_presence_policy"
    return "eligible", "device_policy_approved"



def live_device_permission(hass: Any, area: str, room_config: Mapping,
                           plan: Mapping, device: Mapping) -> tuple[str, str]:
    """Re-check sensor/occupancy evidence at the actual write boundary.

    A plan evaluated before a person enters, leaves or starts sleeping must
    not authorize a stale command. No new entity is discovered or controlled.
    """
    global_settings = plan.get("global_presence")
    area_ids = plan.get("known_presence_areas")
    def permission(room, home, sleeping, sleep_evidence):
        from .arrival_preparation import live_preparation, room_eligible
        preparing, problem = live_preparation(
            hass, plan, home,
            eligible=device.get("_arrival_preparation_eligible", room_eligible(room_config)),
            entry_id=device.get("_arrival_preparation_entry_id"),
        )
        if problem:
            return "held", problem
        return device_permission(device, room, home, sleeping,
                                 household_sleeping=(sleeping is True and
                                     sleep_evidence == "all_occupied_rooms_sleeping"),
                                 preparing_arrival=preparing and device.get(
                                     "_arrival_preparation_presence_override") is True)
    if isinstance(global_settings, Mapping) and global_settings:
        known = (set(area_ids) if isinstance(area_ids, (tuple,list,set))
                 else {area})
        home,_,_=home_presence(hass,global_settings,
                               room_config.get("away_entities"))
        room,_,_=room_presence(hass,area,room_config,global_settings,
                               known_areas=known or {area},home_status=home)
        from time import time as _time
        from .climate_schedule import scheduled_sleep
        zone = getattr(getattr(hass, "config", None), "time_zone", None) or "UTC"
        now = _time()
        local_sleeping, local_reason = scheduled_sleep(room_config, now, zone)
        sleeping, sleep_evidence = controlled_sleep_presence(
            hass, area, global_settings, known or {area},
            home_status=home, local_sleeping=local_sleeping,
            local_reason=local_reason, room_status=room,
            inherit_household=device.get("sleep_when_everyone_asleep") is True, now=now,
        )
        return permission(room,home,sleeping,sleep_evidence)
    home=plan.get("away","unknown")
    trackers=room_config.get("away_entities",plan.get("tracker_entities"))
    if isinstance(trackers,list) and trackers:
        home,_,_=home_presence(hass,{"home_trackers":trackers})
    # Away plans deliberately contain no room evidence. On a return before
    # the next plan, read the actual room configuration rather than trusting
    # that cached unoccupied result or its empty presence_entities list.
    room,_,_=room_presence(hass,area,room_config,{},
                           known_areas={area},home_status=home)
    # Even a climate-only room without General sleeping-room configuration
    # has valid non-sleep evidence from its own disabled/local schedule.
    from time import time as _time
    from .climate_schedule import scheduled_sleep
    zone = getattr(getattr(hass, "config", None), "time_zone", None) or "UTC"
    now = _time()
    local_sleeping, local_reason = scheduled_sleep(room_config, now, zone)
    sleeping, sleep_evidence = controlled_sleep_presence(
        hass, area, {}, {area}, home_status=home,
        local_sleeping=local_sleeping, local_reason=local_reason, room_status=room,
        inherit_household=device.get("sleep_when_everyone_asleep") is True, now=now,
    )
    return permission(room,home,sleeping,sleep_evidence)

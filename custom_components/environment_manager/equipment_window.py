"""Per-device window stop policy, independent of permanent/manual pause latches.

Read live selected contacts at every command boundary. No service calls, no
sleep(), no timers per entity, no native capability inference or global scans.
"""
from __future__ import annotations

from typing import Any
import math

from . import equipment_model as model
from .discovery import entity_area, is_window_contact
from .room_sources import selected

RESUME_SECONDS = 60.0
POLICY_KEY = "pause_on_window_open"


def _stamp(state: Any, now: float) -> float | None:
    try:
        value = state.last_changed.timestamp()
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and 0 <= value <= now else None


def evaluate(runtime: Any, spec: Any, cfg: dict | None = None, *,
             read_only: bool = False) -> dict:
    """Return fresh hold/stop evidence; disabled/no contacts never invent OPEN.

    Unavailable contacts remain visible in diagnostics. Only a reporting contact
    can start or sustain a hold. Hardware dwell is enforced separately.
    """
    cfg = model.settings(runtime.manager, spec) if cfg is None else cfg
    cache = getattr(runtime, "_window_policy_cache", None)
    if read_only:
        # Button/status previews may calculate fresh evidence but must not
        # establish or advance the controller's window-closure baseline.
        cache = dict(cache) if isinstance(cache, dict) else {}
    elif cache is None:
        cache = runtime._window_policy_cache = {}
    previous = cache.get(spec.identifier, {})
    enabled = cfg.get(POLICY_KEY, True) is True
    result = {
        "enabled": enabled, "blocked": False, "stop_requested": False,
        "status": "window_pause_disabled", "resume_delay_seconds": RESUME_SECONDS,
        "remaining_seconds": 0.0, "contacts": [], "open_contacts": [],
        "unknown_contacts": [], "contact_states": {}, "closed_since": None,
        "closed_source_timestamps": {},
    }
    if not enabled:
        cache[spec.identifier] = result
        return result
    contact_ids = selected(runtime.manager.settings, spec.area_id, "windows")
    # For a managed controller, one room's real physical contacts are the
    # ONLY permitted window evidence. A whole-house/stale climate plan can
    # contain foreign contacts and must not block unrelated device owners.
    # An explicit local source remains authoritative even if unavailable.
    from_selection = contact_ids is not None
    if not from_selection:
        plan = getattr(runtime.manager, "plan", None)
        room = next((item for item in (*getattr(plan, "rooms", ()),
                                      *getattr(plan, "climate_rooms", ()))
                     if getattr(item, "area_id", None) == spec.area_id), None)
        if room is not None:
            contact_ids = [item.entity_id for item in room.windows]
        else:
            environment = getattr(plan, "environment", {}) or {}
            area = environment.get(spec.area_id, {})
            climate = area.get("climate_plan", {}) if isinstance(area, dict) else {}
            contact_ids = climate.get("window_contacts") if isinstance(climate, dict) else None
            if contact_ids is None:
                # Missing the whole room inventory is unknown, never proof
                # that the room's own windows are safely closed.
                result.update(
                    blocked=True, status="window_state_unknown",
                    evidence="room_window_inventory_unavailable",
                )
                cache[spec.identifier] = result
                return result
    if not isinstance(contact_ids, (tuple, list)):
        result.update(
            blocked=True, status="window_state_unknown",
            evidence="malformed_window_contact_selection",
        )
        cache[spec.identifier] = result
        return result
    # Wrong-room contacts are never usable as this room's policy sources.
    # Record misconfiguration, but do not mistake a foreign OPEN for the
    # actual room's OPEN or turn a windowless room into a permanent hold.
    # Registry ownership survives missing live states (startup/unloaded
    # integrations); a foreign contact must remain foreign during that gap.
    all_ids = tuple(dict.fromkeys(
        entity for entity in contact_ids if isinstance(entity, str) and entity))
    foreign = tuple(entity for entity in all_ids
                    if entity_area(runtime.hass, entity) not in (spec.area_id, None))
    contact_ids = tuple(entity for entity in all_ids if entity not in foreign)
    if foreign:
        result["ignored_other_room_contacts"] = list(foreign)
    result["contacts"] = list(contact_ids)
    result["identity"] = (spec.area_id, contact_ids)
    if not contact_ids:
        result["status"] = "window_contacts_not_configured"
        cache[spec.identifier] = result
        return result
    now = runtime.clock()
    same = previous.get("identity") == result["identity"]
    same_room = previous.get("identity", (None,))[0] == spec.area_id
    previous_states = previous.get("contact_states", {}) if same_room else {}
    previous_stamps = previous.get("closed_source_timestamps", {}) if same_room else {}
    previous_holds = previous.get("close_holds", {}) if same_room else {}
    holds = {}
    for entity in contact_ids:
        state = runtime.hass.states.get(entity)
        reason = (
            "missing" if state is None else
            "restored" if getattr(state, "attributes", {}).get("restored") is True else
            "unknown" if state.state not in ("on", "off") else
            "invalid_domain" if not entity.startswith("binary_sensor.") else
            "other_area" if entity_area(runtime.hass, entity) != spec.area_id else
            "not_window_contact" if not is_window_contact(
                runtime.hass, state, explicitly_selected=from_selection,
            ) else None
        )
        result["contact_states"][entity] = reason or state.state
        if reason:
            result["unknown_contacts"].append(entity)
            continue
        if state.state == "on":
            result["open_contacts"].append(entity)
            continue
        stamp = _stamp(state, now)
        result["closed_source_timestamps"][entity] = stamp
        last = previous_states.get(entity)
        since = previous_holds.get(entity)
        if last == "on" or (last == "off" and stamp != previous_stamps.get(entity)):
            since = stamp if stamp is not None else now
        elif previous and not same and entity not in previous_states:
            since = now
        if since is not None and now - since < RESUME_SECONDS:
            holds[entity] = since
    result["close_holds"] = holds
    if result["open_contacts"]:
        result.update(blocked=True, stop_requested=True, status="window_open_pause")
    elif any(result["contact_states"][eid] in ("invalid_domain", "other_area", "not_window_contact")
             for eid in result["unknown_contacts"]):
        result.update(blocked=True, status="window_state_unknown")
    elif holds:
        since = max(holds.values())
        result.update(blocked=True, status="window_close_warmup", closed_since=since,
                      remaining_seconds=RESUME_SECONDS - (now - since),
                      stop_requested=previous.get("stop_requested") is True and any(
                          eid in previous_holds or previous_states.get(eid) == "on" for eid in holds))
    elif len(result["unknown_contacts"]) == len(contact_ids):
        result["status"] = "window_state_unknown"
    else:
        result["status"] = "window_closed_ready"
    cache[spec.identifier] = result
    return result

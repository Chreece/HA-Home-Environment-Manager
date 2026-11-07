"""Per-device window stop policy, independent of permanent/manual pause latches.

Read live selected contacts at every command boundary. No service calls, no
sleep(), no timers per entity, no native capability inference or global scans.
"""
from __future__ import annotations

from typing import Any
import math

from . import equipment_model as model
from .discovery import entity_area, is_window
from .room_sources import selected

RESUME_SECONDS = 60.0
POLICY_KEY = "pause_on_window_open"


def _stamp(state: Any, now: float) -> float | None:
    try:
        value = state.last_changed.timestamp()
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and 0 <= value <= now else None


def evaluate(runtime: Any, spec: Any, cfg: dict | None = None) -> dict:
    """Return fresh hold/stop evidence; disabled/no contacts never invent OPEN.

    An unknown contact is not CLOSED. A real open -> closed transition needs
    60 continuous seconds closed. Reopening, losing evidence or changing the
    selected contacts resets this delay. This does not replace hardware dwell.
    """
    cfg = model.settings(runtime.manager, spec) if cfg is None else cfg
    cache = getattr(runtime, "_window_policy_cache", None)
    if cache is None:
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
    closed_times: list[float] = []
    for entity in contact_ids:
        state = runtime.hass.states.get(entity)
        # Explain precisely why the selected contact cannot prove CLOSED.
        # No other area/device is silently used as its replacement.
        reason = (
            "missing" if state is None else
            "invalid_domain" if not entity.startswith("binary_sensor.") else
            "other_area" if entity_area(runtime.hass, entity) != spec.area_id else
            "not_window_contact" if not is_window(runtime.hass, state) else
            "unknown" if state.state not in ("on", "off") else None
        )
        result["contact_states"][entity] = (reason or state.state)
        if reason:
            result["unknown_contacts"].append(entity)
        elif state.state == "on":
            result["open_contacts"].append(entity)
        else:
            changed = _stamp(state, now)
            if changed is None:
                # State is closed but timestamp is not usable. Start a fresh
                # observation period rather than reusing an old safe baseline.
                old_since = previous.get("closed_since") if same else None
                changed = old_since if isinstance(old_since, (int, float)) and 0 <= old_since <= now else now
            closed_times.append(changed)
            result["closed_source_timestamps"][entity] = changed
    same = previous.get("identity") == result["identity"]
    if result["open_contacts"]:
        result.update(blocked=True, stop_requested=True, status="window_open_pause")
    elif result["unknown_contacts"]:
        result.update(blocked=True, status="window_state_unknown",
                      stop_requested=same and previous.get("stop_requested") is True)
    else:
        latest = max(closed_times)
        previous_since = previous.get("closed_since") if same else None
        if not previous:
            # First valid observation of an already-CLOSED contact is a
            # baseline, not proof of an OPEN -> CLOSED transition. HA often
            # recreates all State objects on startup with last_changed=now,
            # even though the physical contact never opened. Applying a 60s
            # window-closure hold here mislabels every restart as a closure.
            # The separate 300s startup hardware protection still applies.
            latest = now - RESUME_SECONDS
        elif not same:
            # Adding/reassigning a selected contact cannot reuse evidence
            # from the old selection, even when both currently report OFF.
            latest = now
        elif previous.get("status") == "window_open_pause":
            # A real OPEN was observed. The physical entity's verified OFF
            # last_changed timestamp identifies the actual closure even if
            # this control tick runs 59 seconds after that event; avoid a
            # second, spurious sixty-second extension at the first read.
            latest = max(closed_times)
        elif previous.get("status") == "window_state_unknown":
            # With missing evidence there is no trustworthy continuity of
            # the CLOSED reading, so require 60 seconds from first recovery.
            latest = now
        elif previous.get("status") == "window_closed_ready":
            # A previously verified CLOSED observation remains ready if its
            # *physical last_changed identity* is unchanged. A new OFF stamp
            # could mean a real OPEN->OFF transition occurred between ticks;
            # don't miss that transition merely because ON was never sampled.
            before_stamps = previous.get("closed_source_timestamps", {})
            before_stamps = before_stamps if isinstance(before_stamps, dict) else {}
            actual_change = any(
                before_stamps.get(entity) != stamp
                for entity, stamp in result["closed_source_timestamps"].items()
            )
            if actual_change:
                latest = max(closed_times)
            else:
                latest = (previous_since
                          if isinstance(previous_since, (int, float))
                          and 0 <= previous_since <= now
                          else now - RESUME_SECONDS)
        elif (isinstance(previous_since, (float, int))
              and 0 <= previous_since <= now):
            # Ongoing real post-close warmup cannot be shortened by an
            # unrelated state update. A newer genuine OFF timestamp may
            # extend it, but can never bypass this safety hold.
            latest = max(latest, previous_since)
        remaining = max(0.0, RESUME_SECONDS - (now - latest))
        result.update(
            closed_since=latest, remaining_seconds=remaining,
            blocked=remaining > 0,
            # Shutdown may finish during the post-close hold, but never from
            # a merely unknown contact that has not actually reported OPEN.
            stop_requested=remaining > 0 and same and bool(
                previous.get("stop_requested") or previous.get("open_contacts")),
            status="window_close_warmup" if remaining > 0 else "window_closed_ready",
        )
    cache[spec.identifier] = result
    return result

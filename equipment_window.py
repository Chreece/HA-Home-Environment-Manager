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
        "unknown_contacts": [], "closed_since": None,
    }
    if not enabled:
        cache[spec.identifier] = result
        return result
    contact_ids = selected(runtime.manager.settings, spec.area_id, "windows")
    if contact_ids is None:
        # Legacy rooms use the same discovered contact inventory as the plan.
        contact_ids = model.plan_for(runtime.manager, spec).get("window_contacts", [])
    if not isinstance(contact_ids, (tuple, list)):
        contact_ids = [""]  # malformed selection is not a verified closed room
    contact_ids = tuple(dict.fromkeys(str(entity) for entity in contact_ids))
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
        if (not entity.startswith("binary_sensor.")
                or entity_area(runtime.hass, entity) != spec.area_id
                or state is None or not is_window(runtime.hass, state)
                or state.state not in ("on", "off")):
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
    same = previous.get("identity") == result["identity"]
    if result["open_contacts"]:
        result.update(blocked=True, stop_requested=True, status="window_open_pause")
    elif result["unknown_contacts"]:
        result.update(blocked=True, status="window_state_unknown",
                      stop_requested=same and previous.get("stop_requested") is True)
    else:
        latest = max(closed_times)
        previous_since = previous.get("closed_since") if same else None
        if previous.get("status") == "window_state_unknown" and same:
            # A return of valid evidence is not proof it stayed closed while
            # that evidence was unavailable.
            latest = now
        if isinstance(previous_since, (float, int)) and 0 <= previous_since <= now:
            latest = max(latest, previous_since)
        # Identity changes do not inherit another contact's completed hold.
        if previous and not same:
            latest = now
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

"""Optional, bounded start deferral; never commands or controls a peer device.

Only explicit direct interior links participate. Native authority, demand,
manual/PID/sleep/away policies and physical timers remain with the runtime.
Missing evidence releases a wait; no assumption of airflow follows from a door.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from collections.abc import Mapping

MAX_WAIT = 180.0
PROGRESS_WINDOW = 60.0
MAX_EPISODES = 128
OPPOSITE = {"heat": "cool", "cool": "heat", "dry": "humidify", "humidify": "dry"}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if isfinite(value) else None
    except (OverflowError, ValueError, TypeError):
        return None


def configured(settings):
    rooms = settings.get("climate_rooms", {})
    return isinstance(rooms, Mapping) and any(
        isinstance(room, Mapping) and isinstance(room.get("door_settings"), Mapping)
        and any(isinstance(item, Mapping) and item.get("coordination") in ("conflicts", "shared")
                for item in room["door_settings"].values()) for room in rooms.values())


class StartBudget:
    """One non-renewable opportunity until verified output, including flapping.

    A release consumes this optional opportunity until the appliance actually
    changes state. A peer change, missing measurement or closure cannot renew it.
    Records are bounded and session-only, never appliance ownership journals.
    """
    def __init__(self):
        self.records = {}

    def decide(self, key, epoch, now, candidate, progress, signature, area):
        record = self.records.get(key)
        if record is not None and record["epoch"] != epoch:
            self.records.pop(key)
            record = None
        if record is None:
            if candidate is None or len(self.records) >= MAX_EPISODES:
                return None
            record = {"epoch": epoch, "started": now, "last": now, "deadline": now + MAX_WAIT,
                      "check_at": now + PROGRESS_WINDOW, "progress": progress,
                      "signature": signature, "area": area, "released": False}
            self.records[key] = record
        if record["released"]:
            return None
        reason = None
        if now < record["last"] or now >= record["deadline"]:
            reason = "budget_complete"
        elif candidate is None or signature != record["signature"]:
            reason = "evidence_or_policy_changed"
        elif candidate["kind"] == "shared" and now >= record["check_at"]:
            previous = record["progress"]
            if progress is None or previous is None or progress - previous < candidate["minimum_progress"]:
                reason = "no_measured_improvement"
            else:
                record.update(check_at=now + PROGRESS_WINDOW, progress=progress)
        record["last"] = now
        if reason:
            record.update(released=True, status=reason)
            return None
        record.update(status="waiting", peer=candidate["peer"], contact=candidate["contact"],
                      kind=candidate["kind"])
        return {"reason": "door_" + candidate["kind"] + "_start_wait",
                "peer": candidate["peer"], "contact": candidate["contact"],
                "remaining_seconds": round(max(0, record["deadline"] - now), 1),
                "deadline": record["deadline"]}


def operation(cap, cfg, native, requested=None):
    """Verified active operation; a selected HVAC mode alone is not output."""
    if cap.domain == "climate":
        if requested in ("heat", "cool", "dry"):
            return requested
        active = {"heating": "heat", "cooling": "cool", "drying": "dry"}.get(native.attributes.get("hvac_action"))
        return active if active == native.state else None
    if cap.domain == "humidifier" and (requested or native.state == "on"):
        return "humidify" if cap.humidifying else "dry"
    if cap.domain == "fan" and cfg.get("fan_purpose") == "filtration" and (requested or native.state == "on"):
        return "filter"
    return None


def metric(values, mode):
    if mode in ("heat", "cool"):
        value = number(values.get("temperature"))
        return None if value is None else value * (1 if mode == "heat" else -1)
    if mode == "filter":
        value = number(values.get("pm25"))
        return None if value is None else -value
    temp, rh = number(values.get("temperature")), number(values.get("humidity"))
    if temp is None or rh is None:
        return None
    from .building_physics import humidity_ratio_g_kg
    ratio = humidity_ratio_g_kg(temp, rh)
    return None if ratio is None else ratio * (1 if mode == "humidify" else -1)


def moderate(values, targets, mode):
    """Conservative operational limits, not medical or building-safety claims."""
    temp, rh, pm = (number(values.get(k)) for k in ("temperature", "humidity", "pm25"))
    if mode in ("heat", "cool"):
        target = number(targets.get(mode))
        return temp is not None and target is not None and 18 <= temp <= 28 and abs(temp - target) < 1.5
    if mode in ("dry", "humidify"):
        target = number(targets.get("humidity"))
        return (temp is not None and 18 <= temp <= 28 and rh is not None
                and target is not None and 30 < rh < 60 and abs(rh - target) < 8)
    return pm is not None and 0 <= pm < 35


def start_hold(runtime, spec, cap, cfg, plan, mode, *, automatic=True, power=True):
    """Called only for a resolved native start and after every dispatch yield."""
    from . import equipment_model as model
    from .room_doors import contact_observation, contact_options
    from .door_settings import inventory, target_areas
    from .device_hierarchy import managed_devices
    from .discovery import entity_area
    from .room_sources import native as native_source
    from .door_context import _source_signature

    now = runtime.clock()
    budget = getattr(runtime, "_door_start_budget", None)
    settings = runtime.manager.settings
    if budget is None and not configured(settings):
        return None
    if budget is None:
        runtime._door_start_budget = budget = StartBudget()
    state = runtime.hass.states.get(cap.primary)
    candidate, progress, signature = None, None, None
    # Unknown/unavailable/active sources cannot be a NEW confirmed OFF start.
    epoch_stamp = getattr(state, "last_changed", None)
    if not isinstance(epoch_stamp, datetime) or epoch_stamp.tzinfo is None:
        return None
    # A reconnect or contact flap cannot buy another delay. Only a verified
    # active native output clears the session opportunity for this controller.
    epoch = cap.primary
    if epoch_stamp.timestamp() > now:
        return None
    if state.state not in ("off", "unknown", "unavailable") and not state.attributes.get("restored"):
        budget.records.pop(spec.identifier, None)
        return None
    eligible = (automatic is True and power is True and mode != "off" and state.state == "off"
                and cfg.get("control_mode") == "automatic" and cfg.get("preset", "none") == "none"
                and plan.get("away") == "home" and plan.get("sleeping") is False
                and plan.get("arrival_preparing") is not True
                and not state.attributes.get("restored"))
    local_mode = operation(cap, cfg, state, mode) if eligible else None
    if local_mode and model.permission(runtime.manager, spec, cap)[1]:
        values = runtime.measurements(spec, cap)
        targets = model.targets(runtime.manager, spec, cap, cfg, plan)
        urgent_mold = (cap.humidity and model.humidity_demand(
            runtime.manager, spec, cap, cfg, plan).get("mold_protection_required") is True)
        if settings.get("use_mold_indicator") is True:
            from .mold_control_demand import room_mold_demand
            urgent_mold = urgent_mold or room_mold_demand(runtime.manager, spec.area_id).get("mold_protection_required") is True
        if not urgent_mold and moderate(values, targets, local_mode):
            links = []
            rooms = settings.get("climate_rooms", {})
            for owner, contact in inventory(runtime.hass, settings):
                config = rooms[owner]
                opts = contact_options(config, contact)
                target = opts["target_area"]
                if (opts["kind"] != "interior" or opts.get("coordination") not in ("conflicts", "shared")
                        or spec.area_id not in (owner, target)
                        or target not in target_areas(runtime.hass, settings, owner)):
                    continue
                observed = contact_observation(runtime.hass, owner, contact, config,
                                               datetime.fromtimestamp(now, timezone.utc))
                if observed["health"] != "ok" or observed["state"] != "open" or observed["state_age_seconds"] < 30:
                    continue
                links.append((target if owner == spec.area_id else owner, contact, opts["coordination"]))
            peers = managed_devices(runtime.hass, runtime.manager.entry.entry_id, settings) if links else ()
            for other, contact, policy in sorted(links)[:128]:
                for peer in peers[:128]:
                    if peer.area_id != other or peer.identifier == spec.identifier or (
                            peer.source_device_id and peer.source_device_id == spec.source_device_id):
                        continue
                    other_cap = model.capabilities(runtime.manager, peer)
                    if other_cap is None:
                        continue
                    native = runtime.hass.states.get(other_cap.primary)
                    record = runtime.records.get(peer.identifier, {})
                    if (native is None or native.state in ("off", "unknown", "unavailable")
                            or native.attributes.get("restored") or record.get("paused") or record.get("pending")
                            or not record.get("power", {}).get(other_cap.primary)
                            or entity_area(runtime.hass, other_cap.primary) != other
                            or not native_source(runtime.hass, other_cap.primary)):
                        continue
                    peer_cfg = model.settings(runtime.manager, peer)
                    peer_plan = model.plan_for(runtime.manager, peer)
                    if (peer_cfg.get("control_mode") != "automatic" or peer_cfg.get("preset", "none") != "none"
                            or peer_plan.get("away") != "home" or peer_plan.get("sleeping") is not False
                            or peer_plan.get("arrival_preparing") is True
                            or not model.permission(runtime.manager, peer, other_cap)[0]):
                        continue
                    peer_mode = operation(other_cap, peer_cfg, native)
                    peer_values = runtime.measurements(peer, other_cap)
                    own_metric = metric(values, local_mode)
                    peer_metric = metric(peer_values, local_mode)
                    if own_metric is None or peer_metric is None:
                        continue
                    kind = "conflicts" if OPPOSITE.get(local_mode) == peer_mode else None
                    if peer_mode == local_mode and policy == "shared":
                        gradient = 3 if local_mode == "filter" else 0.5
                        if peer_metric - own_metric >= gradient:
                            kind = "shared"
                    if kind is None:
                        continue
                    # Never promote a warm/moist peer as a safe drying source.
                    if kind == "shared" and local_mode in ("dry", "humidify"):
                        from .building_physics import humidity_ratio_g_kg, rh_at_temperature_from_ratio
                        ratio = humidity_ratio_g_kg(peer_values["temperature"], peer_values["humidity"])
                        projected = rh_at_temperature_from_ratio(ratio, values["temperature"]) if ratio is not None else None
                        if projected is None or not 30 <= projected < 60:
                            continue
                    candidate = {"kind": kind, "peer": other_cap.primary, "contact": contact,
                                 "minimum_progress": 1 if local_mode == "filter" else 0.1}
                    progress = own_metric
                    signature = (_source_signature(settings, spec.area_id), local_mode,
                                 tuple(sorted(targets.items())), cfg.get("operating_mode"))
                    break
                if candidate is not None:
                    break
    return budget.decide(spec.identifier, epoch, now, candidate, progress, signature, spec.area_id)

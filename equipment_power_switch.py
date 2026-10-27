"""Optional, durable upstream power switch for one managed output.

The switch is an independently selected physical switch.* in the SAME room,
not the controlled output, a Manager-created entity, or another device's
switch. No existing installation changes behavior unless an owner selects it.

An unavailable downstream device is NEVER an idle observation and NEVER
authorizes cutting power. Power-up can be requested from qualified fresh
room measurements and last-known *verified* device capabilities. The native
controller remains logically armed while the external supply is off.
"""
from __future__ import annotations

from collections.abc import Mapping
import time
from typing import Any

from .const import DOMAIN
from .discovery import entity_area
from .pid_math import finite
from . import equipment_model as model

UPSTREAM_MIN_OFF_SECONDS = 600
UPSTREAM_ACK_SECONDS = 120
# External power is never cycled to diagnose or clear a failed device.
_SWITCH_STATES = ("off", "on")


def observed_output_off(state: Any) -> bool:
    """Native switch OFF or a real 0% proportional output, never unavailable."""
    if state is None or state.state in ("unknown", "unavailable"):
        return False
    if getattr(state, "domain", "") in ("number", "input_number"):
        return finite(state.state, 0, 100) == 0
    return state.state == "off"


def relay_identity(hass: Any, spec: Any, entity: str) -> dict | None:
    """Verify a native physical same-room switch and its immutable registry ID."""
    if not isinstance(entity, str) or not entity.startswith("switch."):
        return None
    if entity in spec.source_entities or entity_area(hass, entity) != spec.area_id:
        return None
    from homeassistant.helpers import entity_registry as er
    entry = er.async_get(hass).async_get(entity)
    if entry is None or getattr(entry, "platform", None) == DOMAIN:
        return None
    if (spec.source_device_id is not None
            and getattr(entry, "device_id", None) == spec.source_device_id):
        return None
    stable = getattr(entry, "id", None)
    if not isinstance(stable, str) or not stable:
        return None
    return {"entity": entity, "registry_id": stable,
            "device_id": getattr(entry, "device_id", None),
            "area": spec.area_id}


def _configured_manager_entries(manager: Any) -> tuple[tuple[str, dict], ...]:
    """Inspect unloaded HA config entries as well as loaded controller owners."""
    from .config_data import mutable_copy
    entries = []
    loader = getattr(getattr(manager.hass, "config_entries", None), "async_entries", None)
    if callable(loader):
        for entry in loader(DOMAIN):
            info = mutable_copy({**entry.data, **entry.options})
            entries.append((entry.entry_id, info))
    else:
        entries.append((manager.entry.entry_id, manager.settings))
    return tuple(entries)


def _reserved_outputs(manager: Any) -> set[str]:
    """Legacy direct actuators across ALL configured entries cannot be supplies."""
    from .device_hierarchy import configured_area_ids, configured_sources
    outputs: set[str] = set()
    for _entry_id, settings in _configured_manager_entries(manager):
        for area in configured_area_ids(settings):
            outputs.update(configured_sources(settings, area))
    return outputs


def _other_owners(manager: Any, spec: Any, switch: str) -> bool:
    """Refuse a shared switched supply, even if another entry is not loaded."""
    for entry_id, settings in _configured_manager_entries(manager):
        cfg = settings.get(model.SETTINGS, {})
        if not isinstance(cfg, dict):
            continue
        for key, values in cfg.items():
            if entry_id == manager.entry.entry_id and key == spec.identifier:
                continue
            if isinstance(values, dict) and values.get("power_switch_entity") == switch:
                return True
    return False


def permitted_supply(manager: Any, spec: Any, entity: str,
                     expected: Mapping | None = None) -> dict | None:
    """One output, one exclusive supply, with stable physical identity."""
    identity = relay_identity(manager.hass, spec, entity)
    if (identity is None or entity in _reserved_outputs(manager)
            or _other_owners(manager, spec, entity)
            or expected is not None and dict(expected) != identity):
        return None
    return identity


def supply_options(manager: Any, spec: Any) -> tuple[str, ...]:
    """Offer physical, exact-area switch entities without implicit adoption."""
    candidates = []
    for state in manager.hass.states.async_all("switch"):
        entity = state.entity_id
        if permitted_supply(manager, spec, entity) is not None:
            candidates.append(entity)
    saved = model.settings(manager, spec).get("power_switch_entity")
    if saved and saved not in candidates:
        # Keep an existing identity visible for safe removal/reconciliation,
        # but selection and operation still require successful validation.
        candidates.append(saved)
    return tuple(dict.fromkeys(sorted(candidates)))


def output_required(cap: Any, targets: Mapping, measurements: Mapping,
                    *, method: str, requested_mode: str | None,
                    fan_purpose: str | None, plan: Mapping) -> bool | None:
    """Return TRUE only for verified actual demand, FALSE for verified idle.

    None means insufficient evidence or unsupported intent. No outlet ON/OFF
    can be inferred from a disconnected appliance alone. PID PWM gaps still
    count as demand while temperature/humidity/air quality is out of band.
    """
    if method == "off":
        return False
    if method == "existing":
        return None
    if method == "manual":
        if requested_mode == "off":
            return False
        return True if requested_mode in cap.modes and requested_mode != "off" else None
    if method not in ("automatic", "pid"):
        return None
    if requested_mode == "off":
        return False
    modes = set(cap.modes)
    if requested_mode and requested_mode not in modes:
        return None

    def reading(metric: str, low: float, high: float) -> float | None:
        return finite(measurements.get(metric), low, high)

    if cap.domain == "fan" or modes == {"off", "fan_only"}:
        purpose = fan_purpose
        if purpose == "extraction":
            if plan.get("air_actions", {}).get("outdoor_air_verified") is not True:
                return None
            value = reading("co2", 0, 20000)
            target = finite(plan.get("air_actions", {}).get("thresholds", {}).get(
                "co2_operational_ppm"), 0, 20000)
            margin = 50.
        elif purpose == "filtration":
            value = reading("pm25", 0, 2000)
            target = finite(plan.get("air_actions", {}).get("thresholds", {}).get(
                "pm25_short_term_action_ug_m3"), 0, 2000)
            margin = 2.
        else:
            return None
        if value is None or target is None:
            return None
        return value > target + margin if value > target + margin else (
            False if value <= target - margin else None
        )

    if cap.domain == "humidifier" or (
        "dry" in modes and requested_mode == "dry"
    ) or (modes <= {"off", "dry"} and "dry" in modes):
        current = reading("humidity", 0, 100)
        target = finite(targets.get("humidity"), 0, 100)
        if current is None or target is None:
            return None
        humidifying = bool(getattr(cap, "humidifying", False))
        gap = target-current if humidifying else current-target
        return True if gap > 2 else False if gap < -2 else None

    if "heat" in modes or "cool" in modes or "heat_cool" in modes or "auto" in modes:
        value = reading("temperature", -40, 80)
        heat = finite(targets.get("heat"), -30, 60)
        cool = finite(targets.get("cool"), -30, 60)
        if value is None or heat is None or cool is None or cool-heat < 1:
            return None
        allowed = {requested_mode} if requested_mode else modes
        heat_allowed = bool(allowed & {"heat", "heat_cool", "auto"})
        cool_allowed = bool(allowed & {"cool", "heat_cool", "auto"})
        if heat_allowed and value < heat - .3:
            return True
        if cool_allowed and value > cool + .3:
            return True
        if not heat_allowed and not cool_allowed:
            return None
        # Hysteresis deadband is an indeterminate transition, not a license
        # to power down an appliance whose physical state was not checked.
        if heat + .3 <= value <= cool - .3:
            return False
        return None

    if "dry" in modes:
        current = reading("humidity", 0, 100)
        target = finite(targets.get("humidity"), 0, 100)
        if current is None or target is None:
            return None
        return True if current > target + 2 else False if current < target - 2 else None
    return None


def _observed_off_since(state: Any, now: float) -> float:
    try:
        stamp = state.last_changed.timestamp()
    except (AttributeError, ValueError, OverflowError):
        return now
    parsed = finite(stamp, 0, 1e13)
    return parsed if parsed is not None and parsed <= now else now


def verified_capabilities(runtime: Any, spec: Any) -> Any:
    """Previously observed capabilities may guide power-up, never native I/O."""
    cap = model.capabilities(runtime.manager, spec)
    # A stale 'unavailable' native HA state can retain attributes. Never
    # promote those attributes into a newly verified capability source.
    if cap is not None and model.sources_available(runtime.manager, spec):
        return cap
    record = runtime.records.get(spec.identifier, {})
    if record.get("sources") != list(spec.source_entities) or record.get("area") != spec.area_id:
        return None
    saved = record.get("capabilities")
    if not isinstance(saved, dict):
        return None
    try:
        cached = model.Capabilities(**saved)
    except (TypeError, ValueError):
        return None
    if (cached.primary not in spec.source_entities
            or cached.domain not in ("climate", "humidifier", "fan",
                                     "switch", "input_boolean", "number", "input_number")):
        return None
    return cached


def approved_demand(runtime: Any, spec: Any, cfg: dict,
                    cap: Any) -> bool | None:
    """Live policies and feedback must authorize EACH upstream decision."""
    from .device_activation import authorized, effective_device
    from .occupancy_policy import live_device_permission
    from .climate_arbitration import _contact_interlock
    if not authorized(runtime.manager, spec):
        return None
    method = cfg.get("control_mode")
    if method not in ("automatic", "pid", "manual", "off"):
        return None
    plan = model.plan_for(runtime.manager, spec)
    live = effective_device(runtime.manager, spec, cap.primary)
    room = model.room_config(runtime.manager, spec)
    if method != "off":
        approved, _reason = live_device_permission(
            runtime.hass, spec.area_id, room, plan, live
        )
        if approved != "eligible":
            return None
    if method in ("automatic", "pid", "manual"):
        if (plan.get("window_safe") is not True
                or (cap.domain != "fan" and
                    not _contact_interlock(runtime.hass, spec.area_id, plan))):
            return None
    targets = model.targets(runtime.manager, spec, cap, cfg, plan)
    observed = runtime.measurements(spec, cap)
    return output_required(
        cap, targets, observed, method=method,
        requested_mode=cfg.get("requested_mode"),
        fan_purpose=live.get("fan_purpose"), plan=plan,
    )


def _dispatch_safe(runtime: Any, spec: Any, record: dict, cfg: dict,
                   entity: str, desired: str) -> bool:
    """Re-evaluate physical and sensor truth AFTER every awaited Store write."""
    cap = verified_capabilities(runtime, spec)
    if cap is None or not runtime._current_spec(spec):
        return False
    now = runtime.clock()
    relay = record.get("upstream", {})
    state = runtime.hass.states.get(entity)
    if state is None or state.state != ("off" if desired == "on" else "on"):
        return False
    if desired == "on":
        if now-runtime._started < 300:
            return False
        since = max(finite(relay.get("off_at"), 0, 1e13) or 0,
                    _observed_off_since(state, now))
        if now-since < UPSTREAM_MIN_OFF_SECONDS:
            return False
        native = runtime.hass.states.get(cap.primary)
        if (native is not None and native.state not in ("unknown", "unavailable")
                and not observed_output_off(native)):
            return False
        return approved_demand(runtime, spec, cfg, cap) is True
    if not relay.get("owned") or now-runtime._started < 300:
        return False
    started = finite(relay.get("idle_since"), 0, 1e13)
    cooldown = finite(cfg.get("power_switch_cooldown_seconds"), 60, 86400)
    if started is None or cooldown is None or now-started < cooldown:
        return False
    if approved_demand(runtime, spec, cfg, cap) is not False:
        return False
    if record.get("power") or record.get("pending"):
        return False
    for source in spec.source_entities:
        native = runtime.hass.states.get(source)
        if (native is None or native.state in ("unknown", "unavailable")
                or native.attributes.get("hvac_action") == "defrosting"):
            return False
        if not observed_output_off(native):
            return False
    return True


async def _send(runtime: Any, spec: Any, record: dict, identity: dict,
                desired: str) -> bool:
    """Save exact-switch intent before switching, then await real HA ACK."""
    relay = record.setdefault("upstream", {})
    if (desired not in _SWITCH_STATES or relay.get("pending")
            or relay.get("paused") or not runtime._active or not runtime._ready):
        return False
    entity = identity["entity"]
    observed = runtime.hass.states.get(entity)
    if (observed is None or observed.state not in _SWITCH_STATES
            or not runtime.hass.services.has_service("switch", "turn_" + desired)):
        return False
    if observed.state == desired:
        return False
    before_settings = runtime.manager.settings
    when = runtime.clock()
    relay["pending"] = {"desired": desired, "when": when,
                        "identity": identity, "phase": "intent"}
    await runtime._save()
    # All power work is serialized by the per-output lock in EquipmentRuntime.
    # Once persistence has yielded, reject any changed consent or source ID.
    cfg = model.settings(runtime.manager, spec)
    if (not runtime._active or not runtime._ready
            or cfg.get("power_switch_entity") != entity
            or not runtime._current_spec(spec)
            or permitted_supply(runtime.manager, spec, entity, identity) is None
            or runtime.hass.states.get(entity) is not observed
            or runtime.manager.settings != before_settings
            or not _dispatch_safe(runtime, spec, record, cfg, entity, desired)):
        relay["pending"] = None
        await runtime._save()
        return False
    try:
        async with runtime._commands:
            if (not runtime._active or not runtime._ready
                    or cfg.get("power_switch_entity") != entity
                    or permitted_supply(runtime.manager, spec, entity, identity) is None
                    or runtime.hass.states.get(entity) is not observed
                    or not _dispatch_safe(runtime, spec, record, cfg, entity, desired)):
                relay["pending"] = None
                await runtime._save()
                return False
            await runtime.hass.services.async_call(
                "switch", "turn_" + desired, {},
                target={"entity_id": entity}, blocking=True,
            )
        relay["pending"]["phase"] = "commanded"
        await runtime._save()
        return True
    except Exception:
        # The physical switch may have changed even if HA raised. Do not
        # reverse/guess: persist uncertainty until manual reconciliation.
        relay["paused"] = "switch_command_failed_or_uncertain"
        await runtime._save()
        return False


def prepare_offline_pid(runtime: Any, spec: Any, cap: Any, cfg: dict,
                        demand_verified: bool | None) -> dict:
    """Prepare the *supervisor* from independent sensors while supply is OFF.

    No native device command and no physical startup inferred here. Proportional
    demand is estimated with live sensor readings; I and D are explicitly zero
    because the disconnected plant cannot respond (anti-windup and bumpless
    derivative restart). Re-seed the latest observed measurement on every
    valid OFF evaluation so a disconnected interval is never integrated on
    reconnect. Output PWM timing starts afresh when the outlet is energized.
    """
    if cfg.get("control_mode") != "pid" or demand_verified is None:
        runtime._memory.pop(spec.identifier, None)
        return {"status": "not_prepared", "reason": "not_pid_or_unverified_demand"}
    now = runtime.clock()
    plan = model.plan_for(runtime.manager, spec)
    target = model.targets(runtime.manager, spec, cap, cfg, plan)
    measured = runtime.measurements(spec, cap)
    from .dry_mode import automatic_mode
    mode = cfg.get("requested_mode")
    if mode not in cap.modes or mode == "off":
        mode = automatic_mode(
            cap, None, measured, target,
            dedicated_dry=model.room_config(runtime.manager, spec).get(
                "dry_climate_entity") == cap.primary,
            pid=True,
        )
    if mode not in cap.modes or mode in ("off", "auto", "heat_cool", None):
        runtime._memory.pop(spec.identifier, None)
        return {"status": "not_prepared", "reason": "explicit_single_direction_required"}
    if cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"}:
        from .device_activation import effective_device
        device = effective_device(runtime.manager, spec, cap.primary)
        metric = ("co2" if device.get("fan_purpose") == "extraction" else
                  "pm25" if device.get("fan_purpose") == "filtration" else None)
        threshold = ("co2_operational_ppm" if metric == "co2" else
                     "pm25_short_term_action_ug_m3")
        goal = plan.get("air_actions", {}).get("thresholds", {}).get(threshold)
        increasing = False
    elif cap.domain == "humidifier" or mode == "dry":
        metric = "humidity"
        goal = target.get("humidity")
        increasing = bool(cap.humidifying)
    elif mode in ("heat", "cool"):
        metric = "temperature"
        goal = target.get(mode)
        increasing = mode == "heat"
    else:
        metric, goal, increasing = None, None, False
    value = finite(measured.get(metric), -50 if metric == "temperature" else 0,
                   20000 if metric == "co2" else 2000 if metric == "pm25" else
                   100 if metric == "humidity" else 0) if metric else None
    goal = finite(goal, -50 if metric == "temperature" else 0,
                  20000 if metric == "co2" else 2000 if metric == "pm25" else
                  100 if metric == "humidity" else 0) if metric else None
    if value is None or goal is None:
        runtime._memory.pop(spec.identifier, None)
        return {"status": "not_prepared", "reason": "fresh_independent_sensor_required"}
    kp = finite(cfg.get("kp"), 0, 100)
    if kp is None:
        runtime._memory.pop(spec.identifier, None)
        return {"status": "not_prepared", "reason": "invalid_pid_gain"}
    error = (goal-value) if increasing else (value-goal)
    proportional = round(max(0., min(100., kp*error)), 3)
    signature = (
        metric, goal, increasing, cfg.get("preset"),
        cfg.get("kp"), cfg.get("ki"), cfg.get("kd"),
    )
    # Imported here to avoid coupling the independent supply module to a
    # physical thermostat driver or the HA/PID scheduling implementation.
    memory = model.PIDMemory(
        integral=0., measured=value, stamp=now, derivative=0.,
        demand=proportional,
    )
    runtime._memory[spec.identifier] = (signature, memory, now)
    return {
        "status": "prepared_proportional_only", "metric": metric,
        "direction": mode, "sample_value": value, "target": goal,
        "proportional_demand_percent": proportional,
        "integral_frozen": True, "derivative_reseeded": True,
        "native_output_active": False,
    }


async def before_tick(runtime: Any, spec: Any) -> bool:
    """Return True when outlet control handled/held the native control tick.

    This precedes sources_available() deliberately: a source loses its HA state
    when its own power plug turns off. The logical controller remains armed.
    """
    cfg = model.settings(runtime.manager, spec)
    selected = cfg.get("power_switch_entity")
    if not selected:
        return False
    record = runtime._record(spec)
    relay = record.setdefault("upstream", {})
    if relay.get("entity") != selected:
        if relay.get("owned") or relay.get("pending"):
            runtime._status(spec, "paused", reason="owned_switch_configuration_changed")
            return True
        relay.clear()
        relay["entity"] = selected
        relay["identity"] = permitted_supply(runtime.manager, spec, selected)
        relay["owned"] = False
        await runtime._save()
    identity = permitted_supply(runtime.manager, spec, selected, relay.get("identity"))
    if identity is None or not runtime._current_spec(spec):
        runtime._status(spec, "paused", reason="upstream_switch_identity_or_room_invalid")
        return True
    observed = runtime.hass.states.get(selected)
    if observed is None or observed.state not in _SWITCH_STATES:
        runtime._status(spec, "waiting_for_physical_device", reason="upstream_switch_unavailable")
        return True
    now = runtime.clock()
    pending = relay.get("pending")
    if pending:
        if (pending.get("identity") != identity or pending.get("desired") not in _SWITCH_STATES):
            relay["paused"] = "upstream_switch_pending_identity_changed"
            await runtime._save()
            runtime._status(spec, "paused", reason=relay["paused"])
            return True
        if observed.state == pending["desired"]:
            relay["pending"] = None
            relay["owned"] = pending["desired"] == "on"
            relay["off_at"] = now if observed.state == "off" else relay.get("off_at", now)
            relay["idle_since"] = None
            await runtime._save()
        elif now-pending["when"] > UPSTREAM_ACK_SECONDS:
            relay["paused"] = "upstream_switch_ack_missing"
            await runtime._save()
            runtime._status(spec, "paused", reason=relay["paused"])
            return True
        else:
            runtime._status(spec, "awaiting_physical_acknowledgement",
                            reason="upstream_switch_waiting_for_ack")
            return True
    if relay.get("paused"):
        runtime._status(spec, "paused", reason=relay["paused"])
        return True
    if observed.state == "off" and relay.get("owned"):
        # A third party switched OFF a previously controller-owned outlet.
        # Never switch it on again without the user's intervention.
        relay["paused"] = "upstream_switch_manual_override"
        await runtime._save()
        runtime._status(spec, "paused", reason=relay["paused"])
        return True

    cap = verified_capabilities(runtime, spec)
    if cap is None:
        runtime._status(spec, "waiting_for_physical_device",
                        reason="upstream_switch_capabilities_not_verified")
        return observed.state == "off"
    demand = approved_demand(runtime, spec, cfg, cap)
    if observed.state == "off":
        # Keep independent room/PID preparation live before an unavailable
        # physical appliance could stop the ordinary native control path.
        preview = prepare_offline_pid(runtime, spec, cap, cfg, demand)
        runtime._pid_offline_previews[spec.identifier] = preview
        if relay.get("idle_since") is not None:
            relay["idle_since"] = None
            await runtime._save()
        if demand is not True:
            runtime._status(spec, "within_target_band" if demand is False
                            else "waiting_for_physical_device",
                            reason="upstream_switch_off_no_verified_demand")
            return True
        if now-runtime._started < 300:
            runtime._status(spec, "startup_warmup")
            return True
        since = max(finite(relay.get("off_at"), 0, 1e13) or 0,
                    _observed_off_since(observed, now))
        if now-since < UPSTREAM_MIN_OFF_SECONDS:
            runtime._status(spec, "minimum_off_hold",
                            reason="upstream_switch_minimum_off")
            return True
        # No physical output can be assumed harmless if it reports active
        # while an external supply claims OFF.
        native = runtime.hass.states.get(cap.primary)
        if (native is not None and native.state not in ("unknown", "unavailable")
                and not observed_output_off(native)):
            runtime._status(spec, "paused",
                            reason="upstream_switch_off_but_native_reports_active")
            return True
        if not runtime.hass.services.has_service("switch", "turn_on"):
            runtime._status(spec, "native_service_unavailable")
            return True
        await _send(runtime, spec, record, identity, "on")
        return True

    runtime._pid_offline_previews.pop(spec.identifier, None)
    # Switch is ON. Do not assume it belongs to us just because it is ON.
    if not relay.get("owned"):
        return False
    # An unknown downstream condition is never "no demand".
    native = runtime.hass.states.get(cap.primary)
    native_off = observed_output_off(native)
    no_native_write = not record.get("power") and not record.get("pending")
    no_defrost = native is not None and native.attributes.get("hvac_action") != "defrosting"
    no_active_output = all(
        (state := runtime.hass.states.get(entity)) is not None
        and state.state not in ("unknown", "unavailable")
        and (state.state == "off" or
             entity.startswith(("number.", "input_number."))
             and finite(state.state, 0, 100) == 0)
        for entity in spec.source_entities
    )
    safe_idle = (demand is False and native_off and no_native_write
                 and no_defrost and no_active_output
                 and now-runtime._started >= 300)
    if not safe_idle:
        if relay.get("idle_since") is not None:
            relay["idle_since"] = None
            await runtime._save()
        return False
    if relay.get("idle_since") is None:
        relay["idle_since"] = now
        await runtime._save()
        return False
    if now-relay["idle_since"] < cfg["power_switch_cooldown_seconds"]:
        return False
    if not runtime.hass.services.has_service("switch", "turn_off"):
        runtime._status(spec, "native_service_unavailable")
        return True
    await _send(runtime, spec, record, identity, "off")
    return True

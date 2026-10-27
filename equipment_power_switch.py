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
    # This function runs on Home Assistant's main thread. Beta55 made a
    # recursive deepcopy of every config entry for *each* switch candidate
    # whenever a SelectEntity state was evaluated. That is unacceptable on
    # large installations, and it was unnecessary: the claims are read-only.
    loader = getattr(getattr(manager.hass, "config_entries", None), "async_entries", None)
    if not callable(loader):
        return ((manager.entry.entry_id, manager.settings),)
    return tuple(
        (entry.entry_id, {**entry.data, **entry.options})
        for entry in loader(DOMAIN)
    )


def _switch_claims(manager: Any, spec: Any) -> tuple[set[str], set[str]]:
    """Read all configured output/supply claims ONCE per request.

    No deep copying, no repeated scans per candidate switch, no mutation.
    Include unloaded config entries so a shared supply is never authorized.
    This is for filtering choices only; every actual service command still
    revalidates identity, ownership and live configuration.
    """
    from .device_hierarchy import configured_area_ids, configured_sources
    reserved: set[str] = set()
    assigned: set[str] = set()
    for entry_id, settings in _configured_manager_entries(manager):
        for area in configured_area_ids(settings):
            reserved.update(configured_sources(settings, area))
        controllers = settings.get(model.SETTINGS, {})
        if not isinstance(controllers, dict):
            continue
        for key, values in controllers.items():
            if entry_id == manager.entry.entry_id and key == spec.identifier:
                continue
            if not isinstance(values, dict):
                continue
            switch = values.get("power_switch_entity")
            if isinstance(switch, str) and switch:
                assigned.add(switch)
    return reserved, assigned


def permitted_supply(manager: Any, spec: Any, entity: str,
                     expected: Mapping | None = None) -> dict | None:
    """Exact-device supply permission, independently rechecked at dispatch."""
    identity = relay_identity(manager.hass, spec, entity)
    if identity is None:
        return None
    if expected is not None and dict(expected) != identity:
        return None
    outputs, used_supplies = _switch_claims(manager, spec)
    if entity in outputs or entity in used_supplies:
        return None
    return identity


def supply_options(manager: Any, spec: Any) -> tuple[str, ...]:
    """Discover registered same-room switches even when temporarily offline.

    One lazy registry pass per selector, never on every state serialization.
    Runtime actuation rechecks immutable registry identity, room and ownership.
    """
    from homeassistant.helpers import entity_registry as er

    outputs, used_supplies = _switch_claims(manager, spec)
    candidates: list[str] = []
    registry = er.async_get(manager.hass)
    for entry in registry.entities.values():
        entity = entry.entity_id
        if not entity.startswith("switch."):
            continue
        if entity in outputs or entity in used_supplies:
            continue
        if entity_area(manager.hass, entity) != spec.area_id:
            continue
        if relay_identity(manager.hass, spec, entity) is not None:
            candidates.append(entity)
    saved = model.settings(manager, spec).get("power_switch_entity")
    if isinstance(saved, str) and saved and saved not in candidates:
        # Keep a previously selected identity visible, even if unavailable
        # or now outside the area. It does not gain dispatch permission.
        candidates.append(saved)
    return tuple(sorted(set(candidates)))


def supply_option_labels(hass: Any, entities: tuple[str, ...]) -> dict[str, str]:
    """Render Friendly Device - Friendly Entity (state), without losing IDs.

    Standalone entities have no registered HA device name; use their friendly
    entity name rather than inventing a device. Disambiguate duplicate labels.
    This runs only against cached candidate IDs, never a global switch scan.
    """
    from collections import Counter
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    registry, devices = er.async_get(hass), dr.async_get(hass)
    display: dict[str, str] = {}
    for entity in entities:
        registered = registry.async_get(entity)
        state = hass.states.get(entity)
        device = devices.async_get(registered.device_id) if (
            registered is not None and registered.device_id) else None
        device_name = (getattr(device, "name_by_user", None)
                       or getattr(device, "name", None))
        entity_name = (getattr(state, "name", None)
                       or getattr(registered, "name", None)
                       or getattr(registered, "original_name", None)
                       or entity)
        actual_state = state.state if state is not None else "unavailable"
        display[entity] = (
            f"{device_name} - {entity_name} ({actual_state})"
            if device_name else f"{entity_name} ({actual_state})"
        )
    repetitions = Counter(display.values())
    return {
        entity: (f"{label} [{entity}]" if repetitions[label] > 1 else label)
        for entity, label in display.items()
    }


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


def cold_start_direction_demand(runtime: Any, spec: Any, cfg: dict) -> bool | None:
    """Use explicit saved direction or uniquely identified native purpose.

    The trusted source ID, current exact-device authorization, active PID
    selection and independent room measurements are required. HA sometimes
    has only a DRY-capable native state that is marked unavailable, or an
    explicit room "dry_climate_entity" mapping. Those hints are valid ONLY
    for restoring the separate power relay - never native HVAC commands,
    physical mode advertisements, or persistent verified capabilities.
    """
    if cfg.get("control_mode") not in ("automatic", "pid"):
        return None
    if len(spec.source_entities) != 1:
        return None
    source = spec.source_entities[0]
    domain = source.partition(".")[0]
    if domain not in ("climate", "humidifier"):
        return None
    direction = cfg.get("requested_mode")
    if direction is None:
        native = model.capabilities(runtime.manager, spec)
        # An unavailable state with real HA-advertised HVAC modes may still
        # identify a SINGLE physical purpose. It cannot authenticate a
        # running appliance or qualify for native service dispatch.
        if native is not None and native.primary == source:
            modes = set(native.modes) - {"off"}
            if len(modes) == 1 and next(iter(modes)) in (
                    "heat", "cool", "dry"):
                direction = next(iter(modes))
        if direction is None:
            room = model.room_config(runtime.manager, spec)
            possible = []
            for key, option in (
                ("heat_climate_entity", "heat"),
                ("cool_climate_entity", "cool"),
                ("dry_climate_entity", "dry"),
                ("dehumidifier_entity", "dry"),
            ):
                if room.get(key) == source:
                    possible.append(option)
            if len(set(possible)) == 1 and possible:
                direction = possible[0]
    if direction not in ("heat", "cool", "dry"):
        return None
    # A humidity-only HA endpoint cannot be assigned a temperature role.
    if domain == "humidifier" and direction != "dry":
        return None
    provisional = model.Capabilities(
        primary=source, domain=domain, modes=("off", direction),
        temperature=direction in ("heat", "cool"),
        humidity=direction == "dry",
    )
    return approved_demand(runtime, spec, cfg, provisional)


def cold_start_dispatch_safe(runtime: Any, spec: Any, record: dict,
                             cfg: dict, entity: str) -> bool:
    """Verify a single OFF->ON supply wake after every asynchronous yield.

    The disconnected native source must never be considered OFF by itself.
    A physically OFF upstream relay, exact area/identity, independent fresh
    room demand and the hard OFF dwell are required. This path is not used
    for supply OFF or ANY native climate control command.
    """
    if not runtime._active or not runtime._ready or not runtime._current_spec(spec):
        return False
    if cfg.get("power_switch_entity") != entity:
        return False
    relay = record.get("upstream", {})
    if relay.get("paused") or relay.get("owned"):
        return False
    if record.get("power") or record.get("pending"):
        return False
    observed = runtime.hass.states.get(entity)
    if observed is None or observed.state != "off":
        return False
    if verified_capabilities(runtime, spec) is not None:
        return False  # The established capability-driven path owns this case.
    now = runtime.clock()
    if now - runtime._started < 300:
        return False
    since = max(
        finite(relay.get("off_at"), 0, 1e13) or 0,
        _observed_off_since(observed, now),
    )
    if now - since < UPSTREAM_MIN_OFF_SECONDS:
        return False
    for source in spec.source_entities:
        native = runtime.hass.states.get(source)
        if (native is not None
                and native.state not in ("unknown", "unavailable")
                and not observed_output_off(native)):
            return False
    return cold_start_direction_demand(runtime, spec, cfg) is True


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
        approved, reason = live_device_permission(
            runtime.hass, spec.area_id, room, plan, live
        )
        if reason == "sleep_room_control_paused":
            # Sleep Pause is a verified shutdown request, not missing demand.
            # The native output must turn OFF first; only a subsequently
            # confirmed idle and controller-owned relay may turn OFF after
            # its configured power_switch_cooldown_seconds.
            return False
        if approved != "eligible":
            # Unknown sleep/presence still blocks ON but is NEVER proof that
            # cutting the supply to a running device is safe.
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
        # Pairing while the native appliance is running is configuration
        # only. Never energize an external supply during an unresolved native
        # power command or while the manager still owns a native ON output.
        if record.get("power") or record.get("pending"):
            return False
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
                desired: str, *, cold_start: bool = False) -> bool:
    """Save exact-switch intent before switching, then await real HA ACK."""
    relay = record.setdefault("upstream", {})
    if (desired not in _SWITCH_STATES or relay.get("pending")
            or relay.get("paused") or not runtime._active or not runtime._ready
            or cold_start and desired != "on"):
        return False
    entity = identity["entity"]

    def safe_to_dispatch(cfg: dict) -> bool:
        return (cold_start_dispatch_safe(runtime, spec, record, cfg, entity)
                if cold_start else
                _dispatch_safe(runtime, spec, record, cfg, entity, desired))
    observed = runtime.hass.states.get(entity)
    if (observed is None or observed.state not in _SWITCH_STATES
            or not runtime.hass.services.has_service("switch", "turn_" + desired)):
        return False
    if observed.state == desired:
        return False
    before_settings = runtime.manager.settings
    when = runtime.clock()
    relay["pending"] = {"desired": desired, "when": when,
                        "identity": identity, "phase": "intent",
                        "cold_start": cold_start}
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
            or not safe_to_dispatch(cfg)):
        relay["pending"] = None
        await runtime._save()
        return False
    try:
        async with runtime._commands:
            if (not runtime._active or not runtime._ready
                    or cfg.get("power_switch_entity") != entity
                    or permitted_supply(runtime.manager, spec, entity, identity) is None
                    or runtime.hass.states.get(entity) is not observed
                    or not safe_to_dispatch(cfg)):
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
    mode = cfg.get("requested_mode")
    if mode not in cap.modes or mode == "off":
        from .dry_mode import automatic_mode
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
    bounds = {
        "temperature": (-50., 85.),
        "humidity": (0., 100.),
        "co2": (0., 20000.),
        "pm25": (0., 2000.),
    }.get(metric)
    value = finite(measured.get(metric), *bounds) if bounds else None
    goal = finite(goal, *bounds) if bounds else None
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
        if observed.state != "off":
            runtime._status(spec, "waiting_for_physical_device",
                            reason="upstream_on_native_device_not_reporting")
            return True
        # The selected OFF supply can itself explain native unavailability.
        # A previously authorized, explicit DRY/HEAT/COOL direction can be
        # awakened from FRESH INDEPENDENT demand without native I/O. Without
        # such evidence, hold and say why rather than waiting in a deadlock.
        if record.get("power") or record.get("pending"):
            runtime._status(spec, "owned_shutdown_identity_or_dwell_hold",
                            reason="native_output_ownership_unreconciled")
            return True
        cold_demand = cold_start_direction_demand(runtime, spec, cfg)
        if cold_demand is not True:
            runtime._status(spec, "waiting_for_physical_device",
                            reason="upstream_startup_needs_authorized_direction_and_fresh_demand")
            return True
        if now - runtime._started < 300:
            runtime._status(spec, "startup_warmup")
            return True
        since = max(finite(relay.get("off_at"), 0, 1e13) or 0,
                    _observed_off_since(observed, now))
        if now - since < UPSTREAM_MIN_OFF_SECONDS:
            runtime._status(spec, "minimum_off_hold",
                            reason="upstream_switch_minimum_off")
            return True
        if not cold_start_dispatch_safe(runtime, spec, record, cfg, selected):
            runtime._status(spec, "waiting_for_physical_device",
                            reason="upstream_startup_conditions_changed")
            return True
        await _send(runtime, spec, record, identity, "on", cold_start=True)
        return True
    demand = approved_demand(runtime, spec, cfg, cap)
    if observed.state == "off":
        # A supply may be selected even while a native appliance is running.
        # If that supply later becomes OFF, never re-energize it while the
        # physical appliance still has an owned or pending native output.
        if record.get("power") or record.get("pending"):
            runtime._status(spec, "owned_shutdown_identity_or_dwell_hold",
                            reason="native_output_ownership_unreconciled")
            return True
        # Keep independent room/PID preparation live before an unavailable
        # physical appliance could stop the ordinary native control path.
        preview = prepare_offline_pid(runtime, spec, cap, cfg, demand)
        runtime._pid_offline_previews[spec.identifier] = preview
        if relay.get("idle_since") is not None:
            relay["idle_since"] = None
            await runtime._save()
        if demand is not True:
            from .device_activation import effective_device
            from .occupancy_policy import live_device_permission
            current_plan = model.plan_for(runtime.manager, spec)
            current_room = model.room_config(runtime.manager, spec)
            live = effective_device(runtime.manager, spec, cap.primary)
            _, reason = live_device_permission(
                runtime.hass, spec.area_id, current_room, current_plan, live
            )
            runtime._status(
                spec,
                "sleep_room_control_paused" if reason == "sleep_room_control_paused"
                else "within_target_band" if demand is False
                else "waiting_for_physical_device",
                reason=(reason if reason == "sleep_room_control_paused"
                        else "upstream_switch_off_no_verified_demand"),
            )
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

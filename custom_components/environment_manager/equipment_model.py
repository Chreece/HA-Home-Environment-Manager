"""Capability-driven managed equipment model; no services or registry mutations.

The logical climate entity represents a Manager controller, not a second
physical appliance. Unsupported HVAC modes and invented measurements are never
advertised. All internal temperatures are Celsius; native endpoints are converted
at the write boundary. Existing room controllers remain selected until the user
explicitly chooses a new per-device owner.
"""
from __future__ import annotations

from .config_data import mutable_copy as deepcopy
from dataclasses import dataclass
import math
import hashlib
from typing import Any

from .const import DOMAIN
from .device_hierarchy import ManagedDevice, configured_sources
from .pid_math import finite, target_from_unit
from .climate_strategy import DEFAULT_PROFILE_TARGETS, profile_humidity_target

SETTINGS = "equipment_controllers"
PRESETS = ("none", "home", "comfort", "away", "sleep", "eco")
CONTROL_MODES = ("existing", "automatic", "manual", "off", "pid")
# Native ClimateEntityFeature values, used without importing HA platforms here.
TEMP, RANGE, HUMIDITY, FAN, PRESET, SWING, SWING_H = 1, 2, 4, 8, 16, 32, 512
HVAC_MODES = frozenset(("off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only"))
NUMBER_FIELDS = {
    "kp": (0.001, 100.0, 0.001, None, 10.0),
    "ki": (0.0, 10.0, 0.001, None, 0.1),
    "kd": (0.0, 50.0, 0.01, None, 0.0),
    "sample_seconds": (120.0, 3600.0, 30.0, "s", 300.0),
    "cycle_seconds": (600.0, 86400.0, 60.0, "s", 3600.0),
    "quiet_percentage": (1.0, 100.0, 1.0, "%", 30.0),
    "min_on_seconds": (0.0, 7200.0, 1.0, "s", 600.0),
    "min_off_seconds": (0.0, 14400.0, 1.0, "s", 600.0),
    "max_on_seconds": (900.0, 86400.0, 60.0, "s", 7200.0),
    # Upstream outlet remains separate from the native output. A continuously
    # verified idle period is required before any controller-owned outlet OFF.
    "power_switch_cooldown_seconds": (60.0, 86400.0, 60.0, "s", 600.0),
    # Manufacturer-rated *particle* CADR for a purifier, not fan airflow
    # or CO2 ventilation. Zero denotes unknown/unconfigured, never measured 0.
    "particle_cadr_m3h": (0.0, 100000.0, 1.0, "m³/h", 0.0),
    "window_open_timeout_minutes": (0.0, 30.0, 1.0, "min", 5.0),
}
QUIET_FLAGS = ("quiet_sleep", "quiet_occupied")
from .pid_calibration import METHODS as _CLASSIC_PID_CALIBRATION_METHODS, MODEL_FIELDS as PID_MODEL_FIELDS
from .pid_review import ALL_METHODS as PID_CALIBRATION_METHODS, selected_method, legacy_mode
from .pid_passive import MODES as PID_ADAPTATION_MODES
from .pid_fan_capacity import (
    CAPACITY_FIELDS as PID_FAN_CAPACITY_FIELDS,
    CAPACITY_METHODS as PID_FAN_CAPACITY_METHODS,
    CALIBRATION_DIRECTIONS as PID_FAN_DIRECTIONS,
)
from .equipment_mode_settings import (
    MODE_FIELDS, MODE_KEYS, MODE_METADATA_KEYS, PROFILE_NAMES,
    has_mode_settings, persist_changes, resolve_settings,
)
POWER_FIELDS = ("min_on_seconds", "min_off_seconds", "max_on_seconds",
                "power_switch_cooldown_seconds")
LIMIT_FIELDS = (
    "temperature_min_limit", "temperature_max_limit",
    "humidity_min_limit", "humidity_max_limit",
)
FAN_LIMIT_FIELDS = ("fan_min_percentage", "fan_max_percentage")
DEVICE_SELECTS = {"off_state_watchdog_mode": ("monitor_recover", "monitor_only", "disabled"),
                  "presence_requirement": ("always", "occupied", "absent"),
                  "sleep_behavior": ("normal", "pause", "sleep_targets"),
                  "fan_purpose": ("auto", "extraction", "filtration")}
ROOM_LIMITS_KEY = "equipment_limits"
DEFAULTS = {"control_mode": "existing", "preset": "none", "requested_mode": None,
            # Optional physical switch supplying an individual managed output.
            # 'None' preserves exact Beta54 behavior on every existing device.
            "power_switch_entity": None,
            "quiet_sleep": False, "quiet_occupied": False,
            "sleep_when_everyone_asleep": False,
            "pause_on_window_open": True,
            "announce_before_start": False,
            "native_full_output": True,
            # New native fault announcements are independently enabled by
            # default per selected controller; no synthetic error sensor.
            "announce_device_errors": True,
            # Shared across all modes; preserve legacy b22 recovery behavior.
            "off_state_watchdog_mode": "monitor_recover",
            "quiet_fan_mode": None, "profile_targets": {}, "profile_fans": {},
            "pid_calibration_method": "adaptive_suggest", "pid_last_calibration": None,
            # Observe only; never alter gains without per-device opt-in.
            "pid_adaptation_mode": "observe",
            "pid_fan_capacity_mode": "legacy",
            "pid_fan_capacity_for_mode": "choose",
            "pid_fan_capacity_models": {},
            **{key: item[4] for key, item in NUMBER_FIELDS.items()},
            **{key: 0.0 for key in PID_MODEL_FIELDS},
            **{key: 0.0 for key in PID_FAN_CAPACITY_FIELDS}}


@dataclass(frozen=True, slots=True)
class Capabilities:
    """One controller can combine native HVAC and a same-device fan endpoint."""

    primary: str
    domain: str
    modes: tuple[str, ...]
    temperature: bool = False
    temperature_range: bool = False
    humidity: bool = False
    fan_entity: str | None = None
    fan_modes: tuple[str, ...] = ()
    fan_percentage: bool = False
    swing_modes: tuple[str, ...] = ()
    swing_horizontal_modes: tuple[str, ...] = ()
    humidifying: bool = False
    min_temp: float = 5.0
    max_temp: float = 35.0
    temp_step: float = 0.5
    min_humidity: float = 20.0
    max_humidity: float = 80.0
    # Control of the environmental metric is distinct from a native setpoint
    # service.  For example DRY can lower humidity without SET_HUMIDITY.
    native_temperature_target: bool = False
    native_humidity_target: bool = False


def room_config(manager: Any, spec: ManagedDevice) -> dict:
    rooms = manager.settings.get("climate_rooms", {})
    value = rooms.get(spec.area_id, {}) if isinstance(rooms, dict) else {}
    return value if isinstance(value, dict) else {}


def device_config(manager: Any, spec: ManagedDevice, entity: str | None = None) -> dict:
    room = room_config(manager, spec)
    profiles = room.get("device_settings", {})
    profile = profiles.get(entity, {}) if isinstance(profiles, dict) else {}
    return profile if isinstance(profile, dict) else {}


def raw_settings(manager: Any, spec: ManagedDevice) -> dict:
    """Copy of persisted physical settings, including every operating profile."""
    profiles = manager.settings.get(SETTINGS, {})
    raw = profiles.get(spec.identifier, {}) if isinstance(profiles, dict) else {}
    return deepcopy(raw) if isinstance(raw, dict) else {}


def base_settings(manager: Any, spec: ManagedDevice) -> dict:
    """Legacy effective defaults, without transient or inactive mode metadata."""
    raw = raw_settings(manager, spec)
    result = {**deepcopy(DEFAULTS), **{
        key: value for key, value in raw.items()
        if key not in MODE_METADATA_KEYS and key not in (
            "operating_mode", "timed_setpoint_sequence")
    }}
    # Missing settings and legacy strings/numbers never opt a device in.
    # Old installations keep recovery; invalid persisted settings fail closed.
    watchdog_mode = raw.get("off_state_watchdog_mode", "monitor_recover")
    result["off_state_watchdog_mode"] = (
        watchdog_mode if watchdog_mode in DEVICE_SELECTS["off_state_watchdog_mode"]
        else "disabled"
    )
    result["native_full_output"] = raw.get("native_full_output", True) is True
    result["sleep_when_everyone_asleep"] = raw.get("sleep_when_everyone_asleep") is True
    result["announce_before_start"] = raw.get("announce_before_start") is True
    wait = raw.get("window_open_timeout_minutes", 5.0)
    result["window_open_timeout_minutes"] = (
        finite(wait, 0, 30) if not isinstance(wait, bool) else None
    )
    if result["window_open_timeout_minutes"] is None:
        result["window_open_timeout_minutes"] = 5.0
    # Beta84 resolves the previous overlapping passive/calculator selectors
    # into exactly one persisted gain authority. Legacy settings are read
    # conservatively: an explicit classical tune always wins.
    result["pid_calibration_method"] = selected_method(raw)
    result["pid_adaptation_mode"] = legacy_mode(result["pid_calibration_method"])
    # Keep previous commissioning values when these controls first appear.
    primary = next((e for e in spec.source_entities if not e.startswith("fan.")), spec.source_entities[0])
    dev = device_config(manager, spec, primary)
    for key, fallback in (("presence_requirement", "always"), ("sleep_behavior", "normal"),
                          ("fan_purpose", "auto"), ("sensor_verified", False)):
        result.setdefault(key, dev.get(key, fallback))
    # Beta17 exposes one strict room-state selector per managed controller.
    # Old "room" means occupied; old "home" is narrowed to occupied rather
    # than broadening an existing installation's physical-control window.
    if result.get("presence_requirement") in ("room", "home"):
        result["presence_requirement"] = "occupied"
    elif result.get("presence_requirement") not in DEVICE_SELECTS["presence_requirement"]:
        result["presence_requirement"] = "always"
    for key, legacy in zip(POWER_FIELDS, ("min_on_s", "min_off_s", "max_on_s")):
        if key not in raw and legacy in dev:
            result[key] = dev[legacy]
    if "kp" not in raw and all(e.startswith("fan.") for e in spec.source_entities):
        result["kp"], result["ki"] = 0.05, 0.001
    return result


def settings_for_mode(manager: Any, spec: ManagedDevice, mode: str) -> dict:
    """Resolve a genuine operating profile without selecting or activating it."""
    descriptor = mode_descriptor(manager, spec, mode)
    if descriptor is None:
        raise ValueError("unsupported_operating_mode")
    result = resolve_settings(base_settings(manager, spec), raw_settings(manager, spec), mode,
                              native_mode=descriptor["native_mode"],
                              target_keys=descriptor["target_keys"])
    if result.get("control_mode") not in descriptor["control_modes"]:
        # A shared legacy PID choice is not permission to invent PID for a
        # native AUTO/HEAT_COOL policy. Keep persisted bytes for its genuine
        # directional modes, while this unsupported effective profile yields
        # ownership to Existing until a supported method is selected.
        result["control_mode"] = "existing"
        result["control_mode_reason"] = "unsupported_for_operating_mode"
    # Preserve the single calibration authority when a mode overrides only the
    # current selector; never revive an obsolete passive-selector preference.
    raw = raw_settings(manager, spec)
    scoped = raw.get("mode_settings", {}).get(mode, {}) if has_mode_settings(raw) else {}
    explicit_method = scoped.get("pid_calibration_method") if isinstance(scoped, dict) else None
    result["pid_calibration_method"] = (explicit_method if explicit_method in PID_CALIBRATION_METHODS
                                        else selected_method(result))
    result["pid_adaptation_mode"] = legacy_mode(result["pid_calibration_method"])
    return result


def settings(manager: Any, spec: ManagedDevice) -> dict:
    """The one active actuator profile; reading old installations stays inert.

    The runtime hook must read base_settings rather than this function.  It
    owns logical direction selection independently from a transient native
    OFF state.  Before that direction is resolved, legacy settings let the
    ordinary demand planner choose it without an invented physical mode.
    """
    raw = raw_settings(manager, spec)
    if has_mode_settings(raw):
        choose = getattr(getattr(manager, "equipment", None), "active_control_mode", None)
        mode = choose(spec) if callable(choose) else None
        if mode in operating_modes(manager, spec):
            result = settings_for_mode(manager, spec, mode)
            if raw.get("requested_mode") == "off":
                result["requested_mode"] = "off"
            return result
    return base_settings(manager, spec)


def window_alternative_supported(manager: Any, spec: ManagedDevice,
                                 cap: Capabilities | None = None) -> bool:
    """Offer an airing preference only on indoor remediation equipment.

    This is capability discovery, never authority to operate equipment. An
    extractor replaces room air and is not an alternative to opening windows.
    Existing verified capabilities keep configuration visible while offline.
    """
    cap = cap if cap is not None else capabilities(manager, spec)
    if cap is None:
        record = getattr(getattr(manager, "equipment", None), "records", {}).get(
            spec.identifier, {})
        if (record.get("area") == spec.area_id
                and record.get("source_device_id") == spec.source_device_id
                and tuple(record.get("sources", ())) == spec.source_entities):
            try:
                saved = Capabilities(**record["capabilities"])
                if saved.primary in spec.source_entities:
                    cap = saved
            except (KeyError, TypeError, ValueError):
                pass
    if cap is None:
        return False
    modes = set(cap.modes)
    if cap.domain == "humidifier" or modes & {"heat", "cool", "heat_cool", "auto", "dry"}:
        return True
    if cap.domain == "fan" or modes == {"off", "fan_only"}:
        cfg = settings(manager, spec)
        role = cfg.get("fan_purpose")
        if role not in ("extraction", "filtration"):
            role = device_config(manager, spec, cap.primary).get("fan_purpose")
        if role not in ("extraction", "filtration"):
            room = room_config(manager, spec)
            if room.get("extraction_fan_entity") == cap.primary:
                role = "extraction"
            elif room.get("purifier_fan_entity") == cap.primary:
                role = "filtration"
        if role not in ("extraction", "filtration"):
            from .room_sources import selected
            sources = selected(manager.settings, spec.area_id, "air_quality")
            metrics = set()
            if sources:
                from .discovery import supported_metric
                metrics = {supported_metric(manager.hass, state, outdoor=False)
                           for entity in sources
                           if (state := manager.hass.states.get(entity)) is not None}
            if ("co2" in metrics) != ("pm25" in metrics):
                role = "extraction" if "co2" in metrics else "filtration"
        return role == "filtration"
    return False


@dataclass(frozen=True, slots=True)
class ManagedEndpoint(ManagedDevice):
    """Independent native channels share ONE physical controller child device."""
    physical_identifier: str


def device_identifier(spec: ManagedDevice) -> str:
    return getattr(spec, "physical_identifier", spec.identifier)


def specs(manager: Any) -> tuple[ManagedDevice, ...]:
    result = []
    for item in getattr(manager, "_device_hierarchy", {}).get("controllers", {}).values():
        physical = item["spec"]
        primary = [e for e in physical.source_entities if not e.startswith("fan.")]
        fans = [e for e in physical.source_entities if e.startswith("fan.")]
        if len(primary) <= 1 and len(fans) <= 1:
            result.append(physical)  # A native climate plus its accessory fan.
            continue
        # Never suppress a second independently controlled endpoint merely
        # because it belongs to the same HA physical device (e.g. a dual valve).
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(manager.hass)
        for entity in physical.source_entities:
            native = registry.async_get(entity)
            identity = getattr(native, "id", None) or entity
            suffix = hashlib.sha256(identity.encode()).hexdigest()[:16]
            observed = manager.hass.states.get(entity)
            name = getattr(observed, "name", None) or entity
            result.append(ManagedEndpoint(physical.identifier + "_channel_" + suffix,
                physical.area_id, name, physical.source_device_id, (entity,), physical.identifier))
    return tuple(result)


def _strings(value: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in value if isinstance(v, str) and v)) if isinstance(value, (tuple, list)) else ()


def features(state: Any) -> int:
    try:
        return int(state.attributes.get("supported_features", 0))
    except (TypeError, ValueError, OverflowError, AttributeError):
        return 0


def capabilities(manager: Any, spec: ManagedDevice) -> Capabilities | None:
    """Use a real configured primary endpoint; never combine opposing HVAC units.

    Multiple endpoints are grouped in one HA device, but the primary endpoint
    is stable and the complete source list remains visible in attributes. A
    dedicated fan endpoint may augment native HVAC fan control.
    """
    candidates = tuple(e for e in spec.source_entities if e in configured_sources(
        manager.settings, spec.area_id))
    if not candidates:
        return None
    primary = min(candidates, key=lambda e: (
        {"climate": 0, "humidifier": 1, "fan": 2, "switch": 3,
         "input_boolean": 3, "number": 4, "input_number": 4}.get(e.partition(".")[0], 9), e))
    state = manager.hass.states.get(primary)
    if state is None:
        return None
    domain = primary.partition(".")[0]
    attrs, supported = state.attributes, features(state)
    room = room_config(manager, spec)
    modes: tuple[str, ...] = ()
    if domain == "climate":
        modes = tuple(v for v in _strings(attrs.get("hvac_modes")) if v in HVAC_MODES)
    elif domain == "humidifier":
        if attrs.get("device_class") == "dehumidifier":
            modes = ("off", "dry")
        elif attrs.get("device_class") == "humidifier":
            modes = ("off", "auto")  # AUTO means this humidity controller's policy.
    elif domain == "fan":
        modes = ("off", "fan_only")
    elif domain in ("switch", "input_boolean", "number", "input_number"):
        role = "heat" if room.get("heat_actuator") == primary else (
            "cool" if room.get("cool_actuator") == primary else None)
        if role:
            modes = ("off", role)
    if not modes:
        return None
    fan_entity, fan_modes, percentage = None, (), False
    if domain == "climate" and supported & FAN:
        fan_entity, fan_modes = primary, _strings(attrs.get("fan_modes"))
    if not fan_modes:
        for entity in candidates:
            fan = manager.hass.states.get(entity)
            if entity.startswith("fan.") and fan is not None:
                if features(fan) & 1:
                    # percentages are real HA SET_SPEED values, not guessed labels.
                    step = finite(fan.attributes.get("percentage_step", 1), 1, 100) or 1
                    count = max(1, round(100 / step))
                    fan_modes = tuple(str(round(100 * i / count)) for i in range(1, count + 1))
                    fan_entity, percentage = entity, True
                    break
                presets = _strings(fan.attributes.get("preset_modes"))
                if features(fan) & 8 and presets:
                    fan_entity, fan_modes = entity, presets
                    break
    unit = attrs.get("temperature_unit", "°C")
    lo = target_from_unit(attrs.get("min_temp", 5 if unit == "°C" else 41), unit)
    hi = target_from_unit(attrs.get("max_temp", 35 if unit == "°C" else 95), unit)
    if lo is None or hi is None or lo >= hi:
        lo, hi = 5.0, 35.0
    temp_step = finite(attrs.get("target_temp_step", .5), .1, 10) or .5
    if unit in ("°F", "F"):
        temp_step *= 5 / 9
    direct = domain in ("switch", "input_boolean", "number", "input_number")
    # A native DRY/FAN-only appliance may publish a generic temperature feature
    # bit without supporting any thermal setpoint. Never expose a target for it.
    thermal_mode = bool(set(modes) & {"heat", "cool", "heat_cool", "auto"})
    return Capabilities(
        primary, domain, modes,
        temperature=direct or (domain == "climate" and thermal_mode and (
            bool(supported & TEMP) or not (supported & RANGE) and bool(set(modes) & {"heat", "cool"}))),
        temperature_range=domain == "climate" and thermal_mode and bool(supported & RANGE),
        humidity=domain == "humidifier" or (domain == "climate" and (
            bool(supported & HUMIDITY) or "dry" in modes)),
        fan_entity=fan_entity, fan_modes=fan_modes, fan_percentage=percentage,
        swing_modes=_strings(attrs.get("swing_modes")) if domain == "climate" and supported & SWING else (),
        swing_horizontal_modes=_strings(attrs.get("swing_horizontal_modes")) if domain == "climate" and supported & SWING_H else (),
        humidifying=domain == "humidifier" and attrs.get("device_class") == "humidifier",
        min_temp=lo, max_temp=hi, temp_step=temp_step,
        min_humidity=finite(attrs.get("min_humidity", 20), 0, 100) or 20,
        max_humidity=finite(attrs.get("max_humidity", 80), 1, 100) or 80,
        native_temperature_target=domain == "climate" and thermal_mode and bool(supported & TEMP),
        native_humidity_target=domain == "humidifier" or domain == "climate" and bool(supported & HUMIDITY),
    )


def mode_capabilities(manager: Any, spec: ManagedDevice) -> Capabilities | None:
    """Live or exact-identity cached capabilities for configuration UI only.

    Runtime actuation continues to require capabilities() and live readiness.
    A withdrawn live capability or a changed source/room/device never inherits
    stale controls from a previous physical endpoint.
    """
    cap = capabilities(manager, spec)
    live = sources_available(manager, spec)
    if cap is not None and live:
        return cap
    configured = set(configured_sources(manager.settings, spec.area_id))
    if (not spec.source_entities or not set(spec.source_entities) <= configured
            or live):
        return None
    record = getattr(getattr(manager, "equipment", None), "records", {}).get(spec.identifier, {})
    if not isinstance(record, dict) or not (
            record.get("area") == spec.area_id
            and record.get("source_device_id") == spec.source_device_id
            and tuple(record.get("sources", ())) == spec.source_entities):
        return None
    from .device_activation import authority_context, authorization_matches
    authorities = tuple(saved for saved in (
            record.get("capabilities_authority"),
            raw_settings(manager, spec).get("_native_authorization"))
        if isinstance(saved, dict) and isinstance(saved.get("sources"), list)
        and saved["sources"])
    if not authorities:
        return None
    try:
        current_identity = authority_context(manager, spec)
    except (AttributeError, ImportError, KeyError, TypeError, ValueError):
        # Registry restoration is not proof of physical identity. Keep the
        # editor absent until the selected endpoint can be verified again.
        return None
    if not any(authorization_matches(saved, current_identity) for saved in authorities):
        return None
    if cap is not None:
        return cap
    try:
        saved = Capabilities(**record["capabilities"])
        if (saved.primary not in spec.source_entities
                or saved.domain != saved.primary.partition(".")[0]
                or saved.fan_entity is not None and saved.fan_entity not in spec.source_entities
                or not isinstance(saved.modes, (tuple, list))
                or not saved.modes or not set(saved.modes) <= HVAC_MODES):
            return None
        return saved
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def operating_modes(manager: Any, spec: ManagedDevice) -> tuple[str, ...]:
    """One configuration panel per genuinely supported environmental mode."""
    cap = mode_capabilities(manager, spec)
    if cap is None:
        return ()
    if cap.domain == "humidifier":
        return ("humidify",) if cap.humidifying else ("dry",)
    return tuple(mode for mode in MODE_KEYS if mode != "humidify" and mode in cap.modes)


def mode_descriptor(manager: Any, spec: ManagedDevice, mode: str) -> dict | None:
    """Parameter eligibility and physical mapping, without actuation authority."""
    cap = mode_capabilities(manager, spec)
    if cap is None:
        return None
    supported = (("humidify",) if cap.humidifying else ("dry",)) if cap.domain == "humidifier" else tuple(
        key for key in MODE_KEYS if key != "humidify" and key in cap.modes)
    if mode not in supported:
        return None
    native_mode = "auto" if mode == "humidify" else mode
    thermal = mode in ("heat", "cool", "auto", "heat_cool")
    humidity = mode in ("dry", "humidify")
    target_keys = ((mode,) if mode in ("heat", "cool") else
                   ("heat", "cool") if thermal else ("humidity",) if humidity else ())
    pid = (mode in ("heat", "cool") and (cap.temperature or cap.temperature_range)
           or humidity or mode == "fan_only")
    control = ("existing", "automatic", "manual", "off") + (("pid",) if pid else ())
    numbers = ["kp", "ki", "kd", "sample_seconds", "cycle_seconds", *PID_MODEL_FIELDS] if pid else []
    selects = ["control_mode", "preset"]
    switches = []
    if pid:
        selects.append("pid_calibration_method")
    if cap.fan_modes:
        selects.append("fan_mode")
        switches.extend(QUIET_FLAGS)
        if cap.fan_percentage:
            numbers.append("quiet_percentage")
        else:
            selects.append("quiet_fan_mode")
        if (pid and cap.domain in ("climate", "humidifier")
                and native_mode in PID_FAN_DIRECTIONS):
            from .pid_fan_capacity import ordered_fan_stages, PERCENT_POINT_FIELDS, STAGE_FIELDS
            stages = ordered_fan_stages(cap.fan_modes)
            if cap.fan_percentage:
                numbers.extend(key for pair in PERCENT_POINT_FIELDS for key in pair)
                selects.append("pid_fan_capacity_mode")
            elif 2 <= len(stages) <= 5:
                numbers.extend(STAGE_FIELDS[:len(stages)-1])
                selects.append("pid_fan_capacity_mode")
    if cap.swing_modes:
        selects.append("swing_mode")
    if cap.swing_horizontal_modes:
        selects.append("swing_horizontal_mode")
    return {
        "key": mode, "native_mode": native_mode,
        "metric": "temperature" if thermal else "humidity" if humidity else "air_quality",
        "increasing": True if mode in ("heat", "humidify") else
                      False if mode in ("cool", "dry", "fan_only") else None,
        "temperature": thermal, "humidity": humidity, "target_keys": target_keys,
        "native_target": bool(cap.native_temperature_target or
                              mode in ("auto", "heat_cool") and cap.temperature_range) if thermal
                         else bool(cap.native_humidity_target) if humidity else False,
        "pid_supported": bool(pid), "control_modes": control,
        "fan": bool(cap.fan_modes), "fan_modes": tuple(cap.fan_modes),
        "fan_percentage": cap.fan_percentage,
        "swing": bool(cap.swing_modes), "swing_horizontal": bool(cap.swing_horizontal_modes),
        "number_fields": tuple(numbers), "select_fields": tuple(selects),
        "switch_fields": tuple(switches),
    }


def mode_control_modes(manager: Any, spec: ManagedDevice, mode: str) -> tuple[str, ...]:
    descriptor = mode_descriptor(manager, spec, mode)
    return descriptor["control_modes"] if descriptor is not None else ()


def sources_available(manager: Any, spec: ManagedDevice) -> bool:
    """Pure readiness gate: no policy, target, PID or environmental calculation."""
    configured = set(configured_sources(manager.settings, spec.area_id))
    sources = [entity for entity in spec.source_entities if entity in configured]
    if not sources:
        return False
    return all((state := manager.hass.states.get(entity)) is not None
               and state.state not in ("unknown", "unavailable")
               for entity in sources)


def _fan_bounds(cap: Capabilities) -> tuple[float, float, float]:
    values = sorted({float(value) for value in cap.fan_modes
                     if cap.fan_percentage and finite(value, 0, 100) is not None})
    if not values:
        return 1.0, 100.0, 1.0
    step = min((b-a for a,b in zip(values, values[1:]) if b > a), default=1.0)
    return values[0], values[-1], step


def room_limit_bounds(manager: Any, area: str, key: str) -> tuple[float, float, float, str | None] | None:
    """Common safe editable range from the selected physical devices in one room."""
    caps = [cap for spec in specs(manager) if spec.area_id == area
            if (cap := capabilities(manager, spec)) is not None]
    if key in ("temperature_min_limit", "temperature_max_limit"):
        relevant = [cap for cap in caps if cap.temperature or cap.temperature_range]
        if not relevant:
            return None
        low = max(cap.min_temp for cap in relevant)
        high = min(cap.max_temp for cap in relevant)
        if high <= low:
            return None
        step = min(max(cap.temp_step, 0.1) for cap in relevant)
        return float(low), float(high), float(step), "°C"
    if key in ("humidity_min_limit", "humidity_max_limit"):
        relevant = [cap for cap in caps if cap.humidity]
        if not relevant:
            return None
        low = max(cap.min_humidity for cap in relevant)
        high = min(cap.max_humidity for cap in relevant)
        if high <= low:
            return None
        return float(low), float(high), 1.0, "%"
    if key in ("fan_min_percentage", "fan_max_percentage"):
        relevant = [_fan_bounds(cap) for cap in caps if cap.fan_percentage]
        if not relevant:
            return None
        low = max(item[0] for item in relevant)
        high = min(item[1] for item in relevant)
        if high < low:
            return None
        return float(low), float(high), 1.0, "%"
    return None


# Only temporary SETTINGS-editor bounds. Device actuation always uses the
# observed, capability-intersected room_limit_bounds() above, never these.
_OFFLINE_ROOM_LIMIT_BOUNDS = {
    "temperature_min_limit": (5.0, 35.0, 0.5, "°C"),
    "temperature_max_limit": (5.0, 35.0, 0.5, "°C"),
    "humidity_min_limit": (20.0, 80.0, 1.0, "%"),
    "humidity_max_limit": (20.0, 80.0, 1.0, "%"),
    "fan_min_percentage": (1.0, 100.0, 1.0, "%"),
    "fan_max_percentage": (1.0, 100.0, 1.0, "%"),
}


def room_limit_edit_bounds(
    manager: Any, area: str, key: str
) -> tuple[float, float, float, str | None] | None:
    """Retain verified room settings while their selected native source restores.

    Never advertise an uncommissioned control for a room without a selected
    physical controller. Only a *previously registered* limit or explicitly
    saved limit can use temporary UI bounds, and only while at least one
    selected native controller has not restored its capabilities. This is NOT
    evidence of a usable actuator or of supported physical setpoints.
    """
    current = room_limit_bounds(manager, area, key)
    if current is not None:
        return current
    if key not in _OFFLINE_ROOM_LIMIT_BOUNDS:
        return None
    selected = tuple(spec for spec in specs(manager) if spec.area_id == area)
    if not selected or all(capabilities(manager, spec) is not None for spec in selected):
        return None
    rooms = manager.settings.get("environment_rooms", {})
    room = rooms.get(area, {}) if isinstance(rooms, dict) else {}
    stored = room.get(ROOM_LIMITS_KEY, {}) if isinstance(room, dict) else {}
    saved = isinstance(stored, dict) and key in stored
    if not saved:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(manager.hass)
        lookup = getattr(registry, "async_get_entity_id", None)
        entry_id = manager.entry.entry_id
        unique_id = f"{entry_id}_area_{area}_room_equipment_limit_{key}"
        saved = bool(lookup and lookup("number", DOMAIN, unique_id))
    return _OFFLINE_ROOM_LIMIT_BOUNDS[key] if saved else None


def available_room_limit_fields(manager: Any, area: str) -> tuple[str, ...]:
    return tuple(key for key in LIMIT_FIELDS
                 if room_limit_edit_bounds(manager, area, key) is not None)


def fan_limit_capability(manager: Any, spec: ManagedDevice) -> Capabilities | None:
    """Configuration-only capability, retaining an exact offline fan's bounds.

    Saved capabilities never qualify an actuator write. The runtime still
    reads live capabilities and availability before changing a native fan.
    """
    cap = capabilities(manager, spec)
    if cap is not None and cap.fan_percentage:
        return cap
    if sources_available(manager, spec):
        return None
    record = getattr(getattr(manager, "equipment", None), "records", {}).get(spec.identifier, {})
    if (record.get("area") == spec.area_id
            and record.get("source_device_id") == spec.source_device_id
            and tuple(record.get("sources", ())) == spec.source_entities):
        try:
            saved = Capabilities(**record["capabilities"])
            if (saved.fan_percentage and saved.primary in spec.source_entities
                    and saved.fan_entity in spec.source_entities):
                return saved
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    return None


def fan_limit_edit_bounds(manager: Any, spec: ManagedDevice) -> tuple[float, float, float, str]:
    """Speed limits may lie between native steps; output uses an allowed step."""
    cap = fan_limit_capability(manager, spec)
    low, high, _ = _fan_bounds(cap) if cap is not None else (1.0, 100.0, 1.0)
    return low, high, 1.0, "%"


def device_fan_limits(manager: Any, spec: ManagedDevice,
                      cap: Capabilities | None = None) -> dict[str, float]:
    """Independent limits, with the old effective room range until configured.

    The new pair lives separately from Beta17's retired per-device keys.
    Unedited controllers retain the Beta18–111 room policy, including its
    conservative migration fallback. Editing one controller cannot change
    any sibling's inherited range.
    """
    profiles = manager.settings.get(SETTINGS, {})
    raw = profiles.get(spec.identifier, {}) if isinstance(profiles, dict) else {}
    explicit = raw.get("fan_speed_limits") if isinstance(raw, dict) else None
    explicit = explicit if isinstance(explicit, dict) else {}
    values = {key: finite(explicit.get(key), 1, 100) for key in FAN_LIMIT_FIELDS}
    if (any(value is None for value in values.values())
            or values[FAN_LIMIT_FIELDS[0]] > values[FAN_LIMIT_FIELDS[1]]):
        rooms = manager.settings.get("environment_rooms", {})
        env = rooms.get(spec.area_id, {}) if isinstance(rooms, dict) else {}
        saved = env.get(ROOM_LIMITS_KEY, {}) if isinstance(env, dict) else {}
        saved = saved if isinstance(saved, dict) else {}
        # Retain the former common range only as a compatibility fallback.
        # With no saved legacy limit, each fan uses its own native bounds.
        legacy_present = any(key in saved for key in FAN_LIMIT_FIELDS)
        if not legacy_present and isinstance(profiles, dict):
            legacy_present = any(
                isinstance(profile, dict) and any(key in profile for key in FAN_LIMIT_FIELDS)
                for item in specs(manager) if item.area_id == spec.area_id
                for profile in (profiles.get(item.identifier, {}),)
            )
        bounds = (room_limit_bounds(manager, spec.area_id, FAN_LIMIT_FIELDS[0])
                  if legacy_present else None)
        fallback = bounds or (1.0, 100.0, 1.0, "%")
        values = {}
        for key in FAN_LIMIT_FIELDS:
            value = finite(saved.get(key), fallback[0], fallback[1])
            if value is None:
                value = _legacy_room_limit(manager, spec.area_id, key, fallback)
            values[key] = float(value if value is not None else
                                fallback[0] if "_min_" in key else fallback[1])
        if values[FAN_LIMIT_FIELDS[0]] > values[FAN_LIMIT_FIELDS[1]]:
            values = dict(zip(FAN_LIMIT_FIELDS, fallback[:2]))
    if cap is not None and cap.fan_percentage:
        low, high, _ = _fan_bounds(cap)
        # An incompatible newly reported native range stays empty. Never
        # increase a configured maximum merely to force a usable speed.
        values[FAN_LIMIT_FIELDS[0]] = max(low, values[FAN_LIMIT_FIELDS[0]])
        values[FAN_LIMIT_FIELDS[1]] = min(high, values[FAN_LIMIT_FIELDS[1]])
    return {key: float(value) for key, value in values.items()}


def _legacy_room_limit(manager: Any, area: str, key: str, bounds: tuple[float, float, float, str | None]) -> float | None:
    """Conservatively merge beta17 per-device limits into one room value."""
    profiles = manager.settings.get(SETTINGS, {})
    if not isinstance(profiles, dict):
        return None
    values = []
    for spec in specs(manager):
        if spec.area_id != area:
            continue
        raw = profiles.get(spec.identifier, {})
        value = raw.get(key) if isinstance(raw, dict) else None
        parsed = finite(value, bounds[0], bounds[1]) if value is not None else None
        if parsed is not None:
            values.append(float(parsed))
    if not values:
        return None
    return max(values) if "_min_" in key else min(values)


def room_limit_values(manager: Any, area: str) -> dict[str, float]:
    """Room Environment limits, with conservative beta17 migration fallback."""
    env_rooms = manager.settings.get("environment_rooms", {})
    env = env_rooms.get(area, {}) if isinstance(env_rooms, dict) else {}
    saved = env.get(ROOM_LIMITS_KEY, {}) if isinstance(env, dict) else {}
    saved = saved if isinstance(saved, dict) else {}
    result: dict[str, float] = {}
    for key in LIMIT_FIELDS:
        bounds = room_limit_bounds(manager, area, key)
        if bounds is None:
            continue
        default = bounds[0] if "_min_" in key else bounds[1]
        raw = saved.get(key)
        parsed = finite(raw, bounds[0], bounds[1]) if raw is not None else None
        if parsed is None:
            parsed = _legacy_room_limit(manager, area, key, bounds)
        result[key] = float(default if parsed is None else parsed)
    for low_key, high_key in (
        ("temperature_min_limit", "temperature_max_limit"),
        ("humidity_min_limit", "humidity_max_limit"),
        ("fan_min_percentage", "fan_max_percentage"),
    ):
        if low_key in result and high_key in result and result[low_key] > result[high_key]:
            low_bounds = room_limit_bounds(manager, area, low_key)
            high_bounds = room_limit_bounds(manager, area, high_key)
            result[low_key] = float(low_bounds[0])
            result[high_key] = float(high_bounds[1])
    return result


def room_limit_display_values(manager: Any, area: str) -> dict[str, float]:
    """Number UI values survive offline equipment, without authorizing writes.

    The runtime room_limit_values() above stays strictly capability-driven.
    Offline values are provisional configuration only, replaced by native
    intersections as soon as their physical sources become available again.
    """
    result = room_limit_values(manager, area)
    rooms = manager.settings.get("environment_rooms", {})
    room = rooms.get(area, {}) if isinstance(rooms, dict) else {}
    saved = room.get(ROOM_LIMITS_KEY, {}) if isinstance(room, dict) else {}
    saved = saved if isinstance(saved, dict) else {}
    for key in LIMIT_FIELDS:
        if key in result:
            continue
        bounds = room_limit_edit_bounds(manager, area, key)
        if bounds is None:
            continue
        default = bounds[0] if "_min_" in key else bounds[1]
        raw = saved.get(key)
        value = finite(raw, bounds[0], bounds[1]) if raw is not None else None
        if value is None:
            value = _legacy_room_limit(manager, area, key, bounds)
        result[key] = float(default if value is None else value)
    for low_key, high_key in (
        ("temperature_min_limit", "temperature_max_limit"),
        ("humidity_min_limit", "humidity_max_limit"),
        ("fan_min_percentage", "fan_max_percentage"),
    ):
        if low_key in result and high_key in result and result[low_key] > result[high_key]:
            lo = room_limit_edit_bounds(manager, area, low_key)
            hi = room_limit_edit_bounds(manager, area, high_key)
            if lo is not None and hi is not None:
                result[low_key], result[high_key] = float(lo[0]), float(hi[1])
    return result


def device_limits(manager: Any, spec: ManagedDevice, cap: Capabilities) -> dict[str, float]:
    """Room temperature/RH bounds and this device's independent fan limits."""
    room = room_limit_values(manager, spec.area_id)
    return {
        "temperature_min_limit": max(cap.min_temp, room.get("temperature_min_limit", cap.min_temp)),
        "temperature_max_limit": min(cap.max_temp, room.get("temperature_max_limit", cap.max_temp)),
        "humidity_min_limit": max(cap.min_humidity, room.get("humidity_min_limit", cap.min_humidity)),
        "humidity_max_limit": min(cap.max_humidity, room.get("humidity_max_limit", cap.max_humidity)),
        **device_fan_limits(manager, spec, cap),
    }


def number_bounds(cap: Capabilities, key: str) -> tuple[float, float, float, str | None]:
    """Per-controller numeric bounds for algorithm/quiet settings only."""
    if key in NUMBER_FIELDS:
        return NUMBER_FIELDS[key][:4]
    if key in ("fan_min_percentage", "fan_max_percentage"):
        low, high, step = _fan_bounds(cap)
        return low, high, step, "%"
    raise KeyError(key)


def applicable_limit_fields(cap: Capabilities) -> tuple[str, ...]:
    """Physical limit classification; only temperature/RH remain room-owned."""
    result = []
    if cap.temperature or cap.temperature_range:
        result.extend(("temperature_min_limit", "temperature_max_limit"))
    if cap.humidity:
        result.extend(("humidity_min_limit", "humidity_max_limit"))
    if cap.fan_percentage:
        result.extend(("fan_min_percentage", "fan_max_percentage"))
    return tuple(result)


def permission(manager: Any, spec: ManagedDevice, cap: Capabilities) -> tuple[bool, bool]:
    """Independent grants for ongoing setpoint/speed and power/mode changes."""
    room = room_config(manager, spec)
    device = device_config(manager, spec, cap.primary)
    enabled = room.get("enabled") is True and room.get("allow_actuation") is True
    cfg = settings(manager, spec)
    if "_native_authorization" in cfg:
        from .device_activation import authorized
        valid = cap.domain in ("climate", "fan", "humidifier") and authorized(manager, spec)
        # Automatic/PID/Manual is the explicit permission for this exact native
        # controller. There is no second power/HVAC-mode switch.
        active = cfg.get("control_mode") in ("automatic", "pid", "manual", "off")
        return valid and active, valid and active and "off" in cap.modes
    if device:
        enabled = enabled and device.get("auto_control") is True
        power = enabled and device.get("hardware_confirmed") is True and device.get("method") in ("power", "native")
        return enabled, power
    if cap.domain == "climate":
        pid = manager.settings.get("pid_rooms", {}).get(spec.area_id, {})
        supervisor = pid.get("enabled") is True and cap.primary in pid.get("climate_entities", [])
        # Prior room native mode consent is not generic compressor-cycle consent.
        return enabled or supervisor, False
    if cap.domain == "humidifier":
        return (enabled and (room.get("humidity_setpoint_auto") is True or room.get("humidity_power_auto") is True),
                enabled and room.get("humidity_power_auto") is True and room.get("humidity_power_hardware_confirmed") is True)
    if cap.domain == "fan":
        return (enabled and (room.get("fan_speed_auto") is True or room.get("fan_power_auto") is True),
                enabled and room.get("fan_power_auto") is True and room.get("fan_power_hardware_confirmed") is True)
    direct = enabled and room.get("direct_hardware_confirmed") is True
    return direct, direct


def normalize_native_timing(
    manager: Any, spec: ManagedDevice, cap: Capabilities, config: dict,
) -> dict:
    """Separate operating holds on the first explicit minimum-time edit.

    Reading/upgrading an existing controller does not change its settings or
    pending command context. The editor calls this before overlaying the user's
    requested value, preserving the other effective native minimum and maximum.
    A selected external supply keeps the limits it used before this edit; a
    shorter valve operating hold is not permission to cycle its power supply.
    """
    normalized = deepcopy(config)
    version = config.get("_native_timing_version")
    if version is not None:
        if type(version) is not int or version != 1:
            raise ValueError("unsupported_native_timing_version")
        return normalized
    native_on, native_off, maximum = _legacy_timing(manager, spec, cap)
    supply_on, supply_off, _ = _legacy_timing(
        manager, spec, cap, config=config,
    )
    normalized.update({
        "_native_timing_version": 1,
        "min_on_seconds": native_on,
        "min_off_seconds": native_off,
        "max_on_seconds": maximum,
        "_power_switch_min_on_seconds": supply_on,
        "_power_switch_min_off_seconds": supply_off,
    })
    return normalized


def timing(manager: Any, spec: ManagedDevice, cap: Capabilities, config: dict | None = None) -> tuple[float, float, float]:
    """Native operating holds; zero explicitly disables that particular hold."""
    cfg = config if config is not None else settings(manager, spec)
    version = cfg.get("_native_timing_version")
    if version is None:
        return _legacy_timing(manager, spec, cap, config=config)
    if type(version) is not int or version != 1:
        raise ValueError("unsupported_native_timing_version")
    values = []
    for key in ("min_on_seconds", "min_off_seconds", "max_on_seconds"):
        bounds = NUMBER_FIELDS[key]
        value = finite(cfg.get(key), bounds[0], bounds[1])
        if value is None:
            raise ValueError("invalid_native_operating_timing")
        values.append(value)
    if values[2] <= values[0]:
        raise ValueError("maximum_runtime_must_exceed_minimum_on")
    return tuple(values)


def _legacy_timing(manager: Any, spec: ManagedDevice, cap: Capabilities, config: dict | None = None) -> tuple[float, float, float]:
    """Preserve commissioned timing until the user edits an operating hold."""
    room, dev = room_config(manager, spec), device_config(manager, spec, cap.primary)
    prefix = "fan_power_" if cap.domain == "fan" else "humidity_power_" if cap.domain == "humidifier" else ""
    minimum = 120 if cap.domain == "fan" else 600
    values = []
    cfg = config if config is not None else settings(manager, spec)
    raw_saved = manager.settings.get(SETTINGS, {}).get(spec.identifier, {})
    for key, new_key, fallback in (("min_on_s", "min_on_seconds", 600),
                                   ("min_off_s", "min_off_seconds", 600),
                                   ("max_on_s", "max_on_seconds", 7200)):
        raw = dev.get(key, room.get(prefix + key, fallback))
        if config is not None or new_key in raw_saved:
            proposed = cfg[new_key]
            # Preserve previously commissioned minimum dwell; runtime tuning
            # cannot shorten the original physical protection.
            raw = max(float(raw), proposed) if key != "max_on_s" else proposed
        n = finite(raw, 120 if key != "max_on_s" else 900, 86400)
        if n is None:
            raise ValueError("invalid_hardware_timing")
        values.append(max(minimum, n) if key != "max_on_s" else n)
    if values[2] <= values[0]:
        raise ValueError("maximum_runtime_must_exceed_minimum_on")
    return tuple(values)


def control_modes(manager: Any, spec: ManagedDevice) -> tuple[str, ...]:
    cap = capabilities(manager, spec)
    result = ("existing", "automatic", "manual", "off")
    if cap and (cap.temperature and bool(set(cap.modes) & {"heat", "cool"})
                or cap.domain == "humidifier" and cap.humidity
                or "dry" in cap.modes
                or cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"}):
        return (*result, "pid")
    # A verified PID choice persists through an HA restart. When a climate
    # (including native DRY-only) has not advertised its modes yet, preserve
    # that selected option in the configuration UI; this grants no power or
    # control permission. Runtime actuation still requires live capabilities.
    if (cap is None and settings(manager, spec)["control_mode"] == "pid"
            and any(entity.startswith(("climate.", "humidifier.", "fan."))
                    for entity in spec.source_entities)):
        return (*result, "pid")
    return result


def plan_for(manager: Any, spec: ManagedDevice) -> dict:
    environment = getattr(getattr(manager, "plan", None), "environment", {}) or {}
    item = environment.get(spec.area_id, {})
    plan = item.get("climate_plan", {}) if isinstance(item, dict) else {}
    cached = isinstance(plan, dict) and bool(plan) and plan.get("status") != "disabled"
    cfg = settings(manager, spec)
    current = manager.settings
    # Current configuration owns presence, including an intentional empty
    # selection. A cached room plan can predate a tracker change or HA restart.
    # Older callers without the configuration key may supply its context in
    # the plan, but its states and persisted absence still need live checks.
    shared = (current["occupancy_global"] if "occupancy_global" in current
              else plan.get("global_presence") if cached else {})
    rooms = current.get("climate_rooms", {})
    rooms = rooms if isinstance(rooms, dict) else {}
    from .occupancy_policy import shared_home_settings
    shared = shared_home_settings(shared, rooms)
    continuity = getattr(manager, "presence_continuity", None)
    if continuity is not None:
        shared = continuity.context(shared)
    inherit = (cfg.get("sleep_when_everyone_asleep") is True
               and cfg.get("control_mode") in ("automatic", "pid"))
    # Home/Away and room presence must be refreshed even without optional
    # sleep/alarm features. Otherwise a live Away gate can approve operating
    # an always-allowed heater using an old, higher Home/Comfort target.
    # A native-only controller can run before a room plan exists. Give that
    # fallback the same explicit selections and numeric freshness limits as
    # the manager's room plan, including a deliberately empty sensor list.
    shared = {**shared,
              "_room_occupancy_selections": {
                  area: list(value["occupancy_sensors"])
                  for area, value in rooms.items()
                  if isinstance(value, dict) and isinstance(value.get("occupancy_sensors"), list)
              },
              "_room_occupancy_stale_minutes": {
                  area: value["occupancy_stale_minutes"]
                  for area, value in rooms.items()
                  if isinstance(value, dict) and "occupancy_stale_minutes" in value
              },
              "_room_occupancy_freshness_mode": {
                  area: value.get("occupancy_freshness_mode", "auto")
                  for area, value in rooms.items() if isinstance(value, dict)
              }}
    from .occupancy_policy import room_presence, home_presence, controlled_sleep_presence
    from .climate_schedule import scheduled_sleep
    import time
    room = room_config(manager, spec)
    known = set(plan.get("known_presence_areas", ())) if cached else set()
    if not known:
        known = ({spec.area_id} | set(current.get("areas", ()))
                 | set(rooms))
    home, home_evidence, trackers = home_presence(
        manager.hass, shared, room.get("away_entities", []))
    occupancy, evidence, sensors = room_presence(
        manager.hass, spec.area_id, room, shared, known_areas=known, home_status=home)
    zone = getattr(getattr(manager.hass, "config", None), "time_zone", None) or "UTC"
    now = time.time()
    local_sleep, local_reason = scheduled_sleep(room, now, zone)
    sleeping, sleep_evidence = controlled_sleep_presence(
        manager.hass, spec.area_id, shared, known, home_status=home,
        room_status=occupancy, local_sleeping=local_sleep, local_reason=local_reason,
        inherit_household=inherit, now=now,
    )
    # A per-device policy must not mutate the room plan shared by its peers.
    # Re-reading before dispatch also catches a wake boundary crossed during IO.
    facts = {"away": home, "away_evidence": home_evidence, "sleeping": sleeping,
             "sleep_schedule_evidence": sleep_evidence,
             "occupancy": occupancy, "occupancy_evidence": evidence,
             "presence_entities": sensors, "tracker_entities": trackers,
             "global_presence": shared, "known_presence_areas": sorted(known)}
    preparation = getattr(manager, "arrival_preparation", None)
    if preparation is not None:
        from .arrival_preparation import automatic_eligible
        facts.update(preparation.context(home, eligible=automatic_eligible(cfg)))
    else:
        # Never inherit an active marker from a previous manager instance.
        facts.update(arrival_preparing=False, arrival_preparation_expires_at=None)
    # Every native dispatch rechecks the SAME door/vacancy/temperature/RH
    # gates. A stale cached plan must not keep Eco active after the door opens.
    # Do not operate a physical device or infer isolation from an unselected
    # contact. Use only independently verified fresh same-area measurements.
    if room.get("closed_door_eco") is True or room.get("door_sensors"):
        from .room_doors import observe as observe_room_door
        from .room_sources import (
            selected as selected_room_inputs, aggregate, room_temperature_evidence,
        )
        from .discovery import entity_area
        temperature, _ = room_temperature_evidence(
            manager.hass, current, spec.area_id,
            pinned=room.get("temperature_entity"), age_minutes=10,
        )
        humidity_ids = selected_room_inputs(current, spec.area_id, "humidity")
        if humidity_ids is None:
            legacy_humidity = room.get("humidity_entity")
            humidity_ids = ([legacy_humidity] if isinstance(legacy_humidity, str) and legacy_humidity
                            else [])
        humidity, _ = aggregate(manager.hass, humidity_ids, spec.area_id, "humidity", 10)
        windows = selected_room_inputs(current, spec.area_id, "windows")
        if windows is None:
            contact_ids = [
                state.entity_id for state in manager.hass.states.async_all("binary_sensor")
                if entity_area(manager.hass, state.entity_id) == spec.area_id
                and state.attributes.get("device_class") == "window"
            ]
        else:
            contact_ids = list(windows)
        window_safe = all(
            (item := manager.hass.states.get(eid)) is not None
            and item.state == "off"
            and entity_area(manager.hass, eid) == spec.area_id
            and item.attributes.get("device_class") == "window"
            for eid in contact_ids
        )
        door = observe_room_door(
            manager.hass, spec.area_id, room,
            occupancy=occupancy, occupancy_evidence=evidence,
            occupancy_sources=[source for source in sensors
                               if source != shared.get("occupied_rooms_entity")],
            home=home, sleeping=sleeping,
            temperature_c=temperature, humidity_rh=humidity,
            window_safe=window_safe,
            preparing_arrival=bool(facts.get("arrival_preparing")),
        )
        facts.update(door=door, door_eco_active=door["eco_active"])
    else:
        facts.update(door_eco_active=False)
    if cached:
        return {**plan, **facts}
    # Legacy PID-only rooms have no climate profile/window plan.
    from .discovery import entity_area
    from .room_sources import selected
    chosen_contacts = selected(manager.settings, spec.area_id, "windows")
    if chosen_contacts is None:
        contacts = [state for state in manager.hass.states.async_all("binary_sensor")
                    if entity_area(manager.hass, state.entity_id) == spec.area_id
                    and state.attributes.get("device_class") == "window"]
    else:
        contacts = [state for entity in chosen_contacts
                    if (state := manager.hass.states.get(entity)) is not None
                    and entity_area(manager.hass, entity) == spec.area_id
                    and state.attributes.get("device_class") == "window"]
    return {**facts,
            "window_safe": (chosen_contacts is None or len(contacts) == len(chosen_contacts))
                           and all(state.state == "off" for state in contacts),
            "window_contacts": [state.entity_id for state in contacts]}


def automatic_profile_reason(config: dict, plan: dict) -> str | None:
    """Require verified home evidence before using an inferred active target.

    A restored or unavailable home source is neither Home nor Away. The
    presentation fallback in profile_name must not authorize a new output or
    boost until that source recovers. Explicit presets and Manual control
    keep their own authority; their other live policies still apply.
    """
    if config.get("control_mode") not in ("automatic", "pid"):
        return None
    requested = config.get("preset", "none")
    if requested != "none" and requested in PRESETS:
        return None
    if plan.get("away") not in ("home", "away"):
        return "house_occupancy_unknown"
    return None


def profile_name(config: dict, plan: dict) -> str:
    requested = config.get("preset", "none")
    if requested != "none" and requested in PRESETS:
        return requested
    if config.get("control_mode") == "manual":
        return "manual"  # Manual None keeps its independent explicit targets.
    if (config.get("control_mode") in ("automatic", "pid")
            and plan.get("arrival_preparing") is True and plan.get("away") == "away"):
        return "home"
    if plan.get("away") == "away":
        return "away"
    if plan.get("sleeping") is True:
        return "sleep"
    if plan.get("occupancy") == "occupied":
        return "comfort"
    if (config.get("control_mode") in ("automatic", "pid")
            and plan.get("door_eco_active") is True
            and plan.get("occupancy") == "unoccupied"
            and plan.get("away") == "home"):
        return "eco"
    # A verified home with an empty room, and incomplete occupancy evidence,
    # both use Home. Unknown evidence must never imply Away.
    return "home"


def targets(manager: Any, spec: ManagedDevice, cap: Capabilities, config: dict,
            plan: dict, *, mold_protection: bool = True) -> dict[str, float]:
    room = room_config(manager, spec)
    profile = profile_name(config, plan)
    limits = device_limits(manager, spec, cap)

    raw_profiles = room.get("profiles", {}) if isinstance(room, dict) else {}
    bands = raw_profiles if isinstance(raw_profiles, dict) else {}
    defaults = DEFAULT_PROFILE_TARGETS

    if profile == "manual":
        band=bands.get("comfort",defaults["comfort"])
        fallback=defaults["comfort"]
    else:
        fallback=defaults.get(profile,defaults["home"])
        band=bands.get(profile,fallback)
    band = band if isinstance(band,dict) else fallback
    heat=float(band.get("heat_c",fallback["heat_c"]))
    cool=float(band.get("cool_c",fallback["cool_c"]))
    humidity = profile_humidity_target(room, "comfort" if profile == "manual" else profile)
    result={"heat":float(heat),"cool":float(cool),"humidity":float(humidity)}

    # Optional comfort narrows the effective fixed band, so apply native/room
    # limits first. Clipping an already-adjusted band could erase its deadband.
    # A too-narrow bounded base stays fixed; never invent wider saved targets.
    basis=room.get("target_source")
    if profile in ("comfort", "sleep") and basis in ("auto_comfort", "pmv"):
        from .comfort_targets import automatic_comfort_band, pmv_comfort_band
        hysteresis=finite(room.get("hysteresis_c",0.7),0.2,3)
        base_heat=finite(result["heat"],5,35)
        base_cool=finite(result["cool"],6,40)
        if hysteresis is not None and base_heat is not None and base_cool is not None:
            base_heat=max(limits["temperature_min_limit"],min(limits["temperature_max_limit"],base_heat))
            base_cool=max(limits["temperature_min_limit"],min(limits["temperature_max_limit"],base_cool))
            kwargs={"maximum_adjustment_c": room.get("comfort_adjustment_max_c",1.5),
                    "minimum_deadband_c": max(1.0,2*hysteresis)}
            comfort={}
            if basis=="auto_comfort":
                runtime=getattr(manager,"equipment",None)
                sample=(runtime.measurements(spec,cap) if runtime is not None else {})
                sample=sample if isinstance(sample,dict) else {}
                comfort=automatic_comfort_band(base_heat,base_cool,sample.get("humidity"),**kwargs)
            elif config.get("control_mode") in ("automatic","pid"):
                # Selecting PMV never enables its assessment or physical
                # control. Consume only the current qualified plan, without
                # retaining a previous estimate after evidence disappears.
                rooms=manager.settings.get("environment_rooms",{})
                science=rooms.get(spec.area_id,{}) if isinstance(rooms,dict) else {}
                environment=getattr(getattr(manager,"plan",None),"environment",{})
                current=environment.get(spec.area_id,{}) if isinstance(environment,dict) else {}
                international=current.get("international",{}) if isinstance(current,dict) else {}
                estimate=international.get("pmv_air_target",{}) if isinstance(international,dict) else {}
                if (isinstance(science,dict) and science.get("enable_pmv") is True
                        and isinstance(estimate,dict) and estimate.get("status")=="estimate"):
                    comfort=pmv_comfort_band(
                        base_heat,base_cool,estimate.get("air_temperature_target_c"),**kwargs)
            if comfort.get("status") in ("humidity_aware_estimate","pmv_estimate"):
                result["heat"],result["cool"]=comfort["heat_c"],comfort["cool_c"]

    scoped_mode = config.get("operating_mode")
    if profile == "manual" or scoped_mode in MODE_KEYS:
        table = config.get("profile_targets", {})
        override = table.get(profile, {}) if isinstance(table, dict) else {}
        if isinstance(override,dict):
            allowed = ((scoped_mode,) if scoped_mode in ("heat", "cool") else
                       ("humidity",) if scoped_mode in ("dry", "humidify") else
                       ("heat", "cool") if scoped_mode in ("auto", "heat_cool") else
                       () if scoped_mode == "fan_only" else tuple(result))
            result.update({k:v for k,v in override.items() if k in allowed
                           and finite(v, -math.inf, math.inf) is not None})

    result["heat"]=max(limits["temperature_min_limit"],
                       min(limits["temperature_max_limit"],float(result["heat"])))
    result["cool"]=max(limits["temperature_min_limit"],
                       min(limits["temperature_max_limit"],float(result["cool"])))
    result["humidity"]=max(limits["humidity_min_limit"],
                           min(limits["humidity_max_limit"],float(result["humidity"])))
    if mold_protection and cap.humidity and config.get("control_mode") in ("automatic", "pid"):
        result["humidity"] = _humidity_demand(
            manager, spec, cap, config, result["humidity"], limits,
        )["effective_humidity_target"]
    return result


def _humidity_demand(manager: Any, spec: ManagedDevice, cap: Capabilities,
                     config: dict, requested: float, limits: dict) -> dict:
    from .mold_control_demand import room_mold_demand
    evidence = room_mold_demand(manager, spec.area_id) if cap.humidity else {
        "status": "not_supported", "mold_protection_required": False,
    }
    result = {**evidence, "requested_humidity_target": requested,
              "effective_humidity_target": requested, "mold_target_active": False}
    required = finite(evidence.get("mold_required_humidity_target"), 0.000001, 100)
    if required is None or config.get("control_mode") not in ("automatic", "pid"):
        return result
    # Existing native humidity writes use integral percentage points. Round
    # the derived limit downward so a native target cannot round back above
    # the configured surface limit. A DRY mode with no native RH setpoint can
    # regulate against the full-precision room feedback target instead.
    quantized = (float(math.floor(required)) if cap.native_humidity_target
                 or cap.domain == "humidifier" else required)
    lower, upper = limits["humidity_min_limit"], limits["humidity_max_limit"]
    bounded = max(lower, min(upper, quantized))
    effective = min(requested, bounded)
    limited = bounded > required
    result.update(effective_humidity_target=effective,
                  mold_target_active=effective < requested,
                  mold_target_limited=limited,
                  mold_target_limit_reason="humidity_minimum_limit" if limited else None)
    # Retain this calibrated upper bound below the threshold as well, so a
    # humidifier cannot immediately recreate the same surface-RH problem.
    if effective < requested:
        result["target_provenance"] = "calibrated_surface_rh_limit"
    if limited and evidence.get("mold_protection_required") is True:
        result["status"] = ("mold_target_blocked_by_limits"
                            if evidence.get("indoor_humidity", 0) <= bounded
                            else "mold_target_limited")
    return result


def humidity_demand(manager: Any, spec: ManagedDevice, cap: Capabilities,
                    config: dict, plan: dict) -> dict:
    """Requested/effective RH targets and current calibrated mold provenance.

    Saved target editors use targets(..., mold_protection=False). Runtime and
    its physical facade use the default effective target. This read-only
    diagnostic does not alter saved comfort values or operating permissions.
    """
    requested = targets(manager, spec, cap, config, plan, mold_protection=False)["humidity"]
    return _humidity_demand(manager, spec, cap, config, requested,
                            device_limits(manager, spec, cap))


@dataclass(frozen=True, slots=True)
class PIDMemory:
    integral: float = 0.
    measured: float | None = None
    stamp: float | None = None
    derivative: float = 0.
    demand: float = 0.


def pid_step(measured: float, target: float, now: float, *, increasing: bool,
             kp: float, ki: float, kd: float, sample: float,
             memory: PIDMemory | None = None) -> PIDMemory:
    """Dimension-independent PID: °C, RH points, ppm or µg/m³ are never mixed.

    Derivative on measurement, conditional-integration anti-windup and sample
    hold. A fresh satisfied target overrides the sample hold and clears prior
    effort. Reset on invalid timestamps/gaps; no integral across profiles.
    """
    old = memory or PIDMemory()
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
           for v in (measured, target, now, kp, ki, kd, sample)) or min(kp, ki, kd) < 0 or sample < 120:
        return PIDMemory()
    direction = 1 if increasing else -1
    error = direction * (target - measured)
    if error <= 0:
        # A cycle cannot outlive its measured need. Neither a cached ON demand
        # nor accumulated integral/derivative may request heating/humidifying
        # at or above the target, or cooling/drying at or below it. Reseed the
        # next normal sample so the satisfied interval cannot wind up effort.
        return PIDMemory(measured=measured, stamp=now)
    if old.stamp is None or old.measured is None or now < old.stamp or now-old.stamp > max(3*sample, 1800):
        return PIDMemory(measured=measured, stamp=now, demand=max(0., min(100., kp*error)))
    dt = now-old.stamp
    if dt < sample:
        return old
    minutes = dt/60
    derivative = .25*(measured-old.measured)/minutes + .75*old.derivative
    p, d = kp*error, -direction*kd*derivative
    trial = max(-100., min(100., old.integral+ki*error*minutes))
    raw = p+trial+d
    integral = old.integral if (raw >= 100 and error > 0) or (raw <= 0 and error < 0) else trial
    return PIDMemory(integral, measured, now, derivative, max(0., min(100., p+integral+d)))


def duty_on(demand: float, elapsed: float, cycle: float, min_on: float, min_off: float,
            *, starting: bool = False) -> bool:
    """Slow time-proportioning. Never fabricate a pulse shorter than a dwell.

    Sub-minimum demand is skipped; near-full demand is bounded by min-OFF.
    The runtime separately enforces actual observed transitions and max-ON.
    """
    if (any(isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v)
            for v in (demand, elapsed, cycle, min_on, min_off))
            or cycle <= 0 or min_on < 0 or min_off < 0
            or cycle < min_on+min_off or elapsed < 0):
        return False
    if demand >= 100:
        return True
    duration = cycle * max(0., demand) / 100
    if duration < min_on:
        return False
    duration = min(duration, cycle-min_off)
    phase = elapsed % cycle
    return phase < duration and (not starting or duration-phase >= min_on)


def claimed_sources(manager: Any) -> set[str]:
    active = {e for spec in specs(manager) if settings(manager, spec)["control_mode"] != "existing"
              for e in spec.source_entities}
    for record in getattr(getattr(manager, "equipment", None), "records", {}).values():
        active.update(record.get("power", {}))
        if isinstance(record.get("pending"), dict):
            active.add(record["pending"]["entity"])
        sequence = record.get("native_setpoint_stop")
        if isinstance(sequence, dict) and isinstance(sequence.get("entity"), str):
            active.add(sequence["entity"])
    return active


def legacy_settings(manager: Any) -> tuple[dict, dict]:
    """Remove only claimed endpoints, keeping other devices/areas independent."""
    rooms = deepcopy(manager.settings.get("climate_rooms", {}))
    pids = deepcopy(manager.settings.get("pid_rooms", {}))
    claimed = claimed_sources(manager)
    if not claimed:
        return rooms, pids
    for cfg in rooms.values() if isinstance(rooms, dict) else ():
        if not isinstance(cfg, dict):
            continue
        for key in ("climate_entity", "heat_climate_entity", "cool_climate_entity", "dry_climate_entity",
                    "fan_climate_entity", "humidifier_entity", "dehumidifier_entity",
                    "extraction_fan_entity", "purifier_fan_entity", "heat_actuator", "cool_actuator"):
            if cfg.get(key) in claimed:
                cfg.pop(key, None)
        if isinstance(cfg.get("selected_devices"), list):
            cfg["selected_devices"] = [e for e in cfg["selected_devices"] if e not in claimed]
    for cfg in pids.values() if isinstance(pids, dict) else ():
        if isinstance(cfg, dict) and isinstance(cfg.get("climate_entities"), list):
            cfg["climate_entities"] = [e for e in cfg["climate_entities"] if e not in claimed]
            if not cfg["climate_entities"]:
                cfg["enabled"] = False
    return rooms, pids


def legacy_hold(hass: Any, entry_id: str | None, entity: str) -> str | None:
    manager = getattr(hass, "data", {}).get(DOMAIN, {}).get(entry_id)
    if manager is not None and entity in claimed_sources(manager):
        return "per_device_controller_owns_source"
    return None

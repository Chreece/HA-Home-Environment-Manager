"""Read-only room data availability, separate from actuator safety decisions.

The overview answers whether the room has its necessary measurements. Optional
science, window contacts, a stopped appliance and pending commands are different
diagnostics. Only a configured feedback-dependent controller can make one of the
otherwise optional measurements required. This module never grants control.
"""
from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

METRICS = ("temperature", "humidity", "co2", "pm25", "illuminance")
_THERMAL_MODES = frozenset(("heat", "cool", "heat_cool", "auto"))
_AUTOMATIC = frozenset(("automatic", "pid"))


def usable(value: Any, metric: str) -> bool:
    """Normalized numeric evidence; booleans and missing values are not zero."""
    if type(value) not in (int, float):
        return False
    try:
        if not math.isfinite(value):
            return False
    except OverflowError:
        return False
    if metric == "temperature":
        return -60 <= value <= 85
    if metric == "humidity":
        return 0 < value <= 100
    if metric == "co2":
        return 250 <= value <= 20000
    if metric == "illuminance":
        return 0 <= value <= 300000
    return metric == "pm25" and value >= 0


def _basic_metrics(room: Any, environment: dict) -> set[str]:
    evidence = environment.get("measurement_evidence", {})
    evidence = evidence if isinstance(evidence, dict) else {}
    available = set()
    for metric in ("temperature", "humidity"):
        observation = evidence.get(metric, {})
        if isinstance(observation, dict) and usable(observation.get("value"), metric):
            available.add(metric)
        elif metric not in evidence and any(getattr(item, "metric", None) == metric
                 and usable(getattr(item, "value", None), metric)
                 for item in room.readings):
            available.add(metric)
    # Older plans have a validated climate temperature before the shared
    # measurement-evidence projection exists. Match the room's displayed value.
    climate = environment.get("climate_plan", {})
    if ("measurement_evidence" not in environment and isinstance(climate, dict)
            and usable(climate.get("temperature_c"), "temperature")):
        available.add("temperature")
    return available


def classify(room: Any, environment: dict, controllers: list[dict] | None = None) -> dict:
    """Pure classification shared by dashboard counts and room entities."""
    environment = environment if isinstance(environment, dict) else {}
    basic = _basic_metrics(room, environment)
    missing_basic = [metric for metric in ("temperature", "humidity") if metric not in basic]
    rows = []
    for item in controllers or ():
        if not isinstance(item, dict):
            continue
        metrics = [metric for metric in METRICS if metric in item.get("metrics", ())]
        if not metrics:
            continue
        row = {
            "controller_id": str(item.get("controller_id", "")),
            "name": str(item.get("name", "")),
            "metrics": metrics,
            "missing_metrics": [metric for metric in metrics
                                if metric in item.get("missing_metrics", ())],
        }
        if "target_ready" in item:
            row.update(target_ready=item.get("target_ready") is True,
                       unavailable_reason=str(item.get("unavailable_reason") or ""),
                       missing_inputs=[value for value in item.get("missing_inputs", ())
                                       if isinstance(value, str)])
        rows.append(row)
    required = [metric for metric in METRICS if any(metric in row["metrics"] for row in rows)]
    missing = [metric for metric in required if any(metric in row["missing_metrics"] for row in rows)]
    unavailable = [{"controller_id": row["controller_id"], "name": row["name"],
                    "reason": row["unavailable_reason"]}
                   for row in rows if row.get("target_ready") is False]
    status = ("missing" if missing or unavailable else "ready") if required else (
        "missing" if len(missing_basic) == 2 else "partial" if missing_basic else "ready")
    return {
        "status": status,
        "required_metrics": required,
        "missing_required_metrics": missing,
        "unavailable_controllers": unavailable,
        "controllers": rows,
        "missing_basic_metrics": missing_basic,
    }


def _capabilities(manager: Any, spec: Any, equipment: Any) -> Any | None:
    cap = equipment.capabilities(manager, spec)
    if cap is not None:
        return cap
    # A battery appliance can be offline while its exact configured feedback
    # remains available. Its previously verified capabilities describe what
    # measurement is needed, never permission to operate the offline appliance.
    records = getattr(getattr(manager, "equipment", None), "records", {})
    record = records.get(spec.identifier, {}) if isinstance(records, dict) else {}
    if (not isinstance(record, dict) or record.get("area") != spec.area_id
            or record.get("source_device_id") != spec.source_device_id
            or not isinstance(record.get("sources"), (list, tuple))
            or tuple(record["sources"]) != tuple(spec.source_entities)):
        return None
    try:
        cap = equipment.Capabilities(**record["capabilities"])
        if (cap.primary not in spec.source_entities
                or cap.domain != cap.primary.partition(".")[0]
                or not isinstance(cap.modes, (list, tuple))
                or not cap.modes or not set(cap.modes) <= equipment.HVAC_MODES):
            return None
        return cap
    except (KeyError, TypeError, ValueError):
        return None


def _metric_for_controller(manager: Any, spec: Any, cap: Any, cfg: dict) -> str | None:
    """Mirror the runtime's selected direction, not all advertised modes."""
    if cap.domain == "humidifier":
        return "humidity"
    mode = cfg.get("operating_mode") or cfg.get("requested_mode")
    mode = mode if isinstance(mode, str) else None
    if mode not in cap.modes:
        choose = getattr(getattr(manager, "equipment", None), "active_control_mode", None)
        mode = choose(spec) if callable(choose) else None
        mode = mode if isinstance(mode, str) else None
    if mode not in cap.modes:
        state = manager.hass.states.get(cap.primary)
        observed = getattr(state, "state", None)
        mode = observed if observed in cap.modes and observed != "off" else None
    if mode is None or mode == "off":
        modes = set(cap.modes) - {"off"}
        # A stopped heat/cool controller may need temperature to choose its
        # first direction. Every eligible thermal direction uses that same
        # input; mixed dry/fan modes do not imply an unselected requirement.
        if modes and modes <= _THERMAL_MODES:
            return "temperature"
        mode = next(iter(modes)) if len(modes) == 1 else None
    if cap.domain == "fan" or mode == "fan_only":
        from .device_activation import resolved_fan_purpose
        purpose = resolved_fan_purpose(manager, spec, cap.primary)
        return {"extraction": "co2", "filtration": "pm25"}.get(purpose)
    if mode == "dry":
        return "humidity"
    return "temperature" if mode in _THERMAL_MODES else None


def _configured_metric(manager: Any, spec: Any, cap: Any, cfg: dict,
                       equipment: Any) -> str | None:
    """Keep shared feedback visible while automatic profiles choose a direction.

    At startup a scoped heat/cool controller can have no active mode precisely
    because its temperature is missing. Its base method may still be Existing;
    the runtime considers each eligible mode profile when choosing a direction.
    Mirror those profiles without choosing a mode or counting unused features.
    """
    if cfg.get("requested_mode") is None and cfg.get("operating_mode") is None:
        raw = equipment.raw_settings(manager, spec)
        if equipment.has_mode_settings(raw):
            metrics = set()
            for mode in equipment.operating_modes(manager, spec):
                profile = equipment.settings_for_mode(manager, spec, mode)
                method = profile.get("control_mode")
                if isinstance(method, str) and method in _AUTOMATIC:
                    metric = _metric_for_controller(manager, spec, cap, profile)
                    if metric is not None:
                        metrics.add(metric)
            # Different eligible directions need different evidence. Until a
            # direction exists, only a common input is an unambiguous need.
            # A profile without a resolved feedback metric must not erase
            # the known requirement of another eligible direction.
            return next(iter(metrics)) if len(metrics) == 1 else None
    method = cfg.get("control_mode")
    return (_metric_for_controller(manager, spec, cap, cfg)
            if isinstance(method, str) and method in _AUTOMATIC else None)


def _unavailable_input(manager: Any, spec: Any, cfg: dict, equipment: Any) -> tuple[Any, dict]:
    """Keep an explicit feedback choice visible before native capability arrival.

    This is only an exact source identity for measurements(), not a synthetic
    native capability or actuation grant. No configured direction means no
    guessed requirement. A cached/advertised list is never expanded here.
    """
    from .discovery import entity_area
    from .room_sources import native
    primary = min(spec.source_entities, key=lambda entity: (
        {"climate": 0, "humidifier": 1, "fan": 2, "switch": 3,
         "input_boolean": 3, "number": 4, "input_number": 4}.get(entity.partition(".")[0], 9),
        entity))
    if entity_area(manager.hass, primary) != spec.area_id or not native(manager.hass, primary):
        return None, cfg
    domain = primary.partition(".")[0]
    raw = equipment.raw_settings(manager, spec)
    mode = cfg.get("operating_mode") or cfg.get("requested_mode")
    mode = mode if isinstance(mode, str) else None
    if mode in (None, "off"):
        requested = raw.get("requested_mode")
        mode = requested if isinstance(requested, str) and requested != "off" else None
    modes = raw.get("mode_settings", {})
    if (type(raw.get("mode_settings_version")) is int and raw["mode_settings_version"] == 1
            and isinstance(modes, dict) and isinstance(modes.get(mode), dict)):
        cfg = {**cfg, **modes[mode], "operating_mode": mode}
    if mode not in (*_THERMAL_MODES, "dry", "humidify", "fan_only"):
        return None, cfg
    if domain == "humidifier" and mode == "auto":
        mode = "humidify"
    metric = ("humidity" if mode in ("dry", "humidify") else
              "temperature" if mode in _THERMAL_MODES else None)
    if mode == "fan_only":
        from .device_activation import resolved_fan_purpose
        metric = {"extraction": "co2", "filtration": "pm25"}.get(
            resolved_fan_purpose(manager, spec, primary))
    if metric is None:
        return None, cfg
    return SimpleNamespace(primary=primary, metric=metric), cfg


def _row(identifier: str, name: str, values: dict) -> dict:
    metrics = [metric for metric in METRICS if metric in values]
    return {"controller_id": identifier, "name": name, "metrics": metrics,
            "missing_metrics": [metric for metric in metrics if not usable(values[metric], metric)]}


def controller_inputs(manager: Any, *, area_id: str | None = None) -> dict[str, list[dict]]:
    """Resolve current configured control inputs without services or state writes.

    Area snapshots restrict measurement reads to their own room. All actual
    values come from the existing control resolvers. This projection creates no
    Recorder query, task or persistent journal.
    """
    settings = getattr(manager, "settings", {})
    hass = getattr(manager, "hass", None)
    if not isinstance(settings, dict) or hass is None:
        return {}
    from . import equipment_model as equipment
    from .device_hierarchy import configured_sources
    result: dict[str, list[dict]] = {}
    runtime = getattr(manager, "equipment", None)
    resolver = getattr(runtime, "measurements", None)
    for spec in equipment.specs(manager):
        if area_id is not None and spec.area_id != area_id:
            continue
        sources = tuple(spec.source_entities)
        if not sources or not set(sources).issubset(configured_sources(settings, spec.area_id)):
            continue
        cfg = equipment.settings(manager, spec)
        # Explicit user-requested OFF is an unconditional stop in the runtime,
        # even when Automatic/PID remains the saved supervisory method. The
        # native device merely reporting OFF between cycles is different.
        if cfg.get("requested_mode") == "off":
            continue
        cap = _capabilities(manager, spec, equipment)
        if cap is None:
            source, cfg = _unavailable_input(manager, spec, cfg, equipment)
            metric = source.metric if source is not None else None
            method = cfg.get("control_mode")
            if not isinstance(method, str) or method not in _AUTOMATIC:
                metric = None
        else:
            source = cap
            metric = _configured_metric(manager, spec, cap, cfg, equipment)
        if metric is None:
            continue
        measured = resolver(spec, source) if callable(resolver) else {}
        measured = measured if isinstance(measured, dict) else {}
        values = {metric: measured.get(metric)}
        demand = None
        if (metric == "humidity" and cap is not None
                and equipment.uses_mold_target(manager, spec, cap, cfg)):
            demand = equipment.humidity_demand(
                manager, spec, cap, cfg, equipment.plan_for(manager, spec))
            # The calibrated model can pin a different temperature source.
            # Preserve its exact partial evidence: absent weather must not be
            # represented as absent indoor temperature or a stale RH fallback.
            if "indoor_temperature_c" in demand:
                values["temperature"] = demand.get("indoor_temperature_c")
            if "indoor_humidity" in demand:
                values["humidity"] = demand.get("indoor_humidity")
        row = _row(spec.identifier, spec.name, values)
        if demand is not None:
            ready = demand.get("target_ready") is True
            if not ready and "indoor_humidity" not in demand:
                # Calibration can reject the target before reading any RH.
                # That is an unavailable derived target, not evidence that
                # the selected physical humidity sensors have disappeared.
                row["missing_metrics"] = [value for value in row["missing_metrics"]
                                          if value != "humidity"]
            row.update(target_ready=ready,
                       unavailable_reason="" if ready else demand.get(
                           "target_unavailable_reason", "control_measurement_missing_or_stale"),
                       missing_inputs=demand.get("missing_inputs", []))
        result.setdefault(spec.area_id, []).append(row)

    # Retain the old room PID's exact input only while it still owns targets.
    # Claimed native endpoints are removed by the same projection used by the
    # actual scheduler, so a migrated/off/manual controller is not counted twice.
    if settings.get("pid_rooms"):
        from .discovery import entity_area, temperature_sensor_c
        _, pids = equipment.legacy_settings(manager)
        for area, cfg in pids.items() if isinstance(pids, dict) else ():
            if (area_id is not None and area != area_id
                    or not isinstance(cfg, dict) or cfg.get("enabled") is not True):
                continue
            targets = cfg.get("climate_entities")
            if targets is None:
                targets = [cfg.get("climate_entity")]
            if not isinstance(targets, (list, tuple)) or not any(
                    isinstance(entity, str) and entity.startswith("climate.") for entity in targets):
                continue
            sensor = cfg.get("temperature_entity")
            value = None
            if (isinstance(sensor, str) and sensor.startswith("sensor.")
                    and entity_area(hass, sensor) in (None, area)):
                observed = temperature_sensor_c(hass, sensor, 10)
                if usable(observed, "temperature") and -10 <= observed <= 50:
                    value = observed
            result.setdefault(area, []).append(_row(
                f"legacy_pid:{area}", "PID", {"temperature": value}))

    if settings.get("shade_rooms"):
        from .discovery import entity_area
        from .room_sources import native, room_temperature_evidence, selected
        from .shade_cooling import cover_config, lux_evidence
        rooms = settings["shade_rooms"]
        for area in rooms if isinstance(rooms, dict) else ():
            if area_id is not None and area != area_id:
                continue
            temperature = None
            temperature_read = False
            for entity in selected(settings, area, "shades") or ():
                if (not entity.startswith("cover.") or entity_area(hass, entity) != area
                        or not native(hass, entity)):
                    continue
                cfg = cover_config(settings, area, entity)
                if cfg.get("enabled") is not True:
                    continue
                if not temperature_read:
                    temperature, _ = room_temperature_evidence(hass, settings, area, age_minutes=10)
                    temperature_read = True
                values = {"temperature": temperature}
                if cfg.get("lux_enabled") is True:
                    values["illuminance"] = lux_evidence(hass, settings, area, cfg).get("value_lx")
                state = hass.states.get(entity)
                name = getattr(state, "name", None) or entity
                result.setdefault(area, []).append(_row(f"shade:{entity}", name, values))
    return result

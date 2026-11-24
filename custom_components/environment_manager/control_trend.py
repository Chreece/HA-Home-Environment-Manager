"""Read-only historical targets and reported outputs for managed controllers.

Samples describe the controller's resolved goal and independent native feedback.
They never replay old settings, infer physical power from a PID request, or send
commands. Storage and retention belong to EnvironmentHistory's bounded journal.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any

from . import equipment_model as model
from .lifecycle import is_stopping
from .pid_diagnostics import observed_output

_UNITS = {"temperature": "°C", "humidity": "%", "mold": "%",
          "co2": "ppm", "pm25": "µg/m³"}
_BASES = {"temperature": "temperature", "humidity": "room_relative_humidity",
          "mold": "mold_surface_rh", "co2": "co2", "pm25": "pm25"}


def _number(value: Any, low: float = -1e6, high: float = 1e6) -> float | None:
    return (float(value) if type(value) in (int, float)
            and math.isfinite(value) and low <= value <= high else None)


def _sources(values: Any) -> list[str]:
    if not isinstance(values, (tuple, list)):
        return []
    return sorted({value for value in values
                   if isinstance(value, str) and value.startswith("sensor.")
                   and len(value) <= 255})[:32]


def _reported_at(state: Any) -> float | None:
    stamp = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
    try:
        return _number(stamp.timestamp(), 0, 1e13) if stamp.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _reported_output(manager: Any, spec: Any, cap: Any, mode: str | None,
                     now: float) -> dict[str, Any]:
    """Native reports only; a setpoint, command ACK or supply is not power."""
    entity = cap.primary
    kind = "activity" if cap.domain == "climate" else "binary"
    if cap.domain in ("number", "input_number"):
        kind = "position"
    elif cap.domain == "fan" or mode == "fan_only":
        entity = cap.fan_entity or cap.primary
        kind = "percentage" if cap.fan_percentage else "binary"
    result = {"output_percent": None, "output_kind": kind,
              "output_entity_id": entity, "output_reported_at": None}
    if entity not in spec.source_entities:
        return result
    state = manager.hass.states.get(entity)
    attrs = getattr(state, "attributes", {}) or {}
    stamp = _reported_at(state)
    if (state is None or getattr(state, "state", None) in (None, "unknown", "unavailable")
            or attrs.get("restored") is True or stamp is None or not 0 <= now - stamp <= 1800):
        return result
    result["output_reported_at"] = stamp
    if kind == "position":
        if attrs.get("unit_of_measurement") == "%" and attrs.get("min") == 0 and attrs.get("max") == 100:
            try:
                result["output_percent"] = _number(float(state.state), 0, 100)
            except (TypeError, ValueError, OverflowError):
                pass
    elif kind == "percentage":
        result["output_percent"] = (0. if state.state == "off"
                                    else _number(attrs.get("percentage"), 0, 100))
    elif cap.domain == "fan" or mode == "fan_only":
        # Discrete speed names have no measured percentage scale. A native fan
        # ON/OFF report is still a useful binary observation, clearly labeled.
        if entity.startswith("fan.") and state.state in ("on", "off"):
            result["output_percent"] = 100. if state.state == "on" else 0.
    else:
        activity = observed_output(cap.domain, state, mode)
        if (cap.domain == "climate" and mode in ("auto", "heat_cool")
                and attrs.get("hvac_action") in ("heating", "cooling")
                and state.state != "off"):
            activity = "on"
        result["output_percent"] = 100. if activity == "on" else 0. if activity == "off" else None
    return result


def _mode(manager: Any, spec: Any, cap: Any, cfg: dict, plan: dict,
          measured: dict, targets: dict) -> str | None:
    requested = cfg.get("requested_mode")
    logical = cfg.get("operating_mode")
    state = manager.hass.states.get(cap.primary)
    if requested == "off" or cfg.get("control_mode") == "off":
        if logical in ("heat", "cool", "dry", "fan_only", "auto", "heat_cool"):
            return logical
        native = getattr(state, "state", None)
        if native in cap.modes and native != "off":
            return native
        directions = [value for value in cap.modes if value != "off"]
        return directions[0] if len(directions) == 1 else None
    mode = requested
    # Legacy Automatic may change direction even while its old requested_mode
    # still says Heat. Scoped policies and an explicit PID direction retain the
    # same precedence as the actual tick, rather than plotting the old mode.
    if (cfg.get("control_mode") in ("automatic", "pid")
            and not (logical and mode in cap.modes)
            and not (cfg.get("control_mode") == "pid" and mode in cap.modes and mode != "off")):
        from .dry_mode import automatic_mode
        room = model.room_config(manager, spec)
        mode = automatic_mode(
            cap, state, measured, targets,
            dedicated_dry=room.get("dry_climate_entity") == cap.primary,
            pid=cfg.get("control_mode") == "pid",
        )
    if mode is None:
        mode = (getattr(state, "state", None) if cap.domain == "climate"
                else next((value for value in cap.modes if value != "off"), None))
    return mode


def _manual_target(cfg: dict, profile: str | None, kind: str) -> bool:
    if cfg.get("control_mode") != "manual" or cfg.get("preset", "none") != "none":
        return True
    table = cfg.get("profile_targets", {})
    values = table.get(profile, {}) if isinstance(table, dict) else {}
    # Manual without an explicit HEM goal follows the native device. The room's
    # default Comfort value is not a historical command or a physical setpoint.
    return isinstance(values, dict) and _number(values.get(kind)) is not None


def _request(manager: Any, spec: Any, metric: str, cfg: dict, context: dict,
             *, candidate: float | None, fresh: bool, now: float) -> tuple[float | None, float | None]:
    """Retain a recent evaluated request, never an inferred physical output."""
    cache = getattr(manager, "_control_trend_requests", None)
    if cache is None:
        cache = manager._control_trend_requests = {}
    requests = cache.setdefault(spec.identifier, {})
    key = hashlib.sha256(json.dumps({"configuration": cfg, **context}, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if fresh:
        if candidate is None:
            requests.pop(metric, None)
        else:
            requests[metric] = {"context": key, "at": now, "value": candidate}
    saved = requests.get(metric)
    cadence = _number(cfg.get("sample_seconds"), 120, 3600) or 300.
    if (saved is not None and saved.get("context") == key
            and 0 <= now - saved["at"] <= 1.5 * cadence):
        return saved["value"], saved["at"]
    requests.pop(metric, None)
    return None, None


def _observations(manager: Any, spec: Any, *, configuration: dict | None = None,
                  cap: Any = None, plan: dict | None = None,
                  measurements: dict | None = None, humidity: dict | None = None,
                  status: dict | None = None, evaluation: dict | None = None,
                  now: float) -> list[dict]:
    runtime = manager.equipment
    cfg = configuration if isinstance(configuration, dict) else model.settings(manager, spec)
    evaluation_current = True
    if evaluation is not None:
        # The runtime can have awaited a durable write since its first input
        # snapshot. Present current targets/sources, and reject old requests
        # instead of recording their older configuration at this later time.
        current_cfg = model.settings(manager, spec)
        evaluation_current = cfg == current_cfg
        cfg, cap, plan, measurements, humidity = current_cfg, None, None, None, None
    cap = cap if cap is not None else model.mode_capabilities(manager, spec)
    if cap is None or cap.primary not in spec.source_entities:
        return []
    plan = plan if isinstance(plan, dict) else model.plan_for(manager, spec)
    measured = measurements if isinstance(measurements, dict) else runtime.measurements(spec, cap)
    if (isinstance(humidity, dict) and cap.humidity
            and cfg.get("control_mode") in ("automatic", "pid")):
        targets = model.targets(manager, spec, cap, cfg, plan, mold_protection=False)
        targets["humidity"] = humidity.get("effective_humidity_target")
    else:
        targets = model.targets(manager, spec, cap, cfg, plan)
    mode = _mode(manager, spec, cap, cfg, plan, measured, targets)
    profile = model.profile_name(cfg, plan)
    method = cfg.get("control_mode", "existing")
    inactive = method not in ("automatic", "pid", "manual") or cfg.get("requested_mode") == "off"
    reason = "controller_inactive" if inactive else model.automatic_profile_reason(cfg, plan)
    if reason:
        profile = None
    fresh_status = isinstance(status, dict)
    status = status if fresh_status else getattr(runtime, "statuses", {}).get(spec.identifier, {})
    status = status if isinstance(status, dict) else {}
    # A status read may describe an old tick. Only the caller's fresh evaluation
    # or a newly emitted status can supply a PID request; never read _memory.
    demand = None
    if evaluation is not None and method == "pid" and not reason:
        # Configuration edits and source events can arrive while a tick awaits
        # durable writes. A later observation must not revive its older demand.
        if (evaluation_current
                and spec.identifier not in getattr(runtime, "_invalidated", set())
                and evaluation.get("mode") == mode
                and evaluation.get("profile") == profile):
            demand = _number(evaluation.get("demand_percent"), 0, 100)
    elif (fresh_status and method == "pid" and not reason and status.get("mode") == mode
          and status.get("profile") == profile):
        demand = _number(status.get("demand_percent"), 0, 100)
    if reason or method != "pid" or fresh_status and demand is None:
        getattr(manager, "_control_trend_requests", {}).pop(spec.identifier, None)
    output = _reported_output(manager, spec, cap, mode, now)
    metrics: list[tuple[str, float | None, float | None, float | None, str]] = []
    if cap.domain == "fan" or mode == "fan_only" or set(cap.modes) == {"off", "fan_only"}:
        from .device_activation import effective_device
        device = effective_device(manager, spec, cap.primary)
        metric = "co2" if device.get("fan_purpose") == "extraction" else "pm25"
        threshold = "co2_operational_ppm" if metric == "co2" else "pm25_short_term_action_ug_m3"
        goal = plan.get("air_actions", {}).get("thresholds", {}).get(threshold)
        metrics.append((metric, _number(goal) if method in ("automatic", "pid") else None,
                        None, None, "control"))
    elif cap.domain == "humidifier" or mode == "dry":
        humidity = humidity if isinstance(humidity, dict) else model.humidity_demand(manager, spec, cap, cfg, plan)
        surface = humidity.get("target_basis") == "mold_surface_rh"
        goal = _number(targets.get("humidity")) if _manual_target(cfg, profile, "humidity") else None
        metrics.append(("humidity", goal, None, None, "derived_room_rh" if surface else "control"))
        if surface:
            metrics.append(("mold", _number(humidity.get("control_target")), None, None, "control"))
    elif mode in ("heat", "cool"):
        goal = _number(targets.get(mode)) if _manual_target(cfg, profile, mode) else None
        metrics.append(("temperature", goal, None, None, "control"))
    elif mode in ("auto", "heat_cool") and (cap.temperature or cap.temperature_range):
        low = _number(targets.get("heat")) if _manual_target(cfg, profile, "heat") else None
        high = _number(targets.get("cool")) if _manual_target(cfg, profile, "cool") else None
        metrics.append(("temperature", None, low, high, "control"))
    elif inactive:
        # Preserve an actual inactive endpoint for the previously chartable
        # channel even when a multi-mode appliance now reports only OFF.
        if cap.temperature or cap.temperature_range:
            metrics.append(("temperature", None, None, None, "control"))
        if cap.humidity:
            metrics.append(("humidity", None, None, None, "control"))

    result = []
    for metric, goal, low, high, target_kind in metrics:
        feedback_metric = "humidity" if metric == "mold" else metric
        provenance = measured.get(feedback_metric + "_provenance", {})
        selected_ids = _sources(provenance.get("source_ids")) if isinstance(provenance, dict) else []
        if not selected_ids:
            selected_ids = _sources(measured.get(feedback_metric + "_selected_entities"))
        if not selected_ids:
            selected_ids = _sources([measured.get(feedback_metric + "_entity")])
        source_ids = (_sources(provenance.get("contributor_ids"))
                      if isinstance(provenance, dict) and "contributor_ids" in provenance
                      else selected_ids)
        value = _number(measured.get(feedback_metric))
        context: dict[str, Any] = {"physical": list(spec.source_entities),
                                   "device": spec.source_device_id,
                                   "selected_feedback": selected_ids}
        if metric == "mold" or target_kind == "derived_room_rh":
            humidity = humidity or {}
            if humidity.get("target_ready") is not True:
                getattr(manager, "_control_trend_requests", {}).get(spec.identifier, {}).pop(metric, None)
                continue
            context["mold"] = {key: humidity.get(key) for key in (
                "calibration_factor", "temperature_entities", "humidity_entities", "weather_entities")}
            if metric == "mold":
                value = (_number(humidity.get("control_measurement"), 0, 100)
                         if humidity.get("target_ready") is True else None)
        # A configured setpoint can still be read between room sensor reports.
        # Use the selected chart's identity only for a target-only observation.
        # Derived targets continue to require the inputs that calculate them.
        target_only = value is None and metric != "mold" and target_kind == "control" and bool(selected_ids)
        if target_only:
            source_ids = selected_ids
        elif value is None or metric != "mold" and not source_ids:
            getattr(manager, "_control_trend_requests", {}).get(spec.identifier, {}).pop(metric, None)
            continue
        # Selected source IDs belong to the exact feedback mean. A PID sample
        # computed against an earlier selection never supplies a later request.
        point_demand = demand
        if evaluation is not None and (
                evaluation.get("metric") != feedback_metric
                or _sources(evaluation.get("source_ids")) != source_ids
                or _number(evaluation.get("target")) != (
                    _number(targets.get("humidity")) if metric == "mold" else goal)):
            point_demand = None
        request_context = {**context, "metric": metric, "mode": mode,
                           "profile": profile, "target": goal, "low": low, "high": high,
                           "feedback": source_ids, "target_kind": target_kind,
                           "primary": cap.primary, "fan": cap.fan_entity,
                           "native_modes": list(cap.modes)}
        point_demand, demand_at = _request(
            manager, spec, metric, cfg, request_context,
            candidate=point_demand, fresh=(evaluation is not None or bool(reason)),
            now=now,
        ) if method == "pid" and not reason and not target_only else (None, None)
        if target_only:
            getattr(manager, "_control_trend_requests", {}).get(spec.identifier, {}).pop(metric, None)
        if fresh_status and point_demand is not None and (
                demand != point_demand or status.get("pid_control_metric") != feedback_metric
                or _number(status.get("pid_control_target")) != (
                    _number(targets.get("humidity")) if metric == "mold" else goal)):
            # A late final status cannot introduce demand calculated against
            # an earlier target or sensor set. Only the calculation hook seeds
            # the request cache; statuses can confirm that exact recent value.
            getattr(manager, "_control_trend_requests", {}).get(spec.identifier, {}).pop(metric, None)
            point_demand, demand_at = None, None
        point = {
            "target": None if reason else goal,
            "target_low": None if reason else low,
            "target_high": None if reason else high,
            "measured": value, "demand_percent": point_demand,
            "demand_reported_at": demand_at,
            **output, "profile": profile,
            "mode": "off" if cfg.get("requested_mode") == "off" or method == "off" else mode,
            "control_mode": method,
            "status": status.get("status"),
            "target_unavailable_reason": reason or (
                (humidity or {}).get("target_unavailable_reason")
                if metric in ("humidity", "mold") else None),
        }
        if target_only:
            point.update(output_percent=None, output_reported_at=None)
        result.append({
            "controller_id": spec.identifier, "area_id": spec.area_id, "name": spec.name,
            "source_entity_ids": list(spec.source_entities), "metric": metric,
            "basis": _BASES[metric], "unit": _UNITS[metric],
            "feedback_source_ids": source_ids, "target_kind": target_kind,
            "context_id": hashlib.sha256(json.dumps(context, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()[:32],
            "point": point,
        })
    requests = getattr(manager, "_control_trend_requests", {}).get(spec.identifier, {})
    for metric in set(requests) - {item["metric"] for item in result}:
        requests.pop(metric, None)
    return result


def capture(manager: Any, *, spec: Any = None, now: float | None = None,
            **evidence: Any) -> bool:
    """Append only current observations after restoration; reads never write."""
    if (not getattr(manager, "_active", False)
            or not getattr(manager, "_environment_restored", False)
            or getattr(manager, "_stopping", False)
            or is_stopping(manager.hass) or getattr(manager.hass, "is_stopping", False)):
        return False
    journal = getattr(getattr(manager, "_environment_history", None), "control", None)
    if journal is None:
        return False
    if now is None:
        clock = getattr(getattr(manager, "equipment", None), "clock", None)
        now = clock() if callable(clock) else time.time()
    if _number(now, 0, 1e13) is None:
        return False
    if spec is None:
        specs = model.specs(manager)
        manager._control_trend_specs = {item.identifier: item for item in specs}
        requests = getattr(manager, "_control_trend_requests", {})
        for identifier in set(requests) - set(manager._control_trend_specs):
            requests.pop(identifier, None)
        observations = []
        for item in specs:
            try:
                observations.extend(_observations(manager, item, now=now))
            except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
                # A malformed/temporarily incomplete controller is an absent
                # observation. Reconciliation closes, never fills, its history.
                requests.pop(item.identifier, None)
                continue
        return journal.reconcile(observations, now=now)
    known = getattr(manager, "_control_trend_specs", {})
    if known.get(spec.identifier) != spec:
        return False  # Retired output reconciliation is not an active chart.
    try:
        observations = _observations(manager, spec, now=now, **evidence)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        getattr(manager, "_control_trend_requests", {}).pop(spec.identifier, None)
        return journal.pause(spec.identifier, now=now)
    if not observations:
        getattr(manager, "_control_trend_requests", {}).pop(spec.identifier, None)
        return journal.pause(spec.identifier, now=now)
    return journal.reconcile_controller(spec.identifier, observations, now=now)

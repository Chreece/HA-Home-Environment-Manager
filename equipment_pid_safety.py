"""Fresh, directional target limits for managed automatic output.

This is a limit on requested effort, never a new physical power permission.
Native OFF still passes the existing ownership, dwell and defrost checks.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import equipment_model as model
from .pid_math import finite, quantize_target, target_to_unit


def condition(runtime: Any, spec: Any, cap: Any,
              mode: str | None = None, *,
              include_automatic: bool = False) -> dict | None:
    """Read the exact command direction against the current room measurement.

None means this is not a supported direction. The default remains the PID
cutoff; command checks also opt into Automatic's native-state hysteresis.
Missing feedback has needed=None, which cannot authorize active output.
"""
    cfg = model.settings(runtime.manager, spec)
    method = cfg.get("control_mode")
    if method != "pid" and not (include_automatic and method == "automatic"):
        return None
    native = runtime.hass.states.get(cap.primary)
    plan = model.plan_for(runtime.manager, spec)
    targets = model.targets(runtime.manager, spec, cap, cfg, plan)
    measured = runtime.measurements(spec, cap)
    if mode is None:
        mode = cfg.get("requested_mode")
        if mode is None and native is not None and native.state in ("heat", "cool", "dry"):
            # Stop the OLD running direction before choosing an opposite one.
            mode = native.state
        if mode is None:
            from .dry_mode import automatic_mode
            room = model.room_config(runtime.manager, spec)
            mode = automatic_mode(
                cap, native, measured, targets,
                dedicated_dry=room.get("dry_climate_entity") == cap.primary,
                pid=method == "pid",
            )
        if mode is None:
            single = set(cap.modes) - {"off"}
            if len(single) == 1:
                mode = next(iter(single))
    if cap.domain == "humidifier" or mode == "dry":
        metric, increasing = "humidity", bool(cap.humidifying)
        target = finite(targets.get("humidity"), 0, 100)
        value = finite(measured.get(metric), 0, 100)
    elif mode in ("heat", "cool"):
        metric, increasing = "temperature", mode == "heat"
        target = finite(targets.get(mode), -60, 85)
        value = finite(measured.get(metric), -60, 85)
    elif method == "automatic" and cap.domain == "climate" and mode in ("heat_cool", "auto"):
        metric = "temperature"
        value = finite(measured.get(metric), -60, 85)
        heat, cool = (finite(targets.get(key), -60, 85) for key in ("heat", "cool"))
        increasing = value is not None and heat is not None and value < heat
        target = (heat if increasing else cool) if None not in (heat, cool) and heat < cool else None
    else:
        return None
    needed = None if (target is None or value is None
                      or model.automatic_profile_reason(cfg, plan)) else (
        value < target if increasing else value > target
    )
    mold_inhibit = bool(
        cap.domain == "humidifier" and cap.humidifying
        and hasattr(model, "humidity_demand")
        and model.humidity_demand(runtime.manager, spec, cap, cfg, plan).get("mold_protection_required") is True
    )
    if mold_inhibit:
        needed = False
    if method == "automatic" and needed is not None and not mold_inhibit:
        # Match tick's hysteresis at the LAST dispatch boundary. An OFF
        # device needs a full start gap; running output may remain inside
        # the opposite edge. Cached tick measurements cannot authorize ON.
        running = bool(native is not None and (
            native.state == mode if cap.domain == "climate" else
            finite(native.state, .000001, 100) is not None
            if cap.domain in ("number", "input_number") else native.state == "on"
        ))
        band = .3 if metric == "temperature" else 2
        error = target - value if increasing else value - target
        needed = (None if native is None or native.state in ("unknown", "unavailable")
                  else error > (-band if running else band))
    return {"mode": mode, "metric": metric, "measured": value,
            "target": target, "increasing": increasing, "needed": needed}


def reducing_command(runtime: Any, cap: Any, service: str,
                     data: dict, mode: str) -> bool:
    """Recognize a smaller physical request without relying on a room profile."""
    entity = (cap.fan_entity or cap.primary) if service == "set_percentage" else cap.primary
    native = runtime.hass.states.get(entity)
    if native is None or native.state in ("off", "unknown", "unavailable"):
        return False
    attrs = native.attributes
    if service == "set_value" and cap.domain in ("number", "input_number"):
        requested, actual = finite(data.get("value"), 0, 100), finite(native.state, 0, 100)
        increasing = True
    elif service == "set_percentage":
        requested, actual = finite(data.get("percentage"), 0, 100), finite(attrs.get("percentage"), 0, 100)
        increasing = True
    elif (service == "set_temperature" and set(data) == {"temperature"}
          and mode in ("heat", "cool") and native.state == mode):
        requested = finite(data.get("temperature"), -100, 250)
        actual = finite(attrs.get("temperature"), -100, 250)
        increasing = mode == "heat"
    elif service == "set_humidity" and (cap.domain == "humidifier" or mode == native.state == "dry"):
        requested, actual = finite(data.get("humidity"), 0, 100), finite(attrs.get("humidity"), 0, 100)
        increasing = bool(cap.humidifying)
    else:
        return False
    return bool(requested is not None and actual is not None and (
        requested < actual if increasing else requested > actual
    ))


def stopping_command(service: str, data: dict) -> bool:
    """Recognize an actual OFF payload, not the output's current mode."""
    return bool(service == "turn_off"
                or service == "set_hvac_mode" and data.get("hvac_mode") == "off"
                or service == "set_percentage" and data.get("percentage") == 0
                or service == "set_value" and data.get("value") == 0)


def command_profile_reason(runtime: Any, spec: Any, cap: Any, service: str,
                           data: dict, *, mode: str, automatic: bool,
                           stop_target: bool = False) -> str | None:
    """Unknown Home/Away cannot authorize an implicit automatic power increase."""
    if not automatic or stop_target or stopping_command(service, data):
        return None
    reason = model.automatic_profile_reason(
        model.settings(runtime.manager, spec), model.plan_for(runtime.manager, spec),
    )
    return reason if reason and not reducing_command(runtime, cap, service, data, mode) else None


def command_allowed(runtime: Any, spec: Any, cap: Any, service: str,
                    data: dict, *, mode: str, automatic: bool,
                    power: bool = False, stop_target: bool = False) -> bool:
    """Do not start, boost or repeat a satisfied direction, including at yields."""
    if not automatic or stop_target or stopping_command(service, data):
        return True
    if command_profile_reason(
        runtime, spec, cap, service, data, mode=mode, automatic=automatic,
    ):
        return False
    if (model.automatic_profile_reason(model.settings(runtime.manager, spec),
                                       model.plan_for(runtime.manager, spec))
            and reducing_command(runtime, cap, service, data, mode)):
        return True
    current = condition(runtime, spec, cap, mode, include_automatic=True)
    if current is None or current["needed"] is True:
        return True
    if (model.settings(runtime.manager, spec).get("control_mode") == "automatic"
            and reducing_command(runtime, cap, service, data, mode)):
        return True
    if current["needed"] is None or power:
        return False
    # Setpoint-only authorization cannot turn native power OFF. Permit only
    # an unboosted goal (or a still less demanding target) to remove old trim.
    if model.permission(runtime.manager, spec, cap)[1]:
        return False
    native = runtime.hass.states.get(cap.primary)
    if native is None:
        return False
    if service == "set_humidity" and current["metric"] == "humidity":
        requested = finite(data.get("humidity"), 0, 100)
        goal = round(current["target"])
        actual = finite(native.attributes.get("humidity"), 0, 100)
    elif (service == "set_temperature" and current["metric"] == "temperature"
          and set(data) == {"temperature"}):
        attrs = native.attributes
        unit = attrs.get("temperature_unit", "°C")
        goal = target_to_unit(current["target"], unit)
        requested = finite(data.get("temperature"), -100, 250)
        actual = finite(attrs.get("temperature"), -100, 250)
        step = finite(attrs.get("target_temp_step", .5), .01, 10)
        low = finite(attrs.get("min_temp"), -100, 250)
        high = finite(attrs.get("max_temp"), -100, 250)
        if None not in (goal, step, low, high):
            goal = quantize_target(goal, step, low, high)
    else:
        return False
    if goal is None or requested is None:
        return False
    # Existing native slew limits can require several smaller reductions.
    # Blocking every intermediate value above/below the goal would strand
    # the OLD boost forever. A strictly less demanding step is also safe.
    if current["increasing"]:
        return requested <= goal + .000001 or (
            actual is not None and requested < actual - .000001
        )
    return requested >= goal - .000001 or (
        actual is not None and requested > actual + .000001
    )


async def remember_cutoff(runtime: Any, spec: Any, current: dict | None) -> None:
    """Cancel logical PWM/I/wake state without fabricating a native OFF."""
    record = runtime._record(spec)
    if current is None or current["needed"] is not False:
        if record.pop("pid_target_cutoff", None) is not None:
            await runtime._save()
        return
    for name in ("_memory", "_profile_wake", "_fan_allocations", "_pid_offline_previews"):
        cache = getattr(runtime, name, None)
        if isinstance(cache, dict):
            cache.pop(spec.identifier, None)
    changed = record.pop("pid_checkpoint", None) is not None
    evidence = {"mode": current["mode"], "metric": current["metric"],
                "measured": current["measured"], "target": current["target"]}
    if record.get("pid_target_cutoff") != evidence:
        record["pid_target_cutoff"] = evidence
        changed = True
    if changed:
        await runtime._save()


def status_details(record: dict) -> dict:
    evidence = record.get("pid_target_cutoff")
    if not isinstance(evidence, dict):
        return {}
    metric = evidence.get("metric")
    bounds = (0, 100) if metric == "humidity" else (-60, 85)
    if (metric not in ("temperature", "humidity")
            or finite(evidence.get("target"), *bounds) is None
            or finite(evidence.get("measured"), *bounds) is None):
        return {}
    return {"demand_percent": 0.0, "pid_target_reached": True,
            "pid_control_metric": evidence["metric"],
            "pid_control_target": evidence["target"],
            "pid_control_measurement": evidence["measured"],
            "pid_pwm_state": "target_reached"}


async def suppress_obsolete_pending(runtime: Any, spec: Any,
                                    pending: dict) -> bool:
    """Stop resending obsolete PID effort without inventing an acknowledgement.

An issued setpoint can yield to a protective OFF of an already-owned output;
its original command/attempt ledger remains available for late feedback.
An unconfirmed ON retains its journal and uses the existing read-only
reconciliation workflow. An interrupted/uncertain dispatch is never cleared.
"""
    context = pending.get("retry_context")
    record = runtime._record(spec)
    if (record.get("pending") is not pending
            or pending.get("phase") != "commanded"
            or not isinstance(context, dict)
            or context.get("automatic") is not True
            or context.get("mode") == "off"
            or pending.get("stop_target") or pending.get("stop_finish")
            or not runtime._current_spec(spec) or not runtime._identity_ok(spec)):
        return False
    cap = model.capabilities(runtime.manager, spec)
    if cap is None or pending.get("entity") not in spec.source_entities:
        return False
    current = condition(runtime, spec, cap, context.get("mode"))
    if current is None or current["needed"] is not False:
        return False
    if command_allowed(
        runtime, spec, cap, pending.get("service"), pending.get("data", {}),
        mode=context.get("mode"), automatic=True,
        power=pending.get("power") is True,
    ):
        return False  # An unboosted/less-demanding correction still needs ACK.
    from .equipment_setpoint_sequence import retry_settings_match
    if not retry_settings_match(context.get("settings"), model.settings(runtime.manager, spec)):
        return False
    native = runtime.hass.states.get(pending["entity"])
    if native is None or native.state in ("unknown", "unavailable"):
        return False
    await remember_cutoff(runtime, spec, current)
    # Settings, demand or the original journal may change during persistence.
    cap = model.capabilities(runtime.manager, spec)
    current = condition(runtime, spec, cap, context.get("mode")) if cap else None
    if (record.get("pending") is not pending
            or current is None or current["needed"] is not False
            or not runtime._current_spec(spec) or not runtime._identity_ok(spec)
            or not retry_settings_match(context.get("settings"), model.settings(runtime.manager, spec))):
        return False
    owned_modulation = (
        cap.domain in ("number", "input_number")
        and pending.get("service") == "set_value"
        and pending.get("entity") == cap.primary
        and isinstance(record.get("power", {}).get(cap.primary), dict)
        and finite(native.state, .000001, 100) is not None
        and finite(pending.get("data", {}).get("value"), .000001, 100) is not None
    )
    if (owned_modulation or (
            pending.get("service") in ("set_temperature", "set_humidity", "set_fan_mode",
                                       "set_preset_mode", "set_percentage",
                                       "set_swing_mode", "set_swing_horizontal_mode")
            and not pending.get("power"))):
        # A genuinely different command may already have superseded an older
        # failed target. Keep that evidence as bounded history while making
        # the most recent command's ORIGINAL budget authoritative. Otherwise
        # two different unacknowledged adjustments could block OFF forever.
        retained = record.get("unconfirmed_native_target")
        if retained is not None and not isinstance(retained, dict):
            return False
        if retained is not None and any(
            retained.get(key) != pending.get(key)
            for key in ("entity", "service", "data", "expected")
        ):
            record["previous_unconfirmed_native_target"] = deepcopy(retained)
        retained = deepcopy(pending)
        retained["pid_target_satisfied"] = True
        record["unconfirmed_native_target"] = retained
        record["pending"] = None
        await runtime._save()
        return True
    if pending.get("power") and pending.get("output_on") is True:
        if not isinstance(record.get("automatic_continue_requested"), dict):
            record["automatic_continue_requested"] = {
                "at": runtime.clock(), "method": "pid",
                "awaiting_physical_verification": True,
            }
            await runtime._save()
        runtime._status(spec, "awaiting_physical_acknowledgement",
                        reason="pid_target_reached_original_on_unconfirmed",
                        command_attempts=pending.get("attempts"),
                        **status_details(record))
        return True
    return False

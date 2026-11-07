"""Optional full-demand targets and bounded PID target acknowledgements.

The native mode/power journal remains the actuator authority. A failed target
is only a setpoint observation; it must neither prove power ON/OFF nor prevent
the independent binary controller from operating after its bounded attempts.
"""
from __future__ import annotations

from copy import deepcopy

from .pid_math import finite

OPTION = "native_full_output"
BUDGET = "native_target_attempt_budget"
PREVIOUS_BUDGET = "previous_native_target_attempt_budget"
MARKER = "binary_pid_target"
FULL_MARKER = "native_full_output_target"
DEFERRED = "deferred_native_full_output_target"
ATTEMPT_LIMIT = 3
FEEDBACK_SECONDS = 60.0


def _identity_proof(runtime, spec):
    from .device_activation import authority_context, authorization_matches
    # A legacy explicit power grant may not have saved _native_authorization.
    # Bind this new journal to the real registry identities anyway; permission
    # remains the separate live grant checked by request_context().
    proof = authority_context(runtime.manager, spec)
    return proof if authorization_matches(proof, proof) else None


def _identity_current(runtime, spec, context):
    if not runtime._current_spec(spec) or not runtime._identity_ok(spec):
        return False
    proof = context.get("identity")
    if proof is None:
        return False
    from .device_activation import authority_context, authorization_matches
    return authorization_matches(proof, authority_context(runtime.manager, spec))


def enabled(cfg) -> bool:
    """Preserve the existing full-output behavior for unsaved installations."""
    return cfg.get(OPTION, True) is True


def full_request(cap, attributes, mode):
    """Return only an actual advertised native actuator endpoint."""
    from . import equipment_model as model
    if cap is None or "off" not in cap.modes or mode not in cap.modes:
        return None
    if cap.domain == "climate" and mode in ("heat", "cool"):
        feature, field, low_key, high_key = model.TEMP, "temperature", "min_temp", "max_temp"
        low, high = finite(attributes.get(low_key), -30, 140), finite(attributes.get(high_key), -29, 150)
        high_demand = mode == "heat"
    elif (cap.domain == "climate" and mode == "dry"
          or cap.domain == "humidifier" and mode == ("auto" if cap.humidifying else "dry")):
        feature, field, low_key, high_key = model.HUMIDITY, "humidity", "min_humidity", "max_humidity"
        low, high = finite(attributes.get(low_key), 0, 100), finite(attributes.get(high_key), 0, 100)
        high_demand = cap.humidifying
    else:
        return None
    if cap.domain == "climate":
        try:
            flags = int(attributes.get("supported_features", 0))
        except (TypeError, ValueError, OverflowError):
            return None
        if not flags & feature:
            return None
    if low is None or high is None or low >= high:
        return None
    return {"service": "set_" + field, "data": {field: high if high_demand else low}}


def _direction(manager, spec, cfg, cap, state):
    from .equipment_setpoint_sequence import _direction as selected_direction
    mode = selected_direction(manager, spec, cfg, cap, state)
    return "auto" if cap.domain == "humidifier" and mode == "humidify" else mode


def configuration_modes(manager, spec) -> tuple[str, ...]:
    """Canonical directions with a proven native full-output target endpoint."""
    from .equipment_setpoint_sequence import _configuration_evidence
    cap, attributes = _configuration_evidence(manager, spec)
    if cap is None:
        return ()
    supported = {
        "humidify" if cap.domain == "humidifier" and cap.humidifying else mode
        for mode in cap.modes if full_request(cap, attributes, mode) is not None
    }
    return tuple(mode for mode in ("heat", "cool", "dry", "humidify") if mode in supported)


def configuration_supported(manager, spec) -> bool:
    return bool(configuration_modes(manager, spec))


def control_supported(manager, spec, *, cached=False) -> bool:
    from . import equipment_model as model
    from .equipment_setpoint_sequence import _configuration_evidence
    cfg = model.settings(manager, spec)
    if cfg.get("control_mode") not in ("automatic", "pid"):
        return False
    if cached:
        cap, attributes = _configuration_evidence(manager, spec)
    else:
        cap = model.capabilities(manager, spec)
        state = manager.hass.states.get(cap.primary) if cap is not None else None
        attributes = state.attributes if state is not None else {}
        if not model.sources_available(manager, spec):
            return False
    if cap is None or cap.primary not in spec.source_entities:
        return False
    mode = _direction(manager, spec, cfg, cap, manager.hass.states.get(cap.primary))
    return bool(full_request(cap, attributes, mode) is not None
                and model.permission(manager, spec, cap)[1])


def request_context(runtime, spec, cap, mode, service, data, *, attributes=None, pid_only=True):
    """Bind a PID full-demand request to the selected physical controller."""
    from . import equipment_model as model
    cfg = model.settings(runtime.manager, spec)
    if (cfg.get("control_mode") not in (("pid",) if pid_only else ("automatic", "pid")) or cap is None
            or cap.primary not in spec.source_entities
            or not model.permission(runtime.manager, spec, cap)[1]):
        return None
    state = runtime.hass.states.get(cap.primary)
    attrs = attributes if attributes is not None else (state.attributes if state is not None else {})
    request = full_request(cap, attrs, mode)
    if request is None or request != {"service": service, "data": data}:
        return None
    identity = _identity_proof(runtime, spec)
    if identity is None:
        return None
    return {
        "entity_id": cap.primary, "area_id": spec.area_id,
        "source_device_id": spec.source_device_id, "source_entity_ids": sorted(set(spec.source_entities)),
        "identity": identity,
        "mode": mode, "service": service, "requested": deepcopy(data),
    }


def same_context(budget, context) -> bool:
    return isinstance(budget, dict) and isinstance(context, dict) and budget.get("context") == context


def budget_for(runtime, spec, context):
    budget = runtime._record(spec).get(BUDGET)
    return budget if same_context(budget, context) else None


def exhausted(runtime, spec, context) -> bool:
    budget = budget_for(runtime, spec, context)
    return bool(budget and budget.get("state") == "unconfirmed"
                and type(budget.get("attempts")) is int and budget["attempts"] >= ATTEMPT_LIMIT)


def may_attempt(runtime, spec, context) -> bool:
    budget = budget_for(runtime, spec, context)
    if not budget or budget.get("state") == "confirmed":
        return True
    count = budget.get("attempts")
    last = finite(budget.get("last_attempt_at"), 0, runtime.clock())
    return bool(type(count) is int and 0 <= count < ATTEMPT_LIMIT
                and last is not None and runtime.clock() - last >= FEEDBACK_SECONDS)


def reserve(runtime, spec, pending, context):
    """Reserve durably with the command; a proven pre-dispatch abort restores it."""
    record = runtime._record(spec)
    previous = deepcopy(record.get(BUDGET))
    old = budget_for(runtime, spec, context)
    # Actual matching feedback resolves a failed-attempt episode. A later
    # genuine target reset may be corrected again; a mere power cycle cannot
    # renew an unconfirmed/exhausted budget.
    continuing = bool(old and old.get("state") != "confirmed")
    count = old.get("attempts", 0) if continuing else 0
    if type(count) is not int or count < 0 or count >= ATTEMPT_LIMIT:
        return None
    pending[MARKER] = deepcopy(context)
    pending["attempts"] = count + 1
    if continuing and finite(old.get("when"), 0, runtime.clock()) is not None:
        pending["when"] = old["when"]
    record[BUDGET] = {
        "version": 1, "context": deepcopy(context), "attempts": count + 1,
        "when": pending["when"], "last_attempt_at": runtime.clock(),
        "state": "awaiting_feedback", "phase": "intent",
    }
    if isinstance(previous, dict) and not same_context(previous, context):
        # Keep the earlier evidence durable during reservation. It becomes
        # the previous journal only once the new service is actually called;
        # a proven pre-dispatch abort restores the original budget instead.
        record[BUDGET]["superseded_budget"] = previous
    return {"previous": previous, "reserved": record[BUDGET]}


def rollback(runtime, spec, reservation):
    record = runtime._record(spec)
    if reservation and record.get(BUDGET) is reservation["reserved"]:
        if reservation["previous"] is None:
            record.pop(BUDGET, None)
        else:
            record[BUDGET] = reservation["previous"]


def record_dispatch(runtime, spec, pending):
    context = pending.get(MARKER)
    if not isinstance(context, dict):
        return
    record = runtime._record(spec)
    budget = budget_for(runtime, spec, context)
    if budget is None:
        budget = record[BUDGET] = {"version": 1, "context": deepcopy(context)}
    budget.update(attempts=pending["attempts"], when=pending["when"],
                  last_attempt_at=pending.get("last_attempt_at", runtime.clock()),
                  state="awaiting_feedback", phase=pending.get("phase"))
    if pending.get("phase") == "commanded":
        previous = budget.pop("superseded_budget", None)
        if isinstance(previous, dict):
            record[PREVIOUS_BUDGET] = previous


async def adopt_pending(runtime, spec):
    """Recognize an old full-demand dispatch without rewriting its evidence."""
    from . import equipment_model as model
    record = runtime._record(spec)
    pending = record.get("pending")
    if (not isinstance(pending, dict) or pending.get("power") is True
            or pending.get("stop_target") or pending.get("stop_finish")
            or pending.get("service") not in ("set_temperature", "set_humidity")):
        return
    if isinstance(pending.get(MARKER), dict):
        if budget_for(runtime, spec, pending[MARKER]) is None:
            record_dispatch(runtime, spec, pending)
            await runtime._save()
        return
    if isinstance(pending.get(FULL_MARKER), dict):
        return
    retry = pending.get("retry_context")
    if (pending.get("phase") != "commanded" or not isinstance(retry, dict)
            or type(pending.get("attempts")) is not int or pending["attempts"] < 1
            or finite(pending.get("when"), 0, runtime.clock()) is None
            or finite(pending.get("last_attempt_at"), 0, runtime.clock()) is None
            or retry.get("automatic") is not True
            or retry.get("settings", {}).get("control_mode") not in ("automatic", "pid")
            or pending.get("entity") not in spec.source_entities
            or not runtime._current_spec(spec) or not runtime._identity_ok(spec)):
        return
    try:
        cap = model.Capabilities(**record["capabilities"])
    except (KeyError, TypeError, ValueError):
        return
    baseline = record.get("baseline", {}).get(pending["entity"])
    attributes = baseline.get("attributes", {}) if isinstance(baseline, dict) else {}
    context = request_context(runtime, spec, cap, retry.get("mode"), pending["service"],
                              pending.get("data", {}), attributes=attributes, pid_only=False)
    if (context is None or pending.get("expected") != {"attributes": pending.get("data")}
            or not _identity_current(runtime, spec, context)):
        return
    pending[FULL_MARKER] = context
    if retry["settings"]["control_mode"] == "pid":
        pending[MARKER] = context
        record_dispatch(runtime, spec, pending)
    await runtime._save()


async def observe_feedback(runtime, spec):
    """Accept matching target attributes only; leave power and other changes alone."""
    from .equipment_runtime import matches
    from .equipment_setpoint_sequence import native_human_changed
    record = runtime._record(spec)
    deferred = record.get(DEFERRED)
    deferred_context = deferred.get(FULL_MARKER) if isinstance(deferred, dict) else None
    if isinstance(deferred_context, dict) and _identity_current(runtime, spec, deferred_context):
        entity = deferred_context.get("entity_id")
        state = runtime.hass.states.get(entity)
        if (state is not None and state.state not in ("unknown", "unavailable")
                and not native_human_changed(runtime, spec, entity, state)
                and matches(state, deferred.get("expected", {}))):
            record["last_full_output_target"] = {**deepcopy(deferred), "confirmed_at": runtime.clock()}
            record.pop(DEFERRED, None)
            baseline = record.get("baseline", {}).get(entity)
            if isinstance(baseline, dict) and isinstance(baseline.get("attributes"), dict):
                baseline["attributes"].update({key: deepcopy(state.attributes[key])
                    for key in deferred_context.get("requested", {}) if key in state.attributes})
            await runtime._save()
    budget = record.get(BUDGET)
    context = budget.get("context") if isinstance(budget, dict) else None
    if (not isinstance(context, dict) or context.get("entity_id") not in spec.source_entities
            or context.get("area_id") != spec.area_id
            or context.get("source_device_id") != spec.source_device_id
            or context.get("source_entity_ids") != sorted(set(spec.source_entities))
            or not _identity_current(runtime, spec, context)):
        return
    entity = context["entity_id"]
    state = runtime.hass.states.get(entity)
    expected = {"attributes": context["requested"]}
    if (state is None or state.state in ("unknown", "unavailable")
            or native_human_changed(runtime, spec, entity, state)):
        return
    if matches(state, expected) and budget.get("state") != "confirmed":
        budget.update(state="confirmed", confirmed_at=runtime.clock())
        pending = record.get("pending")
        if not (isinstance(pending, dict) and pending.get(MARKER) == context):
            baseline = record.get("baseline", {}).get(entity)
            if isinstance(baseline, dict) and isinstance(baseline.get("attributes"), dict):
                baseline["attributes"].update({key: deepcopy(state.attributes[key])
                                               for key in context["requested"] if key in state.attributes})
        await runtime._save()
    elif (budget.get("state") not in ("confirmed", "unconfirmed")
          and budget.get("phase") == "commanded"
          and type(budget.get("attempts")) is int and budget["attempts"] >= ATTEMPT_LIMIT
          and (last := finite(budget.get("last_attempt_at"), 0, runtime.clock())) is not None
          and runtime.clock() - last >= FEEDBACK_SECONDS
          and not (isinstance(record.get("pending"), dict)
                   and record["pending"].get(MARKER) == context)):
        budget["state"] = "unconfirmed"
        await runtime._save()


async def handle_pending(runtime, spec, pending) -> bool:
    """Yield only a known optional target, retaining its exact attempt history."""
    from . import equipment_model as model
    from .equipment_setpoint_sequence import native_human_changed, pending_shutdown_reason
    record = runtime._record(spec)
    context = pending.get(MARKER) or pending.get(FULL_MARKER)
    if (record.get("pending") is not pending or not isinstance(context, dict)
            or pending.get("phase") != "commanded" or pending.get("power") is True
            or pending.get("stop_target") or pending.get("stop_finish")
            or not _identity_current(runtime, spec, context)
            or not model.sources_available(runtime.manager, spec)):
        return False
    state = runtime.hass.states.get(pending.get("entity"))
    if state is None or state.state in ("unknown", "unavailable"):
        return False
    if native_human_changed(runtime, spec, pending["entity"], state):
        await runtime._pause(spec, "physical_manual_override")
        return True
    cfg = model.settings(runtime.manager, spec)
    supply = cfg.get("power_switch_entity")
    if supply:
        supplied = runtime.hass.states.get(supply)
        upstream = record.get("upstream", {})
        if supplied is None or supplied.state != "on" or upstream.get("paused") or upstream.get("pending"):
            return False
    cap = model.capabilities(runtime.manager, spec)
    if cap is None:
        return False
    quiet = getattr(runtime, "_quiet_fan_correction_required", None)
    quiet_due = callable(quiet) and quiet(spec, cap, cfg, model.plan_for(runtime.manager, spec))
    budget = budget_for(runtime, spec, context) if isinstance(pending.get(MARKER), dict) else None
    if budget is None:
        if enabled(cfg) and not quiet_due:
            return False
        # Automatic keeps its existing retry policy. Only move its known
        # optional target out of the serializer while a quiet fan correction
        # (or the disabled full-output preference) takes priority.
        record[DEFERRED] = deepcopy(pending)
        record["pending"] = None
        await runtime._save()
        return True
    attempts = pending.get("attempts")
    last = finite(pending.get("last_attempt_at"), 0, runtime.clock())
    done = (type(attempts) is int and attempts >= ATTEMPT_LIMIT and last is not None
            and runtime.clock() - last >= FEEDBACK_SECONDS)
    from .equipment_pid_safety import condition
    target = condition(runtime, spec, cap, context.get("mode"))
    defer = (not retry_live(runtime, spec, cap, pending, state)
             or quiet_due or target is not None and target["needed"] is False
             or pending_shutdown_reason(runtime, spec, cap, pending) is not None)
    if not done and not defer:
        return False
    budget.update(attempts=attempts, when=pending["when"], last_attempt_at=last,
                  phase="commanded", state="unconfirmed" if done else "deferred",
                  journal=deepcopy(pending), deferred_at=runtime.clock())
    legacy = record.get("unconfirmed_native_target")
    if isinstance(legacy, dict) and legacy.get(MARKER) == context:
        record["previous_unconfirmed_native_target"] = deepcopy(legacy)
        record.pop("unconfirmed_native_target", None)
    record["pending"] = None
    request = record.get("automatic_continue_requested")
    if isinstance(request, dict) and not record.get("restart_power_verification"):
        record.pop("automatic_continue_requested", None)
    await runtime._save()
    return True


async def resume_deferred(runtime, spec, cap, mode, service, data):
    """Resume an Automatic target's exact journal after its quiet correction.

    None means there is no matching retained request. False means its original
    feedback interval or live conditions still defer it without blocking other
    control. True means the existing serializer now owns that same request.
    """
    from . import equipment_model as model
    record = runtime._record(spec)
    pending = record.get(DEFERRED)
    context = pending.get(FULL_MARKER) if isinstance(pending, dict) else None
    cfg = model.settings(runtime.manager, spec)
    if (cfg.get("control_mode") != "automatic" or not isinstance(context, dict)
            or context != request_context(runtime, spec, cap, mode, service, data, pid_only=False)
            or not _identity_current(runtime, spec, context)):
        return None
    state = runtime.hass.states.get(cap.primary)
    quiet = getattr(runtime, "_quiet_fan_correction_required", None)
    last = finite(pending.get("last_attempt_at"), 0, runtime.clock())
    if (record.get("pending") or record.get("paused") or pending.get("phase") != "commanded"
            or last is None or runtime.clock() - last < FEEDBACK_SECONDS
            or not retry_live(runtime, spec, cap, pending, state)
            or callable(quiet) and quiet(spec, cap, cfg, model.plan_for(runtime.manager, spec))):
        return False
    resumed = deepcopy(pending)
    # A sleep transition can change the room profile while leaving this
    # exact full-demand endpoint unchanged. Preserve the prior journal and
    # recheck the current profile through the ordinary retry gates; it does
    # not create attempt one or make the native target a power ACK.
    record["last_full_output_target"] = deepcopy(pending)
    resumed["retry_context"]["profile"] = model.profile_name(cfg, model.plan_for(runtime.manager, spec))
    record["pending"] = resumed
    record.pop(DEFERRED, None)
    await runtime._save()
    await runtime._retry_pending(spec, resumed, runtime.clock())
    return True


def verified_reconciliation(runtime, spec, pending, decision):
    """Keep a reconciled optional target's budget without claiming its ACK."""
    if not isinstance(pending, dict) or pending.get("power") or pending.get("stop_target") or pending.get("stop_finish"):
        return
    context = pending.get(MARKER)
    budget = budget_for(runtime, spec, context)
    if budget is None or decision not in ("confirmed", "verified"):
        return
    record_dispatch(runtime, spec, pending)
    budget.update(state="confirmed" if decision == "confirmed" else "deferred",
                  phase="commanded", journal=deepcopy(pending), reconciled_at=runtime.clock(),
                  reconciliation="native_target_ack" if decision == "confirmed" else "stable_native_state")


def retry_live(runtime, spec, cap, pending, state) -> bool:
    """A new target attempt needs the same running mode and live native bounds."""
    context = pending.get(MARKER) or pending.get(FULL_MARKER)
    if not isinstance(context, dict):
        return True
    from . import equipment_model as model
    if state is None or state.state != (context["mode"] if cap.domain == "climate" else "on"):
        return False
    if not enabled(model.settings(runtime.manager, spec)):
        return False
    return request_context(runtime, spec, cap, context["mode"], pending.get("service"),
                           pending.get("data", {}), pid_only=MARKER in pending) == context


def diagnostics(runtime, spec):
    """Allowlisted live feedback only; this serializer does not mutate control."""
    record = runtime.records.get(spec.identifier, {})
    budget = record.get(BUDGET) if isinstance(record, dict) else None
    context = budget.get("context") if isinstance(budget, dict) else None
    if (not isinstance(context, dict) or context.get("entity_id") not in spec.source_entities
            or context.get("area_id") != spec.area_id
            or context.get("source_device_id") != spec.source_device_id
            or context.get("source_entity_ids") != sorted(set(spec.source_entities))):
        return None
    if not _identity_current(runtime, spec, context):
        return None
    from . import equipment_model as model
    from .equipment_setpoint_sequence import _configuration_evidence
    cfg = model.settings(runtime.manager, spec)
    if cfg.get("control_mode") != "pid" or not enabled(cfg):
        return None
    cap, attributes = _configuration_evidence(runtime.manager, spec)
    if cap is None:
        return None
    mode = _direction(runtime.manager, spec, cfg, cap, runtime.hass.states.get(cap.primary))
    request = full_request(cap, attributes, mode)
    if request is None or request_context(runtime, spec, cap, mode, request["service"],
                                           request["data"], attributes=attributes) != context:
        return None
    entity = context["entity_id"]
    state = runtime.hass.states.get(entity)
    field = "humidity" if context.get("service") == "set_humidity" else "temperature"
    live = state is not None and state.state not in ("unknown", "unavailable")
    bounds = (0, 100) if field == "humidity" else (-100, 250)
    reported = finite(state.attributes.get(field), *bounds) if live else None
    done = budget.get("state") == "unconfirmed"
    pending = record.get("pending")
    same_pending = isinstance(pending, dict) and pending.get(MARKER) == context
    last = finite(budget.get("last_attempt_at"), 0, runtime.clock())
    return {
        "role": "binary_pid_full_demand", "entity_id": entity,
        "mode": context.get("mode"), "service": context.get("service"),
        "requested": deepcopy(context.get("requested", {})), "reported": {field: reported},
        "temperature_unit": state.attributes.get("temperature_unit") if live and field == "temperature" else None,
        "attempts": budget.get("attempts"), "attempt_limit": ATTEMPT_LIMIT,
        "state": budget.get("state"), "exhausted": done,
        "nonblocking": done and not same_pending,
        "next_retry_at": last + FEEDBACK_SECONDS if same_pending and last is not None and not done else None,
    }

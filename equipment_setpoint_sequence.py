"""Timed native setpoints around a binary heating/cooling power cycle.

The native mode remains the power acknowledgement. A temperature write never
proves that an appliance is OFF. A committed stop owns only the right to finish
that same OFF; it cannot adopt a running device or authorize another ON.
"""
from __future__ import annotations

import asyncio
import math
from copy import deepcopy

from .pid_math import finite

SETPOINT_GRACE_SECONDS = 30.0
_RECOVERABLE_PAUSES = frozenset((
    None, "restart_reconciliation_required", "physical_acknowledgement_missing",
    "native_command_failed_or_uncertain", "native_retry_intent_uncertain",
))


def wake_at(runtime, spec, deadline: float) -> None:
    """Schedule an ordinary locked evaluation, never an actuator callback."""
    if not callable(getattr(runtime, "schedule", None)):
        return
    wakes = getattr(runtime, "_setpoint_wakeups", None)
    if wakes is None:
        wakes = runtime._setpoint_wakeups = {}
    previous = wakes.get(spec.identifier)
    if previous is not None:
        if previous[0] == deadline and not previous[1].cancelled():
            return
        previous[1].cancel()
    delay = max(0.001, deadline - runtime.clock())

    def due():
        current = wakes.get(spec.identifier)
        if current is None or current[0] != deadline:
            return
        wakes.pop(spec.identifier, None)
        if not runtime._active or not runtime._ready:
            return
        task = getattr(runtime, "_tasks", {}).get(spec.identifier)
        if task is not None and not task.done():
            rerun = getattr(runtime, "_setpoint_rerun", None)
            if rerun is None:
                rerun = runtime._setpoint_rerun = set()
            rerun.add(spec.identifier)
        else:
            runtime.schedule()

    wakes[spec.identifier] = (deadline, asyncio.get_running_loop().call_later(delay, due))


def cancel_wakeups(runtime) -> None:
    for _deadline, handle in getattr(runtime, "_setpoint_wakeups", {}).values():
        handle.cancel()
    getattr(runtime, "_setpoint_wakeups", {}).clear()
    getattr(runtime, "_setpoint_rerun", set()).clear()


def _wait(runtime, spec, status, deadline, **details):
    runtime._status(
        spec, status,
        setpoint_wait_remaining_seconds=math.ceil(max(0, deadline - runtime.clock())),
        setpoint_wait_until=deadline,
        **details,
    )
    wake_at(runtime, spec, deadline)


async def startup_ready(runtime, spec, cap, state) -> bool:
    """Wait once per observed native ON, for every native setpoint path.

    A commanded ON gets its durable timestamp only when the native mode ACKs.
    Existing, already-running soft-control devices use observed ON history.
    Repeated target changes and an HA restart do not restart a completed grace.
    """
    if state is None or state.state in ("off", "unknown", "unavailable"):
        return False
    record, now = runtime._record(spec), runtime.clock()
    owned = record.get("power", {}).get(cap.primary)
    observed = record.get("native_power_observations", {}).get(cap.primary)
    stamps = []
    edge = finite(getattr(runtime, "_native_on_epoch", {}).get(cap.primary), 0, now)
    if edge is not None:
        stamps.append(edge)
    if isinstance(owned, dict):
        stamp = finite(owned.get("since"), 0, now)
        if stamp is not None:
            stamps.append(stamp)
    if isinstance(observed, dict) and observed.get("state") == "on":
        stamp = finite(observed.get("since"), 0, now)
        if stamp is not None:
            stamps.append(stamp)
    if not stamps:
        try:
            stamp = finite(state.last_changed.timestamp(), 0, now)
        except (AttributeError, TypeError, ValueError, OverflowError):
            stamp = None
        if stamp is None:
            history = record.setdefault("setpoint_startup_observations", {})
            previous = history.get(cap.primary)
            stamp = finite(previous, 0, now)
            if stamp is None:
                stamp = now
                history[cap.primary] = stamp
                await runtime._save()
        stamps.append(stamp)
    deadline = max(stamps) + SETPOINT_GRACE_SECONDS
    if now < deadline:
        _wait(runtime, spec, "native_setpoint_startup_grace", deadline,
              native_mode=state.state)
        return False
    return True


def supports_stop(cap, state) -> bool:
    """Only thermostatic binary HEAT/COOL has an opposite temperature limit."""
    return bool(
        cap.domain == "climate" and cap.temperature and "off" in cap.modes
        and state is not None and state.state in ("heat", "cool")
    )


def _opposite(state):
    low = finite(state.attributes.get("min_temp"), -30, 140)
    high = finite(state.attributes.get("max_temp"), -29, 150)
    if low is None or high is None or low >= high:
        return None
    return low if state.state == "heat" else high


def _valid(sequence, record, spec) -> bool:
    return bool(
        isinstance(sequence, dict) and sequence.get("version") == 1
        and sequence.get("entity") in spec.source_entities
        and sequence.get("entity") in record.get("sources", ())
        and sequence.get("source_device_id") == record.get("source_device_id")
        == spec.source_device_id
        and sequence.get("area") == record.get("area") == spec.area_id
        and sequence.get("mode") in ("heat", "cool")
        and finite(sequence.get("temperature"), -30, 150) is not None
        and finite(sequence.get("requested_at"), 0, 1e13) is not None
        and sequence.get("phase") in (
            "preparing", "waiting", "uncertain", "off_ready", "off_pending",
        )
        and type(sequence.get("owned")) is bool
        and (not sequence["owned"]
             or finite(sequence.get("owned_since"), 0, 1e13) is not None)
    )


def _associated(pending, sequence, *, target=False):
    return bool(
        isinstance(pending, dict)
        and pending.get("entity") == sequence["entity"]
        and pending.get("stop_sequence_at") == sequence["requested_at"]
        and (
            pending.get("stop_target") is True
            and pending.get("service") == "set_temperature"
            and pending.get("data") == {"temperature": sequence["temperature"]}
            and pending.get("expected") == {
                "attributes": {"temperature": sequence["temperature"]},
            }
            if target else pending.get("stop_finish") is True
            and pending.get("service") == "set_hvac_mode"
            and pending.get("data") == {"hvac_mode": "off"}
            and pending.get("power") is True
            and pending.get("expected") == {"state": "off"}
        )
    )


def _supply_ready(runtime, spec):
    from . import equipment_model as model
    record = runtime._record(spec)
    relay = record.get("upstream", {})
    supply = model.settings(runtime.manager, spec).get("power_switch_entity") or relay.get("entity")
    if not supply:
        return True
    state = runtime.hass.states.get(supply)
    return bool(state is not None and state.state == "on"
                and not relay.get("pending") and not relay.get("paused"))


def target_authorized(runtime, spec, cap, entity, data, expected) -> bool:
    """Validate the only non-OFF payload permitted by stop preparation."""
    from . import equipment_model as model
    record = runtime._record(spec)
    sequence = record.get("native_setpoint_stop")
    state = runtime.hass.states.get(entity)
    if not (_valid(sequence, record, spec) and sequence["phase"] == "preparing"
            and not sequence.get("invalidated_on_epoch")
            and entity == cap.primary == sequence["entity"]
            and supports_stop(cap, state) and state.state == sequence["mode"]
            and model.features(state) & model.TEMP
            and _opposite(state) == sequence["temperature"]
            and data == {"temperature": sequence["temperature"]}
            and expected == {"attributes": data}
            and _supply_ready(runtime, spec)):
        return False
    owned = record.get("power", {}).get(entity)
    if sequence["owned"]:
        edge = finite(getattr(runtime, "_native_on_epoch", {}).get(entity), 0, runtime.clock())
        return bool(isinstance(owned, dict)
                    and owned.get("since") == sequence["owned_since"]
                    and (edge is None or edge <= sequence["owned_since"])
                    and runtime._shutdown_allowed(spec, entity, {"state": "off"}))
    return bool(runtime._current_spec(spec)
                and model.permission(runtime.manager, spec, cap)[1])


def finish_authorized(runtime, spec, cap, entity) -> bool:
    """A committed leg can finish OFF even if its original demand changes."""
    from . import equipment_model as model
    record, now = runtime._record(spec), runtime.clock()
    sequence = record.get("native_setpoint_stop")
    state = runtime.hass.states.get(entity)
    if not (_valid(sequence, record, spec)
            and not sequence.get("invalidated_on_epoch")
            and sequence["phase"] in ("off_ready", "off_pending")
            and entity == cap.primary == sequence["entity"]
            and state is not None and state.state == sequence["mode"]
            and finite(sequence.get("off_not_before"), 0, now) is not None
            and _supply_ready(runtime, spec)):
        return False
    owned = record.get("power", {}).get(entity)
    if sequence["owned"]:
        edge = finite(getattr(runtime, "_native_on_epoch", {}).get(entity), 0, now)
        return bool(isinstance(owned, dict)
                    and owned.get("since") == sequence["owned_since"]
                    and (edge is None or edge <= sequence["owned_since"])
                    and runtime._shutdown_allowed(spec, entity, {"state": "off"}))
    return bool(runtime._current_spec(spec)
                and model.permission(runtime.manager, spec, cap)[1])


def mark_target_sent(runtime, spec, when):
    sequence = runtime._record(spec)["native_setpoint_stop"]
    sequence.update(phase="waiting", sent_at=when,
                    off_not_before=when + SETPOINT_GRACE_SECONDS)
    wake_at(runtime, spec, sequence["off_not_before"])


async def begin_stop(runtime, spec, cap, *, automatic, shutdown, policy_stop):
    """Called only after _power has verified the physical minimum-ON dwell."""
    from . import equipment_model as model
    record = runtime._record(spec)
    if record.get("native_setpoint_stop"):
        await progress_stop(runtime, spec)
        return False
    state = runtime.hass.states.get(cap.primary)
    value = _opposite(state)
    if value is None or not model.features(state) & model.TEMP:
        runtime._status(spec, "native_setpoint_shutdown_blocked",
                        reason="physical_capabilities_unavailable")
        return False
    if not await startup_ready(runtime, spec, cap, state):
        return False
    if record.get("pending") or record.get("paused"):
        return False
    owned = record.get("power", {}).get(cap.primary)
    sequence = {
        "version": 1, "entity": cap.primary,
        "source_device_id": record.get("source_device_id"), "area": record["area"],
        "mode": state.state, "temperature": value, "phase": "preparing",
        "requested_at": runtime.clock(), "owned": isinstance(owned, dict),
        "owned_since": owned.get("since") if isinstance(owned, dict) else None,
    }
    record["native_setpoint_stop"] = sequence
    # Send even if the last HA report already equals this endpoint: the user
    # requested a fresh shutdown target before the distinct 30-second OFF leg.
    sent = await runtime._send(
        spec, cap, cap.primary, "set_temperature", {"temperature": value},
        {"attributes": {"temperature": value}}, mode="off", automatic=automatic,
        shutdown=shutdown, policy_stop=policy_stop, stop_target=True,
    )
    if sent:
        _wait(runtime, spec, "native_setpoint_shutdown_grace", sequence["off_not_before"],
              requested_temperature=value, native_mode=sequence["mode"])
    elif not record.get("pending") and not record.get("paused"):
        # A proven pre-dispatch abort committed no stop. A changed stop policy
        # remains free to cancel before the reverse command was dispatched.
        record.pop("native_setpoint_stop", None)
        await runtime._save()
    return sent


async def progress_stop(runtime, spec) -> bool:
    """Finish a saved stop before ordinary target, restart or supply control."""
    from . import equipment_model as model
    from .equipment_runtime import (
        _manual_output_changes, entity_area, foreign_owner_hold, matches, snapshot,
        native_retry_decision, NATIVE_COMMAND_MAX_ATTEMPTS,
        NATIVE_RECONNECT_EXTRA_ATTEMPTS, NATIVE_RECONNECT_SETTLE_SECONDS,
    )
    record, now = runtime._record(spec), runtime.clock()
    sequence = record.get("native_setpoint_stop")
    if sequence is None:
        return False

    def blocked(reason):
        runtime._status(spec, "native_setpoint_shutdown_blocked", reason=reason)
        return True

    if not _valid(sequence, record, spec):
        return blocked("invalid_shutdown_sequence")
    entity = sequence["entity"]
    edge = finite(getattr(runtime, "_native_on_epoch", {}).get(entity), 0, now)
    if (sequence["owned"] and edge is not None
            and edge > sequence["owned_since"]
            and edge != sequence.get("invalidated_on_epoch")):
        # Persist the event before ANY early hold (including reconnect or
        # identity holds). Losing this process must not revive the old OFF
        # authorization against a genuinely newer physical ON episode.
        sequence["invalidated_on_epoch"] = edge
        owned = record.get("power", {}).get(entity)
        if isinstance(owned, dict):
            owned["since"] = max(owned["since"], edge)
        record.setdefault("native_power_observations", {})[entity] = {
            "state": "on", "since": edge,
        }
        await runtime._save()
    if (not runtime._identity_ok(spec)
            or entity_area(runtime.hass, entity) != sequence["area"]
            or foreign_owner_hold(runtime.hass, runtime.manager.entry.entry_id, entity)):
        return blocked("physical_source_identity_changed")
    if record.get("paused") not in _RECOVERABLE_PAUSES:
        return blocked(record["paused"])
    state = runtime.hass.states.get(entity)
    if state is None or state.state in ("unknown", "unavailable"):
        runtime._status(spec, "waiting_for_physical_device", reason="native_source_unavailable")
        return True
    if not _supply_ready(runtime, spec):
        return blocked("upstream_switch_not_verified_on")
    settle_fn = getattr(runtime, "_native_settle_remaining", None)
    settle = settle_fn(spec) if callable(settle_fn) else 0
    if settle is None or settle > 0:
        runtime._status(spec, "waiting_for_physical_device", reason="native_restore_settling",
                        reconnect_settle_remaining_seconds=settle)
        if settle:
            wake_at(runtime, spec, now + settle)
        return True
    pending = record.get("pending")
    target_pending = _associated(pending, sequence, target=True)
    off_pending = _associated(pending, sequence)
    if pending and not (target_pending or off_pending):
        return blocked("other_endpoint_acknowledgement_pending")
    if (sequence["phase"] == "preparing" and pending is None
            and not record.get("paused") and "off_not_before" not in sequence):
        # _send has durably proved its pre-dispatch abort. A restart between
        # that save and begin_stop's cleanup must not invent a committed leg.
        record.pop("native_setpoint_stop", None)
        await runtime._save()
        return False
    baseline = record.get("baseline", {}).get(entity)
    current = snapshot(state)
    expected = {"attributes": {"temperature": sequence["temperature"]}}
    confirmed = matches(state, expected)
    changes = _manual_output_changes(baseline, current) if baseline is not None else ()
    if confirmed:
        changes = tuple(key for key in changes if key != "temperature")
    if off_pending and state.state == "off":
        changes = tuple(key for key in changes if key != "state")
    context = getattr(state, "context", None)
    direct_user = bool(getattr(context, "user_id", None)
                       and not getattr(context, "parent_id", None))
    physical_user = str(state.attributes.get("change_origin")
                        or state.attributes.get("operation_source") or "").lower() in (
                            "physical_button", "manual_button", "local_user",
                        )
    if changes and (direct_user or physical_user):
        await runtime._pause(spec, "physical_manual_override")
        return True
    if state.state == "off":
        # A real native OFF can arrive together with the temperature ACK.
        # It ends ownership even though the preceding command was not power.
        record.get("power", {}).pop(entity, None)
        record.setdefault("off_at", {})[entity] = now
        record.setdefault("baseline", {})[entity] = current
        record.setdefault("setpoint_startup_observations", {}).pop(entity, None)
        record.pop("unconfirmed_native_target", None)
        if target_pending or off_pending:
            record["pending"] = None
        sequence.update(completed_at=now, native_off_confirmed=True,
                        target_confirmed=bool(sequence.get("target_confirmed") or confirmed))
        record["last_native_setpoint_stop"] = deepcopy(sequence)
        record.pop("native_setpoint_stop", None)
        record.pop("paused", None)
        record.pop("restart_power_verification", None)
        record.pop("automatic_continue_requested", None)
        await runtime._save()
        runtime._status(spec, "off", native_off_confirmed=True)
        return True
    if sequence.get("invalidated_on_epoch"):
        return blocked("native_mode_changed_during_shutdown")
    if state.state != sequence["mode"]:
        return blocked("native_mode_changed_during_shutdown")
    if state.attributes.get("hvac_action") == "defrosting":
        runtime._status(spec, "native_defrost_protection")
        return True
    cap = model.capabilities(runtime.manager, spec)
    if cap is None or cap.primary != entity:
        try:
            cap = model.Capabilities(**record["capabilities"])
        except (KeyError, TypeError, ValueError):
            return blocked("physical_capabilities_unavailable")
    owned = record.get("power", {}).get(entity)
    if sequence["owned"]:
        edge = finite(getattr(runtime, "_native_on_epoch", {}).get(entity), 0, now)
        if not (isinstance(owned, dict) and owned.get("since") == sequence["owned_since"]
                and (edge is None or edge <= sequence["owned_since"])
                and runtime._shutdown_allowed(spec, entity, {"state": "off"})):
            return blocked("owned_shutdown_identity_or_dwell_hold")
    elif not (runtime._current_spec(spec)
              and model.permission(runtime.manager, spec, cap)[1]):
        return blocked("power_control_not_commissioned")
    if sequence["phase"] == "preparing":
        if not target_pending:
            # No matching durable command can establish a committed phase.
            return blocked("shutdown_command_evidence_missing")
        sent = finite(pending.get("last_attempt_at"), 0, now)
        if pending.get("phase") == "commanded" and sent is not None:
            sequence.update(phase="waiting", sent_at=sent,
                            off_not_before=sent + SETPOINT_GRACE_SECONDS)
        else:
            # An interrupted intent is not an ACK. Keep that exact journal,
            # then allow only OFF after one conservative verified 30s wait.
            sequence.update(phase="uncertain", recovered_at=now,
                            off_not_before=now + SETPOINT_GRACE_SECONDS)
        await runtime._save()
    deadline = finite(sequence.get("off_not_before"), 0, 1e13)
    if deadline is None or deadline > now + SETPOINT_GRACE_SECONDS:
        return blocked("invalid_shutdown_deadline")
    if off_pending:
        # The saved committed OFF survives HA restart and a changed room
        # policy. Keep the original retry budget; every dispatch still uses
        # _send's durable intent and exact owned-shutdown rechecks.
        attempts = pending.get("attempts")
        first = finite(pending.get("when"), 0, now)
        used = pending.get("reconnect_retry_uses", 0)
        if (type(attempts) is not int or not 1 <= attempts <= (
                NATIVE_COMMAND_MAX_ATTEMPTS + NATIVE_RECONNECT_EXTRA_ATTEMPTS)
                or first is None or type(used) is not int
                or not 0 <= used <= NATIVE_RECONNECT_EXTRA_ATTEMPTS):
            return blocked("invalid_shutdown_retry_history")
        decision = native_retry_decision(pending, now, state)
        if decision == "waiting":
            runtime._status(spec, "awaiting_physical_acknowledgement",
                            command_attempts=attempts, native_output_confirmed=False)
            return True
        if decision == "uncertain":
            recovery_due = finite(sequence.get("off_recovery_not_before"), 0, 1e13)
            if recovery_due is None:
                recovery_due = now + SETPOINT_GRACE_SECONDS
                sequence["off_recovery_not_before"] = recovery_due
                await runtime._save()
            if now < recovery_due:
                _wait(runtime, spec, "native_setpoint_shutdown_preparing", recovery_due,
                      reason="native_command_failed_or_uncertain")
                return True
        if attempts >= NATIVE_COMMAND_MAX_ATTEMPTS:
            epoch = finite(getattr(runtime, "_native_reconnect_epoch", {}).get(entity), 0, now)
            last = finite(pending.get("last_attempt_at", pending.get("when")), 0, now)
            if not (attempts < NATIVE_COMMAND_MAX_ATTEMPTS + NATIVE_RECONNECT_EXTRA_ATTEMPTS
                    and used < NATIVE_RECONNECT_EXTRA_ATTEMPTS
                    and epoch is not None and last is not None and epoch > last
                    and epoch != pending.get("reconnect_retry_epoch_used")
                    and now - epoch >= NATIVE_RECONNECT_SETTLE_SECONDS):
                return blocked("physical_acknowledgement_missing")
            pending = deepcopy(pending)
            pending["reconnect_retry_uses"] = used + 1
            pending["reconnect_retry_epoch_used"] = epoch
        sequence["off_retry_budget"] = deepcopy(pending)
        sequence.pop("off_recovery_not_before", None)
        record["pending"] = None
        sequence["phase"] = "off_ready"
    if record.get("paused") in _RECOVERABLE_PAUSES:
        record.pop("paused", None)
        record.pop("automatic_continue_requested", None)
        record.pop("restart_power_verification", None)
    if confirmed and not sequence.get("target_confirmed"):
        sequence["target_confirmed"] = True
        if isinstance(baseline, dict) and isinstance(baseline.get("attributes"), dict):
            baseline["attributes"]["temperature"] = state.attributes["temperature"]
        if target_pending:
            sequence["target_journal"] = deepcopy(pending)
            record["pending"] = None
            target_pending = False
        await runtime._save()
    if now < deadline:
        _wait(runtime, spec, "native_setpoint_shutdown_grace", deadline,
              requested_temperature=sequence["temperature"], native_mode=sequence["mode"],
              native_target_confirmed=bool(sequence.get("target_confirmed")))
        return True
    if target_pending:
        # The original target remains explicitly unconfirmed. Transfer only
        # this stop leg into evidence; _send persists the ensuing OFF intent.
        sequence["target_journal"] = deepcopy(pending)
        sequence["target_confirmed"] = False
        record["pending"] = None
    sequence["phase"] = "off_ready"
    sent = await runtime._send(
        spec, cap, entity, "set_hvac_mode", {"hvac_mode": "off"}, {"state": "off"},
        power=True, mode="off", automatic=False, shutdown=sequence["owned"],
        stop_finish=True,
    )
    if sent:
        sequence["phase"] = "off_pending"
    await runtime._save()
    return True

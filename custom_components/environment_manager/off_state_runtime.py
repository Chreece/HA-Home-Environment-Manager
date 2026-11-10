"""HEM OFF thermal-watch workflow, bound to existing native control authority.

Only the existing EquipmentRuntime journal may send native commands. A room
temperature trend cannot verify that a Zigbee relay or valve is actually ON or
OFF; every warning and repeat uses those precise words.
"""
from __future__ import annotations

import asyncio
import logging
from math import isfinite
from typing import Any

from . import equipment_model as model
from .off_state_watchdog import (
    MAX_OFF_RECOVERY_ATTEMPTS, MAX_WATCH_SECONDS,
    MIN_RECOVERY_INTERVAL_SECONDS, MESSAGES, ThermalWatch, recovery_due,
)
from .room_sources import room_temperature_evidence

_LOGGER = logging.getLogger(__name__)


def _competing_heat_clear(runtime: Any, spec: Any, primary: str) -> bool:
    """Do not attribute one room's warming to a heater while another is ON.

    This checks native heating endpoints, including non-HEM climate entities.
    An unidentified heat source (e.g. sun) is still possible: suspected only.
    """
    hass = runtime.hass
    for other in model.specs(runtime.manager):
        if other.area_id != spec.area_id or other.identifier == spec.identifier:
            continue
        cap = model.capabilities(runtime.manager, other)
        if cap is None or "heat" not in cap.modes or cap.primary == primary:
            continue
        state = hass.states.get(cap.primary)
        if state is None or state.state not in ("off", "idle"):
            return False
    try:
        from .discovery import entity_area
        for state in hass.states.async_all("climate"):
            if state.entity_id == primary or entity_area(hass, state.entity_id) != spec.area_id:
                continue
            if "heat" not in (state.attributes.get("hvac_modes") or ()):
                continue
            if state.state not in ("off", "idle"):
                return False
    except (AttributeError, TypeError):
        return False
    return True


def _independent_room_temperature(runtime: Any, spec: Any) -> tuple[float | None, tuple[str, ...]]:
    """Only verified, fresh, same-room temperature sensors, not heater telemetry."""
    room = model.room_config(runtime.manager, spec)
    pinned = room.get("temperature_entity")
    try:
        temp, evidence = room_temperature_evidence(
            runtime.hass, runtime.manager.settings, spec.area_id,
            pinned=pinned if isinstance(pinned, str) else None,
        )
    except (ImportError, AttributeError):
        # Incomplete source-registry setup is not an authorization to act.
        return None, ()
    ids = tuple(evidence.get("entity_ids") or ())
    if (evidence.get("status") != "ready" or evidence.get("partial") is True
            or not ids or evidence.get("valid_count") != len(ids)):
        return None, ()
    try:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(runtime.hass)
        for entity in ids:
            record = registry.async_get(entity)
            if (record is not None and getattr(record, "device_id", None)
                    == spec.source_device_id and spec.source_device_id):
                return None, ()
    except (ImportError, AttributeError):
        return None, ()
    return temp, ids


def _guard(runtime: Any, spec: Any, cap: Any, state: Any, watch: dict, *,
           allowed_pending: dict | None = None) -> bool:
    """Guard to allow another OFF, never an inferred ON or broadened authority."""
    record = runtime._record(spec)
    now = runtime.clock()
    cfg = model.settings(runtime.manager, spec)
    if (not runtime._active or not runtime._ready
            or cfg.get("control_mode") not in ("automatic", "pid", "off")
            or (record.get("pending") is not None
                and record.get("pending") is not allowed_pending)
            or record.get("paused")
            or record.get("native_setpoint_stop")
            or record.get("restart_power_verification")
            or not runtime._current_spec(spec) or not runtime._identity_ok(spec)
            or cap.primary != watch.get("entity")
            or spec.source_device_id != watch.get("source_device_id")
            or spec.area_id != watch.get("area")
            or state is None or state.state != "off"
            or state.attributes.get("hvac_action") == "defrosting"
            or not model.sources_available(runtime.manager, spec)
            or "off" not in cap.modes or "heat" not in cap.modes):
        return False
    if not model.permission(runtime.manager, spec, cap)[1]:
        return False
    if (getattr(runtime, "_native_settle_remaining", lambda _spec: None)(spec) != 0
            or runtime._gate(spec, cap, cfg, model.plan_for(runtime.manager, spec),
                             "off", automatic=False, window_stop=True)):
        return False
    # A separate supply that is intentionally OFF is not an available
    # destination for a native Zigbee command; never wake it here.
    supply = cfg.get("power_switch_entity")
    if supply and (up := runtime.hass.states.get(supply)) is None:
        return False
    if supply and up.state != "on":
        return False
    # Do not override an explicit HA user or physical-button intervention
    # newer than the original HEM OFF acknowledgement.
    context = getattr(state, "context", None)
    origin = str(state.attributes.get("change_origin")
                 or state.attributes.get("operation_source") or "").lower()
    try:
        updated = state.last_updated.timestamp()
    except (AttributeError, TypeError, ValueError, OverflowError):
        updated = None
    if updated is not None and updated > watch["off_since"] + 1 and (
        (getattr(context, "user_id", None) and
         not getattr(context, "parent_id", None)) or
        origin in ("physical_button", "manual_button", "local_user")
    ):
        return False
    return True


async def _notify(runtime: Any, spec: Any, kind: str, evidence: dict) -> None:
    from .device_faults import _deliver_device_notice
    from .languages import announcement_language
    from homeassistant.helpers import area_registry as ar

    cfg = model.settings(runtime.manager, spec)
    if cfg.get("announce_device_errors", True) is not True:
        return
    area = ar.async_get(runtime.hass).async_get_area(spec.area_id)
    room_name = getattr(area, "name", None) or spec.area_id
    native = runtime.hass.states.get(evidence["entity"])
    device_name = getattr(native, "name", None) or spec.name
    language = announcement_language(
        runtime.hass, runtime.manager.settings.get("language", "auto"),
    )
    words = MESSAGES.get(language, MESSAGES["en"])
    message = words[kind].format(
        name=device_name, room=room_name,
        first=evidence["first_c"], current=evidence["current_c"],
        target=evidence["target_c"], attempts=evidence.get("attempts", 0),
    )
    await _deliver_device_notice(
        runtime.manager, spec, f"HEM · {words['title']}", message, language,
        area_name=room_name, kind="thermal_off_" + kind,
    )


async def watchdog_tick(runtime: Any, spec: Any, cap: Any, state: Any) -> bool:
    """Observe an explicitly HEM-commanded OFF; return True only if OFF resent."""
    record = runtime._record(spec)
    ledger = record.get("thermal_off_watch")
    sessions = getattr(runtime, "_thermal_off_sessions", None)
    if sessions is None:
        sessions = runtime._thermal_off_sessions = {}
    if not isinstance(ledger, dict):
        sessions.pop(spec.identifier, None)
        return False
    now = runtime.clock()
    off_since = ledger.get("off_since")
    if (type(off_since) not in (float, int) or not isfinite(off_since)
            or not 0 <= now - off_since <= MAX_WATCH_SECONDS
            or state is None or state.state != "off"
            or cap.primary != ledger.get("entity")
            or record.get("power", {}).get(cap.primary)
            or spec.source_device_id != ledger.get("source_device_id")
            or spec.area_id != ledger.get("area")):
        sessions.pop(spec.identifier, None)
        return False
    cfg = model.settings(runtime.manager, spec)
    if cfg.get("control_mode") not in ("automatic", "pid", "off"):
        sessions.pop(spec.identifier, None)
        return False
    temperature, ids = _independent_room_temperature(runtime, spec)
    if temperature is None:
        sessions.pop(spec.identifier, None)
        return False
    target = model.targets(
        runtime.manager, spec, cap, cfg, model.plan_for(runtime.manager, spec)
    ).get("heat")
    if type(target) not in (int, float) or not isfinite(target):
        sessions.pop(spec.identifier, None)
        return False
    sensor_watch = sessions.get(spec.identifier)
    if (not isinstance(sensor_watch, ThermalWatch)
            or sensor_watch.source_ids != ids
            or sensor_watch.off_since != off_since):
        sensor_watch = sessions[spec.identifier] = ThermalWatch(ids, off_since)
    risk = sensor_watch.observe(
        now=now, temperature_c=temperature, target_c=target, source_ids=ids,
        off_since=off_since,
        other_heat_sources_clear=_competing_heat_clear(runtime, spec, cap.primary),
    )
    if risk == "none":
        return False
    first = sensor_watch.samples[0][1]
    observation = {
        "state": "suspected",
        "physical_output_confirmed": False,
        "entity": cap.primary,
        "source_ids": list(ids),
        "first_c": round(first, 2),
        "current_c": round(temperature, 2),
        "target_c": round(target, 2),
        "observed_at": now,
        "off_since": off_since,
        "attempts": ledger.get("attempts", 0),
        "last_attempt_at": ledger.get("last_attempt_at"),
        "native_state": "off",
    }
    first_alert = ledger.get("notified") is not True
    if first_alert:
        ledger["notified"] = True
        # Freeze an alert episode before any potentially slow notification.
        record["thermal_off_warning"] = observation
        await runtime._save()
        try:
            await _notify(runtime, spec, "suspected", observation)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("HEM OFF thermal alert delivery failed for %s", spec.identifier)
    # This is a fresh observation and not a physical confirmation. Keep
    # transient diagnostic updates out of the durable HA Store.
    record["thermal_off_warning"] = observation
    eligible = (
        _guard(runtime, spec, cap, state, ledger)
        and _competing_heat_clear(runtime, spec, cap.primary)
    )
    if recovery_due(ledger, now, guarded=eligible):
        # Reserve the finite budget durably *before* sending. An interrupted
        # HA call/restart is NOT a free new attempt.
        ledger["attempts"] = int(ledger.get("attempts", 0)) + 1
        ledger["last_attempt_at"] = now
        await runtime._save()
        service = "set_hvac_mode" if cap.domain == "climate" else "turn_off"
        if cap.domain not in ("climate", "switch", "input_boolean"):
            return False
        result = await runtime._send(
            spec, cap, cap.primary, service,
            {"hvac_mode": "off"} if cap.domain == "climate" else {},
            {"state": "off"}, power=True, mode="off", automatic=False,
            off_state_recovery=True,
        )
        return result is True
    if (type(ledger.get("attempts")) is int
            and ledger["attempts"] >= MAX_OFF_RECOVERY_ATTEMPTS
            and ledger.get("exhausted_notified") is not True
            and type(ledger.get("last_attempt_at")) in (int, float)
            and now - ledger["last_attempt_at"] >= MIN_RECOVERY_INTERVAL_SECONDS):
        ledger["exhausted_notified"] = True
        await runtime._save()
        try:
            await _notify(runtime, spec, "exhausted", observation)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("HEM repeated-OFF escalation delivery failed for %s", spec.identifier)
    return False

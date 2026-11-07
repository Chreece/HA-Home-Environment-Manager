"""Bounded, room-local opportunity to air before a new automatic device start.

The announcement request has one short submission deadline. Only accepted
delivery starts the separate user-response deadline. Neither deadline can be
extended by repeated advice, sensor jitter or failed output. This module never
operates a window or an appliance; existing native safety gates still own all
physical commands, minimum operating times and open-window protection.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from time import time
from typing import Any, Callable

from .const import (
    CONF_AUTO_NOTIFY, CONF_AUTO_TTS, CONF_WINDOW_OPEN_TIMEOUT_MINUTES,
    DEFAULT_WINDOW_OPEN_TIMEOUT_MINUTES, DOMAIN,
)

REQUEST_TIMEOUT_SECONDS = 130
RESOLVED_SECONDS = 60
MAX_ROOMS = 128
_HOLD_STATES = frozenset(("window_request_pending", "window_open_wait"))
_THERMAL = frozenset(("heat", "cool", "heat_cool", "auto"))
_CONDITIONING = _THERMAL | {"dry", "humidify"}


def _number(value: Any, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) and minimum <= parsed <= maximum else None


def _idle(state: Any, *, native_setpoint: bool = False) -> bool:
    """Unknown is never OFF; an armed legacy thermostat needs explicit IDLE."""
    if state is None:
        return False
    if state.state == "off":
        return True
    entity = getattr(state, "entity_id", "")
    if entity.startswith(("number.", "input_number.")):
        return _number(state.state, 0, 100) == 0
    return bool(native_setpoint and entity.startswith("climate.")
                and state.state in _THERMAL | {"dry"}
                and state.attributes.get("hvac_action") in ("idle", "off"))


def _conditioning(cap: Any) -> bool:
    if cap is None or getattr(cap, "domain", None) == "fan":
        return False
    return bool(getattr(cap, "domain", None) == "humidifier"
                or set(getattr(cap, "modes", ())) & _CONDITIONING)


def _area_payload(plan: Any, area: str) -> dict:
    environment = getattr(plan, "environment", {})
    payload = environment.get(area, {}) if isinstance(environment, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _available_person(plan: Any, area: str) -> bool:
    payload = _area_payload(plan, area)
    observed = payload.get("room_presence", {})
    climate = payload.get("climate_plan", {})
    observed = observed if isinstance(observed, dict) else {}
    climate = climate if isinstance(climate, dict) else {}
    # Someone elsewhere at home can air an empty bathroom. A comfort profile
    # or pre-arrival override cannot replace actual home/sleep observations.
    home = observed.get("home", climate.get("away"))
    sleeping = observed.get("sleeping", climate.get("sleeping"))
    return home == "home" and sleeping is False


def _manager(hass: Any, entry_id: str | None) -> Any:
    entries = getattr(hass, "data", {}).get(DOMAIN, {})
    return entries.get(entry_id) if isinstance(entries, dict) else None


def pending_demands(manager: Any, area: str, plan: dict) -> tuple[dict, ...]:
    """Fresh measured demand from exactly selected Automatic/PID controllers.

    The native modes, exact-device grants, effective target profile and normal
    room-source freshness policy are reused. An integral value, a displayed
    duty percentage or a climate entity's name never proves a need to air.
    """
    from . import equipment_model as model
    from .device_activation import effective_device
    from .occupancy_policy import live_device_permission
    from .equipment_power_switch import output_required, verified_capabilities
    from .dry_mode import automatic_mode

    runtime = getattr(manager, "equipment", None)
    if runtime is None or not isinstance(plan, dict):
        return ()
    result = []
    for spec in model.specs(manager):
        if spec.area_id != area:
            continue
        cfg = model.settings(manager, spec)
        if cfg.get("control_mode") not in ("automatic", "pid"):
            continue
        cap = model.capabilities(manager, spec)
        if cap is None:
            cap = verified_capabilities(runtime, spec)
        if not _conditioning(cap) or getattr(cap, "humidifying", False):
            continue
        _soft, power = model.permission(manager, spec, cap)
        if not power or getattr(runtime, "records", {}).get(spec.identifier, {}).get("paused"):
            continue
        device = effective_device(manager, spec, cap.primary, cap=cap)
        if live_device_permission(
            manager.hass, area, model.room_config(manager, spec), plan, device,
        )[0] != "eligible":
            continue
        measured = runtime.measurements(spec, cap)
        targets = model.targets(manager, spec, cap, cfg, plan)
        if output_required(
            cap, targets, measured, method=cfg["control_mode"],
            requested_mode=cfg.get("requested_mode"), fan_purpose=None, plan=plan,
        ) is not True:
            continue
        mode = cfg.get("requested_mode") if cfg["control_mode"] == "pid" else None
        if mode not in ("heat", "cool", "dry"):
            native = manager.hass.states.get(cap.primary)
            if native is None:
                continue
            mode = automatic_mode(
                cap, native, measured, targets,
                dedicated_dry=model.room_config(manager, spec).get("dry_climate_entity") == cap.primary,
                pid=cfg["control_mode"] == "pid",
            )
        range_capable = (getattr(cap, "temperature_range", False) is True
                         and bool(set(cap.modes) & {"heat_cool", "auto"}))
        if mode in ("heat_cool", "auto") and range_capable:
            current = _number(measured.get("temperature"), -40, 80)
            low = _number(targets.get("heat"), -30, 60)
            high = _number(targets.get("cool"), -30, 60)
            # A range is not a particular direction. Only a fresh reading
            # outside its validated band can identify a useful alternative.
            if current is None or low is None or high is None or high - low < 1:
                continue
            mode = "heat" if current < low else "cool" if current > high else None
        if (mode not in ("heat", "cool", "dry")
                or mode not in cap.modes and not (range_capable and mode in ("heat", "cool"))):
            continue
        row = {"entity_id": cap.primary, "effect": mode,
               "temperature_c": measured.get("temperature")}
        if mode == "dry":
            current = _number(measured.get("humidity"), 0, 100)
            target = _number(targets.get("humidity"), 0, 100)
            if current is None or target is None or current <= target:
                continue
            row.update(humidity_percent=current, target_humidity=target)
        else:
            current = _number(measured.get("temperature"), -40, 80)
            target = _number(targets.get(mode), -30, 60)
            if current is None or target is None or (
                current >= target if mode == "heat" else current <= target
            ):
                continue
            row.update(temperature_c=current, target_c=target)
        result.append(row)
    return tuple(result)


@dataclass
class _Episode:
    action: str
    reasons: str
    contacts: tuple[str, ...]
    targets: tuple[str, ...]
    phase: str
    since: float
    until: float
    timeout_seconds: int
    resolved_since: float | None = None
    cancel: Callable[[], None] | None = None


class WindowOpeningWait:
    """A bounded in-memory episode; HA restarts do not restore an old wait."""

    def __init__(self, manager: Any, *, clock: Callable[[], float] = time,
                 schedule: Callable[[float, Callable], Callable] | None = None):
        self.manager = manager
        self.clock = clock
        self._schedule = schedule
        self._rooms: dict[str, _Episode] = {}
        self._offered: dict[str, Any] = {}
        self._inflight: dict[str, tuple[Any, _Episode]] = {}
        self._stopped = False

    def _timeout(self) -> int:
        raw = self.manager.settings.get(
            CONF_WINDOW_OPEN_TIMEOUT_MINUTES, DEFAULT_WINDOW_OPEN_TIMEOUT_MINUTES)
        minutes = _number(raw, 0, 30)
        if minutes is None:
            minutes = DEFAULT_WINDOW_OPEN_TIMEOUT_MINUTES
        return int(minutes * 60)

    def _enabled(self) -> bool:
        settings = self.manager.settings
        return bool(not self._stopped and self._timeout() > 0 and (
            settings.get(CONF_AUTO_TTS) or settings.get(CONF_AUTO_NOTIFY)))

    def _cancel(self, episode: _Episode) -> None:
        cancel, episode.cancel = episode.cancel, None
        if cancel is not None:
            cancel()

    def _finish(self, episode: _Episode, phase: str) -> None:
        self._cancel(episode)
        episode.phase = phase
        episode.until = 0

    def _changed(self) -> None:
        recalculate = getattr(self.manager, "_recalculate", None)
        if callable(recalculate) and not self._stopped:
            recalculate()

    def _timer(self, area: str, episode: _Episode) -> None:
        self._cancel(episode)
        expected_deadline, expected_phase = episode.until, episode.phase

        def expired(_now: Any = None) -> None:
            if (self._stopped or self._rooms.get(area) is not episode
                    or episode.until != expected_deadline or episode.phase != expected_phase):
                return
            episode.cancel = None
            self._finish(episode, "window_open_timeout" if episode.phase == "window_open_wait"
                         else "window_request_timeout")
            self._changed()

        seconds = max(0, episode.until - self.clock())
        if self._schedule is not None:
            episode.cancel = self._schedule(seconds, expired)
        else:
            from homeassistant.core import callback
            from homeassistant.helpers.event import async_call_later
            episode.cancel = async_call_later(self.manager.hass, seconds, callback(expired))

    def _contacts(self, plan: Any, area: str) -> tuple[str, ...]:
        from .room_sources import selected
        choice = selected(self.manager.settings, area, "windows")
        if choice is None:
            room = next((room for room in (
                *getattr(plan, "rooms", ()), *getattr(plan, "climate_rooms", ())
            ) if getattr(room, "area_id", None) == area), None)
            choice = [w.entity_id for w in room.windows] if room is not None else ()
        if not isinstance(choice, (list, tuple)):
            return ()
        return tuple(sorted(set(entity for entity in choice if isinstance(entity, str))))

    def _contact_state(self, area: str, contacts: tuple[str, ...]) -> str:
        from .discovery import entity_area, is_window
        if not contacts:
            return "missing"
        result = "closed"
        for entity in contacts:
            state = self.manager.hass.states.get(entity)
            if (not entity.startswith("binary_sensor.") or state is None
                    or entity_area(self.manager.hass, entity) != area
                    or not is_window(self.manager.hass, state)
                    or state.state not in ("on", "off")):
                return "unknown"
            if state.state == "on":
                result = "open"
        return result

    def _targets(self, plan: Any, area: str, rec: Any) -> tuple[str, ...]:
        from . import equipment_model as model
        from .equipment_power_switch import output_required
        from .device_activation import effective_device
        from .occupancy_policy import live_device_permission
        climate = _area_payload(plan, area).get("climate_plan", {})
        climate = climate if isinstance(climate, dict) else {}
        targets = set()
        managed = set()
        for spec in model.specs(self.manager):
            if spec.area_id != area:
                continue
            cfg = model.settings(self.manager, spec)
            if cfg.get("control_mode") != "existing":
                managed.update(spec.source_entities)
            if (cfg.get("control_mode") not in ("automatic", "pid")
                    or cfg.get("pause_on_window_open", False) is not True):
                continue
            cap = model.capabilities(self.manager, spec)
            primary = getattr(cap, "primary", None)
            if cap is None:
                from .equipment_power_switch import verified_capabilities
                runtime = getattr(self.manager, "equipment", None)
                cap = verified_capabilities(runtime, spec) if runtime is not None else None
                primary = getattr(cap, "primary", None)
            if not _conditioning(cap) or primary is None:
                continue
            _soft, power = model.permission(self.manager, spec, cap)
            record = getattr(getattr(self.manager, "equipment", None), "records", {}).get(spec.identifier, {})
            if (not power or record.get("paused") or record.get("pending")
                    or (record.get("upstream") or {}).get("pending")):
                continue
            runtime = self.manager.equipment
            device = effective_device(self.manager, spec, primary, cap=cap)
            if live_device_permission(
                self.manager.hass, area, model.room_config(self.manager, spec), climate, device,
            )[0] != "eligible":
                continue
            if output_required(
                cap, model.targets(self.manager, spec, cap, cfg, climate),
                runtime.measurements(spec, cap), method=cfg["control_mode"],
                requested_mode=cfg.get("requested_mode"), fan_purpose=None, plan=climate,
            ) is not True:
                continue
            native = self.manager.hass.states.get(primary)
            supply_id = cfg.get("power_switch_entity")
            supply = self.manager.hass.states.get(supply_id) if isinstance(supply_id, str) else None
            if _idle(native) or (
                supply is not None and supply.state == "off"
                and (native is None or native.state in ("unknown", "unavailable"))
            ):
                targets.add(primary)

        # Legacy owners have their own write grants. These entries only opt
        # in to a bounded hold; they never make a native action permissible.
        rooms = self.manager.settings.get("climate_rooms", {})
        cfg = rooms.get(area, {}) if isinstance(rooms, dict) else {}
        if (isinstance(cfg, dict) and cfg.get("enabled") is True
                and cfg.get("allow_actuation") is True
                and cfg.get("pause_on_window_open", True) is True):
            for role in ("climate_entity", "heat_climate_entity", "cool_climate_entity",
                         "dry_climate_entity", "heat_actuator", "cool_actuator",
                         "humidifier_entity", "dehumidifier_entity"):
                entity = cfg.get(role)
                temperature = _number(climate.get("temperature_c"), -40, 80)
                target = _number(climate.get("temperature_target_c"), -30, 60)
                mode = climate.get("mode")
                thermal_need = (temperature is not None and target is not None
                                and mode in ("heat", "cool") and
                                (temperature < target - .3 if mode == "heat"
                                 else temperature > target + .3))
                humidity = climate.get("humidity_management", {})
                humidity = humidity if isinstance(humidity, dict) else {}
                needed = (humidity.get("status") == "advisory"
                          and humidity.get("action") in ("dry", "humidify")) if role in (
                              "humidifier_entity", "dehumidifier_entity", "dry_climate_entity"
                          ) else thermal_need
                if needed and isinstance(entity, str) and entity not in managed and _idle(
                    self.manager.hass.states.get(entity), native_setpoint=True,
                ):
                    targets.add(entity)
        legacy = self.manager.settings.get("pid_rooms", {})
        cfg = legacy.get(area, {}) if isinstance(legacy, dict) else {}
        if (isinstance(cfg, dict) and cfg.get("enabled") is True
                and cfg.get("pause_on_window_open", True) is True):
            entities = cfg.get("climate_entities")
            if entities is None:
                entities = [cfg.get("climate_entity")]
            if isinstance(entities, (list, tuple)):
                from .discovery import temperature_sensor_c
                source = cfg.get("temperature_entity")
                measured = temperature_sensor_c(self.manager.hass, source, 10) if isinstance(source, str) else None
                target = _number(cfg.get("target_c"), 5, 36)
                mode = cfg.get("mode")
                if (measured is not None and target is not None and mode in ("heat", "cool")
                        and (measured < target if mode == "heat" else measured > target)):
                    targets.update(entity for entity in entities
                        if isinstance(entity, str) and entity not in managed and _idle(
                            self.manager.hass.states.get(entity), native_setpoint=True))
        reasons = {reason.code for reason in rec.reasons}
        if reasons and all(code.startswith("climate_window_") for code in reasons):
            climate = _area_payload(plan, area).get("climate_plan", {})
            opportunity = climate.get("window_efficiency", {}) if isinstance(climate, dict) else {}
            candidates = opportunity.get("devices")
            if not isinstance(candidates, (list, tuple)):
                candidates = [opportunity.get("active_device")]
            targets.intersection_update(entity for entity in candidates if isinstance(entity, str))
        return tuple(sorted(targets))

    def prepare(self, plan: Any) -> Any:
        """Annotate the current notices and diagnostics without native I/O."""
        now = self.clock()
        valid_clock = _number(now, 0, 1e13) is not None
        notices = (*plan.recommendations, *plan.climate_recommendations)
        opens = {rec.area_id: rec for rec in notices if rec.action == "open"}
        self._offered = {}
        areas = {room.area_id for room in (*plan.rooms, *plan.climate_rooms)}
        areas.update(rec.area_id for rec in notices)
        enabled = self._enabled() and valid_clock
        for area, episode in tuple(self._rooms.items()):
            if area not in areas:
                self._cancel(episode)
                del self._rooms[area]
                self._inflight.pop(area, None)
                continue
            contacts = self._contacts(plan, area)
            contact_state = self._contact_state(area, contacts)
            rec = opens.get(area)
            if not enabled:
                self._finish(episode, "window_wait_disabled")
            elif contacts != episode.contacts or contact_state in ("unknown", "missing"):
                self._finish(episode, "window_wait_evidence_changed")
            elif contact_state == "open":
                self._finish(episode, "window_opened")
                episode.resolved_since = None
            elif not _available_person(plan, area):
                self._finish(episode, "window_wait_person_unavailable")
            elif episode.phase in _HOLD_STATES:
                if now < episode.since or now >= episode.until:
                    self._finish(episode, "window_open_timeout" if episode.phase == "window_open_wait"
                                 else "window_request_timeout")
                elif rec is None or rec.action_signature != episode.action:
                    # A successfully sent time-only refresh is acknowledged
                    # by the room monitor. Its known one-shot demand remains
                    # valid for this bounded response interval.
                    refresh = any(code in episode.reasons for code in (
                        "air_refresh_wake", "air_refresh_return"))
                    if not (refresh and episode.phase == "window_open_wait"):
                        self._finish(episode, "window_wait_need_resolved")
            if rec is None and contact_state == "closed":
                if episode.resolved_since is None:
                    episode.resolved_since = now
                elif 0 <= now - episode.resolved_since >= RESOLVED_SECONDS and episode.phase not in _HOLD_STATES:
                    self._cancel(episode)
                    del self._rooms[area]
            else:
                episode.resolved_since = None

        rendered = {}
        for area, rec in opens.items():
            contacts = self._contacts(plan, area)
            eligible = bool(enabled and _available_person(plan, area) and contacts
                            and self._contact_state(area, contacts) == "closed"
                            and tuple(sorted(w.entity_id for w in rec.windows)) == contacts)
            episode = self._rooms.get(area)
            if (eligible and episode is not None and episode.phase in _HOLD_STATES
                    and not set(episode.targets).intersection(self._targets(plan, area, rec))):
                self._finish(episode, "window_wait_devices_unavailable")
            if eligible and episode is None and len(self._rooms) < MAX_ROOMS:
                targets = self._targets(plan, area, rec)
                if targets:
                    episode = _Episode(
                        rec.action_signature, rec.reason_signature, contacts, targets,
                        "window_request_pending", now, now + REQUEST_TIMEOUT_SECONDS,
                        self._timeout(),
                    )
                    self._rooms[area] = episode
                    self._timer(area, episode)
            seconds = 0
            if (eligible and episode is not None and episode.phase in _HOLD_STATES
                    and rec.action_signature == episode.action):
                # Reason changes before delivery invalidate the old ACK. They
                # do not reset the finite submission/response deadline.
                if episode.phase == "window_request_pending":
                    episode.reasons = rec.reason_signature
                    seconds = episode.timeout_seconds
                else:
                    seconds = max(0, math.ceil(episode.until - now))
                self._offered[area] = rec
            rendered[area] = replace(rec, wait_seconds=seconds)

        environment = dict(plan.environment)
        for area in areas:
            environment[area] = {**_area_payload(plan, area),
                                 "window_open_wait": self.status(area)}
        return replace(
            plan, environment=environment,
            recommendations=tuple(rendered.get(rec.area_id, rec) if rec.action == "open"
                                  else rec for rec in plan.recommendations),
            climate_recommendations=tuple(rendered.get(rec.area_id, rec) if rec.action == "open"
                                          else rec for rec in plan.climate_recommendations),
        )

    def _current(self, rec: Any) -> _Episode | None:
        episode = self._rooms.get(getattr(rec, "area_id", None))
        candidate = self._offered.get(getattr(rec, "area_id", None))
        if (episode is None or candidate is None or getattr(rec, "action", None) != "open"
                or candidate.action_signature != rec.action_signature
                or candidate.reason_signature != rec.reason_signature
                or episode.action != rec.action_signature
                or episode.reasons != rec.reason_signature):
            return None
        return episode

    def submitted(self, rec: Any) -> bool:
        """An accepted CURRENT request starts one fixed response interval."""
        attempt = self._inflight.get(getattr(rec, "area_id", None))
        if (attempt is None or attempt[0] is not rec
                or attempt[1] is not self._rooms.get(rec.area_id)):
            return False
        self._inflight.pop(rec.area_id, None)
        episode = self._current(rec)
        if episode is None or episode.phase != "window_request_pending":
            return False
        now = self.clock()
        if (not self._enabled() or _number(now, 0, 1e13) is None
                or not episode.since <= now < episode.until
                or not _available_person(self.manager.plan, rec.area_id)
                or self._contacts(self.manager.plan, rec.area_id) != episode.contacts
                or self._contact_state(rec.area_id, episode.contacts) != "closed"):
            self._finish(episode, "window_request_no_longer_current")
            self._changed()
            return False
        episode.phase = "window_open_wait"
        episode.since, episode.until = now, now + episode.timeout_seconds
        self._timer(rec.area_id, episode)
        self._changed()
        return True

    def begin_submission(self, rec: Any) -> None:
        """Bind this exact outbound attempt to its current finite episode.

        The same advice can recur after the old need resolved. An old queued
        ACK must not arm that new episode even when its signatures match.
        Recalculating a plan never creates or replaces this in-flight token.
        """
        episode = self._current(rec)
        if (episode is not None and episode.phase == "window_request_pending"
                and getattr(rec, "wait_seconds", 0) > 0):
            self._inflight[rec.area_id] = (rec, episode)

    def submission_failed(self, rec: Any) -> None:
        """Release a failed current request; a retry cannot silently rearm it."""
        attempt = self._inflight.get(getattr(rec, "area_id", None))
        if (attempt is None or attempt[0] is not rec
                or attempt[1] is not self._rooms.get(rec.area_id)):
            return
        self._inflight.pop(rec.area_id, None)
        episode = self._current(rec)
        if episode is not None and episode.phase == "window_request_pending":
            self._finish(episode, "window_request_failed")
            self._changed()

    def status(self, area: str) -> dict:
        episode = self._rooms.get(area)
        if episode is None:
            return {"status": "window_wait_inactive", "remaining_seconds": 0}
        now = self.clock()
        active = (episode.phase in _HOLD_STATES and _number(now, 0, 1e13) is not None
                  and episode.since <= now < episode.until and self._enabled())
        return {
            "status": episode.phase,
            "active": active,
            "remaining_seconds": max(0, math.ceil(episode.until - now)) if active else 0,
            "expires_at": episode.until if active else None,
            "timeout_seconds": episode.timeout_seconds,
            "request_accepted": episode.phase == "window_open_wait",
            "contacts": list(episode.contacts),
            "devices": list(episode.targets),
        }

    def hold(self, area: str, entity: str) -> dict | None:
        """Recheck live contacts and the current room context at every write."""
        episode = self._rooms.get(area)
        if (episode is None or entity not in episode.targets
                or not self._enabled() or not self.status(area).get("active")
                or not _available_person(self.manager.plan, area)
                or self._contacts(self.manager.plan, area) != episode.contacts
                or self._contact_state(area, episode.contacts) != "closed"):
            return None
        return self.status(area)

    def stop(self) -> None:
        self._stopped = True
        for episode in self._rooms.values():
            self._cancel(episode)
        self._rooms.clear()
        self._offered.clear()
        self._inflight.clear()


def managed_start_hold(runtime: Any, spec: Any, cap: Any, cfg: dict,
                       mode: str | None = None, *, supply: bool = False) -> dict | None:
    """Never defer manual/OFF/running/filter output or an unrelated device."""
    waiter = getattr(runtime.manager, "window_open_wait", None)
    if (waiter is None or cfg.get("control_mode") not in ("automatic", "pid")
            or cfg.get("pause_on_window_open", False) is not True or mode == "off"
            or not _conditioning(cap)):
        return None
    native = runtime.hass.states.get(cap.primary)
    if supply:
        supply_id = cfg.get("power_switch_entity")
        relay = runtime.hass.states.get(supply_id) if isinstance(supply_id, str) else None
        if relay is None or relay.state != "off":
            return None
        if native is not None and native.state not in ("unknown", "unavailable") and not _idle(native):
            return None
    elif not _idle(native):
        return None
    return waiter.hold(spec.area_id, cap.primary)


def legacy_start_hold(hass: Any, entry_id: str | None, area: str, entity: str,
                      purpose: str, config: dict | None = None) -> dict | None:
    manager = _manager(hass, entry_id)
    waiter = getattr(manager, "window_open_wait", None)
    if (waiter is None or purpose not in ("thermal", "humidity")
            or isinstance(config, dict) and config.get("pause_on_window_open", True) is not True
            or not _idle(hass.states.get(entity), native_setpoint=True)):
        return None
    return waiter.hold(area, entity)

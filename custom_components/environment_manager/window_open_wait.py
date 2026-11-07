"""An optional, finite airing request before an individual automatic start.

Only a device's explicit opt-in may defer its next start. Each selected device
owns one submission deadline and one response deadline after accepted delivery.
Repeating an announcement, editing another device, or losing a recommendation
cannot renew either deadline. The normal device drivers remain responsible for
all commands, minimum operating times, ownership and open-window protections.
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
MAX_DEVICES = 512
_HOLD_STATES = frozenset(("window_request_pending", "window_open_wait"))
_THERMAL = frozenset(("heat", "cool", "heat_cool", "auto"))
_CONDITIONING = _THERMAL | {"dry", "humidify"}
_EFFECT_REASONS = {
    "heat": frozenset(("climate_window_heat",)),
    "cool": frozenset(("climate_window_cool", "inside_passive_cooling")),
    "dry": frozenset(("climate_window_dry", "inside_humidity", "inside_mold")),
    "humidify": frozenset(("climate_window_humidify", "inside_low_humidity")),
    # A particle filter is not a CO2, VOC, formaldehyde or general AQI remedy.
    "filtration": frozenset(("climate_window_filtration", "inside_pm25", "inside_pm10")),
}


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
        return state.attributes.get("hvac_action") in (None, "off", "idle")
    entity = getattr(state, "entity_id", "")
    if entity.startswith(("number.", "input_number.")):
        return _number(state.state, 0, 100) == 0
    return bool(native_setpoint and entity.startswith("climate.")
                and state.state in _THERMAL | {"dry"}
                and state.attributes.get("hvac_action") in ("idle", "off"))


def _conditioning(cap: Any) -> bool:
    return bool(cap is not None and (
        getattr(cap, "domain", None) == "humidifier"
        or set(getattr(cap, "modes", ())) & _CONDITIONING
    ))


def _supported(manager: Any, spec: Any, cap: Any, device: dict) -> bool:
    from . import equipment_model as model
    supported = getattr(model, "window_alternative_supported", None)
    if callable(supported):
        return supported(manager, spec, cap)
    # Small test/legacy callers may not expose the optional model helper.
    if cap is not None and (getattr(cap, "domain", None) == "fan"
                            or set(getattr(cap, "modes", ())) == {"off", "fan_only"}):
        return device.get("fan_purpose") == "filtration"
    return _conditioning(cap)


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
    # Actual presence, not a Home comfort profile or arrival preparation.
    return (observed.get("home", climate.get("away")) == "home"
            and observed.get("sleeping", climate.get("sleeping")) is False)


def _manager(hass: Any, entry_id: str | None) -> Any:
    entries = getattr(hass, "data", {}).get(DOMAIN, {})
    return entries.get(entry_id) if isinstance(entries, dict) else None


def _device_timeout(cfg: dict) -> int:
    value = _number(cfg.get("window_open_timeout_minutes", 5), 0, 30)
    return int(value * 60) if value is not None else 0


def _friendly_name(manager: Any, entity: str, spec: Any = None) -> str:
    state = manager.hass.states.get(entity)
    attributes = getattr(state, "attributes", {})
    return str(getattr(state, "name", None) or attributes.get("friendly_name")
               or getattr(spec, "name", None) or entity)


@dataclass(frozen=True)
class _Demand:
    entity_id: str
    identifier: str | None
    friendly_name: str
    effect: str | None
    needed: bool | None
    allowed: bool
    idle: bool
    enabled: bool
    timeout_seconds: int
    row: dict
    legacy: bool = False


def _native_demands(manager: Any, area: str, plan: dict) -> dict[str, _Demand]:
    """Use fresh native-controller demand without confusing unknown with zero."""
    from . import equipment_model as model
    from .device_activation import effective_device
    from .occupancy_policy import live_device_permission
    from .equipment_power_switch import output_required, verified_capabilities, permitted_supply
    from .dry_mode import automatic_mode

    runtime = getattr(manager, "equipment", None)
    if runtime is None or not isinstance(plan, dict):
        return {}
    result = {}
    for spec in model.specs(manager):
        if spec.area_id != area:
            continue
        cfg = model.settings(manager, spec)
        if cfg.get("control_mode") not in ("automatic", "pid"):
            continue
        cap = model.capabilities(manager, spec)
        if cap is None:
            cap = verified_capabilities(runtime, spec)
        if cap is None:
            continue
        device = effective_device(manager, spec, cap.primary, cap=cap)
        if not _supported(manager, spec, cap, device):
            continue
        _soft, power = model.permission(manager, spec, cap)
        record = getattr(runtime, "records", {}).get(spec.identifier, {})
        room_config = model.room_config(manager, spec)
        allowed = bool(power and not record.get("paused") and live_device_permission(
            manager.hass, area, room_config, plan, device,
        )[0] == "eligible")
        measured = runtime.measurements(spec, cap)
        targets = model.targets(manager, spec, cap, cfg, plan)
        purpose = device.get("fan_purpose")
        needed = output_required(
            cap, targets, measured, method=cfg["control_mode"],
            requested_mode=cfg.get("requested_mode"), fan_purpose=purpose, plan=plan,
        )
        native = manager.hass.states.get(cap.primary)
        mode = (cfg.get("requested_mode") if cfg["control_mode"] == "pid"
                or cfg.get("operating_mode") else None)
        if cap.domain == "fan" or set(cap.modes) == {"off", "fan_only"} or mode == "fan_only":
            effect = "filtration" if purpose == "filtration" else None
            if not (device.get("sensor_verified") is True
                    or room_config.get("pm25_sensor_verified") is True):
                allowed = False
        elif getattr(cap, "humidifying", False):
            effect = "humidify"
        else:
            if mode not in ("heat", "cool", "dry", "heat_cool", "auto"):
                mode = automatic_mode(
                    cap, native, measured, targets,
                    dedicated_dry=model.room_config(manager, spec).get("dry_climate_entity") == cap.primary,
                    pid=cfg["control_mode"] == "pid",
                )
            if mode is None and cap.domain in ("switch", "input_boolean", "number", "input_number"):
                modes = set(cap.modes) & {"heat", "cool"}
                mode = next(iter(modes)) if len(modes) == 1 else None
            range_capable = (getattr(cap, "temperature_range", False) is True
                             and bool(set(cap.modes) & {"heat_cool", "auto"}))
            if mode in ("heat_cool", "auto") and range_capable:
                current = _number(measured.get("temperature"), -40, 80)
                low = _number(targets.get("heat"), -30, 60)
                high = _number(targets.get("cool"), -30, 60)
                if current is not None and low is not None and high is not None and high - low >= 1:
                    mode = "heat" if current < low else "cool" if current > high else None
                else:
                    mode = None
            effect = mode if mode in ("heat", "cool", "dry") and (
                mode in cap.modes or range_capable and mode in ("heat", "cool")) else None
        if effect in ("heat", "cool", "dry") and effect in cap.modes and cfg.get("requested_mode") != "off":
            # A shared climate device may select DRY while temperature is
            # already in range. Evaluate its actual automatic direction,
            # rather than accidentally treating thermal idle as humidity idle.
            needed = output_required(
                cap, targets, measured, method=cfg["control_mode"], requested_mode=effect,
                fan_purpose=purpose, plan=plan,
            )
        row = {"entity_id": cap.primary, "effect": effect,
               "temperature_c": measured.get("temperature")}
        if effect in ("dry", "humidify"):
            current = _number(measured.get("humidity"), 0, 100)
            target = _number(targets.get("humidity"), 0, 100)
            row.update(humidity_percent=current, target_humidity=target)
            if current is None or target is None:
                needed = None
            elif (current >= target if effect == "humidify" else current <= target):
                needed = False
            if (effect == "humidify" and hasattr(model, "humidity_demand")
                    and model.humidity_demand(manager, spec, cap, cfg, plan).get(
                        "mold_protection_required") is True):
                # The native and supply drivers inhibit humidification for
                # a qualified mold excess, even if a native minimum prevents
                # the effective target from reaching the required low RH.
                needed = False
        elif effect == "filtration":
            current = _number(measured.get("pm25"), 0, 2000)
            target = _number(plan.get("air_actions", {}).get("thresholds", {}).get(
                "pm25_short_term_action_ug_m3"), 0, 2000)
            row.update(pm25_ug_m3=current, target_pm25=target,
                       fan_purpose="filtration")
            if current is None or target is None:
                needed = None
            elif current <= target:
                needed = False
        elif effect in ("heat", "cool"):
            current = _number(measured.get("temperature"), -40, 80)
            target = _number(targets.get(effect), -30, 60)
            row.update(temperature_c=current, target_c=target)
            if current is None or target is None:
                needed = None
            elif (current >= target if effect == "heat" else current <= target):
                needed = False
        elif needed is True:
            needed = None  # No invented direction for an unsupported AUTO mode.
        supply_id = cfg.get("power_switch_entity")
        supply = manager.hass.states.get(supply_id) if isinstance(supply_id, str) else None
        # A cached mode is useful configuration metadata, not evidence that
        # an unavailable appliance can solve the room's current problem.
        # An explicitly selected, verified OFF supply is the one recoverable
        # offline case: the normal supply driver still owns its startup.
        available = all(
            (state := manager.hass.states.get(entity)) is not None
            and state.state not in ("unknown", "unavailable")
            for entity in spec.source_entities
        )
        upstream = record.get("upstream", {})
        upstream = upstream if isinstance(upstream, dict) else {}
        recoverable_supply = False
        valid_supply = not supply_id
        if supply_id and not upstream.get("paused"):
            try:
                valid_supply = permitted_supply(
                    manager, spec, supply_id, upstream.get("identity"),
                ) is not None
            except (AttributeError, KeyError, TypeError):
                # Partial setup is not proof that a physical supply can act.
                valid_supply = False
            recoverable_supply = bool(valid_supply and supply is not None and supply.state == "off")
        allowed = bool(allowed and valid_supply and (available or recoverable_supply))
        idle = bool(not record.get("pending") and not (record.get("upstream") or {}).get("pending") and (
            _idle(native) or supply is not None and supply.state == "off"
            and (native is None or native.state in ("unknown", "unavailable"))))
        timeout = _device_timeout(cfg)
        result[cap.primary] = _Demand(
            cap.primary, spec.identifier, _friendly_name(manager, cap.primary, spec), effect,
            needed, allowed, idle, cfg.get("announce_before_start") is True and timeout > 0,
            timeout, row,
        )
    return result


def pending_demands(manager: Any, area: str, plan: dict) -> tuple[dict, ...]:
    """Measured, authorized native demand used to prove a window alternative."""
    return tuple(item.row for item in _native_demands(manager, area, plan).values()
                 if item.allowed and item.needed is True and item.effect is not None)


@dataclass
class _Episode:
    action: str
    reasons: str
    contacts: tuple[str, ...]
    target: _Demand
    phase: str
    since: float
    until: float
    timeout_seconds: int
    resolved_since: float | None = None
    finished_at: float | None = None
    cancel: Callable[[], None] | None = None


class WindowOpeningWait:
    """Independent device deadlines, grouped solely for room delivery.

    Completed episodes stay consumed while their measured demand persists.
    Losing one recommendation or sensor report is not evidence that a device
    finished its job. A new HA process never restores a stale active delay.
    """

    def __init__(self, manager: Any, *, clock: Callable[[], float] = time,
                 schedule: Callable[[float, Callable], Callable] | None = None):
        self.manager = manager
        self.clock = clock
        self._schedule = schedule
        self._rooms: dict[str, dict[str, _Episode]] = {}
        self._offered: dict[str, Any] = {}
        self._inflight: dict[str, tuple[Any, tuple[_Episode, ...]]] = {}
        self._stopped = False

    def _timeout(self) -> int:
        """The old global preference applies only to existing legacy owners."""
        raw = self.manager.settings.get(
            CONF_WINDOW_OPEN_TIMEOUT_MINUTES, DEFAULT_WINDOW_OPEN_TIMEOUT_MINUTES)
        minutes = _number(raw, 0, 30)
        return int((DEFAULT_WINDOW_OPEN_TIMEOUT_MINUTES if minutes is None else minutes) * 60)

    def _enabled(self) -> bool:
        settings = self.manager.settings
        return bool(not self._stopped and (
            settings.get(CONF_AUTO_TTS) or settings.get(CONF_AUTO_NOTIFY)))

    def _cancel(self, episode: _Episode) -> None:
        cancel, episode.cancel = episode.cancel, None
        if cancel is not None:
            cancel()

    def _finish(self, episode: _Episode, phase: str) -> None:
        self._cancel(episode)
        episode.phase = phase
        episode.until = 0
        episode.finished_at = self.clock()

    def _changed(self) -> None:
        recalculate = getattr(self.manager, "_recalculate", None)
        if callable(recalculate) and not self._stopped:
            recalculate()

    def _timer(self, area: str, episode: _Episode) -> None:
        self._cancel(episode)
        expected_deadline, expected_phase = episode.until, episode.phase

        def expired(_now: Any = None) -> None:
            if (self._stopped
                    or self._rooms.get(area, {}).get(episode.target.entity_id) is not episode
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

    def _demands(self, plan: Any, area: str) -> dict[str, _Demand]:
        from . import equipment_model as model
        climate = _area_payload(plan, area).get("climate_plan", {})
        climate = climate if isinstance(climate, dict) else {}
        result = _native_demands(self.manager, area, climate)
        managed = {entity for spec in model.specs(self.manager) if spec.area_id == area
                   and model.settings(self.manager, spec).get("control_mode") != "existing"
                   for entity in spec.source_entities}
        # Legacy room controllers retain their explicitly configured global
        # behavior. They cannot opt a native per-device controller back in.
        rooms = self.manager.settings.get("climate_rooms", {})
        cfg = rooms.get(area, {}) if isinstance(rooms, dict) else {}
        if (isinstance(cfg, dict) and cfg.get("enabled") is True
                and cfg.get("allow_actuation") is True
                and cfg.get("pause_on_window_open", True) is True):
            for role in ("climate_entity", "heat_climate_entity", "cool_climate_entity",
                         "dry_climate_entity", "heat_actuator", "cool_actuator",
                         "humidifier_entity", "dehumidifier_entity"):
                entity = cfg.get(role)
                if not isinstance(entity, str) or entity in managed:
                    continue
                if role in ("humidifier_entity", "dehumidifier_entity", "dry_climate_entity"):
                    humidity = climate.get("humidity_management", {})
                    humidity = humidity if isinstance(humidity, dict) else {}
                    effect = "humidify" if role == "humidifier_entity" else "dry"
                    needed = (humidity.get("status") == "advisory"
                              and humidity.get("action") == effect)
                else:
                    effect = climate.get("mode")
                    temperature = _number(climate.get("temperature_c"), -40, 80)
                    target = _number(climate.get("temperature_target_c"), -30, 60)
                    needed = (None if temperature is None or target is None else
                              bool(effect in ("heat", "cool") and
                                   (temperature < target - .3 if effect == "heat"
                                    else temperature > target + .3)))
                if entity in result and result[entity].needed is True and needed is not True:
                    continue
                result[entity] = _Demand(
                    entity, None, _friendly_name(self.manager, entity), effect, needed,
                    True, _idle(self.manager.hass.states.get(entity), native_setpoint=True),
                    self._timeout() > 0, self._timeout(), {}, True,
                )
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
                effect = cfg.get("mode")
                needed = (None if measured is None or target is None else
                          bool(effect in ("heat", "cool") and
                               (measured < target if effect == "heat" else measured > target)))
                for entity in entities:
                    if isinstance(entity, str) and entity not in managed:
                        result[entity] = _Demand(
                            entity, None, _friendly_name(self.manager, entity), effect, needed,
                            True, _idle(self.manager.hass.states.get(entity), native_setpoint=True),
                            self._timeout() > 0, self._timeout(), {}, True,
                        )
        return result

    @staticmethod
    def _matches(demand: _Demand, rec: Any) -> bool:
        codes = _EFFECT_REASONS.get(demand.effect, ())
        return any(reason.code in codes for reason in rec.reasons)

    @staticmethod
    def _immediate_coverage(demands: dict[str, _Demand]) -> set[str]:
        """Causes already handled by a qualified device with no airing wait."""
        return {code for demand in demands.values()
                if demand.needed is True and demand.allowed and not demand.enabled
                for code in _EFFECT_REASONS.get(demand.effect, ())}

    @staticmethod
    def _covered(demand: _Demand, codes: set[str]) -> bool:
        matching = _EFFECT_REASONS.get(demand.effect, ())
        return bool(matching and set(matching) <= codes)

    def has_enabled_alternative(self, area: str, option: dict) -> bool:
        """Per-device opt-in also enables its proved room opening alternative."""
        if not isinstance(option, dict) or option.get("status") != "opportunity":
            return False
        from . import equipment_model as model
        candidates = option.get("devices")
        if not isinstance(candidates, (list, tuple)):
            candidates = [option.get("active_device")]
        for spec in model.specs(self.manager):
            if spec.area_id != area or not set(spec.source_entities).intersection(candidates):
                continue
            cfg = model.settings(self.manager, spec)
            if (cfg.get("control_mode") in ("automatic", "pid")
                    and cfg.get("announce_before_start") is True and _device_timeout(cfg) > 0):
                cap = model.capabilities(self.manager, spec)
                if cap is None or cap.primary not in candidates:
                    continue
                record = getattr(getattr(self.manager, "equipment", None), "records", {}).get(spec.identifier, {})
                if (not record.get("paused") and not record.get("pending")
                        and model.permission(self.manager, spec, cap)[1]
                        and _idle(self.manager.hass.states.get(cap.primary))):
                    return True
        return False

    def prepare(self, plan: Any) -> Any:
        """Annotate current advice and recheck deadlines without native I/O."""
        now = self.clock()
        valid_clock = _number(now, 0, 1e13) is not None
        notices = (*plan.recommendations, *plan.climate_recommendations)
        opens = {rec.area_id: rec for rec in notices if rec.action == "open"}
        areas = {room.area_id for room in (*plan.rooms, *plan.climate_rooms)}
        areas.update(rec.area_id for rec in notices)
        self._offered = {}
        demands = {area: self._demands(plan, area) for area in areas}
        immediate = {area: self._immediate_coverage(items) for area, items in demands.items()}
        enabled = self._enabled() and valid_clock
        for area, episodes in tuple(self._rooms.items()):
            if area not in areas:
                for episode in episodes.values():
                    self._cancel(episode)
                del self._rooms[area]
                self._inflight.pop(area, None)
                continue
            contacts = self._contacts(plan, area)
            contact_state = self._contact_state(area, contacts)
            rec = opens.get(area)
            for entity, episode in tuple(episodes.items()):
                demand = demands[area].get(entity)
                if demand is not None and demand.identifier != episode.target.identifier:
                    # The entity ID may have been reused for another physical
                    # controller. Its new explicit consent owns a new episode;
                    # no old timer or delivery ACK may transfer to it.
                    self._cancel(episode)
                    del episodes[entity]
                    continue
                resolved = bool(demand is not None and (
                    demand.needed is False or demand.needed is True
                    and demand.effect is not None and demand.effect != episode.target.effect))
                if resolved:
                    if episode.phase in _HOLD_STATES:
                        self._finish(episode, "window_wait_need_resolved")
                    if episode.resolved_since is None:
                        episode.resolved_since = now
                    elif valid_clock and 0 <= now - episode.resolved_since >= RESOLVED_SECONDS:
                        self._cancel(episode)
                        del episodes[entity]
                        continue
                else:
                    # Unknown/missing data and lost advice never clear a
                    # consumed need. Otherwise jitter reopens the same wait.
                    episode.resolved_since = None
                if episode.phase not in _HOLD_STATES:
                    continue
                if (not enabled or demand is not None and not demand.enabled
                        or self._covered(episode.target, immediate[area])):
                    # One ready no-wait remedy owns the matching problem.
                    # An opted-in sibling must not recreate a redundant
                    # window request or hold while that remedy can act.
                    self._finish(episode, "window_wait_disabled")
                elif contacts != episode.contacts or contact_state in ("unknown", "missing"):
                    self._finish(episode, "window_wait_evidence_changed")
                elif contact_state == "open":
                    self._finish(episode, "window_opened")
                elif not _available_person(plan, area):
                    self._finish(episode, "window_wait_person_unavailable")
                elif (demand is None or demand.needed is not True or not demand.allowed
                      or not demand.idle or rec is None or not self._matches(demand, rec)
                      or rec.action_signature != episode.action):
                    self._finish(episode, "window_wait_devices_unavailable")
                elif now < episode.since or now >= episode.until:
                    self._finish(episode, "window_open_timeout" if episode.phase == "window_open_wait"
                                 else "window_request_timeout")
                else:
                    if demand.timeout_seconds < episode.timeout_seconds:
                        episode.timeout_seconds = demand.timeout_seconds
                        if episode.phase == "window_open_wait":
                            episode.until = min(episode.until, episode.since + episode.timeout_seconds)
                            if now >= episode.until:
                                self._finish(episode, "window_open_timeout")
                            else:
                                self._timer(area, episode)
                    if episode.phase == "window_request_pending":
                        episode.reasons = rec.reason_signature
                    # Display current names, retaining the original effect.
                    episode.target = replace(episode.target, friendly_name=demand.friendly_name)

        rendered = {}
        count = sum(len(items) for items in self._rooms.values())
        for area, rec in opens.items():
            contacts = self._contacts(plan, area)
            eligible = bool(enabled and _available_person(plan, area) and contacts
                            and self._contact_state(area, contacts) == "closed"
                            and tuple(sorted(w.entity_id for w in rec.windows)) == contacts)
            if eligible:
                episodes = self._rooms.get(area)
                if episodes is None and len(self._rooms) < MAX_ROOMS:
                    episodes = self._rooms[area] = {}
                if episodes is not None:
                    for entity, demand in demands[area].items():
                        if (entity in episodes or count >= MAX_DEVICES or not demand.enabled
                                or not demand.allowed or not demand.idle or demand.needed is not True
                                or not self._matches(demand, rec)
                                or self._covered(demand, immediate[area])):
                            continue
                        episode = _Episode(
                            rec.action_signature, rec.reason_signature, contacts, demand,
                            "window_request_pending", now, now + REQUEST_TIMEOUT_SECONDS,
                            demand.timeout_seconds,
                        )
                        episodes[entity] = episode
                        count += 1
                        self._timer(area, episode)
            entries = []
            if eligible:
                for entity, episode in self._rooms.get(area, {}).items():
                    if (not self._active(episode, now) or episode.action != rec.action_signature
                            or not self._matches(episode.target, rec)):
                        continue
                    seconds = (episode.timeout_seconds if episode.phase == "window_request_pending"
                               else max(0, math.ceil(episode.until - now)))
                    if seconds > 0:
                        entries.append({"entity_id": entity, "friendly_name": episode.target.friendly_name,
                                        "timeout_seconds": episode.timeout_seconds,
                                        "remaining_seconds": seconds, "effect": episode.target.effect})
                if entries:
                    self._offered[area] = rec
            rendered[area] = replace(rec, wait_seconds=max(
                (item["remaining_seconds"] for item in entries), default=0),
                wait_devices=tuple(sorted(entries, key=lambda item: item["entity_id"])))

        environment = dict(plan.environment)
        for area in areas:
            environment[area] = {**_area_payload(plan, area), "window_open_wait": self.status(area)}
        return replace(
            plan, environment=environment,
            recommendations=tuple(rendered.get(rec.area_id, rec) if rec.action == "open"
                                  else rec for rec in plan.recommendations),
            climate_recommendations=tuple(rendered.get(rec.area_id, rec) if rec.action == "open"
                                          else rec for rec in plan.climate_recommendations),
        )

    def _active(self, episode: _Episode, now: float) -> bool:
        return bool(episode.phase in _HOLD_STATES and _number(now, 0, 1e13) is not None
                    and episode.since <= now < episode.until and self._enabled())

    def _current(self, rec: Any) -> tuple[_Episode, ...]:
        candidate = self._offered.get(getattr(rec, "area_id", None))
        if (candidate is None or getattr(rec, "action", None) != "open"
                or candidate.action_signature != rec.action_signature
                or candidate.reason_signature != rec.reason_signature):
            return ()
        return tuple(episode for episode in self._rooms.get(rec.area_id, {}).values()
                     if episode.phase == "window_request_pending"
                     and episode.action == rec.action_signature
                     and episode.reasons == rec.reason_signature)

    def begin_submission(self, rec: Any) -> None:
        """Bind one actual outbound attempt to its exact device episodes."""
        episodes = self._current(rec)
        if episodes and getattr(rec, "wait_seconds", 0) > 0:
            self._inflight[rec.area_id] = (rec, episodes)

    def submitted(self, rec: Any) -> bool:
        """Only accepted delivery starts each still-current device deadline."""
        attempt = self._inflight.get(getattr(rec, "area_id", None))
        if attempt is None or attempt[0] is not rec:
            return False
        self._inflight.pop(rec.area_id, None)
        current = self._current(rec)
        now = self.clock()
        demands = self._demands(self.manager.plan, rec.area_id)
        immediate = self._immediate_coverage(demands)
        accepted = False
        for episode in attempt[1]:
            if (not any(item is episode for item in current)
                    or self._rooms.get(rec.area_id, {}).get(episode.target.entity_id) is not episode):
                continue
            demand = demands.get(episode.target.entity_id)
            if (not self._active(episode, now)
                    or not _available_person(self.manager.plan, rec.area_id)
                    or self._contacts(self.manager.plan, rec.area_id) != episode.contacts
                    or self._contact_state(rec.area_id, episode.contacts) != "closed"
                    or demand is None or not demand.enabled or not demand.allowed or not demand.idle
                    or demand.needed is not True or not self._matches(demand, rec)
                    or self._covered(demand, immediate)):
                self._finish(episode, "window_request_no_longer_current")
                continue
            episode.timeout_seconds = min(episode.timeout_seconds, demand.timeout_seconds)
            episode.phase = "window_open_wait"
            episode.since, episode.until = now, now + episode.timeout_seconds
            self._timer(rec.area_id, episode)
            accepted = True
        self._changed()
        return accepted

    def submission_failed(self, rec: Any) -> None:
        """Release only the pending episodes included in this exact attempt."""
        attempt = self._inflight.get(getattr(rec, "area_id", None))
        if attempt is None or attempt[0] is not rec:
            return
        self._inflight.pop(rec.area_id, None)
        changed = False
        for episode in attempt[1]:
            if (self._rooms.get(rec.area_id, {}).get(episode.target.entity_id) is episode
                    and episode.phase == "window_request_pending"):
                self._finish(episode, "window_request_failed")
                changed = True
        if changed:
            self._changed()

    def status(self, area: str, entity: str | None = None) -> dict:
        episodes = self._rooms.get(area, {})
        selected = ([episodes[entity]] if entity in episodes else []) if entity is not None else list(episodes.values())
        if not selected:
            return {"status": "window_wait_inactive", "active": False, "remaining_seconds": 0}
        now = self.clock()
        active = [episode for episode in selected if self._active(episode, now)]
        pending = [episode for episode in active if episode.phase == "window_request_pending"]
        chosen = max(pending or active or selected,
                     key=lambda episode: episode.until if episode in active else episode.finished_at or episode.since)
        return {
            "status": chosen.phase,
            "active": bool(active),
            "remaining_seconds": max((max(0, math.ceil(item.until - now)) for item in active), default=0),
            "expires_at": max((item.until for item in active), default=None),
            "timeout_seconds": chosen.timeout_seconds,
            "request_accepted": any(item.phase == "window_open_wait" for item in active),
            "contacts": list(chosen.contacts),
            "devices": sorted(item.target.entity_id for item in selected),
            "device_waits": [{
                "entity_id": item.target.entity_id, "friendly_name": item.target.friendly_name,
                "effect": item.target.effect, "status": item.phase,
                "timeout_seconds": item.timeout_seconds,
                "remaining_seconds": max(0, math.ceil(item.until - now)) if item in active else 0,
                "expires_at": item.until if item in active else None,
                "active": item in active,
            } for item in selected],
        }

    def hold(self, area: str, entity: str) -> dict | None:
        """Recheck live consent, demand and room contacts before every write."""
        episode = self._rooms.get(area, {}).get(entity)
        if (episode is None or not self._active(episode, self.clock())
                or not _available_person(self.manager.plan, area)
                or self._contacts(self.manager.plan, area) != episode.contacts
                or self._contact_state(area, episode.contacts) != "closed"):
            return None
        demands = self._demands(self.manager.plan, area)
        demand = demands.get(entity)
        if (demand is None or not demand.enabled or not demand.allowed or not demand.idle
                or demand.needed is not True or demand.effect != episode.target.effect
                or self._covered(demand, self._immediate_coverage(demands))):
            return None
        if demand.timeout_seconds < episode.timeout_seconds:
            episode.timeout_seconds = demand.timeout_seconds
            if episode.phase == "window_open_wait":
                episode.until = min(episode.until, episode.since + demand.timeout_seconds)
                if self.clock() >= episode.until:
                    self._finish(episode, "window_open_timeout")
                    return None
                self._timer(area, episode)
        return self.status(area, entity)

    def announcement_request(self, rec: Any) -> Any:
        """Keep only opening reasons that still require a human response.

        A ready automatic remedy whose airing option is OFF must not regain
        an opening announcement through the general mold/humidity/PM path.
        Keep unrelated causes (for example CO2 beside mold) and never hide
        a warning on the strength of an unavailable or unauthorized device.
        This is a delivery view; it does not change the original request's
        signatures or its accepted-delivery deadline.
        """
        if getattr(rec, "action", None) != "open":
            return rec
        episodes = self._rooms.get(rec.area_id, {})
        now = self.clock()
        active_codes = set()
        for episode in episodes.values():
            if self._active(episode, now):
                active_codes.update(_EFFECT_REASONS.get(episode.target.effect, ()))
        demands = self._demands(self.manager.plan, rec.area_id)
        immediate = self._immediate_coverage(demands)
        consumed_codes = set()
        for entity, demand in demands.items():
            if demand.needed is not True or not demand.allowed:
                continue
            episode = episodes.get(entity)
            consumed = (episode is not None and not self._active(episode, now)
                        and demand.effect == episode.target.effect)
            if consumed:
                consumed_codes.update(_EFFECT_REASONS.get(demand.effect, ()))
        # A newly waiting device may still request its own bounded episode
        # after a sibling's old timeout. An immediately eligible no-wait
        # remedy has priority over both, without hiding unrelated causes.
        covered = immediate | (consumed_codes - active_codes)
        reasons = tuple(reason for reason in rec.reasons if reason.code not in covered)
        if reasons == rec.reasons:
            return rec
        remaining = {reason.code for reason in reasons}
        waits = tuple(row for row in rec.wait_devices
                      if remaining.intersection(_EFFECT_REASONS.get(row.get("effect"), ())))
        seconds = (max((row["remaining_seconds"] for row in waits), default=0)
                   if rec.wait_devices else rec.wait_seconds if reasons else 0)
        return replace(rec, reasons=reasons, wait_devices=waits, wait_seconds=seconds)

    def should_announce(self, rec: Any) -> bool:
        """Do not keep asking for a consumed alternative to the same demand.

        A CO2 or other unmatched reason still needs its own normal advice.
        Explicit manual announcements remain available to the user; the
        manager applies this helper only to automatic delivery and repeats.
        """
        if getattr(rec, "action", None) != "open":
            return True
        return bool(self.announcement_request(rec).reasons)

    def stop(self) -> None:
        self._stopped = True
        for episodes in self._rooms.values():
            for episode in episodes.values():
                self._cancel(episode)
        self._rooms.clear()
        self._offered.clear()
        self._inflight.clear()


def managed_start_hold(runtime: Any, spec: Any, cap: Any, cfg: dict,
                       mode: str | None = None, *, supply: bool = False) -> dict | None:
    """Only an opted-in idle indoor remedy can wait; OFF/running never do."""
    waiter = getattr(runtime.manager, "window_open_wait", None)
    if (waiter is None or cfg.get("control_mode") not in ("automatic", "pid")
            or cfg.get("announce_before_start") is not True or _device_timeout(cfg) <= 0
            or mode == "off"):
        return None
    from .device_activation import effective_device
    device = effective_device(runtime.manager, spec, cap.primary, cap=cap)
    if not _supported(runtime.manager, spec, cap, device):
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

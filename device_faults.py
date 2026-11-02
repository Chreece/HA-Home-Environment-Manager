"""Read the physical device's OWN Home Assistant fault entities and attributes.

No duplicate error sensor is created. This observer links existing native
sensor/binary_sensor fault entities by exact HA device-registry ownership,
watches native source attributes, and exposes a small display snapshot through
the per-managed-device 'Announce errors' SWITCH. It never controls hardware.

Fault announcements are ON by default per device, but no existing/startup
fault is replayed as a new event. Unknown/unavailable input is NOT healthy.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import logging
import math
import re
from typing import Any

from .const import (
    DOMAIN, CONF_HUB, CONF_NOTIFY_TARGETS, CONF_TTS_ENGINE,
    CONF_MEDIA_PLAYERS, CONF_AUTO_TTS,
)
from . import equipment_model as model

_LOGGER = logging.getLogger(__name__)
_FAULT_END = re.compile(
    r"(?:^|_)(?:error|fault|alarm|failure|problem)"
    r"(?:_code|_status|_message|_description)?$",
    re.IGNORECASE,
)
_ATTR_CODES = ("error_code", "fault_code", "alarm_code", "failure_code",
               "error", "fault", "alarm", "failure", "device_error",
               "active_error", "active_fault")
_ATTR_TEXT = ("error_message", "error_description", "fault_message",
              "fault_description", "alarm_message", "alarm_description",
              "failure_message", "error_info", "fault_info")
_ATTR_LEVEL = ("error_severity", "fault_severity", "severity", "alarm_level")
_EMPTY = frozenset((
    "", "0", "0.0", "off", "false", "none", "null", "no error", "no errors",
    "no fault", "no faults", "ok", "okay", "normal", "healthy",
    "idle", "clear", "cleared", "not detected", "inactive", "success",
    "not present", "not_present", "n/a", "na", "unknown",
))
_UNAVAILABLE = frozenset(("unknown", "unavailable"))
_LEVELS = {"critical": 3, "error": 2, "warning": 1}


def _text(value: Any, limit: int = 160) -> str:
    """Keep untrusted physical diagnostic text readable and bounded."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return ""
    if not isinstance(value, (str, int, float)):
        return ""
    return " ".join(str(value).split())[:limit]


def _active(value: Any) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, (int, float)):
        return math.isfinite(value) and value != 0
    if not isinstance(value, str):
        return False
    text = _text(value).casefold()
    if (not text or text.replace("_", " ").replace("-", " ") in _EMPTY
            or text in _UNAVAILABLE):
        return False
    try:
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
            return float(text) != 0.0
    except (ValueError, OverflowError):
        return False
    return True


def _detail_text(value: Any) -> str:
    """Render short, structured manufacturer fault details if HA supplies them."""
    if isinstance(value, Mapping):
        pieces = []
        for key, item in list(value.items())[:6]:
            name = _text(key, 36)
            detail = _text(item, 120)
            if name and detail:
                pieces.append(f"{name}: {detail}")
        return "; ".join(pieces)[:400]
    if isinstance(value, (list, tuple)):
        return "; ".join(_text(v, 95) for v in value[:4]
                         if _text(v, 95))[:400]
    return _text(value, 400)


def _severity(attrs: Mapping, value: str = "") -> str:
    label = next((_text(attrs.get(k), 40).casefold()
                  for k in _ATTR_LEVEL if _active(attrs.get(k))), "")
    label = label or value.casefold()
    if any(v in label for v in ("critical", "fatal", "emergency", "severe")):
        return "critical"
    if any(v in label for v in ("warning", "warn", "caution")):
        return "warning"
    return "error"


def fault_entity_id(entity_id: str, entry: Any, state: Any) -> bool:
    """Strict physical HA fault-entity discovery, not fuzzy area matching."""
    domain, dot, object_id = entity_id.partition(".")
    if dot != "." or domain not in ("sensor", "binary_sensor"):
        return False
    if getattr(entry, "platform", None) == DOMAIN:
        return False
    attrs = getattr(state, "attributes", {}) if state is not None else {}
    if (domain == "binary_sensor" and isinstance(attrs, Mapping)
            and attrs.get("device_class") == "problem"):
        return True
    fields = [object_id, getattr(entry, "original_name", None)]
    return any(
        _FAULT_END.search(str(v).lower().replace("-", "_").replace(" ", "_"))
        for v in fields if isinstance(v, str)
    )


def _read_native_error(entity_id: str, state: Any, *, fault_entity: bool) -> dict | None:
    if state is None or getattr(state, "state", None) in _UNAVAILABLE:
        return None
    attrs = getattr(state, "attributes", {})
    if not isinstance(attrs, Mapping):
        return None
    values = [_text(attrs.get(k), 110) for k in _ATTR_CODES if _active(attrs.get(k))]
    descriptors = [_detail_text(attrs.get(k)) for k in _ATTR_TEXT
                   if _active(attrs.get(k)) or isinstance(
                       attrs.get(k), (dict, list, tuple)
                   ) and bool(_detail_text(attrs.get(k)))]
    state_value = _text(getattr(state, "state", None), 110)
    state_active = fault_entity and _active(getattr(state, "state", None))
    # An explicit native error_code=0 takes precedence over a stale
    # descriptive last-error attribute left by the manufacturer's device.
    if (any(key in attrs for key in _ATTR_CODES)
            and not values and not state_active):
        return None
    if not values and not descriptors and not state_active:
        return None
    code = (values[0] if values else state_value if state_active else "")
    if state_active and not values and code.casefold() in ("on", "true", "1"):
        code = "problem"
    detail = descriptors[0] if descriptors else ""
    if not detail and state_active and state_value.casefold() not in (
            "on", "true", "1", "active", "detected", "problem", "error", "fault", "alarm"):
        detail = state_value
    if not code and detail:
        code = "reported_fault"
    severity = _severity(attrs, " ".join((code, detail)))
    info = {}
    for key in ("error_info", "fault_info", "error_detail", "fault_detail",
                "error_data", "fault_data"):
        value = attrs.get(key)
        info_text = _detail_text(value)
        if (_active(value) or isinstance(value, (dict, list, tuple))) and info_text:
            info[key] = info_text[:400]
    return {
        "source_entity_id": entity_id,
        "source_state": state_value,
        "code": code,
        "description": detail,
        "severity": severity,
        "info": info,
    }


def _faults_for(hass: Any, spec: Any, diagnostic_entities: tuple[str, ...]) -> dict:
    faults = []
    unavailable = []
    has_diagnostic = bool(diagnostic_entities)
    for entity in (*spec.source_entities, *diagnostic_entities):
        state = hass.states.get(entity)
        if state is None or getattr(state, "state", None) in _UNAVAILABLE:
            unavailable.append(entity)
            continue
        fault = _read_native_error(
            entity, state, fault_entity=entity in diagnostic_entities,
        )
        if fault is not None:
            faults.append(fault)
    faults.sort(key=lambda f: (
        -_LEVELS[f["severity"]], f["source_entity_id"], f["code"],
    ))
    # Every original HA error is shown at its own entity ID, never represented
    # by a new HEM error sensor. Repeated source and diagnostic data are
    # bounded to avoid filling HA's 16KB Recorder-attribute budget.
    if faults:
        primary = faults[0]
        return {
            "status": primary["severity"],
            "source_entity_id": primary["source_entity_id"],
            "source_state": primary["source_state"],
            "code": primary["code"],
            "description": primary["description"],
            "severity": primary["severity"],
            "info": primary["info"],
            "active_count": len(faults),
            "faults": faults[:4],
            "native_error_entities": list(diagnostic_entities[:8]),
            "unavailable_entities": unavailable[:5],
        }
    return {
        "status": "unavailable" if unavailable else
                  "no_fault_reported" if not has_diagnostic else "ok",
        "source_entity_id": diagnostic_entities[0] if diagnostic_entities else None,
        "source_state": "unavailable" if unavailable else None,
        "code": None,
        "description": None,
        "severity": None,
        "info": {},
        "active_count": 0,
        "faults": [],
        "native_error_entities": list(diagnostic_entities[:8]),
        "unavailable_entities": unavailable[:5],
    }


def _signature(report: dict) -> tuple:
    return tuple(sorted(
        (row["source_entity_id"], row["code"], row["description"], row["severity"])
        for row in report.get("faults", ())
    ))


def _notification_text(spec: Any, report: dict, area_name: str) -> tuple[str, str]:
    name = _text(spec.name, 96) or "Physical device"
    title = f"Device error · {name}"
    rows = [
        f"Device: {name}",
        f"Room: {_text(area_name, 96)}",
    ]
    for fault in report.get("faults", ())[:4]:
        rows += [
            f"Source: {fault['source_entity_id']}",
            f"Severity: {fault['severity']}",
            f"Error: {fault['code'] or 'fault detected'}",
        ]
        if fault["description"]:
            rows.append(f"Details: {fault['description']}")
        rows.extend(f"{key}: {value}" for key, value in fault["info"].items())
    rows.append("Inspect the original physical device in Home Assistant.")
    return title, "\n".join(rows)[:2800]


class NativeDeviceFaultMonitor:
    """One event-driven monitor per HEM config entry; no second fault entity."""

    def __init__(self, manager: Any) -> None:
        self.manager = manager
        self.hass = manager.hass
        self.active = False
        self._specs: dict[str, Any] = {}
        self._native_ids: dict[str, tuple[str, ...]] = {}
        self._by_entity: dict[str, set[str]] = {}
        self._latest: dict[str, dict] = {}
        self._last_active: dict[str, dict] = {}
        self._fingerprints: dict[str, tuple] = {}
        self._seen_device_alerts: dict[str, tuple] = {}
        self._tasks: set[asyncio.Task] = set()

    def start(self) -> None:
        self.active = True
        self.refresh(baseline=True)

    async def async_stop(self) -> None:
        self.active = False
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._specs.clear()
        self._by_entity.clear()

    def _fault_index(self) -> tuple[dict, dict, dict]:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.hass)
        spec_list = model.specs(self.manager)
        specs = {spec.identifier: spec for spec in spec_list}
        found = defaultdict(list)
        watched = defaultdict(set)
        if not specs:
            return specs, {}, {}
        # One cached registry walk when relevant registry topology changes,
        # never on a temperature or humidity sample/event.
        for entry in registry.entities.values():
            entity_id = getattr(entry, "entity_id", None)
            device_id = getattr(entry, "device_id", None)
            if not device_id or not isinstance(entity_id, str):
                continue
            if getattr(entry, "disabled_by", None) is not None:
                continue
            if not entity_id.startswith(("sensor.", "binary_sensor.")):
                continue
            native_state = self.hass.states.get(entity_id)
            if not fault_entity_id(entity_id, entry, native_state):
                continue
            for spec in spec_list:
                if spec.source_device_id != device_id:
                    continue
                # Same HA registered device, never a similarly named
                # device merely located in the same room.
                if getattr(entry, "area_id", None) not in (None, spec.area_id):
                    continue
                found[spec.identifier].append(entity_id)
        for spec in spec_list:
            for entity in spec.source_entities:
                watched[entity].add(spec.identifier)
            for entity in found[spec.identifier]:
                watched[entity].add(spec.identifier)
        return (
            specs,
            {key: tuple(sorted(set(value))) for key, value in found.items()},
            dict(watched),
        )

    def refresh(self, *, baseline: bool = False) -> None:
        if not self.active:
            return
        try:
            specs, diagnostics, watched = self._fault_index()
        except (ImportError, AttributeError, TypeError):
            _LOGGER.debug("HEM physical error entity registry not yet available", exc_info=True)
            return
        self._specs = specs
        self._native_ids = diagnostics
        self._by_entity = watched
        for identifier, spec in specs.items():
            self._refresh_spec(spec, baseline=baseline)
        for identifier in tuple(self._latest):
            if identifier not in specs:
                self._latest.pop(identifier, None)
                self._last_active.pop(identifier, None)
                self._fingerprints.pop(identifier, None)

    def _refresh_spec(self, spec: Any, *, baseline: bool = False) -> None:
        identifier = spec.identifier
        report = _faults_for(
            self.hass, spec, self._native_ids.get(identifier, ()),
        )
        fingerprint = _signature(report)
        previous = self._fingerprints.get(identifier)
        prior = self._latest.get(identifier)
        if report["status"] == "unavailable":
            previous_fault = self._last_active.get(identifier)
            if previous_fault:
                report["last_known_fault"] = {
                    key: previous_fault.get(key) for key in
                    ("source_entity_id", "code", "description", "severity")
                }
        elif fingerprint:
            self._last_active[identifier] = dict(report)
        elif report["status"] == "ok" or report["status"] == "no_fault_reported":
            self._last_active.pop(identifier, None)
        # Unavailable reads must not clear a previous active fault signature.
        if report["status"] != "unavailable":
            self._fingerprints[identifier] = fingerprint
            if not fingerprint:
                # Rearm an identical future occurrence only after ALL
                # independent channels of this same physical product have
                # recovered. Do not duplicate current errors from siblings.
                device_key = spec.source_device_id or identifier
                if not any(
                    self._fingerprints.get(other.identifier)
                    for other in self._specs.values()
                    if (other.source_device_id or other.identifier) == device_key
                ):
                    self._seen_device_alerts.pop(device_key, None)
        self._latest[identifier] = report
        if prior != report:
            updates = getattr(getattr(self.manager, "equipment", None),
                              "_presentation_updates", None)
            if updates is not None:
                updates.request(identifier)
        if (baseline or not fingerprint or fingerprint == previous
                or not model.settings(self.manager, spec).get(
                    "announce_device_errors", True
                )):
            return
        # Shared native diagnostic entities may belong to multiple logical
        # HEM channels of the same physical product. Announce one physical
        # fault, not one duplicate per logical controller.
        device_key = spec.source_device_id or identifier
        device_signature = (device_key, fingerprint)
        if self._seen_device_alerts.get(device_key) == device_signature:
            return
        self._seen_device_alerts[device_key] = device_signature
        task = self.hass.async_create_task(
            self._announce(spec, fingerprint, dict(report))
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def state_changed(self, entity_id: Any) -> None:
        if not self.active or not isinstance(entity_id, str):
            return
        for identifier in tuple(self._by_entity.get(entity_id, ())):
            spec = self._specs.get(identifier)
            if spec is not None:
                self._refresh_spec(spec)

    def details(self, spec: Any) -> dict:
        return dict(self._latest.get(spec.identifier, {
            "status": "unverified",
            "source_entity_id": None,
            "code": None, "description": None,
            "active_count": 0,
            "native_error_entities": [],
        }))

    async def async_set_announcements(self, spec: Any, enabled: bool) -> None:
        """One HEM configuration write, with no physical source required."""
        from homeassistant.exceptions import HomeAssistantError
        if type(enabled) is not bool or not self.active:
            raise HomeAssistantError("Device error announcement controls are unavailable")
        from .config_data import mutable_copy
        if not any(
            current.identifier == spec.identifier and
            current.area_id == spec.area_id and
            current.source_device_id == spec.source_device_id and
            current.source_entities == spec.source_entities
            for current in model.specs(self.manager)
        ):
            raise HomeAssistantError("Device identity changed; cannot update error notifications")
        lock = getattr(self.manager, "_device_settings_write_lock", None)
        if lock is None:
            lock = self.manager._device_settings_write_lock = asyncio.Lock()
        async with lock:
            if not self.active or spec.identifier not in self._specs:
                raise HomeAssistantError("Device is no longer monitored")
            options = mutable_copy(self.manager.entry.options)
            profiles = mutable_copy(self.manager.settings.get(model.SETTINGS, {}))
            if not isinstance(profiles, dict):
                profiles = {}
            old = profiles.get(spec.identifier)
            profile = dict(old) if isinstance(old, dict) else {}
            profile["announce_device_errors"] = enabled
            profiles[spec.identifier] = profile
            options[model.SETTINGS] = profiles
            self.hass.config_entries.async_update_entry(
                self.manager.entry, options=options,
            )
        self.manager.equipment._presentation_updates.request(spec.identifier)

    async def _announce(self, spec: Any, fingerprint: tuple,
                        report: dict) -> None:
        if not self.active:
            return
        if not model.settings(self.manager, spec).get(
                "announce_device_errors", True):
            return
        # Do not deliver a stale fault after the same physical source has
        # recovered while its queued notification awaited the event loop.
        if self._fingerprints.get(spec.identifier) != fingerprint:
            return
        from homeassistant.helpers import area_registry as ar
        area = ar.async_get(self.hass).async_get_area(spec.area_id)
        area_name = (getattr(area, "name", None) or spec.area_id)
        title, message = _notification_text(spec, report, area_name)
        config = self.manager.settings
        from .hub_delivery import hub_available, async_submit_hub
        if config.get(CONF_HUB) is True and hub_available(self.hass):
            # Hub owns AI, routing, occupancy, retry and visual/TTS fallback.
            # Its rejection is not permission for duplicate local delivery.
            await async_submit_hub(self.hass, {
                "title": title, "area": [area_name],
                "level": "warning", "text": message, "use_ai": False,
            })
            return
        notified = False
        notify_targets = self.manager._targets_in_room(
            config.get(CONF_NOTIFY_TARGETS, []), spec.area_id
        )
        if (notify_targets
                and self.hass.services.has_service("notify", "send_message")):
            try:
                await self.hass.services.async_call(
                    "notify", "send_message", {"title": title, "message": message},
                    target={"entity_id": notify_targets}, blocking=True,
                )
                notified = True
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Unable to send HEM native device error to configured notifications")
        tts_engine = config.get(CONF_TTS_ENGINE)
        if (config.get(CONF_AUTO_TTS) is True and tts_engine
                and self.hass.services.has_service("tts", "speak")):
            targets = self.manager._targets_in_room(
                config.get(CONF_MEDIA_PLAYERS, []), spec.area_id
            )
            if targets:
                try:
                    await self.hass.services.async_call(
                        "tts", "speak",
                        {"media_player_entity_id": targets, "message": message},
                        target={"entity_id": tts_engine}, blocking=True,
                    )
                    notified = True
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.exception("Unable to speak HEM native device error")
        # A persistent HA notification is a single per-physical-device visual
        # fallback when no configured native channel could deliver it.
        if not notified and self.hass.services.has_service(
                "persistent_notification", "create"):
            digest = hashlib.sha256(
                f"{self.manager.entry.entry_id}:{spec.source_device_id or spec.identifier}".encode()
            ).hexdigest()[:24]
            try:
                await self.hass.services.async_call(
                    "persistent_notification", "create", {
                        "notification_id": f"hem_native_fault_{digest}",
                        "title": title, "message": message,
                    }, blocking=True,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Unable to show HEM physical device fault in Home Assistant")

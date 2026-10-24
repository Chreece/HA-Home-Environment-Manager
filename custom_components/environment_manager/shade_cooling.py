"""Opt-in, close-only passive solar cooling for native Home Assistant covers.

Only an exact, explicitly selected, same-area indoor window shade may move.
Selection is not authorization: a separate room switch must enable closing.
No automatic OPEN, no commands to awnings/doors/gates/windows, no area
broadcast, and no guessed temperature or sunlight evidence.

A fully evaluated request is revalidated immediately before its one exact
physical close_cover service call. Per-area tasks are independent; a durable
cooldown prevents repeated close attempts or fighting a user's manual reopen.
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any, Callable

from .const import DOMAIN
from .room_sources import (
    selected, native, category, room_temperature_evidence,
    SHADING_COVER_CLASSES, COVER_CLOSE_FEATURE,
)

_LOGGER = logging.getLogger(__name__)

CONF_SHADE_ROOMS = "shade_rooms"
SHADE_NUMBERS = {
    "close_above_c": (18., 36., .5, "°C", 25.),
    "min_sun_elevation": (3., 80., 1., "°", 10.),
}
HOLD_SECONDS = 7200       # Do not fight a manual reopen or retry a failed close.
STARTUP_SECONDS = 60      # Do not start moving covers during restore/startup.


def config(settings: dict, area: str) -> dict:
    room = settings.get(CONF_SHADE_ROOMS, {})
    saved = room.get(area, {}) if isinstance(room, dict) else {}
    saved = saved if isinstance(saved, dict) else {}
    return {
        "enabled": saved.get("enabled") is True,
        **{key: saved.get(key, bounds[4]) for key, bounds in SHADE_NUMBERS.items()},
    }


def _numeric(value: Any, lo: float, hi: float) -> float | None:
    if type(value) not in (float, int) or not math.isfinite(value):
        return None
    return float(value) if lo <= value <= hi else None


def evaluate_conditions(
    *, active: bool, selected_shades: tuple[str, ...],
    temperature_c: float | None, windows: tuple[Any, ...],
    sun_state: Any, threshold: float, min_sun_elevation: float,
) -> tuple[str, dict]:
    """Pure decision; UNKNOWN never authorizes a physical cover command."""
    evidence: dict = {
        "temperature_c": temperature_c,
        "threshold_c": threshold,
        "selected_covers": list(selected_shades),
    }
    if not active:
        return "disabled", evidence
    if not selected_shades:
        return "no_selected_shades", evidence
    if temperature_c is None or not math.isfinite(temperature_c):
        return "temperature_not_verified", evidence
    if temperature_c < threshold:
        return "room_below_cooling_threshold", evidence
    if not windows:
        return "window_contacts_missing", evidence
    if any(getattr(w, "opened", None) is not False for w in windows):
        return "window_open_or_unknown", evidence
    if sun_state is None or getattr(sun_state, "state", None) != "above_horizon":
        return "sun_not_verified", evidence
    elevation = _numeric(getattr(sun_state, "attributes", {}).get("elevation"), -90, 90)
    if elevation is None:
        return "sun_not_verified", evidence
    evidence["sun_elevation"] = elevation
    if elevation < min_sun_elevation:
        return "sun_below_shading_threshold", evidence
    return "closing_recommended", evidence


def eligible_shade(hass: Any, area: str, entity_id: str,
                   explicitly_selected: tuple[str, ...]) -> tuple[bool, str]:
    """Require registered same-room native indoor shade and CLOSE capability."""
    if entity_id not in explicitly_selected or not entity_id.startswith("cover."):
        return False, "not_selected"
    from .discovery import entity_area
    if entity_area(hass, entity_id) != area:
        return False, "cover_wrong_room"
    if not native(hass, entity_id):
        return False, "manager_generated_cover"
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable"):
        return False, "cover_unavailable"
    if category(hass, state) != "shades":
        return False, "unsupported_cover_device_class_or_close_feature"
    return True, "verified_shade"


class ShadeCoolingController:
    """One serialized room task, no automatic opening or position changes."""

    def __init__(self, manager: Any, *, clock: Callable[[], float] | None = None):
        self.manager, self.hass = manager, manager.hass
        self.clock = clock or time.time
        self.statuses: dict[str, dict] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._records: dict[str, dict] = {}
        self._started = self.clock()
        self._active = False
        self._ready = False
        self._store = None

    async def async_start(self):
        self._started = self.clock()
        try:
            from homeassistant.helpers.storage import Store
            self._store = Store(
                self.hass, 1, f"{DOMAIN}.shade_cooling_{self.manager.entry.entry_id}"
            )
            data = await self._store.async_load()
            if data is not None and (
                not isinstance(data, dict) or data.get("version") != 1
                or not isinstance(data.get("records"), dict)
            ):
                raise ValueError("Unknown shade controller store version")
            records = data.get("records", {}) if data else {}
            if any(not isinstance(entity_id, str)
                   or not isinstance(record, dict)
                   or type(record.get("command_at")) not in (float, int)
                   or not math.isfinite(record["command_at"])
                   or record["command_at"] < 0
                   or not isinstance(record.get("area"), str)
                   for entity_id, record in records.items()):
                raise ValueError("Corrupt persisted shade controller records")
            self._records = records
            self._ready = True
        except Exception:
            # Storage unavailable means no safe command log. Never close an
            # actuator without being able to persist a manual-override hold.
            _LOGGER.exception("Shade cooling storage unavailable; automation remains idle")
            self._ready = False
        self._active = True

    def _status(self, area: str, value: str, **data):
        record = {"status": value, **data}
        if self.statuses.get(area) == record:
            return
        self.statuses[area] = record
        if self._active and getattr(self.manager, "_active", False):
            callback = getattr(self.manager, "_shade_updated", None)
            if callable(callback):
                callback()

    def schedule(self) -> None:
        if not self._ready or not self._active:
            return
        settings = self.manager.settings
        areas = settings.get("areas", [])
        if not isinstance(areas, list):
            return
        for area in areas:
            if not isinstance(area, str):
                continue
            if (area in self._tasks and not self._tasks[area].done()):
                continue
            # Include disabled selected shades so the status remains informative.
            if (selected(settings, area, "shades") or ()) or config(settings, area)["enabled"]:
                task = self.hass.async_create_task(self._tick(area))
                self._tasks[area] = task
                task.add_done_callback(lambda result, name=area: self._finished(name, result))

    def _finished(self, area: str, task: asyncio.Task):
        if self._tasks.get(area) is task:
            self._tasks.pop(area, None)
        if not task.cancelled():
            try:
                task.result()
            except Exception:
                _LOGGER.exception("Shade cooling room task failed: %s", area)
                self._status(area, "controller_error")

    async def _tick(self, area: str) -> None:
        settings = self.manager.settings
        if area not in settings.get("areas", []):
            return
        cfg = config(settings, area)
        sources = selected(settings, area, "shades") or ()
        if not cfg["enabled"]:
            self._status(area, "disabled", selected_covers=list(sources))
            return
        # No movement during HA startup/recovery or when other controllers
        # have not established validated room measurements yet.
        if self.clock() - self._started < STARTUP_SECONDS:
            self._status(area, "startup_hold", selected_covers=list(sources))
            return
        temp, reading_evidence = room_temperature_evidence(
            self.hass, settings, area, age_minutes=10
        )
        plan = self.manager.plan
        room = next((r for r in (*plan.rooms, *plan.climate_rooms)
                     if r.area_id == area), None)
        sun = self.hass.states.get("sun.sun")
        reason, details = evaluate_conditions(
            active=cfg["enabled"], selected_shades=sources,
            temperature_c=temp, windows=room.windows if room else (),
            sun_state=sun, threshold=cfg["close_above_c"],
            min_sun_elevation=cfg["min_sun_elevation"],
        )
        details["temperature_evidence"] = reading_evidence
        if reason != "closing_recommended":
            self._status(area, reason, **details)
            return

        # The service is intentionally one close_cover and one explicit
        # entity_id. No alternate set_position, open, area or device fallback.
        service_available = self.hass.services.has_service("cover", "close_cover")
        if not service_available:
            self._status(area, "close_cover_service_unavailable", **details)
            return

        outcomes: dict[str, str] = {}
        for entity_id in sources:
            # Re-read policy and sources at the last possible instant.
            now = self.clock()
            latest = self.manager.settings
            if (area not in latest.get("areas", [])
                    or not config(latest, area)["enabled"]
                    or entity_id not in (selected(latest, area, "shades") or ())):
                outcomes[entity_id] = "authorization_withdrawn"
                continue
            okay, why = eligible_shade(
                self.hass, area, entity_id, selected(latest, area, "shades") or ()
            )
            if not okay:
                outcomes[entity_id] = why
                continue
            state = self.hass.states.get(entity_id)
            if state.state in ("closed", "closing"):
                outcomes[entity_id] = "already_closed_or_closing"
                continue
            # An opening shade is a manual user action. Never fight it.
            if state.state != "open":
                outcomes[entity_id] = "manual_or_unknown_cover_motion"
                continue
            previous = self._records.get(entity_id, {})
            if (previous.get("area") != area
                    and previous.get("command_at") is not None):
                outcomes[entity_id] = "different_previous_room_owner"
                continue
            since = previous.get("command_at")
            if type(since) in (int, float) and now - since < HOLD_SECONDS:
                outcomes[entity_id] = "recent_close_or_manual_reopen_hold"
                continue
            # Recheck temperature, contacts and solar elevation immediately
            # before *each* command. Another automation may have changed the
            # room while we were waiting for the previous shade's ACK.
            current_temp, _ = room_temperature_evidence(
                self.hass, latest, area, age_minutes=10,
            )
            current_room = next((r for r in (*self.manager.plan.rooms,
                                             *self.manager.plan.climate_rooms)
                                 if r.area_id == area), None)
            current_reason, _ = evaluate_conditions(
                active=True, selected_shades=(entity_id,),
                temperature_c=current_temp,
                windows=current_room.windows if current_room else (),
                sun_state=self.hass.states.get("sun.sun"),
                threshold=config(latest, area)["close_above_c"],
                min_sun_elevation=config(latest, area)["min_sun_elevation"],
            )
            if current_reason != "closing_recommended":
                outcomes[entity_id] = current_reason
                continue
            old = self._records.get(entity_id)
            self._records[entity_id] = {"area": area, "command_at": now}
            try:
                if self._store is None:
                    raise RuntimeError("Shade control durable store missing")
                await self._store.async_save({
                    "version": 1, "records": self._records,
                })
            except Exception:
                if old is None:
                    self._records.pop(entity_id, None)
                else:
                    self._records[entity_id] = old
                self._ready = False
                outcomes[entity_id] = "storage_failure_no_command"
                _LOGGER.exception("Shading intent was not persisted; physical command blocked")
                continue
            # The room's exact selected native shade is the *only* target.
            try:
                await self.hass.services.async_call(
                    "cover", "close_cover", {}, target={"entity_id": entity_id},
                    blocking=True,
                )
            except Exception:
                outcomes[entity_id] = "close_service_failed_hold"
                _LOGGER.exception("Shade cooling close command failed: %s", entity_id)
            else:
                outcomes[entity_id] = "close_command_sent"
        status = ("close_command_sent" if "close_command_sent" in outcomes.values()
                  else "already_closed" if outcomes and all(
                      result == "already_closed_or_closing" for result in outcomes.values())
                  else "cooling_hold")
        self._status(area, status, covers=outcomes, **details)

    async def async_stop(self) -> None:
        self._active = False
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

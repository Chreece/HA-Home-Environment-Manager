"""Weather-aware, ownership-safe solar shading with optional pre-movement notices.

Only known, selected, native, same-room indoor shades are eligible. Closing
requires fresh room feedback, safe window contacts, verified solar elevation
and explicitly selected sunny/partly-cloudy weather. Opening requires a
*confirmed prior close* by this exact integration. Manual reopening revokes
ownership persistently until room auto-shading is switched OFF and ON again.

The record is saved BEFORE every physical service action, with a conservative
ACK state machine to avoid claiming ownership merely from service success.
A weather failure or missing announcement always holds without movement.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, Callable

from .const import DOMAIN, CONF_SHADE_ANNOUNCE
from .room_sources import (
    selected, native, category, room_temperature_evidence,
)
from .shade_weather import weather_evidence, HAZARDOUS
from .shade_delivery import async_announce_before_move

_LOGGER = logging.getLogger(__name__)

CONF_SHADE_ROOMS = "shade_rooms"
SHADE_NUMBERS = {
    "close_above_c": (18., 36., .5, "°C", 25.),
    "min_sun_elevation": (3., 80., 1., "°", 10.),
}
HOLD_SECONDS = 7200
STARTUP_SECONDS = 60
ACK_GRACE_SECONDS = 300
OPEN_STABLE_SECONDS = 300
ANNOUNCEMENT_GRACE_SECONDS = 5
COOLING_HYSTERESIS_C = 1.0
STORE_VERSION = 2
OWNED_PHASES = frozenset(("closing_requested", "owned_closed", "opening_requested"))
FINAL_PHASES = frozenset(("manual_override", "released", "legacy_manual_hold", "open_failed_hold"))


def config(settings: dict, area: str) -> dict:
    rooms = settings.get(CONF_SHADE_ROOMS, {})
    saved = rooms.get(area, {}) if isinstance(rooms, dict) else {}
    saved = saved if isinstance(saved, dict) else {}
    revision = saved.get("authorization_revision", 0)
    if type(revision) is not int or revision < 0:
        revision = 0
    return {
        "enabled": saved.get("enabled") is True,
        "authorization_revision": revision,
        **{key: saved.get(key, bounds[4]) for key, bounds in SHADE_NUMBERS.items()},
    }


def _numeric(value: Any, lo: float, hi: float) -> float | None:
    return float(value) if type(value) in (float, int) and math.isfinite(value) and lo <= value <= hi else None


def evaluate_conditions(
    *, active: bool, selected_shades: tuple[str, ...],
    temperature_c: float | None, windows: tuple[Any, ...],
    sun_state: Any, threshold: float, min_sun_elevation: float,
    weather_status: str | None = None,
) -> tuple[str, dict]:
    """Pure sun/window/room close evaluation, weather optional for old callers.

    Production ALWAYS passes verified weather_status. No unknown weather can
    authorize an actual physical command.
    """
    evidence: dict = {
        "temperature_c": temperature_c, "threshold_c": threshold,
        "selected_covers": list(selected_shades),
        "weather_status": weather_status,
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
    if weather_status is not None and weather_status != "weather_solar":
        return weather_status, evidence
    return "closing_recommended", evidence


def eligible_shade(hass: Any, area: str, entity_id: str,
                   explicitly_selected: tuple[str, ...]) -> tuple[bool, str]:
    """Require exact registered same-room native shade with CLOSE support."""
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


def _open_supported(state: Any) -> bool:
    try:
        # CoverEntityFeature.OPEN == 1; no generic toggle or position fallback.
        return bool(int(state.attributes.get("supported_features", 0)) & 1)
    except (TypeError, ValueError, OverflowError, AttributeError):
        return False


def _solar_release_reason(
    *, temp: float | None, threshold: float,
    sun: Any, min_sun_elevation: float, weather: str,
) -> str | None:
    """Return a reason to open previously owned shades; never guess sunlight."""
    if weather == "weather_hazard_hold":
        return None
    if sun is None:
        return None
    if sun.state == "below_horizon":
        return "night"
    if sun.state != "above_horizon":
        return None
    elevation = _numeric(getattr(sun, "attributes", {}).get("elevation"), -90, 90)
    if elevation is None:
        return None
    if elevation < min_sun_elevation:
        return "sun_low"
    if weather == "weather_no_solar_gain":
        return "weather_cloudy"
    if (temp is not None and math.isfinite(temp)
            and temp <= threshold - COOLING_HYSTERESIS_C):
        return "room_cooled"
    return None


class ShadeCoolingController:
    """One independent FIFO task per room and durable physical cover ownership."""

    def __init__(self, manager: Any, *, clock: Callable[[], float] | None = None,
                 announcement_grace_seconds: float = ANNOUNCEMENT_GRACE_SECONDS):
        self.manager, self.hass = manager, manager.hass
        self.clock = clock or time.time
        self.announcement_grace_seconds = max(0., float(announcement_grace_seconds))
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
            self._store = Store(self.hass, 1,
                f"{DOMAIN}.shade_cooling_{self.manager.entry.entry_id}")
            data = await self._store.async_load()
            if data is not None and (
                not isinstance(data, dict)
                or data.get("version") not in (1, STORE_VERSION)
                or not isinstance(data.get("records"), dict)
            ):
                raise ValueError("Unknown shade-controller storage version")
            records = data.get("records", {}) if data else {}
            validated = {}
            for entity, raw in records.items():
                if (not isinstance(entity, str) or not entity.startswith("cover.")
                        or not isinstance(raw, dict)
                        or not isinstance(raw.get("area"), str)
                        or type(raw.get("command_at")) not in (float, int)
                        or not math.isfinite(raw["command_at"])
                        or raw["command_at"] < 0):
                    raise ValueError("Invalid persisted shade controller record")
                record = dict(raw)
                if data.get("version") == 1 or "phase" not in raw:
                    # Beta43 logged attempts but never proved ownership. It is
                    # unsafe to reopen, or re-close a user-opened legacy shade.
                    record["phase"] = "legacy_manual_hold"
                    record["revision"] = config(self.manager.settings, record["area"])[
                        "authorization_revision"]
                if record.get("phase") not in (OWNED_PHASES | FINAL_PHASES):
                    raise ValueError("Unsupported shade owner state")
                revision = record.get("revision")
                if type(revision) is not int or revision < 0:
                    raise ValueError("Invalid shade owner revision")
                validated[entity] = record
            self._records = validated
            self._ready = True
        except Exception:
            _LOGGER.exception("Shade owner history not verified; do not move covers")
            self._ready = False
        self._active = True

    def _status(self, area: str, value: str, **data):
        report = {"status": value, **data}
        if self.statuses.get(area) == report:
            return
        self.statuses[area] = report
        if self._active and getattr(self.manager, "_active", False):
            cb = getattr(self.manager, "_shade_updated", None)
            if callable(cb):
                cb()

    async def _save(self, entity: str, value: dict | None) -> bool:
        original = self._records.get(entity)
        if value is None:
            self._records.pop(entity, None)
        else:
            self._records[entity] = value
        try:
            if not self._ready or self._store is None:
                raise RuntimeError("Durable shade owner store unavailable")
            await self._store.async_save({
                "version": STORE_VERSION, "records": self._records,
            })
        except Exception:
            if original is None:
                self._records.pop(entity, None)
            else:
                self._records[entity] = original
            self._ready = False
            _LOGGER.exception("Shade ownership cannot be saved; hardware held")
            return False
        return True

    def schedule(self) -> None:
        if not self._ready or not self._active:
            return
        for area in self.manager.settings.get("areas", []):
            if not isinstance(area, str):
                continue
            if area in self._tasks and not self._tasks[area].done():
                continue
            if selected(self.manager.settings, area, "shades") or config(self.manager.settings, area)["enabled"]:
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
                _LOGGER.exception("Shade room task failed: %s", area)
                self._status(area, "controller_error")

    def _inputs(self, area: str, settings: dict) -> tuple[str, dict, Any, Any, float | None, tuple]:
        cfg = config(settings, area)
        sources = selected(settings, area, "shades") or ()
        temp, evidence = room_temperature_evidence(
            self.hass, settings, area, age_minutes=10)
        weather_status, weather = weather_evidence(self.hass, settings)
        plan = self.manager.plan
        room = next((r for r in (*plan.rooms, *plan.climate_rooms)
                     if r.area_id == area), None)
        windows = room.windows if room else ()
        # The plan is an input summary, but read the exact native contacts
        # again just before acting. No state-update lag may permit movement
        # while a real window was opened in the meantime.
        safe_contacts = bool(windows)
        for window in windows:
            physical = self.hass.states.get(window.entity_id)
            if (getattr(window, "opened", None) is not False or
                    physical is None or physical.state not in ("off", "closed")):
                safe_contacts = False
        sun = self.hass.states.get("sun.sun")
        close_reason, details = evaluate_conditions(
            active=cfg["enabled"], selected_shades=sources,
            temperature_c=temp, windows=windows, sun_state=sun,
            threshold=cfg["close_above_c"],
            min_sun_elevation=cfg["min_sun_elevation"],
            weather_status=weather_status,
        )
        if not safe_contacts and windows:
            close_reason = "window_open_or_unknown"
        details.update(weather)
        details["temperature_evidence"] = evidence
        details["window_safe"] = safe_contacts
        details["close_reason"] = close_reason
        return close_reason, details, sun, cfg, temp, windows

    @staticmethod
    def _day(at: float) -> str:
        return datetime.fromtimestamp(at, timezone.utc).strftime("%Y-%m-%d")

    async def _before_move(self, area: str, action: str, entity: str,
                           revision: int) -> bool:
        """Queue configured announcement, then allow time to be noticed.

        All physical state/conditions are rechecked AFTER this point.
        """
        if self.manager.settings.get(CONF_SHADE_ANNOUNCE) is not True:
            return True
        ok = await async_announce_before_move(self.manager, area=area, action=action)
        if not ok:
            return False
        if self.announcement_grace_seconds:
            await asyncio.sleep(self.announcement_grace_seconds)
        return (area in self.manager.settings.get("areas", [])
                and entity in (selected(self.manager.settings, area, "shades") or ())
                and config(self.manager.settings, area)["enabled"]
                and config(self.manager.settings, area)["authorization_revision"] == revision)

    async def _tick(self, area: str):
        settings = self.manager.settings
        if area not in settings.get("areas", []):
            return
        cfg = config(settings, area)
        sources = selected(settings, area, "shades") or ()
        if not cfg["enabled"]:
            self._status(area, "disabled", selected_covers=list(sources))
            return
        if not self._ready:
            self._status(area, "storage_not_ready", selected_covers=list(sources))
            return
        if self.clock() - self._started < STARTUP_SECONDS:
            self._status(area, "startup_hold", selected_covers=list(sources))
            return

        close_reason, details, sun, cfg, temp, windows = self._inputs(area, settings)
        outcomes = {}
        for entity in sources:
            now = self.clock()
            latest = self.manager.settings
            revision = config(latest, area)["authorization_revision"]
            if (area not in latest.get("areas", [])
                    or not config(latest, area)["enabled"]
                    or entity not in (selected(latest, area, "shades") or ())):
                outcomes[entity] = "authorization_withdrawn"
                continue
            ok, why = eligible_shade(self.hass, area, entity, sources)
            if not ok:
                outcomes[entity] = why
                continue
            state = self.hass.states.get(entity)
            record = self._records.get(entity)

            if record is not None and record.get("revision") != revision:
                # Manual override resets only with an explicit re-enable; a
                # prior valid ownership record is NEVER adopted as new.
                if not await self._save(entity, None):
                    outcomes[entity] = "storage_failure_no_command"
                    continue
                record = None

            phase = record.get("phase") if record else None
            if phase in ("legacy_manual_hold", "manual_override", "open_failed_hold"):
                outcomes[entity] = phase
                continue
            if phase == "released":
                # No re-closing the same day after our own automatic opening.
                # Next calendar day permits a fresh independent cycle.
                if record.get("day") == self._day(now):
                    outcomes[entity] = "released_for_today"
                    continue
                if not await self._save(entity, None):
                    outcomes[entity] = "storage_failure_no_command"
                    continue
                record = None
                phase = None

            if phase == "closing_requested":
                if state.state == "closed":
                    saved = {**record, "phase": "owned_closed", "close_confirmed_at": now}
                    if not await self._save(entity, saved):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    record, phase = saved, "owned_closed"
                elif state.state == "opening":
                    if not await self._save(entity, {**record, "phase": "manual_override"}):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    outcomes[entity] = "manual_override"
                    continue
                elif now-record["command_at"] < ACK_GRACE_SECONDS:
                    outcomes[entity] = "awaiting_close_confirmation"
                    continue
                else:
                    if not await self._save(entity, {**record, "phase": "manual_override"}):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    outcomes[entity] = "unconfirmed_close_manual_hold"
                    continue

            if phase == "opening_requested":
                if state.state == "open":
                    if not await self._save(entity, {
                        **record, "phase": "released", "day": self._day(now),
                    }):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    outcomes[entity] = "automatically_opened"
                elif state.state == "closed" and now-record["command_at"] >= ACK_GRACE_SECONDS:
                    if not await self._save(entity, {**record, "phase": "open_failed_hold"}):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    outcomes[entity] = "open_failed_hold"
                else:
                    outcomes[entity] = "awaiting_open_confirmation"
                continue

            if phase == "owned_closed":
                if state.state in ("opening", "open"):
                    if not await self._save(entity, {**record, "phase": "manual_override"}):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    outcomes[entity] = "manual_override"
                    continue
                if state.state != "closed":
                    outcomes[entity] = "cover_state_uncertain_hold"
                    continue
                reason = _solar_release_reason(
                    temp=temp, threshold=cfg["close_above_c"], sun=sun,
                    min_sun_elevation=cfg["min_sun_elevation"],
                    weather=details["close_reason"] if False else
                        ("weather_hazard_hold" if
                          details.get("weather_status") == "weather_hazard_hold" else
                          details.get("weather_status")),
                )
                # Above uses evidence from the same weather check that
                # decided closure; never treat an unknown report as sunny.
                if reason is None:
                    outcomes[entity] = "owned_closed_weather_still_warrants_shade"
                    continue
                if not details["window_safe"]:
                    outcomes[entity] = "open_blocked_window_contact"
                    continue
                if not _open_supported(state):
                    outcomes[entity] = "open_not_supported"
                    continue
                if not self.hass.services.has_service("cover", "open_cover"):
                    outcomes[entity] = "open_service_unavailable"
                    continue
                # Only confirmed, previously-owned closed shades may reopen.
                # A stable benign weather state avoids flapping on passing
                # clouds. A verified sunset can open immediately.
                since = record.get("release_since")
                if reason != "night" and (
                    record.get("release_reason") != reason
                    or type(since) not in (float, int)
                ):
                    updated = {**record, "release_since": now,
                               "release_reason": reason}
                    if not await self._save(entity, updated):
                        outcomes[entity] = "storage_failure_no_command"
                        continue
                    outcomes[entity] = "waiting_for_stable_release"
                    continue
                if reason != "night" and now-since < OPEN_STABLE_SECONDS:
                    outcomes[entity] = "waiting_for_stable_release"
                    continue

                if not await self._before_move(area, "open", entity, revision):
                    outcomes[entity] = "announcement_unavailable_hold"
                    continue
                new_reason, new_details, new_sun, new_cfg, new_temp, _ = self._inputs(
                    area, self.manager.settings)
                newer = self.hass.states.get(entity)
                decision = _solar_release_reason(
                    temp=new_temp,threshold=new_cfg["close_above_c"],sun=new_sun,
                    min_sun_elevation=new_cfg["min_sun_elevation"],
                    weather=new_details.get("weather_status"),
                )
                valid, _ = eligible_shade(self.hass, area, entity,
                    selected(self.manager.settings, area, "shades") or ())
                if (not valid or decision != reason
                        or not new_details["window_safe"]
                        or newer is None or newer.state != "closed"
                        or not _open_supported(newer)
                        or self._records.get(entity, {}).get("phase") != "owned_closed"):
                    outcomes[entity] = "conditions_changed_after_announcement"
                    continue
                updated = {
                    **self._records[entity], "phase": "opening_requested",
                    "command_at": self.clock(),
                }
                if not await self._save(entity, updated):
                    outcomes[entity] = "storage_failure_no_command"
                    continue
                try:
                    await self.hass.services.async_call(
                        "cover", "open_cover", {},
                        target={"entity_id": entity}, blocking=True)
                except Exception:
                    outcomes[entity] = "open_command_failed_hold"
                    _LOGGER.exception("Previously owned shade open failed: %s", entity)
                else:
                    outcomes[entity] = "open_command_sent"
                continue

            # Unknown/pre-owned closed shades are never opened. A new close
            # must be explicitly safe and permitted, not a replay of b43.
            if state.state in ("closed", "closing"):
                outcomes[entity] = "not_owned_already_closed"
                continue
            if state.state != "open":
                outcomes[entity] = "manual_or_unknown_cover_motion"
                continue
            if close_reason != "closing_recommended" or not details["window_safe"]:
                outcomes[entity] = close_reason
                continue
            if (record and now-record.get("command_at", now) < HOLD_SECONDS):
                outcomes[entity] = "recent_close_hold"
                continue
            if not self.hass.services.has_service("cover", "close_cover"):
                outcomes[entity] = "close_service_unavailable"
                continue
            if not await self._before_move(area, "close", entity, revision):
                outcomes[entity] = "announcement_unavailable_hold"
                continue
            new_reason, new_details, _, new_cfg, _, _ = self._inputs(
                area, self.manager.settings)
            newer = self.hass.states.get(entity)
            valid, _ = eligible_shade(self.hass, area, entity,
                selected(self.manager.settings, area, "shades") or ())
            if (not valid or new_reason != "closing_recommended"
                    or not new_details["window_safe"] or newer is None
                    or newer.state != "open" or
                    self._records.get(entity, {}).get("phase") in (
                        "manual_override", "legacy_manual_hold")):
                outcomes[entity] = "conditions_changed_after_announcement"
                continue
            attempt = {
                "area": area, "command_at": self.clock(),
                "revision": revision, "phase": "closing_requested",
            }
            if not await self._save(entity, attempt):
                outcomes[entity] = "storage_failure_no_command"
                continue
            try:
                await self.hass.services.async_call(
                    "cover", "close_cover", {},
                    target={"entity_id": entity}, blocking=True,
                )
            except Exception:
                outcomes[entity] = "close_service_failed_hold"
                _LOGGER.exception("Shade cooling close failed: %s", entity)
            else:
                outcomes[entity] = "close_command_sent"

        status = (
            "open_command_sent" if "open_command_sent" in outcomes.values() else
            "close_command_sent" if "close_command_sent" in outcomes.values() else
            "manual_override" if "manual_override" in outcomes.values() else
            "owned_closed" if "owned_closed_weather_still_warrants_shade" in outcomes.values() else
            "cooling_hold"
        )
        self._status(area, status, covers=outcomes, **details)

    async def async_stop(self):
        self._active = False
        jobs = list(self._tasks.values())
        for job in jobs:
            job.cancel()
        if jobs:
            await asyncio.gather(*jobs, return_exceptions=True)
        self._tasks.clear()

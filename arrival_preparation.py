"""Entry-scoped, expiring Home targets for a deliberately requested arrival.

The stored deadline grants no device ownership and never changes a presence
sensor. Every control boundary still needs current, confirmed whole-home Away.
"""
from __future__ import annotations

import asyncio
import logging
import math
from time import time
from typing import Any

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CONF_TIMEOUT = "arrival_preparation_timeout_minutes"
DEFAULT_TIMEOUT = 60
MIN_TIMEOUT = 1
MAX_TIMEOUT = 1440
DATA_KEY = f"{DOMAIN}_arrival_preparation"
ENTITY_SUFFIXES = {
    "prepare": ("button", "prepare_for_arrival"),
    "cancel": ("button", "cancel_arrival_preparation"),
    "timeout": ("number", "arrival_preparation_timeout"),
}


def automatic_eligible(config: dict) -> bool:
    """Explicit presets and manual/off/other controllers retain authority."""
    return (config.get("control_mode") in ("automatic", "pid")
            and config.get("preset", "none") in (None, "none"))


def room_eligible(config: dict) -> bool:
    """A legacy room's explicit profile or OFF is never a preparation target."""
    return (config.get("manual_profile") not in
            ("comfort", "home", "away", "sleep", "eco")
            and config.get("mode", "auto") != "off")


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


class ArrivalPreparation:
    """A durable absolute deadline, independently revocable before any await."""

    def __init__(self, manager: Any, *, store=None, clock=None, schedule=None):
        self.manager = manager
        self.hass = manager.hass
        self.entry_id = manager.entry.entry_id
        self.clock = clock or time
        self._store = store
        self._schedule = schedule
        self._lock = asyncio.Lock()
        self._started = False
        self._started_at: float | None = None
        self.expires_at: float | None = None
        self._generation = 0
        self._timer_generation = 0
        self._preparing = False
        self._cancel_timer = None
        self._tasks: set[asyncio.Task] = set()

    @property
    def timeout_minutes(self) -> int:
        raw = _finite(self.manager.settings.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        if raw is None or not raw.is_integer() or not MIN_TIMEOUT <= raw <= MAX_TIMEOUT:
            return DEFAULT_TIMEOUT
        return int(raw)

    def home_status(self) -> str:
        """Use the same current shared sources and legacy trackers as planning."""
        from .occupancy_policy import home_presence, shared_home_settings
        settings = self.manager.settings
        shared = shared_home_settings(
            settings.get("occupancy_global", {}), settings.get("climate_rooms", {}),
        )
        continuity = getattr(self.manager, "presence_continuity", None)
        if continuity is not None:
            shared = continuity.context(shared)
        return home_presence(self.hass, shared)[0]

    @property
    def armed(self) -> bool:
        return bool(self._started and self.expires_at is not None
                    and self.clock() < self.expires_at)

    def active_for(self, home_status: str) -> bool:
        """A timer alone is not evidence that the home is still empty."""
        return self.armed and home_status == "away"

    def context(self, home_status: str, *, eligible: bool = True) -> dict:
        active = (eligible and self.active_for(home_status)
                  and self.home_status() == "away")
        return {
            "arrival_preparing": active,
            "arrival_preparation_entry_id": self.entry_id,
            "arrival_preparation_expires_at": self.expires_at if active else None,
        }

    def entity_ids(self) -> dict[str, str | None]:
        """Resolve registry IDs, including user renames, for exactly this entry."""
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.hass)
        result = {}
        for role, (platform, suffix) in ENTITY_SUFFIXES.items():
            unique_id = f"{self.entry_id}_{suffix}"
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
            record = registry.async_get(entity_id) if entity_id else None
            result[role] = (entity_id if record is not None
                            and record.config_entry_id == self.entry_id
                            and record.platform == DOMAIN
                            and record.unique_id == unique_id else None)
        return result

    def snapshot(self) -> dict:
        home = self.home_status()
        return {
            "entry_id": self.entry_id,
            "active": self.armed and home != "home",
            "can_start": self._started and self._store is not None and home == "away",
            "expires_at": self.expires_at if self.armed and home != "home" else None,
            "remaining_seconds": max(0, math.ceil(self.expires_at - self.clock()))
            if self.armed and home != "home" else 0,
            "timeout_minutes": self.timeout_minutes,
            "home_status": home,
            "entity_ids": self.entity_ids(),
        }

    def _stored(self) -> dict:
        return {"started_at": self._started_at, "expires_at": self.expires_at}

    def _changed(self) -> None:
        if self._started and getattr(self.manager, "_active", False):
            self.manager._recalculate()

    def _clear(self) -> bool:
        self._generation += 1
        had_deadline = self.expires_at is not None
        self._started_at = self.expires_at = None
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        return had_deadline

    def _persist_later(self) -> None:
        async def save_current():
            async with self._lock:
                if self._store is not None:
                    try:
                        await self._store.async_save(self._stored())
                    except Exception:
                        _LOGGER.exception("Could not save arrival preparation expiry")
        task = self.hass.async_create_task(save_current())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def observe(self, home_status: str) -> None:
        """Arrival ends the episode; unknown sources only suspend its effect."""
        if self._preparing and home_status != "away":
            self._generation += 1
        if self.expires_at is not None and (
            home_status == "home" or self.clock() >= self.expires_at
        ):
            self._clear()
            self._persist_later()

    def observe_current(self) -> None:
        """Revoke an observed arrival before coalescing a room-plan refresh."""
        if self.expires_at is not None or self._preparing:
            self.observe(self.home_status())

    def _arm_timer(self) -> None:
        if self._cancel_timer is not None:
            self._cancel_timer()
        if self.expires_at is None or not self._started:
            self._cancel_timer = None
            return
        if self._schedule is None:
            from homeassistant.helpers.event import async_call_later
            self._schedule = async_call_later
        self._timer_generation += 1
        deadline, generation = self.expires_at, self._timer_generation

        from homeassistant.core import callback
        @callback
        def expire(_now):
            if (not self._started or self.expires_at != deadline
                    or self._timer_generation != generation):
                return
            self._cancel_timer = None
            # A wall-clock correction must not expire a still-future deadline.
            if self.clock() < deadline:
                self._arm_timer()
                return
            self._clear()
            self._persist_later()
            self._changed()

        self._cancel_timer = self._schedule(
            self.hass, max(0, deadline - self.clock()), expire,
        )

    async def async_start(self) -> None:
        if self._store is None:
            try:
                from homeassistant.helpers.storage import Store
            except ImportError:
                # Pure policy test environments may omit Home Assistant storage.
                self._started = True
                self.hass.data.setdefault(DATA_KEY, {})[self.entry_id] = self
                return
            self._store = Store(self.hass, 1, f"{DOMAIN}.arrival_preparation_{self.entry_id}")
        try:
            stored = await self._store.async_load()
        except Exception:
            _LOGGER.exception("Could not restore arrival preparation deadline")
            stored = None
        if isinstance(stored, dict):
            start, end = _finite(stored.get("started_at")), _finite(stored.get("expires_at"))
            now = self.clock()
            if (start is not None and end is not None and start <= now < end
                    and 0 < end - start <= MAX_TIMEOUT * 60):
                self._started_at, self.expires_at = start, end
        self._started = True
        self.hass.data.setdefault(DATA_KEY, {})[self.entry_id] = self
        self.observe(self.home_status())
        self._arm_timer()

    async def async_prepare(self) -> None:
        from homeassistant.exceptions import HomeAssistantError
        async with self._lock:
            if not self._started or self._store is None:
                raise HomeAssistantError("Arrival preparation is not ready")
            if self.home_status() != "away":
                raise HomeAssistantError("Arrival preparation requires confirmed whole-home absence")
            generation = self._generation
            start = self.clock()
            end = start + self.timeout_minutes * 60
            self._preparing = True
            try:
                # Publish authority only after the original deadline is durable.
                await self._store.async_save({"started_at": start, "expires_at": end})
                if (not self._started or generation != self._generation
                        or self.home_status() != "away" or self.clock() >= end):
                    await self._store.async_save(self._stored())
                    return
                self._started_at, self.expires_at = start, end
                self._generation += 1
                self._arm_timer()
            finally:
                self._preparing = False
        self._changed()

    async def async_cancel(self) -> None:
        # Revoke before waiting for another save or controller task to finish.
        self._clear()
        self._changed()
        async with self._lock:
            if self._store is not None:
                await self._store.async_save(self._stored())

    async def async_stop(self) -> None:
        self._started = False
        self._generation += 1
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        registry = self.hass.data.get(DATA_KEY, {})
        if registry.get(self.entry_id) is self:
            registry.pop(self.entry_id, None)
        # Preserve the absolute future deadline. Reload never renews it.
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        # An in-flight Prepare must finish or roll back its persisted intent
        # before a replacement manager can load the same entry-scoped Store.
        async with self._lock:
            pass


def live_preparation(hass: Any, plan: dict, home_status: str, *,
                     eligible: bool = True,
                     entry_id: str | None = None) -> tuple[bool, str | None]:
    """Validate the entry, deadline and eligibility of a queued control plan."""
    planned_entry = plan.get("arrival_preparation_entry_id")
    if entry_id is not None and planned_entry is not None and planned_entry != entry_id:
        return False, "arrival_preparation_changed"
    if not isinstance(planned_entry, str):
        return False, "arrival_preparation_changed" if plan.get("arrival_preparing") else None
    registry = getattr(hass, "data", {}).get(DATA_KEY, {})
    controller = registry.get(planned_entry)
    live_home = controller.home_status() if controller is not None else home_status
    if (controller is not None and controller.armed and eligible
            and (home_status == "unknown" or live_home == "unknown")):
        return False, "house_occupancy_unknown"
    active = bool(controller is not None and eligible
                  and controller.active_for(home_status)
                  and live_home == "away")
    if (bool(plan.get("arrival_preparing")) != active
            or active and plan.get("arrival_preparation_expires_at") != controller.expires_at):
        return False, "arrival_preparation_changed"
    return active, None

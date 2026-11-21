"""Bounded room-local airing time after a verified response to OPEN advice.

Only the presentation/delivery of CLOSE advice is delayed. Window contacts,
outside evidence and every physical controller's safety inputs are unchanged.
An offer is consumed by the first closed-to-open transition; neither further
openings nor repeated observations can restart that airing interval.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import islice
import logging
from math import isfinite
from time import time
from typing import Any, Callable

from .const import (
    CONF_WINDOW_CLOSE_COOLDOWN_MINUTES, DEFAULT_WINDOW_CLOSE_COOLDOWN_MINUTES,
    MAX_WINDOW_CLOSE_COOLDOWN_MINUTES, CONF_EXCLUDED_WINDOWS, DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
MAX_ROOMS = 128
MAX_CONTACTS = 128
OFFER_MAX_AGE_SECONDS = 10 * 60


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if isfinite(value) else None
    except (ValueError, OverflowError):
        return None


@dataclass
class _Offer:
    contacts: tuple[str, ...]
    offered_at: float


@dataclass
class _Episode:
    contacts: tuple[str, ...]
    opened_at: float
    until: float


class WindowCloseCooldown:
    """One expiry timer and a small journal per integration entry."""

    def __init__(self, manager: Any, *, clock: Callable[[], float] = time,
                 schedule: Callable | None = None, binding: Callable | None = None):
        self.manager = manager
        self.clock = clock
        self._schedule = schedule
        self._binding = binding
        self._offers: dict[str, _Offer] = {}
        self._episodes: dict[str, _Episode] = {}
        self._observed: dict[str, dict[str, bool | None]] = {}
        self._owners: dict[str, str] = {}
        self._last_clock: float | None = None
        self._timer_until: float | None = None
        self._cancel_timer: Callable | None = None
        self._store: Any | None = None
        self._restored = False
        self._stopped = False

    def _seconds(self) -> float:
        raw = self.manager.settings.get(
            CONF_WINDOW_CLOSE_COOLDOWN_MINUTES, DEFAULT_WINDOW_CLOSE_COOLDOWN_MINUTES)
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            value = float("nan")
        if (isinstance(raw, bool) or not isfinite(value) or not value.is_integer()
                or not 0 <= value <= MAX_WINDOW_CLOSE_COOLDOWN_MINUTES):
            value = DEFAULT_WINDOW_CLOSE_COOLDOWN_MINUTES
        return value * 60

    def _now(self) -> float | None:
        now = _number(self.clock())
        if (now is None or now < 0 or self._last_clock is not None
                and now < self._last_clock):
            self._offers.clear()
            self._episodes.clear()
            self._observed.clear()
            self._owners.clear()
            self._sync_timer()
            self._save_later()
            self._last_clock = now if now is not None and now >= 0 else None
            return None
        self._last_clock = now
        return now

    def _valid_binding(self, area: str, contacts: tuple[str, ...], *,
                       allow_missing: bool = False) -> bool:
        if self._binding is not None:
            return bool(self._binding(area, contacts))
        from .discovery import entity_area, is_window_contact
        from .room_sources import selected
        configured = selected(self.manager.settings, area, "windows")
        if isinstance(configured, (list, tuple)) and any(
                not isinstance(entity, str) for entity in configured):
            return False
        explicit = set(configured) if isinstance(configured, (list, tuple)) else set()
        if isinstance(configured, (list, tuple)) and explicit != set(contacts):
            return False
        excluded = self.manager.settings.get(CONF_EXCLUDED_WINDOWS, ())
        if isinstance(excluded, (list, tuple, set)) and any(
                entity in excluded for entity in contacts):
            return False
        for entity in contacts:
            state = self.manager.hass.states.get(entity)
            if entity_area(self.manager.hass, entity) != area:
                return False
            if state is None:
                if not allow_missing:
                    return False
                # A restored interval can precede its source integration's
                # live states. Registry identity, area and type still prove
                # its binding; absence alone must not erase the deadline.
                from homeassistant.helpers import entity_registry as er
                from .discovery import OPTIONAL_WINDOW_CONTACT_CLASSES
                record = er.async_get(self.manager.hass).async_get(entity)
                kind = str(getattr(record, "device_class", None) or
                           getattr(record, "original_device_class", None) or "").casefold()
                if not (kind == "window" or entity in explicit
                        and kind in OPTIONAL_WINDOW_CONTACT_CLASSES):
                    return False
            elif not is_window_contact(self.manager.hass, state,
                                       explicitly_selected=entity in explicit):
                return False
        return bool(contacts)

    def _refresh(self, now: float) -> None:
        seconds = self._seconds()
        changed = False
        for area, episode in tuple(self._episodes.items()):
            # Test the previous deadline before applying a larger preference:
            # an expired interval cannot be resurrected by a settings edit.
            if seconds <= 0 or not episode.opened_at <= now < episode.until:
                del self._episodes[area]
                changed = True
                continue
            until = episode.opened_at + seconds
            if now >= until:
                del self._episodes[area]
                changed = True
            elif episode.until != until:
                episode.until = until
                changed = True
        for area, offer in tuple(self._offers.items()):
            if seconds <= 0 or not 0 <= now - offer.offered_at <= OFFER_MAX_AGE_SECONDS:
                del self._offers[area]
        if changed:
            self._save_later()
        self._sync_timer()

    def _start(self, area: str, entity: str, now: float) -> None:
        offer = self._offers.get(area)
        if (area in self._episodes or offer is None or entity not in offer.contacts
                or not 0 <= now - offer.offered_at <= OFFER_MAX_AGE_SECONDS
                or self._seconds() <= 0 or not self._valid_binding(area, offer.contacts)):
            return
        self._offers.pop(area, None)
        self._episodes[area] = _Episode(offer.contacts, now, now + self._seconds())
        self._save_later()
        self._sync_timer()

    def state_changed(self, entity: str, old: Any, new: Any) -> None:
        """Capture real transitions before asynchronous delivery can resume."""
        if self._stopped or entity not in self._owners:
            return
        now = self._now()
        if now is None:
            return
        self._refresh(now)
        area = self._owners[entity]
        before, after = getattr(old, "state", None), getattr(new, "state", None)
        if before == "off" and after == "on":
            self._start(area, entity, now)
        states = self._observed.get(area, {})
        states[entity] = True if after == "on" else False if after == "off" else None
        if area in self._episodes and states and all(value is False for value in states.values()):
            del self._episodes[area]
            self._save_later()
            self._sync_timer()

    def blocks(self, area: str) -> bool:
        """Recheck live deadlines at an announcement's final dispatch boundary."""
        if self._stopped:
            return False
        now = self._now()
        if now is None:
            return False
        previous = set(self._episodes)
        self._refresh(now)
        if previous.difference(self._episodes) and getattr(self.manager, "_active", False):
            # A transport can resume just before the scheduled expiry callback.
            # Do not cancel that callback and leave an already filtered plan
            # in place until the next unrelated sensor update.
            self.manager._recalculate()
        episode = self._episodes.get(area)
        if episode is not None and not self._valid_binding(
                area, episode.contacts, allow_missing=True):
            del self._episodes[area]
            self._save_later()
            self._sync_timer()
            if getattr(self.manager, "_active", False):
                self.manager._recalculate()
            return False
        return episode is not None

    def prepare(self, plan: Any) -> Any:
        if self._stopped:
            return plan
        now = self._now()
        if now is None:
            return plan
        self._refresh(now)
        snapshots: dict[str, dict[str, bool | None]] = {}
        owners: dict[str, str] = {}
        ambiguous: set[str] = set()
        for room in (*plan.rooms, *plan.climate_rooms):
            area = room.area_id
            if not isinstance(area, str) or not area or len(snapshots) >= MAX_ROOMS:
                continue
            states = {w.entity_id: w.opened for w in room.windows
                      if isinstance(w.entity_id, str) and w.entity_id.startswith("binary_sensor.")
                      and len(w.entity_id) <= 256}
            episode = self._episodes.get(area)
            if episode is not None:
                missing = set(episode.contacts).difference(states)
                if (missing and all(self.manager.hass.states.get(entity) is None
                                    for entity in missing)
                        and self._valid_binding(area, episode.contacts, allow_missing=True)):
                    # Explicit selections already carry unknown placeholders.
                    # Legacy discovery omits not-yet-loaded contacts; retain
                    # those only in this bounded journal, without inventing
                    # an opening or changing the physical room snapshot.
                    states.update((entity, None) for entity in missing)
            if not states or len(states) > MAX_CONTACTS:
                continue
            snapshots[area] = states
            for entity in states:
                if entity in owners and owners[entity] != area:
                    ambiguous.add(entity)
                owners[entity] = area
        for area, states in tuple(snapshots.items()):
            if ambiguous.intersection(states):
                del snapshots[area]
        self._owners = {entity: area for entity, area in owners.items()
                        if entity not in ambiguous and area in snapshots}

        changed = False
        for area in set(self._offers) | set(self._episodes):
            states = snapshots.get(area, {})
            contacts = tuple(sorted(states))
            record = self._episodes.get(area) or self._offers.get(area)
            if (not contacts or record.contacts != contacts
                    or not self._valid_binding(area, contacts,
                                               allow_missing=area in self._episodes)):
                self._offers.pop(area, None)
                changed = self._episodes.pop(area, None) is not None or changed
                continue
            if area in self._episodes:
                if all(value is False for value in states.values()):
                    del self._episodes[area]
                    changed = True
            else:
                previous = self._observed.get(area, {})
                for entity, opened in states.items():
                    if opened is True and previous.get(entity) is False:
                        self._start(area, entity, now)
                        break

        self._observed = snapshots
        if self._seconds() > 0:
            for rec in (*plan.recommendations, *plan.climate_recommendations):
                states = snapshots.get(rec.area_id, {})
                contacts = tuple(sorted(states))
                if (rec.action == "open" and rec.area_id not in self._episodes
                        and contacts and all(value is False for value in states.values())
                        and tuple(sorted(w.entity_id for w in rec.windows)) == contacts
                        and all(w.opened is False for w in rec.windows)
                        and self._valid_binding(rec.area_id, contacts)):
                    self._offers[rec.area_id] = _Offer(contacts, now)
        if changed:
            self._save_later()
        self._sync_timer()
        if not self._episodes:
            return plan

        def allowed(rec):
            return rec.action != "close" or rec.area_id not in self._episodes

        recommendations = tuple(filter(allowed, plan.recommendations))
        climate_recommendations = tuple(filter(allowed, plan.climate_recommendations))
        all_notices = (*recommendations, *climate_recommendations)
        status = ("close" if any(rec.action == "close" for rec in all_notices)
                  else "open" if any(rec.action == "open" for rec in all_notices)
                  else "idle" if plan.outdoor_safe else "blocked")
        environment = dict(plan.environment)
        for area, episode in self._episodes.items():
            raw = environment.get(area, {})
            payload = dict(raw) if isinstance(raw, dict) else {}
            payload["window_close_cooldown"] = {
                "active": True, "opened_at": episode.opened_at, "until": episode.until,
                "window_entities": list(episode.contacts),
            }
            ventilation = payload.get("room_ventilation")
            if isinstance(ventilation, dict) and ventilation.get(
                    "window_energy_status") == "close_window_to_save_energy":
                # The card also renders this independent energy-loss advice.
                # Keep its measured evidence, but hold its actionable status.
                payload["room_ventilation"] = {
                    **ventilation, "window_energy_status": "opening_cooldown",
                }
            environment[area] = payload
        return replace(plan, status=status, recommendations=recommendations,
                       climate_recommendations=climate_recommendations, environment=environment)

    def _sync_timer(self) -> None:
        deadline = min((item.until for item in self._episodes.values()), default=None)
        if self._stopped:
            deadline = None
        if deadline == self._timer_until:
            return
        if self._cancel_timer is not None:
            self._cancel_timer()
        self._timer_until, self._cancel_timer = deadline, None
        if deadline is None:
            return

        def expired(_now=None):
            if self._stopped or self._timer_until != deadline:
                return
            self._timer_until, self._cancel_timer = None, None
            if getattr(self.manager, "_active", False):
                self.manager._recalculate()

        seconds = max(0, deadline - self.clock())
        if self._schedule is not None:
            self._cancel_timer = self._schedule(seconds, expired)
        else:
            from homeassistant.core import callback
            from homeassistant.helpers.event import async_call_later
            self._cancel_timer = async_call_later(self.manager.hass, seconds, callback(expired))

    def snapshot(self) -> dict:
        return {
            "saved_at": self.clock(),
            "rooms": {area: {"contacts": list(item.contacts), "opened_at": item.opened_at,
                             "until": item.until} for area, item in self._episodes.items()},
        }

    def restore(self, data: Any) -> None:
        """Restore only still-active intervals, never offers or inferred openings."""
        self._episodes.clear()
        self._offers.clear()
        now = self._now()
        if now is None or not isinstance(data, dict) or self._seconds() <= 0:
            return
        saved_at = _number(data.get("saved_at"))
        rooms = data.get("rooms")
        if saved_at is None or not 0 <= saved_at <= now or not isinstance(rooms, dict):
            return
        for area, raw in islice(rooms.items(), MAX_ROOMS):
            if not isinstance(area, str) or not area or len(area) > 256 or not isinstance(raw, dict):
                continue
            opened, until = _number(raw.get("opened_at")), _number(raw.get("until"))
            contacts = raw.get("contacts")
            if (opened is None or until is None
                    or not 0 <= opened <= saved_at <= now < until
                    or until - opened > MAX_WINDOW_CLOSE_COOLDOWN_MINUTES * 60
                    or not isinstance(contacts, list) or not 0 < len(contacts) <= MAX_CONTACTS
                    or any(not isinstance(e, str) or not e.startswith("binary_sensor.")
                           or len(e) > 256 for e in contacts)
                    or len(set(contacts)) != len(contacts)):
                continue
            adjusted = opened + self._seconds()
            if now < adjusted:
                self._episodes[area] = _Episode(tuple(sorted(contacts)), opened, adjusted)

    def _save_later(self) -> None:
        if self._store is not None and self._restored and not self._stopped:
            self._store.async_delay_save(self.snapshot, 1)

    async def async_start(self) -> None:
        try:
            from homeassistant.helpers.storage import Store
            self._store = Store(self.manager.hass, 1,
                                f"{DOMAIN}.window_close_cooldown_{self.manager.entry.entry_id}")
            data = await self._store.async_load()
            if not self._stopped:
                self.restore(data)
                self._restored = True
        except ImportError:
            _LOGGER.debug("Home Assistant storage unavailable in test runtime")
        except Exception:
            _LOGGER.exception("Could not restore window advice cooldown")

    def quiesce(self, *, shutdown: bool = False) -> None:
        self._stopped = True
        self._offers.clear()
        self._observed.clear()
        self._owners.clear()
        self._sync_timer()

    async def async_stop(self, *, shutdown: bool = False) -> None:
        self.quiesce(shutdown=shutdown)
        if self._store is not None and self._restored:
            await self._store.async_save(self.snapshot())
        self._episodes.clear()

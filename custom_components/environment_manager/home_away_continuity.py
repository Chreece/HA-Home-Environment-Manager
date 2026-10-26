"""Durable, source-bound evidence for an empty-home Away cooldown.

Home Assistant may give restored source entities new last_changed timestamps.
Store only the start time of a *previously verified* empty-house episode, and
reuse it after a restart solely when the exact selected sources still provide
fresh, mutually consistent negative evidence. Persist no raw presence values
and never turn an unavailable/unknown source into 'away'.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import time
from collections.abc import Mapping
from typing import Any

from .const import DOMAIN
from .occupancy_policy import home_presence

_LOGGER = logging.getLogger(__name__)
VERSION = 1
MAX_CONTINUITY_SECONDS = 7 * 86400
MAX_PENDING_UNKNOWN_SECONDS = 300


def fingerprint(settings: Mapping[str, Any]) -> str:
    """Bind one saved interval to exactly the selected source identities."""
    if not isinstance(settings, Mapping):
        settings = {}
    data = {
        "occupied_rooms_entity": settings.get("occupied_rooms_entity"),
        "occupied_rooms_attribute": settings.get("occupied_rooms_attribute"),
        "room_occupancy_sensors": sorted(set(
            x for x in settings.get("room_occupancy_sensors", ())
            if isinstance(x, str)
        )) if isinstance(settings.get("room_occupancy_sensors"), (list, tuple)) else [],
        "home_trackers": sorted(set(
            x for x in settings.get("home_trackers", ())
            if isinstance(x, str)
        )) if isinstance(settings.get("home_trackers"), (list, tuple)) else [],
    }
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def has_delayed_sources(settings: Mapping[str, Any]) -> bool:
    """The configured cooldown applies only to empty room lists/sensors."""
    return bool(settings.get("occupied_rooms_entity")
                or settings.get("room_occupancy_sensors"))


def _timestamp(value: Any, now: float) -> float | None:
    try:
        stamp = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return stamp if math.isfinite(stamp) and 0 <= now - stamp <= MAX_CONTINUITY_SECONDS else None


def first_verified_empty(hass: Any, settings: Mapping[str, Any], now: float) -> float:
    """Original last transition, bounded by verified live source timestamps."""
    chosen = []
    for key in ("occupied_rooms_entity",):
        source = settings.get(key)
        if isinstance(source, str) and source:
            chosen.append((source, True))
    for key in ("room_occupancy_sensors",):
        for source in settings.get(key, ()) if isinstance(settings.get(key), (list, tuple)) else ():
            if isinstance(source, str):
                chosen.append((source, False))
    # Since the cooldown covers room-list/room sensors, tracker last_changed is
    # not itself the start: a phone can leave before the last room empties.
    stamps = []
    for entity_id, is_list in chosen:
        state = hass.states.get(entity_id)
        if state is None:
            continue
        field = settings.get("occupied_rooms_attribute") if is_list else None
        if is_list and isinstance(field, str) and field not in ("", "__state__"):
            date = getattr(state, "last_updated", None)
        else:
            date = getattr(state, "last_changed", None)
        if isinstance(date, datetime) and date.tzinfo is not None:
            stamp = _timestamp(date.timestamp(), now)
            if stamp is not None:
                stamps.append(stamp)
    return max(stamps) if stamps else now


class HomeAwayContinuity:
    """One observed negative interval; physical control always rechecks live HA."""

    def __init__(self, hass: Any, entry_id: str, *, clock=None) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.clock = clock or time.time
        self._store: Any = None
        self._since: float | None = None
        self._fingerprint: str | None = None
        self._loaded: dict[str, Any] | None = None
        self._unknown_since: float | None = None

    @classmethod
    def restore(cls, hass: Any, entry_id: str, data: Any, *, clock=None):
        instance = cls(hass, entry_id, clock=clock)
        now = instance.clock()
        if (isinstance(data, dict) and data.get("version") == VERSION
                and isinstance(data.get("fingerprint"), str)
                and _timestamp(data.get("since"), now) is not None):
            instance._loaded = {
                "fingerprint": data["fingerprint"],
                "since": float(data["since"]),
            }
        return instance

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "fingerprint": self._fingerprint,
            "since": self._since,
        }

    async def async_start(self) -> None:
        try:
            from homeassistant.helpers.storage import Store
            self._store = Store(
                self.hass, VERSION,
                f"{DOMAIN}.home_away_continuity_{self.entry_id}",
            )
            data = await self._store.async_load()
            restored = self.restore(self.hass, self.entry_id, data, clock=self.clock)
            self._loaded = restored._loaded
        except ImportError:
            _LOGGER.debug("No Home Assistant Store in pure-logic environment")
        except Exception:
            _LOGGER.exception("Away cooldown history could not be read; starting a fresh safe clock")

    def _changed(self) -> None:
        if self._store is not None:
            scheduler = getattr(self._store, "async_delay_save", None)
            if callable(scheduler):
                scheduler(self.snapshot, 1)

    async def async_stop(self) -> None:
        if self._store is not None:
            try:
                await self._store.async_save(self.snapshot())
            except Exception:
                _LOGGER.exception("Could not flush verified-empty cooldown history")

    def settings(self, original: Mapping[str, Any]) -> dict[str, Any]:
        """Decorate live policy with a validated persisted negative start only.

        No cached Away decision is ever returned: every invocation still
        checks today's Person/numeric/room/contact states for positivity and
        availability. A one-time storage failure simply restarts the cooldown.
        """
        raw = dict(original) if isinstance(original, Mapping) else {}
        raw.pop("_verified_empty_since", None)
        if not has_delayed_sources(raw):
            if self._since is not None or self._fingerprint is not None:
                self._since, self._fingerprint, self._loaded = None, None, None
                self._changed()
            return raw

        current_key = fingerprint(raw)
        now = self.clock()
        if self._fingerprint != current_key:
            self._fingerprint, self._since, self._unknown_since = current_key, None, None
            if self._loaded and self._loaded.get("fingerprint") == current_key:
                self._since = _timestamp(self._loaded.get("since"), now)
            self._loaded = None

        immediate = {**raw, "away_cooldown_minutes": 0}
        status, _, _ = home_presence(self.hass, immediate)
        if status == "home":
            self._unknown_since = None
            if self._since is not None:
                self._since = None
                self._changed()
            return raw
        if status != "away":
            if self._unknown_since is None:
                self._unknown_since = now
            elif now - self._unknown_since > MAX_PENDING_UNKNOWN_SECONDS and self._since is not None:
                # A sustained signal outage interrupts the verified-empty
                # episode. Never resume a stale clock after ambiguous evidence.
                self._since = None
                self._changed()
            return raw

        # All selected room/trackers/list evidence has just been revalidated.
        if self._since is None:
            self._since = first_verified_empty(self.hass, raw, now)
            self._changed()
        self._unknown_since = None
        raw["_verified_empty_since"] = self._since
        return raw

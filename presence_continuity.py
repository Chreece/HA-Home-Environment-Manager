"""Restart-safe, source-bound absence evidence for the global Away cooldown.

An HA state entity's last_changed timestamp may be reset when it is recreated
at startup. Keep the *first verified absence* in HA Store across those resets,
but only reuse it when the exact configured sources are unchanged AND every
current relevant source again confirms nobody is home.

No physical actuator writes or inferred positive occupancy. A missing,
unavailable, stale or contradictory source never becomes negative on restart.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from typing import Any

from .occupancy_policy import home_presence

_LOGGER = logging.getLogger(__name__)
DATA_VERSION = 1
MAX_HISTORY_SECONDS = 366 * 24 * 3600


def source_signature(config: dict[str, Any]) -> str:
    """Changing an entity or its source/attribute invalidates old absence."""
    def identities(key: str) -> list[str]:
        selected = config.get(key)
        if not isinstance(selected, list):
            return []
        return sorted(set(value for value in selected if isinstance(value, str) and value))

    fingerprint = {
        "home_trackers": identities("home_trackers"),
        "room_occupancy_sensors": identities("room_occupancy_sensors"),
        "occupied_rooms_entity": config.get("occupied_rooms_entity") or "",
        "occupied_rooms_attribute": config.get("occupied_rooms_attribute") or "__state__",
        "source_stale_minutes": config.get("source_stale_minutes", 240),
    }
    return hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def live_absence_since(hass: Any, config: dict[str, Any], sources: list[str]) -> float:
    """Best observation start for an all-negative set in the current HA run."""
    now = datetime.now(timezone.utc).timestamp()
    stamps: list[float] = []
    attr_entity = config.get("occupied_rooms_entity")
    attr = config.get("occupied_rooms_attribute")
    for entity in sources:
        state = hass.states.get(entity)
        if state is None:
            continue
        change = (
            getattr(state, "last_updated", None)
            if entity == attr_entity and isinstance(attr, str)
            and attr not in ("", "__state__")
            else getattr(state, "last_changed", None)
        )
        if not isinstance(change, datetime) or change.tzinfo is None:
            continue
        stamp = change.timestamp()
        if math.isfinite(stamp) and 0 < stamp <= now:
            stamps.append(stamp)
    return max(stamps) if stamps else now


class PresenceContinuity:
    """One HA config-entry's persisted, conservative all-absent interval."""

    def __init__(self, hass: Any, entry_id: str, *, store: Any = None) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store = store
        self._signature: str | None = None
        self._since: float | None = None
        self._dirty = False

    def _snapshot(self) -> dict[str, Any]:
        return {
            "version": DATA_VERSION,
            "source_signature": self._signature,
            "verified_absence_since": self._since,
        }

    async def async_start(self) -> None:
        try:
            if self._store is None:
                from homeassistant.helpers.storage import Store
                self._store = Store(
                    self.hass, DATA_VERSION,
                    f"environment_manager.presence_absence_{self.entry_id}",
                )
            saved = await self._store.async_load()
            if not isinstance(saved, dict) or saved.get("version") != DATA_VERSION:
                return
            signature, since = saved.get("source_signature"), saved.get("verified_absence_since")
            now = datetime.now(timezone.utc).timestamp()
            try:
                stamp = float(since)
            except (TypeError, ValueError, OverflowError):
                return
            if (isinstance(signature, str) and len(signature) == 64
                    and math.isfinite(stamp) and
                    0 < now - stamp <= MAX_HISTORY_SECONDS):
                self._signature, self._since = signature, stamp
        except ImportError:
            _LOGGER.debug("Home Assistant Store unavailable in test runtime")
        except Exception:
            _LOGGER.exception("Persisted Away evidence unavailable; starting conservatively")

    def _changed(self) -> None:
        self._dirty = True
        if self._store is not None:
            try:
                self._store.async_delay_save(self._snapshot, 1)
            except Exception:
                _LOGGER.exception("Could not schedule Away-presence evidence save")

    def context(self, raw: Any) -> dict[str, Any]:
        """Return read-only, fresh-revalidated evidence for climate plans.

        A verified tracker/not-home numeric 0 can decide Away without the
        room-motion cooldown. When room-only signals determine home absence,
        restore their proven duration across reboot instead of using the new
        HA last_changed timestamps.
        """
        config = dict(raw) if isinstance(raw, dict) else {}
        # Internal keys are generated at runtime, never trusted from config.
        config.pop("_verified_absence_since", None)
        signature = source_signature(config)
        if self._signature != signature:
            self._signature, self._since = signature, None
            self._changed()

        current, _, sources = home_presence(
            self.hass, {**config, "away_cooldown_minutes": 0}
        )
        if current == "home":
            if self._since is not None:
                self._since = None
                self._changed()
        elif current == "away":
            if self._since is None:
                self._since = live_absence_since(self.hass, config, sources)
                self._changed()
            config["_verified_absence_since"] = self._since
        # Unknown, unavailable and not-yet-reported sources do NOT qualify as
        # Away, but also cannot prove somebody returned in our absence.
        return config

    async def async_stop(self) -> None:
        if self._store is not None and self._dirty:
            await self._store.async_save(self._snapshot())
            self._dirty = False

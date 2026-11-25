"""Bounded, per-controller presentation updates. Never delays hardware decisions."""
from __future__ import annotations
from collections import OrderedDict
from logging import getLogger
from time import monotonic

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import SIGNAL_UPDATED

_LOGGER = getLogger(__name__)
_WRITE_BUDGET_SECONDS = 0.008
_MAX_WRITES_PER_TURN = 24


class EquipmentStateWrites:
    """Share the event loop with HTTP and device callbacks during large refreshes."""

    def __init__(self, loop):
        self.loop = loop
        self.pending = OrderedDict()
        self.handle = None

    def request(self, entity):
        self.pending[id(entity)] = entity
        if self.handle is None:
            self.handle = self.loop.call_soon(self._flush)

    def discard(self, entity):
        self.pending.pop(id(entity), None)
        if not self.pending and self.handle is not None:
            self.handle.cancel()
            self.handle = None

    @callback
    def _flush(self):
        self.handle = None
        deadline = monotonic() + _WRITE_BUDGET_SECONDS
        for _ in range(min(_MAX_WRITES_PER_TURN, len(self.pending))):
            if not self.pending:
                break
            _, entity = self.pending.popitem(last=False)
            try:
                entity._equipment_write()
            except Exception:
                _LOGGER.exception("Error refreshing %s", entity.entity_id)
            if monotonic() >= deadline:
                break
        if self.pending and self.handle is None:
            self.handle = self.loop.call_soon(self._flush)


def controller_signal(entry_id: str, identifier: str) -> str:
    return f"{SIGNAL_UPDATED}_{entry_id}_equipment_{identifier}"


class EquipmentUpdates:
    """At most one pending callback; repeated changes keep only latest state."""
    def __init__(self, runtime):
        self.runtime = runtime
        self.pending: set[str] = set()
        self.handle = None

    @callback
    def request(self, identifier: str) -> None:
        if not self.runtime._active:
            return
        self.pending.add(identifier)
        if self.handle is None:
            self.handle = self.runtime.hass.loop.call_soon(self.flush)

    @callback
    def flush(self) -> None:
        self.handle = None
        changed, self.pending = self.pending, set()
        if not self.runtime._active:
            return
        for identifier in changed:
            async_dispatcher_send(self.runtime.hass, controller_signal(
                self.runtime.manager.entry.entry_id, identifier))

    @callback
    def close(self) -> None:
        if self.handle is not None:
            self.handle.cancel()
            self.handle = None
        self.pending.clear()

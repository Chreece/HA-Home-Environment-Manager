"""Bounded, per-controller presentation updates. Never delays hardware decisions."""
from __future__ import annotations
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import SIGNAL_UPDATED


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

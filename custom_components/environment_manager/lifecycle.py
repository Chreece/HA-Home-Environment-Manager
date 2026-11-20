"""Small lifecycle guards shared by HEM's controllers and optional work.

No Home Assistant imports are needed here. The real HA state is authoritative;
an absent state never grants permission to deliver optional external work.
"""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def state_name(hass: Any) -> str:
    state = getattr(hass, "state", None)
    value = getattr(state, "value", state)
    return value.lower() if isinstance(value, str) else ""


def is_stopping(hass: Any) -> bool:
    return state_name(hass) in {"stopping", "final_write", "stopped"}


def is_running(hass: Any) -> bool:
    return state_name(hass) == "running"


def create_background_task(
    hass: Any, entry: Any, coroutine: Coroutine[Any, Any, Any], name: str,
) -> asyncio.Task[Any]:
    """Create optional work without adding it to HA's startup barrier.

The caller must keep and cancel the returned task as part of its own teardown.
The config-entry API additionally owns cancellation on unload and HA shutdown.
"""
    register = getattr(entry, "async_create_background_task", None)
    if callable(register):
        return register(hass, coroutine, name)
    register = getattr(hass, "async_create_background_task", None)
    if callable(register):
        return register(coroutine, name)
    return asyncio.create_task(coroutine, name=name)

"""Lifecycle and response deadlines for optional announcement transports.

Only notification services use this helper. Physical actuator commands keep
their own acknowledgement, ownership and persistence rules.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .lifecycle import is_running, is_stopping

DIRECT_RESPONSE_TIMEOUT = 10


class NotificationDeliveryUnavailable(RuntimeError):
    """Home Assistant is not accepting optional notification work."""


def delivery_allowed(hass: Any) -> bool:
    """Do not send or clear optional notices during startup or shutdown."""
    return is_running(hass) and not is_stopping(hass)


async def async_call_notification(
    hass: Any, domain: str, service: str, data: dict[str, Any], *,
    target: dict[str, Any] | None = None, return_response: bool = False,
    timeout: float | None = None,
) -> Any:
    """Await a bounded notification response and preserve cancellation.

    Check immediately before dispatch, including each later destination or
    fallback in a multi-channel announcement. An acknowledged response remains
    authoritative if shutdown begins while the transport is completing.
    """
    if not delivery_allowed(hass):
        raise NotificationDeliveryUnavailable("Home Assistant is not running")
    kwargs: dict[str, Any] = {"blocking": True}
    if target is not None:
        kwargs["target"] = target
    if return_response:
        kwargs["return_response"] = True
    async with asyncio.timeout(DIRECT_RESPONSE_TIMEOUT if timeout is None else timeout):
        return await hass.services.async_call(domain, service, data, **kwargs)

"""Bounded, source-bound PID restart checkpoint for managed physical devices.

The checkpoint is advisory mathematical state ONLY. It never authorizes a
native ON/OFF command, bypasses physical minimum dwell, or represents a
physical actuator acknowledgement. A stale/invalid/foreign checkpoint is
discarded; current measured feedback always determines the resumed demand.
"""
from __future__ import annotations

import math
from typing import Any

MAX_ANCHOR_AGE = 30 * 86400


def _number(value: Any, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return n if math.isfinite(n) and minimum <= n <= maximum else None


def checkpoint(
    signature: tuple, memory: Any, anchor: float, sources: tuple[str, ...],
    source_device_id: str | None, sample: float, now: float,
) -> dict | None:
    if not isinstance(signature, tuple) or len(signature) != 12:
        return None
    valid = (
        _number(memory.integral, -100, 100),
        _number(memory.measured, -1e6, 1e6),
        _number(memory.stamp, 0, now),
        _number(memory.derivative, -1e6, 1e6),
        _number(memory.demand, 0, 100),
        _number(anchor, 0, now),
        _number(sample, 120, 3600),
    )
    if any(x is None for x in valid):
        return None
    if now - valid[5] > MAX_ANCHOR_AGE:
        return None
    if not all(isinstance(e, str) and e for e in sources):
        return None
    return {
        "version": 1, "signature": list(signature),
        "sources": list(sources), "source_device_id": source_device_id,
        "sample_seconds": valid[6],
        "integral": valid[0], "measured": valid[1], "stamp": valid[2],
        "derivative": valid[3], "demand": valid[4],
        "anchor": valid[5], "saved_at": now,
    }


def restore(
    raw: Any, *, sources: tuple[str, ...], source_device_id: str | None,
    now: float, sample: float, measured: float, goal: float,
    increasing: bool, kp: float,
) -> tuple[tuple, dict, float] | None:
    if not isinstance(raw, dict) or raw.get("version") != 1:
        return None
    if (raw.get("sources") != list(sources)
            or raw.get("source_device_id") != source_device_id):
        return None
    if _number(raw.get("sample_seconds"), sample, sample) is None:
        return None
    signature = raw.get("signature")
    if (not isinstance(signature, list) or len(signature) != 12
            or not all(isinstance(signature[k], str)
                       for k in (0, 3, 4, 5))
            or type(signature[2]) is not bool
            or any(_number(signature[k], -1e6, 1e6) is None
                   for k in (1, 6, 7, 8, 9, 10, 11))):
        return None
    saved_stamp = _number(raw.get("stamp"), 0, now)
    anchor = _number(raw.get("anchor"), 0, now)
    integral = _number(raw.get("integral"), -100, 100)
    saved = _number(raw.get("saved_at"), 0, now)
    if any(v is None for v in (saved_stamp, anchor, integral, saved)):
        return None
    if (now - saved_stamp > max(3 * sample, 1800)
            or now - anchor > MAX_ANCHOR_AGE
            or now < saved_stamp or now < saved):
        return None
    if (any(_number(x, -1e6, 1e6) is None for x in (measured, goal))
            or _number(kp, 0, 1e5) is None
            or type(increasing) is not bool):
        return None
    # The physical device was not continuously observed during HA downtime.
    # Preserve only the previously bounded I term and logical PWM phase;
    # reseed measurement and derivative from fresh evidence. Never integrate
    # the disconnected interval or replay a previously requested output.
    error = (goal - measured) if increasing else (measured - goal)
    demand = max(0.0, min(100.0, kp * error + integral))
    memory = {
        "integral": integral, "measured": measured,
        "stamp": now, "derivative": 0.0, "demand": demand,
    }
    return tuple(signature), memory, anchor

"""Pure, native-capability-gated automatic HVAC direction selection.

Shared heat/cool appliances retain verified temperature priority. Explicit
drying role and real RH demand can select native DRY; no service is sent here.
"""
from __future__ import annotations

import math
from typing import Any


def number(value: Any, low: float, high: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return result if math.isfinite(result) and low <= result <= high else None


def automatic_mode(cap: Any, state: Any, measured: dict, targets: dict,
                   *, dedicated_dry: bool = False, pid: bool = False) -> str | None:
    modes = set(cap.modes)
    if cap.domain == "humidifier":
        return "auto" if cap.humidifying else "dry"
    if cap.domain == "fan" or modes == {"off", "fan_only"}:
        return "fan_only"
    if cap.domain != "climate":
        return None

    native = str(getattr(state, "state", "") or "")
    has_dry = "dry" in modes
    thermal = bool(modes.intersection({"heat", "cool", "heat_cool", "auto"}))
    # A dedicated drying controller can expose native temperature attributes,
    # but those attributes do NOT turn it into a heating/cooling controller.
    if has_dry and (dedicated_dry or not thermal):
        return "dry"

    temperature = number(measured.get("temperature"), -60, 85)
    humidity = number(measured.get("humidity"), 0, 100)
    heat = number(targets.get("heat"), -60, 85)
    cool = number(targets.get("cool"), -60, 85)
    goal = number(targets.get("humidity"), 0, 100)

    # Thermal demand on a shared compressor must take priority.
    if temperature is not None:
        if heat is not None and temperature < heat - .3 and "heat" in modes:
            return "heat"
        if cool is not None and temperature > cool + .3 and "cool" in modes:
            return "cool"
    if has_dry and humidity is not None and goal is not None and (
            humidity > goal + 2 or native == "dry" and humidity >= goal - 2):
        return "dry"

    if temperature is not None:
        if "auto" in modes and not modes.intersection({"heat", "cool", "heat_cool"}):
            return "auto"
        if "heat_cool" in modes and not pid:
            return "heat_cool"
        if native in {"heat", "cool"} and native in modes:
            return native
        if "heat" in modes:
            return "heat"
        if "cool" in modes:
            return "cool"
    return native if native in modes and native != "off" else None

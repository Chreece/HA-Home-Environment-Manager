"""Pure PID cycle rebase logic for a real change of room control intent.

Profile changes and material setpoint changes start a new *logical* PWM phase.
This never resets observed physical OFF/ON dwell, native command ownership or
pending acknowledgements. Minor auto-comfort target noise must not repeatedly
restart the PWM phase (which could starve an actuator indefinitely).
"""
from __future__ import annotations

import math
from typing import Any

TARGET_CHANGE_C = 0.25
COMFORT_ERROR_C = 0.5


def phase_decision(
    previous: tuple | None,
    *, metric: str, target: float, increasing: bool, profile: str,
    mode: str, preset: str, kp: float, ki: float, kd: float,
    cycle_s: float, min_on_s: float, min_off_s: float,
    measured: float,
) -> tuple[tuple, bool, bool]:
    """Return stable signature, reset flag, and one-shot comfort wake request.

    A wake request means only that a supervised, hardware-safe minimum pulse
    should be *considered*. It does not actuate, grant permission, bypass a
    dwell, or infer missing measurement evidence.
    """
    signature = (
        metric, float(target), bool(increasing), profile, mode, preset,
        float(kp), float(ki), float(kd), float(cycle_s),
        float(min_on_s), float(min_off_s),
    )
    prior_ok = (
        isinstance(previous, tuple) and len(previous) == len(signature)
        and isinstance(previous[1], (int, float))
        and math.isfinite(previous[1])
    )
    if prior_ok:
        metadata_changed = any(
            previous[index] != signature[index]
            for index in range(len(signature)) if index != 1
        )
        target_changed = abs(signature[1] - previous[1]) >= TARGET_CHANGE_C
        reset = metadata_changed or target_changed
    else:
        reset = True
    if not reset:
        return previous, False, False
    # On an explicitly more demanding heat/cool profile or first startup,
    # consider one complete minimum-ON heating/cooling pulse, even where the
    # ordinary short PWM duty would be under the device minimum ON duration.
    # It still must pass *all* native authority and physical dwell gates.
    error = (target - measured) if increasing else (measured - target)
    qualifies = (metric == "temperature" and mode in ("heat", "cool")
                 and math.isfinite(error) and error >= COMFORT_ERROR_C)
    if not qualifies:
        return signature, True, False
    if not prior_ok:
        return signature, True, True
    old_target = previous[1]
    increased_need = (target - old_target >= TARGET_CHANGE_C
                      if increasing else old_target - target >= TARGET_CHANGE_C)
    changed_direction = previous[4] != mode
    # Merely changing the profile label without a warmer/cooler target must
    # not produce a surprise pulse. Raising comfort requirements should.
    return signature, True, bool(increased_need or changed_direction)

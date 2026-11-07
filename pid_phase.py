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



def safe_binary_pwm_cycle(
    demand: float, cycle_s: float, min_on_s: float, min_off_s: float,
    *, maximum_s: float = 86400.,
) -> float | None:
    """Fit both operating holds into a bounded whole-number PWM period.

    Preserve requested duty when its ON pulse and OFF rest can both fit. For
    example, 75% duty on a 600s period with a 300s minimum OFF needs a 1200s
    period: 900s ON and 300s OFF. Clipping the short period to its OFF minimum
    would deliver only 50%, despite the larger feasible period.

    Extremely small demand that cannot fit one minimum-ON pulse within the
    horizon remains idle. If a high demand needs an OFF rest beyond that
    horizon, use the largest complete period and let the duty limiter retain
    the full minimum OFF. A continuous 100% request has no scheduled OFF;
    actual target, maximum-runtime and transition gates still apply.
    This calculation never changes physical history or grants actuation.
    """
    from math import ceil, floor, isfinite
    args = (demand, cycle_s, min_on_s, min_off_s, maximum_s)
    if (any(isinstance(v, bool) or not isinstance(v, (int, float))
            or not isfinite(v) for v in args)
            or not 0 <= demand <= 100
            or cycle_s <= 0 or min_on_s < 0 or min_off_s < 0
            or cycle_s < min_on_s + min_off_s
            or maximum_s < cycle_s):
        return None
    if demand == 0:
        return None
    if demand == 100:
        return cycle_s
    available_periods = maximum_s / cycle_s
    if not isfinite(available_periods):
        return None
    largest_multiplier = floor(available_periods)
    bounded = cycle_s * largest_multiplier
    on_fraction, off_fraction = demand / 100., (100. - demand) / 100.
    nominal_on, nominal_off = cycle_s * on_fraction, cycle_s * off_fraction
    if nominal_on <= 0 or min_on_s > bounded * on_fraction:
        return None
    on_multiplier = max(1, ceil(min_on_s / nominal_on - 1e-9))
    if nominal_off <= 0 or min_off_s > bounded * off_fraction:
        # There is no exact duty within the bounded horizon. Keep useful
        # output while the shared duty limiter preserves the whole OFF rest.
        multiplier = largest_multiplier
    else:
        off_multiplier = max(1, ceil(min_off_s / nominal_off - 1e-9))
        multiplier = max(on_multiplier, off_multiplier)
    extended = cycle_s * multiplier
    duration = min(extended * on_fraction, extended - min_off_s)
    if (extended > maximum_s or duration <= 0
            or duration < min_on_s and not math.isclose(
                duration, min_on_s, rel_tol=1e-12, abs_tol=1e-9)):
        return None
    return extended


def binary_pwm_off_phase(
    demand: float, elapsed: float, cycle: float,
    min_on: float, min_off: float, *, starting: bool,
) -> dict:
    """Expose informational PWM state, never authorize a physical command."""
    effective = safe_binary_pwm_cycle(demand, cycle, min_on, min_off)
    if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed) or elapsed < 0):
        effective = None
    if effective is None:
        return {
            "state": "demand_below_minimum_safe_pulse" if demand > 0
                     else "zero_demand",
            "effective_cycle_seconds": None,
            "next_window_seconds": None,
        }
    if demand == 100:
        # Match duty_on's continuous demand. Minimum OFF applies only after
        # a real OFF transition, never as an invented end-of-period gap.
        return {"state": "on_window", "effective_cycle_seconds": effective,
                "next_window_seconds": 0.}
    phase = elapsed % effective
    duration = max(min_on, min(effective * demand / 100., effective - min_off))
    if phase < duration and (not starting or duration-phase >= min_on):
        return {"state": "on_window", "effective_cycle_seconds": effective,
                "next_window_seconds": 0.}
    return {"state": "off_window", "effective_cycle_seconds": effective,
            "next_window_seconds": max(0., effective - phase)}


def sampled_binary_pwm_plan(
    demand: float, elapsed: float, cycle: float, min_on: float, min_off: float,
    *, starting: bool, served_elapsed: float | None, stopped_elapsed: float | None = None,
) -> dict:
    """Plan at most one due pulse from confirmed output, not polling phase.

    A sampled controller can miss the entire nominal ON window or the small
    part in which a full minimum-ON pulse still fits. An unserved due cycle
    therefore retains ONE request. Physical dispatch/ACK owns its eventual
    start; the runtime aligns the next period only to that confirmed start.
    Missed periods never accumulate and a delivered cycle cannot be replayed.

    ``served_elapsed`` is the latest confirmed pulse's logical start relative
    to the same anchor, or conservative observed-OFF evidence in that cycle.
    ``stopped_elapsed`` additionally preserves one complete nominal OFF rest
    from the confirmed stop. Delayed feedback never becomes energy debt.
    This helper never changes device ownership, an ON/OFF hold or PID gains.
    """
    info = binary_pwm_off_phase(demand, elapsed, cycle, min_on, min_off, starting=starting)
    effective = info["effective_cycle_seconds"]
    if effective is None:
        return {**info, "wanted": False, "next_evaluation_seconds": None}
    if demand == 100:
        return {**info, "wanted": True, "next_evaluation_seconds": None}
    phase = elapsed % effective
    cycle_start = elapsed - phase
    duration = max(min_on, min(effective * demand / 100., effective - min_off))
    served = (not isinstance(served_elapsed, bool)
              and isinstance(served_elapsed, (int, float))
              and math.isfinite(served_elapsed) and 0 <= served_elapsed <= elapsed)
    if starting:
        next_start = cycle_start + effective if served and served_elapsed >= cycle_start else elapsed
        stopped = (served and not isinstance(stopped_elapsed, bool)
                   and isinstance(stopped_elapsed, (int, float))
                   and math.isfinite(stopped_elapsed) and 0 <= stopped_elapsed <= elapsed)
        if stopped:
            next_start = max(next_start, stopped_elapsed + effective - duration)
        # Sensor subtraction can put an exact boundary a fraction of a
        # nanosecond ahead (e.g. 4.9% after 21-20.6). Absolute timers round
        # that to now; do not discard an otherwise due mathematical pulse.
        # The actuator still checks real minimum ON/OFF with no tolerance.
        wanted = next_start <= elapsed or math.isclose(
            next_start, elapsed, rel_tol=0., abs_tol=1e-9,
        )
        remaining = None if wanted else next_start - elapsed
    else:
        # An already-running pulse cannot wrap through a missed OFF boundary
        # into another ON window. Its original minimum/maximum physical run
        # remains enforced by the actuator independently.
        on_elapsed = elapsed - served_elapsed if served else elapsed
        wanted = on_elapsed < duration and not math.isclose(
            on_elapsed, duration, rel_tol=0., abs_tol=1e-9,
        )
        remaining = max(0., duration - on_elapsed) if wanted else None
    return {
        **info, "state": "on_window" if wanted else "off_window",
        "next_window_seconds": 0. if wanted else remaining if starting else None,
        "wanted": wanted, "next_evaluation_seconds": remaining,
    }

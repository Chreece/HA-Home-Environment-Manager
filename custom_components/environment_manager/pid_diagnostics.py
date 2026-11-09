"""Read-only, session-bounded PID/Automatic performance observations.

This module is deliberately excluded from all actuator, PID gain and tuning
paths. Estimates only from qualified, fresh controller observations; it never
fills missing intervals, assumes actuator power, or guesses energy use.
No HA imports, timers, storage writes, recorder queries or device commands.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Any

WINDOW_SECONDS = 24 * 3600
MAX_SAMPLES = 800
MIN_EVIDENCE_SECONDS = 30 * 60
BANDS = {"temperature": 0.3, "humidity": 2.0}


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def observed_output(domain: str, state: Any, mode: str) -> str | None:
    """Physical output evidence, never the requested thermostat HVAC mode.

    Climate "heat"/"dry" is a mode, not proof a compressor is operating.
    Unknown hvac_action produces unknown output rather than a false ON.
    """
    status = getattr(state, "state", None)
    if domain == "climate":
        action = (getattr(state, "attributes", None) or {}).get("hvac_action")
        expected = {"heat": "heating", "cool": "cooling", "dry": "drying"}.get(mode)
        if status == "off" or action in ("off", "idle"):
            return "off"
        if expected is not None and action == expected:
            return "on"
        return None
    if domain in ("switch", "input_boolean", "humidifier"):
        return status if status in ("on", "off") else None
    # PWM percentage/valve and fan speed do not indicate a binary physical ON.
    return None


@dataclass(frozen=True, slots=True)
class Observation:
    at: float
    error: float
    output: str | None


class PerformanceWindow:
    """One room/source/mode/profile/target/control-method context at a time.

    No comparison across targets or modes is valid, so a context change
    reinitializes only this mathematical observer (not the hardware controller).
    A stale timestamp or gap never credits unobserved physical runtime.
    """

    def __init__(self) -> None:
        self.context: tuple[Any, ...] | None = None
        self.metric: str | None = None
        self.method: str | None = None
        self.mode: str | None = None
        self.target: float | None = None
        self.samples: deque[Observation] = deque(maxlen=MAX_SAMPLES)
        self.max_gap_seconds = 1800

    def observe(
        self, *, context: tuple[Any, ...], metric: str, method: str,
        mode: str, target: float, measured: float, increasing: bool,
        at: float, sample_seconds: float, output: str | None,
    ) -> bool:
        if (metric not in BANDS or method not in ("pid", "automatic")
                or mode not in ("heat", "cool", "dry")
                or not all(_number(x) for x in (at, target, measured, sample_seconds))
                or not (120 <= sample_seconds <= 3600)
                or at < 0 or output not in (None, "on", "off")):
            return False
        if self.context != context:
            self.context = context
            self.metric, self.method, self.mode, self.target = (
                metric, method, mode, float(target)
            )
            self.samples.clear()
        self.max_gap_seconds = max(3 * sample_seconds, 1800)
        last = self.samples[-1] if self.samples else None
        if last is not None:
            elapsed = at - last.at
            if elapsed <= 0:
                return False
            if elapsed < 0.7 * sample_seconds:
                return False
            # A long gap remains visible between two samples but receives
            # no integration credit. Never infer runtime while HA was asleep.
        direction = 1 if increasing else -1
        self.samples.append(Observation(
            float(at), direction * (target - measured), output
        ))
        while self.samples and at - self.samples[0].at > WINDOW_SECONDS:
            self.samples.popleft()
        return True

    def snapshot(self) -> dict[str, Any]:
        if not self.samples:
            return {"status": "collecting", "sample_count": 0}
        band = BANDS[self.metric]
        samples = list(self.samples)
        covered = integrated = signed = run_floor = off_floor = 0.0
        starts = 0
        gaps = 0
        qualified_pairs = 0
        sample_inside = sum(abs(row.error) <= band for row in samples)
        for previous, current in zip(samples, samples[1:]):
            dt = current.at - previous.at
            # Include only adjacent observations close enough to be credible.
            if dt <= 0 or dt > self.max_gap_seconds:
                gaps += 1
                continue
            qualified_pairs += 1
            covered += dt
            # Trapezoidal integration gives an observed tracking-error estimate.
            integrated += 0.5 * (abs(previous.error) + abs(current.error)) * dt / 3600
            signed += 0.5 * (previous.error + current.error) * dt / 3600
            if previous.output == current.output == "on":
                run_floor += dt
            if previous.output == current.output == "off":
                off_floor += dt
            if previous.output == "off" and current.output == "on":
                starts += 1
        overshoot = max(0.0, *(-s.error for s in samples))
        max_shortfall = max(0.0, *(s.error for s in samples))
        return {
            "status": "observed" if covered >= MIN_EVIDENCE_SECONDS
                else "insufficient_coverage",
            "metric": self.metric, "method": self.method, "mode": self.mode,
            "target": self.target,
            "unit": "°C" if self.metric == "temperature" else "RH points",
            "band": band,
            "sample_count": len(samples),
            "qualified_intervals": qualified_pairs,
            "coverage_hours": round(covered / 3600, 3),
            "first_sample_at": samples[0].at,
            "last_sample_at": samples[-1].at,
            "mae": round(integrated / (covered / 3600), 3) if covered else None,
            "mean_signed_error": round(signed / (covered / 3600), 3) if covered else None,
            "integrated_absolute_error_unit_hours": round(integrated, 3),
            "sampled_in_band_percent": round(
                100 * sample_inside / len(samples), 1
            ),
            "maximum_observed_overshoot": round(overshoot, 3),
            "maximum_observed_shortfall": round(max_shortfall, 3),
            "verified_off_to_on_transitions": starts,
            "observed_on_hours_lower_bound": round(run_floor / 3600, 3),
            "observed_off_hours_lower_bound": round(off_floor / 3600, 3),
            "unobserved_or_long_intervals": gaps,
            "energy_kwh": None,
            "energy_note": "No verified device energy meter; runtime is not energy.",
            "scope": "current context and running Home Assistant session only",
        }

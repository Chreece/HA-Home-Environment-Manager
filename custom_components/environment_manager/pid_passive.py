"""Passive, non-actuating response identification for HEM's existing PID.

This module never touches Home Assistant, its event loop or hardware. Only
complete normal ON/OFF cycles with verified measurement and a stable controller
identity may contribute a model. Partial cycles never survive restarts.
An explicit user choice is required before even *bounded* gain adaptation.
"""
from __future__ import annotations

import json
import math
from statistics import median
from typing import Any

from .pid_calibration import tune

MODES = ("disabled", "observe", "bounded")
METRICS = {
    # minimum measurable response, maximum credible full output response,
    # maximum stable-baseline drift, maximum one-sample jump.
    "temperature": (0.75, 15.0, 0.15, 0.8),
    "humidity": (4.0, 45.0, 0.8, 3.0),
}
MAX_CYCLES = 6
MAX_AGE_S = 21 * 86400
MAX_POINTS = 100
MIN_OFF_S = 15 * 60
MIN_ON_S = 75 * 60
AUTO_MIN_CYCLES = 5
AUTO_INTERVAL_S = 24 * 3600
AUTO_MAX_RELATIVE_CHANGE = 0.10


def identity(*values: Any) -> str:
    """Serialize exact sources, operating direction, metric, preset and target."""
    return json.dumps(values, separators=(",", ":"), ensure_ascii=False)


def _finite(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _fit_episode(
    on: list[tuple[float, float]], baseline: float, direction: int, metric: str
) -> dict[str, float] | None:
    """Fit a bounded first-order-plus-dead-time step to one natural ON run.

    Require an observable plateau. A short ramp cannot separate static gain
    from time constant, even if a numerical optimizer fits it perfectly.
    """
    if metric not in METRICS or len(on) < 10:
        return None
    threshold, maximum, _, max_jump = METRICS[metric]
    start = on[0][0]
    elapsed = [(at - start) / 60 for at, _ in on]
    if elapsed[-1] < MIN_ON_S / 60 or len(on) > MAX_POINTS:
        return None
    y = [direction * (val - baseline) for _, val in on]
    amp = median(y[-3:])
    if not threshold <= amp <= maximum:
        return None
    if max(y) > maximum * 1.25 or min(y) < -threshold * 0.45:
        return None
    # An actual plateau, not a drifting background response.
    # A linear drifting room can appear flat over only a few samples.
    # Require the final eight observations to be close to equilibrium.
    if max(y[-8:]) - min(y[-8:]) > 0.12 * amp:
        return None
    # Exclude obvious secondary sources/disturbances and lost samples.
    if any(abs(b - a) > max_jump for a, b in zip(y, y[1:])):
        return None
    if sum(b + max(0.08, threshold * 0.08) < a for a, b in zip(y, y[1:])) > len(y) // 5:
        return None

    total = sum((v - sum(y) / len(y)) ** 2 for v in y)
    if total <= 0:
        return None
    best = None
    dead_max = min(30, elapsed[-1] / 4)
    tau_max = min(240, elapsed[-1] / 1.7)
    # Coarse, deterministic grid; bounded work only at completion of an ON run.
    dead_candidates = (0.1, *(float(k) for k in range(2, int(dead_max) + 1, 2)))
    for dead in dead_candidates:
        for tau_i in range(8, int(tau_max) + 1, 4):
            tau = float(tau_i)
            shape = [1 - math.exp(-max(0.0, t - dead) / tau) for t in elapsed]
            energy = sum(v * v for v in shape)
            if energy <= 1e-9:
                continue
            gain = sum(a * b for a, b in zip(y, shape)) / energy
            if not threshold <= gain <= maximum:
                continue
            residual = sum((a - gain * b) ** 2 for a, b in zip(y, shape))
            if best is None or residual < best[0]:
                best = (residual, gain, tau, dead)
    if best is None:
        return None
    residual, gain, tau, dead = best
    r2 = 1 - residual / total
    rmse = math.sqrt(residual / len(y))
    if r2 < 0.965 or rmse > min(max_jump * 0.55, 0.13 * amp):
        return None
    return {
        "gain": round(gain, 4), "tau": round(tau, 2),
        "dead": round(dead, 2), "r2": round(r2, 4),
        "duration_minutes": round(elapsed[-1], 1),
    }


def _prediction_error(
    cycle: dict, gain: float, tau: float, dead: float
) -> float:
    """Holdout score from independently identified model parameters."""
    # Retained cycles contain model parameters, not raw waveform; compare the
    # held-out parameters in normalized process units as a conservative
    # prediction-stability gate, not a claim of external validation.
    return max(
        abs(cycle["gain"] - gain) / max(gain, 0.01),
        abs(cycle["tau"] - tau) / max(tau, 1),
        abs(cycle["dead"] - dead) / max(tau, 1),
    )


def _rejection_reason(
    on: list[tuple[float, float]], baseline: float, direction: int, metric: str
) -> str:
    """Diagnostic explanation ONLY; never changes a fit's acceptance."""
    if metric not in METRICS or len(on) < 10:
        return "insufficient_on_samples"
    if (on[-1][0] - on[0][0]) < MIN_ON_S:
        return "on_cycle_too_short"
    threshold, maximum, _, max_jump = METRICS[metric]
    response = [direction * (val - baseline) for _, val in on]
    amp = median(response[-3:])
    if amp < threshold:
        return "response_too_small"
    if amp > maximum:
        return "response_outside_physical_limits"
    if max(response[-8:]) - min(response[-8:]) > 0.12 * amp:
        return "no_stable_plateau"
    if any(abs(b - a) > max_jump for a, b in zip(response, response[1:])):
        return "sensor_jump"
    return "response_model_fit_rejected"


class PassiveObserver:
    """One in-memory sampler and a compact, restart-safe cycle ledger."""

    def __init__(self, saved: dict | None = None):
        self.context: str | None = None
        self.cycles: list[dict] = []
        self.off: list[tuple[float, float]] = []
        self.on: list[tuple[float, float]] = []
        self.baseline: float | None = None
        self.last_on: bool | None = None
        self.last_t: float | None = None
        self.proposal: dict | None = None
        self.status: str = "collecting"
        # Volatile operator diagnostics, never consulted by tuning or actuation.
        self.last_rejection_reason: str | None = None
        self.rejection_counts: dict[str, int] = {}
        if isinstance(saved, dict):
            ctx = saved.get("context")
            rows = saved.get("cycles")
            if isinstance(ctx, str) and isinstance(rows, list):
                self.context = ctx
                self.cycles = [
                    dict(row) for row in rows[-MAX_CYCLES:]
                    if isinstance(row, dict)
                    and all(_finite(row.get(k)) for k in
                            ("at", "gain", "tau", "dead", "r2"))
                ]
                # A persisted model is never sufficient to auto-act after
                # restart without new, live, complete OFF->ON->OFF evidence.
                self.status = "collecting"

    def _reject(self, reason: str) -> None:
        self.last_rejection_reason = reason
        self.rejection_counts[reason] = min(
            9999, self.rejection_counts.get(reason, 0) + 1
        )

    def progress(self) -> dict[str, Any]:
        """Bounded in-session learning progress, no raw waveform or actuation."""
        phase = (
            "observing_on_response" if self.on
            else "collecting_stable_off_baseline" if self.last_on is False
            else "awaiting_verified_off"
        )
        return {
            "phase": phase,
            "valid_cycles": len(self.cycles),
            "required_for_auto": AUTO_MIN_CYCLES,
            "off_samples": len(self.off),
            "on_samples": len(self.on),
            "on_observed_minutes": (
                round(max(0.0, self.on[-1][0] - self.on[0][0]) / 60, 1)
                if self.on else 0.0
            ),
            "last_rejection_reason": self.last_rejection_reason,
            "rejection_counts": dict(self.rejection_counts),
            "raw_history_saved": False,
        }

    def interrupt(self) -> None:
        self.off.clear()
        self.on.clear()
        self.baseline = None
        self.last_on = None
        self.last_t = None

    def observe(
        self, *, context: str, at: float, value: float | None,
        on: bool, owned: bool, metric: str, direction: int,
        sample_seconds: float, safe: bool,
    ) -> bool:
        """Return True ONLY for one newly accepted completed natural cycle."""
        if context != self.context:
            self.context = context
            self.last_rejection_reason = None
            self.rejection_counts.clear()
            self.cycles.clear()
            self.proposal = None
            self.status = "collecting"
            self.interrupt()
        if (not safe or direction not in (-1, 1)
                or metric not in METRICS or not _finite(at)
                or not _finite(value) or not _finite(sample_seconds)
                or sample_seconds < 120):
            if self.last_on is not None:
                self._reject("unsafe_or_invalid_observation")
            self.interrupt()
            return False
        assert value is not None
        if (self.last_t is not None and (
                at <= self.last_t or
                at - self.last_t > max(3 * sample_seconds, 1800))):
            if self.on or self.off:
                self._reject("observation_clock_or_gap")
            self.interrupt()
        if self.last_t is not None and at - self.last_t < sample_seconds * 0.7:
            return False
        before = self.last_on
        self.last_on, self.last_t = on, at
        if not on:
            completed = False
            if before is True and self.on and self.baseline is not None:
                episode = _fit_episode(self.on, self.baseline, direction, metric)
                if episode is None:
                    self._reject(_rejection_reason(
                        self.on, self.baseline, direction, metric
                    ))
                else:
                    episode["at"] = at
                    self.cycles = [
                        cycle for cycle in self.cycles
                        if at >= cycle["at"] and at - cycle["at"] <= MAX_AGE_S
                    ][-MAX_CYCLES + 1:] + [episode]
                    self.status = "model_updated"
                    completed = True
            self.on.clear()
            self.baseline = None
            self.off.append((at, float(value)))
            self.off = self.off[-8:]
            return completed
        if not owned:
            # Exclude manual starts and all unacknowledged/unowned power.
            if before is True or self.on:
                self._reject("unowned_native_output")
            self.interrupt()
            return False
        if before is False:
            bounds = METRICS[metric]
            if (len(self.off) >= 4 and
                    self.off[-1][0] - self.off[0][0] >= MIN_OFF_S and
                    max(v for _, v in self.off[-4:]) -
                    min(v for _, v in self.off[-4:]) <= bounds[2]):
                self.baseline = median(v for _, v in self.off[-4:])
                self.on = [(at, float(value))]
            else:
                self._reject("off_baseline_not_stable_or_too_short")
                self.on.clear()
                self.baseline = None
        elif before is True and self.on and len(self.on) < MAX_POINTS:
            self.on.append((at, float(value)))
        self.off.clear()
        return False

    def summary(self, *, metric: str, sample_seconds: float) -> dict:
        """Use independent natural cycles; never invent gains from short ramps."""
        recent = list(self.cycles)
        result: dict[str, Any] = {
            "status": self.status if recent else "collecting",
            "valid_cycles": len(recent),
            "required_for_auto": AUTO_MIN_CYCLES,
            "metric": metric,
            "confidence": "insufficient",
        }
        if not recent:
            return result
        gain, tau, dead = (median(row[k] for row in recent)
                           for k in ("gain", "tau", "dead"))
        result["identified_model"] = {
            "process_gain": round(gain, 3),
            "time_constant_minutes": round(tau, 2),
            "dead_time_minutes": round(dead, 2),
            "median_r2": round(median(row["r2"] for row in recent), 3),
        }
        if len(recent) < 3:
            return result
        train = recent[:-1]
        stable = (
            all(_prediction_error(c, gain, tau, dead) <= 0.22 for c in recent)
            and min(c["r2"] for c in recent) >= 0.965
        )
        if not stable:
            result["status"] = "inconsistent_plant_response"
            return result
        high = (
            len(recent) >= AUTO_MIN_CYCLES
            and all(c["r2"] >= 0.975 for c in recent[-AUTO_MIN_CYCLES:])
            and _prediction_error(
                recent[-1],
                median(c["gain"] for c in train),
                median(c["tau"] for c in train),
                median(c["dead"] for c in train),
            ) <= 0.14
            and all(_prediction_error(c, gain, tau, dead) <= 0.14
                    for c in recent[-AUTO_MIN_CYCLES:])
        )
        result["confidence"] = "high" if high else "medium"
        lam = min(1440.0, max(10.0, 2.0 * dead, 0.75 * tau, sample_seconds / 60))
        try:
            calc = tune(
                "imc_lambda",
                {"pid_process_gain": gain, "pid_time_constant_minutes": tau,
                 "pid_dead_time_minutes": max(0.1, dead),
                 "pid_lambda_minutes": lam},
                sample_seconds=sample_seconds,
                constraints={
                    "kp": (0.001, 100.0),
                    "ki": (0.0, 10.0),
                    "kd": (0.0, 50.0),
                },
            )
        except ValueError:
            result["status"] = "identified_gains_outside_safe_bounds"
            return result
        result["suggested_gains"] = {
            "kp": round(calc.kp, 4),
            "ki": round(calc.ki, 5),
            "kd": round(calc.kd, 4),
        }
        result["status"] = "validated" if high else "suggestion_only"
        result["last_cycle_at"] = recent[-1]["at"]
        return result

    def ledger(self) -> dict:
        """Compact persisted proof only; never raw waveform or per-tick writes."""
        return {"context": self.context, "cycles": self.cycles[-MAX_CYCLES:]}


def bounded_gains(current: dict, proposed: dict) -> dict[str, float] | None:
    """At most 10% movement per update; no automatic PI->PID derivative."""
    result = {}
    for key, lower, upper in (("kp", 0.001, 100.0),
                              ("ki", 0.0, 10.0)):
        old, wanted = current.get(key), proposed.get(key)
        if not _finite(old) or not _finite(wanted):
            return None
        old, wanted = float(old), float(wanted)
        if not lower <= old <= upper or not lower <= wanted <= upper:
            return None
        limit = max(0.001 if key == "ki" else 0.01,
                    AUTO_MAX_RELATIVE_CHANGE * max(old, lower))
        next_value = max(old - limit, min(old + limit, wanted))
        result[key] = round(max(lower, min(upper, next_value)), 5)
    # SIMC intentionally recommends PI. Keep existing Kd until the operator
    # explicitly changes derivative policy rather than silently zeroing it.
    result["kd"] = current.get("kd")
    return result if any(abs(result[k] - current[k]) > 1e-6 for k in ("kp", "ki")) else None

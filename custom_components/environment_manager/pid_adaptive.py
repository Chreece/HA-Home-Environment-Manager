"""Passive performance assessment and evidence-gated adaptive PID tuning.

No Home Assistant dependency, hardware calls, probing, or assumed feedback
entity. The runtime supplies the exact process value and actual actuator reports
used by its controller. Normal windows of any cycle duration can contribute.
A performance problem alone never authorizes a gain direction: local models
must survive chronological prediction checks and counterfactual replay using
the production PID, output allocator, dwell limits and bumpless transfer.

This is local empirical validation, not a universal stability certificate.
Raw measurements stay bounded in memory. Only completed assessments and trial
receipts survive restart; an outage is never bridged by inferred samples.
"""
from __future__ import annotations

from collections import deque
from bisect import bisect_right
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
from statistics import median
from typing import Any, Callable

from .pid_phase import sampled_binary_pwm_plan

ALGORITHM = "performance_v1"
VERSION = 1
MAX_SAMPLES = 192
MAX_EVENTS = 768
MAX_WINDOWS = 6
MIN_FIT_SAMPLES = 32
ASSESS_EVERY = 8
MAX_VERIFICATION_WINDOWS = 3
MAX_AGE_SECONDS = 7 * 86400
BANDS = {"temperature": .3, "humidity": 2., "co2": 50., "pm25": 2.}
GAIN_BOUNDS = {"kp": (.001, 100.), "ki": (0., 10.), "kd": (0., 50.)}


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _number(value: Any, default=None):
    return float(value) if _finite(value) else default


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _gains(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    result = {}
    for key, (low, high) in GAIN_BOUNDS.items():
        if not _finite(value.get(key)) or not low <= value[key] <= high:
            return None
        result[key] = float(value[key])
    return result


def _valid_model(value: Any) -> bool:
    return (isinstance(value, dict)
            and all(_finite(value.get(k)) for k in
                    ("gain", "offset", "origin", "band", "direction", "tau_seconds", "delay_seconds"))
            and value["gain"] > 0 and value["band"] > 0
            and value["direction"] in (-1, 1)
            and 0 < value["tau_seconds"] <= 86400
            and 0 <= value["delay_seconds"] <= 86400)


def _variance(values: list[float]) -> float:
    if not values:
        return 0.
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _covariance(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.
    lm, rm = sum(left) / len(left), sum(right) / len(right)
    return sum((a - lm) * (b - rm) for a, b in zip(left, right)) / len(left)


def _correlation(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(_variance(left) * _variance(right))
    return _covariance(left, right) / denominator if denominator > 1e-12 else 0.


def _event_value(events: list, at: float) -> float | None:
    value = None
    for stamp, output in events:
        if stamp > at:
            break
        value = output
    return value


class _InputTrace:
    """Exact weighted input integrals without rescanning every actuator edge."""

    def __init__(self, records):
        self.records = list(records)
        self.times = [row[0] for row in self.records]
        self.unknown = [0.]
        for left, right in zip(self.records, self.records[1:]):
            self.unknown.append(self.unknown[-1] + (right[0] - left[0]) * (left[1] is None))
        self.responses = {}

    def __bool__(self):
        return bool(self.records)

    def __getitem__(self, index):
        return self.records[index]

    def append(self, row):
        if self.records:
            old = self.records[-1]
            elapsed = row[0] - old[0]
            if elapsed < 0:
                raise ValueError("nonmonotonic_actuator_history")
            self.unknown.append(self.unknown[-1] + elapsed * (old[1] is None))
            for tau, values in self.responses.items():
                decay = math.exp(-elapsed / tau)
                values.append(decay * values[-1] + (1 - decay) * (old[1] or 0.))
        self.records.append(row)
        self.times.append(row[0])

    def _at(self, at, tau):
        index = bisect_right(self.times, at) - 1
        if index < 0:
            return None
        if tau not in self.responses:
            values = [0.]
            for left, right in zip(self.records, self.records[1:]):
                decay = math.exp(-(right[0] - left[0]) / tau)
                values.append(decay * values[-1] + (1 - decay) * (left[1] or 0.))
            self.responses[tau] = values
        stamp, output = self.records[index]
        elapsed = at - stamp
        decay = math.exp(-elapsed / tau)
        return (decay * self.responses[tau][index] + (1 - decay) * (output or 0.),
                self.unknown[index] + elapsed * (output is None))

    def forcing(self, start, end, tau, delay):
        left, right = self._at(start - delay, tau), self._at(end - delay, tau)
        if left is None or right is None or right[1] - left[1] > 1e-7:
            return None
        decay = math.exp(-(end - start) / tau)
        return (right[0] - decay * left[0]) / max(1e-12, 1 - decay)


def _forcing(events: list, start: float, end: float, tau: float,
             delay: float = 0.) -> float | None:
    """Exact exponential weighting of observed piecewise-constant input."""
    if end <= start or tau <= 0:
        return None
    if isinstance(events, _InputTrace):
        return events.forcing(start, end, tau, delay)
    start -= delay
    end -= delay
    current = _event_value(events, start)
    if current is None:
        return None
    cursor, integral = start, 0.
    for stamp, output in events:
        if stamp <= start:
            continue
        if stamp >= end:
            break
        if current is None:
            return None
        integral += current * (math.exp(-(end - stamp) / tau)
                               - math.exp(-(end - cursor) / tau))
        cursor, current = stamp, output
    if current is None:
        return None
    integral += current * (1. - math.exp(-(end - cursor) / tau))
    return integral / max(1e-12, 1. - math.exp(-(end - start) / tau))


def _advance(model: dict, value: float, start: float, end: float,
             events: list) -> float | None:
    forcing = _forcing(events, start, end, model["tau_seconds"], model["delay_seconds"])
    if forcing is None:
        return None
    decay = math.exp(-(end - start) / model["tau_seconds"])
    return (decay * value + (1. - decay)
            * (model["offset"] + model["gain"] * forcing))


def _performance(points: list[dict], band: float, increasing: bool,
                 semantics: str) -> dict:
    """Elapsed-time scores over observed intervals; no fabricated missing data."""
    if len(points) < 2 or band <= 0:
        return {"observed_seconds": 0., "within_band_fraction": None,
                "mean_absolute_error": None, "normalized_error": None,
                "overshoot": 0., "offset": None, "cycles": 0,
                "output_changes": 0, "limited_fraction": 0.,
                "saturated_fraction": 0., "target_reached": False,
                "time_to_band_seconds": None, "within_band_seconds": 0.}
    direction = 1 if increasing else -1
    total = inside = error_integral = signed_integral = limited = saturated = 0.
    overshoot = 0.
    switches = cycles = 0
    crossed = False
    reach_time = None
    start = points[0]["at"]
    for before, point in zip(points, points[1:]):
        dt = point["at"] - before["at"]
        if dt <= 0 or dt > point.get("max_gap", 1800):
            continue
        error = direction * (point["target"] - point["value"])
        absolute = abs(error) if semantics == "band" else max(0., error)
        is_inside = absolute <= band
        total += dt
        inside += dt * is_inside
        error_integral += dt * absolute
        signed_integral += dt * error
        limited += dt * bool(point.get("limited"))
        actual = point.get("output")
        demand = point.get("demand")
        saturated += dt * (actual is not None and demand is not None
                           and actual >= .98 and demand >= 98 and error > band)
        if semantics == "band":
            overshoot = max(overshoot, max(0., -error - band))
        if is_inside and reach_time is None:
            reach_time = max(0., point["at"] - start)
        previous_output = before.get("output")
        if actual is not None and previous_output is not None:
            switches += abs(actual - previous_output) > .02
            if actual <= .01 < previous_output:
                cycles += 1
        prior_error = direction * (before["target"] - before["value"])
        crossed = crossed or (prior_error > band and error < -band
                              or prior_error < -band and error > band)
    if total <= 0:
        return _performance([], band, increasing, semantics)
    return {
        "observed_seconds": round(total, 3),
        "within_band_seconds": round(inside, 3),
        "within_band_fraction": inside / total,
        "mean_absolute_error": error_integral / total,
        "normalized_error": error_integral / total / band,
        "overshoot": overshoot,
        "offset": signed_integral / total,
        "cycles": cycles, "output_changes": switches,
        "limited_fraction": limited / total,
        "saturated_fraction": saturated / total,
        "target_reached": reach_time is not None,
        "time_to_band_seconds": reach_time,
        "crossed_target_band": crossed,
    }


def _score(performance: dict, band: float) -> float:
    return (float(performance.get("normalized_error") or 0.)
            + .35 * float(performance.get("overshoot") or 0.) / band
            + .01 * float(performance.get("output_changes") or 0.))


def _config(sample: dict) -> dict:
    stages = sample.get("output_stages") or sample.get("stages") or []
    stages = sorted(set(float(v) for v in stages if _finite(v) and 0 < v <= 100))
    return {
        "kind": sample.get("actuator_kind", "unknown"),
        "sample_seconds": _number(sample.get("sample_seconds"), 300.),
        "cycle_seconds": _number(sample.get("cycle_seconds"), 3600.),
        "min_on_seconds": _number(sample.get("min_on_seconds"), 0.),
        "min_off_seconds": _number(sample.get("min_off_seconds"), 0.),
        "max_on_seconds": _number(sample.get("max_on_seconds"), 7200.),
        "min_percentage": _number(sample.get("min_percentage"), 1.),
        "max_percentage": _number(sample.get("max_percentage"), 100.),
        "percentage_step": _number(sample.get("percentage_step"), 1.),
        "max_output_change": _number(sample.get("max_output_change"), 100.),
        "output_step_origin": _number(sample.get("output_step_origin"), 0.),
        "quantization": sample.get("output_quantization", "nearest"),
        "stages": stages,
    }


def _allocate_output(demand: float, output: float, cfg: dict) -> float | None:
    """Reproduce supported native command allocation on its actual 0–100 scale.

    This is command position, never an assertion of equal watts per stage or
    of an inner thermostat's heat output. Timing and power dwell are separate.
    """
    kind, minimum, maximum = cfg["kind"], cfg["min_percentage"], cfg["max_percentage"]
    stages = cfg["stages"]
    if kind == "ordered_stage":
        if not stages:
            return None
        if demand <= 0:
            return 0.
        chosen = stages[min(len(stages) - 1, max(0, math.ceil(demand * len(stages) / 100) - 1))]
        available = [v for v in stages if v <= maximum]
        return min(chosen, max(available)) / 100 if available else None
    if kind not in ("percentage", "setpoint_trim"):
        return None
    if kind != "setpoint_trim" and (demand <= 0 or demand < minimum):
        return 0.
    percent = min(maximum, max(minimum, demand))
    change, step = cfg["max_output_change"], cfg["percentage_step"]
    if not 0 < change <= 100 or step <= 0 or maximum < minimum:
        return None
    percent = max(output * 100 - change, min(output * 100 + change, percent))
    if stages and kind == "percentage":
        available = [v for v in stages if minimum <= v <= maximum]
        if not available:
            return None
        if cfg["quantization"] == "floor":
            percent = max((v for v in available if v <= percent), default=min(available))
        else:
            percent = min(available, key=lambda v: abs(v - percent))
    else:
        origin = cfg["output_step_origin"]
        position = (percent - origin) / step
        if cfg["quantization"] == "native_half_up":
            percent = origin + math.floor(round(position, 10) + .5) * step
        elif cfg["quantization"] == "native_half_down":
            percent = origin + math.ceil(round(position, 10) - .5) * step
        else:
            # Numeric percentage adapters first round to a tenth and then
            # to their advertised native step, using Python's tie rule.
            percent = origin + round((round(percent, 1) - origin) / step) * step
        percent = min(maximum, max(minimum, percent))
    if kind == "setpoint_trim" and abs(percent - output * 100) > change + 1e-5:
        percent = output * 100
    return 0. if abs(percent) < 1e-8 else percent / 100.


class AdaptiveObserver:
    """One bounded observation stream, completed evidence and reversible trial."""

    def __init__(self, saved: dict | None = None, *, now: float | None = None,
                 stepper: Callable | None = None, transfer: Callable | None = None):
        self.context: str | None = None
        self.points: deque = deque(maxlen=MAX_SAMPLES)
        self.events: deque = deque(maxlen=MAX_EVENTS)
        self.windows: list[dict] = []
        self.trial: dict | None = None
        self.last_application: dict | None = None
        self.last_result: dict | None = None
        self._stepper = stepper
        self._transfer = transfer
        self._assessment: dict = {}
        self._sample: dict = {}
        self._count = 0
        self._assessed_at_count = 0
        self._last_report: float | None = None
        self._last_observed: float | None = None
        self._restored = False
        self._causal_hold = False
        try:
            # Store files are input, not trusted live Python objects. Keep
            # corrupt/non-finite/oversized evidence out of the evaluator.
            encoded = json.dumps(saved, allow_nan=False)
            saved = json.loads(encoded) if len(encoded) <= 65536 else None
        except (ValueError, TypeError, OverflowError, RecursionError):
            saved = None
        if isinstance(saved, dict) and saved.get("version") == VERSION and saved.get("algorithm") == ALGORITHM:
            self.context = saved.get("context") if isinstance(saved.get("context"), str) else None
            windows = saved.get("windows")
            if isinstance(windows, list):
                self.windows = [deepcopy(w) for w in windows[-MAX_WINDOWS:]
                                if isinstance(w, dict) and _finite(w.get("at"))
                                and (now is None or 0 <= now - w["at"] <= MAX_AGE_SECONDS)]
            for key in ("trial", "last_application", "last_result"):
                value = saved.get(key)
                if isinstance(value, dict):
                    setattr(self, key, deepcopy(value))
            self._restored = True
            self._assessment = {"status": "waiting", "reason": "restart_verification_required"}
        else:
            self._assessment = {"status": "collecting", "reason": "insufficient_evidence"}
        if self.trial and (
                self.trial.get("state") not in ("evaluating", "retained", "rollback_recommended", "reverted", "cancelled", "inconclusive")
                or not isinstance(self.trial.get("baseline"), dict)
                or not _finite(self.trial["baseline"].get("observed_seconds"))
                or _gains(self.trial.get("applied_gains")) is None
                or not isinstance(self.trial.get("application"), dict)
                or _gains(self.trial["application"].get("previous_gains")) is None):
            self.trial = None
        if self.trial:
            count = self.trial.get("verification_windows", 0)
            self.trial["verification_windows"] = (int(count) if _finite(count)
                                                   and 0 <= count <= MAX_VERIFICATION_WINDOWS else 0)

    def interrupt(self, reason: str = "observation_interrupted") -> None:
        """An outage/hold ends continuity, but never fabricates rollback/applied history."""
        self.points.clear()
        self.events.clear()
        self._last_report = self._last_observed = None
        self._count = self._assessed_at_count = 0
        self._assessment = {"status": "waiting", "reason": reason}
        if self.trial and self.trial.get("state") == "evaluating":
            self.trial["fresh_verification_required"] = True

    def _remember_window(self, result: dict) -> None:
        if not self.points:
            return
        evidence_id = result.get("evidence_id") or _hash([
            self.context, self.points[-1]["at"], result.get("performance"), result.get("reason")])
        window = {
            "evidence_id": evidence_id, "at": self.points[-1]["at"],
            "samples": len(self.points),
            "observed_seconds": result.get("performance", {}).get("observed_seconds", 0.),
            "performance": deepcopy(result.get("performance", {})),
            "model": deepcopy(result.get("model")),
            "candidate": deepcopy(result.get("candidate")),
            "status": result.get("status"), "reason": result.get("reason"),
        }
        if self.windows and self.windows[-1]["evidence_id"] == evidence_id:
            return
        self.windows = (self.windows + [window])[-MAX_WINDOWS:]

    def observe_output(self, at: float, output_percent: float | None) -> bool:
        """Record a real ACK edge without inventing a process-value report.

        The runtime calls this only for the current observer/context after it
        has verified its own command acknowledgement. Unknown output ends
        attribution; a delayed old edge cannot rewrite qualified history.
        """
        if (not self.context or not _finite(at) or at < 0
                or self._last_observed is not None and at < self._last_observed
                or self.events and at < self.events[-1][0]):
            return False
        if not _finite(output_percent) or not 0 <= output_percent <= 100:
            self.interrupt("output_unverified")
            self._causal_hold = True
            return False
        output = output_percent / 100.
        changed = not self.events or self.events[-1][1] != output
        if changed:
            self.events.append((float(at), output))
        self._last_observed = float(at)
        return changed

    def observe(self, sample: dict) -> bool:
        """Consume exact reported input and actual output; repeated reports are not evidence."""
        if not isinstance(sample, dict):
            self.interrupt("invalid_observation")
            return False
        at = _number(sample.get("observed_at"))
        reported = _number(sample.get("reported_at"))
        value = _number(sample.get("measured"))
        target = _number(sample.get("target"))
        band = _number(sample.get("band", sample.get("tolerance")),
                       BANDS.get(sample.get("metric"), 1.))
        context = sample.get("context")
        if (not isinstance(context, str) or not context or at is None or at < 0
                or reported is None or not 0 <= reported <= at or value is None
                or target is None or band is None or band <= 0
                or not isinstance(sample.get("increasing"), bool)
                or _gains(sample.get("gains")) is None):
            self.interrupt("invalid_observation")
            return False
        if self.context != context:
            if self.trial and self.trial.get("state") in ("evaluating", "rollback_recommended"):
                self.trial.update(state="cancelled", reason="verification_context_changed")
                self.last_result = deepcopy(self.trial)
            self.interrupt("context_changed")
            self.context = context
            self.windows = []
        self._sample = deepcopy(sample)
        self._sample["band"] = band
        if sample.get("safe") is not True:
            constraints = sample.get("constraints")
            self.interrupt(str(constraints[0]) if isinstance(constraints, (list, tuple)) and constraints
                           else "controller_paused")
            return False
        if self._last_observed is not None and at < self._last_observed:
            self.interrupt("observation_clock_or_gap")
            return False
        cfg = _config(sample)
        max_gap = max(3 * cfg["sample_seconds"], 1800.)
        if self._last_observed is not None and at - self._last_observed > max_gap:
            self.interrupt("observation_clock_or_gap")
        output = _number(sample.get("observed_output"))
        output = output / 100 if output is not None and 0 <= output <= 100 and sample.get("output_verified") is True else None
        # A second active controller or unknown applied output destroys the
        # attribution needed for identification. This is not an ordinary
        # percentage-of-time limit: no contaminated interval may later become
        # tuning evidence when the peer stops or output feedback returns.
        ambiguous = output is None or "other_controller_active" in (sample.get("constraints") or ())
        if ambiguous != self._causal_hold:
            self.interrupt("other_controller_active" if output is not None and ambiguous
                           else "output_unverified" if ambiguous else "insufficient_evidence")
            self._causal_hold = ambiguous
        if ambiguous:
            return False
        event_at = _number(sample.get("output_at"), at)
        event_at = min(at, max(self._last_observed if self._last_observed is not None else at, event_at))
        if not self.events or self.events[-1][1] != output:
            self.events.append((event_at, output))
        self._last_observed = at
        if at - reported > max_gap:
            self.interrupt("measurement_outdated")
            return False
        if self._last_report is not None and reported <= self._last_report:
            # Output edges still belong to the history, but an old temperature
            # value is not a new independent sample or progress toward tuning.
            return False
        if self._last_report is not None and reported - self._last_report > max_gap:
            self.interrupt("measurement_gap")
            self.events.append((at, output))
            self._last_observed = at
        self._last_report = reported
        point = {
            "at": reported, "observed_at": at, "value": value, "target": target,
            "output": output, "demand": _number(sample.get("requested_output")),
            "limited": bool(sample.get("limited") or sample.get("constraints")),
            "causal_ambiguity": ambiguous,
            "max_gap": max_gap, "gains": _gains(sample["gains"]),
            "pid_memory": deepcopy(sample.get("pid_memory")),
            "pwm_state": deepcopy(sample.get("pwm_state")),
            "output_changed_at": _number(sample.get("output_changed_at")),
        }
        self.points.append(point)
        self._count += 1
        self._restored = False
        while self.events and len(self.events) > 2 and self.events[1][0] < self.points[0]["at"] - max_gap:
            self.events.popleft()
        if self.trial and self.trial.get("state") in ("evaluating", "rollback_recommended"):
            if _gains(self.trial.get("applied_gains")) != point["gains"]:
                self.trial.update(state="cancelled", reason="verification_settings_changed")
                self.last_result = deepcopy(self.trial)
        if self._count - self._assessed_at_count >= ASSESS_EVERY:
            self._assessed_at_count = self._count
            self._assess()
            self._remember_window(self._assessment)
            return True
        # Cheap performance accounting follows every real report. Only
        # identification/counterfactual work is batched; the displayed elapsed
        # observation and target error must not wait for a model-fit interval.
        current = list(self.points)
        semantics = sample.get("target_semantics", "band")
        self._assessment["performance"] = _performance(current, band, sample["increasing"], semantics)
        if len(current) < ASSESS_EVERY and not self.trial and not ambiguous:
            self._assessment.update(status="collecting", reason="insufficient_evidence")
        if len(current) >= ASSESS_EVERY and not (
                self.trial and self.trial.get("state") in ("evaluating", "rollback_recommended")):
            recent = current[-max(ASSESS_EVERY, min(16, len(current) // 3)):]
            perf = _performance(recent, band, sample["increasing"], semantics)
            self._assessment["recent_performance"] = perf
            if (perf["within_band_fraction"] is not None and perf["within_band_fraction"] >= .90
                    and perf["normalized_error"] <= .8 and perf["overshoot"] <= band):
                self._assessment.update(status="retained", reason="tracking_well",
                                        candidate=None, performance=perf)
        return False

    def _base(self) -> dict:
        sample = self._sample
        return {
            "schema_version": VERSION, "algorithm": ALGORITHM,
            "context": self.context, "metric": sample.get("metric"),
            "increasing": sample.get("increasing"),
            "direction": 1 if sample.get("increasing") else -1,
            "target": sample.get("target"), "band": sample.get("band"),
            "tolerance": sample.get("band"),
            "target_semantics": sample.get("target_semantics", "band"),
            "samples": len(self.points),
            "evidence_at": self.points[-1]["at"] if self.points else None,
            "fresh_evidence": len(self.points) >= ASSESS_EVERY and not self._restored,
            "raw_history_saved": False, "candidate": None,
            "last_application": deepcopy(self.last_application),
        }

    def snapshot(self) -> dict:
        result = {**self._base(), **deepcopy(self._assessment)}
        # Current freshness/counts must outrank a cached completed assessment.
        result.update(samples=len(self.points), fresh_evidence=self._base()["fresh_evidence"])
        result["observed_seconds"] = result.get("performance", {}).get("observed_seconds", 0.)
        if self.trial:
            result["verification"] = deepcopy(self.trial)
            result["last_application"] = deepcopy(self.last_application)
        return result

    def progress(self) -> dict:
        return self.snapshot()

    def ledger(self) -> dict:
        return {
            "version": VERSION, "algorithm": ALGORITHM, "context": self.context,
            "assessment": self.snapshot(), "windows": deepcopy(self.windows[-MAX_WINDOWS:]),
            "trial": deepcopy(self.trial), "last_application": deepcopy(self.last_application),
            "last_result": deepcopy(self.last_result), "raw_history_saved": False,
        }

    def mark_applied(self, receipt: dict) -> None:
        if (not isinstance(receipt, dict) or receipt.get("context") != self.context
                or not _finite(receipt.get("at"))
                or _gains(receipt.get("previous_gains")) is None
                or _gains(receipt.get("applied_gains")) is None):
            return
        application = deepcopy(receipt)
        baseline = receipt.get("baseline") or self._assessment.get("performance") or {}
        if not isinstance(baseline, dict) or not _finite(baseline.get("observed_seconds")):
            baseline = {"observed_seconds": 0.}
        model = receipt.get("model") or self._assessment.get("model")
        self.last_application = application
        self.trial = {
            "state": "evaluating", "reason": "evaluating_adjustment",
            "at": receipt["at"], "context": self.context,
            "previous_gains": deepcopy(receipt["previous_gains"]),
            "applied_gains": deepcopy(receipt["applied_gains"]),
            "baseline": deepcopy(baseline), "model": deepcopy(model),
            "application": application, "fresh_verification_required": True,
        }
        self.interrupt("evaluating_adjustment")
        self._assessment = {"status": "verifying", "reason": "evaluating_adjustment",
                            "performance": deepcopy(baseline)}

    def mark_reverted(self, receipt: dict) -> None:
        if not isinstance(receipt, dict):
            return
        self.last_application = deepcopy(receipt)
        if self.trial:
            self.trial.update(state="reverted", reason="previous_gains_restored",
                              rollback_application=deepcopy(receipt))
            self.last_result = deepcopy(self.trial)
        self.interrupt("previous_gains_restored")
        self._assessment = {"status": "reverted", "reason": "previous_gains_restored"}

    def _assess(self) -> None:
        points = list(self.points)
        sample = self._sample
        band = sample["band"]
        semantics = sample.get("target_semantics", "band")
        perf = _performance(points, band, sample["increasing"], semantics)
        base = {**self._base(), "performance": perf, "model": None,
                "status": "collecting", "reason": "insufficient_evidence"}
        self._assessment = base
        if self.trial and self.trial.get("state") in ("evaluating", "rollback_recommended"):
            self._verify(points, base)
            return
        if len(points) < ASSESS_EVERY:
            return
        recent = points[-max(ASSESS_EVERY, min(16, len(points) // 3)):]
        recent_performance = _performance(recent, band, sample["increasing"], semantics)
        base["recent_performance"] = recent_performance
        if (recent_performance["within_band_fraction"] is not None
                and recent_performance["within_band_fraction"] >= .90
                and recent_performance["normalized_error"] <= .8
                and recent_performance["overshoot"] <= band):
            base.update(status="retained", reason="tracking_well", performance=recent_performance)
            return
        previous_decision_at = (self.last_result or {}).get("evidence_at")
        if (_finite(previous_decision_at) and
                sum(p["at"] > previous_decision_at for p in points) < MIN_FIT_SAMPLES):
            base.update(reason="new_evidence_required")
            return
        if perf["saturated_fraction"] >= .6:
            base.update(status="limited", reason="capacity_limited")
            return
        if any(p.get("causal_ambiguity") for p in points):
            base.update(status="waiting", reason="output_unverified" if any(p["output"] is None for p in points)
                        else "other_controller_active")
            return
        if perf["limited_fraction"] >= .25:
            base.update(status="limited", reason="operating_limits")
            return
        if sum(p["output"] is not None for p in points) < len(points) * .95:
            base.update(status="waiting", reason="output_unverified")
            return
        cfg = _config(sample)
        if cfg["kind"] not in ("binary", "percentage", "ordered_stage", "setpoint_trim"):
            base.update(status="waiting", reason="actuator_model_unverified")
            return
        if cfg["kind"] == "ordered_stage" and not cfg["stages"]:
            base.update(status="waiting", reason="actuator_model_unverified")
            return
        if len(points) < MIN_FIT_SAMPLES:
            return
        if max(p["value"] for p in points) - min(p["value"] for p in points) < band * .5:
            base.update(reason="insufficient_response_variation")
            return
        models = self._fit(points)
        if not models:
            base.update(reason="model_not_validated")
            return
        base["model"] = deepcopy(models[0])
        if models[0]["prediction_rmse"] > band * .35:
            base.update(status="waiting", reason="measurement_noise")
            return
        candidate = self._candidate(points, models, cfg)
        if candidate is None:
            base.update(status="retained", reason="no_supported_improvement")
            return
        evidence = [self.context, sample["gains"], cfg,
                    [(p["at"], p["value"], p["target"], p["output"]) for p in points],
                    {k: candidate[k] for k in ("kp", "ki", "kd")}]
        token = _hash(evidence)
        candidate.update(
            evidence_id=token, evidence_at=points[-1]["at"], context=self.context,
            previous_gains=deepcopy(sample["gains"]), validated=True,
            baseline=deepcopy(candidate.get("baseline", perf)), model=deepcopy(models[0]),
        )
        base.update(status="candidate", reason="validated_improvement",
                    candidate=candidate, evidence_id=token)

    def _fit(self, points: list[dict]) -> list[dict]:
        """IV-assisted local fits, then independent chronological rollout checks.

        Lagged actuator instruments mitigate direct feedback/noise correlation.
        They are not assumed valid simply because a fit exists: input strength,
        IV/OLS agreement, residual correlation and held-out simulation all gate
        every model. Unknown disturbances can still defeat local identification,
        in which case no controller update is generated.
        """
        events = _InputTrace(self.events)
        intervals = [b["at"] - a["at"] for a, b in zip(points, points[1:])]
        cadence = median(intervals)
        if cadence <= 0:
            return []
        band = self._sample["band"]
        direction = 1 if self._sample["increasing"] else -1
        origin = median(p["value"] for p in points)
        transformed = [direction * (p["value"] - origin) / band for p in points]
        split = max(20, int(len(points) * .65))
        candidates = []
        for delay_n in (0., 1., 2., 4.):
            delay = cadence * delay_n
            for factor in (.5, 1., 2., 4., 8., 16., 32., 64.):
                tau = cadence * factor
                if not 30 <= tau <= 86400:
                    continue
                rows = []
                for i in range(4, len(points)):
                    a, b = points[i - 1], points[i]
                    dt = b["at"] - a["at"]
                    if dt <= 0 or dt > b["max_gap"]:
                        continue
                    u = _forcing(events, a["at"], b["at"], tau, delay)
                    lag1 = _forcing(events, a["at"] - cadence * 2,
                                    b["at"] - cadence * 2, tau, delay)
                    lag2 = _forcing(events, a["at"] - cadence * 3,
                                    b["at"] - cadence * 3, tau, delay)
                    if None in (u, lag1, lag2):
                        continue
                    decay = math.exp(-dt / tau)
                    response = (transformed[i] - decay * transformed[i - 1]) / (1 - decay)
                    rows.append((i, u, response, lag1, lag2))
                train = [row for row in rows if row[0] < split]
                valid = [row for row in rows if row[0] >= split]
                if len(train) < 14 or len(valid) < 8:
                    continue
                us, qs = [r[1] for r in train], [r[2] for r in train]
                # Small normal output movements can be informative for a
                # sensitive plant. Judge them against observed noise below,
                # rather than demanding an arbitrary large actuator step.
                if _variance(us) < 1e-7 or max(us) - min(us) < .005:
                    continue
                instruments = [[r[k] for r in train] for k in (3, 4)]
                instrument = max(instruments, key=lambda z: abs(_correlation(z, us)))
                strength = abs(_correlation(instrument, us))
                denominator = _covariance(instrument, us)
                if strength < .20 or abs(denominator) < 1e-8:
                    continue
                gain = _covariance(instrument, qs) / denominator
                ordinary = _covariance(us, qs) / _variance(us)
                if not .05 <= gain <= 500 or not .05 <= ordinary <= 500:
                    continue
                disagreement = abs(gain - ordinary) / max(gain, ordinary)
                if disagreement > .35:
                    continue
                offset = sum(qs) / len(qs) - gain * sum(us) / len(us)
                unexplained = math.sqrt(sum((q - offset - gain * u) ** 2
                                            for q, u in zip(qs, us)) / len(us))
                relative_uncertainty = (3 * unexplained / max(1e-12,
                    math.sqrt(len(us) * _variance(us)) * strength * gain))
                if relative_uncertainty > .5:
                    continue
                model = {"tau_seconds": tau, "delay_seconds": delay,
                         "gain": gain, "offset": offset, "origin": origin,
                         "band": band, "direction": direction}
                residuals = []
                prediction = transformed[split - 1]
                rollout = []
                for i in range(split, len(points)):
                    previous, current = points[i - 1], points[i]
                    step = _advance(model, transformed[i - 1], previous["at"], current["at"], events)
                    prediction = _advance(model, prediction, previous["at"], current["at"], events)
                    if step is None or prediction is None:
                        residuals = []
                        break
                    residuals.append(transformed[i] - step)
                    rollout.append(transformed[i] - prediction)
                if len(residuals) < 8:
                    continue
                rmse = math.sqrt(sum(v * v for v in residuals) / len(residuals))
                rollout_rmse = math.sqrt(sum(v * v for v in rollout) / len(rollout))
                autocorr = abs(_correlation(residuals[:-1], residuals[1:]))
                observed_variance = _variance(transformed[split:])
                if (rmse > .35 or rollout_rmse > .65
                        or rollout_rmse > max(.15, math.sqrt(observed_variance) * .65)
                        or autocorr > .80):
                    continue
                model.update(
                    prediction_rmse=rmse * band, rollout_rmse=rollout_rmse * band,
                    instrument_strength=strength, iv_ols_difference=disagreement,
                    relative_gain_uncertainty=relative_uncertainty,
                    residual_lag_correlation=autocorr,
                    training_samples=len(train), validation_samples=len(residuals),
                    validation_start_index=split - 1,
                    validation_kind="chronological_iv_assisted_prediction",
                    uncertainty="local_model_only",
                )
                candidates.append(model)
        candidates.sort(key=lambda m: m["rollout_rmse"] + m["prediction_rmse"])
        if not candidates:
            return []
        best = candidates[0]
        # Retain several plausible delay/time-constant fits; candidate benefit
        # must survive every retained model, not just the best fitted curve.
        threshold = max(best["rollout_rmse"] * 1.5, band * .15)
        accepted = [m for m in candidates if m["rollout_rmse"] <= threshold]
        return accepted[:3]

    def _functions(self):
        if self._stepper is None or self._transfer is None:
            from .equipment_model import pid_step, pid_bumpless
            self._stepper = self._stepper or pid_step
            self._transfer = self._transfer or pid_bumpless
        return self._stepper, self._transfer

    def _candidate(self, points: list[dict], models: list[dict], cfg: dict) -> dict | None:
        gains = _gains(self._sample.get("gains"))
        if gains is None:
            return None
        alternatives = []
        for p, i in ((1.05, 1.), (.95, 1.), (1., 1.05), (1., .95),
                     (1.05, 1.05), (.95, .95), (1.10, 1.), (.90, 1.),
                     (1., 1.10), (1., .90)):
            candidate = {"kp": gains["kp"] * p, "ki": gains["ki"] * i, "kd": gains["kd"]}
            if _gains(candidate) is not None and candidate != gains:
                alternatives.append(candidate)
        band = self._sample["band"]
        semantics = self._sample.get("target_semantics", "band")
        windows = []
        split = models[0]["validation_start_index"]
        # Whole held-out window and its independently initialized latter half.
        windows.append(points[split:])
        if len(points) - split >= 16:
            windows.append(points[split + (len(points) - split) // 2:])
        baseline = []
        for model in models:
            for window in windows:
                result = self._simulate(model, window, cfg, gains, gains)
                if result is None:
                    return None
                observed = _performance(window, band, self._sample["increasing"], semantics)
                # A model that cannot reproduce the current closed loop is
                # not trusted to predict a different controller.
                if (result["response_rmse"] > max(band * .65, model["rollout_rmse"] * 2)
                        or abs(result["performance"]["normalized_error"] - observed["normalized_error"])
                        > max(.35, .35 * observed["normalized_error"])):
                    return None
                baseline.append(result)
        best = None
        for proposed in alternatives:
            improvements = []
            eligible = True
            index = 0
            for model in models:
                for window in windows:
                    simulated = self._simulate(model, window, cfg, proposed, gains)
                    original = baseline[index]
                    index += 1
                    if simulated is None:
                        eligible = False
                        break
                    old, new = original["performance"], simulated["performance"]
                    old_score, new_score = _score(old, band), _score(new, band)
                    improvement = (old_score - new_score) / max(.1, old_score)
                    if (improvement < .01 or old_score - new_score < .005
                            or new["overshoot"] > old["overshoot"] + .1 * band
                            or new["within_band_fraction"] + .03 < old["within_band_fraction"]
                            or new["output_changes"] > old["output_changes"] + 2):
                        eligible = False
                        break
                    improvements.append(improvement)
                if not eligible:
                    break
            if eligible and improvements and (best is None or min(improvements) > best["predicted_improvement"]):
                best = {**proposed, "predicted_improvement": min(improvements),
                        "validated_windows": len(windows),
                        "validated_models": len(models),
                        "baseline": _performance(windows[0], band, self._sample["increasing"], semantics),
                        "validation": "production_pid_constrained_closed_loop",
                        "reason": "consistent_modelled_improvement"}
        return best

    def _simulate(self, model: dict, window: list[dict], cfg: dict,
                  gains: dict, original_gains: dict) -> dict | None:
        """Replay the actual PID and actuator limits on a held-out local model."""
        if len(window) < 4:
            return None
        stepper, transfer = self._functions()
        first = window[0]
        increasing = self._sample["increasing"]
        direction = 1 if increasing else -1
        band = self._sample["band"]
        if cfg["sample_seconds"] < 120 or cfg["max_on_seconds"] <= cfg["min_on_seconds"]:
            return None
        now = first["at"]
        model_value = direction * (first["value"] - model["origin"]) / band
        measured = first["value"]
        target = first["target"]
        memory = stepper(measured, target, now, increasing=increasing,
                         sample=cfg["sample_seconds"], **original_gains)
        saved_memory = first.get("pid_memory")
        if isinstance(saved_memory, dict):
            fields = ("integral", "measured", "stamp", "derivative", "demand")
            if all(saved_memory.get(k) is None or _finite(saved_memory[k]) for k in fields):
                try:
                    memory = replace(memory, **{k: saved_memory[k] for k in fields if k in saved_memory})
                except (TypeError, ValueError):
                    return None
        elif first.get("demand") is not None:
            # Initial integral is observable from the controller's own demand;
            # the subsequent current-controller replay independently checks it.
            error = direction * (target - measured)
            integral = first["demand"] - original_gains["kp"] * error
            if not -100 <= integral <= 100:
                return None
            memory = replace(memory, integral=integral, demand=first["demand"])
        if gains != original_gains:
            memory = transfer(memory, target, increasing=increasing, **gains)
            if memory is None:
                return None
        output = first.get("output")
        if output is None:
            return None
        output_events = _InputTrace(e for e in self.events if e[0] <= now)
        if not output_events:
            return None
        if output_events[-1][0] < now:
            output_events.append((now, output))
        pwm = first.get("pwm_state") or {}
        anchor = _number(pwm.get("anchor"), now)
        served = _number(pwm.get("served_at"), now if output > 0 else None)
        stopped = _number(pwm.get("stopped_at"), now if output == 0 else None)
        on_since = _number(pwm.get("on_since"), now if output > 0 else None)
        off_since = _number(pwm.get("off_since"), now if output == 0 else None)
        command_at = _number(first.get("output_changed_at"), now - cfg["sample_seconds"])
        predicted = [dict(first)]
        squared_error = []
        loops = 0
        for next_point in window[1:]:
            boundary = next_point["at"]
            while now < boundary - 1e-7:
                loops += 1
                if loops > 4096:
                    return None
                memory = stepper(measured, target, now, increasing=increasing,
                                 sample=cfg["sample_seconds"], memory=memory, **gains)
                demand = memory.demand
                delay = None
                if cfg["kind"] == "binary":
                    plan = sampled_binary_pwm_plan(
                        demand, max(0., now - anchor), cfg["cycle_seconds"],
                        cfg["min_on_seconds"], cfg["min_off_seconds"],
                        starting=output <= 0,
                        served_elapsed=served - anchor if served is not None else None,
                        stopped_elapsed=stopped - anchor if stopped is not None else None,
                    )
                    wanted = bool(plan["wanted"])
                    delay = plan.get("next_evaluation_seconds")
                    new_output = 1. if wanted else 0.
                else:
                    new_output = _allocate_output(demand, output, cfg)
                    if new_output is None:
                        return None
                    # Number and native-target writes have a separate
                    # command cadence; extra sensor reports cannot multiply
                    # their permitted per-sample slew.
                    if (cfg["max_output_change"] < 100 and now - command_at < cfg["sample_seconds"]
                            and (new_output > 0 or cfg["kind"] == "setpoint_trim")):
                        new_output = output
                # Runtime target cutoff overrides stored effort, while actual
                # minimum ON can postpone the physical stop.
                if direction * (target - measured) <= 0 and cfg["kind"] != "setpoint_trim":
                    new_output = 0.
                if cfg["kind"] != "setpoint_trim" and output > 0 and on_since is not None:
                    age = now - on_since
                    if age >= cfg["max_on_seconds"]:
                        new_output = 0.
                    elif new_output == 0 and age < cfg["min_on_seconds"]:
                        new_output = output
                        delay = min(delay, cfg["min_on_seconds"] - age) if delay is not None and delay > 0 else cfg["min_on_seconds"] - age
                if cfg["kind"] != "setpoint_trim" and output <= 0 and new_output > 0 and off_since is not None:
                    age = now - off_since
                    if age < cfg["min_off_seconds"]:
                        new_output = 0.
                        delay = min(delay, cfg["min_off_seconds"] - age) if delay is not None and delay > 0 else cfg["min_off_seconds"] - age
                if new_output != output:
                    command_at = now
                    if output <= 0 < new_output:
                        on_since, off_since, served = now, None, now
                        anchor = max(anchor, now)
                    elif new_output <= 0 < output:
                        off_since, on_since, stopped = now, None, now
                    output = new_output
                    output_events.append((now, output))
                end = boundary
                if delay is not None and delay > 1e-6:
                    end = min(end, now + delay)
                if cfg["kind"] != "setpoint_trim" and output > 0 and on_since is not None:
                    end = min(end, on_since + cfg["max_on_seconds"])
                if end <= now + 1e-7:
                    return None
                model_value = _advance(model, model_value, now, end, output_events)
                if model_value is None or not math.isfinite(model_value) or abs(model_value) > 2000:
                    return None
                now = end
            measured = model["origin"] + direction * band * model_value
            target = next_point["target"]
            squared_error.append((measured - next_point["value"]) ** 2)
            predicted.append({**next_point, "value": measured, "target": target,
                              "output": output, "demand": memory.demand, "limited": False})
        performance = _performance(predicted, band, increasing,
                                   self._sample.get("target_semantics", "band"))
        return {"performance": performance,
                "response_rmse": math.sqrt(sum(squared_error) / len(squared_error))}

    def _verify(self, points: list[dict], base: dict) -> None:
        trial = self.trial
        assert trial is not None
        # Pending rollback must be supported again by fresh, comparable data;
        # replaying an expired decision after restart is not new evidence.
        if trial.get("state") == "rollback_recommended":
            trial.update(state="evaluating", reason="evaluating_adjustment")
            trial["previous_gains"] = deepcopy((trial.get("application") or {}).get("previous_gains"))
            for key in ("evidence_id", "evidence_at", "revert_gains"):
                trial.pop(key, None)
        base.update(status="verifying", reason="evaluating_adjustment")
        baseline = trial.get("baseline") or {}
        previous_window = trial.get("last_verification_at")
        if _finite(previous_window):
            points = [p for p in points if p["at"] > previous_window]
        performance = _performance(points, self._sample["band"], self._sample["increasing"],
                                   self._sample.get("target_semantics", "band"))
        if len(points) < MIN_FIT_SAMPLES or performance["observed_seconds"] < baseline.get("observed_seconds", 0.) * .5:
            return
        if any(p.get("causal_ambiguity") for p in points):
            trial["reason"] = "verification_conditions_changed"
            return
        # Inconclusive comparisons cannot lock adaptation forever. Count
        # complete, nonoverlapping observed windows, not time across outages.
        trial["last_verification_at"] = points[-1]["at"]
        trial["verification_windows"] = int(trial.get("verification_windows", 0)) + 1
        base["performance"] = performance
        recent = _performance(points[-16:], self._sample["band"], self._sample["increasing"],
                              self._sample.get("target_semantics", "band"))
        if (recent["within_band_fraction"] is not None and recent["within_band_fraction"] >= .90
                and recent["normalized_error"] <= .8 and recent["overshoot"] <= self._sample["band"]):
            trial.update(state="retained", reason="stable_after_adjustment", evidence_at=points[-1]["at"],
                         result=deepcopy(performance), fresh_verification_required=False)
            self.last_result = deepcopy(trial)
            base.update(status="retained", reason="stable_after_adjustment")
            return

        def unresolved(reason):
            trial["reason"] = reason
            if trial["verification_windows"] >= MAX_VERIFICATION_WINDOWS:
                trial.update(state="inconclusive", reason="verification_inconclusive",
                             comparison_reason=reason, evidence_at=points[-1]["at"],
                             result=deepcopy(performance), fresh_verification_required=False)
                self.last_result = deepcopy(trial)
                base.update(status="retained", reason="verification_inconclusive")

        if performance["limited_fraction"] > .15 or performance["saturated_fraction"] > .3:
            unresolved("verification_conditions_changed")
            return
        model = trial.get("model")
        if not _valid_model(model):
            unresolved("verification_model_unavailable")
            return
        # Recheck the environment against actual post-change input. A worse
        # cold/weather/open-door episode is not proof the new gains are worse.
        events = _InputTrace(self.events)
        predicted = model["direction"] * (points[0]["value"] - model["origin"]) / model["band"]
        errors = []
        for left, right in zip(points, points[1:]):
            predicted = _advance(model, predicted, left["at"], right["at"], events)
            if predicted is None:
                unresolved("verification_conditions_changed")
                return
            observed = model["direction"] * (right["value"] - model["origin"]) / model["band"]
            errors.append((predicted - observed) ** 2)
        if math.sqrt(sum(errors) / max(1, len(errors))) > .75:
            unresolved("verification_conditions_changed")
            return
        cfg = _config(self._sample)
        application = trial.get("application") or {}
        applied = _gains(application.get("applied_gains", trial.get("applied_gains")))
        previous = _gains(application.get("previous_gains", trial.get("previous_gains")))
        if applied is None or previous is None:
            unresolved("verification_settings_changed")
            return
        current = self._simulate(model, points, cfg, applied, applied)
        prior = self._simulate(model, points, cfg, previous, applied)
        if current is None or prior is None or current["response_rmse"] > self._sample["band"] * .75:
            unresolved("verification_conditions_changed")
            return
        current_score = _score(performance, self._sample["band"])
        prior_score = _score(prior["performance"], self._sample["band"])
        token = _hash([trial.get("application", {}).get("evidence_id"), self.context,
                       points[-1]["at"], performance, prior["performance"]])
        trial.update(
            evidence_id=token, evidence_at=points[-1]["at"], context=self.context,
            result=deepcopy(performance), counterfactual_previous=prior["performance"],
            fresh_verification_required=False,
        )
        if current_score > prior_score * 1.12 + .05:
            trial.update(
                state="rollback_recommended", reason="performance_worsened",
                previous_gains=deepcopy(applied), revert_gains=deepcopy(previous),
            )
            base.update(status="rollback", reason="performance_worsened",
                        evidence_id=token, fresh_evidence=True)
        elif current_score <= prior_score * 1.03 + .02:
            trial.update(state="retained", reason="adjustment_verified")
            self.last_result = deepcopy(trial)
            base.update(status="verified", reason="adjustment_verified", evidence_id=token)
        else:
            unresolved("verification_inconclusive")

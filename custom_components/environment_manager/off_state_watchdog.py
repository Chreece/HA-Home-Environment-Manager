"""Conservative room thermal anomaly detector for HEM-owned OFF devices.

A room warming after shutdown is circumstantial evidence, NOT proof that an
appliance's relay/valve is physically ON. This detector never sends a command.
Its output is advisory unless an independent physical-output sensor confirms
unexpected heat production; HEM's existing actuator journal owns all writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

MIN_OFF_SECONDS = 30 * 60
MIN_SAMPLE_SPAN_SECONDS = 15 * 60
MAX_SAMPLE_AGE_SECONDS = 10 * 60
MIN_EXCESS_C = 1.5
MIN_RISE_C = 0.7
MAX_SAMPLES = 16


@dataclass
class ThermalWatch:
    """Session-bound independent room sensor evidence for one native endpoint."""

    source_ids: tuple[str, ...]
    off_since: float
    samples: list[tuple[float, float]] = field(default_factory=list)
    alerted: bool = False
    last_alert_at: float | None = None

    def observe(self, *, now: float, temperature_c: float | None,
                target_c: float | None, source_ids: tuple[str, ...],
                off_since: float, other_heat_sources_clear: bool,
                independent_heat_output: bool | None = None) -> str:
        """Return none, suspected, or confirmed; never infer physical ON.

        Only compare the same independent room sensor inventory and same
        verified OFF episode. No interpolation over missing measurements.
        """
        if (not isfinite(now) or not isfinite(off_since) or now < off_since
                or source_ids != self.source_ids
                or abs(off_since - self.off_since) > 1):
            self.samples.clear()
            return "none"
        if (temperature_c is None or target_c is None
                or not isfinite(temperature_c) or not isfinite(target_c)
                or not -30 <= temperature_c <= 60
                or not 5 <= target_c <= 40):
            self.samples.clear()
            return "none"
        if not other_heat_sources_clear:
            self.samples.clear()
            return "none"
        if self.samples and (now < self.samples[-1][0]
                or now - self.samples[-1][0] > MAX_SAMPLE_AGE_SECONDS):
            self.samples.clear()
        if not self.samples or now > self.samples[-1][0]:
            self.samples.append((now, temperature_c))
            self.samples = self.samples[-MAX_SAMPLES:]
        if now - off_since < MIN_OFF_SECONDS or len(self.samples) < 2:
            return "none"
        first_time, first_temp = self.samples[0]
        if (now - first_time < MIN_SAMPLE_SPAN_SECONDS
                or temperature_c - target_c < MIN_EXCESS_C
                or temperature_c - first_temp < MIN_RISE_C):
            return "none"
        return "confirmed" if independent_heat_output is True else "suspected"

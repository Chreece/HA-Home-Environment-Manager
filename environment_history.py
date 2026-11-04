"""Small bounded history for evidence-qualified environmental indicators.

Persisted through Home Assistant Store by the manager; no cloud, no Recorder
database queries, no raw occupancy log. Snapshot sampling is capped at 5 min.
"""
from __future__ import annotations

import math
import time
from typing import Any

from .building_physics import WEEK_S, DAY_S


FIELDS = frozenset((
    "temperature_c", "humidity", "pm25", "pm10", "co2", "surface_rh",
    "outdoor_temperature_c", "window_open", "occupied",
    "radon", "noise_dba", "hcho", "lux", "melanopic_edi",
    "outdoor_pm25", "outdoor_pm10",
    "radon_source",
))
MAX_AGE = 8 * DAY_S
MAX_POINTS_PER_AREA = 2600
# Bounded, native-contributor-specific time-series for actual 2+ sensor means.
AVG_ALLOWED = frozenset((
    "temperature","humidity","co2","pm25","pm10","pm1","pm4",
    "illuminance","voc","voc_parts","aqi","no2","o3","so2",
    "hcho","formaldehyde","radon","noise",
))
AVG_MAX_AGE = 7 * DAY_S
AVG_MAX_POINTS = 672
AVG_MIN_SAMPLE_SECONDS = 900


class EnvironmentHistory:
    def __init__(self, areas: dict[str, list[dict]] | None = None,
                 daily: dict[str, list[dict]] | None = None,
                 averages: dict[str, dict[str, dict]] | None = None):
        self.areas: dict[str, list[dict]] = areas if areas is not None else {}
        self.daily: dict[str, list[dict]] = daily if daily is not None else {}
        self.averages: dict[str, dict[str, dict]] = averages if averages is not None else {}

    @classmethod
    def restore(cls, data: Any, *, now: float | None = None) -> "EnvironmentHistory":
        current = time.time() if now is None else now
        if not isinstance(data, dict) or data.get("version") != 1:
            return cls()
        areas: dict[str, list[dict]] = {}
        source = data.get("areas")
        if not isinstance(source, dict):
            return cls()
        for area, points in list(source.items())[:150]:
            if not isinstance(area, str) or not isinstance(points, list):
                continue
            valid = []
            for point in points[-MAX_POINTS_PER_AREA:]:
                if not isinstance(point, dict):
                    continue
                try:
                    stamp = float(point["t"])
                except (TypeError, ValueError, KeyError, OverflowError):
                    continue
                if not math.isfinite(stamp) or not current - MAX_AGE <= stamp <= current + 60:
                    continue
                clean = {"t": stamp}
                for key in FIELDS:
                    val = point.get(key)
                    if key == "radon_source":
                        if isinstance(val, str) and val.startswith("sensor.") and len(val) <= 255:
                            clean[key] = val
                    elif key in ("occupied", "window_open"):
                        if type(val) is bool:
                            clean[key] = val
                    elif isinstance(val, (int, float)) and math.isfinite(val):
                        clean[key] = float(val)
                valid.append(clean)
            valid.sort(key=lambda p: p["t"])
            if valid:
                areas[area] = valid
        daily = {}
        raw_daily = data.get("daily")
        if isinstance(raw_daily, dict):
            for key, rows in list(raw_daily.items())[:150]:
                if not isinstance(key, str) or not isinstance(rows, list) or len(key) > 512:
                    continue
                valid_rows = []
                for item in rows[-370:]:
                    if not isinstance(item, dict):
                        continue
                    day, mean, coverage = item.get("day"), item.get("mean_bq_m3"), item.get("coverage_percent")
                    if (type(day) is int and current / DAY_S - 370 <= day <= current / DAY_S
                            and isinstance(mean, (float, int)) and math.isfinite(mean) and 0 <= mean <= 10000
                            and isinstance(coverage, (float, int)) and math.isfinite(coverage) and 80 <= coverage <= 100):
                        valid_rows.append({"day": day, "mean_bq_m3": float(mean),
                                           "coverage_percent": float(coverage)})
                if valid_rows:
                    daily[key] = sorted(valid_rows, key=lambda r: r["day"])
        averages: dict[str, dict[str, dict]] = {}
        stored = data.get("averages")
        if isinstance(stored, dict):
            for area, metrics in list(stored.items())[:80]:
                if not isinstance(area, str) or len(area) > 128 or not isinstance(metrics, dict):
                    continue
                valid_metrics = {}
                for metric, series in list(metrics.items())[:len(AVG_ALLOWED)]:
                    if metric not in AVG_ALLOWED or not isinstance(series, dict):
                        continue
                    sources = series.get("sources")
                    if (not isinstance(sources, list) or not 2 <= len(sources) <= 32
                            or len(set(sources)) != len(sources)
                            or any(not isinstance(source, str) or not source.startswith("sensor.")
                                   or len(source) > 255 for source in sources)):
                        continue
                    points = []
                    for point in (series.get("points") or [])[-AVG_MAX_POINTS:]:
                        if not isinstance(point, dict):
                            continue
                        t, value = point.get("t"), point.get("v")
                        if (type(t) not in (int, float) or type(value) not in (int, float)
                                or not math.isfinite(t) or not math.isfinite(value)
                                or not current - AVG_MAX_AGE <= t <= current + 60):
                            continue
                        if points and t <= points[-1]["t"]:
                            continue
                        points.append({"t": round(float(t), 3), "v": round(float(value), 3)})
                    if points:
                        valid_metrics[metric] = {
                            "sources": sorted(sources), "points": points,
                        }
                if valid_metrics:
                    averages[area] = valid_metrics
        return cls(areas, daily, averages)

    def snapshot(self) -> dict:
        return {"version": 1, "areas": self.areas, "daily": self.daily,
                "averages": self.averages}

    def add_average(self, area: str, metric: str, sources: list[str],
                    value: float, *, now: float) -> bool:
        """Persist only valid simultaneous 2+ native-sensor arithmetic means.

        Changing the exact contributing source set creates a new series;
        a temporarily missing source creates a gap, never a fake one-sensor mean.
        """
        if (not isinstance(area, str) or len(area) > 128 or metric not in AVG_ALLOWED
                or type(value) not in (int, float) or not math.isfinite(value)
                or not isinstance(sources, list) or len(sources) > 32
                or not isinstance(now, (int, float)) or not math.isfinite(now)):
            return False
        if (any(not isinstance(source, str) or not source.startswith("sensor.")
                or len(source) > 255 for source in sources)):
            return False
        unique = sorted(set(sources))
        if len(unique) < 2 or len(unique) != len(sources):
            return False
        room = self.averages.setdefault(area, {})
        series = room.get(metric)
        changed = not isinstance(series, dict) or series.get("sources") != unique
        if changed:
            series = {"sources": unique, "points": []}
            room[metric] = series
        points = series["points"]
        if points and now < points[-1]["t"]:
            return changed
        if points and now - points[-1]["t"] < AVG_MIN_SAMPLE_SECONDS:
            return changed
        points.append({"t": round(now, 3), "v": round(float(value), 3)})
        points[:] = [p for p in points if p["t"] >= now - AVG_MAX_AGE][-AVG_MAX_POINTS:]
        return True

    def average_trend(self, area: str, metric: str, sources: list[str],
                      *, limit: int = 72) -> list[dict]:
        """Bounded 7-day chart, only for the CURRENT identical source set."""
        series = self.averages.get(area, {}).get(metric)
        if (not isinstance(series, dict) or len(sources) < 2
                or series.get("sources") != sorted(sources)):
            return []
        points = series.get("points", [])
        if not points:
            return []
        stride = max(1, math.ceil((len(points) - 1) / max(1, min(limit, 96) - 1)))
        view = points[::stride]
        if view[-1] is not points[-1]:
            view = [*view, points[-1]]
        return [{"t": p["t"], "v": p["v"]} for p in view]

    def add(self, area: str, observation: dict[str, Any], *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        if not isinstance(area, str) or not area or not math.isfinite(current):
            return False
        points = self.areas.setdefault(area, [])
        min_stamp = current - MAX_AGE
        if points and points[-1]["t"] > current:
            return False
        data = {"t": round(current, 3)}
        for key in FIELDS:
            val = observation.get(key)
            if key == "radon_source":
                if isinstance(val, str) and val.startswith("sensor.") and len(val) <= 255:
                    data[key] = val
            elif key in ("occupied", "window_open"):
                if type(val) is bool:
                    data[key] = val
            elif isinstance(val, (int, float)) and math.isfinite(val):
                data[key] = float(val)
        if points and current - points[-1]["t"] < 300:
            # Record window/occupancy transitions immediately to segment ACH.
            if all(points[-1].get(key) == data.get(key) for key in ("occupied", "window_open")):
                return False
        points.append(data)
        points[:] = [s for s in points if s["t"] >= min_stamp][-MAX_POINTS_PER_AREA:]
        return True

    def samples(self, area: str) -> list[dict]:
        return self.areas.get(area, [])

    def record_qualified_radon_days(self, area: str, source: str, *, now: float) -> bool:
        """Accumulate up to 370 confirmed UTC 24h radon means, source-specific.

        No guesswork for unmeasured historical days and no merging sensors
        that could have different calibration/placement.
        """
        from .building_physics import weighted_window
        if not area or not source or not math.isfinite(now):
            return False
        key = area + "|" + source
        history = self.daily.setdefault(key, [])
        existing = {item["day"] for item in history}
        last_complete_day = int(now // DAY_S) - 1
        newly = False
        # Only the last seven days can have enough raw source observations.
        for day in range(max(0,last_complete_day - 7), last_complete_day + 1):
            if day in existing:
                continue
            end = (day + 1) * DAY_S
            scoped = [row for row in self.samples(area)
                      if row.get("radon_source") == source]
            window = weighted_window(scoped, "radon", end, DAY_S, min_coverage=0.8)
            if window.get("status") == "ready":
                history.append({"day": day, "mean_bq_m3": window["mean"],
                                "coverage_percent": window["coverage_percent"]})
                newly = True
        history.sort(key=lambda x: x["day"])
        history[:] = [d for d in history if d["day"] >= now // DAY_S - 370][-370:]
        return newly

    def radon_days(self, area: str, source: str) -> list[dict]:
        return self.daily.get(area + "|" + source, [])

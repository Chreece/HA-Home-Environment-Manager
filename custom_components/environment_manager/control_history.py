"""Bounded, observed target and controller-output intervals for trend overlays.

These are presentation observations, not command journals or actuation authority.
The interval end is advanced only by a real observation; reading history cannot
invent a target before its first sample or extend it through a restart/outage.
"""
from __future__ import annotations

from collections import deque
import heapq
import math
import re
from typing import Any


CONTROL_METRICS = frozenset(("temperature", "humidity", "mold", "co2", "pm25"))
CONTROL_MAX_AGE = 7 * 86400
CONTROL_SAMPLE_SECONDS = 300
CONTROL_MAX_GAP_SECONDS = 900
CONTROL_MAX_CONTROLLERS = 64
CONTROL_MAX_SERIES = 8
CONTROL_MAX_POINTS = 4096
CONTROL_MAX_TOTAL_POINTS = 32768
_QUANTITIES = {
    "temperature": ("temperature", "°C", -100., 150.),
    "humidity": ("room_relative_humidity", "%", 0., 100.),
    "mold": ("mold_surface_rh", "%", 0., 100.),
    "co2": ("co2", "ppm", 0., 100000.),
    "pm25": ("pm25", "µg/m³", 0., 100000.),
}
_OUTPUT_KINDS = frozenset(("activity", "binary", "percentage", "position"))
_TARGET_KINDS = frozenset(("control", "derived_room_rh", "physical_device"))
_ENTITY = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$")
_METADATA = ("metric", "basis", "unit", "feedback_source_ids", "context_id", "target_kind",
             "source_entity_ids")
_OPTIONAL_TEXT = {"status": 96, "target_unavailable_reason": 128}


def _text(value: Any, limit: int) -> str | None:
    if (isinstance(value, str) and 0 < len(value) <= limit
            and not any(ord(char) < 32 for char in value)):
        return value
    return None


def _number(value: Any, low: float, high: float, digits: int = 3) -> float | None:
    if type(value) in (int, float) and math.isfinite(value) and low <= value <= high:
        return round(float(value), digits)
    return None


def _sources(value: Any, *, allow_empty: bool = False) -> list[str] | None:
    if (not isinstance(value, (list, tuple)) or not (0 if allow_empty else 1) <= len(value) <= 32
            or any(not isinstance(item, str) or len(item) > 255 or not _ENTITY.fullmatch(item)
                   for item in value) or len(set(value)) != len(value)):
        return None
    return sorted(value)


def _metadata(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    controller, area = _text(raw.get("controller_id"), 255), _text(raw.get("area_id"), 128)
    metric = raw.get("metric")
    if controller is None or area is None or not isinstance(metric, str) or metric not in CONTROL_METRICS:
        return None
    basis, unit, _low, _high = _QUANTITIES[metric]
    if raw.get("basis") != basis or raw.get("unit") != unit:
        return None
    physical = _sources(raw.get("source_entity_ids"))
    feedback = _sources(raw.get("feedback_source_ids"), allow_empty=True)
    if physical is None or feedback is None:
        return None
    # Native/mean charts are always sensor-backed. Derived mold keeps its own
    # explicit temperature, humidity and weather provenance instead.
    if metric != "mold" and any(not value.startswith("sensor.") for value in feedback):
        return None
    context = raw.get("context_id") if raw.get("context_id") is not None else "default"
    if _text(context, 128) is None:
        return None
    target_kind = raw.get("target_kind", "control")
    if (not isinstance(target_kind, str) or target_kind not in _TARGET_KINDS
            or target_kind == "derived_room_rh" and metric != "humidity"):
        return None
    return {
        "controller_id": controller, "area_id": area,
        "name": _text(raw.get("name"), 160) or controller,
        "source_entity_ids": physical, "metric": metric, "basis": basis, "unit": unit,
        "feedback_source_ids": feedback, "context_id": context, "target_kind": target_kind,
    }


def _point(raw: Any, metadata: dict, now: float) -> dict | None:
    if not isinstance(raw, dict):
        return None
    _basis, _unit, low, high = _QUANTITIES[metadata["metric"]]
    result = {key: _number(raw.get(key), low, high)
              for key in ("target", "target_low", "target_high", "measured")}
    if metadata["metric"] != "temperature":
        result["target_low"] = result["target_high"] = None
    if (result["target_low"] is None or result["target_high"] is None
            or result["target_low"] > result["target_high"]):
        result["target_low"] = result["target_high"] = None
    result["demand_percent"] = _number(raw.get("demand_percent"), 0, 100, 1)
    kind = raw.get("output_kind")
    kind = kind if isinstance(kind, str) and kind in _OUTPUT_KINDS else None
    output = _number(raw.get("output_percent"), 0, 100, 1) if kind else None
    if kind in ("activity", "binary") and output not in (0., 100.):
        output = None
    entity = raw.get("output_entity_id")
    if entity is not None and entity not in metadata["source_entity_ids"]:
        # A different physical endpoint cannot be relabelled this controller's
        # reported output, even if a malformed stored point says otherwise.
        output = None
        entity = None
    result.update(output_percent=output, output_kind=kind,
                  profile=_text(raw.get("profile"), 64),
                  mode=_text(raw.get("mode"), 64),
                  control_mode=_text(raw.get("control_mode"), 64))
    if entity is not None:
        result["output_entity_id"] = entity
    if (reported := _number(raw.get("output_reported_at"), now - CONTROL_MAX_AGE, now + 60)) is not None:
        result["output_reported_at"] = reported
    if (result["demand_percent"] is not None
            and (reported := _number(raw.get("demand_reported_at"), now - CONTROL_MAX_AGE, now + 60)) is not None):
        result["demand_reported_at"] = reported
    for key, limit in _OPTIONAL_TEXT.items():
        if (value := _text(raw.get(key), limit)) is not None:
            result[key] = value
    return result


def _key(metadata: dict) -> tuple:
    return (metadata["metric"], metadata["basis"], metadata["unit"],
            tuple(metadata["feedback_source_ids"]), metadata.get("context_id"),
            metadata["target_kind"], tuple(metadata["source_entity_ids"]))


def _values(point: dict) -> dict:
    """Measured feedback is sampled; only actual control changes are events."""
    return {**{key: value for key, value in point.items()
               if key not in ("t", "until", "break_before", "target_break_before", "measured", "output_reported_at",
                              "demand_reported_at")},
            "measurement_available": point.get("measured") is not None}


class ControlHistory:
    """Up to seven days, with fixed per-controller/context and global budgets."""

    def __init__(self) -> None:
        self._controllers: dict[str, dict] = {}
        self._count = 0
        self._oldest: list[tuple] = []
        self._serial = 0

    def _queue(self, controller: str, key: tuple, series: dict) -> None:
        self._serial += 1
        series["_serial"] = self._serial
        if series["points"]:
            heapq.heappush(self._oldest, (series["points"][0]["t"], self._serial, controller, key))

    def _drop_series(self, controller: str, key: tuple) -> None:
        record = self._controllers.get(controller)
        if record is None:
            return
        series = record["series"].pop(key, None)
        if series is not None:
            self._count -= len(series["points"])
        if not record["series"]:
            self._controllers.pop(controller, None)

    def _compact_heap(self) -> None:
        # Context churn must not leave an unbounded list of stale heap entries.
        number = sum(len(record["series"]) for record in self._controllers.values())
        if len(self._oldest) <= 2 * number + 1024:
            return
        self._oldest.clear()
        for controller, record in self._controllers.items():
            for key, series in record["series"].items():
                self._queue(controller, key, series)

    def _prune(self, now: float) -> bool:
        changed = False
        cutoff = now - CONTROL_MAX_AGE
        # Only the oldest retained point is considered on ordinary updates;
        # never sort the complete multi-controller history on a status change.
        while self._oldest:
            stamp, serial, controller, key = self._oldest[0]
            record = self._controllers.get(controller)
            series = record["series"].get(key) if record else None
            if series is None or series.get("_serial") != serial:
                heapq.heappop(self._oldest)
                continue
            if stamp >= cutoff and self._count <= CONTROL_MAX_TOTAL_POINTS:
                break
            heapq.heappop(self._oldest)
            series["points"].popleft()
            self._count -= 1
            changed = True
            if series["points"]:
                self._queue(controller, key, series)
            else:
                self._drop_series(controller, key)
        self._compact_heap()
        return changed

    def observe(self, observation: Any, *, now: float) -> bool:
        """Observe one exact controller/context without making an output claim.

        Identical control values extend their known interval; five-minute
        heartbeats retain real feedback samples. Target, profile, method and
        reported-output transitions are kept immediately. Heavy event traffic
        can therefore retain less than seven days under the fixed budgets.
        """
        stamp = _number(now, 0, 1e13)
        metadata = _metadata(observation)
        if stamp is None or metadata is None:
            return False
        point = _point(observation.get("point"), metadata, stamp)
        if point is None:
            return False
        controller, key = metadata["controller_id"], _key(metadata)
        record = self._controllers.get(controller)
        series = record["series"].get(key) if record else None
        if series and series["points"] and stamp < series["points"][-1]["until"]:
            return False
        changed = self._prune(stamp)
        record = self._controllers.get(controller)
        if record is not None and record["area_id"] != metadata["area_id"]:
            # A moved controller does not carry another room's historical
            # targets into the new room. Discard that identity's old room data.
            for old_key in list(record["series"]):
                self._drop_series(controller, old_key)
            record = None
            changed = True
        if record is None:
            if len(self._controllers) >= CONTROL_MAX_CONTROLLERS:
                oldest = min(self._controllers, key=lambda identifier: max(
                    row["points"][-1]["until"]
                    for row in self._controllers[identifier]["series"].values()))
                for old_key in list(self._controllers[oldest]["series"]):
                    self._drop_series(oldest, old_key)
            record = self._controllers[controller] = {
                "controller_id": controller, "area_id": metadata["area_id"],
                "name": metadata["name"], "source_entity_ids": metadata["source_entity_ids"],
                "series": {},
            }
        record["name"] = metadata["name"]
        record["source_entity_ids"] = metadata["source_entity_ids"]
        # Returning to an earlier source/calibration context must leave a gap
        # across the intervening observations of a different context.
        for old_key, old in record["series"].items():
            if old_key != key and old["metric"] == metadata["metric"]:
                old["gap"] = True
        series = record["series"].get(key)
        if series is None:
            if len(record["series"]) >= CONTROL_MAX_SERIES:
                oldest_key = min(record["series"], key=lambda candidate:
                                 record["series"][candidate]["points"][-1]["until"])
                self._drop_series(controller, oldest_key)
                # At least seven other contexts remain in the record.
            series = record["series"][key] = {
                **{field: metadata[field] for field in _METADATA}, "points": deque(),
                "gap": False,
            }
        points = series["points"]
        previous = points[-1] if points else None
        interrupted = bool(series.get("gap") or previous
                           and stamp - previous["until"] > CONTROL_MAX_GAP_SECONDS)
        values_changed = previous is None or _values(previous) != _values(point)
        heartbeat = previous is not None and stamp - previous["t"] >= CONTROL_SAMPLE_SECONDS
        if previous is not None and not interrupted and not values_changed and not heartbeat:
            if previous["until"] == stamp:
                return changed
            previous["until"] = stamp
            return True
        if previous is not None and not interrupted:
            previous["until"] = stamp
        fresh = {"t": stamp, "until": stamp, **point}
        if interrupted:
            fresh["break_before"] = True
        if series.get("gap"):
            # A restart, removed controller or changed source ends the setpoint
            # history too. Elapsed time alone only interrupts sampled outputs.
            fresh["target_break_before"] = True
        series["gap"] = False
        if previous is not None and previous["t"] == stamp:
            if previous.get("break_before") is True:
                fresh["break_before"] = True
            if previous.get("target_break_before") is True:
                fresh["target_break_before"] = True
            points[-1] = fresh
        else:
            points.append(fresh)
            self._count += 1
            if len(points) == 1:
                self._queue(controller, key, series)
            if len(points) > CONTROL_MAX_POINTS:
                points.popleft()
                self._count -= 1
                self._queue(controller, key, series)
        self._prune(stamp)
        return True

    def pause(self, controller_id: str, *, now: float) -> bool:
        """Stop continuity without extending an interval into missing evidence."""
        if _number(now, 0, 1e13) is None:
            return False
        record = self._controllers.get(controller_id)
        if record is None:
            return False
        changed = False
        for series in record["series"].values():
            if not series.get("gap"):
                series["gap"] = True
                changed = True
        return changed

    def reconcile(self, observations: Any, *, now: float) -> bool:
        """Observe a complete inventory and pause identities absent this time."""
        if not isinstance(observations, (list, tuple)) or _number(now, 0, 1e13) is None:
            return False
        seen = set()
        changed = False
        # One observation per metric per bounded controller inventory. Larger
        # malformed inputs cannot turn a passive snapshot into unbounded work.
        for observation in observations[:CONTROL_MAX_CONTROLLERS * CONTROL_MAX_SERIES]:
            metadata = _metadata(observation)
            if metadata is None or not isinstance(observation.get("point"), dict):
                continue
            seen.add((metadata["controller_id"], _key(metadata)))
            changed = self.observe(observation, now=now) or changed
        for controller, record in self._controllers.items():
            for key, series in record["series"].items():
                if (controller, key) not in seen and not series.get("gap"):
                    series["gap"] = True
                    changed = True
        return self._prune(now) or changed

    def reconcile_controller(self, controller_id: str, observations: Any, *, now: float) -> bool:
        """Refresh one controller without pausing any peer's separate history."""
        if (not isinstance(observations, (list, tuple)) or _text(controller_id, 255) is None
                or _number(now, 0, 1e13) is None):
            return False
        seen = set()
        changed = False
        for observation in observations[:CONTROL_MAX_SERIES]:
            metadata = _metadata(observation)
            if (metadata is None or metadata["controller_id"] != controller_id
                    or not isinstance(observation.get("point"), dict)):
                continue
            seen.add(_key(metadata))
            changed = self.observe(observation, now=now) or changed
        record = self._controllers.get(controller_id)
        if record is not None:
            for key, series in record["series"].items():
                if key not in seen and not series.get("gap"):
                    series["gap"] = True
                    changed = True
        return self._prune(now) or changed

    def snapshot(self) -> dict:
        """A detached JSON-safe payload for the existing entry-owned Store."""
        return {"version": 1, "controllers": [{
            **{key: (list(value) if isinstance(value, list) else value)
               for key, value in record.items() if key != "series"},
            "series": [{
                **{field: (list(series[field]) if isinstance(series[field], list) else series[field])
                   for field in _METADATA},
                "gap": series.get("gap") is True,
                "points": [dict(point) for point in series["points"]],
            } for series in record["series"].values()],
        } for record in self._controllers.values()]}

    @classmethod
    def restore(cls, raw: Any, *, now: float) -> "ControlHistory":
        history = cls()
        stamp = _number(now, 0, 1e13)
        if (stamp is None or not isinstance(raw, dict) or raw.get("version") != 1
                or not isinstance(raw.get("controllers"), list)):
            return history
        # Only bounded controller/context metadata is inspected. Points are
        # restored through a bounded global heap so corrupt input cannot retain
        # an unbounded intermediate collection before final pruning.
        candidates = []
        for raw_controller in raw["controllers"][-CONTROL_MAX_CONTROLLERS:]:
            if not isinstance(raw_controller, dict) or not isinstance(raw_controller.get("series"), list):
                continue
            for raw_series in raw_controller["series"][-CONTROL_MAX_SERIES:]:
                if not isinstance(raw_series, dict) or not isinstance(raw_series.get("points"), list):
                    continue
                # A series cannot override its containing controller's owner
                # or room and multiply the bounded controller inventory.
                metadata = _metadata({
                    **{field: raw_controller.get(field)
                       for field in ("controller_id", "area_id", "name")},
                    **{field: raw_series.get(field) for field in _METADATA},
                })
                if metadata is not None:
                    candidates.append((metadata, raw_series["points"][-CONTROL_MAX_POINTS:]))
        retained: list[tuple] = []
        sequence = 0
        for index, (metadata, raw_points) in enumerate(candidates):
            previous = None
            for raw_point in raw_points:
                if not isinstance(raw_point, dict):
                    continue
                at = _number(raw_point.get("t"), stamp - CONTROL_MAX_AGE, stamp + 60)
                end = _number(raw_point.get("until"), at if at is not None else 0, stamp + 60)
                if (at is None or end is None
                        or end - at > CONTROL_MAX_GAP_SECONDS + CONTROL_SAMPLE_SECONDS
                        or previous is not None and at <= previous):
                    continue
                clean = _point(raw_point, metadata, stamp)
                if clean is None:
                    continue
                previous = at
                point = {"t": at, "until": end, **clean}
                if raw_point.get("break_before") is True:
                    point["break_before"] = True
                if raw_point.get("target_break_before") is True:
                    point["target_break_before"] = True
                sequence += 1
                row = (at, sequence, index, point)
                if len(retained) < CONTROL_MAX_TOTAL_POINTS:
                    heapq.heappush(retained, row)
                elif at > retained[0][0]:
                    heapq.heapreplace(retained, row)
        for _at, _sequence, index, point in sorted(retained):
            metadata = candidates[index][0]
            controller, key = metadata["controller_id"], _key(metadata)
            record = history._controllers.get(controller)
            if record is not None and record["area_id"] != metadata["area_id"]:
                continue
            if record is None:
                record = history._controllers[controller] = {
                    "controller_id": controller, "area_id": metadata["area_id"],
                    "name": metadata["name"], "source_entity_ids": metadata["source_entity_ids"],
                    "series": {},
                }
            record["name"] = metadata["name"]
            record["source_entity_ids"] = metadata["source_entity_ids"]
            series = record["series"].get(key)
            if series is None:
                if len(record["series"]) >= CONTROL_MAX_SERIES:
                    continue
                series = record["series"][key] = {
                    **{field: metadata[field] for field in _METADATA}, "points": deque(), "gap": True,
                }
            points = series["points"]
            if points and point["t"] <= points[-1]["t"]:
                continue
            if points:
                # A corrupt overlapping interval cannot imply that two targets
                # were simultaneously active for this same physical context.
                points[-1]["until"] = min(points[-1]["until"], point["t"])
            points.append(point)
            history._count += 1
            if len(points) > CONTROL_MAX_POINTS:
                points.popleft()
                history._count -= 1
        for controller, record in history._controllers.items():
            for key, series in record["series"].items():
                history._queue(controller, key, series)
        history._prune(stamp)
        return history

    def view(self, area_id: str, metric: str, source_ids: list[str], *, now: float) -> list[dict]:
        """Copy compatible observations only; never append a current anchor."""
        stamp = _number(now, 0, 1e13)
        sources = _sources(source_ids, allow_empty=metric == "mold")
        if (stamp is None or not isinstance(metric, str) or metric not in CONTROL_METRICS or sources is None
                or metric == "mold" and sources):
            return []
        result = []
        for record in self._controllers.values():
            if record["area_id"] != area_id:
                continue
            series_result = []
            for series in record["series"].values():
                if (series["metric"] != metric
                        or metric != "mold" and series["feedback_source_ids"] != sources):
                    continue
                points = [dict(point) for point in series["points"]
                          if stamp - CONTROL_MAX_AGE <= point["t"] <= stamp + 60]
                if points:
                    series_result.append({
                        **{field: (list(series[field]) if isinstance(series[field], list) else series[field])
                           for field in _METADATA}, "points": points,
                    })
            if series_result:
                result.append({"controller_id": record["controller_id"], "name": record["name"],
                               "area_id": area_id, "source_entity_ids": list(record["source_entity_ids"]),
                               "series": series_result})
        return result

"""Pure recommendation logic; independent of Home Assistant or I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json
import math

from .const import DEFAULT_THRESHOLDS, WEATHER_CLEAR


@dataclass(frozen=True)
class Reading:
    entity_id: str
    name: str
    metric: str
    value: float | None  # Normalized to the units documented in const.py.
    details: dict[str, float | int | str | list[str]] | None = None  # Derived mold data only.


@dataclass(frozen=True)
class Weather:
    entity_id: str
    condition: str | None
    temperature_c: float | None = None
    humidity: float | None = None
    wind_kmh: float | None = None


@dataclass(frozen=True)
class Warning:
    entity_id: str
    name: str
    active: bool | None  # None is unavailable/ambiguous and ignored, not an alert.


@dataclass(frozen=True)
class Window:
    entity_id: str
    name: str
    opened: bool | None


@dataclass(frozen=True)
class Room:
    area_id: str
    name: str
    windows: tuple[Window, ...]
    readings: tuple[Reading, ...]


@dataclass(frozen=True)
class Reason:
    code: str
    label: str = ""
    value: str = ""


@dataclass(frozen=True)
class Recommendation:
    action: str  # open | close
    area_id: str
    area_name: str
    windows: tuple[Window, ...]
    reasons: tuple[Reason, ...]
    # A manual airing opportunity is distinct from permission to draw outdoor
    # air mechanically. Keep adverse/unknown outside conditions explicit.
    cautions: tuple[Reason, ...] = ()
    wait_seconds: int = 0

    @property
    def action_signature(self) -> str:
        """Stable identity of the window action, independent of measurements."""
        return json.dumps(
            [self.action, self.area_id, sorted(w.entity_id for w in self.windows)],
            ensure_ascii=False, separators=(",", ":"),
        )

    @property
    def reason_signature(self) -> str:
        """Identity of an ongoing cause, ignoring numeric sensor oscillations.

        A different pollutant or warning starts a fresh reminder interval;
        fluctuating CO₂ or wind values above the same threshold do not.
        Weather-condition text is categorical and therefore significant.
        """
        reasons = sorted(
            [reason.code, reason.label,
             reason.value if reason.code == "weather_condition" else ""]
            for reason in self.reasons
        )
        cautions = sorted(
            [reason.code, reason.label,
             reason.value if reason.code == "weather_condition" else ""]
            for reason in self.cautions
        )
        return json.dumps([self.action_signature, reasons, cautions], ensure_ascii=False,
                          separators=(",", ":"))


@dataclass(frozen=True)
class Plan:
    status: str  # open | close | idle | blocked
    outdoor_safe: bool
    outside_reasons: tuple[Reason, ...]
    recommendations: tuple[Recommendation, ...]
    diagnostics: tuple[tuple[str, str], ...]  # area name, missing-input reason
    unavailable_outdoor: tuple[str, ...] = ()  # Non-blocking missing entity IDs.
    rooms: tuple[Room, ...] = ()
    outdoor_readings: tuple[Reading, ...] = ()
    weather: tuple[Weather, ...] = ()
    warnings: tuple[Warning, ...] = ()
    # Informational derived physics; not an additional measured air pollutant.
    environment: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Extra climate-only areas are displayed on the dashboard, never passed
    # into the window/announcement evaluator as monitored air-quality rooms.
    climate_rooms: tuple[Room, ...] = ()
    # Explicitly opted-in recommendations for climate-only rooms never
    # modify monitored-room air-quality totals or status.
    climate_recommendations: tuple[Recommendation, ...] = ()

    @property
    def signature(self) -> str:
        """Only actionable changes cause announcements, not numeric oscillations."""
        items = sorted(
            f"{rec.action}:{rec.area_id}:{','.join(sorted(w.entity_id for w in rec.windows))}"
            for rec in (*self.recommendations, *self.climate_recommendations)
        )
        return "|".join(items)


def _number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:,.1f}" if value != int(value) else f"{value:,.0f}"


def _reading_reason(prefix: str, reading: Reading) -> Reason:
    from .const import UNIT_LABEL

    return Reason(
        f"{prefix}_{reading.metric}",
        reading.name,
        f"{_number(reading.value)} {UNIT_LABEL.get(reading.metric, '')}".strip(),
    )


def _averaged_readings(readings: tuple[Reading, ...]) -> tuple[Reading, ...]:
    """One valid normalized mean per measured metric, keeping AQI scales separate.

    Individual unavailable/invalid sensor readings are discarded, not counted
    as zero. AQI is excluded because different provider scales are not
    directly comparable; derived mold evidence also remains independent.
    """
    groups: dict[str, list[Reading]] = {}
    for item in readings:
        group_key = item.metric if item.metric not in ("aqi", "mold", "unknown") else item.entity_id
        groups.setdefault(group_key, []).append(item)
    result = []
    for members in groups.values():
        if len(members) == 1:
            result.append(members[0])
            continue
        values = [
            float(item.value) for item in members
            if isinstance(item.value, (int, float)) and not isinstance(item.value, bool)
            and math.isfinite(item.value)
            and (0 < item.value <= 100 if item.metric == "humidity" else item.value >= 0)
        ]
        first = members[0]
        value = sum(values) / len(values) if values else None
        result.append(Reading(
            first.entity_id, first.name, first.metric, value,
            {"valid_sensor_count": len(values),
             "source_entities": [item.entity_id for item in members],
             "ignored_sensor_count": len(members) - len(values)},
        ))
    return tuple(result)


def _numeric_weather_mean(weather: tuple[Weather, ...], attribute: str,
                          minimum: float, maximum: float) -> float | None:
    values = [float(value) for item in weather
              if isinstance((value := getattr(item, attribute)), (int, float))
              and not isinstance(value, bool)
              and math.isfinite(value) and minimum <= value <= maximum]
    return sum(values) / len(values) if values else None


def _outdoor_not_lower(indoor: Reading, outdoor: tuple[Reading, ...]) -> bool:
    """Reject a claimed pollutant benefit contradicted by comparable evidence.

    Temperature and RH are deliberately excluded: their moisture effect needs
    the humidity-ratio calculation. AQI values only compare on the same
    explicitly verified scale; a numerical index from a different provider
    scale must never be treated as a concentration.
    """
    if indoor.metric not in (
        "co2", "pm25", "pm10", "voc", "voc_parts", "no2", "o3", "so2", "hcho", "aqi"
    ):
        return False
    if (not isinstance(indoor.value, (float, int)) or isinstance(indoor.value, bool)
            or not math.isfinite(indoor.value)):
        return False
    candidates = [item for item in outdoor if item.metric == indoor.metric
                  and isinstance(item.value, (float, int)) and not isinstance(item.value, bool)
                  and math.isfinite(item.value) and item.value >= 0]
    if indoor.metric == "aqi":
        inside_scale = (indoor.details or {}).get("aqi", {})
        if inside_scale.get("status") != "ready" or not inside_scale.get("scale"):
            return False
        # A custom cutoff is not a standardized index, even if both sources
        # happen to use the same word for their independently chosen scales.
        if inside_scale["scale"] == "custom":
            return False
        candidates = [item for item in candidates
                      if (item.details or {}).get("aqi", {}).get("status") == "ready"
                      and (item.details or {}).get("aqi", {}).get("scale") == inside_scale["scale"]]
    return any(item.value >= indoor.value for item in candidates)


def evaluate(
    outdoor: tuple[Reading, ...],
    weather: tuple[Weather, ...],
    warnings: tuple[Warning, ...],
    rooms: tuple[Room, ...],
    limits: dict[str, float] | None = None,
    environment: dict[str, dict[str, Any]] | None = None,
    extra_outside: tuple[Reason, ...] = (),
) -> Plan:
    """Keep machine safety separate from conditional manual airing advice."""
    thresholds = {**DEFAULT_THRESHOLDS, **(limits or {})}
    environmental = environment or {}
    outside: list[Reason] = list(extra_outside)
    unavailable_outdoor: list[str] = []

    # No configured sensors at all is a setup error, distinct from a selected
    # sensor currently reporting unknown/unavailable/stale.
    if not outdoor:
        outside.append(Reason("no_outdoor_data"))
    # Retain per-device diagnostics even when a different source makes the
    # same metric calculable.
    unavailable_outdoor.extend(
        item.entity_id for item in outdoor
        if item.value is None and item.metric != "aqi"
    )
    averaged_outdoor = _averaged_readings(outdoor)
    for reading in averaged_outdoor:
        if reading.metric == "aqi" and reading.value is not None:
            classification = (reading.details or {}).get("aqi", {})
            if classification.get("status") != "ready":
                unavailable_outdoor.append(reading.entity_id)
                outside.append(Reason("aqi_scale_unconfigured", reading.name))
                continue
            if classification.get("operational_unsafe"):
                outside.append(_reading_reason("outside", reading))
            continue
        limit = thresholds.get(f"outdoor_{reading.metric}")
        if reading.value is None or limit is None:
            if reading.value is None and reading.entity_id not in unavailable_outdoor:
                unavailable_outdoor.append(reading.entity_id)
            continue  # Unknown is not unsafe and must not trigger 'close'.
        if reading.value > limit:
            outside.append(_reading_reason("outside", reading))

    if not weather:
        outside.append(Reason("no_weather_data"))
    elif not any(item.condition is not None for item in weather):
        # No valid current weather condition remains: keep ventilation blocked.
        outside.append(Reason("unavailable_weather", weather[0].entity_id))
    for item in weather:
        # A rain/storm condition or active warning is not a numeric sample;
        # keep every reported hazard even with multiple stations.
        if item.condition is not None and item.condition not in WEATHER_CLEAR:
            outside.append(Reason("weather_condition", item.entity_id, item.condition))
    outdoor_temp = _numeric_weather_mean(weather, "temperature_c", -60, 85)
    outdoor_humidity = _numeric_weather_mean(weather, "humidity", 0.00001, 100)
    outdoor_wind = _numeric_weather_mean(weather, "wind_kmh", 0, 400)
    if outdoor_temp is not None and outdoor_temp < thresholds["min_outdoor_temp"]:
        outside.append(Reason("weather_cold", "Average weather temperature", f"{_number(outdoor_temp)} °C"))
    if outdoor_temp is not None and outdoor_temp > thresholds["max_outdoor_temp"]:
        outside.append(Reason("weather_hot", "Average weather temperature", f"{_number(outdoor_temp)} °C"))
    if outdoor_humidity is not None and outdoor_humidity > thresholds["max_outdoor_humidity"]:
        outside.append(Reason("weather_humid", "Average weather humidity", f"{_number(outdoor_humidity)} %"))
    if outdoor_wind is not None and outdoor_wind > thresholds["max_wind_kmh"]:
        outside.append(Reason("weather_wind", "Average weather wind", f"{_number(outdoor_wind)} km/h"))

    # Warning availability is optional evidence, not a weather hazard.
    # Keep the unknown source for diagnostics, but never turn it into an
    # active alert or block unrelated ventilation/climate decisions.
    for warning in warnings:
        if warning.active is True:
            outside.append(Reason("active_warning", warning.name))

    outdoor_safe = not outside
    # Unknown selected sensors are not hazards or proof of safe outdoor air.
    # They remain non-blocking diagnostics, but a spoken opening request must
    # not silently present incomplete outside data as verified suitable.
    opening_cautions = list(outside)
    for item in outdoor:
        if item.entity_id in unavailable_outdoor and not any(
            reason.label == item.name and reason.code in (
                "aqi_scale_unconfigured", "unavailable_outdoor"
            ) for reason in opening_cautions
        ):
            opening_cautions.append(Reason("unavailable_outdoor", item.name))
    # A manual request already explains these conditions as reasons for care.
    # Do not countermand it immediately when the user opens a window and the
    # measured indoor benefit persists. Severe weather, pollution, active
    # alerts and unknown outdoor evidence keep their immediate close rule.
    soft_outside_only = bool(outside) and all(
        reason.code in ("weather_cold", "weather_hot", "weather_humid")
        or reason.code == "weather_condition" and reason.value in ("rainy", "fog")
        for reason in outside
    )
    recommendations: list[Recommendation] = []
    diagnostics: list[tuple[str, str]] = []
    for room in rooms:
        if not room.windows:
            diagnostics.append((room.name, "no_windows"))
            continue
        opened = tuple(win for win in room.windows if win.opened is True)
        closed = tuple(win for win in room.windows if win.opened is False)
        unknown = tuple(win for win in room.windows if win.opened is None)
        if unknown:
            diagnostics.append((room.name, "unknown_window_state"))

        # Input diagnostics remain visible while outside concerns are assessed,
        # including during rain, storms or unavailable outdoor conditions.
        for item in room.readings:
            if item.metric != "mold" or item.value is not None:
                continue
            diagnostics.append((room.name, "mold_indicator_unavailable"))
            for missing in (item.details or {}).get("missing_inputs", []):
                if missing in (
                    "calibration", "indoor_temperature",
                    "outdoor_temperature", "humidity", "calculation",
                ):
                    diagnostics.append((room.name, f"mold_{missing}_unavailable"))

        if not outdoor_safe and opened and (not soft_outside_only or unknown):
            # Hard hazards and unverified contacts still close an exposed room
            # immediately. No second window in that room is requested open.
            recommendations.append(
                Recommendation("close", room.area_id, room.name, opened, tuple(outside))
            )
            continue

        indoor_reasons: list[Reason] = []
        room_environment = environmental.get(room.area_id, {})
        moisture = room_environment.get("moisture", {})
        moisture_status = moisture.get("status")
        for reading in _averaged_readings(room.readings):
            limit = thresholds.get(f"indoor_{reading.metric}")
            if reading.value is None or limit is None:
                continue
            if reading.value >= limit:
                # Never recommend moisture-only airing when measured outdoor
                # vapor mass is clearly higher, even if outdoor RH looks benign.
                # CO2 and PM are evaluated independently; without
                # paired, valid temperature/RH data legacy rules still apply.
                if reading.metric in ("humidity", "mold") and moisture_status in ("humidifying", "neutral"):
                    diagnostics.append((room.name, "outdoor_more_humid_than_indoor"
                                        if moisture_status == "humidifying" else "outdoor_no_drying_advantage"))
                    continue
                if _outdoor_not_lower(reading, averaged_outdoor):
                    diagnostics.append((room.name, f"outdoor_{reading.metric}_not_lower_than_indoor"))
                    continue
                indoor_reasons.append(_reading_reason("inside", reading))

        international = environmental.get(room.area_id, {}).get("international", {})
        hcho = international.get("formaldehyde_30min", {})
        if hcho.get("status") == "ready" and hcho.get("above_who_100ug_m3"):
            formaldehyde = Reading("", "Formaldehyde (30-min mean)", "hcho", hcho.get("mean"))
            if _outdoor_not_lower(formaldehyde, averaged_outdoor):
                diagnostics.append((room.name, "outdoor_hcho_not_lower_than_indoor"))
            else:
                indoor_reasons.append(Reason("inside_formaldehyde", formaldehyde.name,
                                             f'{hcho["mean"]:g} µg/m³'))
        cooling = room_environment.get("passive_cooling", {})
        comfort = room_environment.get("thermal_comfort", {})
        delta = cooling.get("cooling_delta_c")
        # The science module retains its strict outdoor machine-safety gate.
        # Its measured overheating/delta can still support a manual request
        # qualified by the actual outside concerns.
        cooling_needed = cooling.get("status") == "cooling_opportunity" or (
            cooling.get("status") == "outdoors_blocked"
            and comfort.get("status") == "above_band"
            and isinstance(delta, (float, int)) and not isinstance(delta, bool)
            and math.isfinite(delta) and delta >= 2
        )
        if cooling_needed and not indoor_reasons:
            indoor_reasons.append(Reason("inside_passive_cooling", "Cooling opportunity",
                                         f'{cooling["cooling_delta_c"]:g} °C'))
        climate_plan = environmental.get(room.area_id, {}).get("climate_plan", {})
        option = climate_plan.get("window_efficiency", {}) if isinstance(climate_plan,dict) else {}
        if (option.get("status") == "opportunity"
                and option.get("notify_enabled") is True
                and closed and not opened and not unknown):
            from .climate_window import window_reason
            # Existing pollutant or mold warnings keep first priority; the
            # mechanical alternative is still visible within the TTS limit.
            position = 1 if indoor_reasons else 0
            indoor_reasons.insert(position, window_reason(option))
        if not outdoor_safe and opened:
            # Only soft cautions reach here. Let an already-open window serve
            # the continuing measured need; once it resolves, request closure.
            # The separate room temperature/energy monitor can still issue an
            # earlier CLOSE near a heating/cooling target. No device guard or
            # user-response timeout is changed by this advisory exception.
            if not indoor_reasons:
                recommendations.append(
                    Recommendation("close", room.area_id, room.name, opened, tuple(outside))
                )
            continue
        if not any(reading.value is not None and reading.metric != "illuminance"
                   for reading in room.readings) and not indoor_reasons:
            diagnostics.append((room.name, "no_indoor_data"))
        elif indoor_reasons and closed and not opened and not unknown:
            cautions = list(opening_cautions)
            # Airing for another verified need (for example CO2) can still
            # worsen moisture. Describe that room-specific trade-off rather
            # than quietly dropping the humidity request without explanation.
            if moisture_status == "humidifying":
                advantage = moisture.get("drying_potential_g_kg")
                value = (f"{abs(advantage):g} g/kg" if isinstance(advantage, (float, int))
                         and not isinstance(advantage, bool) and math.isfinite(advantage) else "")
                cautions.append(Reason("outside_more_moisture", value=value))
            # Keep the general evaluator independent of Home Assistant;
            # climate opportunities carry JSON-safe caution dictionaries.
            for raw_caution in option.get("cautions", ()):
                if not isinstance(raw_caution, dict) or not isinstance(raw_caution.get("code"), str):
                    continue
                caution = Reason(raw_caution["code"], str(raw_caution.get("label") or ""),
                                 str(raw_caution.get("value") or ""))
                if caution not in cautions:
                    cautions.append(caution)
            recommendations.append(
                Recommendation("open", room.area_id, room.name, closed,
                               tuple(indoor_reasons), tuple(cautions))
            )

    has_open = any(rec.action == "open" for rec in recommendations)
    has_close = any(rec.action == "close" for rec in recommendations)
    status = "close" if has_close else "open" if has_open else "blocked" if not outdoor_safe else "idle"
    return Plan(
        status, outdoor_safe, tuple(outside), tuple(recommendations),
        tuple(diagnostics), tuple(unavailable_outdoor),
        tuple(rooms), tuple(outdoor), tuple(weather), tuple(warnings), environmental,
    )

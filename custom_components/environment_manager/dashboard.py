"""Compact, presentation-neutral snapshot for the Lovelace dashboard card.

The backend owns the safety decision and measurement normalisation; the card
only presents the result in the Home Assistant user's interface language.
"""

from __future__ import annotations

import math
from typing import Any

from .const import UNIT_LABEL
from .logic import Plan, Reading, Reason, Room, Weather, Warning

_MISSING_OUTSIDE = frozenset({
    "no_outdoor_data", "no_weather_data", "unavailable_weather", "unavailable_warning",
    "aqi_scale_unconfigured"
})


def _reason(reason: Reason) -> dict[str, str]:
    return {"code": reason.code, "label": reason.label, "value": reason.value}


def _reading(reading: Reading, threshold: float | None, *, indoor: bool) -> dict[str, Any]:
    value = reading.value
    aqi = (reading.details or {}).get("aqi", {}) if reading.metric == "aqi" else {}
    # An uncalibrated AQI index may have a numeric value but is not
    # evaluated evidence. Show it as incomplete, never as safe/green.
    trusted_aqi = indoor or reading.metric != "aqi" or aqi.get("status") == "ready"
    if aqi:
        threshold = aqi.get("custom_limit") if aqi.get("scale") == "custom" else (
            100 if aqi.get("scale") == "us_epa" else
            3 if aqi.get("scale") == "eea_category" else None
        )
    return {
        "entity_id": reading.entity_id,
        "name": reading.name,
        "metric": reading.metric,
        "unit": ("US AQI" if aqi.get("scale") == "us_epa"
                 else "EEA category" if aqi.get("scale") == "eea_category"
                 else UNIT_LABEL.get(reading.metric, "")),
        "value": value,
        "threshold": threshold,
        "available": value is not None and trusted_aqi,
        **({"details": reading.details} if reading.details else {}),
        "exceeded": (
            (bool(aqi.get("operational_unsafe")) if trusted_aqi else False)
            if aqi else
            (value is not None and threshold is not None
             and (value >= threshold if indoor else value > threshold))
        ),
    }


def _window(window: Any) -> dict[str, Any]:
    return {"entity_id": window.entity_id, "name": window.name, "opened": window.opened}


def _weather(item: Weather) -> dict[str, Any]:
    return {
        "entity_id": item.entity_id,
        "condition": item.condition,
        "temperature_c": item.temperature_c,
        "humidity": item.humidity,
        "wind_kmh": item.wind_kmh,
    }


def _warning(item: Warning) -> dict[str, Any]:
    return {"entity_id": item.entity_id, "name": item.name, "active": item.active}


def _room(room: Room, plan: Plan, limits: dict[str, float], *,
          climate_only: bool = False) -> dict[str, Any]:
    evidence = plan.environment.get(room.area_id, {}).get("measurement_evidence", {})
    readings = []
    for item in room.readings:
        data = _reading(item, limits.get(f"indoor_{item.metric}"), indoor=True)
        # Mold's substitute humidity is a derived room mean, not an HA sensor:
        # show the verified trend when 2+ physical RH sensors contribute.
        if (data.get("details") or {}).get("fallback_for_mold"):
            aggregate = evidence.get("humidity", {})
            if aggregate.get("source_count", 0) >= 2:
                data["average_evidence"] = {**aggregate, "area_id": room.area_id}
        readings.append(data)
    high = [item for item in readings if item["exceeded"]]
    # Estimated eCO₂ is displayed, but cannot alone certify that room air is
    # safe or complete the genuine pollutant evidence used by ventilation.
    air_readings = [item for item in readings
                    if item["metric"] not in ("illuminance", "eco2")]
    # A room has usable environmental data when at least ONE core room
    # measurement (temperature or relative humidity) is available.
    # Optional pollutant, mold and contact sensors must not turn a measured
    # room into "No data". Their unavailability is presented independently.
    def usable_number(value: Any) -> bool:
        return type(value) in (int, float) and math.isfinite(value)

    climate = plan.environment.get(room.area_id, {}).get("climate_plan", {})
    temp_available = any(usable_number(v) for v in (
        evidence.get("temperature", {}).get("value"),
        climate.get("temperature_c"),
        *(item["value"] for item in readings
          if item["metric"] in ("temperature", "temp") and item["available"]),
    ))
    rh_available = any(usable_number(v) for v in (
        evidence.get("humidity", {}).get("value"),
        *(item["value"] for item in readings
          if item["metric"] == "humidity" and item["available"]),
    ))
    missing_measurements = []
    if not temp_available:
        missing_measurements.append({"metric": "temperature", "name": "Temperature",
                                     "reason": "no_valid_core_measurement"})
    if not rh_available:
        missing_measurements.append({"metric": "humidity", "name": "Humidity",
                                     "reason": "no_valid_core_measurement"})
    for item in readings:
        if not item["available"] and item["metric"] not in ("temperature", "temp", "humidity"):
            missing_measurements.append({
                "metric": item["metric"], "name": item["name"],
                "entity_id": item["entity_id"], "reason": "configured_source_unavailable",
            })
    opened = [item for item in room.windows if item.opened is True]
    incomplete_windows = bool(room.windows) and any(item.opened is None for item in room.windows)
    recommended = next((rec for rec in
                        (*plan.recommendations,*plan.climate_recommendations)
                        if rec.area_id == room.area_id), None)

    # Urgent closure always needs attention, even if indoor sensors are missing.
    # Indoor values over a threshold remain important while already ventilating
    # or when opening is prevented by outdoor hazards.
    extended = plan.environment.get(room.area_id, {}).get("international", {})
    hcho = extended.get("formaldehyde_30min", {})
    radon = extended.get("radon", {})
    evidence_high = ((hcho.get("status") == "ready" and hcho.get("above_who_100ug_m3"))
                     or (radon.get("status") == "annual_screening" and radon.get("above_reference")))
    if high or evidence_high or (recommended and recommended.action == "close"):
        # Real hazards and urgent closure remain actionable even without both
        # core room readings; never conceal a hazard as missing data.
        status = "attention"
    elif not temp_available and not rh_available:
        status = "unknown"
    else:
        status = "safe"

    missing_mold = next(
        (item for item in readings if item["metric"] == "mold" and not item["available"]),
        None,
    )
    mold_details = (missing_mold or {}).get("details", {}) or {}
    mold_data_status = mold_details.get("status")
    mold_warnings = [
        code for code in mold_details.get("missing_inputs", [])
        if code in {
            "calibration", "indoor_temperature",
            "outdoor_temperature", "humidity", "calculation",
        }
    ]
    # The fallback is a measured room RH average, not a calculated surface
    # RH reading. The dashboard must label the substitution explicitly and
    # retain mold diagnostics even if the fallback itself is healthy.
    fallback = next(
        (item for item in readings
         if item["metric"] == "humidity"
         and (item.get("details") or {}).get("fallback_for_mold")
         and item["available"]),
        None,
    )
    if status == "unknown":
        status_detail = "no_core_room_data"
    elif missing_measurements or incomplete_windows:
        status_detail = "partial_indoor_data"
    else:
        status_detail = None

    return {
        "area_id": room.area_id,
        "name": room.name,
        "climate_only": climate_only,
        "status": status,
        "status_detail": status_detail,
        "core_measurements": {"temperature": temp_available, "humidity": rh_available},
        "missing_measurements": missing_measurements,
        "window_data_incomplete": incomplete_windows,
        "mold_warnings": mold_warnings,
        "environment": plan.environment.get(room.area_id, {}),
        "rh_fallback": (
            {
                "active": True,
                "value": fallback["value"],
                "threshold": fallback["threshold"],
                "humidity_sensor_count": fallback["details"]["humidity_sensor_count"],
            }
            if fallback else {"active": False}
        ),
        "action": recommended.action if recommended else None,
        "action_window_ids": [w.entity_id for w in recommended.windows] if recommended else [],
        "open_count": len(opened),
        "window_count": len(room.windows),
        "windows": [_window(item) for item in room.windows],
        "readings": readings,
        "high_count": len(high),
        "available_count": sum(item["available"] for item in readings),
        "ventilating": bool(opened) and plan.outdoor_safe,
        "reasons": [_reason(reason) for reason in recommended.reasons] if recommended else [],
        "cautions": [_reason(reason) for reason in recommended.cautions] if recommended else [],
        "window_open_wait": plan.environment.get(room.area_id,{}).get("window_open_wait",{}),
    }


def dashboard_snapshot(plan: Plan, limits: dict[str, float]) -> dict[str, Any]:
    """Describe *all* monitored rooms, not only actionable recommendations.

    Missing sensors are explicitly marked unknown, never optimistically green.
    Incomplete outside air readings are not a known hazard and must not trigger
    closing a window, but the UI must not imply complete verification either.
    """
    room_data = [_room(room, plan, limits) for room in plan.rooms]
    # Distinct from monitored rooms: show explicitly configured climate-only
    # rooms without making up window advice or inflating AQ summary totals.
    already={room.area_id for room in plan.rooms}
    extra=[_room(room,plan,limits,climate_only=True)
           for room in plan.climate_rooms if room.area_id not in already]
    summary = {
        "total": len(room_data),
        "safe": sum(room["status"] == "safe" for room in room_data),
        "attention": sum(room["status"] == "attention" for room in room_data),
        "unknown": sum(room["status"] == "unknown" for room in room_data),
    }
    missing_conditions = bool(plan.unavailable_outdoor) or any(
        reason.code in _MISSING_OUTSIDE for reason in plan.outside_reasons
    )
    known_hazards = any(
        reason.code not in _MISSING_OUTSIDE for reason in plan.outside_reasons
    )
    outside_status = (
        "unsafe" if known_hazards else
        "unknown" if not plan.outdoor_safe else
        "partial" if missing_conditions else "safe"
    )

    return {
        "version": 1,
        "summary": summary,
        "rooms": room_data+extra,
        "climate_only_count":len(extra),
        "outdoor": {
            "status": outside_status,
            "conditional_open": any(rec.action == "open" and rec.cautions
                                    for rec in (*plan.recommendations,*plan.climate_recommendations)),
            "pollen": plan.environment.get("__outside__", {}).get("pollen", {"status":"not_configured"}),
            "safe_to_ventilate": plan.outdoor_safe,
            "data_complete": not missing_conditions,
            "readings": [
                _reading(item, limits.get(f"outdoor_{item.metric}"), indoor=False)
                for item in plan.outdoor_readings
            ],
            "weather": [_weather(item) for item in plan.weather],
            "warnings": [_warning(item) for item in plan.warnings if item.active is not None],
            "ignored_warning_entities": [item.entity_id for item in plan.warnings
                                         if item.active is None],
            "blockers": [_reason(reason) for reason in plan.outside_reasons],
            "unavailable_sensors": list(plan.unavailable_outdoor),
        },
    }

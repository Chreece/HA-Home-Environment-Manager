"""Compact, presentation-neutral snapshot for the Lovelace dashboard card.

The backend owns the safety decision and measurement normalisation; the card
only presents the result in the Home Assistant user's interface language.
"""

from __future__ import annotations

from typing import Any

from .const import UNIT_LABEL
from .logic import Plan, Reading, Reason, Room, Weather, Warning
from .room_data import classify as classify_room_data

_MISSING_OUTSIDE = frozenset({
    "no_outdoor_data", "no_weather_data", "unavailable_weather", "unavailable_warning",
    "aqi_scale_unconfigured"
})


def _reason(reason: Reason) -> dict[str, str]:
    return {"code": reason.code, "label": reason.label, "value": reason.value}


def _reading(reading: Reading, threshold: float | None, *, indoor: bool) -> dict[str, Any]:
    from math import isfinite
    value_available = (isinstance(reading.value, (int, float))
                       and not isinstance(reading.value, bool)
                       and isfinite(reading.value))
    value = reading.value if value_available else None
    aqi = (reading.details or {}).get("aqi", {}) if reading.metric == "aqi" else {}
    # A fresh numeric index and a verified scale are different evidence.
    # Retain the value for a neutral display while keeping existing evaluated
    # availability false until that index can actually be interpreted.
    trusted_aqi = indoor or reading.metric != "aqi" or aqi.get("status") == "ready"
    evaluation_status = ("unavailable" if not value_available else
                         "ready" if trusted_aqi else
                         "invalid" if aqi.get("status") in ("invalid", "unavailable")
                         else "configuration_required")
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
        "available": value_available and trusted_aqi,
        "value_available": value_available,
        "evaluation_status": evaluation_status,
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
          climate_only: bool = False, control_inputs: list[dict] | None = None) -> dict[str, Any]:
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
    opened = [item for item in room.windows if item.opened is True]
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
    availability = classify_room_data(
        room, plan.environment.get(room.area_id, {}), control_inputs)
    if high or evidence_high or (recommended and recommended.action == "close"):
        status = "attention"
    elif availability["status"] == "missing":
        status = "unknown"
    else:
        status = "safe"

    missing_mold = next(
        (item for item in readings if item["metric"] == "mold" and not item["available"]),
        None,
    )
    mold_details = (missing_mold or {}).get("details", {}) or {}
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
    status_detail = ("required_control_data_missing" if availability["missing_required_metrics"]
                     else "no_indoor_data" if availability["status"] == "missing"
                     else "partial_indoor_data" if availability["status"] == "partial"
                     else None)

    return {
        "area_id": room.area_id,
        "name": room.name,
        "climate_only": climate_only,
        "status": status,
        "status_detail": status_detail,
        "data_availability": availability,
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


def dashboard_snapshot(plan: Plan, limits: dict[str, float], *,
                       control_inputs: dict[str, list[dict]] | None = None) -> dict[str, Any]:
    """Describe *all* monitored rooms, not only actionable recommendations.

    Missing required feedback or all basic room data is explicitly unknown.
    Optional sensor/window diagnostics do not imply the room has no data.
    Incomplete outside air readings are not a known hazard and must not trigger
    closing a window, but the UI must not imply complete verification either.
    """
    inputs = control_inputs or {}
    room_data = [_room(room, plan, limits, control_inputs=inputs.get(room.area_id))
                 for room in plan.rooms]
    # Count exactly the rendered rooms. Climate-only membership does not mean
    # missing measurements and still creates no window or air-quality advice.
    already={room.area_id for room in plan.rooms}
    extra=[_room(room,plan,limits,climate_only=True,control_inputs=inputs.get(room.area_id))
           for room in plan.climate_rooms if room.area_id not in already]
    all_rooms = room_data + extra
    summary = {
        "total": len(all_rooms),
        "safe": sum(room["status"] == "safe" for room in all_rooms),
        "attention": sum(room["status"] == "attention" for room in all_rooms),
        "unknown": sum(room["status"] == "unknown" for room in all_rooms),
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
    outdoor_readings = [
        _reading(item, limits.get(f"outdoor_{item.metric}"), indoor=False)
        for item in plan.outdoor_readings
    ]
    unevaluated_aqi = [item["entity_id"] for item in outdoor_readings
                      if item["metric"] == "aqi" and item["value_available"]
                      and not item["available"]]

    return {
        "version": 1,
        "summary": summary,
        "rooms": all_rooms,
        "climate_only_count":len(extra),
        "outdoor": {
            "status": outside_status,
            "conditional_open": any(rec.action == "open" and rec.cautions
                                    for rec in (*plan.recommendations,*plan.climate_recommendations)),
            "pollen": plan.environment.get("__outside__", {}).get("pollen", {"status":"not_configured"}),
            "safe_to_ventilate": plan.outdoor_safe,
            "data_complete": not missing_conditions,
            "readings": outdoor_readings,
            "weather": [_weather(item) for item in plan.weather],
            "warnings": [_warning(item) for item in plan.warnings if item.active is not None],
            "ignored_warning_entities": [item.entity_id for item in plan.warnings
                                         if item.active is None],
            "blockers": [_reason(reason) for reason in plan.outside_reasons],
            # The plan retains every incomplete comparison for control/data
            # health policy. The UI distinguishes missing observations from
            # numeric AQI sources that need scale configuration or correction.
            "unavailable_sensors": [entity for entity in plan.unavailable_outdoor
                                    if entity not in unevaluated_aqi],
            "unevaluated_aqi_sensors": unevaluated_aqi,
        },
    }


def manager_dashboard_snapshot(manager: Any, *, area_id: str | None = None) -> dict[str, Any]:
    """Use the same read-only live input projection for WS and room entities."""
    from .room_data import controller_inputs
    return dashboard_snapshot(manager.plan, manager.thresholds,
                              control_inputs=controller_inputs(manager, area_id=area_id))

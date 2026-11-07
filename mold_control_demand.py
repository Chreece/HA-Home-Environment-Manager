"""Current calibrated surface-humidity evidence for existing device control.

This module derives a humidity goal only; it does not activate a controller,
relax its permissions or send an announcement.  Every use rereads selected
physical inputs and the exact current calibration, rather than treating a
dashboard snapshot or a mold percentage as an actuator measurement.
"""
from __future__ import annotations

from typing import Any

from .const import (
    CONF_AREAS, CONF_EXCLUDED_INDOOR, CONF_MOLD_ROOMS, CONF_OUTDOOR,
    CONF_THRESHOLDS, CONF_USE_MOLD, CONF_WEATHER, DEFAULT_THRESHOLDS,
)
from .mold import estimate_mold, indoor_humidity_for_surface_limit
from .pid_math import finite


def _same_source_set(current: tuple[str, ...] | list[str], saved: list) -> bool:
    """A selected mean depends on source identities, never picker ordering."""
    return (all(isinstance(entity, str) for entity in saved)
            and set(current) == set(saved))


def room_mold_demand(manager: Any, area: str) -> dict:
    """Return qualified current evidence, or a non-demand diagnostic status."""
    config = manager.settings
    result = {"mold_protection_required": False, "status": "disabled"}
    if config.get(CONF_USE_MOLD) is not True or area not in config.get(CONF_AREAS, ()):
        return result
    calibrations = config.get(CONF_MOLD_ROOMS, {})
    calibration = calibrations.get(area, {}) if isinstance(calibrations, dict) else {}
    if not isinstance(calibration, dict):
        return {**result, "status": "needs_calibration"}
    factor = calibration.get("calibration_factor")
    if (isinstance(factor, bool) or finite(factor, -20, 20) is None
            or abs(float(factor)) < 0.5):
        return {**result, "status": "needs_calibration"}

    from .room_sources import selected, room_temperature_evidence, numeric, native
    from .discovery import entity_area, reading, weather

    temperature_ids = selected(config, area, "temperature")
    saved_temperature_ids = calibration.get("indoor_temperature_entities")
    configured_weather = config.get(CONF_WEATHER, [])
    configured_weather = list(dict.fromkeys(
        value for value in configured_weather if isinstance(value, str)
    )) if isinstance(configured_weather, list) else []
    saved_weather_ids = calibration.get("outdoor_weather_entities")
    weather_pin = calibration.get("outdoor_weather_entity")
    if ((isinstance(saved_temperature_ids, list) and temperature_ids is not None
         and not _same_source_set(temperature_ids, saved_temperature_ids))
            or (isinstance(saved_weather_ids, list)
                and not _same_source_set(configured_weather, saved_weather_ids))):
        return {**result, "status": "calibration_sources_changed"}
    weather_ids = (list(dict.fromkeys(saved_weather_ids))
                   if isinstance(saved_weather_ids, list) and saved_weather_ids
                   else [weather_pin] if isinstance(weather_pin, str) and weather_pin else [])
    if not weather_ids or not set(weather_ids) <= set(configured_weather):
        return {**result, "status": "calibration_weather_not_selected"}

    overrides = config.get(CONF_THRESHOLDS, {})
    thresholds = {**DEFAULT_THRESHOLDS, **(overrides if isinstance(overrides, dict) else {})}
    limit = finite(thresholds.get("indoor_mold"), 0.000001, 100)
    weather_age = finite(thresholds.get("max_age_minutes"), 0.000001, 100000)
    if limit is None or weather_age is None:
        return {**result, "status": "invalid_mold_threshold"}
    # The room feedback follows the native controller's ten-minute validity
    # requirement. Weather keeps its explicitly configured publication age;
    # slow weather updates must not be relabeled as current room feedback.
    feedback_age = min(10.0, weather_age)
    pin = calibration.get("indoor_temperature_entity")
    indoor, temperature_evidence = room_temperature_evidence(
        manager.hass, config, area,
        pinned=pin if isinstance(pin, str) else None,
        age_minutes=feedback_age,
    )
    outside_readings = [weather(manager.hass, entity, weather_age) for entity in weather_ids]
    outdoor_values = [value for item in outside_readings
                      if (value := finite(item.temperature_c, -60, 85)) is not None]
    outdoor = sum(outdoor_values) / len(outdoor_values) if outdoor_values else None

    excluded_rooms = config.get(CONF_EXCLUDED_INDOOR, {})
    excluded = set(excluded_rooms.get(area, ())) if isinstance(excluded_rooms, dict) else set()
    excluded.update(config.get(CONF_OUTDOOR, ()))
    humidity_ids = selected(config, area, "humidity")
    values = []
    if humidity_ids is not None:
        for entity in humidity_ids:
            if entity not in excluded:
                value = numeric(manager.hass, entity, area, "humidity", feedback_age)
                if finite(value, 0.000001, 100) is not None:
                    values.append((entity, float(value)))
    else:
        # Preserve the room's legacy included physical RH mean; do not borrow
        # the native appliance's own humidity or an unrelated room's sensor.
        for state in manager.hass.states.async_all("sensor"):
            entity = state.entity_id
            if entity in excluded or entity_area(manager.hass, entity) != area or not native(manager.hass, entity):
                continue
            observed = reading(manager.hass, entity, feedback_age, outdoor=False)
            if observed.metric == "humidity" and finite(observed.value, 0.000001, 100) is not None:
                values.append((entity, float(observed.value)))
    humidity = sum(value for _, value in values) / len(values) if values else None
    missing = [key for key, value in (("indoor_temperature", indoor), ("outdoor_temperature", outdoor),
                                      ("humidity", humidity)) if value is None]
    provenance = {
        "mold_surface_limit": limit,
        "temperature_entities": temperature_evidence.get("entity_ids", []),
        "humidity_entities": [entity for entity, _ in values],
        "weather_entities": list(weather_ids),
        "feedback_max_age_minutes": feedback_age,
        "weather_max_age_minutes": weather_age,
    }
    if missing:
        return {**result, **provenance, "status": "inputs_unavailable", "missing_inputs": missing}
    estimate = estimate_mold(indoor, outdoor, humidity, factor)
    goal = indoor_humidity_for_surface_limit(indoor, outdoor, factor, limit)
    if estimate is None or goal is None:
        return {**result, **provenance, "status": "calculation_unavailable"}
    needed = humidity > goal
    return {
        **provenance, "status": "mold_reduction_needed" if needed else "within_mold_limit",
        "mold_protection_required": needed,
        "reason": "mold_above_limit" if needed else None,
        "mold_surface_rh": estimate.surface_humidity,
        "mold_required_humidity_target": goal,
        "mold_estimated_surface_c": estimate.estimated_surface_c,
        "indoor_temperature_c": indoor, "outdoor_temperature_c": outdoor,
        "indoor_humidity": humidity, "calibration_factor": float(factor),
        "target_provenance": "calibrated_surface_rh_limit",
    }

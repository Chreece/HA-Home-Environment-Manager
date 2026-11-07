"""Pure calibrated mold-indication calculations; no Home Assistant dependencies.

The predicted relative humidity at a room's coldest surface follows
Home Assistant's Mold Indicator (Magnus approximation). Calibration requires
simultaneous room, outdoor and cold-surface measurements.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .logic import Reading, Room, Weather

MAGNUS_A = 17.62
MAGNUS_B = 243.12

# A practical cold-surface-finding target, not a mold-risk threshold or an
# additional calibration-factor validity rule. Home Assistant requires a
# significant simultaneous indoor/outdoor difference; FLIR and RICS recommend
# at least 10°C for building thermography. A snapshot cannot establish the
# stable heating/weather conditions those inspections also require.
# https://www.home-assistant.io/integrations/mold_indicator/#calibration
# https://www.flir.com/globalassets/imported-assets/document/flir-ex-series-user-manual.pdf
# https://ww3.rics.org/uk/en/journals/built-environment-journal/conducting-a-successful-thermographic-survey.html
CALIBRATION_RECOMMENDED_DIFFERENCE_C = 10.0


def _temperature(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) and -60 <= number <= 85 else None
    except (TypeError, ValueError, OverflowError):
        return None


def calibration_factor(indoor_c: float, outdoor_c: float, surface_c: float) -> float | None:
    """Calculate HA-compatible factor from three simultaneous temperatures.

    The 3°C minimum is a numerical validity guard, not an assurance that
    conditions are suitable for finding the coldest surface. A very small
    surface/outdoor denominator, or extreme factor, is not usable.
    Negative factors are valid for unusual thermal conditions (as in HA).
    """
    inside, outside, surface = (_temperature(v) for v in (indoor_c, outdoor_c, surface_c))
    if any(value is None for value in (inside, outside, surface)):
        return None
    if abs(inside - outside) < 3 or abs(surface - outside) < 0.5:
        return None
    factor = (inside - outside) / (surface - outside)
    return factor if math.isfinite(factor) and 0.5 <= abs(factor) <= 20 else None


def calibration_measurement_readiness(
    indoor_c: float | None, outdoor_c: float | None,
) -> dict[str, float | str | list[str]]:
    """Describe the temperature contrast for a winter cold-surface measurement.

    Inputs must already be freshness-checked, selected room/weather evidence
    (as in manager._capture and config_flow._mold_room_notice). Missing, stale,
    wrong-room, or unselected evidence is passed as None, never guessed here.
    A suitable positive difference only helps reveal cold surfaces. It does
    not prove steady state, that the weather station represents this building,
    or that any surface has been measured, and is never a health/risk score.
    """
    inside, outside = _temperature(indoor_c), _temperature(outdoor_c)
    details: dict[str, float | str | list[str]] = {
        "calibration_recommended_difference_c": CALIBRATION_RECOMMENDED_DIFFERENCE_C,
        "calibration_stability": "not_verified",
    }
    missing: list[str] = []
    if inside is None:
        missing.append("indoor_temperature")
    else:
        details["indoor_temperature_c"] = inside
    if outside is None:
        missing.append("outdoor_temperature")
    else:
        details["outdoor_temperature_c"] = outside
    if missing:
        details["calibration_readiness"] = "temperatures_unavailable"
        details["calibration_missing_temperature_inputs"] = missing
        return details

    # Keep the sign: a hot summer day must never be presented as a good
    # opportunity to identify the coldest winter surface. Compare at full
    # precision, keeping display rounding out of the readiness decision.
    difference = inside - outside
    details["calibration_temperature_difference_c"] = difference
    details["calibration_readiness"] = (
        "outdoors_not_colder" if difference <= 0 else
        "difference_too_small" if difference < CALIBRATION_RECOMMENDED_DIFFERENCE_C else
        "difference_suitable"
    )
    return details


def mean_valid_humidity(readings: tuple[Reading, ...]) -> tuple[float | None, int]:
    """Ignore zero, negative, out-of-range, NaN, unknown and missing RH."""
    valid = [
        item.value for item in readings
        if item.metric == "humidity" and item.value is not None
        and isinstance(item.value, (int, float))
        and math.isfinite(item.value) and 0 < item.value <= 100
    ]
    return (sum(valid) / len(valid), len(valid)) if valid else (None, 0)


@dataclass(frozen=True)
class MoldEstimate:
    surface_humidity: float
    indoor_humidity: float
    dewpoint_c: float
    estimated_surface_c: float


def indoor_humidity_for_surface_limit(
    indoor_c: float | None, outdoor_c: float | None,
    factor: float | None, surface_limit: float | None,
) -> float | None:
    """Invert the existing calibrated Magnus surface-RH relationship.

    This is the room RH at which the estimated cold surface reaches the
    configured surface RH limit.  It is not a guessed comfort target, an
    independent building model or a probability of mold growth.  Keep full
    precision: the display estimate is rounded and capped at 100%, so scaling
    a displayed mold percentage would be wrong at condensation and rounding
    boundaries.
    """
    inside, outside = _temperature(indoor_c), _temperature(outdoor_c)
    if isinstance(factor, bool) or isinstance(surface_limit, bool):
        return None
    try:
        f, limit = float(factor), float(surface_limit)
    except (TypeError, ValueError, OverflowError):
        return None
    if (inside is None or outside is None or not math.isfinite(f)
            or not 0.5 <= abs(f) <= 20 or not math.isfinite(limit)
            or not 0 < limit <= 100):
        return None
    surface = outside + (inside - outside) / f
    try:
        humidity = limit * math.exp(
            MAGNUS_A * surface / (MAGNUS_B + surface)
            - MAGNUS_A * inside / (MAGNUS_B + inside)
        )
    except (ValueError, OverflowError, ZeroDivisionError):
        return None
    return min(100.0, humidity) if math.isfinite(humidity) and humidity > 0 else None


def estimate_mold(
    indoor_c: float | None, outdoor_c: float | None,
    humidity: float | None, factor: float | None,
) -> MoldEstimate | None:
    """Estimate surface RH, clamped to 0-100% (not percent probability)."""
    inside, outside = _temperature(indoor_c), _temperature(outdoor_c)
    try:
        rh, f = float(humidity), float(factor)
    except (TypeError, ValueError, OverflowError):
        return None
    if (inside is None or outside is None or not math.isfinite(rh)
            or not 0 < rh <= 100 or not math.isfinite(f)
            or not 0.5 <= abs(f) <= 20):
        return None

    gamma = math.log(rh / 100.0) + MAGNUS_A * inside / (MAGNUS_B + inside)
    dewpoint = MAGNUS_B * gamma / (MAGNUS_A - gamma)
    surface = outside + (inside - outside) / f
    try:
        saturation_ratio = math.exp(
            MAGNUS_A * dewpoint / (MAGNUS_B + dewpoint)
            - MAGNUS_A * surface / (MAGNUS_B + surface)
        )
    except (ValueError, OverflowError, ZeroDivisionError):
        return None
    if not math.isfinite(saturation_ratio):
        return None
    return MoldEstimate(
        surface_humidity=round(min(100.0, max(0.0, 100.0 * saturation_ratio)), 1),
        indoor_humidity=round(rh, 1),
        dewpoint_c=round(dewpoint, 2),
        estimated_surface_c=round(surface, 2),
    )


def estimate_mold_for_room(
    room: Room, indoor_c: float | None,
    weather: tuple[Weather, ...], calibration: dict[str, Any],
) -> Reading:
    """Add one derived mold reading per room, never treating missing data as safe."""
    label = "Mold indication"
    entity = f"derived.mold_{room.area_id}"
    factor = calibration.get("calibration_factor")
    outdoor_id = calibration.get("outdoor_weather_entity")
    outdoor_ids = calibration.get("outdoor_weather_entities")
    if isinstance(outdoor_ids, list) and outdoor_ids:
        # Calibration used the selected weather sources as one numeric input.
        # Temporarily unavailable providers do not poison a valid mean.
        values = [
            _temperature(item.temperature_c) for item in weather
            if item.entity_id in outdoor_ids
        ]
        valid = [value for value in values if value is not None]
        outdoor_c = sum(valid) / len(valid) if valid else None
    elif outdoor_id:
        # Backward compatibility: the old single-provider calibration stays
        # pinned; never substitute an unrelated weather source.
        outdoor_c = next(
            (_temperature(item.temperature_c) for item in weather
             if item.entity_id == outdoor_id), None,
        )
    else:
        # No completed calibration yet: show which inputs are available.
        valid = [_temperature(item.temperature_c) for item in weather]
        present = [value for value in valid if value is not None]
        outdoor_c = sum(present) / len(present) if present else None
    avg, count = mean_valid_humidity(room.readings)
    result = estimate_mold(indoor_c, outdoor_c, avg, factor)

    # Distinguish a calibration that has not been supplied from a calibrated
    # room whose live sensors are temporarily unavailable. The presentation
    # must never mistake either case for "no indoor measurements".
    try:
        factor_number = float(factor)
    except (ValueError, TypeError, OverflowError):
        factor_number = float("nan")
    calibrated = (
        (isinstance(outdoor_id, str) and bool(outdoor_id)
         or isinstance(outdoor_ids, list) and bool(outdoor_ids))
        and math.isfinite(factor_number) and 0.5 <= abs(factor_number) <= 20
    )
    data_status = (
        "needs_calibration" if not calibrated else
        "inputs_unavailable" if result is None else "ready"
    )

    # Report *every* unavailable input, not only the first one encountered.
    # These are presentation/diagnostic warnings, never TTS events or
    # additional conditions for triggering open/close window announcements.
    missing_inputs: list[str] = []
    if not calibrated:
        missing_inputs.append("calibration")
    if _temperature(indoor_c) is None:
        missing_inputs.append("indoor_temperature")
    if _temperature(outdoor_c) is None:
        missing_inputs.append("outdoor_temperature")
    if avg is None:
        missing_inputs.append("humidity")
    if result is None and not missing_inputs:
        missing_inputs.append("calculation")

    details: dict[str, float | int | str | list[str]] = {
        "humidity_sensor_count": count,
        "status": data_status,
        "missing_inputs": missing_inputs,
    }
    if not calibrated:
        # Live guidance is separate from the unavailable mold estimate: even
        # suitable temperature contrast never manufactures a mold reading or
        # asserts that stable measurement conditions have been verified.
        details.update(calibration_measurement_readiness(indoor_c, outdoor_c))
    if calibrated:
        # Preserve the exact saved floating-point factor; rounding is a
        # presentation concern only and must not alter mold calculations.
        details["calibration_factor"] = factor_number
    if isinstance(outdoor_id, str):
        details["outdoor_weather_entity"] = outdoor_id
    if isinstance(outdoor_ids, list):
        details["outdoor_weather_entities"] = list(outdoor_ids)
    indoor_sensor = calibration.get("indoor_temperature_entity")
    if isinstance(indoor_sensor, str):
        details["indoor_temperature_entity"] = indoor_sensor
    indoor_sensors = calibration.get("indoor_temperature_entities")
    if isinstance(indoor_sensors, list):
        details["indoor_temperature_entities"] = list(indoor_sensors)
    if avg is not None:
        details["average_indoor_humidity"] = round(avg, 1)
    if result:
        details.update({
            "dewpoint_c": result.dewpoint_c,
            "estimated_surface_c": result.estimated_surface_c,
            "indoor_temperature_c": round(float(indoor_c), 2),
            "outdoor_temperature_c": round(float(outdoor_c), 2),
        })
    return Reading(entity, label, "mold", result.surface_humidity if result else None, details)


def rh_fallback_for_room(room: Room, mold_reading: Reading) -> Reading | None:
    """Use averaged *valid included* room RH only while mold is unavailable.

    Fallback is the same 65% legacy indoor humidity metric, never a mold
    percentage and never a separate sensor or calibration factor. Once a
    valid mold estimate exists, it takes priority over any room RH.
    """
    if mold_reading.value is not None:
        return None
    mean, count = mean_valid_humidity(room.readings)
    if mean is None:
        return None
    return Reading(
        f"derived.rh_fallback_{room.area_id}",
        "Average room relative humidity (fallback)",
        "humidity",
        mean,  # Compare with threshold at full precision; formatting is UI-only.
        {
            "fallback_for_mold": True,
            "humidity_sensor_count": count,
        },
    )

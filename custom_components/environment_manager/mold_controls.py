"""Per-area mold calibration driven by explicit device inputs.

Room source selections own indoor temperature input. A room Number
holds the measured coldest-surface temperature, and this opt-in calibration
button computes the Magnus factor only after fresh simultaneous evidence.
Never infer a surface temperature from an unrelated room sensor.
"""
from __future__ import annotations

import asyncio
from .config_data import mutable_copy as deepcopy
from datetime import datetime, timezone
import math
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_AREAS, CONF_MOLD_ROOMS, CONF_USE_MOLD, CONF_WEATHER,
    DEFAULT_THRESHOLDS,
)
from .discovery import weather
from .room_sources import room_temperature_evidence, selected
from .mold import calibration_factor


def _calibration(manager: Any, area_id: str) -> dict:
    settings = manager.settings
    if settings.get(CONF_USE_MOLD) is not True or area_id not in settings.get(CONF_AREAS, ()):
        raise HomeAssistantError("Mold indicator is not selected for this room")
    saved = settings.get(CONF_MOLD_ROOMS, {})
    info = saved.get(area_id, {}) if isinstance(saved, dict) else {}
    if not isinstance(info, dict):
        raise HomeAssistantError("Invalid mold configuration")
    return info


def configured_mold(manager: Any, area_id: str) -> dict:
    """Safe read-only attributes for the room's calibration editor."""
    return dict(_calibration(manager, area_id))


def _options_with_room(manager: Any, area_id: str, calibration: dict) -> dict:
    # Only the new options copy is changed, preserving all unrelated rooms,
    # including calibrations originally stored in config-entry data.
    current = manager.settings.get(CONF_MOLD_ROOMS, {})
    rooms = deepcopy(current) if isinstance(current, dict) else {}
    rooms[area_id] = calibration
    options = deepcopy(manager.entry.options)
    options[CONF_MOLD_ROOMS] = rooms
    return options


def _editor_lock(manager: Any) -> asyncio.Lock:
    lock = getattr(manager, "_device_settings_write_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        manager._device_settings_write_lock = lock
    return lock


def _commit(manager: Any, options: dict) -> None:
    manager.hass.config_entries.async_update_entry(manager.entry, options=options)
    if getattr(manager, "_active", False):
        manager._recalculate(initial=True)


async def async_set_surface_temperature(manager: Any, area_id: str, value: float) -> None:
    """Save a measured surface temperature; invalidate any factor from prior input."""
    if isinstance(value, bool):
        raise HomeAssistantError("A measured surface temperature is required")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise HomeAssistantError("Invalid cold-surface temperature") from error
    if not math.isfinite(number) or not -60 <= number <= 85:
        raise HomeAssistantError("Cold-surface temperature must be between -60 and 85°C")
    async with _editor_lock(manager):
        cfg = _calibration(manager, area_id)
        if cfg.get("critical_temperature_c") == number:
            return
        next_cfg = dict(cfg)
        next_cfg["critical_temperature_c"] = number
        for field in ("calibration_factor", "calibrated_indoor_c",
                      "calibrated_outdoor_c", "calibrated_at"):
            next_cfg.pop(field, None)
        _commit(manager, _options_with_room(manager, area_id, next_cfg))


async def async_recalculate_mold_factor(manager: Any, area_id: str) -> float:
    """Calibrate with the available selected sensor means; retain old factor on failure."""
    async with _editor_lock(manager):
        cfg = _calibration(manager, area_id)
        configured = selected(manager.settings, area_id, "temperature")
        pinned = cfg.get("indoor_temperature_entity") if configured is None else None
        age = float(manager.thresholds.get(
            "max_age_minutes", DEFAULT_THRESHOLDS["max_age_minutes"]))
        indoor_c, evidence = room_temperature_evidence(
            manager.hass, manager.settings, area_id,
            pinned=pinned if isinstance(pinned, str) else None,
            age_minutes=age,
        )
        if configured is None and not isinstance(pinned, str):
            raise HomeAssistantError("Select a valid indoor temperature source for this area")
        if indoor_c is None:
            if evidence.get("status") == "pinned_sensor_not_selected":
                raise HomeAssistantError("Mold temperature source is not selected for this room")
            if evidence.get("status") == "selected_temperature_invalid" and pinned:
                raise HomeAssistantError("Select a valid indoor temperature source for this area")
            raise HomeAssistantError("Indoor temperature is unavailable or stale")

        indoor_sources = list(configured) if configured is not None else [pinned]
        # An existing legacy single-sensor pin never overrides two or more
        # explicitly selected sensors for this room.
        indoor_source = indoor_sources[0] if len(indoor_sources) == 1 else None
        surface = cfg.get("critical_temperature_c")
        if isinstance(surface, bool):
            raise HomeAssistantError("Measure the coldest surface and enter its temperature")
        try:
            surface_c = float(surface)
        except (ValueError, TypeError, OverflowError) as error:
            raise HomeAssistantError("Measured cold-surface temperature is missing") from error
        if not math.isfinite(surface_c) or not -60 <= surface_c <= 85:
            raise HomeAssistantError("Measured cold-surface temperature is invalid")

        choices = manager.settings.get(CONF_WEATHER, [])
        if not isinstance(choices, list) or not choices:
            raise HomeAssistantError("Configure outdoor weather sources first")
        pinned_weather = cfg.get("outdoor_weather_entity")
        # Preserve the legacy pin only with one selected provider. With
        # multiple providers, average all available compatible temperatures.
        if pinned_weather and len(choices) == 1 and pinned_weather not in choices:
            raise HomeAssistantError("Selected outdoor weather source is no longer configured")
        available = []
        for entity in dict.fromkeys(choices):
            data = weather(manager.hass, entity, age)
            if (data.temperature_c is not None
                    and math.isfinite(data.temperature_c)
                    and -60 <= data.temperature_c <= 85):
                available.append(data)
        if not available:
            raise HomeAssistantError("Outdoor temperature is unavailable or stale")
        outdoor_c = sum(data.temperature_c for data in available) / len(available)

        factor = calibration_factor(indoor_c, outdoor_c, surface_c)
        if factor is None:
            raise HomeAssistantError(
                "Cannot calibrate: require at least 3°C indoors/outdoors difference, "
                "a valid surface offset and a factor within physical limits"
            )
        weather_sources = list(dict.fromkeys(choices))
        new = {
            **cfg,
            "calibration_factor": factor,
            "indoor_temperature_entity": indoor_source,
            "indoor_temperature_entities": indoor_sources,
            "outdoor_weather_entity": weather_sources[0] if len(weather_sources) == 1 else None,
            "outdoor_weather_entities": weather_sources,
            "critical_temperature_c": surface_c,
            "calibrated_indoor_c": indoor_c,
            "calibrated_outdoor_c": outdoor_c,
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
        }
        _commit(manager, _options_with_room(manager, area_id, new))
        return factor

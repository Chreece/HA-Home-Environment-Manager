"""Exact-area door metadata writes; never door, lock or appliance commands."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import math

from .config_data import mutable_copy as deepcopy
from .room_doors import contact_options


def inventory(hass, settings):
    from .device_hierarchy import configured_area_ids
    from homeassistant.helpers import area_registry as ar
    registry = ar.async_get(hass)
    rooms = settings.get("climate_rooms", {})
    rooms = rooms if isinstance(rooms, Mapping) else {}
    for area in sorted(configured_area_ids(settings)):
        if registry.async_get_area(area) is None:
            continue
        cfg = rooms.get(area, {})
        selected = cfg.get("door_sensors", []) if isinstance(cfg, Mapping) else []
        if isinstance(selected, list):
            for entity in dict.fromkeys(e for e in selected if isinstance(e, str)):
                yield area, entity


def editable_contact(hass, settings, area, entity):
    from .discovery import entity_area, _device_class
    from .room_sources import native
    if (area, entity) not in inventory(hass, settings):
        return False
    if not entity.startswith("binary_sensor.") or entity_area(hass, entity) != area or not native(hass, entity):
        return False
    state = hass.states.get(entity)
    return (state is None or state.state in ("unknown", "unavailable")
            or str(_device_class(hass, state) or "").casefold() == "door")


def target_areas(hass, settings, area):
    from .device_hierarchy import configured_area_ids
    from homeassistant.helpers import area_registry as ar
    registry = ar.async_get(hass)
    return {other: item.name for other in sorted(configured_area_ids(settings))
            if other != area and (item := registry.async_get_area(other)) is not None}


async def async_update(manager, area, entity, key, value):
    """Serialize with all existing HEM edits and recheck current source identity."""
    from homeassistant.exceptions import HomeAssistantError
    lock = getattr(manager, "_device_settings_write_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        manager._device_settings_write_lock = lock
    async with lock:
        current = manager.settings
        if not editable_contact(manager.hass, current, area, entity):
            raise HomeAssistantError("Door contact is no longer selected in this exact Area")
        rooms = deepcopy(current.get("climate_rooms", {}))
        room = rooms[area]
        profiles = deepcopy(room.get("door_settings", {}))
        profiles = profiles if isinstance(profiles, dict) else {}
        original = profiles.get(entity, {})
        item = dict(original) if isinstance(original, Mapping) else {}
        if key == "target_area":
            if value is not None and (not isinstance(value, str)
                                      or value not in target_areas(manager.hass, current, area)):
                raise HomeAssistantError("Choose a different configured Area, or clear the connection")
            if value is not None and item.get("kind") == "exterior":
                raise HomeAssistantError("An exterior door cannot define an interior room connection")
        elif key == "kind":
            if value not in ("interior", "fire", "exterior"):
                raise HomeAssistantError("Unknown door purpose")
            if value != "interior":
                item["coordination"] = "observe"
            if value == "exterior":
                item["target_area"] = None
        elif key == "coordination":
            if value not in ("observe", "conflicts", "shared"):
                raise HomeAssistantError("Unsupported door coordination policy")
            if value != "observe" and item.get("kind", "interior") != "interior":
                raise HomeAssistantError("Only interior doors can coordinate device starts")
        elif key == "energy_meter":
            from .door_energy import choices
            if value is not None and (not isinstance(value, str)
                    or value not in choices(manager.hass, area, item.get("energy_meter"))):
                raise HomeAssistantError("Choose a native cumulative energy meter in this exact Area")
        elif key == "report_timeout_minutes":
            if isinstance(value, bool):
                raise HomeAssistantError("Report timeout must be minutes, not a Boolean")
            try:
                value = float(value)
            except (ValueError, TypeError, OverflowError) as err:
                raise HomeAssistantError("Invalid report timeout") from err
            if not math.isfinite(value) or not 0 <= value <= 10080:
                raise HomeAssistantError("Report timeout must be 0–10080 minutes")
        else:
            raise HomeAssistantError("Unsupported door setting")
        item[key] = value
        if item == original:
            return
        profiles[entity] = item
        room["door_settings"] = profiles
        options = deepcopy(manager.entry.options)
        options["climate_rooms"] = rooms
        manager.hass.config_entries.async_update_entry(manager.entry, options=options)
        if getattr(manager, "_active", False):
            manager._recalculate(initial=True)

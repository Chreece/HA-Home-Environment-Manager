"""Authoritative, read-only managed controller inventory for dashboard UI.

Home Assistant removes normal entity attributes when an entity is unavailable.
The Lovelace card must therefore not infer membership from the current climate
state, the frontend entity registry (which may be unpopulated), or physical
device names. This inventory comes from HEM's persisted, registered sources.
It is only returned by the existing authenticated recommendation WS endpoint.
"""
from __future__ import annotations

from typing import Any

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from . import equipment_model as equipment
from .device_hierarchy import configured_sources


def controller_inventory(manager: Any) -> list[dict[str, Any]]:
    """Return exact registered HEM controllers, even while native Zigbee is off.

    This function has no entity creation, storage write or service call. An
    inventory entry is display evidence, NEVER physical actuation authority.
    """
    registry = er.async_get(manager.hass)
    entry_id = manager.entry.entry_id
    current = manager.settings
    allowed_by_area: dict[str, set[str]] = {}
    result = []

    for spec in equipment.specs(manager):
        area = spec.area_id
        if area not in allowed_by_area:
            allowed_by_area[area] = set(configured_sources(current, area))
        source_ids = tuple(spec.source_entities)
        if not source_ids or not set(source_ids).issubset(allowed_by_area[area]):
            continue  # Source was deselected or cannot be attributed to this room.

        unique_id = f"{spec.identifier}_climate"
        entity_id = registry.async_get_entity_id("climate", DOMAIN, unique_id)
        registered = registry.async_get(entity_id) if entity_id else None
        if not (registered is not None
                and registered.platform == DOMAIN
                and registered.config_entry_id == entry_id
                and registered.unique_id == unique_id
                and getattr(registered, "disabled_by", None) is None):
            entity_id = None  # Keep truthful read-only inventory, no fake HA ID.

        source_states = {
            source: (state.state if (state := manager.hass.states.get(source))
                     is not None else "unavailable")
            for source in source_ids
        }
        unavailable = [source for source, state in source_states.items()
                       if state in ("unavailable", "unknown")]
        settings = equipment.settings(manager, spec)
        runtime = getattr(manager, "equipment", None)
        status = getattr(runtime, "statuses", {}).get(spec.identifier, {})
        status = status if isinstance(status, dict) else {}
        active = getattr(runtime, "active_control_mode", None)
        mode = active(spec) if callable(active) else settings.get("operating_mode")
        modes = list(equipment.operating_modes(manager, spec))
        if mode not in modes:
            mode = None

        record = getattr(runtime, "records", {}).get(spec.identifier, {})
        record = record if isinstance(record, dict) else {}
        cached = record.get("capabilities")
        primary = cached.get("primary") if isinstance(cached, dict) else None
        if primary not in source_ids:
            primary = source_ids[0] if len(source_ids) == 1 else None

        result.append({
            "controller_id": spec.identifier,
            "climate_entity_id": entity_id,
            "area_id": area,
            "name": spec.name,
            "source_device_id": spec.source_device_id,
            "source_entity_ids": list(source_ids),
            "unavailable_source_entity_ids": unavailable,
            "control_mode": settings.get("control_mode", "existing"),
            "supported_operating_modes": modes,
            "selected_operating_mode": mode,
            "native_primary_entity_id": primary,
            "status_code": status.get("status"),
            "status_reason_code": status.get("reason"),
            "upstream_power_switch": settings.get("power_switch_entity"),
        })
    return result

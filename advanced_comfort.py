"""Keep specialist ISO 7730 inputs out of ordinary room controls.

This changes entity visibility only. It never supplies clothing, activity or
airflow values, changes a comfort target, or grants equipment control.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import CONF_CLIMATE_ROOMS, CONF_ENVIRONMENT_ROOMS, DOMAIN

MIGRATION_KEY = "_advanced_comfort_controls_version"
MIGRATION_VERSION = 1
NUMBER_KEYS = ("air_speed_m_s", "met", "clo")
SOURCE_KEYS = ("radiant_temperature_entity", "air_speed_entity")


def advanced_comfort_enabled(settings: Mapping, area: str | None) -> bool:
    """Preserve an explicit PMV calculation or target-source selection."""
    environment = settings.get(CONF_ENVIRONMENT_ROOMS, {})
    climate = settings.get(CONF_CLIMATE_ROOMS, {})
    room = environment.get(area, {}) if isinstance(environment, Mapping) else {}
    policy = climate.get(area, {}) if isinstance(climate, Mapping) else {}
    return bool(
        isinstance(room, Mapping) and room.get("enable_pmv") is True
        or isinstance(policy, Mapping) and policy.get("target_source") == "pmv"
    )


def _control_ids(entry_id: str, area: str, *, include_switch: bool = True):
    prefix = f"{entry_id}_area_{area}_"
    for key in NUMBER_KEYS:
        yield "number", prefix + "area_environment_" + key
    for key in SOURCE_KEYS:
        yield "select", prefix + "area_science_" + key
    if include_switch:
        yield "switch", prefix + "area_environment_enable_pmv"


def _registered_control(registry: Any, entry: Any, domain: str,
                        unique_id: str):
    entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
    entity = registry.async_get(entity_id) if entity_id else None
    if (entity is None or entity.config_entry_id != entry.entry_id
            or entity.platform != DOMAIN or entity.unique_id != unique_id):
        return None
    return entity


def async_migrate_advanced_comfort(hass: Any, entry: Any) -> None:
    """Disable old unused specialist entities once, preserving their identity.

    Registry defaults only apply to new entities. Existing installations need
    this bounded migration, before platform setup. A persisted version makes
    subsequent user enable/disable choices authoritative across all reloads.
    """
    version = entry.data.get(MIGRATION_KEY)
    if type(version) is int and version >= MIGRATION_VERSION:
        return
    from homeassistant.helpers import entity_registry as er
    from .device_hierarchy import configured_area_ids

    settings = {**entry.data, **entry.options}
    registry = er.async_get(hass)
    for area in configured_area_ids(settings):
        if advanced_comfort_enabled(settings, area):
            continue
        for domain, unique_id in _control_ids(entry.entry_id, area):
            entity = _registered_control(registry, entry, domain, unique_id)
            if entity is not None and entity.disabled_by is None:
                registry.async_update_entity(
                    entity.entity_id,
                    disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                )
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, MIGRATION_KEY: MIGRATION_VERSION},
    )


def async_enable_advanced_controls(hass: Any, entry: Any, area: str,
                                   *, include_switch: bool = True) -> None:
    """Expose optional inputs after explicit opt-in, without requiring values.

    Only integration-disabled entities are enabled. User-disabled entities
    remain disabled, and no source or assumption is automatically populated.
    Home Assistant applies registry enable changes through its usual reload.
    """
    if not advanced_comfort_enabled({**entry.data, **entry.options}, area):
        return
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for domain, unique_id in _control_ids(
        entry.entry_id, area, include_switch=include_switch,
    ):
        entity = _registered_control(registry, entry, domain, unique_id)
        if (entity is not None
                and entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION):
            registry.async_update_entity(entity.entity_id, disabled_by=None)

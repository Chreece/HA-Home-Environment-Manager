"""AQI source identity and provider scales, independent of startup state order.

Read only configured source IDs. No filesystem/network I/O, polling, registry
scan, actuator services, or writes to user configuration occur in this module.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

AQI_SCALES = ("auto", "not_configured", "us_epa", "eea_category", "custom")


def _registration(hass: Any, entity_id: str) -> Any:
    from homeassistant.helpers import entity_registry as er
    return er.async_get(hass).async_get(entity_id)


def configured_sources(hass: Any, settings: Mapping) -> tuple[str, ...]:
    """Selected sources remain configurable before their first HA state exists."""
    chosen = settings.get("outdoor_sensors", ())
    if not isinstance(chosen, (tuple, list)):
        return ()
    profile = settings.get("environment_global", {})
    saved = profile.get("aqi_scales", {}) if isinstance(profile, Mapping) else {}
    saved = saved if isinstance(saved, Mapping) else {}
    result = []
    for entity_id in chosen:
        if not isinstance(entity_id, str) or not entity_id.startswith("sensor."):
            continue
        entry = _registration(hass, entity_id)
        state = hass.states.get(entity_id)
        attributes = getattr(state, "attributes", {})
        classes = (
            attributes.get("device_class"),
            getattr(entry, "device_class", None),
            getattr(entry, "original_device_class", None),
        )
        if (any(str(value).casefold() == "aqi" for value in classes)
                or entity_id.endswith(("_aqi", "_air_quality_index"))
                or entity_id in saved):
            result.append(entity_id)
    return tuple(dict.fromkeys(result))


def saved_scale(profile: Mapping, entity_id: str) -> dict:
    scales = profile.get("aqi_scales", {}) if isinstance(profile, Mapping) else {}
    item = scales.get(entity_id, {}) if isinstance(scales, Mapping) else {}
    return dict(item) if isinstance(item, Mapping) else {"scale": item} if isinstance(item, str) else {}


def scale_selection(profile: Mapping, entity_id: str) -> str:
    value = saved_scale(profile, entity_id).get("scale", "auto")
    return value if value in AQI_SCALES else "not_configured"


def resolve_scale(hass: Any, profile: Mapping, entity_id: str) -> dict:
    """Manual override wins; only a registered WAQI provider is auto-detected.

    The source's name, geography, unit AQI and numeric value never identify a
    scale. WAQI is the HA integration documented to publish US EPA AQI.
    An explicit not_configured choice disables automatic interpretation.
    """
    chosen = scale_selection(profile, entity_id)
    if chosen != "auto":
        old = saved_scale(profile, entity_id)
        return {"scale": chosen, "custom_limit": old.get("custom_limit"),
                "scale_source": "manual"}
    entry = _registration(hass, entity_id) if hass is not None else None
    provider = getattr(entry, "platform", None)
    if provider == "waqi":
        # Only source AQ indices, not WAQI pollutant concentration entities.
        if entity_id in configured_sources(hass, {
            "outdoor_sensors": [entity_id], "environment_global": profile,
        }):
            return {"scale": "us_epa", "scale_source": "provider:waqi"}
    return {"scale": "not_configured", "scale_source": "provider_not_identified"}


def source_name(hass: Any, entity_id: str) -> str:
    entry = _registration(hass, entity_id)
    state = hass.states.get(entity_id)
    return str(getattr(state, "name", None) or getattr(entry, "name", None)
               or getattr(entry, "original_name", None) or entity_id)


def control_name(manager: Any, entity_id: str, field: str) -> str:
    from .aqi_names import AQI_NAMES
    tag = str(getattr(getattr(manager.hass, "config", None), "language", "en")).replace("_", "-").lower()
    labels = AQI_NAMES.get(tag, AQI_NAMES.get(tag.split("-")[0], AQI_NAMES["en"]))
    return f"{source_name(manager.hass, entity_id)} - {labels[field]}"


def register_late_sources(manager: Any, entry: Any, add_entities: Any,
                          initial: Any, factory: Any) -> None:
    """One scoped listener per platform; late source controls are added once.

    Startup config controls are independent of source availability. This
    listener covers previously unknown/renamed sources whose AQI metadata
    first arrives later. Relevant metadata changes refresh names/scales, not
    every numeric AQI measurement, and never produce a settings reload.
    """
    from homeassistant.core import callback
    from homeassistant.helpers.event import async_track_state_change_event
    from .room_hubs import async_add_grouped_entities

    chosen = manager.settings.get("outdoor_sensors", ())
    watched = tuple(dict.fromkeys(e for e in chosen
                    if isinstance(e, str) and e.startswith("sensor."))) if isinstance(chosen, (list, tuple)) else ()
    if not watched:
        return
    registered = {item._entity_id: item for item in initial
                  if getattr(item, "_kind", None) in ("aqi_scale", "aqi_limit")}
    signatures = {}

    def signature(entity_id):
        return (source_name(manager.hass, entity_id),
                getattr(_registration(manager.hass, entity_id), "platform", None))

    for entity_id in registered:
        signatures[entity_id] = signature(entity_id)

    @callback
    def changed(event):
        entity_id = event.data.get("entity_id")
        if entity_id not in watched:
            return
        # Do not recreate unrelated configuration controls on this event.
        if entity_id not in registered:
            if entity_id not in configured_sources(manager.hass, manager.settings):
                return
            candidate = factory(entity_id)
            registered[entity_id] = candidate
            signatures[entity_id] = signature(entity_id)
            async_add_grouped_entities(manager, add_entities, [candidate])
            return
        current = signature(entity_id)
        if signatures.get(entity_id) == current:
            return
        signatures[entity_id] = current
        candidate = registered[entity_id]
        if getattr(candidate, "hass", None) is not None:
            candidate.async_write_ha_state()

    entry.async_on_unload(async_track_state_change_event(
        manager.hass, watched, changed,
    ))

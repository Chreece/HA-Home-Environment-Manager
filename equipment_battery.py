"""Classify real HA devices reporting battery information for UI only.

A battery report may be on the selected native entity or on an accompanying
same-device sensor. Never infer that a device is battery-powered from its
room, name or manufacturer, and never modify supply ownership or actuation.

All device-registry lookups are read-only; the entity registry is scanned
exactly once for every setup, not once per controller.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


BATTERY_FIELDS = frozenset((
    "battery", "battery_level", "battery_percentage", "battery_percent",
    "battery_status", "battery_state",
))
BATTERY_SUFFIXES = (
    "_battery", "_battery_level", "_battery_percent",
    "_battery_percentage", "_battery_state", "_battery_status",
)


def _has_battery_attributes(state: Any) -> bool:
    attrs = getattr(state, "attributes", None)
    return bool(isinstance(attrs, dict) and any(
        key in attrs and attrs[key] is not None for key in BATTERY_FIELDS
    ))


def _registered_battery_entity(entry: Any, state: Any) -> bool:
    """Only evidence-bearing battery entities, not a guess from a device label."""
    entity_id = getattr(entry, "entity_id", "")
    if not isinstance(entity_id, str) or not entity_id.startswith((
        "sensor.", "binary_sensor.",
    )):
        return False
    classes = (
        getattr(entry, "device_class", None),
        getattr(entry, "original_device_class", None),
        getattr(state, "attributes", {}).get("device_class")
        if isinstance(getattr(state, "attributes", None), dict) else None,
    )
    if any(str(cls).casefold().split(".")[-1] == "battery"
           for cls in classes if cls is not None):
        return True
    return entity_id.casefold().endswith(BATTERY_SUFFIXES)


def battery_reporting_controllers(
    hass: Any, specs: Iterable[Any], registry: Any,
) -> frozenset[str]:
    """Identify each controller backed by a battery-reporting PHYSICAL device.

    A battery reading belonging to a different HA device in the same room
    cannot suppress the powered controller's selector. A selected source's
    own battery attributes also qualify for registry-less native endpoints.
    """
    specs = tuple(specs)
    device_owners: dict[str, set[str]] = {}
    matches: set[str] = set()
    for spec in specs:
        key = getattr(spec, "identifier", None)
        device = getattr(spec, "source_device_id", None)
        if not isinstance(key, str) or not key:
            continue
        if isinstance(device, str) and device:
            device_owners.setdefault(device, set()).add(key)
        for entity_id in getattr(spec, "source_entities", ()):
            if not isinstance(entity_id, str):
                continue
            state = hass.states.get(entity_id)
            if _has_battery_attributes(state):
                matches.add(key)
            # An intentionally enrolled native sensor may be unavailable;
            # its registry-backed battery device class is still evidence.
            entry = registry.async_get(entity_id)
            if entry is not None and _registered_battery_entity(entry, state):
                matches.add(key)

    if not device_owners:
        return frozenset(matches)
    for entry in registry.entities.values():
        device_id = getattr(entry, "device_id", None)
        if device_id not in device_owners:
            continue
        # The label, room or manufacturer cannot count as battery evidence.
        state = hass.states.get(getattr(entry, "entity_id", ""))
        if _registered_battery_entity(entry, state):
            matches.update(device_owners[device_id])
    return frozenset(matches)

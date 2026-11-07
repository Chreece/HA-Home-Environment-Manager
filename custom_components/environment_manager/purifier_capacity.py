"""Device-owned particle CADR for rated air purifiers.

CADR is the manufacturer's *particle* clean-air delivery rate in m³/h.
It is not ordinary fan airflow, outdoor ventilation ACH or a CO₂ removal
capacity. Never infer CADR from fan RPM, area or current PM2.5 readings.
"""
from __future__ import annotations

from typing import Any

from . import equipment_model as equipment
from .pid_math import finite


def _purifier_state(manager: Any, spec: Any, source: str) -> bool | None:
    """Read actual purifier ON/OFF, including an explicitly OFF supply."""
    cfg = equipment.settings(manager, spec)
    supply = cfg.get("power_switch_entity")
    if isinstance(supply, str):
        state = manager.hass.states.get(supply)
        if state is not None and state.state == "off":
            return False
    state = manager.hass.states.get(source)
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    if source.startswith("climate."):
        return False if state.state == "off" else True if state.state == "fan_only" else None
    return True if state.state == "on" else False if state.state == "off" else None


def rated_purifiers(manager: Any, area: str, room_environment: dict | None = None) -> list[dict]:
    """Report only chosen physical fans, once per controller/physical source.

    The room may retain a legacy purifier link. That identifies the same
    selected physical product but must not be used to invent CADR or airflow.
    """
    room_environment = room_environment if isinstance(room_environment, dict) else {}
    legacy_source = room_environment.get("purifier_entity")
    records = []
    for spec in equipment.specs(manager):
        if spec.area_id != area:
            continue
        cfg = equipment.settings(manager, spec)
        rating = finite(cfg.get("particle_cadr_m3h"), 0, 100000)
        if rating is None or rating <= 0:
            continue
        cap = equipment.capabilities(manager, spec)
        real_fan = next((e for e in spec.source_entities if e.startswith("fan.")), None)
        fan_only = cap is not None and "fan_only" in cap.modes
        if not real_fan and not fan_only:
            continue  # Never credit a heater, dehumidifier or valve as a filter.
        source = real_fan or cap.primary
        from .device_activation import effective_device
        effective = effective_device(manager, spec, cap.primary if cap else source)
        is_purifier = (
            effective.get("fan_purpose") == "filtration" or
            source == legacy_source or
            legacy_source in spec.source_entities
        )
        if not is_purifier:
            continue
        records.append({
            "controller_id": spec.identifier,
            "source_entity_id": source,
            "rated_particle_cadr_m3h": round(rating, 1),
            "operating": _purifier_state(manager, spec, source),
            "source": "managed_device_manufacturer_rating",
        })
    return records

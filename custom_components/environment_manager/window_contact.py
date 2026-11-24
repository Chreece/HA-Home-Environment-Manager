"""Live window readings for room control. Missing reports carry no veto."""
from __future__ import annotations


def opened(state):
    """Return the reported contact position, including None for a lost reading."""
    if state is None or getattr(state, "attributes", {}).get("restored") is True:
        return None
    return {"on": True, "off": False}.get(state.state)


def permits_operation(hass, area, entity, enrolled=()):
    """Recheck a configured contact immediately before a device write."""
    if not isinstance(entity, str) or not entity.startswith("binary_sensor."):
        return False
    state = hass.states.get(entity)
    reading = opened(state)
    if reading is None:
        return True
    from .discovery import entity_area, is_window_contact

    return (reading is False and entity_area(hass, entity) == area
            and is_window_contact(hass, state, explicitly_selected=entity in (enrolled or ())))

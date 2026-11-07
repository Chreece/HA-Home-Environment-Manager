"""Exact-device authorization from its own controls, not a hidden setup menu.

Choosing Automatic, PID or Manual is explicit consent for this exact native
controller to regulate setpoints/speed and to turn its supported native mode
on/off as needed. Raw relay commissioning is never inferred. Physical identity changes invalidate consent until reselected.
"""
from __future__ import annotations
from .config_data import mutable_copy


def authority_context(manager, spec):
    """Bind consent to the physical controller, independently of room readings.

    Room sensor revisions, their order, and policy preferences are rechecked
    by the live control gates. They do not replace the native device that the
    user selected, so they must not silently revoke that selection.
    """
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(manager.hass)
    return mutable_copy({
        "version": 2, "area": spec.area_id,
        "physical_device": spec.source_device_id,
        "sources": sorted([
            [entity, getattr(registry.async_get(entity), "id", None),
             getattr(registry.async_get(entity), "unique_id", None)]
            for entity in spec.source_entities
        ]),
    })


def authorization_matches(saved, current):
    """Accept an existing grant only for exactly the same physical identities.

    The original grant also captured mutable measurement/policy metadata.
    Upgrading that shape is safe only when all its endpoint identities still
    match. Missing, moved, replaced or added physical endpoints never inherit
    consent merely because a profile still says Automatic or PID.
    """
    if not isinstance(saved, dict) or not isinstance(current, dict):
        return False
    if saved.get("version", 1) not in (1, 2):
        return False
    sources = saved.get("sources")
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(source, (list, tuple)) or len(source) != 3
                   or not isinstance(source[0], str)
                   or not any(isinstance(value, str) and value for value in source[1:])
                   for source in sources)):
        return False
    return bool(
        saved.get("area") == current.get("area")
        and saved.get("physical_device") == current.get("physical_device")
        and sorted([list(source) for source in sources]) == current.get("sources")
    )


def authorized(manager, spec):
    from . import equipment_model as model
    return authorization_matches(
        model.settings(manager, spec).get("_native_authorization"),
        authority_context(manager, spec),
    )


def effective_device(manager, spec, entity, *, cap=None):
    from . import equipment_model as model
    original = model.device_config(manager, spec, entity)
    result = dict(original)
    cfg = model.settings(manager, spec)
    from .arrival_preparation import automatic_eligible
    result["_arrival_preparation_eligible"] = automatic_eligible(cfg)
    result["_arrival_preparation_entry_id"] = manager.entry.entry_id
    # Temporarily overriding occupied-only operation needs an existing owned
    # shutdown path when the timer ends. A setpoint-only controller cannot
    # leave its last Home target latched behind a restored presence hold.
    # Supply control can pass its already-validated cached native capability;
    # its independent startup/identity gates still own any power decision.
    cap = cap if cap is not None else model.capabilities(manager, spec)
    result["_arrival_preparation_presence_override"] = bool(
        automatic_eligible(cfg) and cap is not None and "off" in cap.modes
        and model.permission(manager, spec, cap)[1]
    )
    result["sleep_when_everyone_asleep"] = (cfg.get("sleep_when_everyone_asleep") is True
                                            and cfg.get("control_mode") in ("automatic", "pid"))
    if authorized(manager, spec):
        result["auto_control"] = True
    for key in ("presence_requirement", "sleep_behavior", "fan_purpose", "sensor_verified"):
        if key in cfg and cfg[key] is not None and cfg[key] != "auto":
            result[key] = cfg[key]
    if result.get("fan_purpose") not in ("extraction", "filtration"):
        # An exact room assignment is stronger evidence than sensor-based
        # inference. Rooms commonly measure both CO2 and particles; that
        # must not erase their configured purifier or extraction role.
        room = model.room_config(manager, spec)
        if room.get("extraction_fan_entity") == entity:
            result["fan_purpose"] = "extraction"
        elif room.get("purifier_fan_entity") == entity:
            result["fan_purpose"] = "filtration"
    if result.get("fan_purpose") not in ("extraction", "filtration"):
        from .room_sources import selected
        from .discovery import supported_metric
        ids = selected(manager.settings, spec.area_id, "air_quality")
        metrics = {supported_metric(manager.hass, state, outdoor=False)
                   for entity in ids or () if (state := manager.hass.states.get(entity)) is not None}
        if ("co2" in metrics) != ("pm25" in metrics):
            result["fan_purpose"] = "extraction" if "co2" in metrics else "filtration"
    return result


def planning_rooms(manager):
    """Generate room evidence without enabling any previous actuator driver."""
    from . import equipment_model as model
    rooms = mutable_copy(manager.settings.get("climate_rooms", {}))
    for spec in model.specs(manager):
        if model.settings(manager, spec)["control_mode"] in ("automatic", "pid") and authorized(manager, spec):
            room = rooms.setdefault(spec.area_id, {})
            if room.get("enabled") is not True:
                room.update(enabled=True, controller="environment", allow_actuation=False)
    return rooms

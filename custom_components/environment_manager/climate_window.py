"""Advisory substitution of verified mechanical conditioning with window airing.

A window can sometimes provide sensible cooling, limited warming or moisture
removal. This is a conditional *opportunity*, NOT a guaranteed equivalent
energy saving, room temperature forecast, or power-control command.

No external service calls. Physical benefit requires measured indoor/outdoor
conditions and a matching supported device with active or pending demand. A
real closed window must exist in the selected Home Assistant area. Outside
concerns qualify the manual request; they never authorize mechanical intake.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

from .climate_coordination import device_inventory
from .climate_equipment import classify_hvac
from .logic import Reason, _numeric_weather_mean


AIR_POLLUTANTS = frozenset(("aqi", "pm25", "pm10", "no2", "o3", "so2"))
RUNNING_ACTIONS = {"heating": "heat", "cooling": "cool", "drying": "dry"}


def _number(value: Any, low: float, high: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return x if isfinite(x) and low <= x <= high else None


def _running_effects(hass: Any, area: str, config: dict) -> list[tuple[str, str]]:
    """Require native HVAC action or known dedicated dehumidifier power."""
    from .discovery import entity_area

    inventory = device_inventory(hass, area, config)
    active: dict[str, str] = {}
    for item in inventory.values():
        if item.get("status") != "ready":
            continue
        entity = item.get("entity_id")
        if not isinstance(entity, str) or entity_area(hass, entity) != area:
            continue
        state = hass.states.get(entity)
        if state is None:
            continue
        if item.get("domain") == "climate":
            caps = item.get("capabilities", {})
            mode = state.state
            action = state.attributes.get("hvac_action")
            effect = RUNNING_ACTIONS.get(action)
            # A device exposing only one mode remains eligible. DRY selected
            # without hvac_action does NOT prove compressor operation.
            if (effect == "heat" and mode in ("heat", "auto", "heat_cool")
                    and caps.get("heating")):
                active[entity] = effect
            elif (effect == "cool" and mode in ("cool", "auto", "heat_cool")
                  and caps.get("cooling")):
                active[entity] = effect
            elif (effect == "dry" and mode == "dry" and caps.get("drying")):
                active[entity] = effect
        elif (item.get("domain") == "humidifier"
              and item.get("device_class") == "dehumidifier"
              and state.state == "on"):
            active[entity] = "dry"
    return [(entity, effect) for entity, effect in active.items()]


def _supported_effect(hass: Any, area: str, settings: dict,
                      entity: Any, effect: Any, *, fan_purpose: Any = None) -> bool:
    """Revalidate a selected pending endpoint against live local capabilities."""
    from .discovery import entity_area

    if (not isinstance(entity, str) or effect not in ("heat", "cool", "dry", "humidify", "filtration")
            or entity_area(hass, entity) != area):
        return False
    selected = settings.get("selected_devices")
    if isinstance(selected, list) and entity not in selected:
        return False
    observed = hass.states.get(entity)
    if (observed is None or observed.state in ("unknown", "unavailable")
            or observed.attributes.get("hvac_action") == "defrosting"):
        return False
    domain = entity.partition(".")[0]
    if effect == "filtration":
        profiles = settings.get("device_settings", {})
        profile = profiles.get(entity, {}) if isinstance(profiles, dict) else {}
        purpose = fan_purpose
        if purpose not in ("extraction", "filtration"):
            purpose = profile.get("fan_purpose") if isinstance(profile, dict) else None
        if purpose not in ("extraction", "filtration"):
            if settings.get("extraction_fan_entity") == entity:
                purpose = "extraction"
            elif settings.get("purifier_fan_entity") == entity:
                purpose = "filtration"
        if purpose != "filtration":
            return False
        # A declared indoor particle-filter role is required. FAN_ONLY by
        # itself does not prove that the equipment removes any pollutant.
        return bool(domain == "fan" and observed.state in ("on", "off") or
                    domain == "climate" and observed.state in ("off", "fan_only")
                    and set(observed.attributes.get("hvac_modes", ())) == {"off", "fan_only"})
    if domain == "climate":
        if effect == "humidify":
            return False
        caps = classify_hvac(observed.attributes, observed.state)
        return bool(caps.get("status") == "ready"
                    and caps.get({"heat": "heating", "cool": "cooling", "dry": "drying"}[effect]))
    if domain == "humidifier":
        expected = "dehumidifier" if effect == "dry" else "humidifier" if effect == "humidify" else None
        return bool(expected and observed.state in ("on", "off")
                    and observed.attributes.get("device_class") == expected)
    if domain in ("switch", "input_boolean", "number", "input_number"):
        # A direct actuator has no intrinsic HVAC mode. Its real configured
        # heating/cooling role is required, even for advisory substitution.
        if effect not in ("heat", "cool") or settings.get(effect + "_actuator") != entity:
            return False
        return (observed.state in ("on", "off") if domain in ("switch", "input_boolean")
                else _number(observed.state, 0, 100) is not None)
    return False


def _pending_effects(hass: Any, area: str, settings: dict, plan: dict,
                     pending_demands: tuple | list) -> list[dict]:
    """Accept measured demand, never a requested mode alone or stored PID effort.

    Managed callers supply only their selected, authorized automatic/PID
    controllers. Legacy room planning provides its selected equipment intent.
    Both paths recheck real area/capability and the current measurement versus
    the effective target here; this function does not grant device control.
    """
    candidates = [item for item in pending_demands if isinstance(item, dict)]
    equipment = plan.get("equipment_plan", {})
    equipment = equipment if isinstance(equipment, dict) else {}
    thermal = equipment.get("thermal", {})
    thermal = thermal if isinstance(thermal, dict) else {}
    temperature = _number(plan.get("temperature_c"), -10, 50)
    if plan.get("status") == "ready" and thermal.get("status") == "selected":
        effect = thermal.get("mode")
        target = plan.get("temperature_target_c")
        if effect == "heat_cool" and temperature is not None:
            low = _number(plan.get("low_target_c"), 5, 36)
            high = _number(plan.get("high_target_c"), 6, 40)
            if low is not None and temperature < low:
                effect, target = "heat", low
            elif high is not None and temperature > high:
                effect, target = "cool", high
        candidates.append({"entity_id": thermal.get("entity_id"), "effect": effect,
                           "temperature_c": temperature, "target_c": target})
    humidity = plan.get("humidity_management", {})
    humidity = humidity if isinstance(humidity, dict) else {}
    moisture = equipment.get("moisture", {})
    moisture = moisture if isinstance(moisture, dict) else {}
    if (humidity.get("status") == "advisory" and humidity.get("action") in ("dry", "humidify")
            and moisture.get("status") == "selected" and moisture.get("action") == humidity.get("action")):
        effect = humidity["action"]
        candidates.append({"entity_id": moisture.get("entity_id"), "effect": effect,
                           "temperature_c": temperature,
                           "humidity_percent": humidity.get("measured_rh"),
                           "target_humidity": settings.get(
                               "humidity_low_rh" if effect == "humidify" else "humidity_high_rh",
                               40 if effect == "humidify" else 60)})
    result = []
    seen = set()
    for item in candidates:
        entity, effect = item.get("entity_id"), item.get("effect")
        if not _supported_effect(hass, area, settings, entity, effect,
                                 fan_purpose=item.get("fan_purpose")):
            continue
        if effect in ("dry", "humidify"):
            measured = _number(item.get("humidity_percent"), 0, 100)
            target = _number(item.get("target_humidity"), 20, 80)
            needed = measured is not None and target is not None and (
                measured < target if effect == "humidify" else measured > target)
        elif effect == "filtration":
            measured = _number(item.get("pm25_ug_m3"), 0, 2000)
            target = _number(item.get("target_pm25"), 0, 2000)
            needed = measured is not None and target is not None and measured > target + 2
        else:
            measured = _number(item.get("temperature_c"), -10, 50)
            target = _number(item.get("target_c"), 5, 40)
            needed = (measured is not None and target is not None
                      and (measured < target if effect == "heat" else measured > target))
        identity = (entity, effect)
        if needed and identity not in seen:
            seen.add(identity)
            result.append(item)
    return result


def window_substitution(
    hass: Any, room: Any, settings: dict, plan: dict, science: dict,
    weather: tuple, outdoor: tuple, *,
    outside_safe: bool | None,
    outside_reasons: tuple[Reason, ...] = (),
    pending_demands: tuple | list = (),
) -> dict:
    """Choose a single well-supported window alternative, never operate it."""
    base = {"automatic_control": False, "type": "window_efficiency_advice"}
    if not isinstance(settings, dict) or settings.get("enabled") is not True:
        return {**base, "status": "disabled"}
    windows = getattr(room, "windows", ())
    if not windows:
        return {**base, "status": "window_contact_not_configured"}
    if any(w.opened is None for w in windows):
        return {**base, "status": "window_state_unknown"}
    if any(w.opened is True for w in windows):
        return {**base, "status": "window_already_open"}
    from .discovery import entity_area, is_window
    for window in windows:
        if entity_area(hass, window.entity_id) != room.area_id:
            return {**base, "status": "window_wrong_room"}
        observed = hass.states.get(window.entity_id)
        if observed is None or not is_window(hass, observed) or observed.state not in ("on", "off"):
            return {**base, "status": "window_state_unknown"}
        if observed.state == "on":
            return {**base, "status": "window_already_open"}
    cautions = [item for item in outside_reasons if isinstance(item, Reason)]
    if outside_safe is not True and not cautions:
        cautions.append(Reason("outside_conditions_not_verified"))
    # An empty or stale AQ sensor is not proof that outdoor air is harmless;
    # disclose the uncertainty without hiding a measured thermal/moisture need.
    measured = [r for r in outdoor if r.metric in AIR_POLLUTANTS]
    if not measured:
        cautions.append(Reason("no_outdoor_data"))
    for reading in measured:
        if reading.value is None:
            cautions.append(Reason("unavailable_outdoor", reading.name))
        elif reading.metric == "aqi" and (reading.details or {}).get("aqi", {}).get("status") != "ready":
            cautions.append(Reason("aqi_scale_unconfigured", reading.name))
    outdoor_c = _numeric_weather_mean(weather, "temperature_c", -40, 55)
    if outdoor_c is None:
        return {**base, "status": "outdoor_temperature_unknown"}
    # Someone at home can air an empty bathroom or bedroom; exact-room
    # occupancy is not a requirement. Known Away/sleep still suppresses it.
    if plan.get("away") == "away":
        return {**base, "status": "nobody_available_to_open_window"}
    if plan.get("sleeping") is True or plan.get("sleep_schedule_active") is True:
        return {**base, "status": "sleep_room_control_paused"}

    active = [(entity, effect) for entity, effect in _running_effects(hass, room.area_id, settings)
              if _supported_effect(hass, room.area_id, settings, entity, effect)]
    pending = _pending_effects(hass, room.area_id, settings, plan, pending_demands)
    effects = list(dict.fromkeys((*active, *((item["entity_id"], item["effect"]) for item in pending))))
    kinds = {kind for _, kind in effects}
    if not effects:
        return {**base, "status": "no_verified_equipment_demand"}
    if len(kinds) != 1:
        return {**base, "status": "multiple_mechanical_needs"}
    effect = next(iter(kinds))
    device = effects[0][0]
    indoor_c = _number(plan.get("temperature_c"), -10, 50)
    if indoor_c is None:
        indoor_c = next((value for item in pending
                         if (value := _number(item.get("temperature_c"), -10, 50)) is not None), None)
    evidence: dict[str, Any] = {}
    code = ""
    if effect == "cool":
        if indoor_c is None:
            return {**base, "status": "indoor_temperature_missing"}
        # An active compressor can outlive its measured demand (for example
        # during a minimum-ON hold). Do not ask the user to overcool a room
        # already at its known target. Per-device pending targets take
        # precedence over the legacy room target and were checked above.
        known_target = _number(
            plan.get("high_target_c") if plan.get("mode") == "heat_cool"
            else plan.get("temperature_target_c") if plan.get("mode") == "cool" else None,
            5, 40,
        )
        if not pending and known_target is not None and indoor_c <= known_target:
            return {**base, "status": "no_verified_cooling_demand"}
        difference = indoor_c - outdoor_c
        if difference < 2:
            return {**base, "status": "insufficient_free_cooling"}
        code = "climate_window_cool"
        evidence = {"temperature_difference_c": round(difference, 1),
                    "indoor_temperature_c": indoor_c, "outdoor_temperature_c": outdoor_c}
    elif effect == "heat":
        if indoor_c is None:
            return {**base, "status": "indoor_temperature_missing"}
        difference = outdoor_c - indoor_c
        # The outside air must be able to reach the desired indoor heating
        # target; merely being slightly warmer would overpromise substitution.
        targets = [value for item in pending
                   if (value := _number(item.get("target_c"), 5, 36)) is not None]
        desired = max(targets) if targets else _number(
            plan.get("low_target_c") if plan.get("mode") == "heat_cool"
            else plan.get("temperature_target_c"), 5, 36)
        if not pending and desired is not None and indoor_c >= desired:
            return {**base, "status": "no_verified_heating_demand"}
        if desired is None or difference < 2 or outdoor_c < desired - 0.25:
            return {**base, "status": "insufficient_free_warming"}
        code = "climate_window_heat"
        evidence = {"temperature_difference_c": round(difference, 1),
                    "indoor_temperature_c": indoor_c, "outdoor_temperature_c": outdoor_c}
    elif effect == "filtration":
        # Unlike CO2, measured outdoor particles can exceed indoor levels.
        # Only the same pollutant and normalized unit prove this alternative.
        outside_values = [value for reading in outdoor if reading.metric == "pm25"
                          and (value := _number(reading.value, 0, 2000)) is not None]
        inside_values = [value for item in pending
                         if (value := _number(item.get("pm25_ug_m3"), 0, 2000)) is not None]
        targets = [value for item in pending
                   if (value := _number(item.get("target_pm25"), 0, 2000)) is not None]
        if not outside_values or not inside_values or not targets:
            return {**base, "status": "measured_outdoor_particle_benefit_not_verified"}
        outside_pm25 = sum(outside_values) / len(outside_values)
        advantage = min(inside_values) - outside_pm25
        if advantage < 2 or outside_pm25 > min(targets) - 2:
            return {**base, "status": "outside_particles_not_low_enough"}
        code = "climate_window_filtration"
        evidence = {"pm25_advantage_ug_m3": round(advantage, 1),
                    "indoor_pm25_ug_m3": round(min(inside_values), 1),
                    "outdoor_pm25_ug_m3": round(outside_pm25, 1)}
    else:
        humidifying = effect == "humidify"
        humidity = plan.get("humidity_management", {})
        if (not pending and (not isinstance(humidity, dict) or
                humidity.get("status") != "advisory" or
                humidity.get("action") != effect)):
            return {**base, "status": "no_verified_humidifying_demand" if humidifying
                    else "no_verified_drying_demand"}
        if indoor_c is None:
            return {**base, "status": "indoor_temperature_missing_for_moisture"}
        moisture = science.get("moisture", {}) if isinstance(science, dict) else {}
        if not isinstance(moisture, dict) or moisture.get("status") != (
            "humidifying" if humidifying else "drying"
        ):
            return {**base, "status": "measured_outdoor_humidifying_not_verified" if humidifying
                    else "measured_outdoor_drying_not_verified"}
        delta = _number(moisture.get("drying_potential_g_kg"), -30, 30)
        advantage = -delta if humidifying and delta is not None else delta
        targets = [value for item in pending
                   if (value := _number(item.get("target_humidity"), 20, 80)) is not None]
        target_rh = (max(targets) if humidifying else min(targets)) if targets else _number(
            settings.get("humidity_low_rh" if humidifying else "humidity_high_rh",
                         40 if humidifying else 60), 20, 80)
        projected = _number(moisture.get("outside_air_rh_when_warmed_percent"), 0, 100)
        # Prefer shorter airing if outside air would create a large heating
        # burden. Do not equate a window to dehumidifier performance.
        if (advantage is None or advantage < 1.5 or target_rh is None
                or projected is None or (projected < target_rh + 2 if humidifying
                                         else projected > target_rh - 2)):
            return {**base, "status": "humidifying_effect_insufficient" if humidifying
                    else "drying_effect_insufficient"}
        if indoor_c - outdoor_c > 12:
            cautions.append(Reason("weather_heat_loss", value=f"{indoor_c-outdoor_c:g} °C"))
        code = "climate_window_" + effect
        evidence = {"humidity_ratio_advantage_g_kg": round(advantage, 1),
                    "outside_rh_when_warmed_percent": round(projected, 1),
                    "indoor_temperature_c": indoor_c, "outdoor_temperature_c": outdoor_c}
    return {**base, "status": "opportunity", "code": code,
            "effect": effect, "active_device": device, "evidence": evidence,
            "devices": tuple(entity for entity, _ in effects),
            "pending_demand": bool(pending),
            "cautions": [{"code": item.code, "label": item.label, "value": item.value}
                         for item in dict.fromkeys(cautions)],
            "outside_safe": outside_safe is True,
            "reason": "measured_outdoor_air_may_reduce_mechanical_conditioning",
            "note": "Opening a window is a manual, conditional opportunity; do not automatically turn off HVAC equipment."}


def window_cautions(opportunity: dict) -> tuple[Reason, ...]:
    """Convert the JSON-safe dashboard evidence back to announcement reasons."""
    result = []
    for item in opportunity.get("cautions", ()):
        if not isinstance(item, dict) or not isinstance(item.get("code"), str):
            continue
        reason = Reason(item["code"], str(item.get("label") or ""), str(item.get("value") or ""))
        if reason not in result:
            result.append(reason)
    return tuple(result)


def window_reason(opportunity: dict):
    """Build stable, localized reason codes; keep numbers out of dedup keys."""
    from .logic import Reason

    effect = opportunity.get("effect")
    data = opportunity.get("evidence", {})
    if effect in ("heat", "cool"):
        # Valid indoor/outdoor inputs can differ by more than 50 °C. Keep the
        # advisory formatter valid for every opportunity the physics accepts.
        value = _number(data.get("temperature_difference_c"), 0, 100)
        unit = "°C"
    elif effect in ("dry", "humidify"):
        value = _number(data.get("humidity_ratio_advantage_g_kg"), 0, 30)
        unit = "g/kg"
    elif effect == "filtration":
        value = _number(data.get("pm25_advantage_ug_m3"), 0, 2000)
        unit = "µg/m³"
    else:
        raise ValueError("Unsupported window opportunity")
    if value is None:
        raise ValueError("Window opportunity must provide physical evidence")
    return Reason("climate_window_" + effect,
                  str(opportunity.get("active_device") or ""),
                  f"{value:g} {unit}")

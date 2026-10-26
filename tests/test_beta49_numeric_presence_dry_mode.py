"""Beta49: numeric occupancy counters and native dehumidifying climate activation."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from test_discovery import FakeHass, MockState, adapter
from test_equipment_control import home, tick
from custom_components.environment_manager import equipment_model as model
from custom_components.environment_manager.dry_mode import automatic_mode


def test_zero_number_is_away_positive_count_is_home(adapter):
    from custom_components.environment_manager.occupancy_policy import home_presence
    from custom_components.environment_manager.away_windows import confirmed_home_state
    number = MockState("number.home_occupants", 2)
    helper = MockState("input_number.people_home", 0)
    unknown = MockState("person.other", "home")
    hass = FakeHass([number, helper, unknown])
    config = {"occupancy_global": {"home_trackers": [number.entity_id, helper.entity_id]}}
    # Only the explicitly selected sources decide departure, not unrelated
    # person.* entities or a legacy 10-minute Away cooldown.
    assert confirmed_home_state(hass, config) == "home"
    number.state = "0"
    assert confirmed_home_state(hass, config) == "away"
    assert home_presence(hass, config["occupancy_global"])[0] == "away"
    helper.state = "1"
    assert confirmed_home_state(hass, config) == "home"
    helper.state = "0"
    number.state = "unavailable"
    assert confirmed_home_state(hass, config) == "unknown"
    number.state = "nan"
    assert confirmed_home_state(hass, config) == "unknown"
    number.state = "-1"
    assert confirmed_home_state(hass, config) == "unknown"
    number.state = "0.0"
    assert confirmed_home_state(hass, config) == "away"


def test_numeric_sensor_and_room_counter_contribute_to_presence(adapter):
    from custom_components.environment_manager.occupancy_policy import room_presence, home_presence
    hass = FakeHass([
        MockState("sensor.living_people_count", 0),
        MockState("number.kitchen_persons", 0),
    ], {"sensor.living_people_count": "living", "number.kitchen_persons": "kitchen"})
    conf={"room_occupancy_sensors":["sensor.living_people_count", "number.kitchen_persons"],
          "away_cooldown_minutes": 0}
    assert home_presence(hass, conf)[0] == "away"
    assert room_presence(hass, "living", {}, conf, known_areas={"living","kitchen"})[0] == "unoccupied"
    hass.states.get("number.kitchen_persons").state = "2"
    assert home_presence(hass, conf)[0] == "home"
    assert room_presence(hass, "kitchen", {}, conf, known_areas={"living","kitchen"})[0] == "occupied"


def test_numeric_people_count_invalid_and_stale_fail_closed(adapter):
    from custom_components.environment_manager.away_windows import confirmed_home_state
    counter = MockState("input_number.count", 0, hours_old=5)
    hass = FakeHass([counter])
    config = {"occupancy_global": {"home_trackers": [counter.entity_id]}}
    assert confirmed_home_state(hass, config) == "unknown"
    counter.last_reported = counter.last_updated = MockState("sensor.new", 1).last_reported
    counter.state = "bad"
    assert confirmed_home_state(hass, config) == "unknown"
    counter.state = "inf"
    assert confirmed_home_state(hass, config) == "unknown"
    counter.state = "0"
    assert confirmed_home_state(hass, config) == "away"


def test_number_presence_choices_are_user_selectable(monkeypatch, adapter):
    from test_room_setup import build
    flow = build(monkeypatch,adapter)
    for entity, value in (("number.people_home", 0),
                          ("input_number.people_home", 0),
                          ("sensor.room_people_count", 0)):
        state = MockState(entity,value)
        flow.hass._values[entity] = state
        flow.hass._entity_areas[entity] = "living"
    sources=flow._general_options()
    for key in ("general_home_trackers","general_room_occupancy_sensors"):
        available={row["value"] for row in sources[key]}
        assert {"number.people_home","input_number.people_home",
                "sensor.room_people_count"} <= available


@pytest.mark.parametrize("modes", [
    ["off","dry"],
    ["off","cool","dry"],
    ["off","heat","cool","dry","fan_only"],
])
def test_climate_off_dehumidifier_chooses_dry_with_room_rh(runtime_module, modes):
    async def run():
        h=home(runtime_module,domain="climate",mode="automatic")
        h.state.attributes["hvac_modes"]=modes
        h.hass.states.get("sensor.temp").state="22"
        cap=model.capabilities(h.manager,h.spec)
        assert "dry" in cap.modes
        assert cap.humidity, "Logical humidity setpoint must be available in dry mode"
        assert "pid" in model.control_modes(h.manager,h.spec)
        await tick(h)
        assert h.hass.services.calls
        first=h.hass.services.calls[0]
        assert first[0:3] == ("climate","set_hvac_mode",{"hvac_mode":"dry"})
        assert first[3]==h.entity
        await tick(h,advance=1)
        assert h.state.state=="dry"
    asyncio.run(run())


def test_dry_role_wins_when_same_climate_has_native_thermal_features(runtime_module):
    async def run():
        h=home(runtime_module,domain="climate",mode="automatic")
        h.room["dry_climate_entity"]=h.entity
        # Even though a legacy target looks cold, the user explicitly assigned
        # this physical endpoint to DRY instead of the primary heater.
        await tick(h)
        assert h.hass.services.calls[0][2]=={"hvac_mode":"dry"}
    asyncio.run(run())


def test_mixed_compressor_thermal_urgency_wins_over_drying(runtime_module):
    h=home(runtime_module,domain="climate",mode="automatic")
    cap=model.capabilities(h.manager,h.spec)
    assert automatic_mode(cap,h.state,{"temperature":15,"humidity":80},
           {"heat":18,"cool":28,"humidity":50})=="heat"
    assert automatic_mode(cap,h.state,{"temperature":34,"humidity":80},
           {"heat":18,"cool":28,"humidity":50})=="cool"
    assert automatic_mode(cap,h.state,{"temperature":22,"humidity":80},
           {"heat":18,"cool":28,"humidity":50})=="dry"
    assert automatic_mode(cap,h.state,{"temperature":22,"humidity":45},
           {"heat":18,"cool":28,"humidity":50})!="dry"


def test_missing_rh_and_open_window_never_start_drying(runtime_module):
    async def run():
        h=home(runtime_module,domain="climate",mode="automatic")
        h.state.attributes["hvac_modes"]=["off","dry"]
        h.hass.states.get("sensor.rh").state="unavailable"
        await tick(h)
        assert not h.hass.services.calls
        assert h.runtime.statuses[h.spec.identifier]["status"] == "control_measurement_missing_or_stale"
        h.hass.states.get("sensor.rh").state="75"
        h.hass.states.get("binary_sensor.window").state="on"
        await tick(h,advance=1)
        assert not h.hass.services.calls
        assert h.runtime.statuses[h.spec.identifier]["status"]=="open_or_unknown_window"
    asyncio.run(run())


def test_dry_climate_humidity_target_not_fabricated_on_native_device(runtime_module):
    async def run():
        h=home(runtime_module,domain="climate",mode="automatic")
        h.state.attributes["hvac_modes"]=["off","dry"]
        h.state.attributes["supported_features"]=1  # Native temperature only.
        h.hass.states.get("sensor.temp").state="22"
        assert model.capabilities(h.manager,h.spec).humidity
        await tick(h)
        assert h.hass.services.calls[0][1]=="set_hvac_mode"
        await tick(h,advance=1)
        assert not any(x[1]=="set_humidity" for x in h.hass.services.calls), (
            "DRY is controlled by an external RH target, not unsupported native set_humidity")
    asyncio.run(run())

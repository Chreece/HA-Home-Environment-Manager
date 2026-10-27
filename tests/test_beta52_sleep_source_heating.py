"""Beta52: optional sleep-room evidence must not silently disable heating.

Protect real PAUSE semantics and confirmed sleeping occupants; preserve physical
device source authorization, startup, windows and minimum compressor times.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from test_discovery import FakeHass, MockState, adapter
from test_equipment_control import home, tick, runtime_module
from test_equipment_entities import platforms
from custom_components.environment_manager import equipment_model as model


@pytest.mark.parametrize("sleep_behavior", ["pause", "sleep_targets"])
def test_verified_away_allows_heating_when_optional_sleep_source_is_offline(adapter, sleep_behavior):
    from custom_components.environment_manager.occupancy_policy import live_device_permission
    number = MockState("number.people_at_home", 0)
    missing = MockState("sensor.sleep_rooms", "unavailable")
    h = FakeHass([number, missing])
    shared = {"home_trackers": [number.entity_id], "sleep_rooms_entity": missing.entity_id}
    plan = {"global_presence": shared, "known_presence_areas": ["living"],
            "sleeping": None, "away": "away", "tracker_entities": [number.entity_id]}
    device = {"auto_control": True, "presence_requirement": "always",
              "sleep_behavior": sleep_behavior}
    result = live_device_permission(h, "living", {}, plan, device)
    assert result == ("eligible", "device_policy_approved")
    # Any verified arrival removes the Away shortcut. PAUSE remains cautious,
    # while sleep_targets uses the ordinary Home/Comfort fallback setpoint.
    number.state = "1"
    result = live_device_permission(h, "living", {}, plan, device)
    assert result[0] == ("held" if sleep_behavior == "pause" else "eligible")


def test_real_sleeping_signal_still_pauses_heating_even_if_tracker_is_away(adapter):
    from custom_components.environment_manager.occupancy_policy import (
        controlled_sleep_presence, live_device_permission,
    )
    number = MockState("number.people_home", 0)
    room_list = MockState("sensor.sleep_rooms", '["living"]')
    h = FakeHass([number, room_list], {"number.people_home": "living"})
    shared = {"home_trackers": [number.entity_id], "sleep_rooms_entity": room_list.entity_id}
    sleeping, reason = controlled_sleep_presence(
        h, "living", shared, {"living"}, home_status="away",
        local_sleeping=False,
    )
    assert sleeping is True and reason == "verified_rooms_list"
    plan = {"global_presence": shared, "known_presence_areas": ["living"],
            "tracker_entities": [number.entity_id], "sleeping": None}
    device = {"auto_control": True, "presence_requirement": "always",
              "sleep_behavior": "pause"}
    assert live_device_permission(h, "living", {}, plan, device) == (
        "held", "sleep_room_control_paused")


@pytest.mark.parametrize("source", [None, "", "none"])
def test_no_sleep_room_source_never_creates_unknown_sleep_gate(adapter, source):
    from custom_components.environment_manager.occupancy_policy import (
        controlled_sleep_presence, live_device_permission,
    )
    person = MockState("person.resident", "home")
    h = FakeHass([person])
    shared = {"home_trackers": [person.entity_id],
              "sleep_rooms_entity": source}
    sleeping, why = controlled_sleep_presence(
        h, "living", shared, {"living"}, home_status="home")
    assert sleeping is False and why == "sleep_room_source_not_configured"
    plan = {"global_presence": shared, "known_presence_areas": ["living"],
            "tracker_entities": [person.entity_id], "sleeping": None}
    device = {"auto_control": True, "presence_requirement": "always",
              "sleep_behavior": "pause"}
    assert live_device_permission(h, "living", {}, plan, device)[0] == "eligible"


def test_unknown_sleep_source_while_someone_is_home_preserves_explicit_pause(adapter):
    from custom_components.environment_manager.occupancy_policy import live_device_permission
    h = FakeHass([MockState("person.resident", "home"),
                  MockState("sensor.sleep_rooms", "unavailable")])
    plan = {"global_presence": {"home_trackers": ["person.resident"],
                                "sleep_rooms_entity": "sensor.sleep_rooms"},
            "known_presence_areas": ["living"],
            "tracker_entities": ["person.resident"], "sleeping": None}
    device = {"auto_control": True, "presence_requirement": "always",
              "sleep_behavior": "pause"}
    assert live_device_permission(h, "living", {}, plan, device) == (
        "held", "sleep_room_evidence_unknown")


def test_manually_selected_sleep_pause_is_never_bypassed_even_when_away(adapter):
    from custom_components.environment_manager.occupancy_policy import live_device_permission
    counter = MockState("input_number.people_home", 0)
    h = FakeHass([counter])
    room = {"sleep_active": True}
    plan = {"global_presence": {"home_trackers": [counter.entity_id]},
            "known_presence_areas": ["living"], "sleeping": None,
            "tracker_entities": [counter.entity_id]}
    device = {"auto_control": True, "presence_requirement": "always",
              "sleep_behavior": "pause"}
    assert live_device_permission(h, "living", room, plan, device) == (
        "held", "sleep_room_control_paused")


def test_unavailable_optional_sleep_list_does_not_block_real_heater(runtime_module):
    async def scenario():
        h = home(runtime_module, domain="climate", mode="automatic",
                 sleep_behavior="pause")
        # The living-room heater was held in beta51 despite actual cold and
        # zero verified occupants, because its optional sleep list is offline.
        h.state.attributes["hvac_modes"] = ["off", "heat"]
        number = MockState("number.residents_at_home", 0)
        sleepers = MockState("sensor.sleep_rooms", "unavailable")
        h.hass._values[number.entity_id] = number
        h.hass._values[sleepers.entity_id] = sleepers
        shared = {"home_trackers": [number.entity_id],
                  "sleep_rooms_entity": sleepers.entity_id}
        h.manager.entry.data["occupancy_global"] = shared
        h.plan.update(global_presence=shared, known_presence_areas=["room"],
                      tracker_entities=[number.entity_id], away="away",
                      sleeping=None)
        h.hass.states.get("sensor.temp").state = "10"
        await tick(h)
        assert h.hass.services.calls
        domain, service, arguments, target = h.hass.services.calls[0]
        assert domain == "climate" and service == "set_hvac_mode"
        assert arguments == {"hvac_mode": "heat"} and target == h.entity
    asyncio.run(scenario())


def test_climate_only_controller_without_sleep_input_uses_normal_schedule(runtime_module):
    from custom_components.environment_manager.occupancy_policy import home_presence
    h = home(runtime_module, domain="climate", mode="pid")
    h.manager.plan.environment.clear()  # Real climate-only room, no generated climate plan.
    state = MockState("number.people_at_home", 0)
    h.hass._values[state.entity_id] = state
    h.manager.entry.data["occupancy_global"] = {
        "home_trackers": [state.entity_id], "sleep_rooms_entity": None,
    }
    plan = model.plan_for(h.manager, h.spec)
    assert plan["away"] == "away"
    assert plan["sleeping"] is False
    assert plan["sleep_schedule_evidence"] == "sleep_room_source_not_configured"


def test_shared_room_plan_resolves_unknown_sleep_as_not_sleeping_only_when_away(adapter):
    from custom_components.environment_manager.climate_rooms import gather
    from custom_components.environment_manager.logic import Room, Window
    heater = MockState("climate.living", "off")
    heater.attributes.update(hvac_modes=["off", "heat"], supported_features=1)
    temp = MockState("sensor.living_temperature", 10, device_class="temperature", unit="°C")
    resident = MockState("number.people_home", 0)
    sleepers = MockState("sensor.sleep_rooms", "unavailable")
    window = MockState("binary_sensor.living_window", "off", device_class="window")
    h = FakeHass([heater, temp, resident, sleepers, window], {
        heater.entity_id: "living", temp.entity_id: "living",
        window.entity_id: "living"})
    room = Room("living", "Living", (Window(window.entity_id, "Window", False),), ())
    cfg = {"enabled": True, "controller": "device",
           "climate_entity": heater.entity_id, "temperature_entity": temp.entity_id}
    shared = {"home_trackers": [resident.entity_id],
              "sleep_rooms_entity": sleepers.entity_id}
    plan, _ = gather(h, room, cfg, global_presence=shared, known_areas={"living"})
    assert plan["away"] == "away"
    assert plan["sleeping"] is False
    assert plan["sleep_schedule_evidence"] == "verified_home_away_no_sleeping_occupants"


def test_quiet_fan_context_uses_same_sleep_resolution_as_heater(runtime_module):
    h = home(runtime_module, domain="climate", mode="automatic",
             controls={"quiet_sleep": True})
    count = MockState("number.people_home", 0)
    sleep_source = MockState("sensor.sleep_rooms", "unavailable")
    h.hass._values[count.entity_id] = count
    h.hass._values[sleep_source.entity_id] = sleep_source
    shared = {"home_trackers": [count.entity_id],
              "sleep_rooms_entity": sleep_source.entity_id}
    plan = {**h.plan, "global_presence": shared,
            "known_presence_areas": ["room"],
            "tracker_entities": [count.entity_id]}
    cfg = model.settings(h.manager, h.spec)
    assert h.runtime._quiet_context(h.spec, cfg, plan) is False
    count.state = "1"
    # The optional sleeping-room source remains unknown; with beta53 the
    # conservative quiet fan limit applies without vetoing HVAC power.
    assert h.runtime._quiet_context(h.spec, cfg, plan) is True


def test_controller_status_explains_home_and_sleep_source_without_commands(platforms):
    h = home(platforms.runtime, domain="climate", mode="pid")
    h.state.attributes.update(hvac_modes=["off", "heat"])
    count = MockState("number.people_home", 0)
    missing = MockState("sensor.sleep_rooms", "unavailable")
    h.hass._values[count.entity_id] = count
    h.hass._values[missing.entity_id] = missing
    h.manager.entry.data["occupancy_global"] = {
        "home_trackers": [count.entity_id], "sleep_rooms_entity": missing.entity_id}
    h.manager.plan.environment.clear()
    controller = platforms.equipment_status.ControllerStatusSensor(h.manager, h.spec)
    report = controller.extra_state_attributes
    assert report["home_presence_status"] == "away"
    assert report["sleeping"] is False
    assert report["sleep_evidence"] == "verified_home_away_no_sleeping_occupants"
    assert report["sleep_rooms_source_state"] == "unavailable"
    assert report["effective_preset"] == "away"
    assert h.hass.services.calls == []

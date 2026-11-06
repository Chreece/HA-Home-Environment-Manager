"""Environmental consumers honor direct presence, including legacy room trackers.

Execute the production Manager assembly block and the real planning,
presence, continuity and environmental functions. Only Home Assistant
registries/state access and unrelated physical-device enumeration are faked.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "hem_presence_consumers"
AREA = "living"
PERSON = "person.main"
LEGACY = "person.legacy"
MOTION = "binary_sensor.living_presence"
ROOMS = "input_text.occupied_rooms"


def module(name, **members):
    result = ModuleType(name)
    result.__dict__.update(members)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(ROOT)])
module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, State=object, callback=lambda func: func)
module("homeassistant.exceptions", HomeAssistantError=ValueError)
helpers = module("homeassistant.helpers", __path__=[])
module("homeassistant.util", dt=N(utcnow=lambda: datetime.now(timezone.utc)))
for name in ("area_registry", "entity_registry", "device_registry"):
    registry = module(
        "homeassistant.helpers." + name,
        async_get=lambda hass, name=name: getattr(hass, name),
    )
    setattr(helpers, name, registry)

# The consumer runs real planning_rooms; no physical device is enrolled.
module(PACKAGE + ".equipment_model", specs=lambda manager: ())
constants = importlib.import_module(PACKAGE + ".const")
logic = importlib.import_module(PACKAGE + ".logic")
environment = importlib.import_module(PACKAGE + ".environment")
history_module = importlib.import_module(PACKAGE + ".environment_history")
continuity = importlib.import_module(PACKAGE + ".presence_continuity")
arrival = importlib.import_module(PACKAGE + ".arrival_preparation")
occupancy = importlib.import_module(PACKAGE + ".occupancy_policy")
# Keep the empty physical inventory used by Manager assembly above, while
# executing the full production device model for cross-room target decisions.
model_spec = importlib.util.spec_from_file_location(
    PACKAGE + ".consumer_equipment_model", ROOT / "equipment_model.py",
)
model = importlib.util.module_from_spec(model_spec)
sys.modules[model_spec.name] = model
model_spec.loader.exec_module(model)

# Importing the full Manager would require unrelated HA service APIs. Run
# its actual contiguous environmental assembly statements without rewriting
# tracker aggregation or presence decisions inside this test.
manager_tree = ast.parse((ROOT / "manager.py").read_text())
manager_class = next(node for node in manager_tree.body
                     if isinstance(node, ast.ClassDef)
                     and node.name == "AirQualityManager")
capture = next(node for node in manager_class.body
               if isinstance(node, ast.FunctionDef) and node.name == "_capture")
start = next(index for index, node in enumerate(capture.body)
             if isinstance(node, ast.ImportFrom)
             and node.module == "device_activation"
             and any(alias.name == "planning_rooms" for alias in node.names))
end = next(index for index, node in enumerate(capture.body)
           if isinstance(node, ast.Assign)
           and isinstance(node.value, ast.Call)
           and isinstance(node.value.func, ast.Name)
           and node.value.func.id == "build_environment")
assert start < end, "Room planning must precede environmental home resolution"
consumer_code = compile(
    ast.Module(body=capture.body[start:end + 1], type_ignores=[]),
    "manager.py", "exec",
)


class States:
    def __init__(self):
        self.data = {}
        self.reads = []
        self.binary_scans = 0
        self.forbid_room_scan = False

    def get(self, entity):
        self.reads.append(entity)
        if self.forbid_room_scan and entity in (ROOMS, MOTION):
            raise AssertionError("Verified Away must bypass room sources")
        return self.data.get(entity)

    def async_all(self, domain=None):
        if domain == "binary_sensor":
            self.binary_scans += 1
            if self.forbid_room_scan:
                raise AssertionError("Verified Away must skip environmental occupancy")
        return [state for state in self.data.values()
                if domain is None or state.domain == domain]


class Hass:
    def __init__(self):
        self.states = States()
        self.data = {}
        self.config = N(time_zone="UTC")
        self.entries = {}
        self.entity_registry = N(async_get=self.entries.get, entities=self.entries)
        self.device_registry = N(async_get=lambda entity: None)
        self.area_registry = N(async_get_area=lambda area: N(id=area, name=area))

    def put(self, entity, value):
        stamp = datetime.now(timezone.utc) - timedelta(minutes=1)
        attributes = {"device_class": "occupancy"} if entity == MOTION else {}
        self.states.data[entity] = N(
            entity_id=entity, domain=entity.split(".", 1)[0], name=entity,
            state=value, attributes=attributes,
            last_updated=stamp, last_reported=stamp, last_changed=stamp,
        )
        self.entries[entity] = N(
            entity_id=entity, area_id=AREA if entity == MOTION else None,
            device_id=None, platform="test", device_class=None,
            original_device_class=None,
        )


def capture_environment(hass, rooms=None, global_changes=None, *, preparing=False):
    config = {
        constants.CONF_OCCUPANCY_GLOBAL: {
            "home_trackers": [PERSON],
            "occupied_rooms_entity": ROOMS,
            "room_occupancy_sensors": [MOTION],
            **(global_changes or {}),
        },
        "climate_rooms": rooms or {},
        "room_sources": {AREA: {
            "temperature": [], "humidity": [], "air_quality": [], "windows": [],
        }},
    }
    history = history_module.EnvironmentHistory()
    manager = N(
        hass=hass, settings=config, _environment_history=history,
        presence_continuity=continuity.PresenceContinuity(hass, "consumer-test"),
        entry=N(entry_id="consumer-test"), _active=False, _tracked=set(),
    )
    class Store:
        async def async_load(self):
            return None

        async def async_save(self, value):
            self.saved = value

    manager.arrival_preparation = arrival.ArrivalPreparation(
        manager, store=Store(), schedule=lambda hass, delay, callback: lambda: None,
    )
    if preparing:
        async def prepare():
            await manager.arrival_preparation.async_start()
            await manager.arrival_preparation.async_prepare()
        asyncio.run(prepare())
    observed = []
    real_observe = manager.arrival_preparation.observe

    def observe(status):
        observed.append(status)
        real_observe(status)

    manager.arrival_preparation.observe = observe
    room = logic.Room(AREA, "Living room", (), ())
    scope = {
        "__package__": PACKAGE,
        "self": manager, "config": config,
        "CONF_OCCUPANCY_GLOBAL": constants.CONF_OCCUPANCY_GLOBAL,
        "CONF_MOLD_ROOMS": constants.CONF_MOLD_ROOMS,
        "build_environment": environment.build_environment,
        "raw_rooms": (room,), "selected_rooms": (room,),
        "current_weather": (), "outdoor_readings": (),
        "max_age": 240, "environment_rooms": {}, "purifier_ratings": {},
        "base_plan": N(outdoor_safe=True),
    }
    exec(consumer_code, scope)
    assert observed == [scope["home_status"]], "Arrival lifecycle receives actual home evidence"
    assert set(scope["environment_trackers"]) <= manager._tracked, "Every household tracker must receive live events"
    if preparing:
        assert manager.arrival_preparation.active_for(scope["home_status"])
    return scope["home_status"], scope["environment"][AREA], history.samples(AREA)[-1]


class EnvironmentalPresenceTests(unittest.TestCase):
    def test_disabled_room_tracker_is_watched_for_arrival_changes(self):
        hass = Hass()
        tracker = "device_tracker.returning_person"
        hass.put(PERSON, "not_home")
        hass.put(tracker, "not_home")
        home, _, sample = capture_environment(
            hass, {"disabled_room": {"enabled": False, "away_entities": [tracker]}},
            preparing=True,
        )
        self.assertEqual(home, "away")
        self.assertIs(sample["occupied"], False)

    def test_active_arrival_preparation_keeps_environmental_absence_and_history_truthful(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(MOTION, "on")
        hass.states.forbid_room_scan = True
        home, report, sample = capture_environment(hass, preparing=True)
        self.assertEqual(home, "away")
        self.assertIs(sample["occupied"], False)
        self.assertEqual(report["sources"]["occupancy_evidence"], "verified_home_away")
        self.assertNotIn(MOTION, hass.states.reads)

    def test_verified_away_skips_environment_room_sensor_scan(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(MOTION, "on")
        hass.states.forbid_room_scan = True
        home, report, sample = capture_environment(hass)
        self.assertEqual(home, "away")
        self.assertIs(sample["occupied"], False)
        self.assertEqual(report["sources"]["occupancy_evidence"], "verified_home_away")
        self.assertEqual(hass.states.binary_scans, 0)
        self.assertNotIn(MOTION, hass.states.reads)

    def test_unknown_home_preserves_explicit_sensor_selection_and_unknown_room(self):
        hass = Hass()
        hass.put(PERSON, "unavailable")
        hass.put(MOTION, "unavailable")
        home, report, sample = capture_environment(hass)
        self.assertEqual(home, "unknown")
        self.assertIn(MOTION, hass.states.reads)
        self.assertEqual(hass.states.binary_scans, 0)
        self.assertIsNone(sample.get("occupied"))
        self.assertFalse(report["sources"]["occupancy_known"])

    def test_positive_tracker_in_another_room_prevents_derived_vacancy(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(LEGACY, "home")
        hass.put(MOTION, "on")
        home, report, sample = capture_environment(hass, {
            AREA: {"away_entities": []},
            "bedroom": {"away_entities": [LEGACY, LEGACY, None, {}]},
            "ignored": {"away_entities": "person.not_a_list"},
        })
        self.assertEqual(home, "home")
        self.assertIs(sample["occupied"], True)
        self.assertIn(MOTION, hass.states.reads)
        self.assertEqual(hass.states.binary_scans, 0)
        self.assertEqual(report["sources"]["occupancy_evidence"], "selected_room_sensor_on")

    def test_unknown_legacy_tracker_prevents_derived_vacancy(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(LEGACY, "unknown")
        hass.put(MOTION, "unavailable")
        home, report, sample = capture_environment(hass, {
            "bedroom": {"away_entities": [LEGACY]},
        })
        self.assertEqual(home, "unknown")
        self.assertIn(MOTION, hass.states.reads)
        self.assertEqual(hass.states.binary_scans, 0)
        self.assertIsNone(sample.get("occupied"))
        self.assertEqual(report["sources"]["occupancy_evidence"], "room_occupancy_source_unknown")

    def test_room_list_overrides_contradictory_sensor_in_observed_history(self):
        hass = Hass()
        hass.put(PERSON, "home")
        hass.put(MOTION, "on")
        configured = {"occupied_rooms_attribute":"rooms"}
        hass.put(ROOMS, "ready")
        hass.states.data[ROOMS].attributes["rooms"] = []
        home, report, sample = capture_environment(hass, global_changes=configured)
        self.assertEqual(home, "home")
        self.assertIs(sample["occupied"], False)
        self.assertEqual(report["sources"]["occupancy_evidence"], "verified_room_list_unoccupied")
        hass.states.data[ROOMS].attributes["rooms"] = [AREA]
        hass.put(MOTION, "off")
        _, report, sample = capture_environment(hass, global_changes=configured)
        self.assertIs(sample["occupied"], True)
        self.assertEqual(report["sources"]["occupancy_evidence"], "verified_room_occupied")

    def test_room_without_occupancy_sensors_does_not_prove_vacancy_for_science(self):
        hass = Hass()
        hass.put(PERSON, "home")
        hass.put(MOTION, "off")
        _, report, sample = capture_environment(hass, {AREA: {"occupancy_sensors": []}},
                                               {"occupied_rooms_entity": None})
        self.assertIsNone(sample.get("occupied"))
        self.assertFalse(report["sources"]["occupancy_known"])
        self.assertEqual(report["sources"]["occupancy_evidence"], "no_room_presence_sensors")


class CrossRoomArrivalTests(unittest.IsolatedAsyncioTestCase):
    """One legacy tracker must govern every room and every live check."""

    async def asyncSetUp(self):
        self.hass = Hass()
        self.hass.async_create_task = asyncio.create_task
        self.hass.put(LEGACY, "not_home")
        self.now = datetime.now(timezone.utc).timestamp()
        self.spec = model.ManagedDevice("heater", AREA, "Heater", "device", ("climate.heater",))
        self.config = {
            "occupancy_global": {},
            "climate_rooms": {
                AREA: {"occupancy_sensors": []},
                "disabled_room": {"enabled": False, "away_entities": [LEGACY]},
            },
            model.SETTINGS: {"heater": {"control_mode": "automatic", "preset": "none"}},
        }
        self.cached = {"status": "ready", "away": "home", "profile": "home",
                       "occupancy": "occupied", "global_presence": {}, "window_safe": True}
        self.manager = N(
            hass=self.hass, entry=N(entry_id="cross-room"), settings=self.config,
            plan=N(environment={AREA: {"climate_plan": self.cached}}), _active=False,
            presence_continuity=continuity.PresenceContinuity(self.hass, "cross-room"),
        )
        class Store:
            async def async_load(self):
                return None

            async def async_save(self, value):
                self.saved = deepcopy(value)

        self.helper = self.manager.arrival_preparation = arrival.ArrivalPreparation(
            self.manager, store=Store(), clock=lambda: self.now,
            schedule=lambda hass, delay, callback: lambda: None,
        )
        await self.helper.async_start()
        self.device = {
            "auto_control": True, "presence_requirement": "occupied", "sleep_behavior": "normal",
            "_arrival_preparation_eligible": True, "_arrival_preparation_entry_id": "cross-room",
            "_arrival_preparation_presence_override": True,
        }

    async def asyncTearDown(self):
        await self.helper.async_stop()

    def plan(self):
        return model.plan_for(self.manager, self.spec)

    def profile(self, plan):
        return model.profile_name(model.settings(self.manager, self.spec), plan)

    def permission(self, plan):
        return occupancy.live_device_permission(
            self.hass, AREA, self.config["climate_rooms"][AREA], plan, self.device,
        )

    async def test_other_room_tracker_governs_prepare_and_expiry_without_changing_room_presence(self):
        original = deepcopy(self.config)
        cached = deepcopy(self.cached)
        before = self.plan()
        self.assertEqual(self.helper.home_status(), "away")
        self.assertEqual((before["away"], before["occupancy"], self.profile(before)),
                         ("away", "unoccupied", "away"))
        self.assertEqual(before["tracker_entities"], [LEGACY])
        self.assertEqual(self.permission(before), ("held", "room_not_occupied"))
        await self.helper.async_prepare()
        active = self.plan()
        self.assertTrue(active["arrival_preparing"])
        self.assertEqual((active["away"], active["occupancy"], self.profile(active)),
                         ("away", "unoccupied", "home"))
        self.assertEqual(self.permission(active), ("eligible", "preparing_for_arrival"))
        self.now = self.helper.expires_at + 1
        self.helper.observe_current()
        ended = self.plan()
        self.assertFalse(self.helper.armed)
        self.assertEqual((ended["away"], self.profile(ended)), ("away", "away"))
        self.assertEqual(self.permission(ended), ("held", "room_not_occupied"))
        self.assertEqual(self.permission(active), ("held", "arrival_preparation_changed"))
        self.assertEqual(self.config, original)
        self.assertEqual(self.cached, cached)

    async def test_unknown_and_arrival_in_other_room_revoke_live_permission_and_do_not_rearm(self):
        await self.helper.async_prepare()
        active = self.plan()
        self.hass.put(LEGACY, "unknown")
        self.helper.observe_current()
        unknown = self.plan()
        self.assertTrue(self.helper.armed)
        self.assertEqual((self.helper.home_status(), unknown["away"]), ("unknown", "unknown"))
        self.assertFalse(unknown["arrival_preparing"])
        self.assertEqual(self.permission(active), ("held", "house_occupancy_unknown"))
        self.hass.put(LEGACY, "not_home")
        self.assertTrue(self.plan()["arrival_preparing"])
        self.hass.put(LEGACY, "home")
        self.helper.observe_current()
        home = self.plan()
        self.assertEqual((self.helper.home_status(), home["away"], home["occupancy"]),
                         ("home", "home", "unoccupied"))
        self.assertFalse(self.helper.armed)
        self.assertEqual(self.permission(active), ("held", "arrival_preparation_changed"))
        self.hass.put(LEGACY, "not_home")
        departed = self.plan()
        self.assertFalse(departed["arrival_preparing"])
        self.assertEqual(self.profile(departed), "away")

    async def test_shared_tracker_signature_stays_stable_and_current_removal_discards_cached_source(self):
        signature = self.manager.presence_continuity._signature
        since = self.manager.presence_continuity._since
        for mode in ("automatic", "pid"):
            self.config[model.SETTINGS]["heater"]["control_mode"] = mode
            self.assertEqual(self.plan()["global_presence"]["home_trackers"], [LEGACY])
            self.assertEqual(self.helper.home_status(), "away")
            self.assertEqual(self.manager.presence_continuity._signature, signature)
            self.assertEqual(self.manager.presence_continuity._since, since)
        # An explicit empty current selection must not resurrect a source
        # remembered only in a previous plan's merged runtime context.
        self.cached["global_presence"] = self.plan()["global_presence"]
        self.config["climate_rooms"]["disabled_room"]["away_entities"] = []
        self.hass.states.reads.clear()
        current = self.plan()
        self.assertEqual((self.helper.home_status(), current["away"]), ("home", "home"))
        self.assertEqual(current["tracker_entities"], [])
        self.assertNotIn("home_trackers", current["global_presence"])
        self.assertNotIn(LEGACY, self.hass.states.reads)


if __name__ == "__main__":
    unittest.main(verbosity=2)

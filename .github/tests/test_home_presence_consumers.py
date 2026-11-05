"""Environmental consumers honor direct presence, including legacy room trackers.

Execute the production Manager assembly block and the real planning,
presence, continuity and environmental functions. Only Home Assistant
registries/state access and unrelated physical-device enumeration are faked.
"""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import importlib
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
module("homeassistant.core", HomeAssistant=object, State=object)
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
        if entity == ROOMS:
            raise AssertionError("A direct home source must bypass the room list")
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


def capture_environment(hass, rooms=None):
    config = {
        constants.CONF_OCCUPANCY_GLOBAL: {
            "home_trackers": [PERSON],
            "occupied_rooms_entity": ROOMS,
            "room_occupancy_sensors": [MOTION],
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
    )
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
    return scope["home_status"], scope["environment"][AREA], history.samples(AREA)[-1]


class EnvironmentalPresenceTests(unittest.TestCase):
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

    def test_unknown_home_preserves_sensor_scan_and_unknown_room(self):
        hass = Hass()
        hass.put(PERSON, "unavailable")
        hass.put(MOTION, "unavailable")
        home, report, sample = capture_environment(hass)
        self.assertEqual(home, "unknown")
        self.assertGreater(hass.states.binary_scans, 0)
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
        self.assertGreater(hass.states.binary_scans, 0)
        self.assertEqual(report["sources"]["occupancy_evidence"], "room_occupancy_sensors")

    def test_unknown_legacy_tracker_prevents_derived_vacancy(self):
        hass = Hass()
        hass.put(PERSON, "not_home")
        hass.put(LEGACY, "unknown")
        hass.put(MOTION, "unavailable")
        home, report, sample = capture_environment(hass, {
            "bedroom": {"away_entities": [LEGACY]},
        })
        self.assertEqual(home, "unknown")
        self.assertGreater(hass.states.binary_scans, 0)
        self.assertIsNone(sample.get("occupied"))
        self.assertEqual(report["sources"]["occupancy_evidence"], "room_occupancy_source_unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Dependency-free regression audit of selected sensor evidence.

Run from the flat beta package root:
    python3 -m unittest discover -s tests -p 'test_sensor_failsoft.py' -v

AST extraction exercises the actual production functions without importing
Home Assistant or relying on hardware. Full HA integration tests remain
necessary before publishing a physical-control beta.
"""
from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace
import typing
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "environment_manager"
CHANGED = (
    "equipment_runtime.py", "climate_coordination.py", "climate_rooms.py",
    "climate_humidity_native.py", "climate_humidity_power.py",
    "room_sources.py", "manager.py",
)


def source(path):
    return ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)


def load_function(path, name, *, env=None, class_name=None, names=()):
    tree = source(path)
    body = [node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
            and any(isinstance(target, ast.Name) and target.id in names
                    for target in (node.targets if isinstance(node, ast.Assign) else [node.target]))]
    if class_name:
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == class_name)
        target = next(node for node in cls.body
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and node.name == name)
        body.append(ast.ClassDef(name="Isolated", bases=[], keywords=[],
                                 body=[target], decorator_list=[]))
    else:
        body.append(next(node for node in tree.body
                         if isinstance(node, ast.FunctionDef) and node.name == name))
    namespace = {"Any": typing.Any, "math": math}
    namespace.update(env or {})
    unit = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    exec(compile(unit, filename=path, mode="exec"), namespace)
    return getattr(namespace["Isolated"], name) if class_name else namespace[name]


class SensorEvidenceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mean = staticmethod(load_function(
            "climate_coordination.py", "mean_valid_room_humidity"))
        cls.changes = staticmethod(load_function(
            "equipment_runtime.py", "_manual_output_changes",
            names=("SETTABLE_OUTPUT_ATTRIBUTES",)))

    def test_all_changed_modules_parse(self):
        for path in CHANGED:
            with self.subTest(file=path):
                source(path)

    def test_partial_valid_rh_and_deduplicated(self):
        value, reason = self.mean([
            ("sensor.a", 58), ("sensor.b", None), ("sensor.c", 64),
            ("sensor.c", 64), ("sensor.d", float("nan")),
            ("sensor.e", float("inf")), ("sensor.f", True),
        ], ["sensor.a", "sensor.b", "sensor.c"])
        self.assertEqual(value, 61)
        self.assertEqual(reason, "selected_partial_mean")

    def test_rh_all_missing_and_empty_selection(self):
        self.assertEqual(self.mean([("sensor.a", None)], ["sensor.a"])[0], None)
        self.assertEqual(self.mean([("sensor.a", 60)], [])[0], None)
        self.assertEqual(self.mean([("sensor.a", 150)], ["sensor.a"])[0], None)

    def test_ignore_unrelated_sources(self):
        self.assertEqual(self.mean([
            ("sensor.a", 60), ("sensor.not_selected", 2)
        ], ["sensor.a"]), (60, "selected_sensor"))

    def test_passive_esp_capabilities_not_manual_override(self):
        old = {"state": "off", "attributes": {
            "humidity": 50, "fan_mode": "low",
            "supported_features": 413, "fan_modes": ["low", "medium"],
            "hvac_modes": ["off", "dry"]}}
        refreshed = {"state": "off", "attributes": {
            **old["attributes"], "supported_features": 415,
            "fan_modes": ["low", "medium", "high"]}}
        self.assertEqual(self.changes(old, refreshed), ())
        modified = {"state": "off", "attributes": {**old["attributes"], "fan_mode": "high"}}
        self.assertEqual(self.changes(old, modified), ("fan_mode",))
        self.assertEqual(self.changes(old, {"state": "dry", "attributes": old["attributes"]}), ("state",))
        self.assertEqual(self.changes(None, refreshed), ("invalid_baseline",))

    def test_optional_quiet_unknown_never_blocks(self):
        model = SimpleNamespace(ManagedDevice=object, room_config=lambda *_: {})
        quiet = load_function("equipment_runtime.py", "_quiet_context",
                              class_name="EquipmentRuntime", env={"model": model})
        fake = SimpleNamespace(manager=object())
        spec = SimpleNamespace(area_id="badezimmer")
        cfg = {"quiet_sleep": False, "quiet_occupied": True}
        self.assertIs(quiet(fake, spec, cfg, {"occupancy": "unknown"}), True)
        self.assertIs(quiet(fake, spec, cfg, {"occupancy": "occupied"}), True)
        self.assertIs(quiet(fake, spec, cfg, {"occupancy": "unoccupied"}), False)
        self.assertIs(quiet(fake, spec, {"quiet_sleep": True, "quiet_occupied": False},
                            {"sleeping": None}), True)
        self.assertIs(quiet(fake, spec, {"quiet_sleep": True, "quiet_occupied": False},
                            {"sleeping": False}), False)

    def test_room_planner_uses_partial_valid_rh(self):
        planner = load_function(
            "climate_coordination.py", "room_equipment_plan",
            env={
                "device_inventory": lambda *_: {},
                "assigned_entities": lambda _: set(),
                "mean_valid_room_humidity": self.mean,
                "humidity_advice": lambda measured, **_: {
                    "status": "advisory", "measured_rh": measured, "action": "dry"},
                "_usable": lambda *_: False,
                "_pick_thermal": lambda *_: {"status": "none"},
                "_pick_moisture": lambda *_: {"status": "none"},
            })
        readings = tuple(SimpleNamespace(entity_id=name, metric="humidity", value=value)
                         for name, value in (("sensor.a", 58), ("sensor.b", None),
                                             ("sensor.c", 64)))
        planned = planner(
            None, "badezimmer", {}, {"status": "ready", "window_safe": True},
            readings, humidity_source_entities=["sensor.a", "sensor.b", "sensor.c"],
        )
        self.assertEqual(planned["humidity"]["measured_rh"], 61)
        self.assertEqual(planned["humidity_evidence"], "selected_partial_mean")

    def test_unknown_window_remains_a_safety_hold(self):
        interlock = load_function(
            "climate_arbitration.py", "_contact_interlock",
            env={"entity_area": lambda *_: "badezimmer"})
        states = {
            "binary_sensor.window": SimpleNamespace(
                domain="binary_sensor", attributes={"device_class": "window"},
                state="off"),
        }
        hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
        self.assertIs(interlock(hass, "badezimmer", {
            "window_safe": True, "window_contacts": ["binary_sensor.window"]}), True)
        states.pop("binary_sensor.window")
        self.assertIs(interlock(hass, "badezimmer", {
            "window_safe": True, "window_contacts": ["binary_sensor.window"]}), False)
        self.assertIs(interlock(hass, "badezimmer", {
            "window_safe": False, "window_contacts": []}), False)

    def test_live_selected_feedback_falls_back_to_valid_peer(self):
        readings = {
            "sensor.a": SimpleNamespace(metric="humidity", value=58),
            "sensor.b": SimpleNamespace(metric="humidity", value=None),
            "sensor.c": SimpleNamespace(metric="humidity", value=64),
            "sensor.other": SimpleNamespace(metric="humidity", value=30),
        }
        mean = self.mean
        fn = load_function("climate_coordination.py", "live_room_humidity",
                           env={"entity_area": lambda _, e: "badezimmer",
                                "reading": lambda _, e, __, outdoor: readings[e],
                                "mean_valid_room_humidity": mean})
        value, reason = fn(object(), "badezimmer", {},
                           {"humidity_source_entities": ["sensor.a", "sensor.b", "sensor.c"]})
        self.assertEqual((value, reason), (61, "selected_partial_mean"))
        self.assertEqual(fn(object(), "badezimmer", {}, {"humidity_source_entities": []})[0], None)


if __name__ == "__main__":
    unittest.main()

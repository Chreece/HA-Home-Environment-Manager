"""Dependency-free regressions for Beta55's room limits and PID names.

No Home Assistant or physical actuator is imported, invoked or fabricated.
Read production AST functions and the exact shipped in-memory name catalogs.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIMIT_FIELDS = (
    "temperature_min_limit", "temperature_max_limit",
    "humidity_min_limit", "humidity_max_limit",
    "fan_min_percentage", "fan_max_percentage",
)


def extracted(*names: str) -> dict:
    source = (ROOT / "equipment_model.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="equipment_model.py")
    chosen = [node for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and node.name in names]
    assert {n.name for n in chosen} == set(names)
    code = ast.Module(
        body=[ast.parse("from __future__ import annotations").body[0], *chosen],
        type_ignores=[],
    )
    namespace = {}
    exec(compile(ast.fix_missing_locations(code), "equipment_model.py", "exec"),
         namespace)
    return namespace


class Registry:
    def __init__(self):
        self.registered = set()

    def async_get_entity_id(self, domain, platform, unique_id):
        return unique_id if (domain, platform, unique_id) in self.registered else None


class RoomLimitTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        registry_module = types.ModuleType("homeassistant.helpers.entity_registry")
        registry_module.async_get = lambda _hass: self.registry
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.__path__ = []
        helpers.entity_registry = registry_module
        ha = types.ModuleType("homeassistant")
        ha.__path__ = []
        ha.helpers = helpers
        self._original = {name: sys.modules.get(name) for name in (
            "homeassistant", "homeassistant.helpers",
            "homeassistant.helpers.entity_registry",
        )}
        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.helpers"] = helpers
        sys.modules["homeassistant.helpers.entity_registry"] = registry_module

        self.area = "bathroom"
        self.selected = [types.SimpleNamespace(area_id=self.area,
                                               identifier="controlled-dehumidifier")]
        self.capabilities = None
        self.live_bounds = {}
        self.live_values = {}
        self.settings = {"environment_rooms": {self.area: {}}}
        self.manager = types.SimpleNamespace(
            settings=self.settings, hass=types.SimpleNamespace(),
            entry=types.SimpleNamespace(entry_id="entry"),
        )
        n = extracted("room_limit_edit_bounds", "available_room_limit_fields",
                      "room_limit_display_values")
        n.update({
            "specs": lambda manager: self.selected,
            "capabilities": lambda manager, spec: self.capabilities,
            "room_limit_bounds": lambda manager, area, key: self.live_bounds.get(key),
            "room_limit_values": lambda manager, area: self.live_values.copy(),
            "LIMIT_FIELDS": LIMIT_FIELDS,
            "ROOM_LIMITS_KEY": "equipment_limits",
            "DOMAIN": "environment_manager",
            "_OFFLINE_ROOM_LIMIT_BOUNDS": {
                "temperature_min_limit": (5., 35., 0.5, "°C"),
                "temperature_max_limit": (5., 35., 0.5, "°C"),
                "humidity_min_limit": (20., 80., 1., "%"),
                "humidity_max_limit": (20., 80., 1., "%"),
                "fan_min_percentage": (1., 100., 1., "%"),
                "fan_max_percentage": (1., 100., 1., "%"),
            },
            "finite": lambda v, low, high: (
                float(v) if v is not None and not isinstance(v, bool)
                and isinstance(v, (int, float)) and low <= v <= high else None
            ),
            "_legacy_room_limit": lambda manager, area, key, bounds: None,
        })
        # Production functions close over the same dictionary. Recreate them
        # with the complete stub environment, not a copy of their algorithms.
        source = ast.parse((ROOT / "equipment_model.py").read_text(encoding="utf-8"))
        selected = [node for node in source.body
                    if isinstance(node, ast.FunctionDef)
                    and node.name in ("room_limit_edit_bounds",
                                      "available_room_limit_fields",
                                      "room_limit_display_values")]
        module = ast.Module(
            body=[ast.parse("from __future__ import annotations").body[0], *selected],
            type_ignores=[],
        )
        exec(compile(ast.fix_missing_locations(module), "equipment_model.py", "exec"), n)
        self.api = n

    def tearDown(self):
        for name, original in self._original.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def remember(self, key):
        self.registry.registered.add((
            "number", "environment_manager",
            f"entry_area_{self.area}_room_equipment_limit_{key}",
        ))

    def test_missing_first_install_is_not_fabricated(self):
        self.assertIsNone(self.api["room_limit_edit_bounds"](
            self.manager, self.area, "humidity_min_limit"))
        self.assertEqual(self.api["available_room_limit_fields"](
            self.manager, self.area), ())
        self.assertEqual(self.api["room_limit_display_values"](
            self.manager, self.area), {})

    def test_previously_supported_numbers_remain_readable_offline(self):
        for key in LIMIT_FIELDS[:4]:
            self.remember(key)
        self.assertEqual(self.api["available_room_limit_fields"](
            self.manager, self.area), LIMIT_FIELDS[:4])
        values = self.api["room_limit_display_values"](self.manager, self.area)
        self.assertEqual(values["temperature_min_limit"], 5.)
        self.assertEqual(values["temperature_max_limit"], 35.)
        self.assertEqual(values["humidity_min_limit"], 20.)
        self.assertEqual(values["humidity_max_limit"], 80.)

    def test_saved_limits_survive_unavailable_actuator(self):
        self.settings["environment_rooms"][self.area]["equipment_limits"] = {
            "humidity_min_limit": 42.,
            "humidity_max_limit": 67.,
        }
        values = self.api["room_limit_display_values"](self.manager, self.area)
        self.assertEqual(values["humidity_min_limit"], 42.)
        self.assertEqual(values["humidity_max_limit"], 67.)

    def test_no_selected_device_means_no_room_limit(self):
        self.selected.clear()
        self.remember("humidity_min_limit")
        self.assertIsNone(self.api["room_limit_edit_bounds"](
            self.manager, self.area, "humidity_min_limit"))

    def test_capabilities_authoritative_on_recovery(self):
        self.remember("temperature_max_limit")
        self.live_bounds["temperature_max_limit"] = (12., 30., 0.25, "°C")
        self.live_values["temperature_max_limit"] = 27.
        self.assertEqual(self.api["room_limit_edit_bounds"](
            self.manager, self.area, "temperature_max_limit"),
            (12., 30., 0.25, "°C"))
        self.assertEqual(self.api["room_limit_display_values"](
            self.manager, self.area)["temperature_max_limit"], 27.)

    def test_stale_registry_does_not_imitate_live_unsupported_device(self):
        self.remember("humidity_min_limit")
        self.capabilities = object()
        self.assertIsNone(self.api["room_limit_edit_bounds"](
            self.manager, self.area, "humidity_min_limit"))

    def test_native_actuation_never_uses_provisional_bounds(self):
        tree = ast.parse((ROOT / "equipment_model.py").read_text(encoding="utf-8"))
        device_limits = next(node for node in tree.body
                             if isinstance(node, ast.FunctionDef)
                             and node.name == "device_limits")
        referenced = {node.id for node in ast.walk(device_limits)
                      if isinstance(node, ast.Name)}
        self.assertIn("room_limit_values", referenced)
        self.assertNotIn("room_limit_display_values", referenced)


def import_catalog(path: str):
    spec = importlib.util.spec_from_file_location("beta55_" + path[:-3],
                                                  ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NamingTests(unittest.TestCase):
    def test_managed_pid_parameters_before_device_and_translation(self):
        mod = import_catalog("equipment_name_catalog.py")
        self.assertGreaterEqual(len(mod.EQUIPMENT_TRANSLATED_NAMES), 30)
        for locale in mod.EQUIPMENT_TRANSLATED_NAMES:
            for key, label in (("kp", "Kp"), ("ki", "Ki"), ("kd", "Kd"),
                               ("sample_seconds", "Sample"),
                               ("cycle_seconds", "PWM")):
                with self.subTest(locale=locale, key=key):
                    title = mod.localized_equipment_name(
                        key, locale, "Original device · ")
                    self.assertTrue(title.startswith(f"PID · {label} · "),
                                    title)
                    self.assertIn("Original device · ", title)

    def test_room_pid_parameters_precede_localized_description(self):
        mod = import_catalog("room_pid_name_catalog.py")
        self.assertGreaterEqual(len(mod.ROOM_PID_NAMES), 30)
        for locale in mod.ROOM_PID_NAMES:
            for prefix in ("area_pid_", "area_direct_tuning_"):
                for key, label in (("kp", "Kp"), ("ki", "Ki"), ("kd", "Kd"),
                                   ("sample_seconds", "Sample")):
                    with self.subTest(locale=locale, key=prefix + key):
                        title = mod.localized_room_pid_name(prefix + key, locale)
                        self.assertTrue(title.startswith(f"PID · {label} · "),
                                        title)


class SyntaxTests(unittest.TestCase):
    def test_python_sources_compile(self):
        for path in ROOT.glob("*.py"):
            with self.subTest(path=path.name):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_late_number_registration_has_native_recovery(self):
        code = (ROOT / "number.py").read_text(encoding="utf-8")
        self.assertIn("room_limit_numbers", code)
        self.assertIn('equipment.room_limit_edit_bounds(', code)
        self.assertIn("room_limit_display_values(", code)
        self.assertIn("_sync_room_limit_bounds()", code)
        self.assertIn("async_add_grouped_entities(", code)


if __name__ == "__main__":
    unittest.main()

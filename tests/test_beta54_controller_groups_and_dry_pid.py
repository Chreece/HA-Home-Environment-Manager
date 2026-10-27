"""Standalone Beta54 regressions: grouped names and delayed DRY PID controls.

Run in the flat Home Environment Manager source checkout:
    python -m unittest discover -s tests -p 'test_beta54*.py' -v

No Home Assistant runtime, network access or actuator services are required.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
PID_KEYS = {"kp", "ki", "kd", "sample_seconds", "cycle_seconds"}
GROUPS = {
    "control_mode": "control", "resume": "control",
    "control_status": "status", "climate": "climate",
    "quiet_percentage": "quiet", "quiet_sleep": "quiet",
    "quiet_occupied": "quiet", "quiet_fan_mode": "quiet",
    "presence_requirement": "presence", "sleep_behavior": "sleep",
    "fan_purpose": "fan", "sensor_verified": "sensor",
    "min_on_seconds": "power", "min_off_seconds": "power",
    "max_on_seconds": "power",
}


def extract_function(path: str, function: str, context: dict) -> object:
    """Compile the actual pure function without importing HA platforms."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(n for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == function)
    source = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[
            ast.alias(name="annotations")], level=0), node],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(source), path, "exec"), context)
    return context[function]


class Beta54ControllerTests(unittest.TestCase):
    def test_every_locale_groups_all_equipment_names(self):
        paths = [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]
        self.assertEqual(len(paths), 39)
        for path in paths:
            with self.subTest(locale=path.name):
                obj = json.loads(path.read_text(encoding="utf-8"))
                entries = [(key[10:], data["name"])
                           for group in obj["entity"].values()
                           for key, data in group.items()
                           if key.startswith("equipment_") and "name" in data]
                self.assertEqual(len(entries), 39)
                for key, label in entries:
                    prefix = label.split(" · ", 1)[0]
                    self.assertTrue(prefix and "{channel}" not in prefix, (path, key, label))
                    if key.startswith("pid_") or key in PID_KEYS:
                        self.assertEqual(prefix, "PID", (path, key, label))
                    else:
                        self.assertIn(key, GROUPS, (path, key, label))
                    self.assertNotEqual(label[:9], "{channel}", (path, key, label))
                self.assertIn("{channel}", obj["entity"]["climate"]["equipment_climate"]["name"])

    def test_room_level_pid_names_are_translated_and_grouped(self):
        names = {}
        exec(compile((ROOT / "room_pid_name_catalog.py").read_text(encoding="utf-8"),
                     "room_pid_name_catalog.py", "exec"), names)
        lookup = names["localized_room_pid_name"]
        self.assertEqual(len(names["ROOM_PID_NAMES"]), 38)
        for locale, entries in names["ROOM_PID_NAMES"].items():
            with self.subTest(locale=locale):
                self.assertEqual(len(entries), 17)
                source = (ROOT / "strings.json" if locale == "en"
                          else ROOT / "translations" / f"{locale}.json")
                translations = json.loads(source.read_text(encoding="utf-8"))["entity"]
                expected = {key: data["name"]
                            for scope in ("number", "select")
                            for key, data in translations[scope].items()
                            if key.startswith(("area_pid_", "area_direct_tuning_"))}
                self.assertEqual(entries, expected)
                for key, label in entries.items():
                    self.assertTrue(label.startswith("PID · "), (locale, key, label))
                    self.assertEqual(lookup(key, locale), label)
        self.assertEqual(lookup("area_pid_gain_source", "el-GR"),
                         lookup("area_pid_gain_source", "el"))
        self.assertEqual(lookup("area_pid_gain_source", "xx"),
                         lookup("area_pid_gain_source", "en"))

    def test_dry_only_advertises_pid_and_persists_selection(self):
        cap = SimpleNamespace(domain="climate", modes=("off", "dry"),
                              temperature=False, humidity=True)
        saved = {"control_mode": "automatic"}
        global_context = {
            "capabilities": lambda _m, _s: cap,
            "settings": lambda _m, _s: saved,
        }
        choices = extract_function("equipment_model.py", "control_modes", global_context)
        spec = SimpleNamespace(source_entities=("climate.dry_only",))
        self.assertIn("pid", choices(None, spec))
        cap = None
        saved["control_mode"] = "pid"
        self.assertIn("pid", choices(None, spec))
        saved["control_mode"] = "automatic"
        self.assertNotIn("pid", choices(None, spec))
        saved["control_mode"] = "pid"
        self.assertNotIn("pid", choices(None, SimpleNamespace(
            source_entities=("switch.plug",))))
        cap = SimpleNamespace(domain="climate", modes=("off",), temperature=False,
                              humidity=False)
        self.assertNotIn("pid", choices(None, spec))

    def test_dry_pid_tuning_registers_late_and_does_not_invent_hardware(self):
        cfg = {"control_mode": "automatic"}
        qualified = False
        remembered = set()
        spec = SimpleNamespace(source_entities=("climate.bathroom_dry",))
        fake_equipment = SimpleNamespace(
            control_modes=lambda _m, _s: ("existing", "automatic", "pid")
            if qualified else ("existing", "automatic", "manual", "off"),
            settings=lambda _m, _s: cfg,
        )
        context = {
            "equipment": fake_equipment,
            "registered_control": lambda _registry, platform, _spec, key:
                (platform, key) in remembered,
        }
        supported = extract_function("equipment_feature_registration.py",
                                     "pid_calibration_supported", context)
        for platform in ("select", "button"):
            self.assertFalse(supported(None, None, spec, platform=platform))
        qualified = True  # Physical climate advertises OFF + DRY after setup.
        for platform in ("select", "button"):
            self.assertTrue(supported(None, None, spec, platform=platform))
        qualified = False
        cfg["control_mode"] = "pid"  # Preserve explicit previously accepted PID.
        for platform in ("select", "button"):
            self.assertTrue(supported(None, None, spec, platform=platform))
        cfg["control_mode"] = "automatic"
        remembered.add(("select", "pid_calibration_method"))
        self.assertTrue(supported(None, None, spec, platform="select"))
        self.assertFalse(supported(None, None, spec, platform="button"))
        with self.assertRaises(ValueError):
            supported(None, None, spec, platform="climate")

    def test_equipment_init_keeps_identifiers_and_sorts_by_group(self):
        names_module = {}
        exec(compile((ROOT / "equipment_name_catalog.py").read_text(encoding="utf-8"),
                     "equipment_name_catalog.py", "exec"), names_module)
        resolve = names_module["localized_equipment_name"]
        self.assertEqual(resolve("control_mode", "el"), "Έλεγχος · Μέθοδος")
        self.assertEqual(resolve("control_mode", "el-GR"), "Έλεγχος · Μέθοδος")
        self.assertEqual(resolve("control_mode", "de"), "Steuerung · Verfahren")
        self.assertEqual(resolve("control_mode", "zz"), "Control · Method")
        self.assertEqual(resolve("climate", "el", "Comfee"), "Κλίμα · Comfee")
        for loc in ("en", "el", "de", "pt-BR", "zh-Hant"):
            translated = names_module["EQUIPMENT_TRANSLATED_NAMES"][loc]
            path = (ROOT / "strings.json" if loc == "en"
                    else ROOT / "translations" / f"{loc}.json")
            labels = json.loads(path.read_text(encoding="utf-8"))["entity"]
            for domain, group in labels.items():
                for key, item in group.items():
                    if key.startswith("equipment_") and "name" in item:
                        self.assertEqual(translated[key[10:]], item["name"])

        module = ast.parse((ROOT / "equipment_entity.py").read_text(encoding="utf-8"))
        cls = next(n for n in module.body if isinstance(n, ast.ClassDef)
                   and n.name == "EquipmentEntity")
        class Endpoint:
            pass
        context = {
            "DOMAIN": "environment_manager",
            "callback": lambda f: f,
            "localized_equipment_name": resolve,
            "model": SimpleNamespace(
                ManagedEndpoint=Endpoint,
                device_identifier=lambda spec: spec.identifier,
            ),
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])),
                     "equipment_entity.py", "exec"), context)
        Entity = context["EquipmentEntity"]
        spec = SimpleNamespace(identifier="entry_controller_unchanged",
                               name="Bathroom dehumidifier",
                               source_entities=("climate.dry_only",),
                               area_id="bathroom", source_device_id="hardware")
        manager = SimpleNamespace(hass=SimpleNamespace(
            config=SimpleNamespace(language="el"),
            states=SimpleNamespace(get=lambda _id: None)))
        ctrl = Entity()
        ctrl._equipment_init(manager, spec, "pid_calibration_method")
        self.assertFalse(ctrl._attr_has_entity_name)
        self.assertEqual(ctrl._attr_unique_id, "entry_controller_unchanged_pid_calibration_method")
        self.assertEqual(ctrl._attr_translation_placeholders["channel"], "")
        self.assertEqual(ctrl._attr_name, "PID · Μέθοδος βαθμονόμησης")
        climate = Entity()
        climate._equipment_init(manager, spec, "climate")
        self.assertEqual(climate._attr_translation_placeholders["channel"],
                         "Bathroom dehumidifier")
        self.assertEqual(climate._attr_name, "Κλίμα · Bathroom dehumidifier")
        self.assertFalse(climate._attr_has_entity_name)
        endpoint = Endpoint()
        endpoint.identifier = spec.identifier
        endpoint.name = spec.name
        endpoint.source_entities = spec.source_entities
        native = SimpleNamespace(name="Comfee dry controller")
        manager.hass.states.get = lambda _id: native
        channel = Entity()
        channel._equipment_init(manager, endpoint, "kp")
        self.assertEqual(channel._attr_translation_placeholders["channel"],
                         "Comfee dry controller · ")
        self.assertTrue(channel._attr_name.startswith(
            "PID · Comfee dry controller · "))


if __name__ == "__main__":
    unittest.main()

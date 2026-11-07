"""Device operating holds: real Number metadata, edits and localized meaning.

Runs the production EquipmentNumber constructor and value/setter methods with
the production field bounds and EquipmentEntity identity/name initialization.
Only unrelated HA services and capabilities are replaced by small fixtures.
Runtime transition/demand tests cover the actual ON/OFF scheduling separately.
"""
from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
FIELDS = ("min_on_seconds", "min_off_seconds", "max_on_seconds")
MINIMA = FIELDS[:2]
NAMES = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))
HELP = runpy.run_path(str(ROOT / "equipment_help.py"))
DOMAIN = next(ast.literal_eval(node.value)
              for node in ast.parse((ROOT / "const.py").read_text()).body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "DOMAIN"
                      for target in node.targets))


def _compile(nodes, namespace, filename):
    future = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[future, *nodes], type_ignores=[])
    )
    exec(compile(module, str(filename), "exec"), namespace)


def _number_class():
    path = ROOT / "equipment_model.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    model_ns = {}
    _compile([
        node for node in tree.body
        if (isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "NUMBER_FIELDS"
                    for target in node.targets))
        or (isinstance(node, ast.FunctionDef)
            and node.name in ("number_bounds", "device_identifier"))
    ], model_ns, path)

    class ManagedEndpoint(N):
        pass

    model = N(
        **{key: value for key, value in model_ns.items()
           if not key.startswith("__")},
        ManagedEndpoint=ManagedEndpoint,
        FAN_LIMIT_FIELDS=(), PID_FAN_CAPACITY_FIELDS={}, PID_MODEL_FIELDS={},
        capabilities=lambda manager, _spec: manager.cap,
        settings=lambda manager, _spec: manager.values,
    )
    path = ROOT / "equipment_entity.py"
    entity_node = next(node for node in ast.parse(path.read_text()).body
                       if isinstance(node, ast.ClassDef)
                       and node.name == "EquipmentEntity")
    entity_node.body = [node for node in entity_node.body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name in ("_equipment_init", "controller_settings", "_async_update_controller_settings")]
    namespace = {
        "model": model, "equipment": model, "DOMAIN": DOMAIN,
        "localized_equipment_name": NAMES["localized_equipment_name"],
        "EntityCategory": N(CONFIG="config"), "NumberMode": N(BOX="box"),
        "NumberEntity": type("NumberEntity", (), {}),
    }
    _compile([entity_node], namespace, path)
    path = ROOT / "number.py"
    number_node = next(node for node in ast.parse(path.read_text()).body
                       if isinstance(node, ast.ClassDef)
                       and node.name == "EquipmentNumber")
    number_node.body = [node for node in number_node.body
                        if isinstance(node, ast.Assign)
                        or (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and node.name in ("__init__", "native_value",
                                              "async_set_native_value"))]
    _compile([number_node], namespace, path)
    return namespace["EquipmentNumber"], model


EquipmentNumber, MODEL = _number_class()


def _fixture(domain="climate", language="en"):
    manager = N(
        cap=N(domain=domain, fan_percentage=False) if domain else None,
        values={key: value[4] for key, value in MODEL.NUMBER_FIELDS.items()},
        hass=N(config=N(language=language), states=N(
            get=lambda _entity: N(name="Living radiator")
        )),
    )
    spec = MODEL.ManagedEndpoint(
        identifier="entry_living_valve_channel", name="Living radiator",
        physical_identifier="entry_living_valve", source_device_id="zigbee_valve",
        source_entities=("climate.living_valve",), area_id="living",
    )
    manager.saved = []

    async def update(actual_spec, changes):
        manager.saved.append((actual_spec, changes.copy()))
        manager.values.update(changes)

    manager.equipment = N(async_update=update)
    return manager, spec


class OperatingTimingUi(unittest.TestCase):
    def test_minute_bounds_preserve_one_second_minimum_resolution(self):
        # An available TRV, fan, humidifier, and not-yet-restored native device
        # must expose the same editable minimum without a hidden 600s floor.
        for domain in ("climate", "fan", "humidifier", None):
            for key, maximum in zip(MINIMA, (120, 240)):
                with self.subTest(domain=domain, field=key):
                    manager, spec = _fixture(domain)
                    number = EquipmentNumber(manager, spec, key)
                    self.assertEqual(number._attr_native_min_value, 0)
                    self.assertEqual(number._attr_native_max_value, maximum)
                    self.assertEqual(number._attr_native_step, 1 / 60)
                    self.assertEqual(number._attr_native_unit_of_measurement, "min")
                    self.assertEqual(number._attr_mode, "box")

    def test_existing_identity_and_physical_device_association(self):
        manager, spec = _fixture()
        for key in FIELDS:
            with self.subTest(field=key):
                number = EquipmentNumber(manager, spec, key)
                self.assertEqual(number._attr_unique_id, f"{spec.identifier}_{key}")
                self.assertEqual(number._attr_translation_key, f"equipment_{key}")
                self.assertEqual(number._attr_device_info["identifiers"], {
                    ("environment_manager", spec.physical_identifier)
                })
                self.assertFalse(number._attr_has_entity_name)
                self.assertIn("Living radiator · ", number._attr_name)
                self.assertIn("min", number._attr_name)

    def test_zero_and_fractional_minutes_round_trip_saved_seconds(self):
        manager, spec = _fixture()
        for key in MINIMA:
            number = EquipmentNumber(manager, spec, key)
            # Zero is a deliberate configured value; 0.5 minute remains 30s.
            for seconds in (0, 1, 37, 120, 600):
                with self.subTest(field=key, seconds=seconds):
                    asyncio.run(number.async_set_native_value(seconds / 60))
                    self.assertEqual(manager.saved[-1], (spec, {key: seconds}))
                    self.assertEqual(number.native_value, seconds / 60)
            asyncio.run(number.async_set_native_value(0.5))
            self.assertEqual(manager.saved[-1], (spec, {key: 30.0}))
            self.assertEqual(number.native_value, 0.5)

    def test_other_timing_metadata_remains_distinct(self):
        manager, spec = _fixture()
        expected = {
            "sample_seconds": (120, 3600, 30),
            "cycle_seconds": (600, 86400, 60),
            "power_switch_cooldown_seconds": (60, 86400, 60),
        }
        for key, bounds in expected.items():
            with self.subTest(field=key):
                number = EquipmentNumber(manager, spec, key)
                self.assertEqual((number._attr_native_min_value,
                                  number._attr_native_max_value,
                                  number._attr_native_step), bounds)
                self.assertEqual(number._attr_native_unit_of_measurement, "s")

    def test_all_locale_names_match_runtime_catalog_and_existing_keys(self):
        paths = sorted((ROOT / "translations").glob("*.json"))
        self.assertEqual(len(paths), 38)
        names = NAMES["EQUIPMENT_TRANSLATED_NAMES"]
        translate = NAMES["localized_equipment_name"]
        for path in paths:
            data = json.loads(path.read_text())
            for key in FIELDS:
                with self.subTest(locale=path.stem, field=key):
                    label = data["entity"]["number"][f"equipment_{key}"]["name"]
                    self.assertEqual(label, names[path.stem][key])
                    self.assertEqual(label.count("{channel}"), 1)
                    self.assertIn("(", label)
                    self.assertFalse(label.endswith(" (s)"), label)
                    self.assertEqual(translate(key, path.stem, "Valve · "),
                                     label.replace("{channel}", "Valve · "))
            self.assertNotEqual(names[path.stem][FIELDS[0]], names[path.stem][FIELDS[1]])
        english = json.loads((ROOT / "strings.json").read_text())
        for key, label in zip(MINIMA, ("Minimum device ON time", "Minimum device OFF time")):
            expected = f"Operation · {{channel}}{label} (min)"
            self.assertEqual(names["en"][key], expected)
            self.assertEqual(english["entity"]["number"][f"equipment_{key}"]["name"], expected)

    def test_help_explains_zero_device_operation_and_manufacturer_choice(self):
        help_for = HELP["equipment_configuration_help"]
        for locale, minutes, confirmation, manufacturer in (
            ("en", "minutes", "command confirmation", "manufacturer"),
            ("el", "λεπτά", "επιβεβαίωση εντολών", "κατασκευαστή"),
            ("de", "Minuten", "Befehlsbestätigung", "Herstellerangaben"),
        ):
            for key in MINIMA:
                with self.subTest(locale=locale, field=key):
                    help_text = help_for(key, locale)
                    for required in ("0", minutes, confirmation, manufacturer):
                        self.assertIn(required, help_text)
            self.assertNotEqual(help_for(FIELDS[0], locale), help_for(FIELDS[1], locale))
        self.assertIn("remain operating", help_for(FIELDS[0], "en"))
        for locale, retained_cycle in (
            ("en", "current cycle completes first"),
            ("el", "τρέχοντα κύκλο ολοκληρώνεται πρώτα"),
            ("de", "aktuellen Zyklus gespeicherte Mindestlaufzeit"),
        ):
            self.assertIn(retained_cycle, help_for(FIELDS[0], locale))
        self.assertIn("remain stopped", help_for(FIELDS[1], "en"))
        self.assertIn("keeps the observed OFF time", help_for(FIELDS[1], "en"))
        self.assertEqual(help_for(FIELDS[0], "fr"), help_for(FIELDS[0], "en"))


if __name__ == "__main__":
    unittest.main()

"""Device option names/help follow actual native capabilities and live mode updates."""
from __future__ import annotations

import ast
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_061b8_native_target_budget.py"))
model, PACKAGE = base["model"], base["PACKAGE"]
target = base["native_target"]
names = importlib.import_module(PACKAGE + ".equipment_name_catalog")
help_module = importlib.import_module(PACKAGE + ".equipment_help")
mode_names = importlib.import_module(PACKAGE + ".operating_mode_catalog")


def extract(filename, wanted, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
             and node.name in wanted]
    assert {node.name for node in nodes} == set(wanted)
    exec(compile(ast.Module(body=[ast.parse("from __future__ import annotations").body[0], *nodes],
                            type_ignores=[]), filename, "exec"), namespace)


ns = {"__package__": PACKAGE, "model": model, "equipment": model,
      "callback": lambda fn: fn, "DOMAIN": base["const"].DOMAIN,
      "localized_equipment_name": names.localized_equipment_name,
      "equipment_configuration_help": help_module.equipment_configuration_help,
      "SwitchEntity": object, "EntityCategory": N(CONFIG="config")}
extract("equipment_entity.py", ("EquipmentEntity",), ns)
extract("switch.py", ("_device_option_metadata", "EquipmentNativeFullOutputSwitch"), ns)


class OptionMetadata(unittest.TestCase):
    def appliance(self, modes, *, features=None, kind="heat"):
        runtime = base["appliance"](kind)
        if kind != "humidify":
            runtime.state.attributes["hvac_modes"] = ["off", *modes]
            runtime.state.attributes["supported_features"] = (
                model.TEMP | model.HUMIDITY if features is None else features)
        return runtime

    def option(self, runtime):
        return ns["EquipmentNativeFullOutputSwitch"](runtime.manager, runtime.spec)

    def test_titles_list_only_native_target_capable_modes(self):
        cases = [
            (("heat",), model.TEMP, ("heat",)),
            (("heat", "cool"), model.TEMP, ("heat", "cool")),
            (("dry", "fan_only"), model.HUMIDITY | model.FAN, ("dry",)),
            (("heat", "cool", "dry"), model.TEMP | model.HUMIDITY, ("heat", "cool", "dry")),
            (("heat", "cool"), model.RANGE, ()),
            (("fan_only",), model.FAN, ()),
        ]
        for modes, features, expected in cases:
            with self.subTest(modes=modes, features=features):
                runtime = self.appliance(modes, features=features)
                option = self.option(runtime)
                attributes = option.extra_state_attributes
                self.assertEqual(target.configuration_modes(runtime.manager, runtime.spec), expected)
                self.assertEqual(attributes["native_full_output_modes"], list(expected))
                self.assertEqual(attributes["setting_label"], names.native_full_output_label(expected, "en"))
                self.assertTrue(option.name.endswith(attributes["setting_label"]))
                self.assertEqual(runtime.calls, [], "Reading an option must never operate its device")

    def test_humidifier_auto_is_presented_as_humidifying(self):
        runtime = self.appliance((), kind="humidify")
        option = self.option(runtime)
        self.assertEqual(target.configuration_modes(runtime.manager, runtime.spec), ("humidify",))
        self.assertEqual(option.extra_state_attributes["native_full_output_modes"], ["humidify"])
        self.assertIn(mode_names.operating_mode_label("humidify", "en"), option.name)
        self.assertNotIn("(Automatic)", option.name)

    def test_name_and_help_follow_supported_mode_changes_without_new_identity(self):
        runtime = self.appliance(("heat", "cool"), features=model.TEMP)
        option = self.option(runtime)
        unique_id = option._attr_unique_id
        initial = option.name
        runtime.state.attributes["hvac_modes"] = ["off", "heat"]
        self.assertNotEqual(option.name, initial)
        self.assertEqual(option.extra_state_attributes["native_full_output_modes"], ["heat"])
        self.assertEqual(option._attr_unique_id, unique_id)
        self.assertNotIn(mode_names.operating_mode_label("cool", "en"), option.name)
        self.assertEqual(runtime.calls, [])

    def test_title_and_device_help_use_the_requested_locale(self):
        runtime = self.appliance(("dry", "fan_only"), features=model.HUMIDITY | model.FAN)
        runtime.state.attributes["fan_modes"] = ["low", "medium", "high"]
        option = self.option(runtime)
        for locale in names.EQUIPMENT_TRANSLATED_NAMES:
            with self.subTest(locale=locale):
                runtime.hass.config.language = locale
                attributes = option.extra_state_attributes
                expected = names.native_full_output_label(("dry",), locale)
                self.assertEqual(attributes["setting_label"], expected)
                self.assertTrue(option.name.endswith(expected))
                self.assertEqual(attributes["configuration_help"],
                    help_module.equipment_configuration_help("native_full_output", locale, modes=("dry",)))
                self.assertNotIn("timed_setpoint", str(attributes))

    def test_missing_native_bounds_do_not_fabricate_a_target_mode(self):
        runtime = self.appliance(("heat", "cool"), features=model.TEMP)
        option = self.option(runtime)
        runtime.state.attributes.pop("max_temp")
        self.assertEqual(target.configuration_modes(runtime.manager, runtime.spec), ())
        self.assertEqual(option.extra_state_attributes["native_full_output_modes"], [])
        self.assertNotIn("(", option.extra_state_attributes["setting_label"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

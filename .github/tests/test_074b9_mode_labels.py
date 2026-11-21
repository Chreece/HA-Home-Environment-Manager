"""Native mode-setting labels share reviewed translations and raw choices.

Run the production name helpers, metadata, entity names and select setters.
Only HA base classes and the final settings-write boundary are replaced.
"""
from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem_b9_mode_labels"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


def load(name):
    return importlib.import_module(PACKAGE + "." + name)


model = load("equipment_model")
names = load("equipment_name_catalog")
labels = load("equipment_mode_entities")
text = load("backend_text")
help_text = load("equipment_help")


class SelectBase:
    available = True


ns = {
    "__package__": PACKAGE,
    "model": model,
    "equipment": model,
    "DOMAIN": "environment_manager",
    "callback": lambda function: function,
    "localized_equipment_name": names.localized_equipment_name,
    "equipment_configuration_help": help_text.equipment_configuration_help,
    "presentation_languages": text.presentation_languages,
    "SelectEntity": SelectBase,
    "EntityCategory": N(CONFIG="config"),
}
for filename, class_name in (("equipment_entity.py", "EquipmentEntity"),
                             ("select.py", "EquipmentSelect")):
    tree = ast.parse((SOURCE / filename).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == class_name)
    future = ast.parse("from __future__ import annotations").body[0]
    exec(compile(ast.Module(body=[future, cls], type_ignores=[]), filename, "exec"), ns)


class ModeLabelTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.spec = model.ManagedDevice("unit", "room", "Unit", "physical", ("climate.unit",))
        self.state = N(state="dry", attributes={
            "hvac_modes": ["off", "heat", "cool", "dry"],
            "supported_features": model.TEMP | model.FAN | model.SWING | model.SWING_H,
            "fan_modes": ["low", "Turbo"],
            "swing_modes": ["off", "vertical"],
            "swing_horizontal_modes": ["Off", "Left/right"],
        })
        self.manager = N(
            hass=N(config=N(language="en"), states={"climate.unit": self.state}),
            settings={"language": "auto",
                      "climate_rooms": {"room": {"selected_devices": ["climate.unit"]}},
                      model.SETTINGS: {"unit": {"control_mode": "manual"}}},
            equipment=N(records={}, statuses={}, active_control_mode=lambda spec: "dry"),
        )
        self.writes = []

        async def write(spec, changes, *, operating_mode=None):
            self.writes.append((spec.identifier, changes.copy(), operating_mode))
            profiles = self.manager.settings[model.SETTINGS]
            profiles[spec.identifier] = model.persist_changes(
                profiles[spec.identifier], changes, operating_mode=operating_mode)

        self.manager.equipment.async_update = write

    def entity(self, key):
        return ns["EquipmentSelect"](self.manager, self.spec, key, operating_mode="dry")

    def test_all38_use_canonical_reviewed_labels_in_names_and_metadata(self):
        sources = {"fan_mode": "Fan mode", "swing_mode": "Swing mode",
                   "swing_horizontal_mode": "Horizontal swing mode"}
        memory = json.loads((ROOT / ".github/localization/backend_help.json").read_text())
        self.assertEqual(len(text.SUPPORTED_LANGUAGE_TAGS), 38)
        for key, source in sources.items():
            for locale in text.SUPPORTED_LANGUAGE_TAGS:
                with self.subTest(key=key, locale=locale):
                    expected = memory[source][locale]
                    self.manager.hass.config.language = locale
                    entity = self.entity(key)
                    self.assertTrue(entity.available)
                    self.assertTrue(entity.name.endswith(" · " + expected))
                    self.assertEqual(names.localized_equipment_name(key, locale), expected)
                    self.assertEqual(labels.setting_label(key, locale), expected)
                    self.assertEqual(entity.extra_state_attributes["setting_label"], expected)
                    self.assertEqual(entity.extra_state_attributes["setting_label_locales"][locale], expected)
                    if locale != "en":
                        self.assertNotEqual(expected, source)
        self.assertEqual(self.writes, [])

    def test_greek_names_and_native_channel_are_clear(self):
        self.manager.hass.config.language = "el"
        expected = {"fan_mode": "Αφύγρανση · Λειτουργία ανεμιστήρα",
                    "swing_mode": "Αφύγρανση · Λειτουργία ταλάντωσης",
                    "swing_horizontal_mode": "Αφύγρανση · Οριζόντια ταλάντωση"}
        for key, name in expected.items():
            self.assertEqual(self.entity(key).name, name)
        self.assertEqual(names.localized_equipment_name("fan_mode", "el", "Bedroom · "),
                         "Bedroom · Λειτουργία ανεμιστήρα")

    def test_server_name_and_viewer_metadata_keep_independent_languages(self):
        self.manager.hass.config.language = "de"
        self.manager.settings["language"] = "ja"
        entity = self.entity("fan_mode")
        self.assertEqual(entity.name, "Entfeuchten · Lüftermodus")
        attributes = entity.extra_state_attributes
        self.assertEqual(attributes["setting_label"], "ファンモード")
        self.assertEqual(attributes["setting_label_locales"], {
            "en": "Fan mode", "el": "Λειτουργία ανεμιστήρα",
            "de": "Lüftermodus", "ja": "ファンモード",
        })

    def test_region_and_script_aliases_keep_the_correct_translation(self):
        for alias, canonical in (("el-GR", "el"), ("pt_br", "pt-BR"),
                                 ("zh-TW", "zh-Hant"), ("zh-CN", "zh-Hans"),
                                 ("no", "nb"), ("fr-CA", "fr")):
            for key in ("fan_mode", "swing_mode", "swing_horizontal_mode"):
                self.assertEqual(names.localized_equipment_name(key, alias),
                                 names.localized_equipment_name(key, canonical))

    async def test_translated_labels_preserve_native_option_values_and_writes(self):
        self.manager.hass.config.language = "el"
        for key, options in (("fan_mode", ["low", "Turbo"]),
                             ("swing_mode", ["off", "vertical"]),
                             ("swing_horizontal_mode", ["Off", "Left/right"])):
            entity = self.entity(key)
            self.assertEqual(entity.options, options)
            await entity.async_select_option(options[-1])
            self.assertEqual(entity.current_option, options[-1])
            self.assertEqual(self.writes[-1], ("unit", {key: options[-1]}, "dry"))
            self.assertEqual(entity.extra_state_attributes["option_labels"], {})
        self.assertEqual(self.state.attributes["fan_modes"], ["low", "Turbo"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

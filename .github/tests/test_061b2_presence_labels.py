"""Presence labels describe the actual controller gate without changing values.

Exercise the production select identity/read/write methods and live presence
policy against local HA state/area fixtures. No registry or physical command
transport is used.
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
BASE = runpy.run_path(str(ROOT / ".github/tests/test_home_presence_authority.py"))
POLICY = BASE["occupancy"]
HELP = runpy.run_path(str(ROOT / "equipment_help.py"))["equipment_configuration_help"]
NAMES = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))
KEY = "presence_requirement"
OPTIONS = ("always", "occupied", "absent")


def _compile(nodes, namespace, filename):
    future = ast.parse("from __future__ import annotations").body[0]
    exec(compile(ast.Module(body=[future, *nodes], type_ignores=[]),
                 str(ROOT / filename), "exec"), namespace)


def selector_fixture(language="en"):
    model_tree = ast.parse((ROOT / "equipment_model.py").read_text())
    selects = next(ast.literal_eval(node.value)
                   for node in model_tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "DEVICE_SELECTS"
                           for target in node.targets))

    class Endpoint(N):
        pass

    model = N(DEVICE_SELECTS=selects, ManagedEndpoint=Endpoint,
              settings=lambda manager, _spec: manager.values)
    ns = {"model": model, "equipment": model, "DOMAIN": "environment_manager",
          "localized_equipment_name": NAMES["localized_equipment_name"],
          "EntityCategory": N(CONFIG="config"), "SelectEntity": type("SelectEntity", (), {})}
    identifier = next(node for node in model_tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == "device_identifier")
    _compile([identifier], ns, "equipment_model.py")
    model.device_identifier = ns["device_identifier"]
    for filename, name, methods in (
        ("equipment_entity.py", "EquipmentEntity", {"_equipment_init", "controller_settings", "_async_update_controller_settings"}),
        ("select.py", "EquipmentSelect", {"__init__", "options", "current_option", "async_select_option"}),
    ):
        node = next(node for node in ast.parse((ROOT / filename).read_text()).body
                    if isinstance(node, ast.ClassDef) and node.name == name)
        node.body = [item for item in node.body if isinstance(item, ast.Assign)
                     or (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and item.name in methods)]
        _compile([node], ns, filename)
    manager = N(values={KEY: "always"}, saved=[],
                hass=N(config=N(language=language),
                       states=N(get=lambda _entity: N(name="Living radiator"))))
    spec = Endpoint(identifier="entry_living_channel", name="Radiator",
                    physical_identifier="entry_living_device", source_device_id="native_device",
                    source_entities=("climate.living",), area_id="living")

    async def update(actual_spec, changes):
        manager.saved.append((actual_spec, dict(changes)))
        manager.values.update(changes)

    manager.equipment = N(async_update=update)
    return ns["EquipmentSelect"](manager, spec, KEY), manager, spec


class PresenceChoiceTests(unittest.TestCase):
    def test_clear_labels_for_user_languages_keep_distinct_meanings(self):
        expected = {
            "en": ("No room-presence restriction", "Only while room is occupied", "Only while room is empty"),
            "el": ("Χωρίς περιορισμό παρουσίας", "Μόνο με παρουσία στο δωμάτιο", "Μόνο σε άδειο δωμάτιο"),
            "de": ("Unabhängig von der Raumbelegung", "Nur bei belegtem Raum", "Nur bei leerem Raum"),
        }
        for locale, labels in expected.items():
            data = json.loads((ROOT / "translations" / f"{locale}.json").read_text())
            state = data["entity"]["select"]["equipment_presence_requirement"]["state"]
            with self.subTest(locale=locale):
                self.assertEqual(tuple(state[option] for option in OPTIONS), labels)
                # Each explanation names the exact visible choice on its own line.
                lines = HELP(KEY, locale).splitlines()
                for label in labels:
                    self.assertTrue(any(line.startswith(label + ":") for line in lines), label)

    def test_all_locales_keep_native_and_existing_room_choices_separate(self):
        paths = [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]
        self.assertEqual(len(paths), 39)
        for path in paths:
            data = json.loads(path.read_text())
            current = data["entity"]["select"]["equipment_presence_requirement"]["state"]
            legacy = data["selector"]["device_presence_requirement"]["options"]
            with self.subTest(path=path.name):
                self.assertEqual(tuple(current), OPTIONS)
                self.assertEqual(set(legacy), {"always", "room", "home"})
                self.assertEqual(len(set(current.values())), 3)
                self.assertEqual(legacy["always"], current["always"])
                self.assertEqual(legacy["room"], current["occupied"])
                self.assertNotEqual(legacy["home"], current["absent"])
                automatic = data["entity"]["select"]["equipment_control_mode"]["state"]["automatic"]
                self.assertNotEqual(current["always"], automatic)
                self.assertTrue(all(label.strip() and label not in OPTIONS for label in current.values()))
        source = json.loads((ROOT / "strings.json").read_text())
        english = json.loads((ROOT / "translations/en.json").read_text())
        self.assertEqual(source["entity"]["select"]["equipment_presence_requirement"],
                         english["entity"]["select"]["equipment_presence_requirement"])

    def test_production_select_preserves_identity_options_and_saved_values(self):
        for locale in ("en", "el", "de"):
            select, manager, spec = selector_fixture(locale)
            self.assertEqual(select.options, list(OPTIONS))
            self.assertEqual(select._attr_unique_id, spec.identifier + "_presence_requirement")
            self.assertEqual(select._attr_translation_key, "equipment_presence_requirement")
            self.assertEqual(select._attr_device_info["identifiers"], {
                ("environment_manager", spec.physical_identifier)})
            for option in OPTIONS:
                with self.subTest(locale=locale, option=option):
                    asyncio.run(select.async_select_option(option))
                    self.assertEqual(select.current_option, option)
                    self.assertEqual(manager.saved[-1], (spec, {KEY: option}))
            self.assertEqual(len(manager.saved), 3)

    def test_named_choices_match_live_room_and_home_evidence(self):
        cases = (
            ("home", "Living room", "on", (True, True, False)),
            # A room can be empty while someone is still at home. A selected
            # valid room list also overrides a contradictory local ON sensor.
            ("home", "Bathroom", "on", (True, False, True)),
            ("home", "unavailable", "unavailable", (True, False, False)),
            # Confirmed whole-home Away defeats an old occupied-room result.
            ("not_home", "Living room", "on", (True, False, True)),
        )
        for home, rooms, sensor, expected in cases:
            hass = BASE["Hass"]()
            hass.put(BASE["PERSON"], home)
            hass.put(BASE["ROOMS"], rooms)
            hass.put(BASE["MOTION"], sensor)
            plan = {"global_presence": BASE["room_config"](home_trackers=[BASE["PERSON"]]),
                    "known_presence_areas": [BASE["AREA"], "bath"],
                    "occupancy": "occupied", "away": "home"}
            room = {"occupancy_sensors": [BASE["MOTION"]]}
            for option, eligible in zip(OPTIONS, expected):
                with self.subTest(home=home, rooms=rooms, sensor=sensor, option=option):
                    actual, _reason = POLICY.live_device_permission(
                        hass, BASE["AREA"], room, plan, BASE["device"](option))
                    self.assertEqual(actual == "eligible", eligible)

    def test_no_presence_restriction_still_obeys_authorization_and_sleep(self):
        for option in OPTIONS:
            with self.subTest(option=option):
                self.assertEqual(POLICY.device_permission(
                    BASE["device"](option, auto_control=False), "occupied", "home", False),
                    ("held", "device_auto_control_disabled"))
                self.assertEqual(POLICY.device_permission(
                    BASE["device"](option, sleep_behavior="pause"), "occupied", "home", True),
                    ("held", "sleep_room_control_paused"))

    def test_missing_room_sensor_configuration_means_empty_not_unknown(self):
        hass = BASE["Hass"]()
        hass.put(BASE["PERSON"], "home")
        room = {"occupancy_sensors": []}
        plan = {"global_presence": {"home_trackers": [BASE["PERSON"]]},
                "known_presence_areas": [BASE["AREA"]]}
        for option, expected in zip(OPTIONS, (True, False, True)):
            with self.subTest(option=option):
                actual, _reason = POLICY.live_device_permission(
                    hass, BASE["AREA"], room, plan, BASE["device"](option))
                self.assertEqual(actual == "eligible", expected)

    def test_help_covers_unknown_away_protected_stop_and_existing_controller(self):
        english = HELP(KEY, "en")
        for meaning in ("Automatic and PID", "does not mean continuously ON",
                        "elsewhere at home", "Unknown room presence",
                        "whole-home Away", "minimum ON time", "command confirmation",
                        "Target demand, sleep and window"):
            self.assertIn(meaning, english)
        source = json.loads((ROOT / "full_config_help_core.json").read_text())[
            "device_settings.device_presence_requirement"]
        for locale in ("en", "el", "de"):
            data = json.loads((ROOT / "translations" / f"{locale}.json").read_text())
            for flow in ("config", "options"):
                self.assertEqual(data[flow]["step"]["device_settings"]["data_description"][
                    "device_presence_requirement"], source[locale])
            home_label = data["selector"]["device_presence_requirement"]["options"]["home"]
            self.assertIn(home_label, source[locale])
            # The old home selector is not silently redefined as empty-room operation.
            self.assertNotIn(data["entity"]["select"]["equipment_presence_requirement"][
                "state"]["absent"], source[locale])


if __name__ == "__main__":
    unittest.main()

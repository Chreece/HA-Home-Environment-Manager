"""Actual configuration entities: grouped names, help and stable identities.

Only Home Assistant transport/base classes are replaced. Production metadata,
entity constructors, state attributes and option setters are exercised. No
registry edit or actuator service is available to these tests.
"""
from __future__ import annotations

import ast
import asyncio
import copy
from datetime import time
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem116metadata"
pkg = ModuleType(PKG)
pkg.__path__ = [str(ROOT)]
sys.modules[PKG] = pkg
const = importlib.import_module(PKG + ".const")
metadata = importlib.import_module(PKG + ".settings_help")
names = importlib.import_module(PKG + ".settings_name_catalog")
equipment_help = importlib.import_module(PKG + ".equipment_help")


def production_nodes(filename, selected, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in selected:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in selected
                for target in node.targets):
            nodes.append(node)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), namespace)


controls = {"__name__": PKG + ".controls", "__package__": PKG,
            "DEFAULT_PROFILE_TARGETS": importlib.import_module(PKG + ".climate_strategy").DEFAULT_PROFILE_TARGETS}
production_nodes("device_controls.py", {
    "GLOBAL_ENV_NUMBERS", "GLOBAL_OCCUPANCY_NUMBERS", "AREA_ENV_NUMBERS",
    "CLIMATE_OPERATING_NUMBERS", "CLIMATE_POLICY_OPTIONS", "GLOBAL_POLICY_OPTIONS",
    "DIRECT_CONTROLLER_NUMBERS", "DEVICE_TARGET_NUMBERS", "PID_NUMBERS",
}, controls)


class Entity:
    _attr_entity_registry_enabled_default = True

    @property
    def name(self):
        return getattr(self, "_attr_name", None)

    @property
    def extra_state_attributes(self):
        return {"base_attribute": "preserved"}

    @property
    def unique_id(self):
        return self._attr_unique_id

    def async_write_ha_state(self):
        self.write_count = getattr(self, "write_count", 0) + 1


writes = []
calibrations = []


async def update_device_setting(manager, kind, key, value, **kwargs):
    writes.append((kind, key, value, kwargs))


async def recalculate(manager, area):
    calibrations.append(area)


ns = {**vars(const), **controls, "__name__": PKG + ".entities", "__package__": PKG,
      "SettingsMetadata": metadata.SettingsMetadata,
      "NumberEntity": Entity, "SelectEntity": Entity, "SwitchEntity": Entity,
      "ButtonEntity": Entity, "TimeEntity": Entity,
      "NumberMode": N(BOX="box"), "EntityCategory": N(CONFIG="config"),
      "callback": lambda method: method, "time": time,
      "update_device_setting": update_device_setting,
      "async_recalculate_mold_factor": recalculate,
      "climate_settings": lambda settings, area: settings.get("climate_rooms", {}).get(area, {}),
      "localized_room_pid_name": lambda key, locale: names.localized_setting_name(key, locale),
      "controller_device_info": lambda manager, area, source: {"identifiers": {(const.DOMAIN, source)}},
      "PROFILE_OPTIONS": ("auto", "comfort", "home", "away", "sleep", "eco")}
for filename, classes in {
    "number.py": {"ConfigNumber", "ShadeCoolingNumber", "ShadeIlluminanceNumber", "ShadeDeviceNumber"},
    "select.py": {"ConfigSelect", "TTSLanguageSelect", "ShadeWindowSelect", "ShadeIlluminanceSelect"},
    "switch.py": {"HomeSettingSwitch", "ShadeCoolingSwitch", "ShadeDeviceSwitch"},
    "button.py": {"AreaMoldCalibrationButton"}, "time.py": {"AreaScheduleTime"},
}.items():
    production_nodes(filename, classes, ns)


class MetadataTests(unittest.TestCase):
    def setUp(self):
        writes.clear()
        calibrations.clear()
        self.manager = N(settings={"climate_rooms": {"room": {}}, "mold_rooms": {
            "room": {"calibration_factor": 1.7, "critical_temperature_c": 13.2}}},
            hass=N(config=N(language="en"), states=N(get=lambda entity: None)),
            thresholds=const.DEFAULT_THRESHOLDS.copy())

    def test_bare_ten_minute_control_is_named_and_remains_same_setting(self):
        number = ns["ConfigNumber"](self.manager, "entry", None,
            "global_occupancy", "away_cooldown_minutes", (0, 240, 1, "min"))
        self.assertEqual(number.native_value, 10)
        self.assertEqual(number.unique_id, "entry_home_global_occupancy_away_cooldown_minutes")
        self.assertEqual(number._attr_translation_key, "global_occupancy_away_cooldown_minutes")
        self.assertEqual(number.name, "Home Occupancy · Away delay (min)")
        self.assertFalse(number._attr_has_entity_name)
        help_text = number.extra_state_attributes["configuration_help"]
        self.assertIn("only when no direct home trackers", help_text)
        self.assertIn("immediately", help_text)
        self.manager.settings["occupancy_global"] = {"away_cooldown_minutes": 27}
        self.assertEqual(number.native_value, 27)
        self.assertEqual(number.extra_state_attributes["base_attribute"], "preserved")

    def test_wind_help_explains_window_use_and_is_read_only_in_memory(self):
        number = ns["ConfigNumber"](self.manager, "entry", None,
            "global_threshold", "max_wind_kmh", (0, 200, 1, "km/h"))
        before = copy.deepcopy(self.manager.settings)
        with patch("builtins.open", side_effect=AssertionError("runtime file read")):
            for locale in ("en", "el", "de", "de-DE", "pt-BR", "unknown"):
                self.manager.hass.config.language = locale
                self.assertTrue(number.name)
                attrs = number.extra_state_attributes
                self.assertTrue(attrs["configuration_help"])
                self.assertTrue(attrs["setting_group"])
        self.assertEqual(self.manager.settings, before)
        self.assertEqual(writes, [])
        text = metadata.configuration_help("global_threshold_max_wind_kmh", "en")
        self.assertIn("window-ventilation", text)
        self.assertIn("km/h", text)
        self.assertIn("stronger wind", text)

    def test_occupancy_name_options_and_storage_identity(self):
        self.manager.settings["occupancy_global"] = {"home_policy": "all_home"}
        select = ns["ConfigSelect"](self.manager, "entry", None, "global_policy",
            ("any_home", "all_home"), setting_key="home_policy")
        self.assertEqual(select.name, "Home Occupancy")
        self.assertEqual(select.current_option, "all_home")
        self.assertEqual(select.unique_id, "entry_home_global_policy_home_policy")
        self.assertIn("same rule", select.extra_state_attributes["configuration_help"])
        self.manager.hass.config.language = "el"
        self.assertEqual(select.name, "Σπίτι - Παρουσία")
        asyncio.run(select.async_select_option("any_home"))
        self.assertEqual(writes, [("global_policy", "home_policy", "any_home",
                                  {"area": None, "entity_id": None})])
        self.assertEqual(select._attr_options, ["any_home", "all_home"])

    def test_sleep_controls_have_distinct_names_and_purposes(self):
        values = [("area_environment", "sleep_room", "Noise · "),
                  ("climate_operating", "sleep_active", "Sleep · Sleeping now"),
                  ("climate_operating", "sleep_schedule_enabled", "Sleep · Use schedule")]
        controls = []
        for kind, key, prefix in values:
            switch = ns["HomeSettingSwitch"](self.manager, "entry", key, kind=kind, area="room")
            self.assertTrue(switch.name.startswith(prefix), switch.name)
            self.assertEqual(switch.unique_id, f"entry_area_room_{kind}_{key}")
            self.assertTrue(switch.extra_state_attributes["configuration_help"])
            controls.append(switch.extra_state_attributes["configuration_help"])
        self.assertIn("22:00–07:00", controls[0])
        self.assertIn("does not activate", controls[0])
        self.assertIn("Off does not force awake", controls[1])
        self.assertEqual(len(set(controls)), 3)

    def test_mold_button_keeps_action_and_calibration_snapshot(self):
        button = ns["AreaMoldCalibrationButton"](self.manager, "entry", "room")
        self.assertEqual(button.name, "Mold · Recalculate calibration factor")
        self.assertEqual(button.unique_id, "entry_area_room_mold_recalibrate")
        attrs = button.extra_state_attributes
        self.assertEqual(attrs["calibration_factor"], 1.7)
        self.assertEqual(attrs["measured_cold_surface_c"], 13.2)
        self.assertEqual(attrs["status"], "calibrated")
        self.assertIn("does not remeasure", attrs["configuration_help"])
        self.assertIn("not a new validity rule", attrs["configuration_help"])
        asyncio.run(button.async_press())
        self.assertEqual(calibrations, ["room"])
        self.assertEqual(writes, [])

    def test_time_and_dynamic_source_controls_preserve_identity(self):
        clock = ns["AreaScheduleTime"](self.manager, "entry", "room", "sleep_start")
        self.assertEqual(clock.unique_id, "entry_area_room_climate_sleep_start")
        self.assertEqual(clock.native_value, time(22))
        self.assertEqual(clock.name, "Sleep · Start time (local)")
        self.assertIn("Use schedule", clock.extra_state_attributes["configuration_help"])
        self.manager.hass.states.get = lambda entity: N(name="Kitchen extractor")
        fan = ns["ConfigNumber"](self.manager, "entry", "room", "device_target",
                                "fan_speed_percent", (0, 100, 1, "%"), entity_id="fan.kitchen")
        self.assertEqual(fan.unique_id, "entry_area_room_device_target_fan_kitchen_fan_speed_percent")
        self.assertEqual(fan.name, "Fan · Kitchen extractor · Target speed (%)")
        self.assertIn("extraction or filtration", fan.extra_state_attributes["configuration_help"])
        self.manager.hass.states.get = lambda entity: N(name="Living room shade")
        cover = ns["ShadeWindowSelect"](self.manager, "entry", "room", "cover.living")
        self.assertEqual(cover.name, "Shading · Living room shade · Associated window contact")
        self.assertEqual(cover.unique_id, "entry_area_room_shade_cover_living_window")

    def test_all_runtime_static_config_keys_have_native_help(self):
        key_sets = {
            "global_environment": controls["GLOBAL_ENV_NUMBERS"],
            "global_occupancy": controls["GLOBAL_OCCUPANCY_NUMBERS"],
            "area_area_environment": controls["AREA_ENV_NUMBERS"],
            "area_climate_operating": controls["CLIMATE_OPERATING_NUMBERS"],
            "area_pid": controls["PID_NUMBERS"],
            "area_direct_tuning": controls["DIRECT_CONTROLLER_NUMBERS"],
            "area_climate_policy": controls["CLIMATE_POLICY_OPTIONS"],
            "home_global_policy": controls["GLOBAL_POLICY_OPTIONS"],
        }
        expected = {f"{prefix}_{key}" for prefix, keys in key_sets.items() for key in keys}
        expected |= {f"global_threshold_{key}" for key in const.DEFAULT_THRESHOLDS}
        for key in expected:
            self.assertIn(key, metadata.SETTING_HELP)
        self.assertEqual(set(metadata.SETTING_HELP), set(names.SETTING_GROUPS))
        for key, entry in metadata.SETTING_HELP.items():
            self.assertTrue({"en", "el", "de"} <= set(entry) <= set(names.SETTING_NAMES), key)
            self.assertTrue(all(len(text) > 60 for text in entry.values()), key)
            self.assertEqual(metadata.configuration_help(key, "unsupported"), entry["en"])

    def test_all_catalog_names_states_and_attribute_labels_are_synchronized(self):
        paths = [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]
        self.assertEqual(len(paths), 39)
        for path in paths:
            locale = "en" if path.name == "strings.json" else path.stem
            catalog = json.loads(path.read_text())
            for domain in ("number", "select", "switch", "button", "time"):
                for key, entry in catalog["entity"][domain].items():
                    self.assertTrue(entry["state_attributes"]["configuration_help"]["name"])
                    if key.startswith("equipment_"):
                        continue
                    self.assertEqual(names.localized_setting_name(key, locale), entry["name"], (locale, key))
                    self.assertTrue(names.localized_setting_group(key, locale), (locale, key))
                    self.assertIn(key, metadata.SETTING_HELP)
            for key in ("home_global_policy_home_policy", "area_climate_policy_away_policy"):
                state = catalog["entity"]["select"][key]["state"]
                self.assertEqual(set(state), {"any_home", "all_home"})
                self.assertNotEqual(state["any_home"], "any_home")
                self.assertNotEqual(state["all_home"], "all_home")
            self.assertIn("auto", catalog["entity"]["select"]["area_manual_profile"]["state"])
            self.assertNotIn("none", catalog["entity"]["select"]["area_manual_profile"]["state"])
            # Forms cannot retain the former all-home veto or noise/climate ambiguity.
            for flow in ("options", "config"):
                general = catalog[flow]["step"]["general_settings"]
                self.assertEqual(general["data_description"]["general_home_policy"],
                    metadata.configuration_help("home_global_policy_home_policy", locale))

    def test_real_attribute_overrides_merge_setting_help(self):
        # Cover and PMV subclasses have their own attributes. Their return paths
        # must preserve the metadata inherited from the actual production mixin.
        for file, class_names in {
            "switch.py": ("HomeSettingSwitch", "ShadeCoolingSwitch", "ShadeDeviceSwitch"),
            "select.py": ("ConfigSelect", "ShadeIlluminanceSelect", "ShadeWindowSelect"),
            "button.py": ("AreaMoldCalibrationButton",),
        }.items():
            tree = ast.parse((ROOT / file).read_text())
            for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in class_names):
                method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "extra_state_attributes")
                returns = [n.value for n in ast.walk(method) if isinstance(n, ast.Return)]
                for value in returns:
                    self.assertIn("super().extra_state_attributes", ast.unparse(value), (file, cls.name))

    def test_equipment_specific_help_covers_exposed_fields(self):
        # Source-derived keys include every equipment entity initialized with a
        # literal key plus number/select catalog definitions in the model.
        keys = {"control_mode", "resume", "climate", "pause_on_window_open",
                "announce_device_errors", "sensor_verified", "honor_timed_setpoint",
                "quiet_sleep", "quiet_occupied", "quiet_percentage", "quiet_fan_mode",
                "power_switch_entity", "power_switch_cooldown_seconds", "particle_cadr_m3h",
                "pid_apply_calibration", "pid_apply_fan_capacity", "pid_review_approve",
                "pid_review_discard", "presence_requirement", "sleep_behavior", "fan_purpose"}
        # Timed-setpoint's exact key is taken from its source, avoiding an alias.
        tree = ast.parse((ROOT / "switch.py").read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EquipmentTimedSetpointSwitch")
        keys.discard("honor_timed_setpoint")
        for node in ast.walk(cls):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "_equipment_init":
                keys.add(ast.literal_eval(node.args[-1]))
        for key in keys:
            self.assertIn(key, equipment_help.HELP)
            for locale in ("en", "el", "de"):
                self.assertGreater(len(equipment_help.equipment_configuration_help(key, locale)), 60)
        self.assertNotEqual(equipment_help.equipment_configuration_help("quiet_sleep"),
                            equipment_help.equipment_configuration_help("power_switch_entity"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

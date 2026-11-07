"""Operating profiles use real capabilities and retain one physical owner.

Exercises the production model/storage helpers with current native state and
saved identity evidence.  There are no hardware services or registry writes.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
package = ModuleType("hem061b7_modes")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
model = importlib.import_module(package.__name__ + ".equipment_model")
activation = importlib.import_module(package.__name__ + ".device_activation")


class ModeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.spec = model.ManagedDevice("unit", "room", "Room unit", "physical", ("climate.unit",))
        self.states = {"climate.unit": N(state="off", attributes={
            "hvac_modes": ["off", "heat", "cool", "dry", "fan_only", "auto", "heat_cool"],
            "supported_features": model.TEMP | model.FAN,
            "fan_modes": ["low", "medium", "high"],
            "min_temp": 10, "max_temp": 32,
            "min_humidity": 30, "max_humidity": 75,
        })}
        self.raw = {"control_mode": "automatic", "kp": 8, "requested_mode": "heat",
                    "profile_targets": {"manual": {"heat": 21, "cool": 26, "humidity": 60}},
                    "_native_authorization": {"version": 2, "physical": "unchanged"},
                    "min_on_seconds": 600, "min_off_seconds": 600}
        self.manager = N(settings={
            "climate_rooms": {"room": {"selected_devices": ["climate.unit"]}},
            model.SETTINGS: {"unit": self.raw},
        }, hass=N(states=self.states), equipment=N(records={}, active_control_mode=lambda spec: "heat"))
        self.manager._device_hierarchy = {"controllers": {"unit": {"spec": self.spec}}}

    def save(self, changes, mode=None):
        saved = model.persist_changes(self.raw, changes, operating_mode=mode)
        self.manager.settings[model.SETTINGS]["unit"] = self.raw = saved
        return saved

    def test_negative_temperature_override_uses_actual_native_bounds(self):
        self.states["climate.unit"].attributes.update(min_temp=-10, max_temp=32)
        self.save({"control_mode": "manual", "profile_targets": {"manual": {"heat": -3}}}, "heat")
        cfg = model.settings_for_mode(self.manager, self.spec, "heat")
        cap = model.capabilities(self.manager, self.spec)
        self.assertEqual(model.targets(self.manager, self.spec, cap, cfg, {}, mold_protection=False)["heat"], -3)

    def test_legacy_read_has_no_storage_or_identity_side_effect(self):
        before = deepcopy(self.manager.settings)
        config = model.settings(self.manager, self.spec)
        self.assertEqual(config["kp"], 8)
        self.assertNotIn("operating_mode", config)
        self.assertEqual(self.manager.settings, before)
        self.assertEqual(model.specs(self.manager), (self.spec,))
        config["profile_targets"]["manual"]["heat"] = 99
        config["_native_authorization"]["physical"] = "changed"
        self.assertEqual(self.manager.settings, before)
        other = model.base_settings(N(settings={}, hass=self.manager.hass), self.spec)
        other["profile_targets"]["manual"] = {"heat": 99}
        self.assertEqual(model.DEFAULTS["profile_targets"], {})

    def test_inactive_edit_retains_active_context_and_physical_owner(self):
        self.save({"control_mode": "pid", "kp": 12}, "heat")
        active = model.settings(self.manager, self.spec)
        before_heat = deepcopy(self.raw["mode_settings"]["heat"])
        self.save({"control_mode": "off", "kp": 2, "profile_targets": {"away": {"cool": 28}}}, "cool")
        self.assertEqual(model.settings(self.manager, self.spec), active)
        self.assertEqual(self.raw["mode_settings"]["heat"], before_heat)
        self.assertEqual(self.raw["requested_mode"], "heat")
        self.assertEqual(self.raw["kp"], 8)
        self.assertEqual(model.specs(self.manager), (self.spec,))
        self.assertNotIn("mode_settings", active)
        self.assertNotIn("mode_settings_version", active)
        self.assertEqual(active["operating_mode"], "heat")
        self.assertEqual(model.settings_for_mode(self.manager, self.spec, "cool")["control_mode"], "off")

    def test_shared_dwell_and_authority_are_not_copied_into_mode(self):
        self.save({"kp": 3, "min_on_seconds": 700, "pause_on_window_open": False}, "dry")
        self.assertEqual(self.raw["mode_settings"]["dry"], {"kp": 3})
        for direction in ("heat", "cool", "dry"):
            config = model.settings_for_mode(self.manager, self.spec, direction)
            self.assertEqual(config["min_on_seconds"], 700)
            self.assertFalse(config["pause_on_window_open"])
            self.assertEqual(config["_native_authorization"], self.raw["_native_authorization"])

    def test_explicit_off_does_not_erase_active_direction_profile(self):
        self.save({"control_mode": "pid", "kp": 12}, "heat")
        self.save({"requested_mode": "off"})
        effective = model.settings(self.manager, self.spec)
        self.assertEqual((effective["operating_mode"], effective["requested_mode"], effective["kp"]),
                         ("heat", "off", 12))
        self.assertEqual(model.settings_for_mode(self.manager, self.spec, "heat")["requested_mode"], "heat")

    def test_no_active_hook_does_not_guess_direction_from_off_state(self):
        self.save({"control_mode": "pid", "kp": 12}, "cool")
        self.manager.equipment.active_control_mode = lambda spec: None
        config = model.settings(self.manager, self.spec)
        self.assertNotIn("operating_mode", config)
        self.assertEqual(config["control_mode"], "automatic")
        self.assertEqual(config["requested_mode"], "heat")

    def test_native_auto_does_not_advertise_directional_pid(self):
        self.assertEqual(model.operating_modes(self.manager, self.spec),
                         ("heat", "cool", "dry", "fan_only", "auto", "heat_cool"))
        for mode in ("auto", "heat_cool"):
            descriptor = model.mode_descriptor(self.manager, self.spec, mode)
            self.assertFalse(descriptor["pid_supported"])
            self.assertNotIn("pid", descriptor["control_modes"])
            self.assertNotIn("kp", descriptor["number_fields"])
            self.assertEqual(descriptor["target_keys"], ("heat", "cool"))
        self.states["climate.unit"].attributes["hvac_modes"] = ["off", "auto"]
        self.assertEqual(model.operating_modes(self.manager, self.spec), ("auto",))
        self.assertIsNone(model.mode_descriptor(self.manager, self.spec, "heat"))

    def test_legacy_pid_has_a_valid_inert_native_auto_profile_without_rewriting_storage(self):
        self.raw["control_mode"] = "pid"
        before = deepcopy(self.raw)
        for mode in ("auto", "heat_cool"):
            config = model.settings_for_mode(self.manager, self.spec, mode)
            self.assertEqual(config["control_mode"], "existing")
            self.assertIn(config["control_mode"], model.mode_control_modes(self.manager, self.spec, mode))
            self.assertEqual(config["control_mode_reason"], "unsupported_for_operating_mode")
        self.assertEqual(self.raw, before)
        self.assertEqual(model.settings_for_mode(self.manager, self.spec, "heat")["control_mode"], "pid")
        self.save({"control_mode": "automatic"}, "auto")
        self.assertEqual(model.settings_for_mode(self.manager, self.spec, "auto")["control_mode"], "automatic")
        self.assertEqual(self.raw["control_mode"], "pid")

    def test_dry_and_multimode_fan_have_independent_actual_parameters(self):
        dry = model.mode_descriptor(self.manager, self.spec, "dry")
        self.assertTrue(dry["humidity"])
        self.assertTrue(dry["pid_supported"])
        self.assertFalse(dry["native_target"], "DRY is not proof of SET_HUMIDITY")
        self.assertEqual(dry["target_keys"], ("humidity",))
        self.assertEqual(dry["metric"], "humidity")
        fan = model.mode_descriptor(self.manager, self.spec, "fan_only")
        self.assertTrue(fan["pid_supported"])
        self.assertEqual(fan["target_keys"], ())
        self.assertEqual(fan["metric"], "air_quality")
        self.assertNotIn("min_on_seconds", dry["number_fields"])
        self.assertNotIn("pid_capacity_stage_3", dry["number_fields"])
        self.assertIn("pid_capacity_stage_2", dry["number_fields"])

    def test_humidifier_and_dehumidifier_have_correct_physical_direction(self):
        for device_class, logical, native, increasing in (
                ("humidifier", "humidify", "auto", True),
                ("dehumidifier", "dry", "dry", False)):
            spec = model.ManagedDevice("humidity", "room", "Humidity", "h", ("humidifier.unit",))
            self.manager.settings["climate_rooms"]["room"]["selected_devices"].append("humidifier.unit")
            self.states["humidifier.unit"] = N(state="off", attributes={"device_class": device_class})
            self.assertEqual(model.operating_modes(self.manager, spec), (logical,))
            descriptor = model.mode_descriptor(self.manager, spec, logical)
            self.assertEqual(descriptor["native_mode"], native)
            self.assertEqual(descriptor["increasing"], increasing)
            self.assertTrue(descriptor["native_target"])
            self.assertIn("pid", descriptor["control_modes"])

    def test_offline_editor_requires_exact_saved_physical_identity(self):
        cap = model.capabilities(self.manager, self.spec)
        self.manager.equipment.records["unit"] = {
            "area": "room", "source_device_id": "physical", "sources": ["climate.unit"],
            "capabilities": asdict(cap),
        }
        identity = {"version": 2, "area": "room", "physical_device": "physical",
                    "sources": [["climate.unit", "registry-id", "native-unique-id"]]}
        self.manager.equipment.records["unit"]["capabilities_authority"] = deepcopy(identity)
        identity_patch = patch.object(activation, "authority_context", return_value=identity)
        identity_patch.start()
        self.addCleanup(identity_patch.stop)
        self.states.clear()
        self.assertEqual(model.mode_capabilities(self.manager, self.spec), cap)
        self.assertIn("dry", model.operating_modes(self.manager, self.spec))
        for key, value in (("area", "other"), ("source_device_id", "replacement"),
                           ("sources", ["climate.someone_else"])):
            record = self.manager.equipment.records["unit"]
            original = record[key]
            record[key] = value
            self.assertIsNone(model.mode_capabilities(self.manager, self.spec))
            record[key] = original
        identity["sources"][0][2] = "replacement-unique-id"
        self.assertIsNone(model.mode_capabilities(self.manager, self.spec))
        identity["sources"][0][2] = "native-unique-id"
        self.manager.settings["climate_rooms"]["room"]["selected_devices"] = []
        self.assertIsNone(model.mode_capabilities(self.manager, self.spec))

    def test_live_withdrawal_does_not_reintroduce_cached_modes(self):
        cap = model.capabilities(self.manager, self.spec)
        self.manager.equipment.records["unit"] = {
            "area": "room", "source_device_id": "physical", "sources": ["climate.unit"],
            "capabilities": asdict(cap),
        }
        self.states["climate.unit"].attributes["hvac_modes"] = ["off", "cool"]
        self.assertEqual(model.operating_modes(self.manager, self.spec), ("cool",))
        self.states["climate.unit"].attributes["hvac_modes"] = []
        self.assertEqual(model.operating_modes(self.manager, self.spec), ())

    def test_calibration_and_capacity_evidence_never_cross_direction(self):
        self.raw.update(pid_process_gain=23, pid_last_calibration={"direction": "heat", "method": "imc_lambda"},
                        pid_fan_capacity_for_mode="heat", pid_capacity_stage_1=35,
                        pid_fan_capacity_models={"heat": {"direction": "heat", "proof": "h"},
                                                 "cool": {"direction": "cool", "proof": "c"}})
        heat = model.settings_for_mode(self.manager, self.spec, "heat")
        dry = model.settings_for_mode(self.manager, self.spec, "dry")
        self.assertEqual(heat["pid_process_gain"], 23)
        self.assertEqual(heat["pid_fan_capacity_models"], {"heat": {"direction": "heat", "proof": "h"}})
        self.assertEqual(dry["pid_process_gain"], 0)
        self.assertIsNone(dry["pid_last_calibration"])
        self.assertEqual(dry["pid_fan_capacity_models"], {})
        self.assertEqual(dry["pid_capacity_stage_1"], 0)
        self.save({"pid_process_gain": 7, "pid_last_calibration": {"method": "imc_lambda"}}, "dry")
        self.assertEqual(model.settings_for_mode(self.manager, self.spec, "dry")["pid_process_gain"], 7)
        self.assertEqual(model.settings_for_mode(self.manager, self.spec, "heat"), heat)

    def test_explicit_manual_calibration_does_not_inherit_legacy_adaptive_authority(self):
        self.raw.update(pid_calibration_method="adaptive_auto", pid_adaptation_mode="bounded")
        self.save({"pid_calibration_method": "manual"}, "dry")
        config = model.settings_for_mode(self.manager, self.spec, "dry")
        self.assertEqual(config["pid_calibration_method"], "manual")
        self.assertEqual(config["pid_adaptation_mode"], "disabled")
        heat = model.settings_for_mode(self.manager, self.spec, "heat")
        self.assertEqual(heat["pid_calibration_method"], "adaptive_auto")

    def test_scoped_six_profile_targets_use_only_their_metric_and_existing_bounds(self):
        limits = {"temperature_min_limit": 10, "temperature_max_limit": 32,
                  "humidity_min_limit": 30, "humidity_max_limit": 75}
        cap = model.capabilities(self.manager, self.spec)
        self.save({"profile_targets": {name: {"heat": 29, "cool": 14, "humidity": 40}
                                      for name in model.PROFILE_NAMES}}, "heat")
        with patch.object(model, "device_limits", return_value=limits):
            for profile in model.PROFILE_NAMES:
                cfg = model.settings_for_mode(self.manager, self.spec, "heat")
                cfg.update(control_mode="manual" if profile == "manual" else "automatic",
                           preset="none" if profile == "manual" else profile)
                result = model.targets(self.manager, self.spec, cap, cfg, {}, mold_protection=False)
                self.assertEqual(result["heat"], 29, profile)
                self.assertNotEqual(result["cool"], 14, profile)
                self.assertNotEqual(result["humidity"], 40, profile)
                # A directional heat target is independent of the cooling
                # profile, so crossing an inherited cool band is not rejected.
            legacy = model.base_settings(self.manager, self.spec)
            legacy.update(preset="home", profile_targets={"home": {"heat": 29}})
            self.assertNotEqual(model.targets(self.manager, self.spec, cap, legacy, {},
                                             mold_protection=False)["heat"], 29)

    def test_unknown_versions_and_nested_replacement_are_rejected(self):
        for version in (True, 2, "1"):
            with self.assertRaises(ValueError):
                model.persist_changes({"mode_settings_version": version}, {"kp": 2}, operating_mode="heat")
        with self.assertRaises(ValueError):
            model.persist_changes(self.raw, {"mode_settings": {"heat": {"kp": 100}}})
        with self.assertRaises(ValueError):
            model.persist_changes(self.raw, {"kp": 2}, operating_mode="invented")
        original = deepcopy(self.raw)
        result = model.persist_changes(self.raw, {"operating_mode": "heat", "kp": 2}, operating_mode="heat")
        self.assertNotIn("operating_mode", result)
        self.assertEqual(self.raw, original)


if __name__ == "__main__":
    unittest.main()

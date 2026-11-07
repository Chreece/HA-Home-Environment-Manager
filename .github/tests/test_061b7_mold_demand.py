"""Calibrated surface-RH demand reaches device targets and supply approval.

Production discovery/model/physics run with selected timestamped native
inputs. The fixture replaces HA registries only, never physics or the target
calculation. No network request or physical equipment is used.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import importlib
import math
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(Path(__file__).with_name("test_beta115_mold_readiness.py")))
PKG = fixture["pkg"].__name__
model = importlib.import_module(PKG + ".equipment_model")
mold = importlib.import_module(PKG + ".mold")
demand = importlib.import_module(PKG + ".mold_control_demand")
power = importlib.import_module(PKG + ".equipment_power_switch")
activation = importlib.import_module(PKG + ".device_activation")
occupancy = importlib.import_module(PKG + ".occupancy_policy")
NOW = fixture["NOW"]


class States(dict):
    def async_all(self, domain=None):
        return [state for state in self.values()
                if domain is None or state.domain == domain]


class MoldDemandTests(unittest.TestCase):
    def setUp(self):
        fixture["entities"].clear()
        self.states = States()
        self.hass = N(states=self.states)
        self.settings = {
            "areas": ["room"], "use_mold_indicator": True,
            "weather_entities": ["weather.home"],
            "room_sources": {"room": {"temperature": ["sensor.room_temperature"],
                                      "humidity": ["sensor.room_humidity"]}},
            "mold_rooms": {"room": {"calibration_factor": 1.63,
                "indoor_temperature_entity": "sensor.room_temperature",
                "indoor_temperature_entities": ["sensor.room_temperature"],
                "outdoor_weather_entity": "weather.home",
                "outdoor_weather_entities": ["weather.home"]}},
            "thresholds": {"indoor_mold": 70, "max_age_minutes": 90},
            "climate_rooms": {"room": {"selected_devices": ["humidifier.dryer"],
                "profiles": {"home": {"heat_c": 20, "cool_c": 26, "humidity": 60},
                             "comfort": {"heat_c": 20, "cool_c": 26, "humidity": 60}},
                "humidity_target": 60}},
        }
        # Use production constant names, so a renamed persisted key cannot
        # make the test silently exercise a disabled default path.
        const = fixture["constants"]
        self.settings[const.CONF_WEATHER] = self.settings.pop("weather_entities")
        self.settings[const.CONF_THRESHOLDS] = self.settings.pop("thresholds")
        self.threshold_key = const.CONF_THRESHOLDS
        self.weather_key = const.CONF_WEATHER
        self.manager = N(settings=self.settings, hass=self.hass)
        self.spec = model.ManagedDevice("dryer", "room", "Dryer", "dryer-device", ("humidifier.dryer",))
        self.cap = model.Capabilities("humidifier.dryer", "humidifier", ("off", "dry"),
                                      humidity=True, min_humidity=30, max_humidity=80,
                                      native_humidity_target=True)
        self.cfg = {**deepcopy(model.DEFAULTS), "control_mode": "automatic",
                    "requested_mode": "dry", "preset": "home", "pause_on_window_open": False}
        self.plan = {"away": "home", "occupancy": "unoccupied", "sleeping": False,
                     "window_safe": True}
        self.limits = {"temperature_min_limit": 5, "temperature_max_limit": 35,
                       "humidity_min_limit": 30, "humidity_max_limit": 80}
        self.sensor("sensor.room_temperature", 20, "temperature", "°C")
        self.sensor("sensor.room_humidity", 55.8, "humidity", "%")
        self.weather(5)
        self.limit_patch = patch.object(model, "device_limits", return_value=self.limits)
        self.limit_patch.start()
        self.addCleanup(self.limit_patch.stop)

    def sensor(self, entity, value, kind, unit, *, age=0, area="room", restored=False):
        self.states[entity] = N(entity_id=entity, domain="sensor", name=entity, state=str(value),
            attributes={"device_class": kind, "unit_of_measurement": unit, "restored": restored},
            last_updated=NOW-timedelta(minutes=age), last_reported=NOW-timedelta(minutes=age))
        fixture["entities"][entity] = N(area_id=area, device_id=None, platform="native",
                                       device_class=None, original_device_class=None)

    def weather(self, temperature, *, age=0):
        self.states["weather.home"] = N(entity_id="weather.home", domain="weather", name="Weather",
            state="cloudy", attributes={"temperature": temperature, "temperature_unit": "°C"},
            last_updated=NOW-timedelta(minutes=age), last_reported=NOW-timedelta(minutes=age))

    def info(self, cap=None, cfg=None):
        return model.humidity_demand(self.manager, self.spec, cap or self.cap, cfg or self.cfg, self.plan)

    def test_inverse_uses_same_unrounded_surface_model_including_condensation(self):
        goal = mold.indoor_humidity_for_surface_limit(20, 5, 1.63, 70)
        self.assertAlmostEqual(mold.estimate_mold(20, 5, goal, 1.63).surface_humidity, 70, places=1)
        self.assertLess(goal, 55.8)
        saturated = mold.estimate_mold(20, 5, 90, 1.63)
        self.assertEqual(saturated.surface_humidity, 100)
        self.assertNotAlmostEqual(goal, 90 * 70 / saturated.surface_humidity)
        for args in ((20, 5, True, 70), (None, 5, 1.63, 70), (20, 5, 0, 70),
                     (20, 5, 1.63, 0), (20, 5, float("nan"), 70), (20, 5, 1.63, True)):
            self.assertIsNone(mold.indoor_humidity_for_surface_limit(*args))

    def test_above_surface_limit_creates_drying_below_comfort_rh_target(self):
        before = deepcopy(self.settings)
        for method in ("automatic", "pid"):
            cfg = {**self.cfg, "control_mode": method}
            info = self.info(cfg=cfg)
            self.assertTrue(info["mold_protection_required"])
            self.assertGreater(info["mold_surface_rh"], 70)
            self.assertEqual(info["reason"], "mold_above_limit")
            self.assertEqual(info["requested_humidity_target"], 60)
            self.assertLess(info["effective_humidity_target"], 55.8)
            target = model.targets(self.manager, self.spec, self.cap, cfg, self.plan)
            self.assertEqual(target["humidity"], info["effective_humidity_target"])
            self.assertTrue(power.output_required(self.cap, target, {"humidity": 55.8},
                method=method, requested_mode="dry", fan_purpose=None, plan=self.plan))
            self.assertEqual(model.targets(self.manager, self.spec, self.cap, cfg, self.plan,
                                           mold_protection=False)["humidity"], 60)
        self.assertEqual(self.settings, before)

    def test_manual_targets_do_not_silently_rewrite_automatic_policy(self):
        cfg = {**self.cfg, "control_mode": "manual", "preset": "none",
               "profile_targets": {"manual": {"humidity": 60}}}
        self.assertEqual(model.targets(self.manager, self.spec, self.cap, cfg, self.plan)["humidity"], 60)
        self.assertTrue(self.info(cfg=cfg)["mold_protection_required"])

    def test_native_integer_target_stays_below_surface_limit_and_dry_pwm_keeps_precision(self):
        info = self.info()
        exact = info["mold_required_humidity_target"]
        self.assertEqual(info["effective_humidity_target"], math.floor(exact))
        self.assertLessEqual(mold.estimate_mold(20, 5, info["effective_humidity_target"], 1.63).surface_humidity, 70)
        dry = model.Capabilities("climate.dry", "climate", ("off", "dry"), humidity=True)
        self.assertAlmostEqual(self.info(cap=dry)["effective_humidity_target"], exact)

    def test_limits_remain_authoritative_with_explicit_unattainable_reason(self):
        self.limits["humidity_min_limit"] = 60
        info = self.info()
        self.assertEqual(info["effective_humidity_target"], 60)
        self.assertTrue(info["mold_target_limited"])
        self.assertEqual(info["status"], "mold_target_blocked_by_limits")
        self.assertTrue(info["mold_protection_required"])
        self.assertEqual(info["mold_target_limit_reason"], "humidity_minimum_limit")

    def test_stricter_existing_target_survives_mold_limit(self):
        cfg = {**self.cfg, "operating_mode": "dry", "profile_targets": {"home": {"humidity": 40}}}
        info = self.info(cfg=cfg)
        self.assertEqual(info["requested_humidity_target"], 40)
        self.assertEqual(info["effective_humidity_target"], 40)
        self.assertFalse(info["mold_target_active"])

    def test_recovery_keeps_calibrated_upper_bound_for_humidification(self):
        self.sensor("sensor.room_humidity", 40, "humidity", "%")
        humidifier = replace(self.cap, modes=("off", "auto"), humidifying=True)
        info = self.info(cap=humidifier)
        self.assertFalse(info["mold_protection_required"])
        self.assertEqual(info["status"], "within_mold_limit")
        self.assertLess(info["effective_humidity_target"], 60)
        self.assertEqual(info["target_provenance"], "calibrated_surface_rh_limit")

    def test_current_threshold_changes_target_without_saving_comfort_target(self):
        target70 = self.info()["effective_humidity_target"]
        self.settings[self.threshold_key]["indoor_mold"] = 80
        self.assertGreater(self.info()["effective_humidity_target"], target70)
        self.settings[self.threshold_key]["indoor_mold"] = 95
        self.assertFalse(self.info()["mold_protection_required"])
        self.assertEqual(self.info()["effective_humidity_target"], 60)

    def test_stale_restored_or_moved_feedback_never_creates_mold_demand(self):
        for sensor, kind, unit, value in (("sensor.room_humidity", "humidity", "%", 55.8),
                                          ("sensor.room_temperature", "temperature", "°C", 20)):
            for bad in ({"age": 11}, {"restored": True}, {"area": "other"}):
                with self.subTest(sensor=sensor, bad=bad):
                    self.sensor(sensor, value, kind, unit, **bad)
                    info = self.info()
                    self.assertFalse(info["mold_protection_required"])
                    self.assertEqual(info["status"], "inputs_unavailable")
                    self.assertEqual(info["effective_humidity_target"], 60)
                    self.sensor(sensor, value, kind, unit)
        self.weather(5, age=91)
        self.assertFalse(self.info()["mold_protection_required"])
        self.assertIn("outdoor_temperature", self.info()["missing_inputs"])

    def test_selected_source_changes_require_recalibration(self):
        original = deepcopy(self.settings)
        self.settings["room_sources"]["room"]["temperature"] = ["sensor.other_temperature"]
        self.sensor("sensor.other_temperature", 20, "temperature", "°C")
        self.assertEqual(self.info()["status"], "calibration_sources_changed")
        self.settings.clear()
        self.settings.update(original)
        self.settings[self.weather_key] = ["weather.changed"]
        self.assertEqual(self.info()["status"], "calibration_sources_changed")

    def test_reordered_or_duplicate_source_ids_keep_the_same_qualified_mean(self):
        self.sensor("sensor.second_temperature", 22, "temperature", "°C")
        self.states["weather.second"] = N(**{
            **vars(self.states["weather.home"]), "entity_id": "weather.second",
            "attributes": {"temperature": 9, "temperature_unit": "°C"},
        })
        temperatures = ["sensor.room_temperature", "sensor.second_temperature"]
        providers = ["weather.home", "weather.second"]
        self.settings["room_sources"]["room"]["temperature"] = temperatures[:]
        self.settings[self.weather_key] = providers[:]
        calibration = self.settings["mold_rooms"]["room"]
        calibration.update(indoor_temperature_entities=temperatures[:],
                           indoor_temperature_entity=None,
                           outdoor_weather_entities=providers[:],
                           outdoor_weather_entity=None)
        before = self.info()
        self.assertTrue(before["mold_protection_required"])
        self.assertEqual(before["indoor_temperature_c"], 21)
        self.assertEqual(before["outdoor_temperature_c"], 7)
        self.settings["room_sources"]["room"]["temperature"] = list(reversed(temperatures))
        self.settings[self.weather_key] = list(reversed(providers))
        for duplicate_saved_sources in (False, True):
            if duplicate_saved_sources:
                calibration["indoor_temperature_entities"].append(temperatures[0])
                calibration["outdoor_weather_entities"].append(providers[0])
            info = self.info()
            for key in ("status", "mold_protection_required", "indoor_temperature_c",
                        "outdoor_temperature_c", "mold_required_humidity_target",
                        "effective_humidity_target"):
                self.assertEqual(info[key], before[key], (duplicate_saved_sources, key))
        self.settings[self.weather_key] = ["weather.home"]
        self.assertEqual(self.info()["status"], "calibration_sources_changed")

    def test_legacy_weather_pin_is_not_replaced_by_reordered_provider_mean(self):
        calibration = self.settings["mold_rooms"]["room"]
        calibration.pop("outdoor_weather_entities")
        self.states["weather.second"] = N(**{
            **vars(self.states["weather.home"]), "entity_id": "weather.second",
            "attributes": {"temperature": 25, "temperature_unit": "°C"},
        })
        for providers in (["weather.home", "weather.second"],
                          ["weather.second", "weather.home"]):
            self.settings[self.weather_key] = providers
            info = self.info()
            self.assertTrue(info["mold_protection_required"])
            self.assertEqual(info["outdoor_temperature_c"], 5)
            self.assertEqual(info["weather_entities"], ["weather.home"])
        self.settings[self.weather_key] = ["weather.second"]
        self.assertEqual(self.info()["status"], "calibration_weather_not_selected")

    def test_missing_calibration_or_explicit_empty_sources_do_not_guess(self):
        original = deepcopy(self.settings["mold_rooms"]["room"])
        for value in (None, True, 0, float("nan")):
            self.settings["mold_rooms"]["room"]["calibration_factor"] = value
            self.assertEqual(self.info()["status"], "needs_calibration")
            self.assertEqual(self.info()["effective_humidity_target"], 60)
        self.settings["mold_rooms"]["room"] = original
        self.settings["room_sources"]["room"]["humidity"] = []
        self.assertEqual(self.info()["status"], "inputs_unavailable")
        self.assertEqual(self.info()["humidity_entities"], [])

    def test_only_valid_selected_included_humidity_sources_contribute(self):
        self.settings["room_sources"]["room"]["humidity"] += ["sensor.second_humidity", "sensor.stale_humidity"]
        self.sensor("sensor.second_humidity", 60, "humidity", "%")
        self.sensor("sensor.stale_humidity", 95, "humidity", "%", age=11)
        self.sensor("sensor.unselected_humidity", 10, "humidity", "%")
        info = self.info()
        self.assertAlmostEqual(info["indoor_humidity"], 57.9)
        self.assertEqual(info["humidity_entities"], ["sensor.room_humidity", "sensor.second_humidity"])

    def test_disabled_or_unmonitored_room_has_no_mold_control(self):
        self.settings["use_mold_indicator"] = False
        self.assertEqual(self.info()["effective_humidity_target"], 60)
        self.assertEqual(self.info()["status"], "disabled")
        self.settings["use_mold_indicator"] = True
        self.settings["areas"] = ["other"]
        self.assertEqual(self.info()["status"], "disabled")

    def test_verified_mold_blocks_humidifier_supply_before_native_feedback_read(self):
        humidifier = replace(self.cap, modes=("off", "auto"), humidifying=True)
        runtime = N(manager=self.manager, hass=self.hass,
                    measurements=lambda *args: self.fail("Humidification supply reached demand despite verified mold"))
        with patch.object(activation, "authorized", return_value=True), \
             patch.object(activation, "effective_device", return_value={}), \
             patch.object(occupancy, "live_device_permission", return_value=("eligible", None)), \
             patch.object(model, "plan_for", return_value=self.plan):
            self.assertIs(power.approved_demand(runtime, self.spec, self.cfg, humidifier), False)

    def test_multimode_fan_supply_uses_its_metric_and_directional_heat_has_no_cool_dependency(self):
        cap = model.Capabilities("climate.multi", "climate", ("off", "heat", "cool", "fan_only"),
                                  temperature=True)
        plan = {"air_actions": {"outdoor_air_verified": True,
                                 "thresholds": {"co2_operational_ppm": 1000,
                                                "pm25_short_term_action_ug_m3": 25}}}
        targets = {"heat": 29, "cool": 24}
        for method in ("automatic", "pid"):
            self.assertTrue(power.output_required(cap, targets, {"co2": 1300}, method=method,
                requested_mode="fan_only", fan_purpose="extraction", plan=plan))
            self.assertTrue(power.output_required(cap, targets, {"pm25": 35}, method=method,
                requested_mode="fan_only", fan_purpose="filtration", plan=plan))
            self.assertIsNone(power.output_required(cap, targets, {"temperature": 10}, method=method,
                requested_mode="fan_only", fan_purpose="filtration", plan=plan))
            self.assertTrue(power.output_required(cap, targets, {"temperature": 27}, method=method,
                requested_mode="heat", fan_purpose=None, plan=plan))
            self.assertFalse(power.output_required(cap, targets, {"temperature": 30}, method=method,
                requested_mode="heat", fan_purpose=None, plan=plan))
        self.assertFalse(power.output_required(cap, targets, {"pm25": 25}, method="pid",
            requested_mode="fan_only", fan_purpose="filtration", plan=plan))


if __name__ == "__main__":
    unittest.main()

"""Cold-surface measurement guidance from actual selected, current evidence.

No devices or network calls. Uses production discovery, source normalization,
mold calculations and dashboard serialization with lightweight HA registries.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
pkg = ModuleType("hem115moldtest")
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
logic = importlib.import_module(f"{pkg.__name__}.logic")
mold = importlib.import_module(f"{pkg.__name__}.mold")
constants = importlib.import_module(f"{pkg.__name__}.const")
dash = importlib.import_module(f"{pkg.__name__}.dashboard")

NOW = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
ha = ModuleType("homeassistant")
ha.__path__ = []
core = ModuleType("homeassistant.core")
core.HomeAssistant = core.State = object
helpers = ModuleType("homeassistant.helpers")
helpers.__path__ = []
util = ModuleType("homeassistant.util")
util.dt = N(utcnow=lambda: NOW)
entities, devices = {}, {}
registries = {}
for name in ("area_registry", "entity_registry", "device_registry"):
    module = ModuleType("homeassistant.helpers." + name)
    if name == "area_registry":
        registry = N(async_get_area=lambda area: N(name=area))
    else:
        values = entities if name == "entity_registry" else devices
        registry = N(async_get=values.get, entities=values)
    module.async_get = lambda hass, registry=registry: registry
    setattr(helpers, name, module)
    registries[module.__name__] = module
sys.modules.update({"homeassistant": ha, "homeassistant.core": core,
                    "homeassistant.helpers": helpers, "homeassistant.util": util,
                    **registries})
discovery = importlib.import_module(f"{pkg.__name__}.discovery")
sources = importlib.import_module(f"{pkg.__name__}.room_sources")

ROOM = logic.Room("room", "Room", (), (
    logic.Reading("sensor.rh", "Humidity", "humidity", 55.0),))


class MoldMeasurementReadiness(unittest.TestCase):
    def setUp(self):
        entities.clear()
        self.states = {}
        self.hass = N(states=N(get=self.states.get))
        self.settings = {"room_sources": {"room": {"temperature": ["sensor.room_temperature"]}}}
        self.sensor("sensor.room_temperature", 21)
        self.weather("weather.home", 5)

    def sensor(self, entity, value, *, area="room", age=0, unit="°C", platform="test"):
        self.states[entity] = N(entity_id=entity, state=str(value),
            attributes={"device_class": "temperature", "unit_of_measurement": unit},
            last_updated=NOW-timedelta(minutes=age), last_reported=NOW-timedelta(minutes=age))
        entities[entity] = N(area_id=area, device_id=None, platform=platform,
                             device_class=None, original_device_class=None)

    def weather(self, entity, temperature, *, age=0, unit="°C"):
        self.states[entity] = N(entity_id=entity, state="cloudy",
            attributes={"temperature": temperature, "temperature_unit": unit},
            last_updated=NOW-timedelta(minutes=age), last_reported=NOW-timedelta(minutes=age))

    def live(self, weather_ids=("weather.home",)):
        inside, evidence = sources.room_temperature_evidence(
            self.hass, self.settings, "room", age_minutes=90)
        weather = tuple(discovery.weather(self.hass, entity, 90) for entity in weather_ids)
        return mold.estimate_mold_for_room(ROOM, inside, weather, {}), evidence

    def test_temperature_contrast_is_conditional_not_calibration_or_health(self):
        reading, _ = self.live()
        self.assertEqual(reading.details["calibration_readiness"], "difference_suitable")
        self.assertEqual(reading.details["calibration_temperature_difference_c"], 16)
        self.assertEqual(reading.details["calibration_stability"], "not_verified")
        self.assertEqual(reading.details["status"], "needs_calibration")
        self.assertEqual(reading.details["missing_inputs"], ["calibration"])
        self.assertIsNone(reading.value)
        self.assertNotIn("calibration_factor", reading.details)
        self.assertNotIn("estimated_surface_c", reading.details)
        self.assertEqual(mold.rh_fallback_for_room(ROOM, reading).value, 55)

    def test_warm_weather_reversed_and_zero_difference(self):
        for inside, outside in ((21, 35), (21, 21), (5, 20)):
            with self.subTest(inside=inside, outside=outside):
                info = mold.calibration_measurement_readiness(inside, outside)
                self.assertEqual(info["calibration_readiness"], "outdoors_not_colder")
                self.assertLessEqual(info["calibration_temperature_difference_c"], 0)

    def test_small_difference_and_exact_recommended_boundary(self):
        for outside in (19.9, 18, 15, 10.000001):
            self.assertEqual(mold.calibration_measurement_readiness(20, outside)
                ["calibration_readiness"], "difference_too_small")
        for outside in (10, 0, -15):
            info = mold.calibration_measurement_readiness(20, outside)
            self.assertEqual(info["calibration_readiness"], "difference_suitable")
            self.assertEqual(info["calibration_recommended_difference_c"], 10)

    def test_invalid_inputs_never_qualify_and_missing_sources_are_named(self):
        for invalid in (None, float("nan"), float("inf"), -100, 100, True, False, "unknown"):
            for indoor, outdoor, missing in ((invalid, 0, "indoor_temperature"),
                                             (20, invalid, "outdoor_temperature")):
                with self.subTest(indoor=indoor, outdoor=outdoor):
                    info = mold.calibration_measurement_readiness(indoor, outdoor)
                    self.assertEqual(info["calibration_readiness"], "temperatures_unavailable")
                    self.assertEqual(info["calibration_missing_temperature_inputs"], [missing])
                    self.assertNotIn("calibration_temperature_difference_c", info)
        self.assertEqual(mold.calibration_measurement_readiness(None, None)
            ["calibration_missing_temperature_inputs"], ["indoor_temperature", "outdoor_temperature"])

    def test_stale_and_unavailable_real_inputs_do_not_reuse_saved_temperatures(self):
        self.sensor("sensor.room_temperature", 21, age=91)
        self.weather("weather.home", 5, age=91)
        inside, _ = sources.room_temperature_evidence(self.hass, self.settings, "room", age_minutes=90)
        outdoor = discovery.weather(self.hass, "weather.home", 90)
        saved = {"calibrated_indoor_c": 22, "calibrated_outdoor_c": 0,
                 "critical_temperature_c": 14, "indoor_temperature_entity": "sensor.room_temperature"}
        reading = mold.estimate_mold_for_room(ROOM, inside, (outdoor,), saved)
        self.assertEqual(reading.details["calibration_readiness"], "temperatures_unavailable")
        self.assertEqual(reading.details["calibration_missing_temperature_inputs"],
                         ["indoor_temperature", "outdoor_temperature"])
        self.assertNotIn("indoor_temperature_c", reading.details)
        self.assertNotIn("outdoor_temperature_c", reading.details)
        self.states["weather.home"].state = "unavailable"
        self.assertIsNone(discovery.weather(self.hass, "weather.home", 90).temperature_c)

    def test_wrong_room_unselected_and_manager_owned_temperatures_do_not_qualify(self):
        for options in ({"area": "other"}, {"platform": constants.DOMAIN}):
            self.sensor("sensor.room_temperature", 22, **options)
            self.assertEqual(self.live()[0].details["calibration_readiness"], "temperatures_unavailable")
        self.sensor("sensor.room_temperature", 22)
        self.settings["room_sources"]["room"]["temperature"] = []
        self.assertEqual(self.live()[0].details["calibration_readiness"], "temperatures_unavailable")

    def test_recently_reported_unchanged_state_is_current_and_fahrenheit_is_normalized(self):
        self.sensor("sensor.room_temperature", 68, unit="°F")
        self.weather("weather.home", 50, unit="°F")
        self.states["sensor.room_temperature"].last_updated = NOW-timedelta(days=1)
        reading, _ = self.live()
        self.assertEqual(reading.details["calibration_readiness"], "difference_suitable")
        self.assertEqual(reading.details["indoor_temperature_c"], 20)
        self.assertEqual(reading.details["outdoor_temperature_c"], 10)

    def test_partial_selected_means_ignore_stale_inputs(self):
        self.sensor("sensor.second_temperature", 80, age=91)
        self.settings["room_sources"]["room"]["temperature"].append("sensor.second_temperature")
        self.weather("weather.stale", 60, age=91)
        reading, evidence = self.live(("weather.home", "weather.stale"))
        self.assertEqual(evidence["valid_count"], 1)
        self.assertTrue(evidence["partial"])
        self.assertEqual(reading.details["calibration_temperature_difference_c"], 16)

    def test_unconfigured_guidance_does_not_depend_on_humidity_or_make_missing_rh_safe(self):
        room = replace(ROOM, readings=())
        reading = mold.estimate_mold_for_room(room, 20, (logic.Weather("weather.home", "cloudy", 0),), {})
        self.assertEqual(reading.details["calibration_readiness"], "difference_suitable")
        self.assertIn("humidity", reading.details["missing_inputs"])
        self.assertIsNone(reading.value)
        self.assertIsNone(mold.rh_fallback_for_room(room, reading))

    def test_existing_factor_and_pinned_sources_retain_same_calculation(self):
        factor = 1.234567891234
        config = {"calibration_factor": factor, "outdoor_weather_entity": "weather.pinned"}
        weather = (logic.Weather("weather.pinned", "cloudy", 5),
                   logic.Weather("weather.other", "cloudy", -30))
        reading = mold.estimate_mold_for_room(ROOM, 21, weather, config)
        self.assertEqual(reading.value, mold.estimate_mold(21, 5, 55, factor).surface_humidity)
        self.assertEqual(reading.details["calibration_factor"], factor)
        self.assertNotIn("calibration_readiness", reading.details)
        # The new 10°C suggestion never changes the existing 3°C numeric guard.
        self.assertEqual(mold.calibration_factor(20, 17, 18.5), 2)
        self.assertIsNone(mold.calibration_factor(20, 17.01, 18.5))

    def test_dashboard_retains_guidance_and_unavailable_mold_value(self):
        reading, _ = self.live()
        room = replace(ROOM, readings=(mold.rh_fallback_for_room(ROOM, reading), reading))
        plan = logic.evaluate((), (), (), (room,), constants.DEFAULT_THRESHOLDS)
        payload = dash.dashboard_snapshot(plan, constants.DEFAULT_THRESHOLDS)["rooms"][0]
        reported = next(item for item in payload["readings"] if item["metric"] == "mold")
        self.assertEqual(payload["status_detail"], "mold_not_calibrated")
        self.assertEqual(reported["details"]["calibration_readiness"], "difference_suitable")
        self.assertFalse(reported["available"])
        self.assertIsNone(reported["value"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MoldMeasurementReadiness)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("BETA115_MOLD_MEASUREMENT_CONTRAST_FRESHNESS_NO_FABRICATED_READINESS=PASS")

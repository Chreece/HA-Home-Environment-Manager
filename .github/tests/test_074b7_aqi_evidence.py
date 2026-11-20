"""AQI values stay visible without inventing provider scale or safe air.

Run the production discovery, freshness, AQI classification, recommendation
logic and dashboard projection against local HA states/registry fixtures.
No physical service, global registry scan or network access is permitted.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem_074b7_aqi_evidence"


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(SOURCE)])
module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, State=object)
helpers = module("homeassistant.helpers", __path__=[])
module("homeassistant.util", dt=N(utcnow=lambda: datetime.now(timezone.utc)))


class Registry:
    def __init__(self):
        self.rows = {}

    def async_get(self, entity):
        return self.rows.get(entity)

    @property
    def entities(self):
        raise AssertionError("AQI evaluation must not enumerate the registry")


registry = Registry()
for kind in ("area_registry", "device_registry", "entity_registry"):
    entry = module("homeassistant.helpers." + kind, async_get=lambda _: registry)
    setattr(helpers, kind, entry)

logic = importlib.import_module(PACKAGE + ".logic")
dashboard = importlib.import_module(PACKAGE + ".dashboard")
discovery = importlib.import_module(PACKAGE + ".discovery")
science = importlib.import_module(PACKAGE + ".environment_science")
sources = importlib.import_module(PACKAGE + ".aqi_sources")
constants = importlib.import_module(PACKAGE + ".const")

# Load the unchanged production wrapper without importing unrelated room
# physics/adaptation modules. Its real resolver and classifier run below.
tree = ast.parse((SOURCE / "environment_extended.py").read_text())
wrapper = next(node for node in tree.body
               if isinstance(node, ast.FunctionDef) and node.name == "global_aqi")
scope = {"__name__": PACKAGE + ".environment_extended", "__package__": PACKAGE,
         "Any": Any, "aqi_category": science.aqi_category}
exec(compile(ast.Module(body=[wrapper], type_ignores=[]),
             str(SOURCE / "environment_extended.py"), "exec"), scope)
global_aqi = scope["global_aqi"]


def forbidden(*_args, **_kwargs):
    raise AssertionError("AQI display must not send services or scan all states")


def state(entity, value, name, *, metric="aqi", unit="", age=0, restored=False):
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=age)
    return N(entity_id=entity, name=name, domain="sensor", state=str(value),
             attributes={"device_class": metric, "unit_of_measurement": unit,
                         **({"restored": True} if restored else {})},
             last_updated=timestamp, last_reported=timestamp)


def screenshot_states():
    registry.rows.clear()
    result = {}
    for suffix, name, value in (
        ("co2", "AQI Co2", 1), ("humidity", "AQI Humidity", 2),
        ("pm25", "AQI PM 2.5", 1), ("temperature", "AQI Temperature", 2),
        ("tvoc", "AQI TVOC", 1), ("home", "Home AQI Index", 1),
    ):
        entity = "sensor.aqi_" + suffix
        result[entity] = state(entity, value, name)
        registry.rows[entity] = N(platform="template", original_device_class="aqi")
    entity = "sensor.piraeus_air_quality_index"
    result[entity] = state(entity, 85, "Pireaus-1, Greece - Air quality index")
    registry.rows[entity] = N(platform="waqi", original_device_class="aqi")
    return result


def project(states, profile=None):
    profile = profile or {}
    hass = N(states=N(get=states.get, async_all=forbidden),
             services=N(async_call=forbidden))
    readings = []
    for entity in states:
        reading = discovery.reading(hass, entity, 90, outdoor=True)
        if reading.metric == "aqi" and reading.value is not None:
            reading = logic.Reading(reading.entity_id, reading.name, reading.metric,
                                    reading.value, {"aqi": global_aqi(reading, profile, hass=hass)})
        readings.append(reading)
    weather = (logic.Weather("weather.home", "partlycloudy", 22.7, 61., 19.8),)
    room = logic.Room("living", "Living room",
                      (logic.Window("binary_sensor.window", "Window", False),),
                      (logic.Reading("sensor.indoor_co2", "Room CO2", "co2", 1350.),))
    plan = logic.evaluate(tuple(readings), weather, (), (room,), constants.DEFAULT_THRESHOLDS)
    return plan, dashboard.dashboard_snapshot(plan, constants.DEFAULT_THRESHOLDS)


def fixture_payload():
    """The browser test can consume the same real backend projection."""
    return project(screenshot_states())[1]


class AQIEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.states = screenshot_states()

    def test_screenshot_values_and_source_names_survive_unknown_scale(self):
        before = deepcopy(self.states)
        plan, payload = project(self.states)
        outside = payload["outdoor"]
        readings = outside["readings"]
        self.assertEqual(len(readings), 7)
        self.assertEqual([item["value"] for item in readings], [1., 2., 1., 2., 1., 1., 85.])
        self.assertEqual([item["name"] for item in readings], [item.name for item in self.states.values()])
        self.assertTrue(all(item["value_available"] for item in readings))
        self.assertTrue(all(item["metric"] == "aqi" for item in readings))
        for item in readings[:6]:
            self.assertFalse(item["available"])
            self.assertFalse(item["exceeded"])
            self.assertEqual(item["evaluation_status"], "configuration_required")
            self.assertEqual(item["details"]["aqi"]["scale"], "not_configured")
            self.assertNotIn(item["unit"], ("ppm", "%", "°C", "US AQI"))
        self.assertEqual(readings[-1]["unit"], "US AQI")
        self.assertTrue(readings[-1]["available"])
        self.assertFalse(readings[-1]["exceeded"])
        self.assertEqual(readings[-1]["evaluation_status"], "ready")
        self.assertEqual(outside["status"], "partial")
        self.assertFalse(outside["data_complete"])
        self.assertEqual(outside["unavailable_sensors"], [])
        self.assertEqual(outside["unevaluated_aqi_sensors"], list(self.states)[:6])
        self.assertTrue(plan.outdoor_safe)
        self.assertEqual(plan.outside_reasons, ())
        self.assertEqual([item.action for item in plan.recommendations], ["open"])
        self.assertEqual(self.states, before)

    def test_stale_unavailable_and_restored_values_never_become_display_data(self):
        entity = "sensor.aqi_co2"
        for value, age, restored in ((1, 120, False), ("unavailable", 0, False),
                                     ("unknown", 0, False), (1, 0, True)):
            with self.subTest(value=value, age=age, restored=restored):
                self.states[entity] = state(entity, value, "AQI Co2", age=age, restored=restored)
                _, payload = project(self.states)
                outside = payload["outdoor"]
                item = next(row for row in outside["readings"] if row["entity_id"] == entity)
                self.assertIsNone(item["value"])
                self.assertFalse(item["value_available"])
                self.assertFalse(item["available"])
                self.assertEqual(item["evaluation_status"], "unavailable")
                self.assertIn(entity, outside["unavailable_sensors"])
                self.assertNotIn(entity, outside["unevaluated_aqi_sensors"])

    def test_explicit_invalid_scale_keeps_raw_value_and_diagnostic_scale(self):
        entity = "sensor.piraeus_air_quality_index"
        cases = (("us_epa", 701, None, "invalid", "US AQI"),
                 ("eea_category", 85, None, "invalid", "EEA category"),
                 ("custom", 85, None, "configuration_required", "AQI"))
        for scale, value, limit, expected, unit in cases:
            with self.subTest(scale=scale):
                self.states[entity] = state(entity, value, "Chosen AQI")
                profile = {"aqi_scales": {entity: {"scale": scale, "custom_limit": limit}}}
                before = deepcopy(profile)
                _, payload = project(self.states, profile)
                item = payload["outdoor"]["readings"][-1]
                self.assertEqual(item["value"], value)
                self.assertEqual(item["unit"], unit)
                self.assertTrue(item["value_available"])
                self.assertFalse(item["available"])
                self.assertFalse(item["exceeded"])
                self.assertEqual(item["evaluation_status"], expected)
                self.assertEqual(item["details"]["aqi"]["scale"], scale)
                self.assertEqual(item["details"]["aqi"]["scale_source"], "manual")
                self.assertEqual(profile, before)

    def test_known_air_hazards_still_override_optional_unknown_indices(self):
        entity = "sensor.outdoor_pm25"
        self.states[entity] = state(entity, 55, "Outdoor PM2.5", metric="pm25", unit="µg/m³")
        plan, payload = project(self.states)
        self.assertFalse(plan.outdoor_safe)
        self.assertEqual(payload["outdoor"]["status"], "unsafe")
        self.assertTrue(payload["outdoor"]["readings"][-1]["exceeded"])
        self.assertTrue(any(reason.code == "outside_pm25" for reason in plan.outside_reasons))

        self.states.pop(entity)
        entity = "sensor.piraeus_air_quality_index"
        self.states[entity] = state(entity, 140, "Verified AQI")
        plan, payload = project(self.states)
        self.assertFalse(plan.outdoor_safe)
        self.assertEqual(payload["outdoor"]["status"], "unsafe")
        self.assertTrue(payload["outdoor"]["readings"][-1]["exceeded"])

    def test_missing_pollutant_remains_separate_from_scale_setup(self):
        entity = "sensor.missing_pm25"
        self.states[entity] = state(entity, "unavailable", "Missing particles",
                                    metric="pm25", unit="µg/m³")
        _, payload = project(self.states)
        outside = payload["outdoor"]
        self.assertEqual(outside["unavailable_sensors"], [entity])
        self.assertEqual(len(outside["unevaluated_aqi_sensors"]), 6)
        self.assertEqual(outside["status"], "partial")
        self.assertFalse(outside["data_complete"])

    def test_unknown_scale_never_inferred_from_names_units_or_small_values(self):
        entity = "sensor.germany_us_epa_aqi"
        self.states = {entity: state(entity, 1, "US EPA WAQI", unit="AQI")}
        registry.rows[entity] = N(platform="template", original_device_class="aqi")
        _, payload = project(self.states)
        item = payload["outdoor"]["readings"][0]
        self.assertEqual(item["value"], 1.)
        self.assertEqual(item["evaluation_status"], "configuration_required")
        self.assertEqual(item["details"]["aqi"]["scale"], "not_configured")
        self.assertFalse(item["available"])
        self.assertEqual(payload["outdoor"]["status"], "partial")


if __name__ == "__main__":
    if "--fixture-json" in sys.argv:
        print(json.dumps(fixture_payload(), ensure_ascii=False))
    else:
        unittest.main(verbosity=2)

"""Production trend observations preserve goals, sources and output evidence.

The collector, model target resolution, selected sensor normalization, mold
physics and bounded history run unchanged. Only HA registries/presence and
clock boundaries are simulated. No hardware service is available to this test.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import logging
from pathlib import Path
import sys
from types import MethodType, ModuleType, SimpleNamespace as N
from typing import Any
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem075controlcapture"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package
CLOCK = N(now=1_795_000_000.)
ENTITIES = {}


def module(name, **attributes):
    item = ModuleType(name)
    item.__dict__.update(attributes)
    sys.modules[name] = item
    return item


module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, State=object)
helpers = module("homeassistant.helpers", __path__=[])
module("homeassistant.util", dt=N(utcnow=lambda: datetime.fromtimestamp(CLOCK.now, timezone.utc)))
for name in ("area_registry", "entity_registry", "device_registry"):
    registry = (N(async_get_area=lambda area: N(name=area)) if name == "area_registry"
                else N(async_get=(ENTITIES.get if name == "entity_registry" else lambda _: None),
                       entities=ENTITIES))
    setattr(helpers, name, module("homeassistant.helpers." + name,
                                async_get=lambda hass, registry=registry: registry))

model = importlib.import_module(PACKAGE + ".equipment_model")
discovery = importlib.import_module(PACKAGE + ".discovery")
collector = importlib.import_module(PACKAGE + ".control_trend")
History = importlib.import_module(PACKAGE + ".environment_history").EnvironmentHistory
const = importlib.import_module(PACKAGE + ".const")


def production_methods(filename, class_name, names, namespace):
    tree = ast.parse((SOURCE / filename).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    methods = [deepcopy(node) for node in cls.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    for node in methods:
        node.decorator_list = []
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE / filename), "exec"), namespace)


runtime_namespace = {
    "__package__": PACKAGE, "Any": Any, "model": model,
    "CONF_EXCLUDED_INDOOR": const.CONF_EXCLUDED_INDOOR,
    "entity_area": discovery.entity_area, "reading": discovery.reading,
    "temperature_sensor_c": discovery.temperature_sensor_c,
    "_reported_timestamp": collector._reported_at,
}
production_methods("equipment_runtime.py", "EquipmentRuntime", {"measurements"}, runtime_namespace)
manager_namespace = {
    "__package__": PACKAGE, "Any": Any,
    "is_stopping": collector.is_stopping,
    "_LOGGER": logging.getLogger("hem075controlcapture"),
}
production_methods("manager.py", "AirQualityManager", {
    "_environment_snapshot", "_schedule_environment_save", "_capture_control_trends",
}, manager_namespace)


class States(dict):
    def async_all(self, domain=None):
        return [value for value in self.values() if domain is None or value.domain == domain]


class CollectorTests(unittest.TestCase):
    def setUp(self):
        CLOCK.now = 1_795_000_000.
        ENTITIES.clear()
        self.states = States()
        self.hass = N(states=self.states, is_stopping=False, state="running")
        self.cfg = {**deepcopy(model.DEFAULTS), "control_mode": "pid", "requested_mode": "heat",
                    "preset": "home", "pause_on_window_open": False}
        self.plan = {"away": "home", "occupancy": "unoccupied", "sleeping": False,
                     "window_safe": True}
        self.settings = {
            "areas": ["room"],
            "room_sources": {"room": {"temperature": ["sensor.temp"], "humidity": ["sensor.rh"],
                                       "air_quality": []}},
            "climate_rooms": {"room": {"selected_devices": ["climate.native"],
                "profiles": {
                    "home": {"heat_c": 20, "cool_c": 26, "humidity": 60},
                    "away": {"heat_c": 16, "cool_c": 29, "humidity": 65},
                    "comfort": {"heat_c": 22, "cool_c": 24, "humidity": 55},
                    "sleep": {"heat_c": 18, "cool_c": 27, "humidity": 62},
                    "eco": {"heat_c": 19, "cool_c": 28, "humidity": 64},
                }}},
        }
        self.spec = model.ManagedDevice("heater", "room", "Heater", "native-device", ("climate.native",))
        self.specs = [self.spec]
        self.cap = model.Capabilities("climate.native", "climate", ("off", "heat", "cool", "heat_cool"),
                                      temperature=True, temperature_range=True)
        self.runtime = N(hass=self.hass, clock=lambda: CLOCK.now, statuses={}, records={}, _invalidated=set())
        self.manager = N(settings=self.settings, hass=self.hass, equipment=self.runtime,
                         _active=True, _environment_restored=True, _stopping=False,
                         _environment_history=History(), _environment_store=None,
                         _environment_save_scheduled=False)
        self.runtime.manager = self.manager
        self.runtime.measurements = MethodType(runtime_namespace["measurements"], self.runtime)
        self.limits = {"temperature_min_limit": 5., "temperature_max_limit": 35.,
                       "humidity_min_limit": 20., "humidity_max_limit": 80.}
        for name, function in (
            ("settings", lambda manager, spec: self.cfg),
            ("mode_capabilities", lambda manager, spec: self.cap),
            ("plan_for", lambda manager, spec: self.plan),
            ("specs", lambda manager: tuple(self.specs)),
            ("device_limits", lambda manager, spec, cap: self.limits),
        ):
            item = patch.object(model, name, side_effect=function)
            item.start()
            self.addCleanup(item.stop)
        self.sensor("sensor.temp", 20., "temperature", "°C")
        self.sensor("sensor.rh", 55.8, "humidity", "%")
        self.native("climate.native", "heat", hvac_action="heating", temperature=5.)

    def sensor(self, entity, value, kind, unit, *, age=0, restored=False):
        stamp = datetime.fromtimestamp(CLOCK.now, timezone.utc) - timedelta(minutes=age)
        self.states[entity] = N(entity_id=entity, domain="sensor", name=entity, state=str(value),
            attributes={"device_class": kind, "unit_of_measurement": unit, "restored": restored},
            last_updated=stamp, last_reported=stamp)
        ENTITIES[entity] = N(area_id="room", device_id=None, platform="native",
                             device_class=None, original_device_class=None)

    def native(self, entity, state, **attributes):
        stamp = datetime.fromtimestamp(CLOCK.now, timezone.utc)
        self.states[entity] = N(entity_id=entity, domain=entity.split(".")[0], name=entity,
            state=state, attributes=attributes, last_updated=stamp, last_reported=stamp)
        ENTITIES[entity] = N(area_id="room", device_id="native-device", platform="native",
                             device_class=None, original_device_class=None)

    def dryer(self):
        self.cfg.update(control_mode="pid", requested_mode="dry")
        self.spec = model.ManagedDevice("dryer", "room", "Dryer", "dryer-device", ("humidifier.dryer",))
        self.specs = [self.spec]
        self.cap = model.Capabilities("humidifier.dryer", "humidifier", ("off", "dry"), humidity=True,
                                      native_humidity_target=True, min_humidity=20, max_humidity=80)
        self.settings.update({
            const.CONF_USE_MOLD: True, const.CONF_WEATHER: ["weather.home"],
            const.CONF_THRESHOLDS: {"indoor_mold": 70, "max_age_minutes": 90},
            const.CONF_MOLD_ROOMS: {"room": {"calibration_factor": 1.63,
                "indoor_temperature_entity": "sensor.temp", "indoor_temperature_entities": ["sensor.temp"],
                "outdoor_weather_entity": "weather.home", "outdoor_weather_entities": ["weather.home"]}},
        })
        self.native("humidifier.dryer", "on", humidity=40., device_class="dehumidifier")
        self.native("weather.home", "cloudy", temperature=5., temperature_unit="°C")

    def capture(self, **kwargs):
        return collector.capture(self.manager, **kwargs)

    def views(self, metric="temperature", sources=None):
        if sources is None:
            sources = [] if metric == "mold" else ["sensor.rh"] if metric == "humidity" else ["sensor.temp"]
        return self.manager._environment_history.control.view("room", metric, sources, now=CLOCK.now)

    def points(self, metric="temperature", sources=None):
        return self.views(metric, sources)[0]["series"][-1]["points"]

    def evaluation(self, value=37.):
        return {"metric": "temperature", "mode": "heat", "profile": "home", "target": 20.,
                "source_ids": ["sensor.temp"], "demand_percent": value}

    def test_saved_profile_targets_change_at_observation_not_backfilled(self):
        before = deepcopy(self.settings)
        for index, (preset, goal) in enumerate((("home", 20), ("away", 16), ("comfort", 22),
                                                ("sleep", 18), ("eco", 19))):
            self.cfg["preset"] = preset
            CLOCK.now += 20
            self.capture()
            self.assertEqual(self.points()[-1]["target"], goal)
            self.assertEqual(self.points()[-1]["profile"], preset)
            self.assertEqual(len(self.points()), index + 1)
        self.assertEqual(self.settings, before)
        self.assertEqual([point["target"] for point in self.points()], [20, 16, 22, 18, 19])
        self.assertNotEqual(self.points()[0]["target"], self.states["climate.native"].attributes["temperature"])

    def test_inferred_unknown_home_and_manual_without_goal_are_not_false_targets(self):
        self.cfg["preset"] = "none"
        self.plan["away"] = "unknown"
        self.capture()
        self.assertIsNone(self.points()[-1]["target"])
        self.assertIsNone(self.points()[-1]["profile"])
        self.assertEqual(self.points()[-1]["target_unavailable_reason"], "house_occupancy_unknown")
        self.cfg.update(control_mode="manual", profile_targets={"manual": {"heat": 23.}})
        CLOCK.now += 1
        self.capture()
        self.assertEqual(self.points()[-1]["target"], 23.)
        self.cfg["profile_targets"] = {}
        CLOCK.now += 1
        self.capture()
        self.assertIsNone(self.points()[-1]["target"])
        for changes in ({"control_mode": "off"}, {"control_mode": "existing"},
                        {"control_mode": "pid", "requested_mode": "off"}):
            self.cfg.update(changes)
            CLOCK.now += 1
            self.capture()
            self.assertIsNone(self.points()[-1]["target"])
            self.assertIsNone(self.points()[-1]["demand_percent"])

    def test_auto_records_real_band_and_fahrenheit_feedback_is_celsius(self):
        self.sensor("sensor.temp", 68., "temperature", "°F")
        self.cfg.update(control_mode="automatic", requested_mode="heat_cool", operating_mode="heat_cool")
        self.capture()
        point = self.points()[-1]
        self.assertEqual((point["target"], point["target_low"], point["target_high"]), (None, 20., 26.))
        self.assertEqual(point["measured"], 20.)
        self.assertEqual(self.views()[0]["series"][0]["unit"], "°C")
        self.assertEqual(point["output_kind"], "activity")
        self.assertEqual(point["output_percent"], 100.)

    def test_legacy_automatic_direction_matches_runtime_instead_of_old_request(self):
        self.sensor("sensor.temp", 30., "temperature", "°C")
        self.cfg.update(control_mode="automatic", requested_mode="heat")
        self.capture()
        self.assertEqual((self.points()[-1]["mode"], self.points()[-1]["target"]), ("cool", 26.))
        self.cfg["operating_mode"] = "heat"
        CLOCK.now += 1
        self.capture()
        self.assertEqual((self.points()[-1]["mode"], self.points()[-1]["target"]), ("heat", 20.))
        self.cfg.pop("operating_mode")
        self.cfg["control_mode"] = "pid"
        CLOCK.now += 1
        self.capture()
        self.assertEqual((self.points()[-1]["mode"], self.points()[-1]["target"]), ("heat", 20.))

    def test_calibrated_mold_and_effective_room_rh_are_different_historical_series(self):
        self.dryer()
        self.capture()
        expected = model.humidity_demand(self.manager, self.spec, self.cap, self.cfg, self.plan)
        mold, room = self.points("mold")[-1], self.points("humidity")[-1]
        self.assertEqual(mold["target"], 60.)
        self.assertNotEqual(mold["target"], 70.)
        self.assertAlmostEqual(mold["measured"], expected["control_measurement"], places=3)
        self.assertEqual(room["target"], expected["effective_humidity_target"])
        self.assertEqual(room["measured"], 55.8)
        self.assertEqual(self.views("humidity")[0]["series"][0]["target_kind"], "derived_room_rh")
        self.assertEqual(self.views("mold")[0]["series"][0]["basis"], "mold_surface_rh")
        restored = History.restore(deepcopy(self.manager._environment_history.snapshot()), now=CLOCK.now)
        self.assertEqual(restored.control.view("room", "mold", [], now=CLOCK.now), self.views("mold"))
        self.assertEqual(restored.control.view("room", "humidity", ["sensor.rh"], now=CLOCK.now),
                         self.views("humidity"))

    def test_missing_mold_inputs_pause_instead_of_ambient_fallback(self):
        self.dryer()
        self.capture()
        old_until = self.points("mold")[-1]["until"]
        self.states["weather.home"].state = "unavailable"
        CLOCK.now += 30
        self.capture(spec=self.spec)
        self.assertEqual(self.points("mold")[-1]["until"], old_until)
        self.states["weather.home"].state = "cloudy"
        CLOCK.now += 30
        self.capture(spec=self.spec)
        self.assertTrue(self.points("mold")[-1]["break_before"])
        self.assertTrue(self.points("humidity")[-1]["break_before"])

    def test_actual_contributors_match_mean_and_selected_set_change_breaks_context(self):
        self.sensor("sensor.second", 22., "temperature", "°C")
        self.sensor("sensor.stale", 99., "temperature", "°C", age=11)
        selected = self.settings["room_sources"]["room"]["temperature"] = ["sensor.temp", "sensor.second", "sensor.stale"]
        self.capture()
        sources = ["sensor.temp", "sensor.second"]
        self.assertEqual(self.points(sources=sources)[-1]["measured"], 21.)
        self.assertEqual(self.views(sources=["sensor.temp"]), [])
        self.assertEqual(self.views(sources=selected), [])
        first_context = self.views(sources=sources)[0]["series"][0]["context_id"]
        selected.remove("sensor.stale")
        CLOCK.now += 30
        self.capture()
        series = self.views(sources=sources)[0]["series"]
        self.assertEqual(len(series), 2)
        self.assertNotEqual(series[-1]["context_id"], first_context)
        self.states["sensor.temp"].state = self.states["sensor.second"].state = "unavailable"
        previous = series[-1]["points"][-1]["until"]
        CLOCK.now += 30
        self.capture(spec=self.spec)
        self.assertEqual(self.views(sources=sources)[0]["series"][-1]["points"][-1]["until"], previous)

    def test_physical_mode_is_not_output_and_missing_restored_or_old_reports_stay_null(self):
        self.states["climate.native"].attributes.pop("hvac_action")
        self.capture()
        self.assertIsNone(self.points()[-1]["output_percent"])
        for attributes in ({"hvac_action": "idle"}, {"hvac_action": "heating"},
                           {"hvac_action": "heating", "restored": True}):
            CLOCK.now += 1
            self.states["climate.native"].attributes.update(attributes)
            self.capture()
        self.assertEqual([point["output_percent"] for point in self.points()], [None, 0., 100., None])
        self.states["climate.native"].attributes["restored"] = False
        self.states["climate.native"].last_reported -= timedelta(minutes=31)
        CLOCK.now += 1
        self.capture()
        self.assertIsNone(self.points()[-1]["output_percent"])
        self.states["climate.native"].state = "unavailable"
        self.capture()
        self.assertIsNone(self.points()[-1]["output_percent"])

    def test_reported_fan_setting_and_valve_position_are_labeled(self):
        for domain, attributes, kind, value in (
            ("fan", {"percentage": 37.5}, "percentage", "on"),
            ("number", {"min": 0, "max": 100, "unit_of_measurement": "%"}, "position", "37.5"),
        ):
            entity = domain + ".native"
            spec = model.ManagedDevice(domain, "room", domain, None, (entity,))
            cap = model.Capabilities(entity, domain, ("off", "fan_only" if domain == "fan" else "heat"),
                                     fan_entity=entity if domain == "fan" else None,
                                     fan_percentage=domain == "fan")
            self.native(entity, value, **attributes)
            output = collector._reported_output(self.manager, spec, cap, "fan_only" if domain == "fan" else "heat", CLOCK.now)
            self.assertEqual((output["output_kind"], output["output_percent"]), (kind, 37.5))
        self.states["number.native"].attributes["unit_of_measurement"] = "W"
        self.assertIsNone(collector._reported_output(self.manager, spec, cap, "heat", CLOCK.now)["output_percent"])

    def test_fresh_request_is_reused_without_recalc_null_churn_but_hold_clears(self):
        self.capture()
        CLOCK.now += 1
        self.capture(spec=self.spec, evaluation=self.evaluation())
        points = self.points()
        self.assertEqual(points[-1]["demand_percent"], 37.)
        self.assertEqual(points[-1]["output_percent"], 100.)
        count = len(points)
        CLOCK.now += 30
        self.capture()
        self.assertEqual(len(self.points()), count)
        self.assertEqual(self.points()[-1]["demand_percent"], 37.)
        CLOCK.now += 1
        self.capture(spec=self.spec, status={"status": "minimum_off_hold", "mode": "heat"})
        self.assertIsNone(self.points()[-1]["demand_percent"])
        CLOCK.now += 1
        self.capture()
        self.assertIsNone(self.points()[-1]["demand_percent"])

    def test_request_context_changes_and_age_never_reuse_old_output(self):
        self.capture()
        self.capture(spec=self.spec, evaluation=self.evaluation())
        self.cfg["kp"] = 17.
        CLOCK.now += 1
        self.capture()
        self.assertIsNone(self.points()[-1]["demand_percent"])
        self.capture(spec=self.spec, evaluation=self.evaluation())
        CLOCK.now += 451
        self.capture()
        self.assertIsNone(self.points()[-1]["demand_percent"])
        self.capture(spec=self.spec, evaluation=self.evaluation())
        self.cfg["control_mode"] = "automatic"
        CLOCK.now += 1
        self.capture()
        self.cfg["control_mode"] = "pid"
        CLOCK.now += 1
        self.capture()
        self.assertIsNone(self.points()[-1]["demand_percent"])

    def test_late_status_cannot_seed_old_demand_after_target_or_sources_changed(self):
        self.capture()
        status = {"status": "controlling", "mode": "heat", "profile": "home", "demand_percent": 37.,
                  "pid_control_metric": "temperature", "pid_control_target": 20.,
                  "pid_control_measurement": 20.}
        self.capture(spec=self.spec, status=status)
        self.assertIsNone(self.points()[-1]["demand_percent"])
        self.capture(spec=self.spec, evaluation=self.evaluation())
        self.settings["climate_rooms"]["room"]["profiles"]["home"]["heat_c"] = 21.
        CLOCK.now += 1
        self.capture(spec=self.spec, status=status)
        self.assertEqual(self.points()[-1]["target"], 21.)
        self.assertIsNone(self.points()[-1]["demand_percent"])
        self.settings["climate_rooms"]["room"]["profiles"]["home"]["heat_c"] = 20.
        self.capture(spec=self.spec, evaluation=self.evaluation())
        self.sensor("sensor.replacement", 20., "temperature", "°C")
        self.settings["room_sources"]["room"]["temperature"] = ["sensor.replacement"]
        CLOCK.now += 1
        self.capture(spec=self.spec, status=status)
        self.assertIsNone(self.points(sources=["sensor.replacement"])[-1]["demand_percent"])
        # Even a passed pre-await measurement/config snapshot is revalidated.
        stale_cfg = deepcopy(self.cfg)
        self.cfg["kp"] = 44.
        self.capture(spec=self.spec, configuration=stale_cfg, evaluation=self.evaluation(),
                     measurements={"temperature": 20., "temperature_entity": "sensor.temp"})
        self.assertIsNone(self.points(sources=["sensor.replacement"])[-1]["demand_percent"])

    def test_restart_restoration_and_stopping_never_capture_or_restore_request(self):
        self.capture()
        self.capture(spec=self.spec, evaluation=self.evaluation())
        saved = deepcopy(self.manager._environment_history.snapshot())
        self.manager._environment_restored = False
        CLOCK.now += 30
        self.assertFalse(self.capture())
        self.assertEqual(self.manager._environment_history.snapshot(), saved)
        self.manager._environment_history = History.restore(saved, now=CLOCK.now)
        self.manager._environment_restored = True
        self.manager.__dict__.pop("_control_trend_requests", None)
        self.capture()
        self.assertIsNone(self.points()[-1]["demand_percent"])
        self.assertTrue(self.points()[-1]["break_before"])
        self.manager._stopping = True
        saved = deepcopy(self.manager._environment_history.snapshot())
        CLOCK.now += 30
        self.assertFalse(self.capture())
        self.assertEqual(self.manager._environment_history.snapshot(), saved)
        self.manager._stopping = False
        for core_state in ("stopping", "final_write", "stopped"):
            self.hass.state = N(value=core_state)
            self.assertFalse(self.capture())
            self.assertEqual(self.manager._environment_history.snapshot(), saved)

    def test_save_deadline_does_not_slide_with_every_observation(self):
        scheduled = []
        self.manager._environment_store = N(async_delay_save=lambda callback, delay: scheduled.append((callback, delay)))
        for name in ("_environment_snapshot", "_schedule_environment_save", "_capture_control_trends"):
            setattr(self.manager, name, MethodType(manager_namespace[name], self.manager))
        self.manager._capture_control_trends()
        for _ in range(5):
            CLOCK.now += 30
            self.manager._capture_control_trends()
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled[0][1], 300)
        self.assertEqual(scheduled[0][0](), self.manager._environment_history.snapshot())
        CLOCK.now += 30
        self.manager._capture_control_trends()
        self.assertEqual(len(scheduled), 2)
        self.manager._stopping = True
        CLOCK.now += 30
        self.manager._capture_control_trends()
        self.assertEqual(len(scheduled), 2)


def fixture_payload():
    """Real collector/storage payloads for the frontend transport regression."""
    fixture = CollectorTests(methodName="runTest")
    fixture.setUp()
    try:
        fixture.capture()
        thermal = fixture.views()
        fixture.dryer()
        CLOCK.now += 30
        fixture.capture()
        common = {"version": 1, "area_id": "room", "retention_seconds": 604800,
                  "sample_interval_seconds": 300, "max_gap_seconds": 900}
        return {
            "now": CLOCK.now,
            "temperature": {**common, "metric": "temperature", "source_ids": ["sensor.temp"],
                            "controllers": thermal},
            "humidity": {**common, "metric": "humidity", "source_ids": ["sensor.rh"],
                         "controllers": fixture.views("humidity")},
            "mold": {**common, "metric": "mold", "source_ids": [], "controllers": fixture.views("mold")},
        }
    finally:
        fixture.doCleanups()


if __name__ == "__main__":
    unittest.main()

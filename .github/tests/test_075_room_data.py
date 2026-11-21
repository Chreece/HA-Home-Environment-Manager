"""Room readiness follows actual control feedback, with no physical side effects.

Use the production measurement resolver, discovery, source policy, equipment
configuration and snapshot classifier. Only HA's transport/registries are fake.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem075roomdata"
NOW = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(SOURCE)])
module("probatio", Required=lambda key: key, In=lambda values: lambda value: value)
module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, State=object, callback=lambda fn: fn)
module("homeassistant.helpers", __path__=[])
module("homeassistant.util", dt=N(utcnow=lambda: NOW))
module("homeassistant.exceptions", HomeAssistantError=RuntimeError)
module("homeassistant.auth", __path__=[])
module("homeassistant.auth.permissions", __path__=[])
module("homeassistant.auth.permissions.const", POLICY_READ="read")
module("homeassistant.components", __path__=[])
module("homeassistant.components.sensor", SensorEntity=type("SensorEntity", (), {}),
       SensorStateClass=N(MEASUREMENT="measurement"))
module("homeassistant.helpers.dispatcher", async_dispatcher_connect=lambda *args: None)
module("homeassistant.components.websocket_api", ActiveConnection=object,
       websocket_command=lambda schema: lambda fn: fn,
       ERR_NOT_FOUND="not_found", ERR_UNAUTHORIZED="unauthorized")
for name in ("entity_registry", "device_registry", "area_registry"):
    module("homeassistant.helpers." + name,
           async_get=lambda hass, name=name: getattr(hass, name))

logic = importlib.import_module(PACKAGE + ".logic")
constants = importlib.import_module(PACKAGE + ".const")
discovery = importlib.import_module(PACKAGE + ".discovery")
equipment = importlib.import_module(PACKAGE + ".equipment_model")
data = importlib.import_module(PACKAGE + ".room_data")
dashboard = importlib.import_module(PACKAGE + ".dashboard")
api = importlib.import_module(PACKAGE + ".dashboard_api")
areas = importlib.import_module(PACKAGE + ".area_entities")

# Read the exact shipped methods without importing unrelated actuator services.
tree = ast.parse((SOURCE / "equipment_runtime.py").read_text())
controller_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                        and any(isinstance(item, ast.FunctionDef) and item.name == "measurements"
                                for item in node.body))
methods = [node for node in controller_class.body if isinstance(node, ast.FunctionDef)
           and node.name in ("measurements", "active_control_mode")]
timestamp = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_reported_timestamp")
runtime_class = ast.ClassDef(name="ReadOnlyRuntime", bases=[], keywords=[],
                            body=methods, decorator_list=[])
scope = {"__name__": PACKAGE + ".equipment_runtime", "__package__": PACKAGE,
         "Any": Any, "model": equipment, "datetime": datetime,
         "entity_area": discovery.entity_area, "reading": discovery.reading,
         "temperature_sensor_c": discovery.temperature_sensor_c,
         "CONF_EXCLUDED_INDOOR": constants.CONF_EXCLUDED_INDOOR}
exec(compile(ast.fix_missing_locations(ast.Module(body=[timestamp, runtime_class], type_ignores=[])),
             str(SOURCE / "equipment_runtime.py"), "exec"), scope)
Runtime = scope["ReadOnlyRuntime"]


class NoActions:
    def __getattr__(self, name):
        raise AssertionError(f"Room data projection attempted an external action: {name}")


class StateMap(dict):
    def async_all(self, domain=None):
        return [state for state in self.values() if domain is None or state.domain == domain]


class RoomDataTests(unittest.TestCase):
    def setUp(self):
        self.states, self.entities, self.devices = StateMap(), {}, {}
        registry = N(async_get=self.entities.get, entities=self.entities)
        registry.async_get_entity_id = lambda *args: None
        self.hass = N(states=self.states, entity_registry=registry,
                      device_registry=N(async_get=self.devices.get),
                      area_registry=N(async_get_area=lambda area: N(id=area, name=area)),
                      services=NoActions(), config_entries=NoActions())
        self.manager = N(hass=self.hass, entry=N(entry_id="entry"),
                         settings={"areas": ["room"], "climate_rooms": {},
                                   "room_sources": {}, "equipment_controllers": {}},
                         _device_hierarchy={"controllers": {}},
                         thresholds=constants.DEFAULT_THRESHOLDS)
        self.runtime = Runtime()
        self.runtime.manager, self.runtime.hass = self.manager, self.hass
        self.runtime.records = {}
        self.manager.equipment = self.runtime
        self.manager.plan = self.plan()
        self.hass.data = {"environment_manager": {"entry": self.manager}}

    def state(self, entity, state, *, area="room", attrs=None, minutes=0):
        self.states[entity] = N(entity_id=entity, state=str(state), name=entity,
                               domain=entity.partition(".")[0], attributes=attrs or {},
                               last_updated=NOW-timedelta(minutes=minutes),
                               last_reported=NOW-timedelta(minutes=minutes),
                               last_changed=NOW-timedelta(minutes=minutes))
        self.entities[entity] = N(entity_id=entity, area_id=area, device_id=None,
                                  platform="test", id=entity, unique_id=entity,
                                  device_class=None, original_device_class=None)

    def sensor(self, metric, value, *, entity=None, area="room", minutes=0, restored=False):
        entity = entity or "sensor." + metric
        klass = {"co2": "carbon_dioxide", "pm25": "pm25"}.get(metric, metric)
        unit = {"temperature": "°C", "humidity": "%", "co2": "ppm",
                "pm25": "µg/m³", "aqi": None, "illuminance": "lx"}[metric]
        self.state(entity, value, area=area, minutes=minutes,
                   attrs={"device_class": klass, "unit_of_measurement": unit,
                          "restored": restored})
        return entity

    def selection(self, *, temperature=(), humidity=(), air_quality=(), shades=(), area="room"):
        self.manager.settings["room_sources"][area] = {
            "temperature": list(temperature), "humidity": list(humidity),
            "air_quality": list(air_quality), "shades": list(shades)}

    def controller(self, entity="climate.heat", *, mode="heat", method="automatic",
                   area="room", native="off", modes=None, fan_purpose=None):
        domain = entity.partition(".")[0]
        attrs = {"hvac_modes": list(modes or ("off", mode)), "supported_features": 1}
        if domain == "humidifier":
            attrs = {"device_class": "dehumidifier" if mode == "dry" else "humidifier",
                     "supported_features": 1}
        if domain == "fan":
            attrs = {"supported_features": 1, "percentage_step": 1}
        self.state(entity, native, area=area, attrs=attrs)
        spec = equipment.ManagedDevice(entity, area, entity, None, (entity,))
        self.manager._device_hierarchy["controllers"][entity] = {"spec": spec, "device_id": "hem_"+entity}
        room = self.manager.settings["climate_rooms"].setdefault(area, {})
        room.setdefault("selected_devices", []).append(entity)
        cfg = {"control_mode": method, "requested_mode": mode}
        if fan_purpose:
            cfg["fan_purpose"] = fan_purpose
        self.manager.settings["equipment_controllers"][spec.identifier] = cfg
        return spec

    def plan(self, *, temperature=21., humidity=50., optional=(), area="room", windows=(),
             recommendations=(), climate_rooms=(), environment=None):
        readings = tuple(logic.Reading("sensor."+metric, metric, metric, value)
                         for metric, value in (("temperature", temperature), ("humidity", humidity)))
        room = logic.Room(area, area, tuple(windows), readings+tuple(optional))
        return logic.Plan("idle", True, (), tuple(recommendations), (), rooms=(room,),
                          climate_rooms=tuple(climate_rooms), environment=environment or {})

    def snapshot(self):
        return dashboard.manager_dashboard_snapshot(self.manager)

    def room(self):
        return self.snapshot()["rooms"][0]

    def test_monitoring_basics_ignore_optional_sensors_and_windows(self):
        optional = tuple(logic.Reading("sensor."+metric, metric, metric, None)
                         for metric in ("aqi", "mold", "illuminance", "co2"))
        for temperature, humidity, expected in ((21., 50., "ready"),
                                               (21., None, "partial"),
                                               (None, 50., "partial"),
                                               (None, None, "missing")):
            for windows in ((), (logic.Window("binary_sensor.window", "Window", None),)):
                with self.subTest(temperature=temperature, humidity=humidity, windows=windows):
                    self.manager.plan = self.plan(temperature=temperature, humidity=humidity,
                                                  optional=optional, windows=windows)
                    room = self.room()
                    self.assertEqual(room["data_availability"]["status"], expected)
                    self.assertEqual(room["status"], "unknown" if expected == "missing" else "safe")
                    self.assertEqual(room["data_availability"]["controllers"], [])

    def test_optional_real_reading_does_not_replace_both_missing_basics(self):
        self.manager.plan = self.plan(temperature=None, humidity=None,
            optional=(logic.Reading("sensor.co2", "CO2", "co2", 700.),))
        self.assertEqual(self.room()["status"], "unknown")

    def test_controller_requires_its_exact_input_despite_other_visible_measurements(self):
        self.controller()
        self.sensor("temperature", 21.)
        self.selection(temperature=())
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["temperature"])
        self.assertEqual(self.room()["status"], "unknown")
        self.selection(temperature=("sensor.temperature",))
        self.assertEqual(self.room()["data_availability"]["status"], "ready")
        self.entities["sensor.temperature"].area_id = "elsewhere"
        self.assertEqual(self.room()["status"], "unknown")

    def test_invalid_stale_restored_sources_cannot_be_control_feedback(self):
        self.controller()
        self.selection(temperature=("sensor.temperature",))
        for value, minutes, restored in (("unavailable", 0, False), ("nan", 0, False),
                                         ("inf", 0, False), ("broken", 0, False),
                                         (21., 11, False), (21., 0, True)):
            with self.subTest(value=value, minutes=minutes, restored=restored):
                self.sensor("temperature", value, minutes=minutes, restored=restored)
                self.assertEqual(self.room()["status"], "unknown")
        self.sensor("temperature", 0.)
        self.assertEqual(self.room()["status"], "safe")

    def test_valid_selected_mean_survives_one_unavailable_contributor(self):
        self.controller()
        self.sensor("temperature", 20., entity="sensor.one_temperature")
        self.sensor("temperature", "unavailable", entity="sensor.two_temperature")
        self.selection(temperature=("sensor.one_temperature", "sensor.two_temperature"))
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], [])

    def test_offline_or_off_between_cycles_does_not_remove_required_input(self):
        spec = self.controller()
        cap = equipment.capabilities(self.manager, spec)
        self.runtime.records[spec.identifier] = {"area": "room", "source_device_id": None,
            "sources": list(spec.source_entities), "capabilities": asdict(cap)}
        self.sensor("temperature", 21.)
        self.selection(temperature=("sensor.temperature",))
        for native in ("off", "unavailable", "unknown"):
            with self.subTest(native=native):
                self.states[cap.primary].state = native
                if native != "off":
                    self.states[cap.primary].attributes = {}
                self.assertEqual(self.room()["data_availability"]["required_metrics"], ["temperature"])
                self.assertEqual(self.room()["status"], "safe")
        self.states["sensor.temperature"].state = "unavailable"
        self.assertEqual(self.room()["status"], "unknown")

    def test_explicit_requested_off_removes_feedback_requirement_until_rearmed(self):
        spec = self.controller(method="pid", native="off")
        cap = equipment.capabilities(self.manager, spec)
        record = {"area": "room", "source_device_id": None,
                  "sources": list(spec.source_entities), "capabilities": asdict(cap)}
        cfg = self.manager.settings["equipment_controllers"][spec.identifier]
        self.selection()  # Visible basics exist, but control feedback is absent.
        for transport in ("live_off", "cached_offline", "first_boot_offline"):
            with self.subTest(transport=transport):
                if transport != "live_off":
                    self.states["climate.heat"].state = "unavailable"
                    self.states["climate.heat"].attributes = {}
                self.runtime.records = ({spec.identifier: deepcopy(record)}
                                        if transport == "cached_offline" else {})
                cfg["requested_mode"] = "heat"
                self.assertEqual(self.room()["data_availability"]["missing_required_metrics"],
                                 ["temperature"])
                cfg["requested_mode"] = "off"
                stopped = self.room()
                self.assertEqual(stopped["data_availability"]["required_metrics"], [])
                self.assertEqual(stopped["data_availability"]["controllers"], [])
                self.assertEqual(stopped["status"], "safe")
                self.assertEqual(cfg["control_mode"], "pid")
                cfg["requested_mode"] = "heat"
                self.assertEqual(self.room()["status"], "unknown")

    def test_requested_off_overrides_retained_mode_scoped_automatic_profile(self):
        spec = self.controller(native="off")
        cfg = self.manager.settings["equipment_controllers"][spec.identifier]
        cfg.update(mode_settings_version=1, mode_settings={"heat": {"control_mode": "automatic"}})
        self.runtime.records[spec.identifier] = {"active_operating_mode": "heat"}
        self.selection()
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["temperature"])
        cfg["requested_mode"] = "off"
        self.assertEqual(equipment.settings(self.manager, spec)["operating_mode"], "heat")
        self.assertEqual(self.room()["data_availability"]["required_metrics"], [])
        self.assertEqual(self.room()["status"], "safe")

    def test_first_boot_offline_explicit_mode_still_requires_its_input(self):
        spec = self.controller()
        self.states["climate.heat"].state = "unavailable"
        self.states["climate.heat"].attributes = {}
        self.selection()
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["temperature"])
        self.manager.settings["equipment_controllers"][spec.identifier] = {
            "requested_mode": "heat", "mode_settings_version": 1,
            "mode_settings": {"heat": {"control_mode": "pid"}}}
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["temperature"])
        self.sensor("temperature", 21.)
        self.selection(temperature=("sensor.temperature",))
        self.assertEqual(self.room()["status"], "safe")
        self.manager.settings["equipment_controllers"][spec.identifier]["mode_settings"]["heat"]["control_mode"] = "manual"
        self.assertEqual(self.room()["data_availability"]["required_metrics"], [])

    def test_inactive_supervisory_methods_add_no_fictional_requirements(self):
        spec = self.controller()
        self.selection()
        for method in ("manual", "off", "existing"):
            with self.subTest(method=method):
                self.manager.settings["equipment_controllers"][spec.identifier]["control_mode"] = method
                self.assertEqual(self.room()["data_availability"]["required_metrics"], [])
                self.assertEqual(self.room()["status"], "safe")
                self.manager.plan = self.plan(temperature=None, humidity=None)
                self.assertEqual(self.room()["status"], "unknown")
                self.manager.plan = self.plan()

    def test_selected_heating_mode_does_not_require_unused_dry_and_fan_sensors(self):
        self.controller(mode="heat", modes=("off", "heat", "cool", "dry", "fan_only"))
        self.sensor("temperature", 20.)
        self.selection(temperature=("sensor.temperature",))
        self.manager.plan = self.plan(humidity=None)
        self.assertEqual(self.room()["data_availability"]["required_metrics"], ["temperature"])
        self.assertEqual(self.room()["status"], "safe")

    def test_unresolved_thermal_direction_needs_temperature_without_guessing_mixed_modes(self):
        self.manager.plan = self.plan(temperature=None, humidity=50.)
        self.sensor("humidity", 50.)
        for modes, required in (
                (("off", "heat", "cool"), ["temperature"]),
                (("off", "auto", "heat_cool"), ["temperature"]),
                (("off", "heat", "cool", "dry"), []),
                (("off", "heat", "cool", "fan_only"), [])):
            with self.subTest(modes=modes):
                spec = self.controller(mode=None, native="off", modes=modes)
                self.sensor("temperature", "unavailable")
                self.selection(temperature=("sensor.temperature",), humidity=("sensor.humidity",))
                self.assertIsNone(self.runtime.active_control_mode(spec))
                result = self.room()
                self.assertEqual(result["data_availability"]["required_metrics"], required)
                self.assertEqual(result["data_availability"]["missing_required_metrics"], required)
                self.assertEqual(result["status"], "unknown" if required else "safe")
                self.sensor("temperature", 21.)
                self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], [])
                self.assertEqual(self.room()["status"], "safe")

    def test_unresolved_scoped_thermal_profiles_require_their_shared_input(self):
        for heat, cool in (("automatic", "automatic"), ("pid", "pid"), ("automatic", "pid")):
            with self.subTest(heat=heat, cool=cool):
                self.setUp()
                spec = self.controller(mode=None, modes=("off", "heat", "cool"))
                cfg = self.manager.settings["equipment_controllers"][spec.identifier]
                cfg.clear()
                cfg.update(requested_mode=None, mode_settings_version=1,
                           mode_settings={"heat": {"control_mode": heat},
                                          "cool": {"control_mode": cool}})
                self.sensor("humidity", 50.)
                self.sensor("temperature", "unavailable")
                self.selection(temperature=("sensor.temperature",), humidity=("sensor.humidity",))
                self.manager.plan = self.plan(temperature=None, humidity=50.)
                self.assertIsNone(self.runtime.active_control_mode(spec))
                self.assertEqual(equipment.settings(self.manager, spec)["control_mode"], "existing")
                before = deepcopy((self.manager.settings, self.runtime.records))
                result = self.snapshot()
                self.assertEqual(result["rooms"][0]["data_availability"]["required_metrics"], ["temperature"])
                self.assertEqual(result["rooms"][0]["data_availability"]["missing_required_metrics"], ["temperature"])
                self.assertEqual(result["rooms"][0]["status"], "unknown")
                self.assertEqual(result["summary"]["unknown"], 1)
                self.assertEqual(areas.AreaOverview(self.manager, "entry", "room").native_value, "unknown")
                self.sensor("temperature", 21.)
                self.assertEqual(self.room()["status"], "safe")
                self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], [])
                self.assertIsNone(self.runtime.active_control_mode(spec))
                self.assertEqual((self.manager.settings, self.runtime.records), before)
                cfg["requested_mode"] = "off"
                self.states["sensor.temperature"].state = "unavailable"
                self.assertEqual(self.room()["data_availability"]["required_metrics"], [])
                self.assertEqual(self.room()["status"], "safe")

    def test_unresolved_scoped_modes_use_only_eligible_profile_requirements(self):
        spec = self.controller(mode=None, modes=("off", "heat", "cool", "dry", "fan_only"))
        cfg = self.manager.settings["equipment_controllers"][spec.identifier]
        cfg.update(mode_settings_version=1, mode_settings={
            "heat": {"control_mode": "automatic"}, "cool": {"control_mode": "pid"},
            "dry": {"control_mode": "manual"}, "fan_only": {"control_mode": "existing"}})
        self.selection()
        self.assertIsNone(self.runtime.active_control_mode(spec))
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["temperature"])
        # An old flat Automatic method must not resurrect an inactive profile.
        for mode in ("heat", "cool"):
            cfg["mode_settings"][mode]["control_mode"] = "off"
        self.assertEqual(self.room()["data_availability"]["required_metrics"], [])
        cfg["mode_settings"]["heat"]["control_mode"] = "automatic"
        cfg["mode_settings"]["dry"]["control_mode"] = "automatic"
        self.assertEqual(self.room()["data_availability"]["required_metrics"], [])
        # Once a direction is explicitly selected, its own input is required.
        cfg["requested_mode"] = "dry"
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["humidity"])

    def test_two_controllers_report_independent_required_metrics(self):
        self.controller()
        self.controller("humidifier.dry", mode="dry", method="pid")
        self.sensor("temperature", 20.)
        self.sensor("humidity", "unavailable")
        self.selection(temperature=("sensor.temperature",), humidity=("sensor.humidity",))
        result = self.room()["data_availability"]
        self.assertEqual(result["required_metrics"], ["temperature", "humidity"])
        self.assertEqual(result["missing_required_metrics"], ["humidity"])
        self.assertEqual(result["controllers"][0]["missing_metrics"], [])
        self.assertEqual(result["controllers"][1]["missing_metrics"], ["humidity"])

    def test_fan_control_uses_exact_pollutant_not_aqi_or_other_basic_readings(self):
        spec = self.controller("fan.cleaner", mode="fan_only", fan_purpose="filtration")
        self.sensor("aqi", 20.)
        self.sensor("co2", 700.)
        self.sensor("pm25", 0.)
        self.selection(air_quality=("sensor.aqi", "sensor.co2"))
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["pm25"])
        self.selection(air_quality=("sensor.aqi", "sensor.pm25"))
        self.assertEqual(self.room()["status"], "safe")
        self.manager.settings["equipment_controllers"][spec.identifier]["fan_purpose"] = "extraction"
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["co2"])
        self.selection(air_quality=("sensor.co2",))
        self.assertEqual(self.room()["status"], "safe")

    def test_climate_only_control_data_and_summary_count_same_rendered_rooms(self):
        self.controller("fan.cleaner", mode="fan_only", area="extra", fan_purpose="filtration")
        self.sensor("pm25", 3., area="extra")
        self.selection(air_quality=("sensor.pm25",), area="extra")
        extra = logic.Room("extra", "extra", (), ())
        self.manager.plan = self.plan(climate_rooms=(extra,))
        result = self.snapshot()
        self.assertEqual(result["summary"], {"total": 2, "safe": 2, "attention": 0, "unknown": 0})
        self.assertTrue(result["rooms"][1]["climate_only"])
        self.assertEqual(result["rooms"][1]["data_availability"]["status"], "ready")
        self.assertEqual(result["rooms"][1]["data_availability"]["missing_basic_metrics"],
                         ["temperature", "humidity"])

    def test_urgent_close_and_real_high_readings_keep_attention(self):
        self.controller()
        self.selection()
        for recommendations, humidity in (((), 90.),
                ((logic.Recommendation("close", "room", "room", (), ()),), 50.)):
            with self.subTest(humidity=humidity):
                self.manager.plan = self.plan(humidity=humidity, recommendations=recommendations)
                result = self.room()
                self.assertEqual(result["status"], "attention")
                self.assertEqual(result["data_availability"]["status"], "missing")
                self.assertEqual(result["data_availability"]["missing_required_metrics"], ["temperature"])

    def test_enabled_cover_requires_temperature_and_only_opted_in_lux(self):
        self.state("cover.blind", "closed", attrs={"device_class": "shutter", "supported_features": 2})
        self.sensor("temperature", 21.)
        self.sensor("illuminance", 0.)
        self.selection(temperature=("sensor.temperature",), shades=("cover.blind",),
                       air_quality=("sensor.illuminance",))
        self.manager.settings["shade_rooms"] = {"room": {"covers": {"cover.blind": {
            "enabled": True, "lux_enabled": True, "lux_entity": "sensor.illuminance"}}}}
        cfg = self.manager.settings["shade_rooms"]["room"]["covers"]["cover.blind"]
        self.assertEqual(self.room()["data_availability"]["required_metrics"], ["temperature", "illuminance"])
        self.assertEqual(self.room()["status"], "safe")
        self.states["sensor.illuminance"].state = "unavailable"
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["illuminance"])
        cfg["lux_enabled"] = False
        self.assertEqual(self.room()["status"], "safe")
        cfg["enabled"] = False
        self.assertEqual(self.room()["data_availability"]["required_metrics"], [])

    def test_legacy_pid_keeps_its_exact_pinned_sensor_and_skips_migrated_owners(self):
        self.state("climate.legacy", "off", attrs={"hvac_modes": ["off", "heat"], "supported_features": 1})
        self.sensor("temperature", 21.)
        self.sensor("temperature", "unavailable", entity="sensor.pid_temperature")
        self.selection(temperature=("sensor.temperature",))
        cfg = {"enabled": True, "climate_entities": ["climate.legacy"],
               "temperature_entity": "sensor.pid_temperature"}
        self.manager.settings["pid_rooms"] = {"room": cfg}
        self.assertEqual(self.room()["data_availability"]["missing_required_metrics"], ["temperature"])
        self.states["sensor.pid_temperature"].state = "21"
        self.assertEqual(self.room()["status"], "safe")
        self.controller("climate.legacy", method="manual")
        self.assertEqual(self.room()["data_availability"]["controllers"], [])

    def test_projection_is_read_only_and_area_scoped_across_reload(self):
        self.controller()
        self.controller("climate.other", area="other")
        self.sensor("temperature", 21.)
        self.selection(temperature=("sensor.temperature",))
        before = deepcopy((self.manager.settings, self.runtime.records, self.states, self.entities))
        complete = self.room()
        one = dashboard.manager_dashboard_snapshot(self.manager, area_id="room")["rooms"][0]
        self.assertEqual(one, complete)
        self.assertEqual(list(data.controller_inputs(self.manager, area_id="room")), ["room"])
        self.assertEqual((self.manager.settings, self.runtime.records, self.states, self.entities), before)
        self.manager.settings = deepcopy(self.manager.settings)
        self.runtime.records = deepcopy(self.runtime.records)
        self.assertEqual(self.room(), complete)

    def test_websocket_and_room_sensor_publish_same_readiness(self):
        self.controller()
        self.selection()
        self.entities["sensor.hem"] = N(platform="environment_manager", config_entry_id="entry",
                                         unique_id="entry_recommendation")
        results, errors = [], []
        connection = N(user=N(is_admin=True),
                       send_result=lambda request_id, result: results.append(result),
                       send_error=lambda *args: errors.append(args))
        api.websocket_dashboard(self.hass, connection, {"id": 1, "entity_id": "sensor.hem"})
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 1)
        row = areas.room_snapshot(self.manager, "room")
        self.assertEqual(results[0]["rooms"][0], row)
        self.assertEqual(row["data_availability"]["missing_required_metrics"], ["temperature"])
        self.assertEqual(results[0]["summary"]["unknown"], 1)
        self.sensor("temperature", 21.)
        self.selection(temperature=("sensor.temperature",))
        api.websocket_dashboard(self.hass, connection, {"id": 2, "entity_id": "sensor.hem"})
        self.assertEqual(results[-1]["rooms"][0], areas.room_snapshot(self.manager, "room"))
        self.assertEqual(results[-1]["summary"]["safe"], 1)

    def test_climate_only_native_overview_matches_assessment_not_controller_readiness(self):
        self.controller("climate.extra", area="extra")
        self.manager.settings["climate_rooms"]["extra"].update(enabled=True, controller="device")
        self.selection(area="extra")
        extra = logic.Room("extra", "extra", (), ())
        self.manager.plan = self.plan(climate_rooms=(extra,), environment={"extra": {
            "measurement_evidence": {"temperature": {"value": 21.}, "humidity": {"value": 50.}},
            "climate_plan": {"status": "ready", "mode": "heat"}}})
        overview = areas.AreaOverview(self.manager, "entry", "extra")
        self.assertEqual(overview.native_value, "unknown")
        attributes = overview.extra_state_attributes
        self.assertEqual(attributes["assessment"]["status"], "unknown")
        self.assertEqual(attributes["assessment"]["data_availability"]["missing_required_metrics"],
                         ["temperature"])
        self.assertEqual(attributes["assessment"]["data_availability"]["controllers"][0]["name"],
                         "climate.extra")
        self.assertEqual(attributes["controller"]["status"], "ready")
        self.assertFalse(attributes["monitoring_enabled"])
        self.sensor("temperature", 21., area="extra")
        self.selection(temperature=("sensor.temperature",), area="extra")
        canonical = areas.room_snapshot(self.manager, "extra")
        attributes = overview.extra_state_attributes
        self.assertEqual(overview.native_value, canonical["status"])
        self.assertEqual(overview.native_value, "safe")
        self.assertEqual(attributes["assessment"]["data_availability"], canonical["data_availability"])
        self.assertEqual(attributes["assessment"]["data_availability"]["missing_required_metrics"], [])
        self.assertEqual(attributes["controller"]["status"], "ready")

    def test_mold_sensor_getters_do_not_resolve_controller_measurements(self):
        self.controller()
        self.selection()
        self.manager.settings[constants.CONF_USE_MOLD] = True
        self.manager.settings[constants.CONF_MOLD_ROOMS] = {"room": {
            "calibration_factor": 1.4, "critical_temperature_c": 17.,
            "calibrated_at": "2026-11-20T12:00:00+00:00"}}
        mold = logic.Reading("calculated.mold", "Surface humidity", "mold", 65., {
            "status": "ready", "dewpoint_c": 12., "estimated_surface_c": 17.,
            "calibration_factor": 1.4, "missing_inputs": []})
        self.manager.plan = self.plan(optional=(mold,))
        sensor = areas.AreaMoldSurfaceHumidity(self.manager, "entry", "room")
        with patch.object(data, "controller_inputs", wraps=data.controller_inputs) as projection, \
                patch.object(self.runtime, "measurements", wraps=self.runtime.measurements) as resolver:
            self.assertEqual(sensor.native_value, 65.)
            attributes = sensor.extra_state_attributes
            self.assertEqual(attributes["calibration_status"], "ready")
            self.assertEqual(attributes["estimated_surface_temperature_c"], 17.)
            self.assertEqual(attributes["calibration_factor"], 1.4)
            self.assertEqual(attributes["calibrated_at"], "2026-11-20T12:00:00+00:00")
            self.assertEqual(attributes["missing_inputs"], [])
            projection.assert_not_called()
            resolver.assert_not_called()
            # Prove this room still resolves its missing feedback for overview.
            self.assertEqual(areas.AreaOverview(self.manager, "entry", "room").native_value, "unknown")
            self.assertEqual(projection.call_count, 1)
            self.assertEqual(resolver.call_count, 1)

    def test_malformed_monitoring_values_are_absent_and_zero_temperature_is_valid(self):
        for value in (None, True, "21", float("nan"), float("inf"), 999.):
            self.manager.plan = self.plan(temperature=value, humidity=None)
            self.assertEqual(self.room()["status"], "unknown")
        self.manager.plan = self.plan(temperature=0., humidity=None)
        self.assertEqual(self.room()["status"], "safe")

    def test_modern_missing_measurement_evidence_cannot_revive_legacy_plan_value(self):
        for evidence in ({}, {"temperature": {"value": None}}):
            self.manager.plan = self.plan(temperature=None, humidity=None, environment={"room": {
                "measurement_evidence": evidence, "climate_plan": {"temperature_c": 21.}}})
            self.assertEqual(self.room()["status"], "unknown")
        # Older already-validated plan payloads keep compatibility until recapture.
        self.manager.plan = self.plan(temperature=None, humidity=None, environment={"room": {
            "climate_plan": {"temperature_c": 21.}}})
        self.assertEqual(self.room()["status"], "safe")


if __name__ == "__main__":
    unittest.main(verbosity=2)

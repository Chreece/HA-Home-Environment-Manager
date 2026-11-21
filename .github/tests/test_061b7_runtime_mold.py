"""Real native control consumes calibrated mold demand and live source validity.

Combines the runtime-mode fixture's actual tick/dispatch/ACK/safety paths with
production selected-sensor discovery, measurements, mold physics and target
resolution. Only HA registry/state/service transport, presence and time are
simulated. Native service success never fabricates a physical acknowledgement.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import importlib
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(ROOT / ".github/tests/test_061b7_runtime_modes.py"))
Runtime, model, production, PACKAGE = (b[key] for key in ("Runtime", "model", "production", "PACKAGE"))
PRIMARY, ORIGINAL_SPEC = b["PRIMARY"], b["SPEC"]
activation = b["activation"]
CURRENT = None


def module(name, **values):
    result = sys.modules.setdefault(name, ModuleType(name))
    result.__dict__.update(values)
    return result


# The parent fixture deliberately isolates qualified measurements. This gate
# restores their real production discovery, using simulated HA registries and
# a clock that advances with the actual runtime under test.
module("homeassistant.core", HomeAssistant=object, State=object)
helpers = module("homeassistant.helpers")
for name, registry in (
    ("area_registry", lambda hass: N(async_get_area=lambda area: N(name=area))),
    ("device_registry", lambda hass: N(async_get=lambda device: None)),
):
    item = module("homeassistant.helpers." + name, async_get=registry)
    setattr(helpers, name, item)
module("homeassistant.util", dt=N(utcnow=lambda: datetime.fromtimestamp(CURRENT.now, timezone.utc)))
sys.modules.pop(PACKAGE + ".discovery", None)
discovery = importlib.import_module(PACKAGE + ".discovery")
sys.modules.pop(PACKAGE + ".room_sources", None)
importlib.import_module(PACKAGE + ".room_sources")
const = importlib.import_module(PACKAGE + ".const")
mold = importlib.import_module(PACKAGE + ".mold")
power = importlib.import_module(PACKAGE + ".equipment_power_switch")
safety = importlib.import_module(PACKAGE + ".equipment_pid_safety")
production.entity_area = power.entity_area = discovery.entity_area
production.reading = discovery.reading
production.temperature_sensor_c = discovery.temperature_sensor_c
production.CONF_EXCLUDED_INDOOR = const.CONF_EXCLUDED_INDOOR
b["base"]["extract"](ROOT / "equipment_runtime.py", ("measurements", "_reported_timestamp"), production.__dict__)


class States(dict):
    def async_all(self, domain=None):
        return [state for state in self.values() if domain is None or state.domain == domain]


class MoldRuntime(Runtime):
    def __init__(self, *, method="pid", kind="climate", humidity_target=True,
                 supply=False, minimum=20):
        global CURRENT
        logical = "humidify" if kind == "humidifier" else "dry"
        native_mode = "auto" if kind == "humidifier" else "dry"
        super().__init__(profile={
            "control_mode": method, "requested_mode": native_mode,
            "pause_on_window_open": False,
            "mode_settings_version": 1,
            "mode_settings": {logical: {"control_mode": method, "kp": 10, "ki": .1,
                "profile_targets": {"home": {"humidity": 60}, "comfort": {"humidity": 60}}}},
            "power_switch_entity": "switch.supply" if supply else None,
        })
        CURRENT = self
        primary = PRIMARY if kind == "climate" else "humidifier.native_humidity"
        self.spec = model.ManagedDevice(ORIGINAL_SPEC.identifier, "room", "Humidity appliance",
                                       ORIGINAL_SPEC.source_device_id, (primary,))
        self.primary = primary
        self.state.entity_id = primary
        self.state.domain = primary.partition(".")[0]
        self.state.name = "Humidity appliance"
        self.state.last_updated = self.state.last_reported = datetime.fromtimestamp(self.now, timezone.utc)
        self.state.attributes.update(min_humidity=minimum, max_humidity=80, humidity=60,
                                     current_humidity=47)
        if kind == "climate":
            self.state.attributes["hvac_modes"] = ["off", "heat", "cool", "dry"]
            self.state.attributes["supported_features"] = model.TEMP | (model.HUMIDITY if humidity_target else 0)
        else:
            self.state.attributes["device_class"] = "humidifier" if kind == "humidifier" else "dehumidifier"
            self.state.attributes.pop("hvac_modes", None)
            self.state.attributes["supported_features"] = 0
        self.states = States({primary: self.state})
        self.hass.states = self.states
        self.registry_rows.clear()
        self.register(primary, device=self.spec.source_device_id)
        self.manager._device_hierarchy = {"controllers": {self.spec.identifier: {"spec": self.spec}}}
        area = self.manager.entry.data["climate_rooms"]["room"]
        area["selected_devices"] = [primary]
        area["device_settings"] = {primary: self.manager.device}
        area["profiles"] = {profile: {"heat_c": 20, "cool_c": 26, "humidity": 60}
                            for profile in ("home", "comfort")}
        self.manager.plan.update(away="home", occupancy="occupied", sleeping=False)
        self.record.update(sources=[primary], source_device_id=self.spec.source_device_id)
        self._native_ready_since = {primary: self.now - 30}
        self._native_settled_for = {(self.spec.identifier, primary): self.now - 30}

        # Construct a measured surface calibration that yields exactly 80%
        # surface RH at the reported 20°C / 55.8% room and 5°C outdoors.
        gamma = math.log(55.8 / 80) + mold.MAGNUS_A * 20 / (mold.MAGNUS_B + 20)
        surface = mold.MAGNUS_B * gamma / (mold.MAGNUS_A - gamma)
        factor = mold.calibration_factor(20, 5, surface)
        self.manager.entry.options.update({
            const.CONF_USE_MOLD: True,
            const.CONF_WEATHER: ["weather.home"],
            const.CONF_THRESHOLDS: {"indoor_mold": 70, "max_age_minutes": 90},
            "room_sources": {"room": {"temperature": ["sensor.room_temperature"],
                                       "humidity": ["sensor.room_humidity"], "air_quality": []}},
            const.CONF_MOLD_ROOMS: {"room": {
                "calibration_factor": factor, "critical_temperature_c": surface,
                "indoor_temperature_entity": "sensor.room_temperature",
                "indoor_temperature_entities": ["sensor.room_temperature"],
                "outdoor_weather_entity": "weather.home", "outdoor_weather_entities": ["weather.home"],
            }},
        })
        raw = model.raw_settings(self.manager, self.spec)
        raw["_native_authorization"] = activation.authority_context(self.manager, self.spec)
        self.manager.entry.options[model.SETTINGS] = {self.spec.identifier: raw}
        self.sensor("sensor.room_temperature", 20, "temperature", "°C")
        self.sensor("sensor.room_humidity", 55.8, "humidity", "%")
        self.weather()
        if supply:
            self.register("switch.supply", device="supply-device")
            self.states["switch.supply"] = self.observation("switch.supply", "off", {}, age=1200)

    def register(self, entity, *, device=None, area="room"):
        self.registry_rows[entity] = N(entity_id=entity, id="registry-" + entity,
            unique_id="native-" + entity, device_id=device, platform="native", area_id=area,
            device_class=None, original_device_class=None)

    def observation(self, entity, value, attributes, *, age=0):
        stamp = datetime.fromtimestamp(self.now, timezone.utc) - timedelta(seconds=age)
        return N(entity_id=entity, domain=entity.partition(".")[0], name=entity, state=str(value),
                 attributes=attributes, last_updated=stamp, last_reported=stamp, last_changed=stamp,
                 context=N(user_id=None, parent_id=None))

    def sensor(self, entity, value, kind, unit, *, age=0, restored=False):
        self.register(entity)
        self.states[entity] = self.observation(entity, value,
            {"device_class": kind, "unit_of_measurement": unit, "restored": restored}, age=age)

    def weather(self, *, age=0):
        self.states["weather.home"] = self.observation("weather.home", "cloudy",
            {"temperature": 5, "temperature_unit": "°C"}, age=age)

    @property
    def cfg(self):
        return model.settings(self.manager, self.spec)

    @property
    def cap(self):
        return model.capabilities(self.manager, self.spec)

    def raw(self):
        return model.raw_settings(self.manager, self.spec)

    def humidity_info(self):
        return model.humidity_demand(self.manager, self.spec, self.cap, self.cfg, self.manager.plan)

    def surface_reading(self, surface_rh=64.4, *, humidity=49.4):
        """Create physical inputs for a chosen surface RH, without mocking physics."""
        inside, factor = 20.4, 1.310048
        gamma = math.log(humidity / surface_rh) + mold.MAGNUS_A * inside / (mold.MAGNUS_B + inside)
        surface = mold.MAGNUS_B * gamma / (mold.MAGNUS_A - gamma)
        outside = (factor * surface - inside) / (factor - 1)
        self.manager.entry.options[const.CONF_MOLD_ROOMS]["room"]["calibration_factor"] = factor
        self.sensor("sensor.room_temperature", inside, "temperature", "°C")
        self.sensor("sensor.room_humidity", humidity, "humidity", "%")
        self.weather()
        self.states["weather.home"].attributes["temperature"] = outside

    measurements = production.measurements

    async def evaluate(self, advance=0):
        global CURRENT
        CURRENT = self
        self.now += advance
        await self.tick(self.spec)
        while self.queued_tasks:
            tasks, self.queued_tasks = self.queued_tasks, []
            await asyncio.gather(*tasks)


class RuntimeMoldTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_off_keeps_supply_shutdown_without_mold_feedback(self):
        for method in ("automatic", "pid"):
            for kind in ("climate", "dehumidifier"):
                for missing in ("calibration", "weather", "humidity"):
                    with self.subTest(method=method, kind=kind, missing=missing):
                        r = MoldRuntime(method=method, kind=kind, supply=True)
                        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
                        raw["requested_mode"] = "off"
                        r.record["active_operating_mode"] = "dry"
                        if missing == "calibration":
                            r.manager.entry.options[const.CONF_MOLD_ROOMS]["room"]["calibration_factor"] = None
                        else:
                            r.states.pop("weather.home" if missing == "weather" else "sensor.room_humidity")
                        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), False,
                                      "An explicit Off remains verified absence of demand")
                        # Demand alone must not bypass ownership, physical
                        # native OFF or the established relay idle cooldown.
                        r.states["switch.supply"].state = "on"
                        r.record["upstream"] = {
                            "owned": True, "on_at": r.now - 1200,
                            "idle_since": r.now - r.cfg["power_switch_cooldown_seconds"],
                        }
                        self.assertTrue(power._dispatch_safe(
                            r, r.spec, r.record, r.cfg, "switch.supply", "off"))
                        r.record["upstream"]["owned"] = False
                        self.assertFalse(power._dispatch_safe(
                            r, r.spec, r.record, r.cfg, "switch.supply", "off"))
                        r.record["upstream"]["owned"] = True
                        r.state.state = "dry" if kind == "climate" else "on"
                        self.assertFalse(power._dispatch_safe(
                            r, r.spec, r.record, r.cfg, "switch.supply", "off"))
                        r.state.state = "off"
                        r.record["upstream"]["idle_since"] = r.now - 1
                        self.assertFalse(power._dispatch_safe(
                            r, r.spec, r.record, r.cfg, "switch.supply", "off"))

    async def test_saved_surface_profiles_cannot_block_method_changes_or_other_edits(self):
        for enabled in (True, False):
            for method in ("off", "manual", "existing", "automatic", "pid"):
                with self.subTest(enabled=enabled, method=method):
                    r = MoldRuntime()
                    raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
                    raw["mode_settings"]["dry"]["profile_targets"].update(
                        eco={"humidity": 95}, away={"humidity": 10})
                    saved = deepcopy(raw["mode_settings"]["dry"]["profile_targets"])
                    r.manager.entry.options[const.CONF_USE_MOLD] = enabled
                    await r.async_update(r.spec, {"control_mode": method}, operating_mode="dry")
                    local = model.settings_for_mode(r.manager, r.spec, "dry")
                    self.assertEqual(local["control_mode"], method)
                    self.assertEqual(local["profile_targets"], saved)
                    await r.async_update(r.spec, {"kp": 15}, operating_mode="dry")
                    local = model.settings_for_mode(r.manager, r.spec, "dry")
                    self.assertEqual(local["kp"], 15)
                    self.assertEqual(local["profile_targets"], saved)
                    if not enabled or method not in ("automatic", "pid"):
                        for profile, expected in (("eco", 80), ("away", 20)):
                            bounded = model.targets(r.manager, r.spec, r.cap,
                                {**local, "preset": profile}, {}, mold_protection=False)
                            self.assertEqual(bounded["humidity"], expected)

    async def test_new_profile_values_keep_current_bounds_with_saved_surface_profiles(self):
        r = MoldRuntime()
        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
        raw["mode_settings"]["dry"]["profile_targets"]["eco"] = {"humidity": 95}
        r.manager.entry.options[const.CONF_USE_MOLD] = False
        table = deepcopy(raw["mode_settings"]["dry"]["profile_targets"])
        table["home"]["humidity"] = 50
        await r.async_update(r.spec, {"profile_targets": table}, operating_mode="dry")
        self.assertEqual(model.settings_for_mode(r.manager, r.spec, "dry")["profile_targets"], table)
        for profile in ("home", "eco", "manual"):
            for value in (10, 90):
                with self.subTest(profile=profile, value=value):
                    invalid = deepcopy(table)
                    invalid[profile] = {"humidity": value}
                    with self.assertRaisesRegex(ValueError, "Target outside physical device or room limits"):
                        await r.async_update(r.spec, {"profile_targets": invalid}, operating_mode="dry")
                    self.assertEqual(model.settings_for_mode(r.manager, r.spec, "dry")["profile_targets"], table)

    async def test_legacy_room_surface_targets_survive_method_changes_with_native_limits(self):
        for enabled in (True, False):
            for method in ("off", "manual", "existing"):
                with self.subTest(enabled=enabled, method=method):
                    r = MoldRuntime()
                    raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
                    raw.pop("mode_settings")
                    raw.pop("mode_settings_version")
                    raw["profile_targets"] = {"manual": {"humidity": 60}}
                    profiles = r.manager.entry.data["climate_rooms"]["room"]["profiles"]
                    profiles["home"]["humidity"] = 95
                    profiles["comfort"]["humidity"] = 95
                    saved = deepcopy(profiles)
                    r.manager.entry.options[const.CONF_USE_MOLD] = enabled
                    await r.async_update(r.spec, {"control_mode": method})
                    self.assertEqual(model.settings(r.manager, r.spec)["control_mode"], method)
                    self.assertEqual(r.manager.entry.data["climate_rooms"]["room"]["profiles"], saved)
                    self.assertEqual(model.targets(r.manager, r.spec, r.cap,
                        {**model.settings(r.manager, r.spec), "preset": "comfort"}, {},
                        mold_protection=False)["humidity"], 80)
                    with self.assertRaisesRegex(ValueError, "Target outside physical device or room limits"):
                        await r.async_update(r.spec, {"profile_targets": {"manual": {"humidity": 95}}})

    async def test_profile_surface_target_creates_demand_below_room_rh_and_warning_targets(self):
        for method in ("automatic", "pid"):
            for kind, setter in (("climate", True), ("climate", False), ("dehumidifier", True)):
                with self.subTest(method=method, kind=kind, setter=setter):
                    r = MoldRuntime(method=method, kind=kind, humidity_target=setter)
                    r.surface_reading()
                    r.state.attributes.update(current_humidity=44, humidity=60)
                    info = r.humidity_info()
                    self.assertEqual(info["target_basis"], "mold_surface_rh")
                    self.assertTrue(info["target_ready"])
                    self.assertEqual(info["control_target"], 60)
                    self.assertEqual(info["control_measurement"], 64.4)
                    self.assertFalse(info["mold_protection_required"], "Global warning stays at 70")
                    self.assertTrue(info["mold_control_demand_required"])
                    self.assertLess(info["effective_humidity_target"], 49.4)
                    self.assertTrue(safety.condition(r, r.spec, r.cap, include_automatic=True)["needed"])
                    await r.evaluate()
                    self.assertNotEqual(r.status["status"], "within_target_band")
                    self.assertEqual(len(r.calls), 1, r.status)
                    self.assertEqual(r.calls[0]["service"], "set_hvac_mode" if kind == "climate" else "turn_on")
                    self.assertNotEqual(r.status.get("demand_reason"), "mold_above_limit")

    async def test_satisfied_surface_profile_stays_idle_even_with_warning_or_native_upper_limit(self):
        for warning, maximum in ((50, 80), (70, 40)):
            with self.subTest(warning=warning, maximum=maximum):
                r = MoldRuntime(kind="dehumidifier")
                r.surface_reading()
                for profile in ("home", "comfort"):
                    r.manager.entry.options[model.SETTINGS][r.spec.identifier]["mode_settings"]["dry"][
                        "profile_targets"][profile]["humidity"] = 95
                r.manager.entry.options[const.CONF_THRESHOLDS]["indoor_mold"] = warning
                r.state.attributes["max_humidity"] = maximum
                self.assertFalse(r.humidity_info()["mold_control_demand_required"])
                self.assertFalse(safety.condition(r, r.spec, r.cap)["needed"])
                self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), False)
                await r.evaluate()
                self.assertEqual(r.calls, [])
                self.assertEqual(r.status["status"], "within_target_band")
                self.assertTrue(r.status["pid_target_reached"])
                self.assertEqual(r.status["humidity_demand"]["control_target"], 95)

    async def test_disabled_mold_retains_room_rh_and_invalid_calibration_never_falls_back(self):
        for enabled, factor in ((False, 1.310048), (True, None), (True, 0)):
            with self.subTest(enabled=enabled, factor=factor):
                r = MoldRuntime(kind="dehumidifier")
                r.surface_reading()
                r.manager.entry.options[const.CONF_USE_MOLD] = enabled
                r.manager.entry.options[const.CONF_MOLD_ROOMS]["room"]["calibration_factor"] = factor
                await r.evaluate()
                self.assertEqual(r.calls, [])
                info = r.status["humidity_demand"]
                self.assertEqual(info["control_target"], 60)
                if enabled:
                    self.assertEqual(info["target_basis"], "mold_surface_rh")
                    self.assertFalse(info["target_ready"])
                    self.assertIsNone(info["effective_humidity_target"])
                    self.assertEqual(r.status["status"], "target_unavailable")
                else:
                    self.assertEqual(info["target_basis"], "room_relative_humidity")
                    self.assertEqual(info["effective_humidity_target"], 60)
                    self.assertEqual(r.status["status"], "within_target_band")

    async def test_active_room_profile_and_scoped_override_drive_surface_target_live(self):
        r = MoldRuntime(kind="dehumidifier")
        r.surface_reading()
        profile_targets = {"home": 60, "comfort": 55, "eco": 75, "sleep": 70, "away": 80}
        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
        raw["mode_settings"]["dry"]["profile_targets"] = {
            name: {"humidity": value} for name, value in profile_targets.items()}
        for profile, plan in (
                ("comfort", {"away": "home", "occupancy": "occupied", "sleeping": False}),
                ("eco", {"away": "home", "occupancy": "unoccupied", "sleeping": False, "door_eco_active": True}),
                ("sleep", {"away": "home", "occupancy": "occupied", "sleeping": True}),
                ("away", {"away": "away", "occupancy": "unoccupied", "sleeping": False}),
                ("home", {"away": "home", "occupancy": "unoccupied", "sleeping": False})):
            with self.subTest(profile=profile):
                r.manager.plan = {"window_safe": True, **plan}
                info = r.humidity_info()
                self.assertEqual(model.profile_name(r.cfg, r.manager.plan), profile)
                self.assertEqual(info["control_target"], profile_targets[profile])
                self.assertEqual(safety.condition(r, r.spec, r.cap)["needed"], 64.4 > profile_targets[profile])
        raw["mode_settings"]["dry"]["profile_targets"]["home"]["humidity"] = 85
        self.assertEqual(r.humidity_info()["control_target"], 85)
        self.assertFalse(safety.condition(r, r.spec, r.cap)["needed"])
        r.manager.plan["away"] = "unknown"
        self.assertIsNone(safety.condition(r, r.spec, r.cap)["needed"])

    async def test_legacy_pinned_device_humidity_cannot_differ_from_mold_feedback(self):
        r = MoldRuntime(kind="dehumidifier")
        r.manager.entry.options.pop("room_sources")
        r.sensor("sensor.pinned_humidity", 20, "humidity", "%")
        r.manager.device["humidity_entity"] = "sensor.pinned_humidity"
        info = r.humidity_info()
        measured = r.measurements(r.spec, r.cap)
        self.assertAlmostEqual(info["indoor_humidity"], (55.8 + 20) / 2)
        self.assertEqual(measured["humidity"], info["indoor_humidity"])
        self.assertEqual(set(measured["humidity_selected_entities"]),
                         {"sensor.pinned_humidity", "sensor.room_humidity"})

    async def test_inferred_dry_uses_its_calibrated_mean_while_previous_mode_is_heating(self):
        r = MoldRuntime()
        r.manager.entry.options.pop("room_sources")
        r.sensor("sensor.room_humidity", 95, "humidity", "%")
        r.sensor("sensor.pinned_humidity", 20, "humidity", "%")
        r.manager.device["humidity_entity"] = "sensor.pinned_humidity"
        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
        raw["requested_mode"] = None
        raw["mode_settings"]["heat"] = {"control_mode": "pid"}
        r.record["active_operating_mode"] = "heat"
        before = deepcopy(r.raw())
        self.assertEqual(r.measurements(r.spec, r.cap)["humidity"], 20)
        local = model.settings_for_mode(r.manager, r.spec, "dry")
        info = model.humidity_demand(r.manager, r.spec, r.cap, local, r.manager.plan)
        self.assertEqual(info["indoor_humidity"], 57.5)
        self.assertGreater(info["control_measurement"], info["control_target"])
        await r.evaluate()
        self.assertEqual(r.active_control_mode(r.spec), "dry")
        self.assertEqual(r.calls[0]["data"], {"hvac_mode": "dry"})
        self.assertEqual(r.raw(), before)
        # A real heating deficit still has priority over that same Dry need.
        other = MoldRuntime()
        other.manager.entry.options.pop("room_sources")
        other.sensor("sensor.room_temperature", 15, "temperature", "°C")
        other.sensor("sensor.room_humidity", 95, "humidity", "%")
        other.sensor("sensor.pinned_humidity", 20, "humidity", "%")
        other.manager.device["humidity_entity"] = "sensor.pinned_humidity"
        raw = other.manager.entry.options[model.SETTINGS][other.spec.identifier]
        raw["requested_mode"] = None
        raw["mode_settings"]["heat"] = {"control_mode": "pid"}
        other.record["active_operating_mode"] = "heat"
        await other.evaluate()
        self.assertEqual(other.active_control_mode(other.spec), "heat")
        self.assertEqual(other.calls[0]["data"], {"hvac_mode": "heat"})

    async def test_missing_mold_calibration_does_not_hold_selected_thermal_mode(self):
        r = MoldRuntime()
        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
        raw["requested_mode"] = "heat"
        raw["mode_settings"]["heat"] = {"control_mode": "pid"}
        r.manager.entry.options[const.CONF_MOLD_ROOMS]["room"]["calibration_factor"] = None
        self.assertFalse(model.uses_mold_target(r.manager, r.spec, r.cap, r.cfg))
        self.assertNotEqual(r._gate(r.spec, r.cap, r.cfg, r.manager.plan, "heat"), "target_unavailable")
        await r.evaluate()
        self.assertNotEqual(r.status["status"], "target_unavailable")

    async def test_unresolved_supply_keeps_surface_goal_and_independent_thermal_demand(self):
        r = MoldRuntime()
        r.surface_reading()
        r.state.attributes.update(hvac_modes=["off", "dry", "fan_only"], max_humidity=40)
        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
        raw["requested_mode"] = None
        for profile in ("home", "comfort"):
            raw["mode_settings"]["dry"]["profile_targets"][profile]["humidity"] = 95
            r.manager.entry.data["climate_rooms"]["room"]["profiles"][profile]["humidity"] = 30
        self.assertIsNone(r.active_control_mode(r.spec))
        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), False)
        for profile in ("home", "comfort"):
            raw["mode_settings"]["dry"]["profile_targets"][profile]["humidity"] = 40
            r.manager.entry.data["climate_rooms"]["room"]["profiles"][profile]["humidity"] = 95
        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), True)
        raw["mode_settings"]["dry"]["control_mode"] = "off"
        self.assertIsNot(power.approved_demand(r, r.spec, r.cfg, r.cap), True)
        raw["mode_settings"]["dry"]["control_mode"] = "pid"
        r.state.attributes["hvac_modes"] = ["off", "heat", "cool", "dry"]
        r.manager.entry.options[const.CONF_MOLD_ROOMS]["room"]["calibration_factor"] = None
        r.sensor("sensor.room_temperature", 15, "temperature", "°C")
        self.assertIsNone(r.active_control_mode(r.spec))
        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), True)

    async def test_unresolved_shared_supply_accepts_drying_inside_thermal_band(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                r = MoldRuntime(method=method)
                r.surface_reading()
                raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
                raw["requested_mode"] = None
                raw["mode_settings"]["heat"] = {"control_mode": method}
                raw["mode_settings"]["cool"] = {"control_mode": method}
                before = deepcopy(r.raw())
                self.assertIsNone(r.active_control_mode(r.spec))
                self.assertEqual(r.cap.modes, ("off", "heat", "cool", "dry"))
                self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), True)
                self.assertEqual(r.calls, [], "Demand inspection must not operate the relay")
                self.assertEqual(r.raw(), before, "Demand inspection must not select a mode")

    async def test_unresolved_supply_respects_each_scoped_method_and_target(self):
        r = MoldRuntime()
        r.surface_reading()
        raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
        raw["requested_mode"] = None
        raw["mode_settings"]["heat"] = {"control_mode": "off"}
        raw["mode_settings"]["cool"] = {"control_mode": "off"}
        for method in ("off", "manual", "existing"):
            with self.subTest(method=method):
                raw["mode_settings"]["dry"]["control_mode"] = method
                self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), False)
        raw["mode_settings"]["dry"]["control_mode"] = "automatic"
        for profile in ("home", "comfort"):
            raw["mode_settings"]["dry"]["profile_targets"][profile]["humidity"] = 62.4
        self.assertIsNone(power.approved_demand(r, r.spec, r.cfg, r.cap),
                          "Scoped Automatic keeps its deadband despite the legacy PID method")
        raw["mode_settings"]["dry"]["control_mode"] = "pid"
        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), True)
        raw["mode_settings"]["dry"]["control_mode"] = "off"
        r.sensor("sensor.room_temperature", 18, "temperature", "°C")
        raw["mode_settings"]["heat"] = {"control_mode": "pid", "profile_targets": {
            "home": {"heat": 17}, "comfort": {"heat": 17}}}
        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), False,
                      "The scoped heat target overrides the room target")
        raw["mode_settings"]["heat"]["profile_targets"]["comfort"]["heat"] = 19
        self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), True)

    async def test_unresolved_supply_keeps_unknown_drying_separate_from_thermal_demand(self):
        for missing in ("calibration", "weather", "humidity"):
            with self.subTest(missing=missing):
                r = MoldRuntime()
                r.surface_reading()
                raw = r.manager.entry.options[model.SETTINGS][r.spec.identifier]
                raw["requested_mode"] = None
                raw["mode_settings"]["heat"] = {"control_mode": "pid"}
                raw["mode_settings"]["cool"] = {"control_mode": "pid"}
                if missing == "calibration":
                    r.manager.entry.options[const.CONF_MOLD_ROOMS]["room"]["calibration_factor"] = None
                else:
                    r.states.pop("weather.home" if missing == "weather" else "sensor.room_humidity")
                self.assertIsNone(power.approved_demand(r, r.spec, r.cfg, r.cap),
                                  "Missing Dry evidence cannot authorize turning the supply off")
                r.sensor("sensor.room_temperature", 15, "temperature", "°C")
                self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), True,
                              "A verified heat deficit remains independently eligible")
                self.assertEqual(r.calls, [])

    async def test_surface_80_over_70_starts_dry_below_saved_60_for_automatic_and_pid(self):
        for method in ("automatic", "pid"):
            for kind, setter in (("climate", True), ("climate", False), ("dehumidifier", True)):
                with self.subTest(method=method, kind=kind, setter=setter):
                    r = MoldRuntime(method=method, kind=kind, humidity_target=setter)
                    saved = deepcopy(r.raw())
                    self.assertEqual(r.measurements(r.spec, r.cap)["humidity"], 55.8)
                    info = r.humidity_info()
                    self.assertEqual(info["mold_surface_rh"], 80)
                    self.assertEqual(info["mold_surface_limit"], 70)
                    self.assertEqual(info["requested_humidity_target"], 60)
                    self.assertLess(info["effective_humidity_target"], 55.8)
                    await r.evaluate()
                    self.assertEqual(len(r.calls), 1, r.status)
                    call = r.calls[0]
                    self.assertEqual(call["service"], "set_hvac_mode" if kind == "climate" else "turn_on")
                    self.assertEqual(call["data"], {"hvac_mode": "dry"} if kind == "climate" else {})
                    self.assertEqual(r.record["pending"]["phase"], "commanded")
                    self.assertFalse(r.record["power"], "A service return is not a native ON ACK")
                    self.assertEqual(r.status["demand_reason"], "mold_above_limit")
                    self.assertEqual(r.status["humidity_demand"]["effective_humidity_target"],
                                     info["effective_humidity_target"])
                    self.assertEqual(r.raw(), saved)

    async def test_unavailable_room_feedback_cannot_start_or_reuse_old_mold_demand(self):
        for method in ("automatic", "pid"):
            for source in ("humidity", "temperature", "weather"):
                with self.subTest(method=method, source=source):
                    r = MoldRuntime(method=method)
                    self.assertTrue(r.humidity_info()["mold_protection_required"])
                    if source == "humidity":
                        r.sensor("sensor.room_humidity", 55.8, "humidity", "%", age=601)
                    elif source == "temperature":
                        r.sensor("sensor.room_temperature", 20, "temperature", "°C", restored=True)
                    else:
                        r.weather(age=5401)
                    await r.evaluate()
                    self.assertEqual(r.calls, [], r.status)
                    info = r.status["humidity_demand"]
                    self.assertEqual(info["status"], "inputs_unavailable")
                    self.assertFalse(info["mold_protection_required"])
                    self.assertIsNone(info["effective_humidity_target"])
                    self.assertFalse(info["target_ready"])
                    self.assertEqual(r.status["status"], "target_unavailable")

    async def test_native_sensor_below_goal_cannot_cancel_room_mold_demand_or_allow_a_pre_ack_extreme(self):
        for method in ("automatic", "pid"):
            for kind in ("climate", "dehumidifier"):
                with self.subTest(method=method, kind=kind):
                    r = MoldRuntime(method=method, kind=kind)
                    effective = r.humidity_info()["effective_humidity_target"]
                    r.state.attributes["current_humidity"] = 35
                    self.assertGreater(effective, 35, "A native humidistat using the room goal would stay satisfied")
                    self.assertEqual(r.measurements(r.spec, r.cap)["humidity"], 55.8)
                    self.assertEqual(r.humidity_info()["mold_surface_rh"], 80)
                    await r.evaluate()
                    self.assertEqual(len(r.calls), 1)
                    await r.evaluate()
                    self.assertEqual(len(r.calls), 1, "No humidity write before actual ON/mode feedback")
                    r.report(mode="dry" if kind == "climate" else "on")
                    await r.evaluate()
                    self.assertIn(r.primary, r.record["power"])
                    # HEM owns the ON/OFF actuator and uses independent room
                    # feedback. The appliance's own lower humidity must not
                    # veto an ON period required by the selected room inputs.
                    native_goal = r.state.attributes["min_humidity"]
                    self.assertEqual(r.calls[-1]["service"], "set_humidity", r.status)
                    self.assertEqual(r.calls[-1]["data"], {"humidity": native_goal})
                    self.assertEqual(r.record["pending"]["expected"], {"attributes": {"humidity": native_goal}})
                    self.assertEqual(r.state.attributes["humidity"], 60, "Service success is not a target ACK")
                    r.state.attributes["humidity"] = native_goal
                    await r.evaluate()
                    self.assertIsNone(r.record["pending"])
                    self.assertEqual(r.status["humidity_demand"]["effective_humidity_target"], effective)
                    self.assertEqual(r.status["demand_reason"], "mold_above_limit")
                    self.assertEqual([call["data"]["humidity"] for call in r.calls
                                      if call["service"] == "set_humidity"], [native_goal])
                    self.assertEqual(model.targets(r.manager, r.spec, r.cap, r.cfg, r.manager.plan,
                                                   mold_protection=False)["humidity"], 60)

    async def test_dry_without_a_native_humidity_setter_remains_mode_only_after_ack(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                r = MoldRuntime(method=method, humidity_target=False)
                self.assertEqual(r.state.attributes["current_humidity"], 47)
                await r.evaluate()
                self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "dry"})
                r.report(mode="dry")
                await r.evaluate()
                self.assertEqual(len(r.calls), 1)
                self.assertFalse(any(call["service"] == "set_humidity" for call in r.calls))
                self.assertEqual(r.status["demand_reason"], "mold_above_limit")
                self.assertAlmostEqual(r.status["humidity_demand"]["effective_humidity_target"], 41.85)

    async def test_pid_mold_target_cutoff_preserves_real_minimum_on_until_off_ack(self):
        for setter in (False, True):
            with self.subTest(native_humidity_setter=setter):
                r = MoldRuntime(method="pid", humidity_target=setter)
                effective = r.humidity_info()["effective_humidity_target"]
                await r.evaluate()
                r.report(mode="dry")
                await r.evaluate()
                if setter:
                    self.assertEqual(r.calls[-1]["data"], {"humidity": r.cap.min_humidity})
                    r.state.attributes["humidity"] = r.cap.min_humidity
                    await r.evaluate()
                self.assertEqual(r._memory[r.spec.identifier][0][0], "humidity")
                self.assertAlmostEqual(r._memory[r.spec.identifier][0][1], effective)
                original = deepcopy(r.record["power"][r.primary])
                commanded = len(r.calls)
                r.sensor("sensor.room_humidity", effective, "humidity", "%")
                await r.evaluate(599)
                self.assertEqual(len(r.calls), commanded, "Satisfied humidity does not shorten native physical dwell")
                self.assertEqual(r.record["power"][r.primary], original)
                self.assertTrue(r.status["pid_target_reached"])
                self.assertEqual(r.status["pid_control_target"], effective)
                self.assertEqual(r.status["status"], "minimum_on_hold")
                await r.evaluate(1)
                self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
                self.assertEqual(r.record["power"][r.primary], original, "OFF service success is not its ACK")
                r.report(mode="off")
                await r.evaluate()
                self.assertNotIn(r.primary, r.record["power"])
                self.assertEqual(r.record["off_at"][r.primary], r.now)
                self.assertEqual(model.targets(r.manager, r.spec, r.cap, r.cfg, r.manager.plan,
                                               mold_protection=False)["humidity"], 60)

    async def test_native_unavailability_keeps_pending_intent_and_does_not_report_mold_clear(self):
        r = MoldRuntime()
        await r.evaluate()
        pending = deepcopy(r.record["pending"])
        r.report(mode="unavailable")
        await r.evaluate(60)
        self.assertEqual(len(r.calls), 1)
        self.assertEqual(r.record["pending"], pending)
        self.assertEqual(r.status["status"], "waiting_for_physical_device")
        self.assertTrue(r.status["humidity_demand"]["mold_protection_required"])
        self.assertEqual(r.status["demand_reason"], "mold_above_limit")

    async def test_minimum_humidity_limit_cannot_hide_an_unresolved_mold_problem(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                r = MoldRuntime(method=method, minimum=60)
                await r.evaluate()
                self.assertEqual(r.calls, [])
                self.assertNotEqual(r.status["status"], "within_target_band")
                info = r.status["humidity_demand"]
                self.assertTrue(info["mold_protection_required"])
                self.assertEqual(info["status"], "mold_target_blocked_by_limits")
                self.assertEqual(info["effective_humidity_target"], 60)
                self.assertEqual(r.status["demand_reason"], "mold_above_limit")
                self.assertEqual(r.status["status"], "target_outside_device_limits")
                self.assertFalse(r.status.get("pid_target_reached", False))

    async def test_limited_controller_reduces_toward_safe_bound_then_reports_unmet_target(self):
        r = MoldRuntime(kind="dehumidifier", minimum=50)
        self.assertTrue(r.humidity_info()["mold_target_limited"])
        self.assertFalse(r.humidity_info()["target_blocked_by_limits"])
        await r.evaluate()
        self.assertEqual(r.calls[-1]["service"], "turn_on")
        r.report(mode="on")
        await r.evaluate()
        r.state.attributes["humidity"] = 50
        await r.evaluate()
        r.sensor("sensor.room_humidity", 50, "humidity", "%")
        await r.evaluate(600)
        self.assertEqual(r.calls[-1]["service"], "turn_off")
        r.report(mode="off")
        await r.evaluate()
        self.assertTrue(r.status["humidity_demand"]["mold_control_demand_required"])
        self.assertTrue(r.status["humidity_demand"]["target_blocked_by_limits"])
        self.assertEqual(r.status["status"], "target_outside_device_limits")
        self.assertFalse(r.status["pid_target_reached"])

    async def test_high_mold_inhibits_humidifier_native_and_upstream_wake(self):
        for method in ("automatic", "pid"):
            for supply in (False, True):
                with self.subTest(method=method, supply=supply):
                    # The native/room floor intentionally makes a numerical
                    # target alone unable to prevent humidification here.
                    r = MoldRuntime(method=method, kind="humidifier", supply=supply, minimum=60)
                    self.assertTrue(r.humidity_info()["mold_protection_required"])
                    self.assertIs(power.approved_demand(r, r.spec, r.cfg, r.cap), False)
                    check = safety.condition(r, r.spec, r.cap, include_automatic=True)
                    self.assertIs(check["needed"], False)
                    self.assertEqual(r._gate(r.spec, r.cap, r.cfg, r.manager.plan, "auto"), "mold_above_limit")
                    await r.evaluate()
                    self.assertEqual(r.calls, [], r.status)
                    self.assertFalse(r.record.get("pending"))
                    self.assertFalse(r.record.get("upstream", {}).get("pending"))
                    self.assertEqual(r.status["demand_reason"], "mold_above_limit")


if __name__ == "__main__":
    unittest.main(verbosity=2)

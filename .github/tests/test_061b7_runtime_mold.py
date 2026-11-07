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
b["base"]["extract"](ROOT / "equipment_runtime.py", ("measurements",), production.__dict__)


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
                    self.assertEqual(info["effective_humidity_target"], 60)
                    if source == "humidity":
                        self.assertEqual(r.status["status"], "control_measurement_missing_or_stale")

    async def test_native_sensor_47_cannot_cancel_room_mold_demand_or_allow_a_pre_ack_extreme(self):
        for method in ("automatic", "pid"):
            for kind in ("climate", "dehumidifier"):
                with self.subTest(method=method, kind=kind):
                    r = MoldRuntime(method=method, kind=kind)
                    effective = r.humidity_info()["effective_humidity_target"]
                    self.assertEqual(r.state.attributes["current_humidity"], 47)
                    self.assertGreater(effective, 47, "A native humidistat using the room goal would stay satisfied")
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
                    # feedback. The appliance's own 47% sensor must not veto
                    # an ON period simply because the room goal is 48%.
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
                self.assertAlmostEqual(r.status["humidity_demand"]["effective_humidity_target"], 48.825)

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

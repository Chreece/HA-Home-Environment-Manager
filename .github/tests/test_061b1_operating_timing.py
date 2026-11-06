"""Native operating holds through real settings, dispatch and acknowledgement.

The fixture supplies HA state/service/registry transport and already-qualified
room measurements/presence. Settings, timing normalization, capability/permission
selection, async_update, tick, _power, _send, _reconcile and relay dwell decisions
are production code. No Home Assistant instance or physical device is used.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_onoff_native_extrema.py"))
PACKAGE, PRIMARY, SPEC = (base[key] for key in ("PACKAGE", "PRIMARY", "SPEC"))
sys.modules[PACKAGE].__path__ = [str(ROOT)]
# Replace the older harness's isolated model methods with the complete actual
# model. Its state/service/registry transport remains the same.
sys.modules.pop(f"{PACKAGE}.equipment_model")
model = importlib.import_module(f"{PACKAGE}.equipment_model")
model.plan_for = lambda manager, spec: dict(manager.plan)  # Qualified room input.
production = base["production"]
production.model = model
production.HomeAssistantError = ValueError
sys.modules[f"{PACKAGE}.equipment_pid_safety"].model = model
sys.modules.pop(f"{PACKAGE}.device_activation")
importlib.import_module(f"{PACKAGE}.device_activation")
discovery = ModuleType(f"{PACKAGE}.discovery")
discovery.entity_area = production.entity_area
sys.modules[discovery.__name__] = discovery
sys.modules.pop(f"{PACKAGE}.equipment_power_switch")
supply = importlib.import_module(f"{PACKAGE}.equipment_power_switch")
phase = base["phase"]
base["extract"](ROOT / "equipment_runtime.py", ("async_update", "_lock"), production.__dict__)


class SettingsManager:
    def __init__(self, hass, *, profile=None, room=None, device=None):
        native = {
            "auto_control": True, "hardware_confirmed": True, "method": "native",
            "fan_purpose": "extraction", "sleep_behavior": "normal",
            **(device or {}),
        }
        area = {
            "enabled": True, "allow_actuation": True,
            "selected_devices": [PRIMARY], "device_settings": {PRIMARY: native},
            "profiles": {
                name: {"heat_c": 21.0, "cool_c": 26.0, "humidity": 50.0}
                for name in ("home", "comfort")
            },
            **(room or {}),
        }
        self.hass, self._active = hass, False
        self.entry = N(entry_id="test_entry", options={}, data={
            "areas": ["room"], "climate_rooms": {"room": area},
            model.SETTINGS: {SPEC.identifier: {
                "control_mode": "pid", "requested_mode": "heat", "preset": "none",
                "timed_setpoint_sequence": False, **(profile or {}),
            }},
        })
        self.plan = {"away": "home", "occupancy": "occupied", "window_safe": True}
        self.device = native
        self._device_hierarchy = {"controllers": {SPEC.identifier: {"spec": SPEC}}}

    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}


class TimingRuntime(base["NativeRuntime"]):
    def __init__(self, *, profile=None, room=None, device=None, off_age=1200.0):
        super().__init__(off_age=off_age)
        self.manager = SettingsManager(self.hass, profile=profile, room=room, device=device)
        self.manager.equipment = self
        self._locks, self._pid_passive_observers = {}, {}
        self.hass.config_entries = N(async_update_entry=self.update_entry)

    @staticmethod
    def update_entry(entry, *, options):
        entry.options = deepcopy(options)

    @property
    def cfg(self):
        return model.settings(self.manager, SPEC)

    @property
    def cap(self):
        return model.capabilities(self.manager, SPEC)

    def own_running(self, age=100.0):
        self.report(mode=self.cfg["requested_mode"])
        self.state.last_changed = datetime.fromtimestamp(self.now - age, timezone.utc)
        minimum, _, maximum = model.timing(self.manager, SPEC, self.cap)
        self.record["power"][PRIMARY] = {
            "since": self.now - age, "min_on": minimum, "max_on": maximum,
        }
        self.record["baseline"][PRIMARY] = production.snapshot(self.state)

    async_update = production.async_update
    _lock = production._lock


class NativeOperatingTimingTests(unittest.IsolatedAsyncioTestCase):
    async def test_minimum_only_edit_preserves_other_minimum_maximum_and_supply(self):
        cases = (
            ({}, {}, (600.0, 600.0, 7200.0), (600.0, 600.0)),
            ({"min_on_s": 120, "min_off_s": 120, "max_on_s": 1800}, {},
             (600.0, 600.0, 1800.0), (600.0, 600.0)),
            ({"min_on_s": 900, "min_off_s": 1200, "max_on_s": 3600}, {},
             (900.0, 1200.0, 3600.0), (900.0, 1200.0)),
            ({}, {"min_on_s": 900, "min_off_s": 1200, "max_on_s": 1800},
             (900.0, 1200.0, 1800.0), (900.0, 1200.0)),
        )
        for device, room, old_native, old_supply in cases:
            with self.subTest(device=device, room=room):
                runtime = TimingRuntime(device=device, room=room)
                before = deepcopy(runtime.manager.settings)
                self.assertEqual(model.timing(runtime.manager, SPEC, runtime.cap), old_native)
                self.assertEqual(supply.device_supply_dwell(runtime, SPEC, runtime.cfg), old_supply)
                self.assertNotIn("_native_timing_version", runtime.cfg)
                self.assertEqual(runtime.manager.settings, before, "Reading is not migration")
                await runtime.async_update(SPEC, {"min_on_seconds": 0})
                self.assertEqual(runtime.cfg["_native_timing_version"], 1)
                self.assertEqual(model.timing(runtime.manager, SPEC, runtime.cap),
                                 (0.0, old_native[1], old_native[2]))
                self.assertEqual(supply.device_supply_dwell(runtime, SPEC, runtime.cfg), old_supply)
                self.assertEqual(runtime.calls, [], "Saving a preference sends no native command")
                await runtime.async_update(SPEC, {"min_off_seconds": 7})
                self.assertEqual(model.timing(runtime.manager, SPEC, runtime.cap),
                                 (0.0, 7.0, old_native[2]))
                self.assertEqual(supply.device_supply_dwell(runtime, SPEC, runtime.cfg), old_supply)
                self.assertEqual(runtime.manager.settings["climate_rooms"], before["climate_rooms"])

    async def test_unrelated_edit_does_not_normalize_legacy_timing(self):
        runtime = TimingRuntime(room={"min_on_s": 900, "min_off_s": 1200, "max_on_s": 1800})
        before = model.timing(runtime.manager, SPEC, runtime.cap)
        await runtime.async_update(SPEC, {"quiet_percentage": 31})
        self.assertNotIn("_native_timing_version", runtime.cfg)
        self.assertNotIn("_power_switch_min_on_seconds", runtime.cfg)
        # Existing full-settings saves keep the legacy resolver's behavior.
        self.assertEqual(before, (900.0, 1200.0, 1800.0))
        self.assertEqual(supply.device_supply_dwell(runtime, SPEC, runtime.cfg), (900.0, 1200.0))
        self.assertEqual(runtime.calls, [])

    async def test_active_cycle_retains_its_minimum_then_zero_applies_next_cycle(self):
        runtime = TimingRuntime(device={"min_on_s": 900, "min_off_s": 1200})
        runtime.own_running(age=10)
        original = deepcopy(runtime.record)
        await runtime.async_update(SPEC, {"min_on_seconds": 0, "min_off_seconds": 0})
        self.assertEqual(runtime.record, original, "No physical history changes when saved")
        self.assertEqual(runtime.calls, [])
        await runtime._power(SPEC, runtime.cap, "off", automatic=True)
        self.assertEqual(runtime.calls, [])
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")
        runtime.now += 890
        await runtime._power(SPEC, runtime.cap, "off", automatic=True)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertIn(PRIMARY, runtime.record["power"], "Service return is not an OFF ACK")
        runtime.report(mode="off")
        await runtime._reconcile(SPEC)
        self.assertNotIn(PRIMARY, runtime.record["power"])
        self.assertEqual(runtime.record["off_at"][PRIMARY], runtime.now)
        await runtime._power(SPEC, runtime.cap, "heat", automatic=True)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "heat"})
        self.assertEqual(runtime.record["pending"]["min_on"], 0.0)
        runtime.report(mode="heat")
        await runtime._reconcile(SPEC)
        self.assertEqual(runtime.record["power"][PRIMARY]["min_on"], 0.0)
        await runtime._power(SPEC, runtime.cap, "off", automatic=True)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(len(runtime.calls), 3)
        self.assertEqual(supply.device_supply_dwell(runtime, SPEC, runtime.cfg), (900.0, 1200.0))

    async def test_pending_command_keeps_original_minimum_until_actual_ack(self):
        runtime = TimingRuntime()
        await runtime._power(SPEC, runtime.cap, "heat", automatic=True)
        pending = deepcopy(runtime.record["pending"])
        off_at, baseline = deepcopy(runtime.record["off_at"]), deepcopy(runtime.record["baseline"])
        self.assertEqual(pending["min_on"], 600.0)
        await runtime.async_update(SPEC, {"min_on_seconds": 0, "min_off_seconds": 0})
        self.assertEqual(runtime.record["pending"], pending)
        self.assertEqual(runtime.record["baseline"], baseline)
        self.assertEqual(runtime.record["off_at"], off_at)
        self.assertEqual(runtime.record["power"], {})
        self.assertEqual(len(runtime.calls), 1, "Preference save neither sends nor retries")
        runtime.report(mode="heat")
        await runtime._reconcile(SPEC)
        self.assertEqual(runtime.record["power"][PRIMARY]["min_on"], 600.0)
        await runtime._power(SPEC, runtime.cap, "off", automatic=True)
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")

    async def test_small_seconds_control_actual_native_transition_boundaries(self):
        runtime = TimingRuntime(off_age=0)
        await runtime.async_update(SPEC, {"min_on_seconds": 1, "min_off_seconds": 7})
        await runtime._power(SPEC, runtime.cap, "heat", automatic=True)
        self.assertEqual(runtime.calls, [])
        self.assertEqual(runtime.statuses[-1][0], "minimum_off_hold")
        runtime.now += 7
        await runtime._power(SPEC, runtime.cap, "heat", automatic=True)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "heat"})
        runtime.report(mode="heat")
        await runtime._reconcile(SPEC)
        await runtime._power(SPEC, runtime.cap, "off", automatic=True)
        self.assertEqual(len(runtime.calls), 1)
        runtime.now += 1
        await runtime._power(SPEC, runtime.cap, "off", automatic=True)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(len(runtime.calls), 2)

    async def test_zero_minima_tick_still_requires_ack_and_fresh_target_demand(self):
        runtime = TimingRuntime(off_age=0)
        await runtime.async_update(SPEC, {"min_on_seconds": 0, "min_off_seconds": 0})
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "heat"}, runtime.statuses)
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.calls), 1, "Zero dwell does not bypass a pending ACK")
        runtime.report(mode="heat")
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"temperature": 35.0}, runtime.statuses)
        self.assertEqual(runtime.record["power"][PRIMARY]["min_on"], 0.0)
        runtime.report(temperature=35.0)
        await runtime.tick(SPEC)
        self.assertIsNone(runtime.record["pending"])
        runtime.measurement = 21.0
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"}, runtime.statuses)
        self.assertEqual(len(runtime.calls), 3)

    async def test_zero_native_does_not_reduce_relay_dwell_or_idle_cooldown(self):
        runtime = TimingRuntime(device={"min_on_s": 900, "min_off_s": 1200})
        await runtime.async_update(SPEC, {"min_on_seconds": 0, "min_off_seconds": 0})
        cfg, cap, now = runtime.cfg, runtime.cap, runtime.now
        for age, expected in ((899, False), (900, True)):
            relay = {"on_at": now-age}
            self.assertEqual(supply.supply_minimum_on(runtime, SPEC, cfg, cap, relay, now), expected)
        for age, expected in ((1199, False), (1200, True)):
            relay = {"off_at": now-age}
            self.assertEqual(supply.supply_minimum_off(runtime, SPEC, cfg, cap, relay, runtime.state, now), expected)
        self.assertFalse(supply.supply_minimum_on(
            runtime, SPEC, cfg, cap, {"on_at": now-900, "on_min_seconds": 1800}, now))
        self.assertFalse(supply.supply_minimum_off(
            runtime, SPEC, cfg, cap, {"off_at": now-1200, "off_min_seconds": 1800}, runtime.state, now))
        self.assertFalse(supply.idle_cooldown_ready(cfg, {"idle_since": now-599}, now, now-1000))
        self.assertTrue(supply.idle_cooldown_ready(cfg, {"idle_since": now-600}, now, now-1000))
        self.assertFalse(supply.idle_cooldown_ready(cfg, {"idle_since": now-600}, now, now-59))
        runtime.state.state = "unavailable"
        self.assertEqual(supply.device_supply_dwell(runtime, SPEC, cfg), (900.0, 1200.0))

    async def test_invalid_native_and_frozen_relay_values_fail_closed(self):
        runtime = TimingRuntime()
        for field in ("min_on_seconds", "min_off_seconds"):
            for invalid in (-1, True, float("nan"), float("inf")):
                with self.subTest(field=field, invalid=invalid):
                    before = deepcopy(runtime.manager.entry.options)
                    with self.assertRaises(ValueError):
                        await runtime.async_update(SPEC, {field: invalid})
                    self.assertEqual(runtime.manager.entry.options, before)
        await runtime.async_update(SPEC, {"min_on_seconds": 0, "min_off_seconds": 0})
        for field in ("_power_switch_min_on_seconds", "_power_switch_min_off_seconds"):
            for invalid in (None, 0, 599, True, float("nan"), float("inf")):
                with self.subTest(field=field, invalid=invalid):
                    cfg = {**runtime.cfg, field: invalid}
                    self.assertIsNone(supply.device_supply_dwell(runtime, SPEC, cfg, runtime.cap))
        for version in (True, 1.0, 2, "1"):
            cfg = {**runtime.cfg, "_native_timing_version": version}
            with self.assertRaises(ValueError):
                model.timing(runtime.manager, SPEC, runtime.cap, config=cfg)
            self.assertIsNone(supply.device_supply_dwell(runtime, SPEC, cfg, runtime.cap))
        self.assertEqual(runtime.calls, [])

    def test_fan_migration_preserves_distinct_legacy_native_and_supply_values(self):
        runtime = TimingRuntime(room={"fan_power_min_on_s": 180, "fan_power_min_off_s": 300,
                                      "fan_power_max_on_s": 1800})
        fan = N(identifier="fan_controller", area_id="room", source_device_id="fan",
                source_entities=("fan.native",))
        cap = model.Capabilities("fan.native", "fan", ("off", "fan_only"))
        cfg = model.settings(runtime.manager, fan)
        self.assertEqual(model.timing(runtime.manager, fan, cap), (180.0, 300.0, 1800.0))
        self.assertEqual(supply.device_supply_dwell(runtime, fan, cfg, cap), (600.0, 600.0))
        normalized = model.normalize_native_timing(runtime.manager, fan, cap, cfg)
        normalized["min_on_seconds"] = 0
        self.assertEqual(model.timing(runtime.manager, fan, cap, config=normalized), (0.0, 300.0, 1800.0))
        self.assertEqual(supply.device_supply_dwell(runtime, fan, normalized, cap), (600.0, 600.0))
        self.assertNotIn("_native_timing_version", cfg)

    def test_pwm_zero_and_asymmetric_minima_preserve_real_on_off_windows(self):
        for on, off in ((0, 0), (0, 60), (60, 0)):
            with self.subTest(min_on=on, min_off=off):
                cycle = phase.safe_binary_pwm_cycle(25, 600, on, off)
                self.assertEqual(cycle, 600.0)
                self.assertTrue(model.duty_on(25, 0, cycle, on, off, starting=True))
                self.assertTrue(model.duty_on(25, 149, cycle, on, off))
                self.assertFalse(model.duty_on(25, 150, cycle, on, off))
                self.assertEqual(phase.binary_pwm_off_phase(25, 150, cycle, on, off, starting=True)["state"], "off_window")
                self.assertTrue(model.duty_on(25, 600, cycle, on, off, starting=True))
        self.assertEqual(phase.safe_binary_pwm_cycle(18, 1800, 600, 600), 3600.0)
        for demand, cycle, on, off in ((25, 0, 0, 0), (25, 600, -1, 0), (25, 600, 0, -1),
                                       (25, 600, True, 0), (25, 600, 0, float("nan")),
                                       (25, float("inf"), 0, 0)):
            with self.subTest(demand=demand, cycle=cycle, min_on=on, min_off=off):
                self.assertIsNone(phase.safe_binary_pwm_cycle(demand, cycle, on, off))
                self.assertFalse(model.duty_on(demand, 0, cycle, on, off))
        self.assertIsNone(phase.safe_binary_pwm_cycle(0, 600, 0, 0))
        self.assertFalse(model.duty_on(0, 0, 600, 0, 0))
        self.assertEqual(phase.binary_pwm_off_phase(0, 0, 600, 0, 0, starting=True)["state"], "zero_demand")


if __name__ == "__main__":
    unittest.main()

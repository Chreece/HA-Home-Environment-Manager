"""Minute number inputs retain seconds in the real settings/power lifecycle."""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
f = runpy.run_path(str(ROOT / ".github/tests/test_061b1_operating_timing.py"))
Runtime, SPEC, PRIMARY, model, supply, PACKAGE = (
    f[key] for key in ("TimingRuntime", "SPEC", "PRIMARY", "model", "supply", "PACKAGE"))
names = importlib.import_module(PACKAGE + ".equipment_name_catalog")
ns = {
    "__name__": PACKAGE + ".minute_entities", "__package__": PACKAGE,
    "model": model, "equipment": model, "DOMAIN": "environment_manager",
    "localized_equipment_name": names.localized_equipment_name,
    "callback": lambda fn: fn, "NumberEntity": type("NumberEntity", (), {}),
    "NumberMode": N(BOX="box"), "EntityCategory": N(CONFIG="config"),
}
for filename, name in (("equipment_entity.py", "EquipmentEntity"), ("number.py", "EquipmentNumber")):
    node = next(n for n in ast.parse((ROOT / filename).read_text()).body
                if isinstance(n, ast.ClassDef) and n.name == name)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    tree = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
    exec(compile(tree, filename, "exec"), ns)
Number = ns["EquipmentNumber"]
FIELDS = ("min_on_seconds", "min_off_seconds", "max_on_seconds")


def runtime(**profile):
    return Runtime(profile={"_native_timing_version": 1, "min_on_seconds": 600.,
                            "min_off_seconds": 600., "max_on_seconds": 7200., **profile})


class TimingMinutes(unittest.IsolatedAsyncioTestCase):
    def test_bounds_units_step_and_device_identity(self):
        r = runtime()
        for domain in ("climate", "humidifier", "fan", None):
            cap = model.Capabilities(PRIMARY, domain, ("off", "heat")) if domain else None
            with patch.object(model, "capabilities", return_value=cap):
                expected = ((0., 120., 1 / 60), (0., 240., 1 / 60),
                            (15., 480. if domain in ("climate", "humidifier") else 1440., 1.))
                for key, bounds in zip(FIELDS, expected):
                    number = Number(r.manager, SPEC, key)
                    self.assertEqual((number._attr_native_min_value,
                                      number._attr_native_max_value, number._attr_native_step), bounds)
                    self.assertEqual(number._attr_native_unit_of_measurement, "min")
                    self.assertEqual(number._attr_unique_id, SPEC.identifier + "_" + key)
                    self.assertEqual(number._attr_translation_key, "equipment_" + key)

    def test_old_saved_seconds_are_read_in_minutes_without_migration(self):
        for version in (None, 1):
            profile = dict(min_on_seconds=900., min_off_seconds=1200., max_on_seconds=3600.)
            if version is not None:
                profile["_native_timing_version"] = version
            r = Runtime(profile=profile)
            before = deepcopy(r.manager.entry.data), deepcopy(r.manager.entry.options)
            values = [Number(r.manager, SPEC, key).native_value for key in FIELDS]
            self.assertEqual(values, [15., 20., 60.])
            self.assertEqual(model.timing(r.manager, SPEC, r.cap), (900., 1200., 3600.))
            self.assertEqual((r.manager.entry.data, r.manager.entry.options), before)
            self.assertEqual(r.calls, [])

    async def test_fractional_minute_save_crosses_real_validator_and_preserves_legacy_supply(self):
        r = Runtime(device={"min_on_s": 900, "min_off_s": 1200, "max_on_s": 3600})
        number = Number(r.manager, SPEC, "min_on_seconds")
        self.assertEqual(number.native_value, 15.)
        await number.async_set_native_value(0.5)
        self.assertEqual(r.manager.entry.options[model.SETTINGS][SPEC.identifier]["min_on_seconds"], 30.)
        self.assertEqual(model.timing(r.manager, SPEC, r.cap), (30., 1200., 3600.))
        self.assertEqual(supply.device_supply_dwell(r, SPEC, r.cfg), (900., 1200.))
        self.assertEqual(Number(r.manager, SPEC, "min_on_seconds").native_value, 0.5)
        self.assertEqual(r.calls, [])

    async def test_repeated_read_write_reload_preserves_exact_saved_seconds(self):
        r = runtime(min_on_seconds=0., min_off_seconds=0.)
        number = Number(r.manager, SPEC, "min_on_seconds")
        for seconds in (1., 37., 37.125, 61.01):
            await number.async_set_native_value(seconds / 60.)
            saved = r.cfg["min_on_seconds"]
            self.assertAlmostEqual(saved, seconds, places=12)
            for _ in range(5):
                number = Number(r.manager, SPEC, "min_on_seconds")
                await number.async_set_native_value(number.native_value)
                self.assertEqual(r.cfg["min_on_seconds"], saved)
        self.assertEqual(r.calls, [])

    async def test_minute_edit_preserves_running_ownership_and_original_minimum(self):
        r = runtime(min_on_seconds=900., min_off_seconds=1200.)
        r.own_running(age=100.)
        power, off_at = deepcopy(r.record["power"]), deepcopy(r.record["off_at"])
        pending = deepcopy(r.record["pending"])
        await Number(r.manager, SPEC, "min_on_seconds").async_set_native_value(0.5)
        self.assertEqual(r.cfg["min_on_seconds"], 30.)
        self.assertEqual(r.record["power"], power)
        self.assertEqual(r.record["off_at"], off_at)
        self.assertEqual(r.record["pending"], pending)
        self.assertEqual(r.calls, [])
        await r._power(SPEC, r.cap, "off", automatic=True)
        self.assertEqual(r.statuses[-1][0], "minimum_on_hold")
        self.assertEqual(r.calls, [])
        r.now += 800.
        await r._power(SPEC, r.cap, "off", automatic=True)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(r.record["power"], power, "OFF dispatch remains unacknowledged")

    async def test_fractional_minutes_govern_real_physical_boundaries_in_seconds(self):
        r = Runtime(profile={"_native_timing_version": 1}, off_age=0)
        await Number(r.manager, SPEC, "min_on_seconds").async_set_native_value(0.5)
        await Number(r.manager, SPEC, "min_off_seconds").async_set_native_value(1.25)
        self.assertEqual(model.timing(r.manager, SPEC, r.cap), (30., 75., 7200.))
        await r._power(SPEC, r.cap, "heat", automatic=True)
        self.assertEqual(r.calls, [])
        r.now += 75.
        await r._power(SPEC, r.cap, "heat", automatic=True)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "heat"})
        self.assertFalse(r.record["power"])
        r.report(mode="heat")
        await r._reconcile(SPEC)
        self.assertEqual(r.record["power"][PRIMARY]["min_on"], 30.)
        r.now += 29.999
        await r._power(SPEC, r.cap, "off", automatic=True)
        self.assertEqual(len(r.calls), 1)
        r.now += .001
        await r._power(SPEC, r.cap, "off", automatic=True)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertIn(PRIMARY, r.record["power"])

    async def test_maximum_still_exceeds_minimum_and_rejects_invalid_minute_inputs(self):
        r = runtime(min_on_seconds=1200., max_on_seconds=3600.)
        number = Number(r.manager, SPEC, "max_on_seconds")
        original = deepcopy(r.manager.entry.options)
        for value in (None, True, "invalid", float("nan"), float("inf"), -1., 481., 15., 20.):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    await number.async_set_native_value(value)
                self.assertEqual(r.manager.entry.options, original)
        await number.async_set_native_value(480.)
        self.assertEqual(r.cfg["max_on_seconds"], 28800.)
        self.assertEqual(model.timing(r.manager, SPEC, r.cap), (1200., 600., 28800.))
        self.assertEqual(number.native_value, 480.)
        self.assertEqual(r.calls, [])

    async def test_other_duration_and_percentage_entities_keep_their_native_units(self):
        r = runtime()
        for key, unit in (("sample_seconds", "s"), ("cycle_seconds", "s"),
                          ("power_switch_cooldown_seconds", "s"), ("quiet_percentage", "%")):
            number = Number(r.manager, SPEC, key)
            self.assertEqual(number._attr_native_unit_of_measurement, unit)
            self.assertEqual(number.native_value, r.cfg[key])
            self.assertEqual(number._attr_native_step, model.NUMBER_FIELDS[key][2])
        await Number(r.manager, SPEC, "power_switch_cooldown_seconds").async_set_native_value(120.)
        self.assertEqual(r.cfg["power_switch_cooldown_seconds"], 120.)
        self.assertEqual(r.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

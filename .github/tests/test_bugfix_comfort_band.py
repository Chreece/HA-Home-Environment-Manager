"""Production comfort targets preserve controller gaps, limits and opt-ins.

Only the HA state/manager transport is simulated. Target resolution and native
capability/limit handling use the actual modules, with no service interface.
"""
from __future__ import annotations

from copy import deepcopy
import importlib
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_bugfix_comfort_band"
package = ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package
comfort = importlib.import_module(PKG + ".comfort_targets")
strategy = importlib.import_module(PKG + ".climate_strategy")
model = importlib.import_module(PKG + ".equipment_model")

AREA = "room"
ENTITY = "climate.room"
CAPABILITY = {"kind": "climate", "heat": True, "cool": True,
              "range": True, "setpoint": True,
              "modes": ["off", "heat", "cool", "heat_cool"]}


def room_settings(heat=21., cool=22.5, *, hysteresis=.7, source="auto_comfort"):
    return {"enabled": True, "controller": "device", "mode": "auto",
            "hysteresis_c": hysteresis, "target_source": source,
            "profiles": {name: {"heat_c": heat, "cool_c": cool}
                         for name in ("comfort", "sleep")}}


def legacy(settings, rh=80., *, target=None, sleeping=False):
    return strategy.policy(settings, temp_c=30., capability=CAPABILITY,
                           at_home="home", occupied="occupied", sleeping=sleeping,
                           comfort_humidity_rh=rh, comfort_target_c=target)


class Fixture:
    def __init__(self, room=None, *, rh=80., native=(5., 35.), room_limits=None,
                 pmv_enabled=True, estimate=None):
        self.spec = model.ManagedDevice("controller", AREA, "Room", "physical", (ENTITY,))
        self.settings = {"areas": [AREA], "climate_rooms": {AREA: {
            "selected_devices": [ENTITY], **deepcopy(room or room_settings())}},
            "environment_rooms": {AREA: {"enable_pmv": pmv_enabled,
                "equipment_limits": deepcopy(room_limits or {})}}}
        self._device_hierarchy = {"controllers": {self.spec.identifier: {"spec": self.spec}}}
        self.hass = N(states={ENTITY: N(state="off", attributes={
            "hvac_modes": ["off", "heat", "cool", "heat_cool"],
            "supported_features": 3, "temperature_unit": "°C",
            "min_temp": native[0], "max_temp": native[1], "target_temp_step": .1,
        })})
        self.equipment = N(measurements=lambda spec, cap: {"humidity": rh})
        self.plan = N(environment={AREA: {"international": {"pmv_air_target": estimate}}})
        self.cap = model.capabilities(self, self.spec)

    def target(self, mode="automatic", *, preset="none", plan=None, manual=None):
        config = {"control_mode": mode, "preset": preset}
        if manual is not None:
            config["profile_targets"] = {"manual": manual}
        return model.targets(self, self.spec, self.cap, config,
                             plan or {"away": "home", "occupancy": "occupied"})


class ComfortBandTests(unittest.TestCase):
    def assert_band(self, result, heat, cool, gap):
        low, high = result["heat_c"], result["cool_c"]
        self.assertTrue(math.isfinite(low) and math.isfinite(high))
        self.assertGreaterEqual(low, heat)
        self.assertLessEqual(high, cool)
        self.assertGreaterEqual(high - low + 1e-9, gap)

    def test_narrow_saved_band_remains_actionable_in_legacy_policy(self):
        for rh, expected in ((80., (21., 22.4)), (0., (21.1, 22.5))):
            with self.subTest(rh=rh):
                output = legacy(room_settings(), rh)
                self.assertEqual(output.state, "ready")
                self.assertAlmostEqual(output.range_low_c, expected[0])
                self.assertAlmostEqual(output.range_high_c, expected[1])

    def test_decimal_minimum_gap_is_valid_without_weakening_guard(self):
        settings = room_settings(cool=22.4)
        self.assertIsNone(strategy.profiles(settings)[1])
        self.assertEqual(strategy.auto_mode(24., 21., 22.4, None)[0], "cool")
        self.assertEqual(legacy(settings).state, "ready")
        self.assertIsNotNone(strategy.profiles(room_settings(cool=22.399))[1])
        self.assertIsNone(strategy.auto_mode(24., 21., 22.399, None)[0])

    def test_rh_extremes_and_effective_hysteresis_preserve_gap(self):
        for hysteresis in (.2, .5, .7, .701, 1.25, 3.):
            gap = max(1., 2 * hysteresis)
            heat, cool = 21., 21. + gap + .1
            for rh in (0., 20., 30., 40., 50., 60., 80., 100.):
                with self.subTest(hysteresis=hysteresis, rh=rh):
                    result = comfort.automatic_comfort_band(
                        heat, cool, rh, minimum_deadband_c=gap)
                    self.assertEqual(result["status"], "humidity_aware_estimate")
                    self.assert_band(result, heat, cool, gap)
                    self.assertLessEqual(result["heat_c"] - heat, .6 + 1e-9)
                    self.assertLessEqual(cool - result["cool_c"], .9 + 1e-9)
                    self.assertEqual(legacy(room_settings(heat, cool, hysteresis=hysteresis), rh).state,
                                     "ready")

    def test_existing_humidity_formula_and_adjustment_limit_are_unchanged(self):
        for rh, expected in ((30., (20.3, 26.)), (50., (20., 26.)), (80., (20., 25.1))):
            result = comfort.automatic_comfort_band(20., 26., rh)
            self.assertEqual((result["heat_c"], result["cool_c"]), expected)
        for rh in (0., 100.):
            result = comfort.automatic_comfort_band(20., 26., rh, maximum_adjustment_c=.004)
            self.assertLessEqual(result["heat_c"] - 20., .004 + 1e-9)
            self.assertLessEqual(26. - result["cool_c"], .004 + 1e-9)

    def test_missing_or_nonfinite_rh_retains_fixed_targets(self):
        for rh in (None, "unknown", True, float("nan"), float("inf"), -float("inf"), -1., 101.):
            with self.subTest(rh=rh):
                result = comfort.automatic_comfort_band(21., 22.5, rh, minimum_deadband_c=1.4)
                self.assertEqual(result["status"], "fixed_targets_missing_humidity")
                self.assertEqual((result["heat_c"], result["cool_c"]), (21., 22.5))
                self.assertEqual(Fixture(rh=rh).target(), {"heat": 21., "cool": 22.5, "humidity": 65.})

    def test_invalid_numbers_fail_closed(self):
        for value in (None, "invalid", True, float("nan"), float("inf"), -float("inf")):
            for key in ("heat_c", "cool_c", "maximum_adjustment_c", "minimum_deadband_c"):
                args = {"heat_c": 20., "cool_c": 26., "relative_humidity": 80., key: value}
                with self.subTest(key=key, value=value):
                    self.assertEqual(comfort.automatic_comfort_band(**args)["status"], "invalid_config")
            for index in range(3):
                args = [24., 21., 23.]
                args[index] = value
                self.assertEqual(strategy.auto_mode(*args, None)[0], None)
            self.assertIsNone(strategy.auto_mode(24., 21., 23., None, hysteresis_c=value)[0])

    def test_rounding_stays_inside_fractional_saved_bounds_and_gap(self):
        for rh in (0., 100.):
            result = comfort.automatic_comfort_band(21.003, 22.409, rh, minimum_deadband_c=1.402)
            self.assert_band(result, 21.003, 22.409, 1.402)

    def test_unified_targets_adjust_inside_native_and_room_limits(self):
        room = room_settings(20., 26.)
        for limits in ((21., 22.5), (21.003, 22.409)):
            room["hysteresis_c"] = .7 if limits[0] == 21. else .701
            for where in ("native", "room"):
                kwargs = ({"native": limits} if where == "native" else {"room_limits": {
                    "temperature_min_limit": limits[0], "temperature_max_limit": limits[1]}})
                for rh in (0., 100.):
                    with self.subTest(limits=limits, where=where, rh=rh):
                        fixture = Fixture(room, rh=rh, **kwargs)
                        before = deepcopy(fixture.settings)
                        target = fixture.target()
                        self.assert_band({"heat_c": target["heat"], "cool_c": target["cool"]},
                                         *limits, max(1., 2 * room["hysteresis_c"]))
                        self.assertEqual(fixture.settings, before)

    def test_limits_too_narrow_do_not_invent_a_new_band(self):
        for source in ("auto_comfort", "pmv"):
            fixture = Fixture(room_settings(20., 26., source=source), native=(21., 22.),
                              estimate={"status": "estimate", "air_temperature_target_c": 21.5})
            self.assertEqual(fixture.target(), {"heat": 21., "cool": 22., "humidity": 65.})

    def test_unaffected_profiles_fixed_selection_and_manual_targets(self):
        fixture = Fixture(room_settings(20., 26.))
        for profile in ("home", "away", "eco"):
            expected = strategy.DEFAULT_PROFILE_TARGETS[profile]
            self.assertEqual(fixture.target(preset=profile), {"heat": expected["heat_c"],
                "cool": expected["cool_c"], "humidity": expected["humidity"]})
        fixture.settings["climate_rooms"][AREA]["target_source"] = "fixed"
        self.assertEqual(fixture.target(), {"heat": 20., "cool": 26., "humidity": 65.})
        self.assertEqual(fixture.target("manual", manual={"heat": 19., "cool": 27.}),
                         {"heat": 19., "cool": 27., "humidity": 65.})


class PMVWiringTests(unittest.TestCase):
    def fixture(self, **kwargs):
        return Fixture(room_settings(20., 26., source="pmv"),
                       estimate={"status": "estimate", "air_temperature_target_c": 23.}, **kwargs)

    def test_selected_qualified_pmv_changes_automatic_and_pid_targets(self):
        fixture = self.fixture()
        before = deepcopy(fixture.settings)
        for mode in ("automatic", "pid"):
            for sleeping in (False, True):
                plan = {"away": "home", "occupancy": "occupied", "sleeping": sleeping}
                target = fixture.target(mode, plan=plan)
                self.assertEqual(target, {"heat": 21.5, "cool": 24.5, "humidity": 65.})
                output = legacy(fixture.settings["climate_rooms"][AREA], target=23., sleeping=sleeping)
                self.assertEqual((output.range_low_c, output.range_high_c), (target["heat"], target["cool"]))
        self.assertEqual(fixture.settings, before)

    def test_pmv_adjustment_preserves_effective_gap_in_both_resolvers(self):
        fixture = Fixture(room_settings(source="pmv"),
                          estimate={"status": "estimate", "air_temperature_target_c": 21.75})
        target = fixture.target()
        self.assertEqual((target["heat"], target["cool"]), (21., 22.5))
        output = legacy(fixture.settings["climate_rooms"][AREA], target=21.75)
        self.assertEqual(output.state, "ready")
        self.assertEqual((output.range_low_c, output.range_high_c), (21., 22.5))

    def test_missing_invalid_unqualified_and_disabled_pmv_are_fixed(self):
        for estimate in (None, {}, {"status": "target_not_bracketed", "air_temperature_target_c": 23.},
                         {"status": "estimate"},
                         *({"status": "estimate", "air_temperature_target_c": value}
                           for value in (None, True, "bad", float("nan"), float("inf"), 15., 31.))):
            with self.subTest(estimate=estimate):
                fixture = self.fixture()
                fixture.plan.environment[AREA]["international"]["pmv_air_target"] = estimate
                self.assertEqual(fixture.target(), {"heat": 20., "cool": 26., "humidity": 65.})
        for enabled in (False, None, "true", 1):
            self.assertEqual(self.fixture(pmv_enabled=enabled).target(),
                             {"heat": 20., "cool": 26., "humidity": 65.})
        for environment in ({}, None, {AREA: None}, {AREA: {"international": None}}):
            fixture = self.fixture()
            fixture.plan.environment = environment
            self.assertEqual(fixture.target(), {"heat": 20., "cool": 26., "humidity": 65.})

    def test_a_previous_qualified_estimate_is_not_reused_after_evidence_expires(self):
        fixture = self.fixture()
        self.assertEqual(fixture.target()["heat"], 21.5)
        fixture.plan.environment[AREA]["international"]["pmv_air_target"] = {
            "status": "insufficient_fresh_pmv_inputs"}
        self.assertEqual(fixture.target(), {"heat": 20., "cool": 26., "humidity": 65.})

    def test_pmv_preserves_manual_existing_off_and_explicit_profile_selection(self):
        fixture = self.fixture()
        for mode in ("manual", "existing", "off"):
            for preset in ("none", "comfort", "sleep"):
                self.assertEqual(fixture.target(mode, preset=preset),
                                 {"heat": 20., "cool": 26., "humidity": 65.})
        self.assertEqual(fixture.target("manual", manual={"heat": 19., "cool": 27.}),
                         {"heat": 19., "cool": 27., "humidity": 65.})
        for profile in ("home", "away", "eco"):
            expected = strategy.DEFAULT_PROFILE_TARGETS[profile]
            result = fixture.target(preset=profile)
            self.assertEqual((result["heat"], result["cool"]), (expected["heat_c"], expected["cool_c"]))
        fixture.settings["climate_rooms"][AREA]["target_source"] = "fixed"
        self.assertEqual(fixture.target(), {"heat": 20., "cool": 26., "humidity": 65.})

    def test_pmv_respects_native_limits_and_the_saved_adjustment_cap(self):
        fixture = self.fixture(native=(21., 25.))
        fixture.settings["climate_rooms"][AREA]["comfort_adjustment_max_c"] = .25
        target = fixture.target()
        self.assertEqual((target["heat"], target["cool"]), (21.25, 24.75))


if __name__ == "__main__":
    unittest.main()

"""Beta56 production-function tests: offline PID, simple comfort and purifier CADR.

No Home Assistant, physical switch, HVAC output or network calls are used.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def finite(value, low, high):
    try:
        if isinstance(value, bool):
            return None
        n = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return n if math.isfinite(n) and low <= n <= high else None


def extract(path, functions, namespace):
    src = ROOT / path
    tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
    chosen = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in functions]
    assert {n.name for n in chosen} == set(functions)
    mod = ast.Module(body=[ast.parse("from __future__ import annotations").body[0],
                           *chosen], type_ignores=[])
    exec(compile(ast.fix_missing_locations(mod), str(src), "exec"), namespace)
    return namespace


class AutomaticComfortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ns = extract("comfort_targets.py", {"automatic_comfort_band"},
                     {"finite": finite})
        cls.calculate = staticmethod(ns["automatic_comfort_band"])

    def test_no_humidity_does_not_fake_comfort_measurement(self):
        result = self.calculate(20, 26, None)
        self.assertEqual(result["status"], "fixed_targets_missing_humidity")
        self.assertEqual((result["heat_c"], result["cool_c"]), (20, 26))
        self.assertIsNone(result["rh_used"])

    def test_normal_humidity_preserves_user_temperature_band(self):
        result = self.calculate(20, 26, 50)
        self.assertEqual((result["heat_c"], result["cool_c"]), (20, 26))
        self.assertIn("not_iso7730", result["model"])

    def test_high_humidity_advances_cooling_without_exceeding_limit(self):
        result = self.calculate(20, 26, 85)
        self.assertEqual(result["heat_c"], 20)
        self.assertAlmostEqual(result["cool_c"], 25.1)
        self.assertLessEqual(26-result["cool_c"], .9)

    def test_low_humidity_small_heating_change_only(self):
        result = self.calculate(20, 26, 25)
        self.assertLessEqual(result["heat_c"]-20, .6)
        self.assertGreater(result["heat_c"], 20)
        self.assertEqual(result["cool_c"], 26)

    def test_zero_adjustment_never_moves_targets(self):
        result = self.calculate(20, 26, 90, maximum_adjustment_c=0)
        self.assertEqual((result["heat_c"], result["cool_c"]), (20, 26))

    def test_keep_minimum_one_degree_gap(self):
        result = self.calculate(24, 25, 85)
        self.assertGreaterEqual(result["cool_c"]-result["heat_c"], 1)

    def test_invalid_nonfinite_inputs_never_authorize_adjustment(self):
        self.assertEqual(self.calculate(20, 26, math.inf)["status"],
                         "fixed_targets_missing_humidity")
        self.assertEqual(self.calculate(28, 26, 55)["status"], "invalid_config")


@dataclass
class Memory:
    integral: float = 0.
    measured: float | None = None
    stamp: float | None = None
    derivative: float = 0.
    demand: float = 0.


class OfflinePIDTests(unittest.TestCase):
    def setUp(self):
        self.current = 18.
        self.now = 1000.
        self.memory = {}
        self.spec = SimpleNamespace(identifier="heater1", area_id="room1")
        self.cap = SimpleNamespace(
            domain="climate", modes=("off", "heat"),
            primary="climate.heater1", humidifying=False)
        self.cfg = dict(control_mode="pid", requested_mode="heat",
                        kp=10., ki=.4, kd=2., preset="none")
        self.runtime = SimpleNamespace(
            manager=SimpleNamespace(),
            _memory=self.memory, clock=lambda: self.now,
            measurements=lambda spec, cap: {"temperature": self.current})
        model = SimpleNamespace(
            PIDMemory=Memory, plan_for=lambda manager, spec: {},
            targets=lambda manager, spec, cap, cfg, plan: {
                "heat":20., "cool":26., "humidity":55.},
        )
        self.prepare = extract(
            "equipment_power_switch.py", {"prepare_offline_pid"},
            {"finite": finite, "model": model}
        )["prepare_offline_pid"]

    def test_prepares_live_proportional_demand_without_physical_device(self):
        v = self.prepare(self.runtime, self.spec, self.cap, self.cfg, True)
        self.assertEqual(v["status"], "prepared_proportional_only")
        self.assertEqual(v["proportional_demand_percent"], 20.)
        signature, memory, anchor = self.memory["heater1"]
        self.assertEqual(memory.integral, 0.)
        self.assertEqual(memory.derivative, 0.)
        self.assertEqual(memory.measured, 18.)
        self.assertEqual((memory.stamp, anchor), (1000., 1000.))

    def test_no_integral_windup_during_prolonged_off_period(self):
        self.prepare(self.runtime, self.spec, self.cap, self.cfg, True)
        self.now = 5000.
        self.current = 19.
        v = self.prepare(self.runtime, self.spec, self.cap, self.cfg, True)
        self.assertEqual(v["proportional_demand_percent"], 10.)
        _, memory, anchor = self.memory["heater1"]
        self.assertEqual(memory.integral, 0.)
        self.assertEqual(memory.derivative, 0.)
        self.assertEqual((memory.stamp, anchor), (5000., 5000.))

    def test_unknown_feedback_discards_preview(self):
        self.prepare(self.runtime, self.spec, self.cap, self.cfg, True)
        self.current = None
        v = self.prepare(self.runtime, self.spec, self.cap, self.cfg, None)
        self.assertEqual(v["status"], "not_prepared")
        self.assertNotIn("heater1", self.memory)

    def test_automatic_non_pid_does_not_fabricate_pid_state(self):
        self.cfg["control_mode"] = "automatic"
        v = self.prepare(self.runtime, self.spec, self.cap, self.cfg, False)
        self.assertEqual(v["status"], "not_prepared")
        self.assertEqual(self.memory, {})


class IntegrationContractTests(unittest.TestCase):
    def test_room_and_equipment_both_consume_auto_comfort(self):
        for path in ("climate_strategy.py", "equipment_model.py"):
            text = (ROOT/path).read_text()
            self.assertIn("auto_comfort", text, path)
            self.assertIn("automatic_comfort_band", text, path)

    def test_manager_watches_reconnecting_native_source_and_power_switch(self):
        text = (ROOT/"manager.py").read_text()
        self.assertIn("self._tracked.update(native_spec.source_entities)", text)
        self.assertIn("self._tracked.add(upstream)", text)
        self.assertIn("purifier_ratings_by_room=purifier_ratings", text)

    def test_offline_pid_does_not_bypass_native_availability_gate(self):
        runtime = (ROOT/"equipment_runtime.py").read_text()
        self.assertLess(runtime.index("power_switch_before_tick(self, spec)"),
                        runtime.index("model.sources_available(self.manager, spec)"))
        self.assertGreater(runtime.index("memory = model.pid_step(value, goal, self.clock(),"),
                           runtime.index("model.sources_available(self.manager, spec)"))
        self.assertIn("self._pid_offline_previews", runtime)

    def test_cadr_is_device_owned_not_room_number(self):
        model = (ROOT/"equipment_model.py").read_text()
        numbers = (ROOT/"number.py").read_text()
        controls = (ROOT/"device_controls.py").read_text()
        self.assertIn('"particle_cadr_m3h": (0.0, 100000.0', model)
        self.assertIn('key == "particle_cadr_m3h"', numbers)
        area_section = controls.split("AREA_ENV_NUMBERS = {", 1)[1].split("}",1)[0]
        self.assertNotIn('"particle_cadr_m3h"', area_section)
        self.assertIn("legacy_room_pending_device_assignment",
                      (ROOT/"environment_extended.py").read_text())

    def test_every_locale_displays_three_valid_comfort_choices(self):
        files = tuple((ROOT/"translations").glob("*.json"))
        self.assertEqual(len(files), 38)
        for p in files:
            with self.subTest(locale=p.stem):
                j = json.loads(p.read_text(encoding="utf-8"))
                choices = j["entity"]["select"]["area_climate_policy_target_source"]["state"]
                self.assertEqual(set(choices),
                                 {"temperature", "auto_comfort", "pmv"})
                self.assertTrue(j["entity"]["number"]["equipment_particle_cadr_m3h"]["name"])

    def test_sources_compile(self):
        for path in ROOT.glob("*.py"):
            with self.subTest(source=path.name):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


if __name__ == "__main__":
    unittest.main()

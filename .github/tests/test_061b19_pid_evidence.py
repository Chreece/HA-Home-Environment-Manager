"""B19: actual read-only PID evidence, learning progress, and control isolation.

All observations are synthetic; the production pure functions and exact
controller PID step are executed, never an actual HA device or service.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"


def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


diagnostics = load("pid_diagnostics.py", "test_hem_b19_diagnostics")
pkg = types.ModuleType("test_hem_b19_pkg")
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
load("pid_calibration.py", pkg.__name__ + ".pid_calibration")
passive = load("pid_passive.py", pkg.__name__ + ".pid_passive")


class Native:
    def __init__(self, state, action=None):
        self.state = state
        self.attributes = {"hvac_action": action}


class EvidenceTests(unittest.TestCase):
    def test_hvac_mode_is_not_physical_on_evidence(self):
        output = diagnostics.observed_output
        self.assertIsNone(output("climate", Native("heat"), "heat"))
        self.assertIsNone(output("climate", Native("dry", "heating"), "dry"))
        self.assertEqual(output("climate", Native("heat", "heating"), "heat"), "on")
        self.assertEqual(output("climate", Native("heat", "idle"), "heat"), "off")
        self.assertEqual(output("climate", Native("off"), "heat"), "off")
        self.assertIsNone(output("climate", Native("unavailable"), "heat"))
        self.assertEqual(output("switch", Native("on"), "dry"), "on")
        self.assertIsNone(output("fan", Native("70"), "heat"))

    def test_24h_error_coverage_and_verified_starts(self):
        window = diagnostics.PerformanceWindow()
        values = [
            (0, 20.0, "off"),
            (300, 20.5, "on"),
            (600, 20.8, "on"),
            (900, 21.0, "on"),
        ]
        for at, value, output in values:
            accepted = window.observe(
                context=("room", "source", "heat", "pid", 21.0),
                metric="temperature", method="pid", mode="heat",
                target=21.0, measured=value, increasing=True,
                at=at, sample_seconds=300, output=output,
            )
            self.assertTrue(accepted)
        result = window.snapshot()
        self.assertEqual(result["verified_off_to_on_transitions"], 1)
        self.assertEqual(result["observed_on_hours_lower_bound"], round(600 / 3600, 3))
        self.assertEqual(result["coverage_hours"], 0.25)
        self.assertEqual(result["sample_count"], 4)
        self.assertGreater(result["mae"], 0)
        self.assertLess(result["mae"], 1)
        self.assertEqual(result["sampled_in_band_percent"], 50.0)
        self.assertEqual(result["energy_kwh"], None)
        self.assertIn("not energy", result["energy_note"].lower())
        self.assertEqual(result["scope"], "current context and running Home Assistant session only")
        self.assertFalse(window.observe(
            context=("room", "source", "heat", "pid", 21.0),
            metric="temperature", method="pid", mode="heat",
            target=21.0, measured=21.0, increasing=True,
            at=900, sample_seconds=300, output="on",
        ))
        self.assertEqual(window.snapshot()["sample_count"], 4)

    def test_context_change_separates_fixed_from_pid_and_sensor_changes(self):
        window = diagnostics.PerformanceWindow()
        params = dict(metric="humidity", mode="dry", target=65.0,
                      increasing=False, sample_seconds=300)
        self.assertTrue(window.observe(context=("a", "pid"), method="pid",
                                       at=0, measured=70.0, output="off", **params))
        self.assertTrue(window.observe(context=("a", "automatic"), method="automatic",
                                       at=300, measured=68.0, output="on", **params))
        result = window.snapshot()
        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(result["verified_off_to_on_transitions"], 0)
        self.assertEqual(result["method"], "automatic")
        self.assertEqual(result["metric"], "humidity")
        self.assertEqual(result["unit"], "RH points")
        self.assertTrue(window.observe(context=("another_sensor", "automatic"),
                                       method="automatic",
                                       at=600, measured=64.0, output="off", **params))
        self.assertEqual(window.snapshot()["maximum_observed_overshoot"], 1.0)
        self.assertEqual(window.snapshot()["sample_count"], 1)

    def test_sampling_gaps_are_not_interpolated(self):
        window = diagnostics.PerformanceWindow()
        args = dict(context=("room", "heat"), metric="temperature",
                    method="pid", mode="heat", target=21.0,
                    measured=20.0, increasing=True,
                    sample_seconds=300, output="on")
        self.assertTrue(window.observe(at=0, **args))
        self.assertTrue(window.observe(at=3600, **args))
        snap = window.snapshot()
        self.assertEqual(snap["coverage_hours"], 0.0)
        self.assertEqual(snap["observed_on_hours_lower_bound"], 0)
        self.assertEqual(snap["unobserved_or_long_intervals"], 1)
        self.assertEqual(snap["status"], "insufficient_coverage")
        # Never create a false ON transition after a missing interval.
        self.assertTrue(window.observe(at=3900, **{**args, "output": "off"}))
        self.assertTrue(window.observe(at=4200, **args))
        self.assertEqual(window.snapshot()["verified_off_to_on_transitions"], 1)

    def test_bounded_memory_no_future_data_or_fake_energy(self):
        window = diagnostics.PerformanceWindow()
        args = dict(context=("living", "heat"), metric="temperature",
                    method="pid", mode="heat", target=21.0, measured=20.0,
                    increasing=True, sample_seconds=120, output=None)
        for index in range(750):
            window.observe(at=index*120, **args)
        result = window.snapshot()
        self.assertLessEqual(result["sample_count"], 721)
        self.assertLessEqual(result["coverage_hours"], 24)
        self.assertEqual(result["verified_off_to_on_transitions"], 0)
        self.assertEqual(result["observed_on_hours_lower_bound"], 0)
        self.assertEqual(result["energy_kwh"], None)
        self.assertFalse(window.observe(at=True, **args))
        self.assertFalse(window.observe(at=float("nan"), **args))

    def test_live_learning_progress_rejection_explained_only(self):
        observer = passive.PassiveObserver()
        options = dict(context="single-physical-room", metric="temperature",
                       direction=1, sample_seconds=300, safe=True)
        for at in (0, 300, 600, 900):
            observer.observe(at=at, value=20.0, on=False, owned=False, **options)
        self.assertEqual(observer.progress()["phase"], "collecting_stable_off_baseline")
        observer.observe(at=1200, value=20.0, on=True, owned=True, **options)
        observer.observe(at=1500, value=20.3, on=True, owned=True, **options)
        self.assertEqual(observer.progress()["phase"], "observing_on_response")
        observer.observe(at=1800, value=20.3, on=False, owned=False, **options)
        progress = observer.progress()
        self.assertEqual(progress["valid_cycles"], 0)
        self.assertEqual(progress["required_for_auto"], 5)
        self.assertEqual(progress["last_rejection_reason"], "insufficient_on_samples")
        self.assertFalse(progress["raw_history_saved"])
        self.assertGreater(progress["rejection_counts"]["insufficient_on_samples"], 0)
        observer.observe(at=2100, value=20.0, on=False, owned=False,
                         **{**options, "context": "different_temperature_sensor"})
        self.assertIsNone(observer.progress()["last_rejection_reason"])
        self.assertEqual(observer.progress()["rejection_counts"], {})

    def test_real_pid_math_unchanged_by_diagnostics(self):
        tree = ast.parse((ROOT / "equipment_model.py").read_text(encoding="utf-8"))
        block = [node for node in tree.body
                 if isinstance(node, ast.ClassDef) and node.name == "PIDMemory"
                 or isinstance(node, ast.FunctionDef) and node.name == "pid_step"]
        self.assertEqual(len(block), 2)
        module = types.ModuleType("test_hem_b19_real_pid_math")
        sys.modules[module.__name__] = module
        module.__dict__.update({"math": math, "dataclass": dataclass})
        exec(compile(ast.Module(body=block, type_ignores=[]),
                     "equipment_model.py", "exec"), module.__dict__)
        PIDMemory = module.PIDMemory
        step = module.pid_step
        previous = PIDMemory(integral=80, measured=19, stamp=0, derivative=0,
                             demand=100)
        result = step(19, 21, 300, increasing=True, kp=100, ki=.5,
                      kd=0, sample=300, memory=previous)
        self.assertEqual(result.integral, 80)  # no saturation windup
        self.assertEqual(result.demand, 100)
        satisfied = step(21, 21, 360, increasing=True, kp=100, ki=.5,
                         kd=0, sample=300, memory=result)
        self.assertEqual(satisfied.demand, 0)
        self.assertEqual(satisfied.integral, 0)

    def test_diagnostic_runtime_never_writes_device_or_storage(self):
        tree = ast.parse((ROOT/"equipment_runtime.py").read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "EquipmentRuntime")
        fn = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                  and node.name == "_observe_pid_performance")
        source = ast.get_source_segment(
            (ROOT/"equipment_runtime.py").read_text(encoding="utf-8"), fn
        )
        for forbidden in ("await ", "async_call(", "callService", "_save(",
                          "_power(", "_send(", "async_update("):
            self.assertNotIn(forbidden, source)
        self.assertIn("PerformanceWindow", source)
        status = (ROOT/"equipment_status.py").read_text(encoding="utf-8")
        self.assertIn('"pid_performance_24h"', status)
        self.assertIn('"pid_learning_progress"', status)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Fresh measured target satisfaction must stop retained PID effort.

Run the production managed-device PID, the legacy setpoint/direct-output PID,
and the real restart checkpoint restoration. No actuator or HA service is used.
Set HEM_TEST_PID_MODEL_SOURCE / HEM_TEST_PID_MATH_SOURCE to immutable earlier
sources to reproduce the stale integral, derivative and sample-hold defects.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import importlib.util
import math
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODEL_SOURCE = Path(os.environ.get(
    "HEM_TEST_PID_MODEL_SOURCE", ROOT / "equipment_model.py"))
MATH_SOURCE = Path(os.environ.get(
    "HEM_TEST_PID_MATH_SOURCE", ROOT / "pid_math.py"))


def load_pure(name, path):
    definition = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(definition)
    sys.modules[name] = module
    definition.loader.exec_module(module)
    return module


maths = load_pure("beta111_pid_math", MATH_SOURCE)
restart = load_pure("beta111_pid_restart", ROOT / "pid_restart.py")
definitions = [
    node for node in ast.parse(MODEL_SOURCE.read_text()).body
    if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    and node.name in ("PIDMemory", "pid_step")
]
assert {node.name for node in definitions} == {"PIDMemory", "pid_step"}
scope = {"math": math, "dataclass": dataclass}
exec(compile(ast.Module(body=definitions, type_ignores=[]),
             str(MODEL_SOURCE), "exec"), scope)
PIDMemory, pid_step = scope["PIDMemory"], scope["pid_step"]

# name, increases measured variable, target, already-satisfied measurement
CASES = (
    ("heat", True, 21.0, 22.1),
    ("cool", False, 24.0, 22.9),
    ("humidify", True, 50.0, 55.0),
    ("dry", False, 60.0, 55.0),
)
NOW = 100_000.0
SAMPLE = 300.0


class TestManagedPidCutoff(unittest.TestCase):
    def step(self, measured, target, increasing, memory=None, *, now=NOW,
             kp=10.0, ki=0.2, kd=0.0):
        return pid_step(
            measured, target, now, increasing=increasing,
            kp=kp, ki=ki, kd=kd, sample=SAMPLE, memory=memory,
        )

    def assert_stopped(self, result, measured, *, now=NOW):
        self.assertEqual(result.demand, 0.0)
        self.assertEqual(result.integral, 0.0)
        self.assertEqual(result.derivative, 0.0)
        self.assertEqual(result.measured, measured)
        self.assertEqual(result.stamp, now)

    def test_positive_integral_cannot_continue_past_target_in_any_direction(self):
        for name, increasing, target, measured in CASES:
            with self.subTest(name=name):
                previous = PIDMemory(
                    integral=80.0, measured=target, stamp=NOW-SAMPLE,
                    derivative=0.0, demand=80.0,
                )
                result = self.step(measured, target, increasing, previous)
                self.assert_stopped(result, measured)

    def test_target_equality_is_zero_even_with_retained_effort(self):
        for name, increasing, target, _ in CASES:
            with self.subTest(name=name):
                previous = PIDMemory(
                    integral=80.0, measured=target, stamp=NOW-SAMPLE,
                    derivative=-5.0 if increasing else 5.0, demand=90.0,
                )
                result = self.step(target, target, increasing, previous, kd=5.0)
                self.assert_stopped(result, target)

    def test_cutoff_overrides_cached_positive_demand_before_sample_due(self):
        for name, increasing, target, measured in CASES:
            with self.subTest(name=name):
                previous = PIDMemory(
                    integral=70.0, measured=target-1 if increasing else target+1,
                    stamp=NOW-1.0, derivative=5.0, demand=100.0,
                )
                result = self.step(measured, target, increasing, previous)
                self.assert_stopped(result, measured)

    def test_positive_derivative_effort_cannot_continue_past_target(self):
        for name, increasing, target, measured in CASES:
            with self.subTest(name=name):
                previous = PIDMemory(
                    integral=0.0,
                    measured=measured+5.0 if increasing else measured-5.0,
                    stamp=NOW-SAMPLE,
                    derivative=-10.0 if increasing else 10.0,
                    demand=60.0,
                )
                result = self.step(
                    measured, target, increasing, previous, kp=1.0, ki=0.0, kd=5.0,
                )
                self.assert_stopped(result, measured)

    def test_initial_satisfied_target_never_requests_output(self):
        for name, increasing, target, measured in CASES:
            for value in (target, measured):
                with self.subTest(name=name, value=value):
                    self.assert_stopped(self.step(value, target, increasing), value)

    def test_reentry_uses_normal_sampling_without_old_integral_or_derivative(self):
        for name, increasing, target, measured in CASES:
            with self.subTest(name=name):
                old = PIDMemory(85.0, target, NOW-1.0, 9.0, 95.0)
                stopped = self.step(measured, target, increasing, old)
                needed = target-1.0 if increasing else target+1.0
                held = self.step(needed, target, increasing, stopped, now=NOW+1.0)
                self.assertEqual(held.demand, 0.0)
                resumed = self.step(
                    needed, target, increasing, held, now=NOW+SAMPLE,
                    kp=10.0, ki=0.2, kd=0.0,
                )
                self.assertAlmostEqual(resumed.integral, 1.0)
                self.assertAlmostEqual(resumed.demand, 11.0)

    def test_restart_cannot_replay_positive_integral_at_satisfied_target(self):
        for name, increasing, target, measured in CASES:
            with self.subTest(name=name):
                signature = (
                    "humidity" if name in ("humidify", "dry") else "temperature",
                    target, increasing, "comfort", name, "none",
                    10.0, 0.2, 0.0, 3600.0, 600.0, 600.0,
                )
                saved = restart.checkpoint(
                    signature, PIDMemory(80.0, target, NOW-60.0, 3.0, 90.0),
                    NOW-1200.0, ("climate.test",), "device", SAMPLE, NOW-1.0,
                )
                self.assertIsNotNone(saved)
                restored = restart.restore(
                    saved, sources=("climate.test",), source_device_id="device",
                    now=NOW, sample=SAMPLE, measured=measured, goal=target,
                    increasing=increasing, kp=10.0,
                )
                self.assertIsNotNone(restored)
                _, restored_memory, anchor = restored
                self.assertEqual(anchor, NOW-1200.0)
                # tick() always applies current feedback before allocation,
                # even though restore reseeds its timestamp to exactly NOW.
                result = self.step(
                    measured, target, increasing, PIDMemory(**restored_memory),
                )
                self.assert_stopped(result, measured)

    def test_unsatisfied_pid_and_invalid_input_behavior_are_preserved(self):
        first = self.step(20.0, 21.0, True)
        self.assertEqual(first.demand, 10.0)
        held = self.step(20.0, 21.0, True, first, now=NOW+1.0)
        self.assertIs(held, first)
        advanced = self.step(20.0, 21.0, True, held, now=NOW+SAMPLE)
        self.assertEqual(advanced.demand, 11.0)
        for invalid in (None, True, float("nan"), float("inf")):
            with self.subTest(invalid=invalid):
                result = self.step(invalid, 21.0, True, first)
                self.assertEqual(result.demand, 0.0)
                self.assertIsNone(result.stamp)


class TestLegacyPidCutoff(unittest.TestCase):
    def step(self, measured, target, mode, memory=None, *, now=NOW,
             kp=10.0, ki=0.2, kd=0.0):
        return maths.step(measured, target, now, mode, kp, ki, kd, SAMPLE, memory)

    def assert_stopped(self, result, measured):
        # Both legacy consumers require ready to replace their retained
        # output. Waiting_sample would keep climate_direct's old PWM demand.
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.demand_percent, 0.0)
        self.assertEqual(result.integral, 0.0)
        self.assertEqual(result.derivative, 0.0)
        self.assertEqual(result.memory.integral, 0.0)
        self.assertEqual(result.memory.derivative_c_per_min, 0.0)
        self.assertEqual(result.memory.last_c, measured)
        self.assertEqual(result.memory.last_s, NOW)

    def test_integral_derivative_and_early_sample_cannot_keep_legacy_output_on(self):
        for mode, increasing, target, measured in CASES[:2]:
            for delay in (1.0, SAMPLE):
                for value in (target, measured):
                    with self.subTest(mode=mode, delay=delay, value=value):
                        old = maths.Memory(
                            80.0, target, NOW-delay, -5.0 if increasing else 5.0,
                        )
                        result = self.step(value, target, mode, old, kd=5.0)
                        self.assert_stopped(result, value)

    def test_satisfied_first_sample_is_zero_instead_of_waiting_for_history(self):
        for mode, _, target, measured in CASES[:2]:
            with self.subTest(mode=mode):
                self.assert_stopped(self.step(measured, target, mode), measured)

    def test_legacy_setpoint_only_output_removes_trim_without_inventing_power(self):
        for mode, _, target, measured in CASES[:2]:
            with self.subTest(mode=mode):
                result = self.step(
                    measured, target, mode, maths.Memory(80.0, target, NOW-1.0),
                )
                desired = maths.setpoint_c(
                    target, result.demand_percent, mode, 1.5, 16.0, 27.0,
                )
                self.assertEqual(desired, target)

    def test_legacy_reentry_uses_normal_sample_and_new_effort_only(self):
        for mode, increasing, target, measured in CASES[:2]:
            with self.subTest(mode=mode):
                stopped = self.step(
                    measured, target, mode, maths.Memory(80.0, target, NOW-1.0),
                )
                needed = target-1.0 if increasing else target+1.0
                held = self.step(needed, target, mode, stopped.memory, now=NOW+1.0)
                self.assertEqual(held.status, "waiting_sample")
                self.assertEqual(held.memory.integral, 0.0)
                resumed = self.step(
                    needed, target, mode, held.memory, now=NOW+SAMPLE,
                )
                self.assertEqual(resumed.status, "ready")
                self.assertEqual(resumed.integral, 1.0)
                self.assertEqual(resumed.demand_percent, 11.0)

    def test_legacy_unsatisfied_initialization_and_bad_inputs_are_preserved(self):
        initial = self.step(20.0, 21.0, "heat")
        self.assertEqual(initial.status, "initializing")
        self.assertIsNone(initial.demand_percent)
        held = self.step(20.0, 21.0, "heat", initial.memory, now=NOW+1.0)
        self.assertEqual(held.status, "waiting_sample")
        result = self.step(20.0, 21.0, "heat", held.memory, now=NOW+SAMPLE)
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.demand_percent, 11.0)
        self.assertEqual(self.step(float("nan"), 21.0, "heat").status, "invalid_input")
        self.assertEqual(self.step(22.0, 21.0, "invalid").status, "unsupported_mode")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Configured operating holds in Automatic and PID decisions.

Uses production settings, timing, PID phase/duty and runtime dispatch through
simulated HA state/service transport. No Home Assistant instance or physical
appliance is used. A successful service call is deliberately not an ACK.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_061b1_operating_timing.py"))
TimingRuntime, SPEC, PRIMARY, model, phase = (
    fixture[key] for key in ("TimingRuntime", "SPEC", "PRIMARY", "model", "phase")
)


class DryTimingRuntime(TimingRuntime):
    """Dry-only native controller, avoiding the separate thermal comfort wake."""

    def __init__(self, *, demand=75.0, method="pid", off_age=1200.0):
        super().__init__(profile={
            "control_mode": method, "requested_mode": "dry",
            "kp": demand, "ki": 0.0, "kd": 0.0,
        }, off_age=off_age)
        self.humidity = 51.0
        self.state.attributes.update(hvac_modes=["off", "dry"], humidity=50.0)

    def measurements(self, spec, cap):
        return {"temperature": 20.0, "humidity": self.humidity,
                "pm25": None, "co2": None}

    async def configure(self, *, min_on=0.0, min_off=300.0, maximum=7200.0):
        await self.async_update(SPEC, {
            "cycle_seconds": 600.0, "min_on_seconds": min_on,
            "min_off_seconds": min_off, "max_on_seconds": maximum,
        })


class FeasiblePwmTimingTests(unittest.TestCase):
    def test_both_duty_halves_determine_the_smallest_complete_period(self):
        # Expected periods follow ON/duty and OFF/(1-duty), rounded to a
        # complete base period. Asymmetric OFF must not clip or starve demand.
        cases = (
            (75.0, 0.0, 300.0, 1200.0),
            (90.0, 60.0, 300.0, 3000.0),
            (25.0, 300.0, 0.0, 1200.0),
            (25.0, 0.0, 600.0, 1200.0),
            (75.0, 0.0, 0.0, 600.0),
            (0.1, 1.0, 0.0, 1200.0),
            (99.9, 0.0, 1.0, 1200.0),
            (50.0, 300.0, 300.0, 600.0),
        )
        for demand, minimum_on, minimum_off, expected in cases:
            with self.subTest(demand=demand, minimum_on=minimum_on, minimum_off=minimum_off):
                cycle = phase.safe_binary_pwm_cycle(demand, 600.0, minimum_on, minimum_off)
                self.assertEqual(cycle, expected)
                duration = cycle * demand / 100.0
                self.assertGreaterEqual(duration, minimum_on)
                self.assertGreaterEqual(cycle - duration + 1e-9, minimum_off)
                self.assertTrue(model.duty_on(demand, 0.0, cycle, minimum_on, minimum_off, starting=True))
                self.assertTrue(model.duty_on(demand, duration - 1e-7, cycle, minimum_on, minimum_off))
                self.assertFalse(model.duty_on(demand, duration, cycle, minimum_on, minimum_off))
                info = phase.binary_pwm_off_phase(demand, duration, 600.0, minimum_on, minimum_off, starting=False)
                self.assertEqual(info["state"], "off_window")
                self.assertAlmostEqual(info["next_window_seconds"], cycle - duration)

    def test_late_start_still_requires_a_complete_minimum_on_pulse(self):
        for elapsed, allowed in ((840.0, True), (841.0, False)):
            with self.subTest(elapsed=elapsed):
                info = phase.binary_pwm_off_phase(75.0, elapsed, 600.0, 60.0, 300.0, starting=True)
                self.assertEqual(info["effective_cycle_seconds"], 1200.0)
                self.assertEqual(info["state"] == "on_window", allowed)
                self.assertEqual(model.duty_on(75.0, elapsed, 1200.0, 60.0, 300.0, starting=True), allowed)
        self.assertTrue(model.duty_on(75.0, 841.0, 1200.0, 60.0, 300.0),
                        "An already acknowledged pulse may finish its scheduled ON window")

    def test_bounded_high_demand_retains_off_rest_without_suppressing_all_output(self):
        for horizon, expected in ((1800.0, 1800.0), (1900.0, 1800.0), (86400.0, 86400.0)):
            with self.subTest(horizon=horizon):
                cycle = phase.safe_binary_pwm_cycle(99.9, 600.0, 60.0, 300.0, maximum_s=horizon)
                self.assertEqual(cycle, expected)
                self.assertLessEqual(cycle, horizon)
                # Exact 99.9% is infeasible in this horizon; duty_on retains
                # the full 300-second OFF rest and therefore limits delivery.
                self.assertLess(cycle - 300.0, cycle * 0.999)
                self.assertTrue(model.duty_on(99.9, cycle - 300.0 - 1e-7, cycle, 60.0, 300.0))
                self.assertFalse(model.duty_on(99.9, cycle - 300.0, cycle, 60.0, 300.0))
        self.assertIsNone(phase.safe_binary_pwm_cycle(0.1, 1200.0, 600.0, 600.0))
        self.assertIsNone(phase.safe_binary_pwm_cycle(0.0, 600.0, 0.0, 0.0))
        self.assertIsNone(phase.safe_binary_pwm_cycle(75.0, 600.0, 400.0, 300.0))

    def test_full_demand_is_continuous_in_both_diagnostics_and_duty(self):
        for elapsed in (0.0, 300.0, 599.0, 600.0, 1199.0, 86401.0):
            for starting in (False, True):
                with self.subTest(elapsed=elapsed, starting=starting):
                    info = phase.binary_pwm_off_phase(100.0, elapsed, 600.0, 1.0, 300.0, starting=starting)
                    self.assertEqual(info, {"state": "on_window", "effective_cycle_seconds": 600.0,
                                            "next_window_seconds": 0.0})
                    self.assertTrue(model.duty_on(100.0, elapsed, 600.0, 1.0, 300.0, starting=starting))


class AutomaticRuntimeTimingTests(unittest.IsolatedAsyncioTestCase):
    async def test_high_pid_pulse_and_actual_delayed_off_ack(self):
        runtime = DryTimingRuntime()
        await runtime.configure()
        start = runtime.now
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "dry"}, runtime.statuses)
        pending = deepcopy(runtime.record["pending"])
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.calls), 1, "PWM cannot bypass the pending ON ACK")
        self.assertEqual(runtime.record["pending"], pending)
        runtime.report(mode="dry")
        await runtime.tick(SPEC)
        self.assertEqual(runtime.record["power"][PRIMARY]["min_on"], 0.0)
        original_owned = deepcopy(runtime.record["power"])
        for elapsed in (300.0, 899.0):
            runtime.now = start + elapsed
            await runtime.tick(SPEC)
            self.assertEqual(len(runtime.calls), 1, "75% duty is 900s ON, not a clipped 300s")
            self.assertEqual(runtime.statuses[-1][1]["pid_pwm_effective_cycle_seconds"], 1200.0)
            self.assertEqual(runtime.record["power"], original_owned)
        runtime.now = start + 900.0
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(runtime.record["power"], original_owned, "Dispatch is not observed OFF")
        runtime.now += 5.0
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.calls), 2, "Pending OFF must be acknowledged")
        runtime.now = start + 910.0
        runtime.report(mode="off")
        await runtime.tick(SPEC)
        self.assertEqual(runtime.record["off_at"][PRIMARY], start + 910.0)
        runtime.now = start + 1200.0
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.calls), 2, "Logical cycle restart cannot shorten actual OFF dwell")
        self.assertEqual(runtime.statuses[-1][0], "minimum_off_hold")
        runtime.now = start + 1210.0
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "dry"})
        self.assertEqual(len(runtime.calls), 3)

    async def test_longer_period_does_not_extend_the_owned_maximum_runtime(self):
        for demand, expected_cycle in ((90.0, 3000.0), (100.0, 600.0)):
            with self.subTest(demand=demand):
                runtime = DryTimingRuntime(demand=demand)
                await runtime.configure(min_on=60.0, maximum=900.0)
                start = runtime.now
                await runtime.tick(SPEC)
                runtime.report(mode="dry")
                await runtime.tick(SPEC)
                self.assertEqual(runtime.statuses[-1][1]["pid_pwm_effective_cycle_seconds"], expected_cycle)
                self.assertEqual(runtime.record["power"][PRIMARY]["max_on"], 900.0)
                runtime.now = start + 899.0
                await runtime.tick(SPEC)
                self.assertEqual(len(runtime.calls), 1)
                runtime.now += 1.0
                await runtime.tick(SPEC)
                self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
                self.assertEqual(len(runtime.calls), 2, "Maximum runtime ends a still-positive planned pulse")
                self.assertEqual(runtime.record["power"][PRIMARY]["since"], start)
                self.assertEqual(runtime.record["power"][PRIMARY]["max_on"], 900.0)

    async def test_automatic_hysteresis_honors_one_and_seven_second_holds(self):
        runtime = DryTimingRuntime(method="automatic", off_age=0.0)
        runtime.humidity = 53.0
        await runtime.configure(min_on=1.0, min_off=7.0)
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls, [])
        self.assertEqual(runtime.statuses[-1][0], "minimum_off_hold")
        runtime.now += 7.0
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "dry"}, runtime.statuses)
        runtime.report(mode="dry")
        await runtime.tick(SPEC)
        self.assertEqual(runtime.record["power"][PRIMARY]["min_on"], 1.0)
        runtime.humidity = 48.0
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")
        runtime.now += 1.0
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(len(runtime.calls), 2)

    async def test_zero_holds_leave_startup_window_and_target_gates_intact(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                runtime = DryTimingRuntime(method=method, off_age=0.0)
                runtime.humidity = 53.0
                await runtime.configure(min_on=0.0, min_off=0.0)
                runtime.startup_ready = False
                await runtime.tick(SPEC)
                self.assertEqual(runtime.calls, [])
                runtime.startup_ready = True
                runtime.window.update(blocked=True, status="window_fixture_hold")
                await runtime.tick(SPEC)
                self.assertEqual(runtime.calls, [])
                runtime.window.update(blocked=False, status="ready")
                await runtime.tick(SPEC)
                self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "dry"})
                runtime.report(mode="dry")
                await runtime.tick(SPEC)
                runtime.humidity = 48.0 if method == "automatic" else 50.0
                await runtime.tick(SPEC)
                self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
                self.assertEqual(len(runtime.calls), 2, "Fresh target attainment overrides a planned ON window")


if __name__ == "__main__":
    unittest.main()

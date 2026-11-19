"""Passive PID evidence, gain limits and truthful operator status regressions.

Run the production pure modules from the canonical integration directory.
All measurements and clocks are synthetic; no Home Assistant import, output
command, storage write, or shortened process-identification requirement.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import random
import sys
import types
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"
PACKAGE = "hem_074_learning_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", SOURCE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("pid_calibration")
passive = load("pid_passive")
status = load("pid_learning_status")


class LearningMathTests(unittest.TestCase):
    def options(self, sample=300):
        return dict(context="same-room-and-sensor", metric="temperature",
                    direction=1, sample_seconds=sample, safe=True)

    def test_off_baseline_spans_required_time_at_fast_and_jittered_intervals(self):
        for interval, sample in ((120, 120), (84, 120), (300, 300)):
            with self.subTest(interval=interval, sample=sample):
                observer = passive.PassiveObserver()
                for index in range(100):
                    observer.observe(at=index * interval, value=20., on=False,
                                     owned=False, **self.options(sample))
                span = observer.off[-1][0] - observer.off[0][0]
                self.assertGreaterEqual(span, passive.MIN_OFF_S)
                self.assertLess(span, passive.MIN_OFF_S + interval)
                self.assertLessEqual(len(observer.off), passive.MAX_POINTS)
                observer.observe(at=100 * interval, value=20., on=True,
                                 owned=True, **self.options(sample))
                self.assertEqual(observer.baseline, 20.)
                self.assertEqual(len(observer.on), 1)
                self.assertEqual(observer.cycles, [])

    def test_short_or_unstable_baseline_still_cannot_start_a_learning_episode(self):
        for values in ([20.] * 8, [20.] * 10 + [20.5, 20., 20.5, 20.]):
            with self.subTest(values=values):
                observer = passive.PassiveObserver()
                for index, value in enumerate(values):
                    observer.observe(at=index * 120, value=value, on=False,
                                     owned=False, **self.options(120))
                observer.observe(at=len(values) * 120, value=20., on=True,
                                 owned=True, **self.options(120))
                self.assertIsNone(observer.baseline)
                self.assertEqual(observer.on, [])
                self.assertEqual(observer.last_rejection_reason,
                                 "off_baseline_not_stable_or_too_short")

    def test_fast_verified_off_on_edges_never_merge_two_powered_runs(self):
        observer = passive.PassiveObserver()
        for at in (0, 300, 600, 900):
            observer.observe(at=at, value=20., on=False, owned=False, **self.options())
        for at, value in ((1200, 20.), (1500, 20.1)):
            observer.observe(at=at, value=value, on=True, owned=True, **self.options())
        observer.observe(at=1501, value=20.1, on=True, owned=True, **self.options())
        self.assertEqual(len(observer.on), 2, "Same-state readings remain throttled")
        observer.observe(at=1510, value=20.1, on=False, owned=False, **self.options())
        self.assertIs(observer.last_on, False)
        self.assertEqual(observer.on, [])
        self.assertEqual(observer.cycles, [], "The short first run is not a valid model")
        observer.observe(at=1520, value=20.1, on=True, owned=True, **self.options())
        self.assertIs(observer.last_on, True)
        self.assertIsNone(observer.baseline)
        self.assertEqual(observer.on, [], "Ten seconds OFF cannot seed a second episode")

    def test_actual_ten_percent_bound_includes_small_and_zero_integral_gains(self):
        for kp, ki in ((.001, .00001), (.01, .001), (20., 0.), (20., .2)):
            with self.subTest(kp=kp, ki=ki):
                current = {"kp": kp, "ki": ki, "kd": 3.}
                candidate = passive.bounded_gains(current, {"kp": 80., "ki": 1., "kd": 0.})
                self.assertIsNotNone(candidate)
                for key in ("kp", "ki"):
                    self.assertLessEqual(abs(candidate[key] - current[key]),
                                         .1 * current[key] + 1e-14)
                self.assertEqual(candidate["kd"], 3.)
                if ki == 0:
                    self.assertEqual(candidate["ki"], 0., "Automatic tuning cannot enable I from zero")

    def test_rounding_does_not_reverse_tiny_gain_direction_or_move_equal_target(self):
        for old, wanted in ((1.3e-8, 1.43e-8), (1.3e-8, 1.17e-8),
                            (.123456789012, .123456789012)):
            with self.subTest(old=old, wanted=wanted):
                candidate = passive.bounded_gains(
                    {"kp": 20., "ki": old, "kd": 2.},
                    {"kp": 80., "ki": wanted, "kd": 0.},
                )
                self.assertIsNotNone(candidate)
                self.assertGreaterEqual(candidate["ki"], min(old, wanted))
                self.assertLessEqual(candidate["ki"], max(old, wanted))
                self.assertLessEqual(abs(candidate["ki"] - old), .1 * old + 1e-14)
                if old == wanted:
                    self.assertEqual(candidate["ki"], old)

    def test_bounded_gain_property_across_supported_magnitudes(self):
        rng = random.Random(7401)
        for _ in range(500):
            current = {"kp": 10 ** rng.uniform(-3, 2),
                       "ki": 0. if rng.random() < .1 else 10 ** rng.uniform(-10, 1),
                       "kd": 4.}
            proposed = {"kp": 10 ** rng.uniform(-3, 2),
                        "ki": 10 ** rng.uniform(-10, 1), "kd": 0.}
            candidate = passive.bounded_gains(current, proposed)
            if candidate is None:
                continue
            for key in ("kp", "ki"):
                self.assertLessEqual(abs(candidate[key] - current[key]), .1 * current[key] + 1e-12)
                self.assertGreaterEqual(candidate[key], min(current[key], proposed[key]))
                self.assertLessEqual(candidate[key], max(current[key], proposed[key]))
            self.assertEqual(candidate["kd"], current["kd"])


class LearningStatusTests(unittest.TestCase):
    NOW = 2_000_000.

    def context(self, mode="heat", sensor="sensor.room"):
        return passive.identity("room", ["climate.unit"], "climate.unit", mode,
                                "temperature", sensor, "home", 21., None, None)

    def arguments(self, automatic=False):
        return dict(
            cfg={"control_mode": "pid", "requested_mode": "heat", "operating_mode": "heat",
                 "pid_calibration_method": "adaptive_auto" if automatic else "adaptive_suggest",
                 "kp": 10., "ki": .1, "kd": 0.},
            domain="climate", record={}, progress=None, observer_context=None,
            hold=None, observed={}, native_state="off", active=True, ready=True, now=self.NOW,
        )

    def model(self, mode="heat"):
        return {"context": self.context(mode), "cycles": [], "summary": {
            "status": "validated", "valid_cycles": 5, "last_cycle_at": self.NOW - 300,
            "suggested_gains": {"kp": 20., "ki": .2, "kd": 0.},
        }}

    def test_eligibility_reports_unsupported_outputs_and_unselected_pid(self):
        cases = (
            ({"pid_calibration_method": "manual"}, "climate", "disabled", "manual_calibration"),
            ({"control_mode": "automatic"}, "climate", "inactive", "pid_not_active"),
            ({"requested_mode": "fan_only"}, "fan", "unsupported", "unsupported_operating_mode"),
            ({}, "number", "unsupported", "unsupported_output"),
            ({}, None, "waiting", "device_unavailable"),
        )
        for changes, domain, state, reason in cases:
            with self.subTest(changes=changes, domain=domain):
                args = self.arguments()
                args["cfg"].update(changes)
                args["domain"] = domain
                result = status.snapshot(**args)
                self.assertEqual((result["status"], result["reason"]), (state, reason))
                self.assertFalse(result["eligible"])

    def test_suggest_and_automatic_have_distinct_cycle_requirements(self):
        for automatic, required in ((False, 3), (True, 5)):
            args = self.arguments(automatic)
            args.update(progress={"valid_cycles": 2}, observer_context=self.context())
            result = status.snapshot(**args)
            self.assertEqual(result["valid_cycles"], 2)
            self.assertEqual(result["required_cycles"], required)
            self.assertEqual(result["status"], "collecting")

    def test_unavailable_pending_and_paused_states_do_not_claim_active_learning(self):
        cases = (
            ({"native_state": "unavailable"}, "device_unavailable"),
            ({"active": False}, "controller_inactive"),
            ({"ready": False}, "controller_inactive"),
            ({"record": {"pending": {"expected": "off"}}}, "pending_command"),
            ({"record": {"upstream": {"pending": {"expected": "on"}}}}, "pending_command"),
            ({"record": {"paused": "physical_manual_override"}}, "controller_paused"),
            ({"observed": {"status": "window_open_wait"}}, "controller_paused"),
            ({"hold": {"operating_mode": "heat", "reason": "single_feedback_sensor_required"}},
             "single_feedback_sensor_required"),
        )
        for changes, reason in cases:
            with self.subTest(changes=changes):
                args = self.arguments()
                args.update(changes)
                result = status.snapshot(**args)
                self.assertEqual(result["reason"], reason)
                self.assertNotEqual(result["status"], "collecting")

    def test_other_modes_do_not_supply_progress_review_holds_or_last_application(self):
        args = self.arguments(automatic=True)
        args.update(
            record={"pid_passive": self.model("cool"), "pid_passive_review": {
                "operating_mode": "cool", "state": "pending"}},
            observer_context=self.context("cool"),
            progress={"valid_cycles": 6, "last_rejection_reason": "sensor_jump"},
            hold={"operating_mode": "cool", "reason": "verified_activity_required"},
        )
        args["cfg"]["pid_last_calibration"] = {
            "operating_mode": "cool", "method": "passive_imc_lambda", "at": self.NOW - 60,
        }
        result = status.snapshot(**args)
        self.assertEqual(result["valid_cycles"], 0)
        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["reason"], "waiting_for_complete_cycles")
        args["cfg"]["pid_calibration_method"] = "adaptive_suggest"
        self.assertNotEqual(status.snapshot(**args)["status"], "ready_for_review")

    def test_current_review_is_visible_but_same_mode_stale_context_is_not_ready(self):
        args = self.arguments()
        args["record"] = {"pid_passive": self.model(), "pid_passive_review": {
            "operating_mode": "heat", "state": "pending", "context": self.context(),
            "cycle_at": self.NOW - 300,
        }}
        self.assertEqual(status.snapshot(**args)["status"], "ready_for_review")
        args["record"]["pid_passive_review"]["context"] = self.context(sensor="sensor.old")
        self.assertNotEqual(status.snapshot(**args)["status"], "ready_for_review")
        args["record"].pop("pid_passive")
        self.assertNotEqual(status.snapshot(**args)["status"], "ready_for_review")

    def test_cooldown_then_two_new_cycles_and_safe_off_are_reported(self):
        args = self.arguments(automatic=True)
        args["record"]["pid_passive"] = self.model()
        last_cycle = self.NOW - 2 * passive.AUTO_INTERVAL_S
        last = {"method": "passive_imc_lambda", "operating_mode": "heat",
                "at": self.NOW - 60, "cycle_at": last_cycle}
        args["cfg"]["pid_last_calibration"] = last
        result = status.snapshot(**args)
        self.assertEqual(result["status"], "cooldown")
        self.assertEqual(result["next_application_at"], last["at"] + passive.AUTO_INTERVAL_S)
        last["at"] = self.NOW - passive.AUTO_INTERVAL_S
        args["record"]["pid_passive"]["cycles"] = [{"at": last_cycle + 300}]
        self.assertEqual(status.snapshot(**args)["reason"], "new_cycles_required")
        args["record"]["pid_passive"]["cycles"].append({"at": last_cycle + 600})
        args["native_state"] = "heat"
        self.assertEqual(status.snapshot(**args)["status"], "waiting_for_safe_off")
        args["native_state"] = "off"
        args["record"]["power"] = {"climate.unit": {"since": self.NOW - 10}}
        self.assertEqual(status.snapshot(**args)["status"], "waiting_for_safe_off")

    def test_rejection_and_no_change_are_truthful_and_snapshot_is_read_only(self):
        args = self.arguments()
        args.update(observer_context=self.context(), progress={
            "valid_cycles": 1, "last_rejection_reason": "no_stable_plateau"})
        before = deepcopy(args)
        self.assertEqual(status.snapshot(**args)["reason"], "no_stable_plateau")
        self.assertEqual(args, before)
        args["record"]["pid_passive"] = self.model()
        args["record"]["pid_passive"]["summary"]["suggested_gains"] = {
            key: args["cfg"][key] for key in ("kp", "ki", "kd")}
        self.assertEqual(status.snapshot(**args)["status"], "no_change")


if __name__ == "__main__":
    unittest.main(verbosity=2)

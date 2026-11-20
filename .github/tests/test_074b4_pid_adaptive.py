"""Generic adaptive PID checks against an independent closed-loop plant.

Production pid_step, pid_bumpless and PWM allocation are loaded unchanged.
Synthetic plants generate fresh reports, device output edges and noise; no
learner thresholds are shortened and no validated model/candidate is seeded.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import asdict, dataclass
import importlib.util
import math
from pathlib import Path
import random
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem_074b4_adaptive_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


def load(name):
    spec = importlib.util.spec_from_file_location(PACKAGE + "." + name, SOURCE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


phase = load("pid_phase")
adaptive = load("pid_adaptive")
store = load("pid_adaptive_store")
allocator = load("pid_output_allocator")
pid_math = load("pid_math")

# Avoid importing HA in pure mathematical tests while executing the exact
# production definitions, rather than a second hand-written PID controller.
tree = ast.parse((SOURCE / "equipment_model.py").read_text())
names = {"PIDMemory", "pid_step", "pid_bumpless"}
nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
production = {"math": math, "dataclass": dataclass}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "production PID definitions", "exec"), production)
pid_step, transfer = production["pid_step"], production["pid_bumpless"]


def observer(saved=None, now=None):
    return adaptive.AdaptiveObserver(saved, now=now, stepper=pid_step, transfer=transfer)


def sample(at=1_000_000., measured=20., target=21., output=0., demand=10.,
           metric="temperature", increasing=True, band=.3, **kwargs):
    result = {
        "context": "same-device-source-and-mode",
        "observed_at": at, "reported_at": at, "output_at": at,
        "measured": measured, "target": target, "metric": metric,
        "unit": "°C", "increasing": increasing, "band": band,
        "target_semantics": "band",
        "gains": {"kp": 10., "ki": .1, "kd": 0.},
        "sample_seconds": 120., "cycle_seconds": 600.,
        "min_on_seconds": 60., "min_off_seconds": 60., "max_on_seconds": 7200.,
        "actuator_kind": "percentage", "min_percentage": 1., "max_percentage": 100.,
        "percentage_step": 1.,
        "requested_output": demand, "constrained_output": output,
        "observed_output": output, "output_verified": output is not None,
        "constraints": [], "safe": True,
    }
    result.update(kwargs)
    return result


class Plant:
    """First-order environment with independent exact physical integration."""

    def __init__(self, gains=None, *, kind="percentage", increasing=True,
                 metric="temperature", band=.3, ambient=18., gain=8.,
                 target=21., tau=960., delay=0., step=120., noise=0., seed=74,
                 max_on=86400., semantics="band"):
        self.gains = gains or {"kp": 10., "ki": .1, "kd": 0.}
        self.kind, self.increasing, self.metric, self.band = kind, increasing, metric, band
        self.ambient, self.gain, self.target, self.tau = ambient, gain, target, tau
        self.delay, self.step, self.noise = delay, step, noise
        self.max_on = max_on
        self.semantics = semantics
        self.rng = random.Random(seed)
        self.value = ambient
        self.now = 1_000_000.
        self.output, self.output_at = 0., self.now
        self.memory = None
        self.anchor = self.now
        self.served = self.stopped = self.on_since = None
        self.off_since = self.now - 600
        self.events = [(self.now - 3600, 0.)]
        self.seen = []

    def measured(self):
        return self.value + self.rng.gauss(0., self.noise)

    def _integrate(self, end):
        cursor = self.now
        current = self.events[0][1]
        for stamp, output in self.events:
            if stamp <= cursor - self.delay:
                current = output
        boundaries = [(t + self.delay, u) for t, u in self.events if cursor < t + self.delay < end]
        for boundary, after in boundaries + [(end, current)]:
            equilibrium = self.ambient + (1 if self.increasing else -1) * self.gain * current
            self.value = equilibrium + (self.value - equilibrium) * math.exp(-(boundary - cursor) / self.tau)
            cursor, current = boundary, after
        self.now = end

    def tick(self, learner, **overrides):
        measured = self.measured()
        datum = sample(self.now, measured, self.target, self.output * 100,
                       self.memory.demand if self.memory else self.gains["kp"] * abs(self.target - measured),
                       metric=self.metric, increasing=self.increasing, band=self.band,
                       gains=deepcopy(self.gains), actuator_kind=self.kind, output_at=self.output_at,
                       sample_seconds=self.step, max_on_seconds=self.max_on,
                       target_semantics=self.semantics,
                       pid_memory=asdict(self.memory) if self.memory else None,
                       pwm_state={"anchor": self.anchor, "served_at": self.served,
                                  "stopped_at": self.stopped, "on_since": self.on_since,
                                  "off_since": self.off_since})
        if self.kind == "setpoint_trim":
            direction = 1 if self.increasing else -1
            datum.update(min_percentage=0., max_output_change=100./3,
                         percentage_step=.1 / 1.5 * 100,
                         output_step_origin=direction * (5. - self.target) / 1.5 * 100,
                         output_quantization="native_half_up" if self.increasing else "native_half_down",
                         output_changed_at=self.output_at)
        datum.update(overrides)
        learner.observe(datum)
        self.seen.append(deepcopy(learner.snapshot()))
        end = self.now + self.step
        while self.now < end - 1e-7:
            self.memory = pid_step(measured, self.target, self.now, increasing=self.increasing,
                                   sample=self.step, memory=self.memory, **self.gains)
            demand = self.memory.demand
            next_timer = None
            if self.kind == "binary":
                info = phase.sampled_binary_pwm_plan(
                    demand, self.now - self.anchor, 600., 60., 60.,
                    starting=self.output == 0,
                    served_elapsed=self.served - self.anchor if self.served is not None else None,
                    stopped_elapsed=self.stopped - self.anchor if self.stopped is not None else None)
                new_output = float(info["wanted"])
                next_timer = info.get("next_evaluation_seconds")
            elif self.kind == "setpoint_trim":
                direction = 1 if self.increasing else -1
                actual_target = self.target + direction * 1.5 * self.output
                requested = self.target + direction * 1.5 * demand / 100
                bounded = max(actual_target - .5, min(actual_target + .5, requested))
                native = pid_math.quantize_target(bounded, .1, 5., 35.)
                new_output = direction * (native - self.target) / 1.5
                if abs(native - actual_target) > .500001:
                    new_output = self.output
            else:
                new_output = min(100., max(1., round(demand))) / 100 if demand >= 1 else 0.
            if self.kind != "setpoint_trim" and self.output and new_output == 0 and self.on_since is not None and self.now - self.on_since < 60:
                new_output = self.output
                next_timer = 60 - (self.now - self.on_since)
            if self.kind != "setpoint_trim" and self.output and self.on_since is not None and self.now - self.on_since >= self.max_on:
                new_output = 0.
            if self.kind != "setpoint_trim" and not self.output and new_output and self.off_since is not None and self.now - self.off_since < 60:
                new_output = 0.
                next_timer = 60 - (self.now - self.off_since)
            if new_output != self.output:
                if self.output == 0 and new_output:
                    self.served = self.on_since = self.now
                    self.off_since = None
                    self.anchor = max(self.anchor, self.now)
                elif self.output and new_output == 0:
                    self.stopped = self.off_since = self.now
                    self.on_since = None
                self.output, self.output_at = new_output, self.now
                self.events.append((self.now, new_output))
                learner.observe_output(self.now, new_output * 100.)
            boundary = min(end, self.now + next_timer) if next_timer and next_timer > 1e-6 else end
            if self.kind != "setpoint_trim" and self.output and self.on_since is not None:
                boundary = min(boundary, self.on_since + self.max_on)
            self._integrate(boundary)
        return datum


def config(plant):
    return {**plant.gains, "control_mode": "pid", "operating_mode": "heat",
            "requested_mode": "heat", "pid_calibration_method": "adaptive_auto",
            "sample_seconds": plant.step, "cycle_seconds": 600.,
            "min_on_seconds": 60., "min_off_seconds": 60., "max_on_seconds": plant.max_on}


def first_candidate(plant, learner, limit=128):
    for _ in range(limit):
        plant.tick(learner)
        if learner.snapshot().get("candidate"):
            return learner.snapshot()
    return None


def apply_candidate(plant, learner, snapshot):
    proof = store.make_proof(config(plant), snapshot, learner.context, plant.now)
    if proof is None:
        raise AssertionError("Public candidate was not authorized by the independent proof store")
    receipt = store.calibration_receipt(proof, plant.now)
    transferred = transfer(plant.memory, plant.target, increasing=plant.increasing, **receipt["applied_gains"])
    if transferred is None:
        raise AssertionError("Candidate could not be applied without an output jump")
    plant.memory, plant.gains = transferred, deepcopy(receipt["applied_gains"])
    learner.mark_applied(receipt)
    return receipt


class AssessmentTests(unittest.TestCase):
    def test_healthy_band_and_threshold_control_retains_gains(self):
        for metric, direction, semantics, value, target, band in (
            ("temperature", True, "band", 20.95, 21., .3),
            ("humidity", False, "band", 51., 50., 2.),
            ("co2", False, "upper_threshold", 600., 1000., 50.),
            ("pm25", False, "upper_threshold", 2., 15., 2.),
            ("humidity", True, "lower_threshold", 55., 45., 2.),
        ):
            with self.subTest(metric=metric, semantics=semantics):
                learner = observer()
                for i in range(16):
                    learner.observe(sample(1_000_000. + i * 120, value, target,
                                           metric=metric, increasing=direction, band=band,
                                           target_semantics=semantics))
                result = learner.snapshot()
                self.assertEqual(result["reason"], "tracking_well")
                self.assertIsNone(result["candidate"])
                self.assertEqual(result["performance"]["within_band_fraction"], 1.)
                if semantics != "band":
                    self.assertEqual(result["performance"]["mean_absolute_error"], 0.)

    def test_repeated_input_report_does_not_invent_samples_but_records_output_edges(self):
        learner = observer()
        learner.observe(sample())
        for i in range(1, 40):
            learner.observe(sample(1_000_000. + i * 5, reported_at=1_000_000.,
                                   output=(i % 2) * 100.))
        self.assertEqual(len(learner.points), 1)
        self.assertGreater(len(learner.events), 1)
        self.assertFalse(learner.snapshot()["fresh_evidence"])

    def test_invalid_or_interrupted_evidence_never_retunes(self):
        learner = observer()
        for i in range(24):
            learner.observe(sample(1_000_000. + i * 120, measured=19.))
        learner.observe(sample(1_004_000., safe=False, constraints=["window_open"]))
        self.assertEqual(len(learner.points), 0)
        self.assertIsNone(learner.snapshot()["candidate"])
        self.assertEqual(learner.snapshot()["reason"], "window_open")
        learner.observe(sample(1_004_100., measured=float("nan")))
        self.assertFalse(learner.snapshot()["fresh_evidence"])

    def test_capacity_and_unknown_actuator_are_not_tuning_failures(self):
        for output, demand, expected in ((100., 100., "capacity_limited"),
                                        (None, 50., "output_unverified")):
            with self.subTest(expected=expected):
                learner = observer()
                for i in range(40):
                    learner.observe(sample(1_000_000. + i * 120, measured=18.,
                                           output=output, demand=demand))
                self.assertEqual(learner.snapshot()["reason"], expected)
                self.assertIsNone(learner.snapshot()["candidate"])

    def test_rolling_history_includes_new_disturbance_after_previous_cap(self):
        learner = observer()
        for i in range(260):
            learner.observe(sample(1_000_000. + i * 120, measured=21. if i < 210 else 25.))
        self.assertEqual(len(learner.points), adaptive.MAX_SAMPLES)
        self.assertEqual(learner.points[-1]["value"], 25.)
        self.assertNotEqual(learner.snapshot()["reason"], "tracking_well")
        saved = learner.ledger()
        self.assertFalse(saved["raw_history_saved"])
        self.assertNotIn("points", saved)
        restored = observer(saved, now=1_040_000.)
        self.assertEqual(len(restored.points), 0)
        self.assertFalse(restored.snapshot()["fresh_evidence"])
        self.assertIsNone(restored.snapshot()["candidate"])

    def test_peer_response_or_unknown_output_cannot_survive_in_a_later_fit(self):
        for ambiguity in ({"constraints": ["other_controller_active"]}, {"output_verified": False}):
            with self.subTest(ambiguity=ambiguity):
                learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.})
                for _ in range(16):
                    plant.tick(learner)
                plant.tick(learner, **ambiguity)
                contaminated_at = plant.now - plant.step
                self.assertIsNone(learner.snapshot()["candidate"])
                for _ in range(16):
                    plant.tick(learner)
                # One contaminated report is less than 25% of the original
                # window, but every identification point must be after it.
                self.assertEqual(len(learner.points), 16)
                self.assertTrue(all(p["at"] > contaminated_at for p in learner.points))
                self.assertIsNone(learner.snapshot()["candidate"])

    def test_fresh_sensor_noise_does_not_authorize_a_gain_direction(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.}, noise=.5)
        for _ in range(128):
            plant.tick(learner)
        self.assertTrue(all(s.get("candidate") is None for s in plant.seen))
        self.assertNotEqual(learner.snapshot()["reason"], "tracking_well")

    def test_corrupt_saved_trials_and_repeated_stale_reports_are_not_evidence(self):
        for trial in ({"state": "evaluating", "baseline": []},
                      {"state": "evaluating", "baseline": {"observed_seconds": float("nan")}}):
            learner = observer({"version": 1, "algorithm": "performance_v1", "trial": trial})
            learner.observe(sample())
            self.assertIsNone(learner.trial)
        learner = observer()
        learner.observe(sample())
        learner.observe(sample(1_002_000., reported_at=1_000_000.))
        self.assertEqual(learner.snapshot()["reason"], "measurement_outdated")
        self.assertFalse(learner.snapshot()["fresh_evidence"])

    def test_acknowledged_output_edges_do_not_create_process_samples(self):
        learner = observer()
        learner.observe(sample())
        self.assertTrue(learner.observe_output(1_000_030., 100.))
        self.assertTrue(learner.observe_output(1_000_060., 0.))
        self.assertEqual(len(learner.points), 1)
        self.assertFalse(learner.observe_output(1_000_020., 100.))
        self.assertEqual(learner.events[-1], (1_000_060., 0.))
        learner.observe_output(1_000_090., None)
        self.assertEqual(len(learner.points), 0)
        self.assertEqual(learner.snapshot()["reason"], "output_unverified")


class ClosedLoopTests(unittest.TestCase):
    def test_real_normal_short_cycles_can_generate_authorized_candidate(self):
        learner = observer()
        plant = Plant({"kp": 10., "ki": .5, "kd": 0.}, kind="percentage")
        for _ in range(128):
            plant.tick(learner)
        candidates = [s for s in plant.seen if s.get("candidate")]
        self.assertTrue(candidates, [(s["samples"], s["reason"]) for s in plant.seen[7::8]])
        snapshot = candidates[0]
        candidate = snapshot["candidate"]
        self.assertGreater(candidate["predicted_improvement"], 0.)
        self.assertTrue(candidate["validated"])
        self.assertEqual(candidate["kd"], 0.)
        cfg = config(plant)
        proof = store.make_proof(cfg, snapshot, learner.context, candidate["evidence_at"])
        self.assertIsNotNone(proof)
        self.assertTrue(store.validate_proof(proof, cfg, snapshot, learner.context, candidate["evidence_at"]))

    def test_short_binary_on_off_cycles_produce_a_real_validated_candidate(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.}, kind="binary")
        snapshot = first_candidate(plant, learner)
        self.assertIsNotNone(snapshot)
        on_runs = [right[0] - left[0] for left, right in zip(plant.events, plant.events[1:]) if left[1] > 0]
        self.assertGreater(len(on_runs), 3)
        self.assertLess(max(on_runs), 5 * 60)
        self.assertIsNotNone(store.make_proof(config(plant), snapshot, learner.context, plant.now))

    def test_the_same_learning_equations_support_nonthermal_units_and_directions(self):
        for metric, band, increasing, semantics, target in (
            ("humidity", 2., True, "band", 50.),
            ("humidity", 2., False, "band", 50.),
            ("co2", 50., False, "upper_threshold", 1000.),
            ("pm25", 2., False, "upper_threshold", 15.),
        ):
            with self.subTest(metric=metric, increasing=increasing):
                scale, direction = band / .3, 1 if increasing else -1
                plant = Plant({"kp": 10. / scale, "ki": .5 / scale, "kd": 0.},
                              metric=metric, band=band, increasing=increasing, semantics=semantics,
                              ambient=target - direction * 3 * scale, target=target, gain=8 * scale)
                learner = observer()
                snapshot = first_candidate(plant, learner)
                self.assertIsNotNone(snapshot)
                self.assertEqual(snapshot["metric"], metric)
                self.assertEqual(snapshot["target_semantics"], semantics)
                self.assertTrue(snapshot["candidate"]["validated"])

    def test_real_application_is_followed_by_observation_and_retention(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.})
        receipt = apply_candidate(plant, learner, first_candidate(plant, learner))
        for _ in range(31):
            plant.tick(learner)
            self.assertEqual(learner.trial["state"], "evaluating")
            self.assertIsNone(learner.snapshot()["candidate"])
        plant.tick(learner)
        self.assertEqual(learner.trial["state"], "retained")
        self.assertIn(learner.snapshot()["reason"], ("adjustment_verified", "stable_after_adjustment"))
        self.assertEqual(learner.last_application, receipt)

    def test_new_reports_refresh_metrics_without_mutating_candidate_proof(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.})
        before = first_candidate(plant, learner)
        proof = store.make_proof(config(plant), before, learner.context, plant.now)
        plant.tick(learner)
        after = learner.snapshot()
        self.assertGreater(after["observed_seconds"], before["observed_seconds"])
        self.assertEqual(after["candidate"], before["candidate"])
        self.assertTrue(store.validate_proof(proof, config(plant), after, learner.context, plant.now))

    def test_native_target_trim_is_assessed_on_acknowledged_command_steps(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.}, kind="setpoint_trim")
        for _ in range(128):
            plant.tick(learner)
        # This is an empirical outer-loop response to acknowledged setpoints;
        # neutral trim is an operating thermostat, not a presumed power OFF.
        self.assertTrue(any(s.get("model") for s in plant.seen))
        self.assertNotEqual(learner.snapshot()["reason"], "actuator_model_unverified")
        self.assertTrue(all(abs(b[1] - a[1]) * 1.5 <= .500001
                            for a, b in zip(plant.events, plant.events[1:])))

    def test_restart_during_a_trial_requires_a_fresh_comparable_window(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.})
        apply_candidate(plant, learner, first_candidate(plant, learner))
        for _ in range(16):
            plant.tick(learner)
        restored = observer(learner.ledger(), now=plant.now)
        self.assertEqual(restored.trial["state"], "evaluating")
        self.assertFalse(restored.snapshot()["fresh_evidence"])
        for _ in range(31):
            plant.tick(restored)
            self.assertEqual(restored.trial["state"], "evaluating")
            self.assertIsNone(restored.snapshot()["candidate"])
        plant.tick(restored)
        self.assertEqual(restored.trial["state"], "retained")

    def test_persistent_environment_change_closes_inconclusive_without_false_rollback(self):
        learner, plant = observer(), Plant({"kp": 10., "ki": .5, "kd": 0.})
        apply_candidate(plant, learner, first_candidate(plant, learner))
        # A real changed thermal load invalidates the old local model. It is
        # neither a gain-regression finding nor permanent adaptation lockout.
        plant.ambient -= 8.
        for _ in range(96):
            plant.tick(learner)
        self.assertEqual(learner.trial["state"], "inconclusive")
        self.assertEqual(learner.trial["verification_windows"], 3)
        self.assertEqual(learner.snapshot()["reason"], "verification_inconclusive")
        self.assertIsNone(learner.snapshot()["candidate"])
        for _ in range(8):
            plant.tick(learner)
        self.assertEqual(learner.snapshot()["reason"], "new_evidence_required")

    def test_actual_regression_requests_receipted_rollback_and_restart_requires_new_evidence(self):
        # Delay and PWM discontinuities make a local improvement forecast
        # imperfect. This exact independent plant naturally supplies a case
        # whose held-out candidate improves, but its later trial regresses.
        learner = observer()
        plant = Plant({"kp": 20., "ki": .5, "kd": 0.}, kind="binary", tau=1920., delay=480.)
        original = deepcopy(plant.gains)
        snapshot = first_candidate(plant, learner)
        self.assertIsNotNone(snapshot)
        receipt = apply_candidate(plant, learner, snapshot)
        for _ in range(96):
            plant.tick(learner)
            self.assertIsNone(learner.snapshot()["candidate"])
            if learner.trial["state"] == "rollback_recommended":
                break
        self.assertEqual(learner.trial["state"], "rollback_recommended")
        self.assertEqual(learner.trial["revert_gains"], original)
        cfg = {**config(plant), "pid_last_calibration": receipt}
        proof = store.make_proof(cfg, learner.snapshot(), learner.context, plant.now, rollback=True)
        self.assertIsNotNone(proof)
        self.assertTrue(store.validate_proof(proof, cfg, learner.snapshot(), learner.context, plant.now))
        restored = observer(learner.ledger(), now=plant.now)
        self.assertIsNone(store.make_proof(cfg, restored.snapshot(), restored.context, plant.now, rollback=True))
        # An outage is not new support for an expired decision. If conditions
        # now change, the next comparison must withhold that old rollback.
        plant.ambient -= 8.
        for _ in range(32):
            plant.tick(restored)
        self.assertNotEqual(restored.trial["state"], "rollback_recommended")
        self.assertEqual(restored.trial["application"], receipt)
        self.assertNotIn("revert_gains", restored.trial)
        self.assertNotIn("evidence_id", restored.trial)
        self.assertIsNone(store.make_proof(cfg, restored.snapshot(), restored.context, plant.now, rollback=True))
        # A committed receipt is the only event that labels gains restored.
        rollback_receipt = store.calibration_receipt(proof, proof["created_at"])
        learner.mark_reverted(rollback_receipt)
        self.assertEqual(learner.snapshot()["status"], "reverted")
        self.assertEqual(learner.trial["rollback_application"]["applied_gains"], original)


class AdapterTests(unittest.TestCase):
    def test_staged_and_percentage_fan_commands_match_native_allocation(self):
        stages = [100. / 3, 200. / 3, 100.]
        names = ("low", "medium", "high")
        for quiet in (False, True):
            cfg = adaptive._config(sample(actuator_kind="ordered_stage", output_stages=stages,
                                          max_percentage=stages[1] if quiet else 100.))
            for demand in (1., 20., 33.333, 33.334, 60., 90., 100.):
                expected = allocator.fan_speed_for_pid(demand, modes=names, percentage=False,
                                                       quiet=quiet, quiet_mode="medium")
                self.assertAlmostEqual(adaptive._allocate_output(demand, 0., cfg), stages[names.index(expected)] / 100.)
        cfg = adaptive._config(sample(output_stages=[20., 40., 80.], min_percentage=20., max_percentage=60.,
                                      output_quantization="floor"))
        self.assertEqual(adaptive._allocate_output(58., .4, cfg), .4)
        self.assertEqual(adaptive._allocate_output(19., .4, cfg), 0.)

    def test_numeric_slew_and_native_trim_quantization_use_production_ties(self):
        cfg = adaptive._config(sample(min_percentage=0., percentage_step=5., max_output_change=10.))
        self.assertEqual(adaptive._allocate_output(90., .225, cfg), .3)
        for increasing in (True, False):
            direction = 1 if increasing else -1
            goal, actual, native_min, native_max = 21., 21., 5., 35.
            cfg = adaptive._config(sample(actuator_kind="setpoint_trim", min_percentage=0.,
                                          max_output_change=100./3, percentage_step=100./3,
                                          output_step_origin=direction * (native_min-goal)/1.5*100,
                                          output_quantization="native_half_up" if increasing else "native_half_down"))
            for demand in (0., 100./6, 100./3, 50., 100.):
                desired = goal + direction * 1.5 * demand / 100
                command = max(actual - .5, min(actual + .5, desired))
                native = pid_math.quantize_target(command, .5, native_min, native_max)
                expected = direction * (native-goal)/1.5
                self.assertAlmostEqual(adaptive._allocate_output(demand, 0., cfg), expected, places=7)

    def test_cached_input_integrals_equal_exact_edge_integration(self):
        events = [(0., 0.), (30., .4), (75., .1), (160., 1.), (230., .2)]
        cached = adaptive._InputTrace(events)
        for tau in (30., 120., 600.):
            for start, end, delay in ((20., 80., 0.), (80., 200., 20.), (200., 300., 60.)):
                self.assertAlmostEqual(adaptive._forcing(events, start, end, tau, delay),
                                       adaptive._forcing(cached, start, end, tau, delay), places=10)
        cached.append((300., .7))
        self.assertAlmostEqual(adaptive._forcing(events+[(300., .7)], 240., 360., 120.),
                               adaptive._forcing(cached, 240., 360., 120.), places=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)

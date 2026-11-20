"""Versioned adaptive proposals, interrupted commits and rollback authority."""
from copy import deepcopy
import ast
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "hem_performance_lifecycle"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/environment_manager")]
sys.modules[PACKAGE] = package
store = importlib.import_module(PACKAGE + ".pid_adaptive_store")
review = importlib.import_module(PACKAGE + ".pid_review")

NOW = 100_000.0
CONTEXT = '{"mode":"humidify","metric":"humidity","source":"room_mean"}'


def cfg(method="adaptive_auto"):
    return {
        "control_mode": "pid", "operating_mode": "humidify",
        "pid_calibration_method": method,
        "kp": 10.0, "ki": .1, "kd": 0.0,
        "sample_seconds": 120, "cycle_seconds": 600,
        "min_on_seconds": 60, "min_off_seconds": 60, "max_on_seconds": 7200,
        "power_switch_entity": None, "power_switch_cooldown_seconds": 0,
    }


def snapshot():
    return {
        "algorithm": store.ALGORITHM, "context": CONTEXT,
        "status": "candidate_ready", "fresh_evidence": True, "metric": "humidity",
        "performance": {"observed_seconds": 1200, "mean_error": 2.2},
        "model": {"gain": 8.0, "tau_seconds": 600.0},
        "candidate": {
            "validated": True, "evidence_id": "a" * 64, "evidence_at": NOW - 60,
            "previous_gains": {"kp": 10.0, "ki": .1, "kd": 0.0},
            "kp": 9.0, "ki": .095, "kd": 0.0,
            "validated_windows": 2, "predicted_improvement": .08,
        },
        "verification": {"state": "none"},
    }


def saved(value):
    return {"version": 1, "algorithm": store.ALGORITHM, "context": CONTEXT,
            "ledger": {"version": 1, "algorithm": store.ALGORITHM,
                       "context": CONTEXT, "assessment": deepcopy(value)}}


class AuthorityTests(unittest.TestCase):
    def test_fresh_validated_normal_observation_authorizes_one_bounded_trial(self):
        settings, data = cfg(), snapshot()
        proof = store.make_proof(settings, data, CONTEXT, NOW)
        self.assertTrue(store.validate_proof(proof, settings, data, CONTEXT, NOW + 20))
        receipt = store.calibration_receipt(proof, NOW + 20)
        self.assertEqual(receipt["method"], "performance_adaptive")
        self.assertEqual(receipt["applied_gains"], proof["apply"])
        settings.update(proof["apply"], pid_last_calibration=receipt)
        self.assertFalse(store.validate_proof(proof, settings, data, CONTEXT, NOW + 21))

    def test_stale_context_gain_timing_and_evidence_are_rejected_after_await(self):
        settings, data = cfg(), snapshot()
        proof = store.make_proof(settings, data, CONTEXT, NOW)
        for field, value in (("kp", 10.1), ("operating_mode", "dry"),
                             ("sample_seconds", 300), ("min_off_seconds", 600),
                             ("pid_calibration_method", "manual")):
            with self.subTest(field=field):
                self.assertFalse(store.validate_proof(proof, {**settings, field: value}, data, CONTEXT, NOW))
        self.assertFalse(store.validate_proof(proof, settings, data, CONTEXT + "x", NOW))
        self.assertFalse(store.validate_proof(proof, settings, data, CONTEXT, NOW + 1801))
        changed = deepcopy(data)
        changed["candidate"]["evidence_id"] = "b" * 64
        self.assertFalse(store.validate_proof(proof, settings, changed, CONTEXT, NOW))

    def test_only_validated_useful_nonzero_bounded_adjustments_pass(self):
        settings = cfg()
        cases = (
            {"validated": False}, {"validated_windows": 0}, {"validated_windows": True},
            {"predicted_improvement": 0}, {"predicted_improvement": float("nan")},
            {"kp": 8.99}, {"kd": .001}, {"kp": float("inf")}, {"ki": True},
            {"kp": 10.0, "ki": .1}, {"evidence_id": "unverified"},
            {"evidence_at": NOW + 1}, {"evidence_at": False},
        )
        for patch in cases:
            with self.subTest(patch=patch):
                data = snapshot()
                data["candidate"].update(patch)
                self.assertIsNone(store.make_proof(settings, data, CONTEXT, NOW))
        data = snapshot()
        data["fresh_evidence"] = False
        self.assertIsNone(store.make_proof(settings, data, CONTEXT, NOW))
        data = snapshot()
        data["verification"]["state"] = "evaluating"
        self.assertIsNone(store.make_proof(settings, data, CONTEXT, NOW))

    def test_approve_is_bound_to_explicit_suggest_mode(self):
        self.assertIsNone(store.make_proof(cfg("adaptive_suggest"), snapshot(), CONTEXT, NOW))
        self.assertIsNone(store.make_proof(cfg(), snapshot(), CONTEXT, NOW, approved_id="a" * 32))
        self.assertIsNone(store.proposal_for(cfg(), snapshot(), CONTEXT, NOW))
        proposal = store.proposal_for(cfg("adaptive_suggest"), snapshot(), CONTEXT, NOW)
        self.assertTrue(review.is_pending(proposal))
        proof = store.make_proof(cfg("adaptive_suggest"), snapshot(), CONTEXT, NOW,
                                 approved_id=proposal["id"])
        self.assertIsNotNone(proof)
        self.assertEqual(store.calibration_receipt(proof, NOW)["proposal_id"], proposal["id"])

    def test_existing_derivative_gain_cannot_change_in_a_trial(self):
        settings, data = cfg(), snapshot()
        settings["kd"] = 1.0
        data["candidate"]["previous_gains"]["kd"] = 1.0
        data["candidate"]["kd"] = 1.0
        self.assertIsNotNone(store.make_proof(settings, data, CONTEXT, NOW))
        for derivative in (.9, 1.01, 1.1):
            with self.subTest(derivative=derivative):
                data["candidate"]["kd"] = derivative
                self.assertIsNone(store.make_proof(settings, data, CONTEXT, NOW))

    def test_live_progress_cannot_rewrite_frozen_candidate_evidence(self):
        settings, data = cfg(), snapshot()
        data["candidate"]["baseline"] = deepcopy(data["performance"])
        data["candidate"]["model"] = deepcopy(data["model"])
        proof = store.make_proof(settings, data, CONTEXT, NOW)
        data["performance"] = {"observed_seconds": 1320, "mean_error": 2.0}
        data["model"] = {"display_only": True}
        self.assertTrue(store.validate_proof(proof, settings, data, CONTEXT, NOW + 20))
        data["candidate"]["baseline"]["mean_error"] = 1.0
        self.assertFalse(store.validate_proof(proof, settings, data, CONTEXT, NOW + 20))

    def test_atomic_gain_receipt_recovers_interrupted_review_bookkeeping(self):
        settings, data = cfg("adaptive_suggest"), snapshot()
        proposal = store.proposal_for(settings, data, CONTEXT, NOW)
        proof = store.make_proof(settings, data, CONTEXT, NOW, approved_id=proposal["id"])
        receipt = store.calibration_receipt(proof, NOW + 1)
        settings.update(proof["apply"], pid_last_calibration=receipt)
        # An exact committed application survives missing volatile observations.
        projected = review.review_projection(proposal, settings, NOW + 2,
                                             context="restarted", saved={})
        self.assertEqual(projected["state"], "applied")
        self.assertEqual(proposal["state"], "pending")  # pure projection
        for field, value in (("proposal_id", "b" * 32), ("context", "wrong"),
                             ("evidence_id", "b" * 64), ("operating_mode", "dry"),
                             ("method", "performance_adaptive"), ("at", float("nan"))):
            altered = deepcopy(settings)
            altered["pid_last_calibration"][field] = value
            self.assertFalse(review.review_application_matches(proposal, altered), field)

    def test_pending_review_tracks_current_completed_evidence(self):
        settings, data = cfg("adaptive_suggest"), snapshot()
        proposal = store.proposal_for(settings, data, CONTEXT, NOW)
        self.assertEqual(review.review_projection(proposal, settings, NOW,
                         context=CONTEXT, saved=saved(data))["state"], "pending")
        data["candidate"] = None
        self.assertEqual(review.review_projection(proposal, settings, NOW,
                         context=CONTEXT, saved=saved(data))["state"], "expired")
        self.assertEqual(review.review_projection(proposal, settings,
                         NOW + store.REVIEW_MAX_AGE_S + 1)["reason"], "recommendation_expired")
        changed = {**settings, "sample_seconds": 300}
        self.assertEqual(review.review_projection(proposal, changed, NOW)["reason"], "tuning_settings_changed")
        proposal["state"] = "discarded"
        self.assertEqual(review.review_projection(proposal, settings, NOW)["state"], "discarded")

    def test_rollback_restores_exact_trial_gains_and_cannot_be_invented(self):
        settings, data = cfg(), snapshot()
        proof = store.make_proof(settings, data, CONTEXT, NOW)
        receipt = store.calibration_receipt(proof, NOW)
        settings.update(proof["apply"], pid_last_calibration=receipt)
        data.update(candidate=None, last_application=receipt,
                    verification={"state": "rollback_recommended", "evidence_id": "c" * 64,
                                  "evidence_at": NOW + 600,
                                  "previous_gains": dict(proof["apply"]),
                                  "revert_gains": dict(proof["current"]),
                                  "reason": "confirmed_regression"})
        rollback = store.make_proof(settings, data, CONTEXT, NOW + 600, rollback=True)
        self.assertIsNotNone(rollback)
        # Restoring 10 after a 10% reduction to9 is valid despite being +11.1%.
        self.assertEqual(rollback["apply"]["kp"], 10)
        self.assertEqual(store.calibration_receipt(rollback, NOW + 600)["method"], "performance_rollback")
        data["verification"]["revert_gains"]["kp"] = 100
        self.assertIsNone(store.make_proof(settings, data, CONTEXT, NOW + 600, rollback=True))
        data["verification"]["revert_gains"]["kp"] = 10
        data.pop("last_application")
        self.assertIsNone(store.make_proof(settings, data, CONTEXT, NOW + 600, rollback=True))

    def test_unknown_and_malformed_saved_versions_do_not_authorize(self):
        for value in (None, [], {}, {"version": 0}, {"ledger": []},
                      {"version": 1, "algorithm": "future", "assessment": snapshot()}):
            self.assertEqual(store.saved_snapshot(value), {})

    def test_new_notifications_describe_observations_and_preserved_output(self):
        proposal = store.proposal_for(cfg("adaptive_suggest"), snapshot(), CONTEXT, NOW)
        for language in ("en", "el", "de"):
            text = review.notification_text(SimpleNamespace(name="Humidity"), proposal, language)
            self.assertIn("**KP**: 10 → 9", text)
            self.assertNotIn("24", text)
            self.assertNotIn("75", text)
        english = review.notification_text(SimpleNamespace(name="Humidity"), proposal)
        self.assertIn("observation windows", english)
        self.assertIn("preserves the current demand", english)
        self.assertIn("restored", english)

    def test_native_approve_button_uses_current_generic_context_and_guard(self):
        # Execute the production projection/availability methods. The button's
        # HA transport and spec identity are the only substitutes here.
        path = ROOT / "custom_components/environment_manager/button.py"
        source = ast.parse(path.read_text())
        original = next(node for node in source.body
                        if isinstance(node, ast.ClassDef) and node.name == "EquipmentPIDReviewButton")
        nodes = [node for node in original.body
                 if isinstance(node, ast.FunctionDef) and node.name in ("_review_status", "available")]
        holder = ast.ClassDef(name="ReviewButton", bases=[], keywords=[], body=nodes, decorator_list=[])
        module = ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[]))
        namespace = {"__package__": PACKAGE}
        exec(compile(module, str(path), "exec"), namespace)
        settings, data = cfg("adaptive_suggest"), snapshot()
        proposal = store.proposal_for(settings, data, CONTEXT, NOW)
        calls = []
        runtime = SimpleNamespace(
            _active=True, _ready=True, clock=lambda: NOW,
            records={"fixture": {"pid_adaptive": saved(data)}},
            _pid_adaptive_context=lambda spec, **kwargs: CONTEXT,
            _pid_adaptive_review_authorized=lambda spec, token: calls.append(token) or True,
            _pid_review_authorized=lambda *args, **kwargs: self.fail("Legacy guard used for generic evidence"),
        )
        button = namespace["ReviewButton"]()
        button._manager = SimpleNamespace(equipment=runtime)
        button._spec = SimpleNamespace(identifier="fixture")
        button._action = "approve"
        button._review = lambda: proposal
        button.controller_settings = settings
        self.assertTrue(button.available)
        self.assertEqual(calls, [proposal["id"]])
        runtime._pid_adaptive_review_authorized = lambda spec, token: False
        self.assertFalse(button.available)
        runtime._pid_adaptive_context = lambda spec, **kwargs: "different-input"
        self.assertFalse(button.available)
        button._action = "discard"
        self.assertTrue(button.available)


if __name__ == "__main__":
    unittest.main(verbosity=2)

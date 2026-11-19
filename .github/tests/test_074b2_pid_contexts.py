"""Pure production regressions for bounded, context-specific PID evidence.

No HA, actuator, service, Store, or fixture-specific controller implementation.
Exercise JSON restart roundtrips and real observer fitting/expiry independently
of the runtime tests that verify when these transforms are invoked.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import sys
import types
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"
PACKAGE = "hem_074b2_context_test"
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
store = load("pid_learning_store")


class ContextStoreTests(unittest.TestCase):
    NOW = 10_000_000.

    def context(self, mode="heat", profile="home", target=21., sensor="sensor.room"):
        return passive.identity("room", ["climate.unit"], "climate.unit", mode,
                                "humidity" if mode == "dry" else "temperature",
                                sensor, profile, target, "auto", None)

    def rows(self, count=5, *, now=None, gain=4.):
        now = self.NOW if now is None else now
        return [{"at": now - (count - index) * 3600, "gain": gain, "tau": 28.,
                 "dead": 10., "r2": .99, "duration_minutes": 205.}
                for index in range(count)]

    def seed(self, record, context, *, now=None, count=5, gain=4., sample=300):
        now = self.NOW if now is None else now
        metric = json.loads(context)[4]
        store.activate(record, context, now, metric, sample)
        store.remember(record, {"context": context,
                               "cycles": self.rows(count, now=now, gain=gain)}, now)

    def test_context_switch_roundtrip_keeps_independent_completed_models(self):
        record = {}
        home, sleep = self.context(), self.context(profile="sleep", target=19.)
        self.seed(record, home)
        home_model = deepcopy(record[store.ACTIVE])
        self.seed(record, sleep, now=self.NOW + 300, count=3, gain=6.)
        sleep_model = deepcopy(record[store.ACTIVE])
        self.assertEqual(sleep_model["summary"]["valid_cycles"], 3)
        self.assertTrue(store.activate(record, home, self.NOW + 600, "temperature", 300))
        self.assertEqual(record[store.ACTIVE], home_model)
        self.assertTrue(store.activate(record, sleep, self.NOW + 900, "temperature", 300))
        self.assertEqual(record[store.ACTIVE], sleep_model)
        self.assertEqual(len(record[store.BANK]), 2)

    def test_direction_target_and_sensor_do_not_share_cycle_counts(self):
        record = {}
        contexts = [self.context(), self.context("cool"), self.context(target=22.),
                    self.context(sensor="sensor.replacement")]
        for index, context in enumerate(contexts):
            self.seed(record, context, now=self.NOW + index * 300, count=index + 1)
        for index, context in enumerate(contexts):
            store.activate(record, context, self.NOW + 1500, "temperature", 300)
            self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], index + 1)

    def test_restart_roundtrip_restores_cycles_but_requires_fresh_complete_cycle(self):
        record = {}
        home, sleep = self.context(), self.context(profile="sleep")
        self.seed(record, home)
        self.seed(record, sleep, now=self.NOW + 300, count=3)
        restored = json.loads(json.dumps(record, allow_nan=False))
        store.activate(restored, home, self.NOW + 600, "temperature", 300)
        observer = passive.PassiveObserver(restored[store.ACTIVE], now=self.NOW + 600)
        self.assertEqual(len(observer.cycles), 5)
        self.assertEqual(observer.off, [])
        self.assertEqual(observer.on, [])
        self.assertIsNone(observer.last_t)
        self.assertTrue(observer.progress()["fresh_cycle_required"])
        self.assertEqual(restored[store.ACTIVE]["summary"]["status"], "validated")

    def test_legacy_active_ledger_migrates_and_remains_available_after_switch(self):
        home, sleep = self.context(), self.context(profile="sleep")
        record = {store.ACTIVE: {"context": home, "cycles": self.rows(),
                                 "summary": {"status": "validated", "valid_cycles": 99}}}
        self.assertTrue(store.activate(record, home, self.NOW, "temperature", 300))
        self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], 5)
        self.assertEqual(record[store.ACTIVE]["summary"]["status"], "validated")
        store.activate(record, sleep, self.NOW + 300, "temperature", 300)
        self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], 0)
        store.activate(record, home, self.NOW + 600, "temperature", 300)
        self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], 5)

    def test_legacy_prune_retains_model_without_guessing_actionable_sample_interval(self):
        context = self.context()
        record = {store.ACTIVE: {"context": context, "cycles": self.rows(),
                                 "summary": {"suggested_gains": {"kp": 999.}}}}
        store.prune(record, self.NOW)
        self.assertEqual(len(record[store.ACTIVE]["cycles"]), 5)
        self.assertIsNone(record[store.BANK][context]["sample_seconds"])
        self.assertNotIn("suggested_gains", record[store.ACTIVE]["summary"])
        store.activate(record, context, self.NOW, "temperature", 300)
        self.assertIn("suggested_gains", record[store.ACTIVE]["summary"])

    def test_repeated_same_context_activation_and_pruning_are_idempotent(self):
        record, context = {}, self.context()
        self.seed(record, context)
        before = deepcopy(record)
        self.assertFalse(store.activate(record, context, self.NOW + 300, "temperature", 300))
        self.assertFalse(store.prune(record, self.NOW + 600))
        self.assertFalse(store.remember(record, record[store.ACTIVE], self.NOW + 900))
        self.assertEqual(record, before, "No timestamp or per-tick storage churn")

    def test_sampling_change_recomputes_recommendation_from_the_same_evidence(self):
        record, context = {}, self.context()
        self.seed(record, context)
        self.assertIn("suggested_gains", record[store.ACTIVE]["summary"])
        store.activate(record, context, self.NOW + 300, "temperature", 3600)
        self.assertEqual(record[store.ACTIVE]["summary"]["status"],
                         "identified_gains_outside_safe_bounds")
        self.assertNotIn("suggested_gains", record[store.ACTIVE]["summary"])
        self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], 5)
        store.activate(record, context, self.NOW + 600, "temperature", 300)
        self.assertEqual(record[store.ACTIVE]["summary"]["status"], "validated")

    def test_expiry_recomputes_count_confidence_and_removes_stale_gains_without_new_cycle(self):
        record, context = {}, self.context()
        self.seed(record, context)
        now = self.NOW + passive.MAX_AGE_S - 2 * 3600
        self.assertTrue(store.prune(record, now))
        summary = record[store.ACTIVE]["summary"]
        self.assertEqual(summary["valid_cycles"], 2)
        self.assertEqual(summary["confidence"], "insufficient")
        self.assertNotIn("suggested_gains", summary)
        self.assertNotIn("last_cycle_at", summary)
        store.prune(record, self.NOW + passive.MAX_AGE_S)
        self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], 0)

    def test_age_boundary_future_rows_duplicates_and_raw_payloads_are_sanitized(self):
        record, context = {}, self.context()
        row = self.rows(1)[0]
        stamps = [self.NOW - passive.MAX_AGE_S - 1,
                  self.NOW - passive.MAX_AGE_S, self.NOW + 1, -1., self.NOW - 100]
        rows = [{**row, "at": stamp, "raw_samples": list(range(10))} for stamp in stamps]
        rows.extend([{**row, "at": self.NOW - 100}, {**row, "gain": float("nan")},
                     {**row, "tau": 0.}, {**row, "dead": float("inf")},
                     {**row, "r2": True}, {**row, "gain": 10 ** 1000},
                     {**row, "gain": 1e308}, {**row, "tau": 1e308}])
        store.activate(record, context, self.NOW, "temperature", 300)
        store.remember(record, {"context": context, "cycles": rows,
                               "summary": {"valid_cycles": 99}, "on": [1, 2]}, self.NOW)
        self.assertEqual([r["at"] for r in record[store.ACTIVE]["cycles"]],
                         [self.NOW - passive.MAX_AGE_S, self.NOW - 100])
        self.assertNotIn("raw_samples", json.dumps(record, allow_nan=False))
        self.assertNotIn("on", record[store.ACTIVE])

    def test_only_six_newest_valid_cycles_are_kept_and_bank_has_no_shared_alias(self):
        record, context = {}, self.context()
        store.activate(record, context, self.NOW, "temperature", 300)
        rows = self.rows(20)
        store.remember(record, {"context": context, "cycles": list(reversed(rows))}, self.NOW)
        self.assertEqual(record[store.ACTIVE]["cycles"], rows[-6:])
        self.assertEqual(record[store.BANK][context]["cycles"], rows[-6:])
        record[store.ACTIVE]["cycles"][0]["gain"] = 999.
        self.assertEqual(record[store.BANK][context]["cycles"][0]["gain"], 4.)

    def test_context_bank_has_twelve_entry_lru_bound_and_preserves_selected_context(self):
        record = {}
        contexts = [self.context(target=20. + index / 10) for index in range(21)]
        for index, context in enumerate(contexts[:20]):
            self.seed(record, context, now=self.NOW + index * 300, count=1)
        self.assertEqual(len(record[store.BANK]), 12)
        self.assertEqual(set(record[store.BANK]), set(contexts[8:20]))
        store.activate(record, contexts[8], self.NOW + 6100, "temperature", 300)
        self.seed(record, contexts[20], now=self.NOW + 6400, count=1)
        self.assertIn(contexts[8], record[store.BANK])
        self.assertNotIn(contexts[9], record[store.BANK])
        self.assertEqual(record[store.ACTIVE]["context"], contexts[20])
        self.assertEqual(len(record[store.BANK]), 12)

    def test_inactive_expired_entries_are_removed(self):
        record = {}
        old, fresh = self.context(), self.context("cool")
        self.seed(record, old)
        self.seed(record, fresh, now=self.NOW + passive.MAX_AGE_S - 1000)
        store.prune(record, self.NOW + passive.MAX_AGE_S)
        self.assertNotIn(old, record[store.BANK])
        self.assertEqual(record[store.ACTIVE]["context"], fresh)
        self.assertEqual(record[store.ACTIVE]["summary"]["valid_cycles"], 5)

    def test_mode_specific_invalidation_leaves_other_modes_and_gains_untouched(self):
        record = {"kp": 10., "pid_passive_review": {"state": "pending"}}
        heat, sleep, cool = self.context(), self.context(profile="sleep"), self.context("cool")
        for context in (heat, sleep, cool):
            self.seed(record, context)
        cool_model = deepcopy(record[store.ACTIVE])
        self.assertTrue(store.invalidate(record, "heat"))
        self.assertEqual(set(record[store.BANK]), {cool})
        self.assertEqual(record[store.ACTIVE], cool_model)
        self.assertEqual(record["kp"], 10.)
        self.assertEqual(record["pid_passive_review"], {"state": "pending"})
        self.assertFalse(store.invalidate(record, "heat"))
        self.assertTrue(store.invalidate(record, "cool"))
        self.assertNotIn(store.ACTIVE, record)
        self.assertNotIn(store.BANK, record)

    def test_invalidate_all_clears_only_completed_learning_fields(self):
        record = {"other": {"value": 7}}
        self.seed(record, self.context())
        self.assertTrue(store.invalidate(record))
        self.assertEqual(record, {"other": {"value": 7}})
        self.assertFalse(store.invalidate(record))

    def test_malformed_persistence_is_bounded_and_invalid_clock_does_not_mutate(self):
        for bad in (None, [], "bad", 1, True):
            record = {store.ACTIVE: bad, store.BANK: bad, "unrelated": 3}
            store.prune(record, self.NOW)
            self.assertEqual(record, {"unrelated": 3})
        record = {}
        self.seed(record, self.context())
        before = deepcopy(record)
        for now in (None, -1, float("nan"), float("inf"), True, 10 ** 1000):
            self.assertFalse(store.prune(record, now))
            self.assertFalse(store.activate(record, self.context(), now, "temperature", 300))
            self.assertEqual(record, before)


class ObserverExpiryTests(unittest.TestCase):
    NOW = ContextStoreTests.NOW
    context = ContextStoreTests.context
    rows = ContextStoreTests.rows

    def test_constructor_with_clock_expires_history_but_no_clock_keeps_legacy_semantics(self):
        saved = {"context": self.context(), "cycles": self.rows()}
        legacy = passive.PassiveObserver(saved)
        self.assertEqual(len(legacy.cycles), 5)
        expired = passive.PassiveObserver(saved, now=self.NOW + passive.MAX_AGE_S)
        self.assertEqual(expired.cycles, [])
        self.assertTrue(expired.progress()["fresh_cycle_required"])

    def test_observation_prunes_old_evidence_even_without_a_new_completed_cycle(self):
        saved = {"context": self.context(), "cycles": self.rows()}
        observer = passive.PassiveObserver(saved)
        now = self.NOW + passive.MAX_AGE_S - 2 * 3600
        complete = observer.observe(context=self.context(), at=now, value=20.,
                                    on=False, owned=False, metric="temperature",
                                    direction=1, sample_seconds=300, safe=True)
        self.assertFalse(complete)
        self.assertEqual(len(observer.cycles), 2)
        self.assertEqual(observer.summary(metric="temperature", sample_seconds=300)
                         ["confidence"], "insufficient")

    def test_real_completed_cycle_clears_fresh_requirement_and_interrupt_restores_it(self):
        observer = passive.PassiveObserver(now=self.NOW)
        options = {"context": self.context(), "metric": "temperature", "direction": 1,
                   "sample_seconds": 300, "safe": True}
        for index in range(6):
            observer.observe(at=self.NOW + index * 300, value=20., on=False,
                             owned=False, **options)
        start = self.NOW + 1800
        for index in range(42):
            value = 20. + 4. * (1. - math.exp(-max(0., index * 5. - 10.) / 28.))
            observer.observe(at=start + index * 300, value=value, on=True,
                             owned=True, **options)
        self.assertTrue(observer.progress()["fresh_cycle_required"])
        self.assertTrue(observer.observe(at=start + 42 * 300, value=24., on=False,
                                         owned=False, **options))
        self.assertFalse(observer.progress()["fresh_cycle_required"])
        observer.interrupt()
        self.assertTrue(observer.progress()["fresh_cycle_required"])
        self.assertEqual(len(observer.cycles), 1)
        self.assertEqual(observer.off, [])
        self.assertEqual(observer.on, [])


if __name__ == "__main__":
    unittest.main()

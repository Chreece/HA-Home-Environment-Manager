"""Retired timing settings and command journals migrate without actuator guesses."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import MappingProxyType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
f = runpy.run_path(str(ROOT / ".github/tests/test_beta109_setpoint_sequence.py"))
Runtime, SPEC, PRIMARY, model, sequence, production = (
    f[key] for key in ("SequenceRuntime", "SPEC", "PRIMARY", "model", "sequence", "production"))
seed = f["seed_legacy_stop"]


class RemovedTimingTests(unittest.IsolatedAsyncioTestCase):
    def assert_off(self, r):
        self.assertEqual(len(r.calls), 1, r.statuses)
        self.assertEqual(r.calls[0]["data"], {"hvac_mode": "off"})
        self.assertEqual(r.record["pending"]["expected"], {"state": "off"})
        self.assertTrue(r.record["pending"]["power"])
        self.assertIn(PRIMARY, r.record["power"], "Dispatch never acknowledges native OFF")

    async def test_old_reverse_dispatch_or_interrupted_intent_finishes_without_delay(self):
        for phase in ("commanded", "intent", "retry_intent"):
            for mode in ("heat", "cool"):
                with self.subTest(phase=phase, mode=mode):
                    r = Runtime("pid", mode)
                    old = seed(r, phase=phase)
                    r.record["paused"] = "restart_reconciliation_required"
                    r.record["automatic_continue_requested"] = {"method": "pid", "at": r.now}
                    await r.evaluate()
                    self.assert_off(r)
                    self.assertEqual(r.call_times[0], old["last_attempt_at"])
                    self.assertEqual(r.record["native_setpoint_stop"]["target_journal"], old)
                    self.assertFalse(r.record["native_setpoint_stop"]["target_confirmed"])
                    r.report(mode="off")
                    await r.evaluate()
                    self.assertNotIn(PRIMARY, r.record["power"])
                    self.assertIsNone(r.record["pending"])
                    self.assertNotIn("native_setpoint_stop", r.record)
                    self.assertEqual(r.record["last_native_setpoint_stop"]["target_journal"], old)
                    self.assertEqual(r.record["off_at"][PRIMARY], r.now)

    async def test_legacy_target_ack_does_not_acknowledge_power(self):
        r = Runtime()
        old = seed(r)
        r.report(temperature=r.original_target)
        await r.evaluate()
        self.assert_off(r)
        self.assertTrue(r.record["native_setpoint_stop"]["target_confirmed"])
        self.assertEqual(r.record["native_setpoint_stop"]["target_journal"], old)
        self.assertNotEqual(r.state.state, "off")

    async def test_committed_stop_survives_changed_demand_and_disabled_old_setting(self):
        r = Runtime("automatic")
        seed(r)
        r.manager.settings.pop("timed_setpoint_sequence", None)
        r.close_window()
        r.measurement = 10.0
        await r.evaluate()
        self.assert_off(r)

    async def test_old_off_keeps_attempts_phase_and_original_retry_deadline(self):
        r = Runtime("automatic")
        old = seed(r, off_pending=True)
        r.record["paused"] = "restart_reconciliation_required"
        await r.evaluate(59.999)
        self.assertFalse(r.calls)
        self.assertEqual(r.record["pending"], old)
        await r.evaluate(.001)
        self.assert_off(r)
        self.assertEqual(r.record["pending"]["attempts"], 3)
        self.assertEqual(r.record["pending"]["when"], old["when"])
        self.assertEqual(r.service_journals[-1]["pending"]["phase"], "retry_intent")
        self.assertEqual(r.service_journals[-1]["pending"]["attempts"], 3)

    async def test_interrupted_off_remains_uncertain_instead_of_getting_new_budget(self):
        r = Runtime()
        old = seed(r, off_pending=True, phase="intent")
        await r.evaluate(100)
        await r.evaluate(100)
        self.assertFalse(r.calls)
        self.assertEqual(r.record["pending"], old)
        self.assertEqual(r.record["paused"], "native_retry_intent_uncertain")
        self.assertIn(PRIMARY, r.record["power"])
        r.report(mode="off")
        await r.evaluate()
        self.assertIsNone(r.record["pending"])
        self.assertNotIn(PRIMARY, r.record["power"])

    async def test_physical_minimum_on_still_blocks_legacy_completion(self):
        r = Runtime()
        old = seed(r, age=599.999)
        await r.evaluate()
        self.assertFalse(r.calls)
        self.assertEqual(r.statuses[-1][0], "minimum_on_hold")
        self.assertEqual(r.record["native_setpoint_stop"]["target_journal"], old)
        await r.evaluate(.001)
        self.assert_off(r)

    async def test_previously_unowned_stop_keeps_observed_native_minimum_on(self):
        r = Runtime("automatic")
        seed(r, age=599.999)
        r.record["native_setpoint_stop"].update(owned=False, owned_since=None)
        r.record["power"].clear()
        await r.evaluate()
        self.assertFalse(r.calls)
        self.assertEqual(r.statuses[-1][0], "minimum_on_hold")
        await r.evaluate(.001)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertFalse(r.record["power"], "Migration never adopts an unowned output")

    async def test_native_off_confirmation_preserves_new_minimum_off(self):
        r = Runtime("automatic")
        seed(r)
        await r.evaluate()
        r.report(mode="off")
        await r.evaluate()
        off_at = r.record["off_at"][PRIMARY]
        await r.evaluate(599.999)
        self.assertEqual(len(r.calls), 1)
        await r.evaluate(.001)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "heat"})
        self.assertEqual(r.call_times[-1] - off_at, 600)

    async def test_source_change_defrost_and_verified_manual_override_still_block(self):
        for change in ("source", "defrost", "manual"):
            with self.subTest(change=change):
                r = Runtime()
                seed(r)
                if change == "source":
                    r.registered_device_id = "replacement"
                elif change == "defrost":
                    r.state.attributes["hvac_action"] = "defrosting"
                else:
                    r.enable_config_writes()
                    r.state.attributes["fan_mode"] = "low"
                    r.record["baseline"][PRIMARY] = production.snapshot(r.state)
                    r.now += 1
                    r.state.attributes["fan_mode"] = "high"
                    r.state.last_updated = datetime.fromtimestamp(r.now, timezone.utc)
                    r.state.context = N(user_id="human", parent_id=None, id="new-action")
                await r.evaluate()
                self.assertFalse(r.calls)
                self.assertIn(PRIMARY, r.record["power"])
                if change == "manual":
                    self.assertEqual(r.record["paused"], "physical_manual_override")

    async def test_new_native_on_episode_cannot_inherit_committed_stop_authority(self):
        r = Runtime()
        seed(r)
        r._native_on_epoch[PRIMARY] = r.now
        await r.evaluate()
        self.assertFalse(r.calls)
        saved = deepcopy(r.record)
        r = Runtime()
        r.record = saved
        r.records = {SPEC.identifier: saved}
        r.report(mode="heat", temperature=r.requested_target)
        await r.evaluate(1000)
        self.assertFalse(r.calls)
        self.assertIn("invalidated_on_epoch", r.record["native_setpoint_stop"])

    async def test_abort_before_any_reverse_dispatch_does_not_commit_a_stop(self):
        r = Runtime("automatic")
        seed(r)
        old = r.record["native_setpoint_stop"]
        old["phase"] = "preparing"
        old.pop("sent_at")
        old.pop("off_not_before")
        r.record["pending"] = None
        await r.evaluate()
        self.assertFalse(r.calls)
        self.assertNotIn("native_setpoint_stop", r.record)
        self.assertTrue(r.record["last_native_setpoint_stop"]["retired_without_dispatch"])

    async def test_orphan_reverse_target_is_archived_without_replay_or_power_credit(self):
        r = Runtime("automatic")
        old = seed(r)
        r.record.pop("native_setpoint_stop")
        r.record["power"].clear()
        await r.evaluate()
        self.assertFalse(r.calls)
        self.assertEqual(r.record["retired_native_setpoint_target"], old)
        self.assertFalse(r.record["power"])
        self.assertIsNone(r.record["pending"])

    def test_saved_old_flags_are_removed_from_data_options_and_inactive_modes(self):
        model.SETTINGS = "equipment_controllers"
        raw = {model.SETTINGS: {"a": {"timed_setpoint_sequence": True,
                   "native_full_output": False, "mode_settings": {
                       "heat": {"timed_setpoint_sequence": True, "kp": 7},
                       "cool": {"control_mode": "manual"}}},
                   "b": {"timed_setpoint_sequence": "true", "other": 9}},
               "unrelated": {"timed_setpoint_sequence": "keep"}}
        def frozen(value):
            return MappingProxyType({key: frozen(item) for key, item in value.items()}) if (
                isinstance(value, dict)) else value
        entry = N(data=frozen(deepcopy(raw)), options=frozen(deepcopy(raw)))
        originals = (entry.data, entry.options)
        calls = []
        def update(item, **changes):
            calls.append(deepcopy(changes))
            for key, value in changes.items():
                setattr(item, key, value)
        manager = N(entry=entry, hass=N(config_entries=N(async_update_entry=update)))
        self.assertTrue(sequence.remove_legacy_settings(manager))
        expected = deepcopy(raw)
        for profile in expected[model.SETTINGS].values():
            profile.pop("timed_setpoint_sequence", None)
            for mode in profile.get("mode_settings", {}).values():
                mode.pop("timed_setpoint_sequence", None)
        self.assertEqual(entry.data, expected)
        self.assertEqual(entry.options, expected)
        self.assertTrue(originals[0][model.SETTINGS]["a"]["timed_setpoint_sequence"])
        self.assertTrue(originals[1][model.SETTINGS]["a"]["mode_settings"]["heat"]["timed_setpoint_sequence"])
        self.assertFalse(sequence.remove_legacy_settings(manager))
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

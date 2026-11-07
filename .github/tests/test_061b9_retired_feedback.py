"""Late legacy target feedback cannot revive timing or acknowledge native power.

Exercise the production migration, command, feedback and manual-override paths
after the retired reverse-target sequence has already archived a real OFF.
Only native transport, clock and persisted historical input are fixture data.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta109_setpoint_sequence.py"))
Runtime, SPEC, PRIMARY, seed = (
    fixture[name] for name in ("SequenceRuntime", "SPEC", "PRIMARY", "seed_legacy_stop")
)


class RetiredFeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def archived(self, method="pid", mode="heat", *, phase="commanded", with_fan=False):
        runtime = Runtime(method, mode)
        if with_fan:
            runtime.state.attributes.update(fan_mode="low", fan_modes=["low", "medium", "high"])
            runtime.state.attributes["supported_features"] |= 8
        old_target = seed(runtime, phase=phase)
        # A real previously controlled appliance has a confirmed control
        # context. Keep it so a manual-diff test cannot pass just because
        # the fixture omitted the evidence needed to detect human changes.
        runtime.record["native_control_confirmed"] = {
            PRIMARY: {"at": runtime.now - 120, "context_id": "last-controller-feedback"},
        }
        runtime.state.context = N(user_id=None, parent_id=None, id="last-controller-feedback")
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.calls[0]["data"], {"hvac_mode": "off"})
        self.assertIn(PRIMARY, runtime.record["power"])
        runtime.now += 1
        runtime.report(mode="off")
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        await runtime.evaluate()
        self.assertNotIn("native_setpoint_stop", runtime.record)
        self.assertEqual(runtime.record["last_native_setpoint_stop"]["target_journal"], old_target)
        self.assertTrue(runtime.record["last_native_setpoint_stop"]["native_off_confirmed"])
        self.assertIsNone(runtime.record["pending"])
        self.assertNotIn(PRIMARY, runtime.record["power"])
        return runtime, old_target

    def report_late_target(self, runtime, old_target, *, context=None, origin=None):
        runtime.now += 1
        runtime.report(temperature=old_target["data"]["temperature"])
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        runtime.state.context = context or N(user_id=None, parent_id=None, id="late-device-report")
        if origin is not None:
            runtime.state.attributes["operation_source"] = origin

    async def test_late_reverse_ack_after_off_archive_is_an_observation_without_timer_or_power(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                for phase in ("commanded", "retry_intent"):
                    with self.subTest(method=method, mode=mode, phase=phase):
                        runtime, old_target = await self.archived(method, mode, phase=phase)
                        archived = deepcopy(runtime.record["last_native_setpoint_stop"])
                        off_at = runtime.record["off_at"][PRIMARY]
                        handles = tuple(runtime.timer_loop.handles)
                        self.report_late_target(runtime, old_target)
                        await runtime.evaluate()
                        self.assertFalse(runtime.record.get("paused"))
                        self.assertEqual(runtime.manager.settings["control_mode"], method)
                        self.assertEqual(len(runtime.calls), 1)
                        self.assertIsNone(runtime.record["pending"])
                        self.assertNotIn("native_setpoint_stop", runtime.record)
                        self.assertNotIn(PRIMARY, runtime.record["power"])
                        self.assertEqual(runtime.record["off_at"][PRIMARY], off_at)
                        self.assertEqual(runtime.record["last_native_setpoint_stop"], archived)
                        self.assertEqual(runtime.record["baseline"][PRIMARY]["attributes"]["temperature"],
                                         old_target["data"]["temperature"])
                        self.assertEqual(tuple(runtime.timer_loop.handles), handles,
                                         "A retired target reply must not create a new timer")

    async def test_reused_old_user_context_is_not_a_new_manual_action(self):
        runtime, old_target = await self.archived()
        self.report_late_target(runtime, old_target, context=N(
            user_id="previous-user", parent_id=None, id="last-controller-feedback",
        ))
        await runtime.evaluate()
        self.assertFalse(runtime.record.get("paused"))
        self.assertEqual(runtime.manager.settings["control_mode"], "pid")
        self.assertEqual(len(runtime.calls), 1)
        self.assertIsNone(runtime.record["pending"])
        self.assertNotIn("native_setpoint_stop", runtime.record)

    async def test_genuine_user_edit_remains_manual_even_when_it_matches_the_archived_target(self):
        for source in ("ha_user", "physical_button", "simultaneous_fan_edit"):
            with self.subTest(source=source):
                runtime, old_target = await self.archived(with_fan=source == "simultaneous_fan_edit")
                runtime.enable_config_writes()
                off_at = runtime.record["off_at"][PRIMARY]
                if source == "physical_button":
                    self.report_late_target(runtime, old_target, origin="physical_button")
                else:
                    self.report_late_target(runtime, old_target, context=N(
                        user_id="new-user", parent_id=None, id="new-user-action",
                    ))
                    if source == "simultaneous_fan_edit":
                        runtime.state.attributes["fan_mode"] = "high"
                await runtime.evaluate()
                self.assertEqual(runtime.record["paused"], "physical_manual_override")
                self.assertEqual(runtime.manager.settings["control_mode"], "manual")
                changed = runtime.record["manual_override_evidence"]["changed_controls"]
                self.assertIn("temperature", changed)
                if source == "simultaneous_fan_edit":
                    self.assertIn("fan_mode", changed)
                self.assertEqual(len(runtime.calls), 1)
                self.assertNotIn(PRIMARY, runtime.record["power"])
                self.assertEqual(runtime.record["off_at"][PRIMARY], off_at)
                self.assertNotIn("native_setpoint_stop", runtime.record)

    async def test_interrupted_off_retains_exact_history_across_restart_until_real_off(self):
        for phase in ("intent", "retry_intent"):
            with self.subTest(phase=phase):
                runtime = Runtime()
                seed(runtime, phase=phase, off_pending=True)
                runtime.record["pending"].update(
                    attempts=7, when=runtime.now - 300, last_attempt_at=runtime.now - 120,
                )
                old_off = deepcopy(runtime.record["pending"])
                await runtime.evaluate(100)
                self.assertFalse(runtime.calls)
                self.assertEqual(runtime.record["pending"], old_off)
                self.assertEqual(runtime.record["paused"], "native_retry_intent_uncertain")
                saved = deepcopy(runtime.record)
                restarted = Runtime()
                restarted.record = saved
                restarted.records = {SPEC.identifier: saved}
                restarted.state = deepcopy(runtime.state)
                restarted.now = runtime.now + 1000
                await restarted.evaluate()
                self.assertFalse(restarted.calls)
                self.assertEqual(restarted.record["pending"], old_off)
                self.assertEqual(restarted.record["paused"], "native_retry_intent_uncertain")
                self.assertIn(PRIMARY, restarted.record["power"])
                restarted.report(mode="off")
                await restarted.evaluate()
                self.assertFalse(restarted.calls)
                self.assertIsNone(restarted.record["pending"])
                self.assertNotIn(PRIMARY, restarted.record["power"])
                self.assertEqual(restarted.record["off_at"][PRIMARY], restarted.now)
                self.assertEqual(restarted.record["last_native_setpoint_stop"]["off_journal"], old_off)
                self.assertTrue(restarted.record["last_native_setpoint_stop"]["native_off_confirmed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

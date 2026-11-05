"""Interrupted native retries use real state verification and the original budget.

Run production dispatch/retry, startup, Resume, and ordinary tick paths using
the established native Home Assistant transport fixture. No physical service
is sent. The optional HEM_TEST_RUNTIME_SOURCE / HEM_TEST_RESUME_SOURCE inputs
allow these regressions to be checked against the preceding release.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import logging
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_beta108_retry_recovery.py"))
RecoveryRuntime, SPEC, PRIMARY, production = (
    fixture[name] for name in ("RecoveryRuntime", "SPEC", "PRIMARY", "production")
)
base = fixture["fixture"]
resume = sys.modules[f"{base['PACKAGE']}.equipment_resume"]
production.model.SETTINGS = "native_controller_profiles"
production._LOGGER = logging.getLogger(__name__)
base["extract"](base["RUNTIME"], ("async_start", "_startup_readiness"),
                production.__dict__, constants=(
                    "HA_READY_COOLDOWN_SECONDS", "NATIVE_STARTUP_STABLE_SECONDS",
                ))

storage = ModuleType("homeassistant.helpers.storage")


class Store:
    def __init__(self, hass, *args):
        self.hass = hass

    async def async_load(self):
        return deepcopy(self.hass.fixture.restart_store)


storage.Store = Store
sys.modules[storage.__name__] = storage


class RestartRuntime(RecoveryRuntime):
    _startup_readiness = production._startup_readiness

    def __init__(self, method="pid", mode="heat"):
        super().__init__(method, mode)
        self.manager.settings[production.model.SETTINGS] = {
            SPEC.identifier: {"control_mode": method},
        }
        self.manager.entry.options = deepcopy(self.manager.settings)
        self.manager.settings["kp"] = 100.0
        self.hass.state = N(value="running")
        self._ha_running_since = self.now - 600
        self._startup_source_observed = {}
        self._startup_source_since = {}
        self._startup_source_done = {(SPEC.identifier, PRIMARY)}

    async def _save(self):
        # The real startup method replaces records after loading Store.
        self.record = self.records[SPEC.identifier]
        await super()._save()

    async def restart(self):
        self.restart_store = {"version": 1, "records": deepcopy(self.records)}
        await production.async_start(self)
        self.assert_started = self._ready


class InterruptedRetryTests(unittest.IsolatedAsyncioTestCase):
    async def interrupted(self, attempt=2, method="pid", *, power_command=False):
        runtime = RestartRuntime(method)
        if not power_command:
            runtime.own_running()
        await runtime.evaluate()
        for _ in range(2, attempt):
            await runtime.evaluate(30)

        original_call = runtime.service_call

        async def timeout_after_dispatch(*args, **kwargs):
            await original_call(*args, **kwargs)
            raise TimeoutError("Native retry completion is unknown")

        runtime.hass.services.async_call = timeout_after_dispatch
        await runtime.evaluate(30)
        pending = runtime.record["pending"]
        self.assertEqual(pending["phase"], "retry_intent")
        self.assertEqual(pending["attempts"], attempt)
        self.assertEqual(len(runtime.calls), attempt)
        self.assertEqual(runtime.record["paused"], "native_command_failed_or_uncertain")
        return runtime, pending

    async def settle_restart(self, runtime):
        before = len(runtime.calls)
        await runtime.restart()
        self.assertTrue(runtime.assert_started)
        self.assertIn("automatic_continue_requested", runtime.record)
        await runtime.evaluate()
        await runtime.evaluate(60)
        await runtime.evaluate(60)
        await runtime.evaluate(30)
        self.assertIn("pending_resume_probe", runtime.record)
        self.assertEqual(len(runtime.calls), before)
        await runtime.evaluate(59)
        self.assertIsNotNone(runtime.record["pending"])
        await runtime.evaluate(1)
        self.assertIsNone(runtime.record["pending"])
        self.assertIsNone(runtime.record["paused"])
        self.assertEqual(len(runtime.calls), before, "State verification sends no service")

    async def test_partial_retry_survives_restart_and_uses_only_remaining_attempts(self):
        for method in ("pid", "automatic"):
            with self.subTest(method=method):
                runtime, pending = await self.interrupted(method=method)
                first, last = pending["when"], pending["last_attempt_at"]
                await self.settle_restart(runtime)
                budget = runtime.record["unconfirmed_native_target"]
                self.assertEqual((budget["attempts"], budget["when"], budget["last_attempt_at"]),
                                 (2, first, last))
                self.assertGreaterEqual(budget["retry_state_verified_at"], last)
                runtime.hass.services.async_call = runtime.service_call
                await runtime.evaluate()
                self.assertEqual(len(runtime.calls), 2, "Original startup warmup still applies")
                await runtime.evaluate(90)
                self.assertEqual(len(runtime.calls), 3)
                self.assertEqual(runtime.record["pending"]["attempts"], 3)
                self.assertEqual(runtime.record["pending"]["when"], first)
                self.assertNotIn("retry_state_verified_at", runtime.record["pending"])
                await runtime.evaluate(30)
                self.assertEqual(len(runtime.calls), 4)
                await runtime.evaluate(30)
                await runtime.evaluate()
                await runtime.evaluate(60)
                for delta in (0, 30, 120, 300):
                    await runtime.evaluate(delta)
                self.assertEqual(len(runtime.calls), 4, "Verified state cannot start a new budget")
                self.assertEqual(runtime.record["unconfirmed_native_target"]["attempts"], 4)

    async def test_exhausted_interrupted_retry_keeps_count_and_reconnect_credit(self):
        runtime, pending = await self.interrupted(attempt=4)
        first = pending["when"]
        await self.settle_restart(runtime)
        for delta in (0, 30, 120):
            await runtime.evaluate(delta)
        self.assertEqual(len(runtime.calls), 4)
        self.assertEqual(runtime.record["unconfirmed_native_target"]["attempts"], 4)
        runtime.hass.services.async_call = runtime.service_call
        runtime.availability_event("unavailable")
        await runtime.evaluate()
        runtime.now += 1
        runtime.availability_event("heat")
        await runtime.evaluate()
        await runtime.evaluate(60)
        self.assertEqual(len(runtime.calls), 5)
        self.assertEqual(runtime.record["pending"]["attempts"], 5)
        self.assertEqual(runtime.record["pending"]["when"], first)
        self.assertEqual(runtime.record["pending"]["reconnect_retry_uses"], 1)
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 5)

    async def test_latest_retry_time_requires_settling_and_fresh_matching_feedback(self):
        runtime, pending = await self.interrupted()
        # An old original dispatch does not age a newly interrupted retry.
        pending["when"] = runtime.now - 1000
        runtime.report(temperature=runtime.requested_target)
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now - 1, timezone.utc)
        expected = deepcopy(pending)
        checked = runtime.resume_information(SPEC)
        self.assertEqual(checked["decision"], "settling")
        runtime.now += 120
        checked = runtime.resume_information(SPEC)
        self.assertEqual(checked["decision"], "first_check", "Old feedback is not retry ACK")
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        self.assertEqual(runtime.resume_information(SPEC)["decision"], "confirmed")
        self.assertTrue(await runtime.async_continue_automatic(SPEC))
        self.assertIsNone(runtime.record["pending"])
        self.assertEqual(runtime.record["last_resume_reconciliation"]["method"], "fresh_native_ack")
        self.assertEqual(len(runtime.calls), 2)
        self.assertEqual(expected["attempts"], 2)

    async def test_repeated_retry_timeouts_do_not_reset_counts_or_reuse_verified_marker(self):
        runtime, pending = await self.interrupted()
        first = pending["when"]
        for expected_attempt in (3, 4):
            await self.settle_restart(runtime)
            await runtime.evaluate(90)
            self.assertEqual(len(runtime.calls), expected_attempt)
            self.assertEqual(runtime.record["pending"]["attempts"], expected_attempt)
            self.assertEqual(runtime.record["pending"]["when"], first)
            self.assertNotIn("retry_state_verified_at", runtime.record["pending"])
        await self.settle_restart(runtime)
        for delta in (0, 60, 300):
            await runtime.evaluate(delta)
        active_targets = [call for call in runtime.calls
                          if call["data"] == {"temperature": runtime.requested_target}]
        self.assertEqual(len(active_targets), 4)
        self.assertTrue(any(call["data"] == {"hvac_mode": "off"} for call in runtime.calls),
                        "An unresolved target must still permit protective shutdown")

    async def test_commanded_retry_mismatch_settles_but_matching_ack_is_immediate(self):
        runtime, pending = await self.interrupted()
        pending["phase"] = "commanded"
        pending["when"] = runtime.now - 1000
        checked = runtime.resume_information(SPEC)
        self.assertEqual(checked["decision"], "settling")
        self.assertEqual(checked["remaining_seconds"], 120)
        runtime.report(temperature=runtime.requested_target)
        self.assertEqual(runtime.resume_information(SPEC)["decision"], "confirmed")

    async def test_recovered_partial_retry_rechecks_current_settings_and_user_mode(self):
        for change in ("settings", "manual", "permission"):
            with self.subTest(change=change):
                runtime, _ = await self.interrupted()
                await self.settle_restart(runtime)
                if change == "settings":
                    runtime.manager.settings["kp"] -= 1
                elif change == "manual":
                    runtime.manager.settings["control_mode"] = "manual"
                else:
                    runtime.manager.soft_grant = False
                    runtime.manager.power_grant = False
                await runtime.evaluate(90)
                self.assertEqual(len(runtime.calls), 2)

    async def test_probe_is_bound_to_latest_attempt_and_invalid_retry_time_stays_held(self):
        runtime, pending = await self.interrupted()
        runtime.now += 200
        initial = resume.check_pending(pending, runtime.state, runtime.now, None,
                                       matches_expected=False)
        self.assertEqual(initial["decision"], "first_check")
        probe = {"command": initial["command"], "observed": initial["observation"],
                 "at": runtime.now - 60}
        for field, value in (("attempts", 3), ("last_attempt_at", pending["last_attempt_at"] + 1)):
            changed = {**pending, field: value}
            checked = resume.check_pending(changed, runtime.state, runtime.now, probe,
                                           matches_expected=False)
            self.assertEqual(checked["decision"], "first_check", field)
        for bad in (None, float("nan"), runtime.now + 1, pending["when"] - 1):
            checked = resume.check_pending({**pending, "last_attempt_at": bad},
                                           runtime.state, runtime.now, probe,
                                           matches_expected=False)
            self.assertIn(checked["decision"], ("unknown_dispatch_time", "invalid"))

    async def test_verified_marker_cannot_bypass_timestamp_validation(self):
        runtime, pending = await self.interrupted()
        runtime.now += 200
        for marker in (None, True, float("nan"), pending["last_attempt_at"] - 1,
                       runtime.now + 1):
            checked = production.native_retry_decision(
                {**pending, "retry_state_verified_at": marker}, runtime.now, runtime.state,
            )
            self.assertEqual(checked, "uncertain")

    async def test_interrupted_power_retry_matching_ack_preserves_conservative_dwell(self):
        runtime, pending = await self.interrupted(power_command=True)
        self.assertTrue(pending["power"])
        self.assertEqual(runtime.state.state, "off")
        self.assertFalse(runtime.record["power"])
        runtime.now += 120
        runtime.report(mode="heat")
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        await runtime.async_resume(SPEC)
        self.assertIsNone(runtime.record["pending"])
        self.assertEqual(runtime.record["power"][PRIMARY]["since"], runtime.now)
        self.assertEqual(len(runtime.calls), 2)

    async def test_state_change_during_retry_ack_save_restores_original_journal(self):
        runtime, pending = await self.interrupted(power_command=True)
        original = deepcopy(pending)
        runtime.now += 120
        runtime.report(mode="heat")
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        save = runtime._save
        changed = False

        async def changed_during_save():
            nonlocal changed
            await save()
            if runtime.record.get("pending") is None and not changed:
                changed = True
                runtime.report(mode="off")

        runtime._save = changed_during_save
        with self.assertRaises(fixture["HomeAssistantError"]):
            await runtime.async_resume(SPEC)
        self.assertTrue(changed)
        self.assertEqual(runtime.record["pending"], original)
        self.assertEqual(runtime.record["paused"], "physical_state_changed_during_resume")
        self.assertEqual(len(runtime.calls), 2)

    async def test_manual_override_is_not_automatically_rearmed_after_restart(self):
        runtime, _ = await self.interrupted()
        runtime.record["paused"] = "physical_manual_override"
        runtime.manager.settings["control_mode"] = "manual"
        runtime.manager.settings[production.model.SETTINGS][SPEC.identifier]["control_mode"] = "manual"
        await runtime.restart()
        self.assertNotIn("automatic_continue_requested", runtime.record)
        for delta in (0, 60, 60, 30, 120):
            await runtime.evaluate(delta)
        self.assertEqual(runtime.record["paused"], "physical_manual_override")
        self.assertEqual(runtime.record["pending"]["attempts"], 2)
        self.assertEqual(len(runtime.calls), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

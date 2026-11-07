"""Retry automatic targets while preserving old journals and guarded shutdown.

The Beta106 fixture supplies native HA state/service/registry transport and
policy inputs. This suite additionally runs the production automatic recovery
and explicit Resume methods, real availability-event/reconnect tracking,
settling and retry gates. No ACK, recovery decision or service dispatch is
stubbed. The event-loop scheduler is the only added boundary: tests advance the
clock and drain actual recovery tasks deterministically.

HEM_TEST_RUNTIME_SOURCE and HEM_TEST_RESUME_SOURCE can select older production
sources for a before/after regression check. The independent Beta99 startup
suite covers interrupted-intent recovery through the actual startup lifecycle.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_onoff_native_extrema.py"))
NativeRuntime, SPEC, PRIMARY, production = (
    fixture[name] for name in ("NativeRuntime", "SPEC", "PRIMARY", "production")
)
fixture["load_pure"](
    "equipment_resume",
    Path(os.environ.get("HEM_TEST_RESUME_SOURCE", ROOT / "equipment_resume.py")),
)


class HomeAssistantError(Exception):
    """HA's user-facing exception type; no installed HA instance is needed."""


production.HomeAssistantError = HomeAssistantError
RECOVERY_METHODS = (
    "_lock", "_pause", "resume_information", "_automatic_recovery_gate",
    "_schedule_automatic_reconciliation", "_apply_automatic_reconciliation",
    "async_resume", "observe_native_availability", "_native_settle_remaining",
    "_retry_after_verified_reconnect", "_observed_off_since", "async_continue_automatic",
)
fixture["extract"](fixture["RUNTIME"], RECOVERY_METHODS, production.__dict__)


def no_supply(*args):
    raise AssertionError("This fixture has no external supply to authorize")


# async_resume imports this helper even when no supply is selected. Any actual
# invocation would be a fixture error, rather than a mocked authorization.
fixture["supply"].permitted_supply = no_supply


class RecoveryRuntime(NativeRuntime):
    def __init__(self, method="pid", mode="heat"):
        super().__init__(method, mode, low=5.0, high=30.0)
        self._locks = {}
        self._native_ready_since = {
            PRIMARY: self.now - production.NATIVE_RECONNECT_SETTLE_SECONDS,
        }
        self._native_settled_for = {
            (SPEC.identifier, PRIMARY): self._native_ready_since[PRIMARY],
        }
        self._native_reconnect_epoch = {}
        self.queued_tasks = []
        self.created_recovery_tasks = 0
        self.scheduled_evaluations = 0
        self.hass.config = N(language="en", units=N(temperature_unit="°C"))
        self.hass.async_create_task = self.create_task
        self.state.attributes["current_temperature"] = self.measurement
        self.requested_target = 30.0 if mode == "heat" else 5.0
        self.original_target = self.state.attributes["temperature"]

    def create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.queued_tasks.append(task)
        self.created_recovery_tasks += 1
        return task

    def schedule(self):
        # Evaluations are explicit below; this never executes controller logic.
        self.scheduled_evaluations += 1

    async def evaluate(self, advance=0.0):
        self.now += advance
        await self.tick(SPEC)
        while self.queued_tasks:
            tasks, self.queued_tasks = self.queued_tasks, []
            await asyncio.gather(*tasks)

    def availability_event(self, mode):
        old = deepcopy(self.state)
        self.report(mode=mode)
        self.state.last_updated = datetime.fromtimestamp(self.now, timezone.utc)
        self.observe_native_availability(PRIMARY, old, self.state)


for method in RECOVERY_METHODS:
    setattr(RecoveryRuntime, method, getattr(production, method))


class AutomaticTargetRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def dispatched(self, method="pid", mode="heat"):
        runtime = RecoveryRuntime(method, mode)
        runtime.manager.settings["kp"] = 100.0
        runtime.own_running()
        await runtime.evaluate()
        pending = runtime.record["pending"]
        self.assertEqual(runtime.calls, [{
            "domain": "climate", "service": "set_temperature",
            "data": {"temperature": runtime.requested_target},
            "target": {"entity_id": PRIMARY},
        }])
        self.assertEqual(pending["phase"], "commanded")
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        return runtime, pending

    async def legacy_journal(self, method="pid", mode="heat", *, retired=False):
        """Restore the shape that an earlier release persisted after attempt4.

        The real first dispatch establishes source identity, capabilities,
        expected feedback and settings. Only the historical clock/count and
        pause/retired location are seeded at the persistence boundary; current
        production behavior is never made to exhaust its new minute policy.
        """
        runtime, pending = await self.dispatched(method, mode)
        runtime.now += 120
        pending.update(attempts=4, last_attempt_at=pending["when"] + 90)
        pending.pop("retry_policy", None)
        runtime.calls.clear()
        if retired:
            runtime.record["unconfirmed_native_target"] = deepcopy(pending)
            runtime.record["pending"] = None
            runtime.record["paused"] = None
        else:
            runtime.record["paused"] = "physical_acknowledgement_missing"
        await runtime._save()
        return runtime, deepcopy(pending)

    def rehydrate(self, original):
        runtime = RecoveryRuntime(original.manager.settings["control_mode"],
                                  original.manager.settings["requested_mode"])
        runtime.manager.settings = deepcopy(original.manager.settings)
        runtime.record = deepcopy(original.persisted[-1])
        runtime.records = {SPEC.identifier: runtime.record}
        runtime.state = deepcopy(original.state)
        runtime.now = original.now + 600
        runtime._native_ready_since[PRIMARY] = runtime.now - 30
        runtime._native_settled_for[(SPEC.identifier, PRIMARY)] = runtime.now - 30
        return runtime

    # Ongoing retries beyond three are Automatic policy. Binary PID full-output
    # exhaustion/restart/pulse persistence is covered by test_061b8_native_target_budget.
    async def test_unchanged_feedback_retries_each_minute_without_resetting_history(self):
        for method in ("automatic",):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, pending = await self.dispatched(method, mode)
                    original_call = deepcopy(runtime.calls[0])
                    when = pending["when"]
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    for attempt in range(2, 9):
                        await runtime.evaluate(59.999)
                        self.assertEqual(len(runtime.calls), attempt - 1)
                        await runtime.evaluate(.001)
                        self.assertEqual(len(runtime.calls), attempt)
                        self.assertEqual(pending["attempts"], attempt)
                        self.assertEqual(pending["when"], when)
                        self.assertIs(runtime.record["pending"], pending)
                        self.assertFalse(runtime.record.get("paused"))
                        self.assertEqual(runtime.manager.settings["control_mode"], method)
                    self.assertEqual(runtime.calls, [original_call] * 8)
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertNotIn("unconfirmed_native_target", runtime.record)
                    self.assertNotIn("pending_resume_probe", runtime.record)
                    self.assertEqual(runtime.state.attributes["temperature"], runtime.original_target)
                    self.assertFalse(production.matches(runtime.state, pending["expected"]))

    async def test_legacy_pending_and_retired_targets_migrate_with_original_history(self):
        for method in ("automatic",):
            for retired in (False, True):
                with self.subTest(method=method, retired=retired):
                    runtime, original = await self.legacy_journal(method, retired=retired)
                    await runtime.evaluate()
                    self.assertEqual(runtime.calls, [], "The last historical attempt was only30 seconds ago")
                    pending = runtime.record["pending"]
                    self.assertIsInstance(pending, dict)
                    self.assertEqual(pending["attempts"], 4)
                    self.assertEqual(pending["when"], original["when"])
                    self.assertEqual(pending["retry_policy"], "automatic_minute")
                    self.assertFalse(runtime.record.get("paused"))
                    await runtime.evaluate(29.999)
                    self.assertEqual(runtime.calls, [])
                    await runtime.evaluate(.001)
                    self.assertEqual(len(runtime.calls), 1)
                    self.assertEqual(pending["attempts"], 5)
                    self.assertEqual(pending["when"], original["when"])
                    self.assertNotIn("unconfirmed_native_target", runtime.record)
                    self.assertEqual(runtime.calls[-1]["data"], original["data"])
                    await runtime.evaluate(60)
                    self.assertEqual(pending["attempts"], 6)
                    self.assertEqual(len(runtime.calls), 2)

    async def test_late_target_ack_stops_retries_without_replay_or_dwell_reset(self):
        for method in ("automatic",):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, pending = await self.dispatched(method, mode)
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    measured = runtime.state.attributes["current_temperature"]
                    for _ in range(4):
                        await runtime.evaluate(60)
                    self.assertEqual(pending["attempts"], 5)
                    count = len(runtime.calls)
                    runtime.report(temperature=runtime.requested_target)
                    self.assertTrue(production.matches(runtime.state, pending["expected"]))
                    await runtime.evaluate()
                    self.assertIsNone(runtime.record["pending"])
                    self.assertNotIn("unconfirmed_native_target", runtime.record)
                    self.assertFalse(runtime.record.get("paused"))
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertEqual(runtime.state.attributes["current_temperature"], measured)
                    self.assertNotEqual(measured, runtime.requested_target)
                    await runtime.evaluate(60)
                    self.assertEqual(len(runtime.calls), count)

    async def test_reconnects_keep_minute_spacing_settling_and_original_attempts(self):
        for method in ("automatic",):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, pending = await self.dispatched(method, mode)
                    original_when, original_call = pending["when"], deepcopy(runtime.calls[0])
                    for attempt in range(2, 5):
                        before_calls = len(runtime.calls)
                        runtime.now += 1
                        runtime.availability_event("unavailable")
                        await runtime.evaluate()
                        self.assertEqual(len(runtime.calls), before_calls)
                        runtime.now += 5
                        runtime.availability_event(mode)
                        await runtime.evaluate(29.999)
                        self.assertEqual(len(runtime.calls), before_calls,
                                         "Native reconnect must settle before another attempt")
                        await runtime.evaluate(.001)
                        self.assertEqual(len(runtime.calls), before_calls,
                                         "A reconnect cannot shorten the60-second command interval")
                        await runtime.evaluate(23.999)
                        self.assertEqual(len(runtime.calls), before_calls)
                        await runtime.evaluate(.001)
                        self.assertEqual(len(runtime.calls), attempt)
                        self.assertEqual(pending["attempts"], attempt)
                        self.assertEqual(pending["when"], original_when)
                        self.assertIs(runtime.record["pending"], pending)
                        self.assertEqual(runtime.calls[-1], original_call)
                    await runtime.evaluate(60)
                    self.assertEqual(pending["attempts"], 5, "No two-reconnect cap in Automatic")
                    self.assertFalse(runtime.record.get("paused"))
                    self.assertFalse(production.matches(runtime.state, pending["expected"]))

    async def test_reconnect_revalidates_settings_before_identical_target_dispatch(self):
        runtime, pending = await self.dispatched()
        original = deepcopy(pending)
        runtime.now += 1
        runtime.availability_event("unavailable")
        runtime.now += 5
        runtime.availability_event("heat")
        runtime.manager.settings["kp"] -= 1.0
        await runtime.evaluate(60)
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.record["pending"], original)
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        self.assertEqual(runtime.manager.settings["control_mode"], "pid")

    async def test_explicit_continue_clears_legacy_budget_without_service_until_next_tick(self):
        for method in ("automatic",):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, _ = await self.legacy_journal(method, mode, retired=True)
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    scheduled = runtime.scheduled_evaluations
                    self.assertTrue(await runtime.async_continue_automatic(SPEC))
                    self.assertNotIn("unconfirmed_native_target", runtime.record)
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertEqual(runtime.calls, [], "The actual button verifier sends no service")
                    self.assertGreater(runtime.scheduled_evaluations, scheduled)
                    await runtime.evaluate()
                    self.assertEqual(len(runtime.calls), 1)
                    self.assertEqual(runtime.calls[-1]["data"], {"temperature": runtime.requested_target})
                    self.assertEqual(runtime.record["pending"]["attempts"], 1)

    async def test_explicit_two_checks_keep_physical_reconciliation_without_device_command(self):
        runtime, _ = await self.legacy_journal()
        pending = runtime.record["pending"]
        with self.assertRaises(HomeAssistantError):
            await runtime.async_resume(SPEC)
        self.assertNotIn("pending_resume_probe", runtime.record)
        remaining = runtime.resume_information(SPEC)["remaining_seconds"]
        self.assertEqual(remaining, 90)
        runtime.now += remaining
        with self.assertRaises(HomeAssistantError):
            await runtime.async_resume(SPEC)
        self.assertIn("pending_resume_probe", runtime.record)
        self.assertIs(runtime.record["pending"], pending)
        runtime.now += 60
        await runtime.async_resume(SPEC)
        self.assertIsNone(runtime.record["pending"])
        self.assertNotIn("unconfirmed_native_target", runtime.record)
        self.assertEqual(runtime.record["last_resume_reconciliation"]["method"], "two_physical_checks")
        self.assertEqual(runtime.calls, [])

    async def test_restart_keeps_pending_history_until_target_ack(self):
        for method in ("automatic",):
            with self.subTest(method=method):
                original, pending = await self.dispatched(method)
                await original.evaluate(60)
                await original.evaluate(60)
                expected = deepcopy(pending)
                runtime = self.rehydrate(original)
                await runtime.evaluate()
                self.assertEqual(len(runtime.calls), 1)
                self.assertEqual(runtime.record["pending"]["attempts"], 4)
                self.assertEqual(runtime.record["pending"]["when"], expected["when"])
                self.assertEqual(runtime.calls[0]["data"], expected["data"])
                self.assertFalse(production.matches(runtime.state, expected["expected"]))
                runtime.report(temperature=runtime.requested_target)
                await runtime.evaluate()
                self.assertIsNone(runtime.record["pending"])
                self.assertNotIn("unconfirmed_native_target", runtime.record)
                self.assertEqual(len(runtime.calls), 1)

    async def test_retired_legacy_target_still_allows_guarded_stop_and_requires_physical_off(self):
        runtime, original = await self.legacy_journal(retired=True)
        runtime.measurement = 23.0
        await runtime.evaluate()
        self.assertEqual(runtime.calls, [], "Old failed targets cannot bypass physical minimum ON")
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")
        deadline = runtime.statuses[-1][1]["minimum_on_until"]
        await runtime.evaluate(deadline - runtime.now - .001)
        self.assertEqual(runtime.calls, [])
        await runtime.evaluate(.001)
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(len(runtime.calls), 1)
        self.assertNotIn("native_setpoint_stop", runtime.record)
        self.assertIn("unconfirmed_native_target", runtime.record,
                      "OFF dispatch cannot acknowledge the old target or physical OFF")
        self.assertEqual(runtime.record["unconfirmed_native_target"], original)
        self.assertIn(PRIMARY, runtime.record["power"])
        runtime.report(mode="off")
        await runtime.evaluate()
        self.assertNotIn(PRIMARY, runtime.record["power"])
        self.assertIsNone(runtime.record["pending"])
        self.assertNotIn("unconfirmed_native_target", runtime.record)

    async def test_cancelled_retry_preserves_reserved_attempt_and_needs_restart_verification(self):
        runtime, pending = await self.dispatched()
        service = runtime.service_call

        async def cancelled(*args, **kwargs):
            await service(*args, **kwargs)
            raise asyncio.CancelledError("Interrupted after dispatch; completion is unknown")

        runtime.hass.services.async_call = cancelled
        with self.assertRaises(asyncio.CancelledError):
            await runtime.evaluate(60)
        self.assertEqual(len(runtime.calls), 2)
        self.assertEqual(pending["phase"], "retry_intent")
        self.assertEqual(pending["attempts"], 2)
        self.assertNotIn("retry_state_verified_at", pending)
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        recovered = self.rehydrate(runtime)
        recovered.record["automatic_continue_requested"] = {
            "at": recovered.now, "method": "pid", "origin": "automatic_restart_reconciliation",
        }
        await recovered.evaluate()
        self.assertEqual(recovered.calls, [], "Restart alone cannot replay an interrupted intent")
        outstanding = recovered.record.get("pending") or recovered.record.get("unconfirmed_native_target")
        self.assertEqual(outstanding["attempts"], 2)
        self.assertEqual(outstanding["when"], pending["when"])
        self.assertFalse(production.matches(recovered.state, outstanding["expected"]))

    async def test_service_timeout_is_a_failed_attempt_and_retry_history_survives_restart(self):
        runtime, pending = await self.dispatched()
        service = runtime.service_call

        async def timeout(*args, **kwargs):
            await service(*args, **kwargs)
            raise TimeoutError("Native command completion was not confirmed")

        runtime.hass.services.async_call = timeout
        await runtime.evaluate(60)
        self.assertEqual(len(runtime.calls), 2)
        self.assertEqual(pending["attempts"], 2)
        self.assertEqual(pending["phase"], "commanded")
        self.assertFalse(runtime.record.get("paused"))
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        recovered = self.rehydrate(runtime)
        await recovered.evaluate()
        self.assertEqual(len(recovered.calls), 1)
        self.assertEqual(recovered.record["pending"]["attempts"], 3)
        self.assertEqual(recovered.record["pending"]["when"], pending["when"])
        self.assertFalse(production.matches(recovered.state, pending["expected"]))

    async def test_pre_dispatch_settings_change_does_not_consume_reserved_retry(self):
        runtime, pending = await self.dispatched()
        original = deepcopy(pending)
        original_save = runtime._save
        changed = False

        async def change_during_retry_intent():
            nonlocal changed
            await original_save()
            active = runtime.record.get("pending")
            if not changed and active and active.get("phase") == "retry_intent" and active["attempts"] == 2:
                changed = True
                runtime.manager.settings["kp"] -= 1.0

        runtime._save = change_during_retry_intent
        await runtime.evaluate(60)
        self.assertTrue(changed, "The actual durable retry boundary must be reached")
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.record["pending"], original)
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        self.assertEqual(runtime.manager.settings["control_mode"], "pid")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Retain exhausted target budgets while ordinary shutdown remains reachable.

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


class ExhaustedTargetRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def exhausted(self, method="pid", mode="heat"):
        runtime = RecoveryRuntime(method, mode)
        # Keep a continuously requested ON episode in the budget tests. PWM
        # OFF and stop-policy obligations are covered in the shutdown suite.
        runtime.manager.settings["kp"] = 100.0
        runtime.own_running()
        await runtime.evaluate()
        pending = runtime.record["pending"]
        self.assertEqual(runtime.calls, [{
            "domain": "climate", "service": "set_temperature",
            "data": {"temperature": runtime.requested_target},
            "target": {"entity_id": PRIMARY},
        }])
        for attempt in (2, 3, 4):
            await runtime.evaluate(30)
            self.assertEqual(pending["attempts"], attempt)
            self.assertIs(runtime.record["pending"], pending)
        await runtime.evaluate(30)
        self.assertEqual(len(runtime.calls), 4)
        self.assertEqual(runtime.record["paused"], "physical_acknowledgement_missing")
        self.assertEqual(pending["phase"], "commanded")
        self.assertEqual(runtime.state.attributes["temperature"], runtime.original_target)
        self.assertFalse(production.matches(runtime.state, pending["expected"]))
        return runtime, pending

    async def retire(self, runtime, pending):
        original = deepcopy(pending)
        owned_since = runtime.record["power"][PRIMARY]["since"]
        await runtime.evaluate()
        self.assertIs(runtime.record["pending"], pending)
        information = runtime.resume_information(SPEC) or {}
        if information.get("decision") == "settling":
            remaining = information["remaining_seconds"]
            # The fourth/reconnect attempt needs its own full 120-second
            # settle period; time since the original attempt is insufficient.
            await runtime.evaluate(remaining - 1)
            self.assertIs(runtime.record["pending"], pending)
            self.assertNotIn("pending_resume_probe", runtime.record)
            await runtime.evaluate(1)
        self.assertIn("pending_resume_probe", runtime.record)
        await runtime.evaluate(60)
        self.assertIsNone(runtime.record["pending"])
        self.assertIsNone(runtime.record["paused"])
        self.assertIn("unconfirmed_native_target", runtime.record)
        ledger = runtime.record["unconfirmed_native_target"]
        self.assertEqual(ledger, original)
        self.assertEqual(runtime.record["last_resume_reconciliation"]["method"],
                         "stable_native_state")
        self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
        self.assertFalse(runtime.statuses[-1][1]["physical_output_confirmed"])
        self.assertNotIn("automatic_continue_requested", runtime.record)
        return ledger

    async def reconciled(self, method="pid", mode="heat"):
        runtime, pending = await self.exhausted(method, mode)
        ledger = await self.retire(runtime, pending)
        return runtime, ledger

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

    async def test_unchanged_feedback_cannot_reset_retired_four_attempt_budget(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, ledger = await self.reconciled(method, mode)
                    original_ledger = deepcopy(ledger)
                    recovery_tasks = runtime.created_recovery_tasks
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    for delta in (0, 5, 25, 60, 60, 120, 300, 900):
                        await runtime.evaluate(delta)
                    self.assertEqual(len(runtime.calls), 4, runtime.calls)
                    self.assertIsNone(runtime.record["pending"])
                    self.assertIsNone(runtime.record["paused"])
                    self.assertEqual(runtime.record["unconfirmed_native_target"], original_ledger)
                    self.assertEqual(runtime.state.attributes["temperature"], runtime.original_target)
                    self.assertFalse(production.matches(runtime.state, ledger["expected"]))
                    self.assertNotIn("pending_resume_probe", runtime.record)
                    self.assertEqual(runtime.created_recovery_tasks, recovery_tasks)
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertEqual(runtime.statuses[-1][0], "awaiting_physical_acknowledgement")
                    self.assertEqual(runtime.statuses[-1][1]["command_attempts"], 4)
                    self.assertFalse(runtime.statuses[-1][1]["native_output_confirmed"])

    async def test_late_native_target_ack_clears_budget_without_replay_or_dwell_reset(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, ledger = await self.reconciled(method, mode)
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    measured = runtime.state.attributes["current_temperature"]
                    await runtime.evaluate(180)
                    self.assertEqual(len(runtime.calls), 4)
                    runtime.report(temperature=runtime.requested_target)
                    self.assertTrue(production.matches(runtime.state, ledger["expected"]))
                    await runtime.evaluate()
                    self.assertNotIn("unconfirmed_native_target", runtime.record)
                    self.assertIsNone(runtime.record["pending"])
                    self.assertIsNone(runtime.record["paused"])
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertEqual(runtime.state.attributes["current_temperature"], measured)
                    self.assertNotEqual(measured, runtime.requested_target)
                    self.assertEqual(len(runtime.calls), 4)
                    await runtime.evaluate(1)
                    self.assertEqual(len(runtime.calls), 4)

    async def test_only_two_real_reconnects_can_extend_original_target_budget(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, ledger = await self.reconciled(method, mode)
                    original_call = deepcopy(runtime.calls[0])
                    original_when = ledger["when"]
                    last_used_epoch = None
                    for reconnect in (1, 2, 3):
                        before_calls = len(runtime.calls)
                        runtime.now += 1
                        runtime.availability_event("unavailable")
                        await runtime.evaluate()
                        self.assertEqual(len(runtime.calls), before_calls)
                        runtime.now += 5
                        runtime.availability_event(mode)
                        epoch = runtime._native_reconnect_epoch[PRIMARY]
                        self.assertGreater(epoch, runtime.record["unconfirmed_native_target"]["last_attempt_at"])
                        await runtime.evaluate()
                        await runtime.evaluate(29)
                        self.assertEqual(len(runtime.calls), before_calls,
                                         "Native reconnection must settle before any retry")
                        await runtime.evaluate(1)
                        expected_calls = 4 + min(reconnect, 2)
                        self.assertEqual(len(runtime.calls), expected_calls)
                        if reconnect <= 2:
                            pending = runtime.record["pending"]
                            self.assertEqual(pending["attempts"], expected_calls)
                            self.assertEqual(pending["when"], original_when)
                            self.assertEqual(pending["reconnect_retry_uses"], reconnect)
                            self.assertEqual(runtime.record["unconfirmed_native_target"]["attempts"], expected_calls)
                            last_used_epoch = epoch
                            await runtime.evaluate(30)
                            self.assertEqual(runtime.record["paused"], "physical_acknowledgement_missing")
                            await self.retire(runtime, pending)
                        budget = runtime.record["unconfirmed_native_target"]
                        self.assertEqual(budget["attempts"], expected_calls)
                        self.assertEqual(budget["reconnect_retry_uses"], min(reconnect, 2))
                        self.assertEqual(budget["reconnect_retry_epoch_used"], last_used_epoch)
                        self.assertEqual(budget["when"], original_when)
                        for delta in (0, 30, 60, 180):
                            await runtime.evaluate(delta)
                            self.assertEqual(len(runtime.calls), expected_calls,
                                             "One reconnect does not create repeated retry grants")
                            self.assertIsNone(runtime.record["pending"])
                        self.assertFalse(production.matches(runtime.state, budget["expected"]))
                    self.assertEqual(runtime.calls, [original_call] * 6)

    async def test_reconnect_revalidates_settings_before_identical_target_dispatch(self):
        runtime, ledger = await self.reconciled()
        runtime.now += 1
        runtime.availability_event("unavailable")
        runtime.now += 5
        runtime.availability_event("heat")
        runtime.manager.settings["kp"] -= 1.0
        await runtime.evaluate(30)
        self.assertEqual(len(runtime.calls), 4)
        self.assertIsNone(runtime.record["pending"])
        self.assertEqual(runtime.record["unconfirmed_native_target"], ledger)
        self.assertFalse(production.matches(runtime.state, ledger["expected"]))

    async def test_explicit_continue_button_clears_budget_without_service_until_next_tick(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime, _ = await self.reconciled(method, mode)
                    owned_since = runtime.record["power"][PRIMARY]["since"]
                    scheduled = runtime.scheduled_evaluations
                    self.assertTrue(await runtime.async_continue_automatic(SPEC))
                    self.assertNotIn("unconfirmed_native_target", runtime.record)
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
                    self.assertEqual(len(runtime.calls), 4, "The actual button verifier sends no service")
                    self.assertGreater(runtime.scheduled_evaluations, scheduled)
                    await runtime.evaluate()
                    self.assertEqual(len(runtime.calls), 5)
                    self.assertEqual(runtime.calls[-1]["data"], {"temperature": runtime.requested_target})
                    self.assertEqual(runtime.record["pending"]["attempts"], 1)

    async def test_explicit_two_checks_keep_existing_user_reconciliation(self):
        runtime, pending = await self.exhausted()
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
        self.assertEqual(len(runtime.calls), 4)

    async def test_persisted_budget_survives_automatic_rehydration_until_target_or_off_ack(self):
        for method in ("pid", "automatic"):
            for ending in ("target_ack", "off_ack"):
                with self.subTest(method=method, ending=ending):
                    original, ledger = await self.reconciled(method)
                    runtime = self.rehydrate(original)
                    self.assertIsNone(runtime.record["pending"])
                    await runtime.async_resume(SPEC, automatic=True)
                    self.assertEqual(runtime.record["unconfirmed_native_target"], ledger)
                    await runtime.evaluate()
                    self.assertEqual(runtime.calls, [], "Restart must not create a fresh target budget")
                    self.assertEqual(runtime.record["unconfirmed_native_target"]["attempts"], 4)
                    if ending == "target_ack":
                        runtime.report(temperature=runtime.requested_target)
                        await runtime.evaluate()
                        self.assertEqual(runtime.calls, [])
                    else:
                        runtime.measurement = 23.0
                        await runtime.evaluate()
                        self.assertEqual(runtime.calls[-1]["data"], {"temperature": runtime.original_target})
                        self.assertEqual(len(runtime.calls), 1)
                        await runtime.evaluate(30)
                        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
                        self.assertEqual(len(runtime.calls), 2)
                        self.assertIn("unconfirmed_native_target", runtime.record,
                                      "A successful OFF service is not physical OFF feedback")
                        runtime.report(mode="off")
                        await runtime.evaluate()
                        self.assertNotIn(PRIMARY, runtime.record["power"])
                    self.assertIsNone(runtime.record["pending"])
                    self.assertNotIn("unconfirmed_native_target", runtime.record)

    async def test_interrupted_reconnect_intent_cannot_lose_its_reserved_budget(self):
        runtime, _ = await self.reconciled()
        original_service = runtime.service_call
        async def uncertain_service(*args, **kwargs):
            await original_service(*args, **kwargs)
            raise TimeoutError("Simulated uncertain native completion")
        runtime.hass.services.async_call = uncertain_service
        runtime.now += 1
        runtime.availability_event("unavailable")
        runtime.now += 5
        runtime.availability_event("heat")
        await runtime.evaluate(30)
        self.assertEqual(len(runtime.calls), 5)
        self.assertEqual(runtime.record["pending"]["phase"], "intent")
        self.assertEqual(runtime.record["unconfirmed_native_target"]["attempts"], 5)
        recovered = self.rehydrate(runtime)
        recovered.record["automatic_continue_requested"] = {
            "at": recovered.now, "method": "pid", "origin": "automatic_restart_reconciliation",
        }
        pending = recovered.record["pending"]
        await self.retire(recovered, pending)
        self.assertEqual(recovered.record["unconfirmed_native_target"]["attempts"], 5)
        self.assertEqual(recovered.record["unconfirmed_native_target"]["reconnect_retry_uses"], 1)
        await recovered.evaluate()
        self.assertEqual(recovered.calls, [])

    async def test_pre_dispatch_abort_preserves_the_old_reconnect_budget(self):
        runtime, ledger = await self.reconciled()
        old_budget = deepcopy(ledger)
        original_save = runtime._save
        changed = False
        async def change_during_intent_save():
            nonlocal changed
            await original_save()
            pending = runtime.record.get("pending")
            if not changed and pending and pending.get("phase") == "intent" and pending["attempts"] == 5:
                changed = True
                runtime.manager.settings["kp"] -= 1.0
        runtime._save = change_during_intent_save
        runtime.now += 1
        runtime.availability_event("unavailable")
        runtime.now += 5
        runtime.availability_event("heat")
        await runtime.evaluate(30)
        self.assertTrue(changed)
        self.assertEqual(len(runtime.calls), 4)
        self.assertIsNone(runtime.record["pending"])
        self.assertEqual(runtime.record["unconfirmed_native_target"], old_budget)


if __name__ == "__main__":
    unittest.main(verbosity=2)

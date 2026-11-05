"""An unconfirmed target must not prevent a guarded native OFF command.

Run the production command/recovery lifecycle against the native HA transport
fixture. Stable feedback may release command serialization, but the separate
failed-target journal must preserve its retry budget through policy changes.
The tests assert actual OFF dispatch, not merely absence of another target.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_retry_recovery.py"),
                     run_name="hem_target_shutdown_fixture")
fixture, production = base["fixture"], base["production"]
SPEC, PRIMARY = base["SPEC"], base["PRIMARY"]
LEDGER = "unconfirmed_native_target"

# Use the production source-identity checks as well as the existing native
# shutdown gate. The one registered device can change independently of the
# saved controller record, as a real HA registry entry can.
production.configured_sources = lambda settings, area: (PRIMARY,)
fixture["registry"].async_get = lambda hass: N(async_get=lambda entity: N(
    platform="native_fixture", device_id=hass.fixture.registered_device_id,
) if entity == PRIMARY else None)
fixture["extract"](fixture["RUNTIME"],
                   ("_identity_ok", "_current_spec", "_retired"), production.__dict__)


class ShutdownRuntime(base["RecoveryRuntime"]):
    _identity_ok = production._identity_ok
    _current_spec = production._current_spec
    _retired = production._retired

    def __init__(self, method="pid", mode="heat"):
        super().__init__(method, mode)
        self.registered_device_id = SPEC.source_device_id
        self.after_persist = None

    async def _save(self):
        await super()._save()
        if self.after_persist is not None:
            self.after_persist(self)


class TargetShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def exhausted(self, *, method="pid", mode="heat", owned_age=1200):
        runtime = ShutdownRuntime(method, mode)
        runtime.own_running(age=owned_age)
        await runtime.evaluate()
        for attempt in (2, 3, 4):
            await runtime.evaluate(30)
            self.assertEqual(runtime.record["pending"]["attempts"], attempt)
        await runtime.evaluate(30)
        self.assertEqual(len(runtime.calls), 4)
        self.assertTrue(all(call["service"] == "set_temperature" for call in runtime.calls))
        self.assertEqual(runtime.record["paused"], "physical_acknowledgement_missing")
        self.assertFalse(production.matches(runtime.state, runtime.record["pending"]["expected"]))
        return runtime, deepcopy(runtime.record["pending"])

    def open_window(self, runtime):
        runtime.window.update(blocked=True, stop_requested=True, status="window_open_pause")

    def close_window(self, runtime):
        runtime.window.update(blocked=False, stop_requested=False, status="ready")

    def require_stop(self, runtime, stop):
        if stop == "window":
            self.open_window(runtime)
        elif stop == "sleep":
            runtime.sleeping = True
            runtime.manager.device["sleep_behavior"] = "pause"
        elif stop == "idle":
            runtime.measurement = 23.0 if runtime.manager.settings["requested_mode"] == "heat" else 24.0
        else:
            owned = runtime.record["power"][PRIMARY]
            runtime.now = owned["since"] + owned["max_on"] + 1

    def assert_ledger(self, runtime, original):
        self.assertEqual(runtime.record.get(LEDGER), original)
        self.assertEqual(runtime.record[LEDGER]["attempts"], 4)
        self.assertFalse(production.matches(runtime.state, original["expected"]))

    async def reconcile_target(self, runtime, original):
        owned_since = runtime.record["power"][PRIMARY]["since"]
        await self.begin_verification(runtime)
        self.assertIsNotNone(runtime.record["pending"])
        await runtime.evaluate(60)
        self.assertIsNone(runtime.record["pending"])
        self.assertIsNone(runtime.record["paused"])
        self.assert_ledger(runtime, original)
        self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
        self.assertEqual(len(runtime.calls), 4, "State reconciliation is not a device command")
        self.assertNotEqual(runtime.record["last_resume_reconciliation"]["method"], "fresh_native_ack")

    async def begin_verification(self, runtime):
        await runtime.evaluate()
        information = runtime.resume_information(SPEC) or {}
        if information.get("decision") == "settling":
            # Each retry starts its own physical settling window; a stop
            # policy does not turn older first-attempt age into fresh proof.
            await runtime.evaluate(information["remaining_seconds"] - 1)
            self.assertNotIn("pending_resume_probe", runtime.record)
            await runtime.evaluate(1)
        self.assertIn("pending_resume_probe", runtime.record)

    async def drain_recovery_tasks(self, runtime):
        while runtime.queued_tasks:
            tasks, runtime.queued_tasks = runtime.queued_tasks, []
            await asyncio.gather(*tasks)

    def assert_off_command(self, runtime, original):
        self.assertEqual(len(runtime.calls), 6, runtime.calls)
        self.assertEqual(runtime.calls[-1], {
            "domain": "climate", "service": "set_hvac_mode",
            "data": {"hvac_mode": "off"}, "target": {"entity_id": PRIMARY},
        })
        self.assertEqual(runtime.record["pending"]["expected"], {"state": "off"})
        self.assertEqual(runtime.record["pending"]["phase"], "commanded")
        self.assert_ledger(runtime, original)
        self.assertIn(PRIMARY, runtime.record["power"], "Service completion does not prove OFF")

    async def finish_prepared_stop(self, runtime, original):
        # Beta109 adds a distinct reducing-target leg. It is allowed even
        # while the failed ON target keeps its original exhausted budget.
        self.assertEqual(len(runtime.calls), 5)
        self.assertEqual(runtime.calls[-1]["data"], {"temperature": runtime.original_target})
        self.assert_ledger(runtime, original)
        self.assertIn("native_setpoint_stop", runtime.record)
        await runtime.evaluate(30)
        self.assert_off_command(runtime, original)

    async def test_each_required_stop_dispatches_off_and_waits_for_its_ack(self):
        for method in ("automatic", "pid"):
            for mode in ("heat", "cool"):
                for stop in ("window", "sleep", "idle", "maximum_on"):
                    with self.subTest(method=method, mode=mode, stop=stop):
                        runtime, original = await self.exhausted(method=method, mode=mode)
                        self.require_stop(runtime, stop)
                        cap = fixture["model"].capabilities(runtime.manager, SPEC)
                        if stop != "maximum_on":
                            self.assertTrue(runtime._stop_policy_verified(SPEC, cap, stop))
                        self.assertTrue(runtime._shutdown_allowed(SPEC, PRIMARY, {"state": "off"}))
                        await self.reconcile_target(runtime, original)
                        await runtime.evaluate()
                        await self.finish_prepared_stop(runtime, original)
                        runtime.report(mode="off")
                        await runtime.evaluate(1)
                        self.assertIsNone(runtime.record["pending"])
                        self.assertNotIn(PRIMARY, runtime.record["power"])
                        self.assertNotIn(LEDGER, runtime.record)
                        self.assertEqual(len(runtime.calls), 6)

    async def test_withdrawn_stop_cannot_reset_the_failed_target_budget(self):
        for method in ("automatic", "pid"):
            for mode in ("heat", "cool"):
                for change_at in ("before_resume_task", "after_resume"):
                    with self.subTest(method=method, mode=mode, change_at=change_at):
                        runtime, original = await self.exhausted(method=method, mode=mode)
                        self.open_window(runtime)
                        await self.begin_verification(runtime)
                        runtime.now += 60
                        if change_at == "before_resume_task":
                            await runtime.tick(SPEC)
                            self.assertTrue(runtime.queued_tasks)
                            self.close_window(runtime)
                            await self.drain_recovery_tasks(runtime)
                        else:
                            await runtime.evaluate()
                            self.close_window(runtime)
                        self.assertIsNone(runtime.record["pending"])
                        self.assert_ledger(runtime, original)
                        cap = fixture["model"].capabilities(runtime.manager, SPEC)
                        self.assertIs(fixture["supply"].approved_demand(
                            runtime, SPEC, runtime.manager.settings, cap,
                        ), True)
                        for delta in (1, 30, 60):
                            await runtime.evaluate(delta)
                            self.assertEqual(len(runtime.calls), 4, runtime.calls)
                            self.assertIsNone(runtime.record["pending"])
                            self.assert_ledger(runtime, original)

    async def test_stop_withdrawn_during_preparation_persistence_preserves_failed_target(self):
        runtime, original = await self.exhausted()
        self.open_window(runtime)
        await self.reconcile_target(runtime, original)

        def withdraw_after_intent(controller):
            pending = controller.record.get("pending") or {}
            if pending.get("stop_target") and pending.get("phase") == "intent":
                self.close_window(controller)
                controller.after_persist = None

        runtime.after_persist = withdraw_after_intent
        await runtime.evaluate()
        self.assertIsNone(runtime.after_persist, "The test must reach durable preparation intent")
        self.assertEqual(len(runtime.calls), 4, "The fresh stop recheck must prevent stale preparation")
        self.assertIsNone(runtime.record["pending"])
        self.assert_ledger(runtime, original)
        await runtime.evaluate(1)
        self.assertEqual(len(runtime.calls), 4, "Aborting preparation must not replenish the target budget")
        self.assert_ledger(runtime, original)

    async def test_reconciliation_preserves_minimum_on_before_off(self):
        runtime, original = await self.exhausted(owned_age=100)
        self.open_window(runtime)
        await self.reconcile_target(runtime, original)
        owned = runtime.record["power"][PRIMARY]
        self.assertLess(runtime.now - owned["since"], owned["min_on"])
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 4)
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")
        runtime.now = owned["since"] + owned["min_on"] - 1
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 4)
        self.assert_ledger(runtime, original)
        await runtime.evaluate(1)
        await self.finish_prepared_stop(runtime, original)

    async def test_late_target_ack_does_not_hide_an_explicit_user_mode_change(self):
        runtime, original = await self.exhausted()
        await self.reconcile_target(runtime, original)
        # Let the production manual-override handler write the selected
        # method through the fixture's HA configuration-entry boundary.
        model = fixture["model"]
        model.SETTINGS = "equipment_controllers"
        runtime.manager.entry.options = {}

        def update_entry(entry, *, options):
            entry.options = deepcopy(options)
            runtime.manager.settings.update(options[model.SETTINGS][SPEC.identifier])

        runtime.hass.config_entries = N(async_update_entry=update_entry)
        owned_since = runtime.record["power"][PRIMARY]["since"]
        runtime.state.context = N(user_id="explicit_ha_user", parent_id=None)
        runtime.report(mode="cool", temperature=runtime.requested_target)
        await runtime.evaluate(1)
        self.assertNotIn(LEDGER, runtime.record, "The target itself was acknowledged")
        self.assertEqual(runtime.record["paused"], "physical_manual_override")
        self.assertEqual(runtime.manager.settings["control_mode"], "manual")
        self.assertEqual(runtime.record["manual_override_evidence"]["kind"], "ha_user")
        self.assertIn("state", runtime.record["manual_override_evidence"]["changed_controls"])
        self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
        self.assertEqual(len(runtime.calls), 4, "A target ACK must not erase the user's mode change")

    async def test_foreign_owner_and_changed_identity_block_off(self):
        for guard in ("foreign_owner", "changed_identity"):
            with self.subTest(guard=guard):
                runtime, original = await self.exhausted()
                self.open_window(runtime)
                await self.reconcile_target(runtime, original)
                if guard == "foreign_owner":
                    runtime.foreign_owner = "different_controller"
                else:
                    runtime.registered_device_id = "replacement_device"
                    self.assertFalse(runtime._identity_ok(SPEC))
                await runtime.evaluate()
                self.assertEqual(len(runtime.calls), 4)
                self.assert_ledger(runtime, original)
                self.assertIn(PRIMARY, runtime.record["power"])

    async def test_off_dispatch_rechecks_owner_and_identity_after_persistence(self):
        for guard in ("foreign_owner", "changed_identity"):
            with self.subTest(guard=guard):
                runtime, original = await self.exhausted()
                self.open_window(runtime)
                await self.reconcile_target(runtime, original)

                def change_after_intent(controller):
                    pending = controller.record.get("pending") or {}
                    if pending.get("service") == "set_hvac_mode" and pending.get("phase") == "intent":
                        if guard == "foreign_owner":
                            controller.foreign_owner = "different_controller"
                        else:
                            controller.registered_device_id = "replacement_device"
                        controller.after_persist = None

                runtime.after_persist = change_after_intent
                await runtime.evaluate()
                self.assertEqual(runtime.calls[-1]["data"], {"temperature": runtime.original_target})
                await runtime.evaluate(30)
                self.assertIsNone(runtime.after_persist, "The test must reach durable OFF intent")
                self.assertEqual(len(runtime.calls), 5, "Only the preparation was dispatched")
                self.assertIsNone(runtime.record["pending"])
                self.assert_ledger(runtime, original)

    async def test_revoked_grant_keeps_existing_resume_restriction_and_failed_budget(self):
        runtime, original = await self.exhausted()
        runtime.manager.power_grant = False
        self.assertTrue(runtime._shutdown_allowed(SPEC, PRIMARY, {"state": "off"}))
        # Existing explicit Resume requires a power grant even for an owned
        # active output. This patch must not invent one or drop its journal.
        for delta in (0, 90, 60):
            await runtime.evaluate(delta)
            self.assertEqual(len(runtime.calls), 4)
            self.assertEqual(runtime.record["pending"], original)
            self.assertNotIn(LEDGER, runtime.record)
            self.assertIn(PRIMARY, runtime.record["power"])
        self.assertIn("Physical power control is not authorized", runtime.statuses[-1][1]["last_verification_issue"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

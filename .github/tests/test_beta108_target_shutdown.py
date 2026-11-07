"""An unconfirmed target must not prevent a guarded native OFF command.

Run the production command/recovery lifecycle against the native HA transport
fixture. Stable feedback may release command serialization, but the separate
failed-target journal must preserve its command history through policy changes.
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
    id="registry-" + entity, unique_id="native-" + entity,
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
    # This fixture exercises continuing Automatic target journals. PID cutoff
    # and its separate bounded target ledger retain their own dedicated gates.
    async def unconfirmed(self, *, method="automatic", mode="heat", owned_age=1200):
        runtime = ShutdownRuntime(method, mode)
        runtime.manager.settings["kp"] = 100.0
        runtime.own_running(age=owned_age)
        await runtime.evaluate()
        for attempt in (2, 3, 4):
            await runtime.evaluate(60)
            self.assertEqual(runtime.record["pending"]["attempts"], attempt)
        self.assertEqual(len(runtime.calls), 4)
        self.assertTrue(all(call["service"] == "set_temperature" for call in runtime.calls))
        self.assertFalse(runtime.record.get("paused"))
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

    def assert_history(self, runtime, original, *, archived=True):
        retained = runtime.record.get(LEDGER)
        if not archived and retained is None:
            retained = runtime.record.get("pending")
        self.assertIsInstance(retained, dict, "The unconfirmed original command must remain accounted for")
        for key, value in original.items():
            self.assertEqual(retained.get(key), value, key)
        self.assertEqual(retained["attempts"], 4)
        self.assertFalse(production.matches(runtime.state, original["expected"]))

    def assert_off_command(self, runtime, original):
        self.assertEqual(len(runtime.calls), 5, runtime.calls)
        self.assertEqual(runtime.calls[-1], {
            "domain": "climate", "service": "set_hvac_mode",
            "data": {"hvac_mode": "off"}, "target": {"entity_id": PRIMARY},
        })
        self.assertEqual(runtime.record["pending"]["expected"], {"state": "off"})
        self.assertEqual(runtime.record["pending"]["phase"], "commanded")
        self.assert_history(runtime, original)
        self.assertIn(PRIMARY, runtime.record["power"], "Service completion does not prove OFF")
        self.assertNotIn("native_setpoint_stop", runtime.record,
                         "A new stop must send OFF directly without the retired target preparation")

    async def test_each_required_stop_dispatches_off_and_waits_for_its_ack(self):
        for method in ("automatic",):
            for mode in ("heat", "cool"):
                for stop in ("window", "sleep", "idle", "maximum_on"):
                    with self.subTest(method=method, mode=mode, stop=stop):
                        runtime, original = await self.unconfirmed(method=method, mode=mode)
                        self.require_stop(runtime, stop)
                        cap = fixture["model"].capabilities(runtime.manager, SPEC)
                        if stop != "maximum_on":
                            self.assertTrue(runtime._stop_policy_verified(SPEC, cap, stop))
                        self.assertTrue(runtime._shutdown_allowed(SPEC, PRIMARY, {"state": "off"}))
                        await runtime.evaluate()
                        self.assert_off_command(runtime, original)
                        runtime.report(mode="off")
                        await runtime.evaluate(1)
                        self.assertIsNone(runtime.record["pending"])
                        self.assertNotIn(PRIMARY, runtime.record["power"])
                        self.assertNotIn(LEDGER, runtime.record)
                        self.assertEqual(len(runtime.calls), 5)

    async def test_withdrawn_stop_preserves_target_history_and_resumes_same_minute_episode(self):
        for method in ("automatic",):
            for change_at in ("archive_save", "off_intent"):
                with self.subTest(method=method, change_at=change_at):
                    runtime, original = await self.unconfirmed(method=method)
                    self.open_window(runtime)

                    def withdraw_after_persist(controller):
                        pending = controller.record.get("pending") or {}
                        archived = controller.record.get(LEDGER)
                        at_boundary = (
                            isinstance(archived, dict) and archived.get("when") == original["when"]
                            and not pending
                            if change_at == "archive_save" else
                            pending.get("service") == "set_hvac_mode"
                            and pending.get("expected") == {"state": "off"}
                            and pending.get("phase") == "intent"
                        )
                        if at_boundary:
                            controller.after_persist = None
                            self.close_window(controller)

                    runtime.after_persist = withdraw_after_persist
                    await runtime.evaluate()
                    self.assertIsNone(runtime.after_persist, "The real durable stop boundary must be reached")
                    self.assertEqual(len(runtime.calls), 4, "Withdrawn stop must not dispatch stale OFF")
                    self.assertNotIn("native_setpoint_stop", runtime.record)
                    self.assert_history(runtime, original, archived=False)
                    await runtime.evaluate(59.999)
                    self.assertEqual(len(runtime.calls), 4, "Retiring a target cannot reset its retry interval")
                    await runtime.evaluate(.001)
                    self.assertEqual(len(runtime.calls), 5)
                    self.assertEqual(runtime.calls[-1]["data"], original["data"])
                    self.assertEqual(runtime.record["pending"]["attempts"], 5)
                    self.assertEqual(runtime.record["pending"]["when"], original["when"])
                    self.assertFalse(runtime.record.get("paused"))

    async def test_dispatched_off_keeps_waiting_for_ack_after_window_closes_without_losing_target(self):
        runtime, original = await self.unconfirmed()
        self.open_window(runtime)
        await runtime.evaluate()
        self.assert_off_command(runtime, original)
        pending_off = deepcopy(runtime.record["pending"])
        self.close_window(runtime)
        await runtime.evaluate(1)
        self.assert_off_command(runtime, original)
        self.assertEqual(runtime.record["pending"], pending_off)
        self.assertEqual(runtime.record["pending"]["expected"], {"state": "off"})

    async def test_pending_target_does_not_shortcut_minimum_on_before_off(self):
        runtime, original = await self.unconfirmed(owned_age=100)
        self.open_window(runtime)
        owned = runtime.record["power"][PRIMARY]
        self.assertLess(runtime.now - owned["since"], owned["min_on"])
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 4)
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")
        runtime.now = owned["since"] + owned["min_on"] - .001
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 4)
        self.assert_history(runtime, original, archived=False)
        await runtime.evaluate(.001)
        self.assert_off_command(runtime, original)

    async def test_late_target_ack_does_not_hide_an_explicit_user_mode_change(self):
        runtime, original = await self.unconfirmed()
        model = fixture["model"]
        model.SETTINGS = "equipment_controllers"
        runtime.manager.entry.options = {}

        def update_entry(entry, *, options):
            entry.options = deepcopy(options)
            runtime.manager.settings.update(options[model.SETTINGS][SPEC.identifier])

        runtime.hass.config_entries = N(async_update_entry=update_entry)
        owned_since = runtime.record["power"][PRIMARY]["since"]
        runtime.now += 1
        runtime.state.context = N(user_id="explicit_ha_user", parent_id=None, id="new-user-action")
        runtime.report(mode="cool", temperature=runtime.requested_target)
        self.assertTrue(production.matches(runtime.state, original["expected"]))
        await runtime.evaluate()
        self.assertEqual(runtime.record["paused"], "physical_manual_override")
        self.assertEqual(runtime.manager.settings["control_mode"], "manual")
        self.assertEqual(runtime.record["manual_override_evidence"]["kind"], "ha_user")
        self.assertIn("state", runtime.record["manual_override_evidence"]["changed_controls"])
        self.assertEqual(runtime.record["power"][PRIMARY]["since"], owned_since)
        self.assertEqual(len(runtime.calls), 4, "A target ACK must not erase the user's mode change")

    async def test_foreign_owner_and_changed_identity_block_off(self):
        for guard in ("foreign_owner", "changed_identity"):
            with self.subTest(guard=guard):
                runtime, original = await self.unconfirmed()
                self.open_window(runtime)
                if guard == "foreign_owner":
                    runtime.foreign_owner = "different_controller"
                else:
                    runtime.registered_device_id = "replacement_device"
                    self.assertFalse(runtime._identity_ok(SPEC))
                await runtime.evaluate()
                self.assertEqual(len(runtime.calls), 4)
                self.assert_history(runtime, original, archived=False)
                self.assertIn(PRIMARY, runtime.record["power"])

    async def test_off_dispatch_rechecks_owner_and_identity_after_persistence(self):
        for guard in ("foreign_owner", "changed_identity"):
            with self.subTest(guard=guard):
                runtime, original = await self.unconfirmed()
                self.open_window(runtime)

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
                self.assertIsNone(runtime.after_persist, "The test must reach durable OFF intent")
                self.assertEqual(len(runtime.calls), 4, "Changed ownership or identity must prevent OFF dispatch")
                self.assertIsNone(runtime.record["pending"])
                self.assert_history(runtime, original)
                self.assertIn(PRIMARY, runtime.record["power"])

    async def test_revoked_grant_blocks_explicit_resume_but_owned_protective_off_remains_authorized(self):
        runtime, original = await self.unconfirmed()
        runtime.manager.power_grant = False
        self.assertTrue(runtime._shutdown_allowed(SPEC, PRIMARY, {"state": "off"}))
        with self.assertRaises(base["HomeAssistantError"]):
            await runtime.async_resume(SPEC)
        self.assertEqual(len(runtime.calls), 4, "No explicit Resume may invent a physical power grant")
        self.assertEqual(runtime.record["pending"], original)
        self.open_window(runtime)
        await runtime.evaluate()
        self.assert_off_command(runtime, original)
        self.assertEqual(runtime.record["pending"]["data"], {"hvac_mode": "off"})
        self.assertIn(PRIMARY, runtime.record["power"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

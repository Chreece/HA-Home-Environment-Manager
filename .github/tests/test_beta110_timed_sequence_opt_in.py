"""Compare ordinary and opted-in native command traces on the production runtime.

The Beta109 harness isolates HA transport, settings, persistence and time.
The actual decision, intent, dispatch, retry and observation paths run here.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta109_setpoint_sequence.py"))
Runtime, SPEC, PRIMARY = (base[k] for k in ("SequenceRuntime", "SPEC", "PRIMARY"))
model, production, fixture = (base[k] for k in ("model", "production", "fixture"))
KEY = "timed_setpoint_sequence"
UNSET = object()


def choose(runtime, value):
    if value is UNSET:
        runtime.manager.settings.pop(KEY, None)
    else:
        runtime.manager.settings[KEY] = value


def calls(runtime):
    return [(c["service"], c["data"]) for c in runtime.calls]


OFF = ("set_hvac_mode", {"hvac_mode": "off"})


class OptInTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_invalid_options_use_immediate_extreme_and_ordinary_off(self):
        for value in (UNSET, False, None, 1, "true"):
            for method in ("automatic", "pid"):
                for mode in ("heat", "cool"):
                    with self.subTest(value="missing" if value is UNSET else value, method=method, mode=mode):
                        r = Runtime(method, mode)
                        choose(r, value)
                        r.manager.settings["kp"] = 100.
                        await r.evaluate()
                        mode_on = ("set_hvac_mode", {"hvac_mode": mode})
                        self.assertEqual(calls(r), [mode_on], "Never send a setpoint while OFF")
                        r.report(mode=mode)
                        ack_at = r.now
                        await r.evaluate()
                        target = ("set_temperature", {"temperature": r.requested_target})
                        self.assertEqual(calls(r), [mode_on, target])
                        self.assertEqual(r.call_times[-1], ack_at)
                        r.report(temperature=r.requested_target)
                        r.open_window()
                        await r.evaluate(599.999)
                        self.assertEqual(calls(r), [mode_on, target], "Minimum ON still applies")
                        await r.evaluate(.001)
                        self.assertEqual(calls(r), [mode_on, target, OFF])
                        self.assertNotIn("native_setpoint_stop", r.record)
                        self.assertIn(PRIMARY, r.record["power"], "OFF dispatch is not an ACK")
                        active_deadlines = [handle.deadline for handle in r.timer_loop.handles
                                            if not handle.cancelled() and not handle.fired]
                        self.assertEqual(active_deadlines, [r.now + 60],
                                         "Only the ordinary minute retry; no optional 30-second grace")

    async def test_soft_manual_range_and_humidity_send_without_optional_startup_grace(self):
        for service, data in (("set_temperature", {"temperature": 20.}),
                              ("set_temperature", {"target_temp_low": 19., "target_temp_high": 25.}),
                              ("set_humidity", {"humidity": 45.})):
            with self.subTest(service=service, data=data):
                r = Runtime("manual")
                choose(r, UNSET)
                r.manager.power_grant = False
                r.state.attributes.update(supported_features=7, humidity=60.,
                                          target_temp_low=18., target_temp_high=26.)
                r.report(mode="heat")
                cap = model.capabilities(r.manager, SPEC)
                await r._observe_native_running(SPEC, cap, r.state)
                self.assertTrue(await r.command(service, data))
                self.assertEqual(calls(r), [(service, data)])
                self.assertEqual(r.call_times[-1], r.state.last_changed.timestamp())

    async def test_switching_off_during_startup_grace_releases_the_target(self):
        r = Runtime("automatic")
        choose(r, True)
        await r.evaluate()
        r.report(mode="heat")
        await r.evaluate()
        self.assertEqual(r.statuses[-1][0], "native_setpoint_startup_grace")
        choose(r, False)
        await r.evaluate(1)
        self.assertEqual(calls(r), [("set_hvac_mode", {"hvac_mode": "heat"}),
                                    ("set_temperature", {"temperature": r.requested_target})])

    async def test_maximum_on_uses_prestop_lead_only_for_enabled_device(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                r = Runtime("automatic", "cool")
                r.running_extreme(age=7169)
                choose(r, enabled)
                await r.evaluate()
                self.assertFalse(r.calls)
                await r.evaluate(1)
                expected = [("set_temperature", {"temperature": r.original_target})] if enabled else []
                self.assertEqual(calls(r), expected)
                await r.evaluate(29.999)
                self.assertEqual(calls(r), expected)
                await r.evaluate(.001)
                self.assertEqual(calls(r), [*expected, OFF])
                self.assertEqual(r.call_times[-1] - r.record["power"][PRIMARY]["since"], 7200)

    async def test_pre_dispatch_toggle_rechecks_both_reverse_target_and_direct_off(self):
        for enabled in (True, False):
            for stage in ("intent_save", "semaphore"):
                with self.subTest(enabled=enabled, stage=stage):
                    r = Runtime("automatic", "cool")
                    r.running_extreme()
                    r.open_window()
                    choose(r, enabled)
                    saved_intent = asyncio.Event()
                    preparing = []

                    def at_intent(controller):
                        p = controller.record.get("pending") or {}
                        if p.get("phase") == "intent":
                            preparing.append(bool(p.get("stop_target")))
                            controller.after_persist = None
                            saved_intent.set()
                            if stage == "intent_save":
                                choose(controller, not enabled)

                    r.after_persist = at_intent
                    if stage == "semaphore":
                        await r._commands.acquire()
                        task = asyncio.create_task(r.evaluate())
                        try:
                            await asyncio.wait_for(saved_intent.wait(), timeout=2)
                            self.assertFalse(task.done())
                            choose(r, not enabled)
                        finally:
                            r._commands.release()
                        await task
                    else:
                        await r.evaluate()
                    self.assertTrue(saved_intent.is_set())
                    self.assertEqual(preparing, [enabled], "Exactly one initial stop decision")
                    self.assertFalse(r.calls, "Do not dispatch the old decision after a setting change")
                    self.assertIsNone(r.record.get("pending"))
                    self.assertNotIn("native_setpoint_stop", r.record)
                    await r.evaluate()
                    expected = OFF if enabled else ("set_temperature", {"temperature": r.original_target})
                    self.assertEqual(calls(r), [expected])

    async def test_finish_committed_stop_after_disable_or_b109_upgrade(self):
        for restart in (False, True):
            for confirmed in (False, True):
                with self.subTest(restart=restart, confirmed=confirmed):
                    r = Runtime("automatic", "heat")
                    r.running_extreme()
                    r.open_window()
                    choose(r, True)
                    await r.evaluate()
                    self.assertEqual(calls(r), [("set_temperature", {"temperature": r.original_target})])
                    anchor = r.record["native_setpoint_stop"]["sent_at"]
                    if confirmed:
                        r.report(temperature=r.original_target)
                        await r.evaluate(5)
                    if restart:
                        # A real b109 journal has no preference in its retry context.
                        backup = deepcopy(r.persisted[-1])
                        p = backup.get("pending")
                        if p:
                            p["retry_context"]["settings"].pop(KEY, None)
                        old = r
                        r = Runtime("automatic", "heat")
                        r.record = backup
                        r.records = {SPEC.identifier: r.record}
                        r.state = deepcopy(old.state)
                        r.now = old.now
                        r.record["paused"] = "restart_reconciliation_required"
                        choose(r, UNSET)
                    else:
                        choose(r, False)
                    r.close_window()
                    await r.evaluate(anchor + 29.999 - r.now)
                    self.assertFalse(any(call == OFF for call in calls(r)))
                    await r.evaluate(.001)
                    self.assertEqual(calls(r)[-1], OFF)
                    self.assertEqual(sum(call == OFF for call in calls(r)), 1)
                    self.assertEqual(r.call_times[-1], anchor + 30)
                    self.assertEqual(r.record["native_setpoint_stop"]["target_confirmed"], confirmed)
                    r.report(mode="off", temperature=r.original_target)
                    await r.evaluate()
                    self.assertNotIn("native_setpoint_stop", r.record)
                    self.assertNotIn(PRIMARY, r.record["power"])
                    n = len(r.calls)
                    await r.evaluate(599.999)
                    self.assertEqual(len(r.calls), n)
                    await r.evaluate(.001)
                    self.assertEqual(calls(r)[-1], ("set_hvac_mode", {"hvac_mode": "heat"}))
                    r.report(mode="heat")
                    await r.evaluate()
                    self.assertEqual(calls(r)[-1], ("set_temperature", {"temperature": r.requested_target}))

    async def test_legacy_pending_snapshot_with_missing_option_still_retries(self):
        for reason in ("target", "off"):
            with self.subTest(reason=reason):
                r = Runtime("automatic", "heat")
                choose(r, UNSET)
                if reason == "target":
                    r.own_running(age=900.)
                else:
                    r.running_extreme()
                    r.open_window()
                await r.evaluate()
                self.assertEqual(len(r.calls), 1)
                original = calls(r)[0]
                self.assertEqual(r.record["pending"]["attempts"], 1)
                r.record["pending"]["retry_context"]["settings"].pop(KEY, None)
                choose(r, False)
                await r.evaluate(59.999)
                self.assertEqual(calls(r), [original], "Retry must wait one full minute")
                await r.evaluate(.001)
                self.assertEqual(calls(r), [original, original])
                self.assertEqual(r.record["pending"]["attempts"], 2)
                self.assertFalse(r.record.get("paused"))
                self.assertNotIn("native_setpoint_stop", r.record)

    async def test_enabling_during_reserved_target_retry_preserves_attempt_and_waits_for_new_on(self):
        r = Runtime("automatic")
        choose(r, False)
        r.own_running(age=900.)
        await r.evaluate()
        target = ("set_temperature", {"temperature": r.requested_target})
        self.assertEqual(calls(r), [target])
        initial = deepcopy(r.record["pending"])
        # HA emits a genuine OFF->ON while the original target remains
        # unconfirmed; the final snapshot has the same mode/old setpoint.
        r.now += 55
        r.availability_event("off")
        r.availability_event("heat")

        def enable_before_retry(controller):
            if (controller.record.get("pending") or {}).get("phase") == "retry_intent":
                controller.after_persist = None
                choose(controller, True)
        r.after_persist = enable_before_retry
        await r.evaluate(5)
        self.assertIsNone(r.after_persist, "Must reach the durable retry boundary")
        self.assertEqual(calls(r), [target])
        self.assertEqual(r.record["pending"], initial, "A deferred retry has not consumed an attempt")
        self.assertFalse(r.record.get("paused"))
        await r.evaluate(24.999)
        self.assertEqual(calls(r), [target])
        await r.evaluate(.001)
        self.assertEqual(calls(r), [target, target])
        self.assertEqual(r.record["pending"]["attempts"], 2)

    async def test_two_native_entities_share_manager_but_use_separate_preferences(self):
        # HA transport and per-spec registry/config lookup are the only new fixture
        # boundaries. Both writes go through the same runtime, semaphore and Store.
        r = Runtime("automatic", "heat")
        second = N(identifier="second_controller", area_id=SPEC.area_id,
                   source_device_id="second_device", source_entities=("climate.other",))
        specs = (SPEC, second)
        entities = tuple(s.source_entities[0] for s in specs)
        devices = {s.source_entities[0]: s.source_device_id for s in specs}
        r.running_extreme(age=0)
        r.report(temperature=r.original_target)
        caps = {s.identifier: deepcopy(r.manager.settings) for s in specs}
        caps[SPEC.identifier][KEY] = True
        caps[second.identifier].pop(KEY, None)
        r.manager.settings = {"equipment_controllers": caps}
        r.hass.states.get = {entity: deepcopy(r.state) for entity in entities}.get
        for spec in specs:
            entity = spec.source_entities[0]
            r.records[spec.identifier] = {
                "area": spec.area_id, "source_device_id": spec.source_device_id,
                "sources": [entity], "baseline": {}, "power": {entity: {
                    "since": r.now, "min_on": 600., "max_on": 7200.,
                }}, "off_at": {},
            }
        r._record = lambda spec: r.records[spec.identifier]
        with ExitStack() as stack:
            stack.enter_context(patch.object(model, "configured_sources", lambda *_: entities))
            stack.enter_context(patch.object(production, "configured_sources", lambda *_: entities))
            stack.enter_context(patch.object(production, "entity_area", lambda *_: SPEC.area_id))
            stack.enter_context(patch.object(model, "settings",
                lambda manager, spec: manager.settings["equipment_controllers"][spec.identifier]))
            stack.enter_context(patch.object(fixture["registry"], "async_get",
                lambda hass: N(async_get=lambda entity: N(platform="native", device_id=devices[entity],
                    id="registry-" + entity, unique_id="native-" + entity))))
            async def target(spec):
                return await r._native_target(spec, model.capabilities(r.manager, spec),
                    "heat", {"heat": 21., "cool": 26.}, None, True)
            await target(SPEC)
            self.assertEqual(r.calls, [])
            await target(second)
            self.assertEqual([c["target"]["entity_id"] for c in r.calls], [entities[1]])
            r.now += 30
            await target(SPEC)
            self.assertEqual([c["target"]["entity_id"] for c in r.calls], [entities[1], entities[0]])
            self.assertTrue(all(c["data"] == {"temperature": r.requested_target} for c in r.calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Native start/stop setpoint timing through production command machinery.

HA states, service transport, registry/config storage and the timer loop are
isolated boundaries. Production tick/_power/_native_target/_send/_reconcile,
real ON observation and the sequence module execute together. Timers request
an evaluation; tests explicitly advance their clock and run that evaluation.
No physical acknowledgement is fabricated by service completion.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta108_target_shutdown.py"),
                     run_name="hem_sequence_fixture")
fixture, production = base["fixture"], base["production"]
SPEC, PRIMARY = base["SPEC"], base["PRIMARY"]
model, phase = fixture["model"], fixture["phase"]
sequence = fixture["load_pure"]("equipment_setpoint_sequence", "equipment_setpoint_sequence.py")
fixture["extract"](fixture["RUNTIME"], ("_observe_native_running", "_run"), production.__dict__)
fixture["extract"](ROOT / "equipment_model.py", ("control_modes",), model.__dict__)
production._LOGGER = N(exception=lambda *args, **kwargs: None)
CURRENT_LOOP = ContextVar("hem_sequence_timer_loop", default=None)
# Only the sequence's timer factory is isolated. Production async service
# timeouts/tasks and every state-machine decision still use their real code.
sequence.asyncio = N(get_running_loop=lambda: CURRENT_LOOP.get() or asyncio.get_running_loop())


class TimerHandle:
    def __init__(self, deadline, callback, args):
        self.deadline, self.callback, self.args = deadline, callback, args
        self._cancelled = False
        self.fired = False

    def cancel(self):
        self._cancelled = True

    def cancelled(self):
        return self._cancelled


class ClockLoop:
    def __init__(self, runtime):
        self.runtime = runtime
        self.handles = []

    def call_later(self, delay, callback, *args):
        handle = TimerHandle(self.runtime.now + delay, callback, args)
        self.handles.append(handle)
        return handle

    def fire_due(self):
        for handle in tuple(self.handles):
            if not handle.fired and not handle.cancelled() and handle.deadline <= self.runtime.now:
                handle.fired = True
                handle.callback(*handle.args)


class SequenceRuntime(base["ShutdownRuntime"]):
    _observe_native_running = production._observe_native_running
    _run = production._run

    def __init__(self, method="pid", mode="heat"):
        super().__init__(method, mode)
        self._native_session_observations = {}
        self._tasks = {}
        self._setpoint_rerun = set()
        self.timer_loop = ClockLoop(self)
        self.call_times, self.service_journals = [], []
        self.service_delay = 0.0

    async def service_call(self, *args, **kwargs):
        self.call_times.append(self.now)
        self.service_journals.append(deepcopy(self.record))
        await super().service_call(*args, **kwargs)
        self.now += self.service_delay

    async def evaluate(self, advance=0.0):
        self.now += advance
        token = CURRENT_LOOP.set(self.timer_loop)
        try:
            self.timer_loop.fire_due()
            await super().evaluate()
        finally:
            CURRENT_LOOP.reset(token)

    async def command(self, service, data, *, automatic=False):
        cap = model.capabilities(self.manager, SPEC)
        token = CURRENT_LOOP.set(self.timer_loop)
        try:
            return await self._send(SPEC, cap, PRIMARY, service, data,
                                    {"attributes": data}, automatic=automatic)
        finally:
            CURRENT_LOOP.reset(token)

    def running_extreme(self, age=900.0):
        self.own_running(age)
        self.report(temperature=self.requested_target)
        self.record["baseline"][PRIMARY] = production.snapshot(self.state)
        self.record["native_power_observations"] = {
            PRIMARY: {"state": "on", "since": self.now - age},
        }
        self._native_session_observations[(SPEC.identifier, PRIMARY)] = "on"
        self.record["capabilities"] = asdict(model.capabilities(self.manager, SPEC))

    def open_window(self):
        self.window.update(blocked=True, stop_requested=True, status="window_open_pause")

    def close_window(self):
        self.window.update(blocked=False, stop_requested=False, status="ready")

    def enable_config_writes(self):
        model.SETTINGS = "equipment_controllers"
        profile = {key: deepcopy(value) for key, value in self.manager.settings.items()
                   if key != model.SETTINGS}
        self.manager.settings[model.SETTINGS] = {SPEC.identifier: profile}
        self.manager.entry.options = {model.SETTINGS: deepcopy(self.manager.settings[model.SETTINGS])}
        def update_entry(entry, *, options):
            entry.options = deepcopy(options)
            self.manager.settings[model.SETTINGS] = deepcopy(options[model.SETTINGS])
            self.manager.settings.update(options[model.SETTINGS][SPEC.identifier])
        self.hass.config_entries = N(async_update_entry=update_entry)


class SetpointSequenceTests(unittest.IsolatedAsyncioTestCase):
    def rehydrate_stop(self, original, elapsed=0.0):
        runtime = SequenceRuntime(original.manager.settings["control_mode"],
                                  original.manager.settings["requested_mode"])
        runtime.record = deepcopy(original.persisted[-1])
        runtime.records = {SPEC.identifier: runtime.record}
        runtime.manager.settings = deepcopy(original.manager.settings)
        runtime.state = deepcopy(original.state)
        runtime.now = original.now + elapsed
        runtime._native_ready_since[PRIMARY] = runtime.now - 30
        runtime._native_settled_for[(SPEC.identifier, PRIMARY)] = runtime.now - 30
        runtime.record["paused"] = "restart_reconciliation_required"
        runtime.record["automatic_continue_requested"] = {"method": "pid", "at": runtime.now}
        return runtime

    def assert_reverse_target(self, runtime, count=1):
        self.assertEqual(len(runtime.calls), count, runtime.calls)
        self.assertEqual(runtime.calls[-1], {
            "domain": "climate", "service": "set_temperature",
            "data": {"temperature": runtime.original_target},
            "target": {"entity_id": PRIMARY},
        })
        self.assertIn("native_setpoint_stop", runtime.record)
        self.assertIn(PRIMARY, runtime.record["power"])
        self.assertEqual(runtime.service_journals[-1]["pending"]["phase"], "intent")

    def assert_off_request(self, runtime, count=2):
        self.assertEqual(len(runtime.calls), count, runtime.calls)
        self.assertEqual(runtime.calls[-1]["service"], "set_hvac_mode")
        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(runtime.record["pending"]["expected"], {"state": "off"})
        self.assertIn(PRIMARY, runtime.record["power"], "Sending OFF is not native OFF feedback")

    async def test_binary_start_waits_30_seconds_after_native_on_ack(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    runtime = SequenceRuntime(method, mode)
                    runtime.manager.settings["kp"] = 100.0
                    await runtime.evaluate()
                    self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": mode})
                    self.assertFalse(runtime.record["power"])
                    await runtime.evaluate(5)
                    self.assertEqual(len(runtime.calls), 1)
                    runtime.report(mode=mode)
                    ack_at = runtime.now
                    await runtime.evaluate()
                    self.assertEqual(len(runtime.calls), 1, "Mode ACK must not send the setpoint immediately")
                    self.assertEqual(runtime.record["power"][PRIMARY]["since"], ack_at)
                    self.assertEqual(runtime.statuses[-1][0], "native_setpoint_startup_grace")
                    await runtime.evaluate(29.999)
                    self.assertEqual(len(runtime.calls), 1)
                    await runtime.evaluate(0.001)
                    self.assertEqual(len(runtime.calls), 2)
                    self.assertEqual(runtime.calls[-1]["data"], {"temperature": runtime.requested_target})
                    self.assertGreaterEqual(runtime.call_times[-1] - ack_at, 30)
                    runtime.report(temperature=runtime.requested_target)
                    await runtime.evaluate(1)
                    self.assertIsNone(runtime.record["pending"])
                    self.assertEqual(len(runtime.calls), 2)

    async def test_manual_soft_range_and_humidity_setpoints_share_startup_guard(self):
        cases = (
            ("manual", "set_temperature", {"temperature": 22.0}),
            ("pid", "set_temperature", {"temperature": 22.0}),
            ("automatic", "set_temperature", {"target_temp_low": 18.0, "target_temp_high": 25.0}),
            ("manual", "set_humidity", {"humidity": 45.0}),
        )
        for method, service, data in cases:
            with self.subTest(method=method, service=service, data=data):
                runtime = SequenceRuntime(method)
                runtime.manager.power_grant = False
                runtime.state.attributes.update(supported_features=7, humidity=60.0,
                                                target_temp_low=17.0, target_temp_high=26.0)
                runtime.report(mode="heat")
                cap = model.capabilities(runtime.manager, SPEC)
                await runtime._observe_native_running(SPEC, cap, runtime.state)
                self.assertFalse(runtime.record["power"])
                self.assertFalse(await runtime.command(service, data, automatic=method != "manual"))
                self.assertEqual(runtime.calls, [])
                runtime.now += 29.999
                self.assertFalse(await runtime.command(service, data, automatic=method != "manual"))
                runtime.now += 0.001
                self.assertTrue(await runtime.command(service, data, automatic=method != "manual"))
                self.assertEqual(runtime.calls[-1]["data"], data)
                self.assertEqual(runtime.call_times[-1] - runtime.state.last_changed.timestamp(), 30.0)

    async def test_all_binary_stop_entrypoints_prepare_then_wait_then_off(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                for stop in ("idle", "window", "sleep", "explicit_off", "retired"):
                    with self.subTest(method=method, mode=mode, stop=stop):
                        runtime = SequenceRuntime(method, mode)
                        runtime.running_extreme()
                        if stop == "idle":
                            runtime.measurement = 23.0
                        elif stop == "window":
                            runtime.open_window()
                        elif stop == "sleep":
                            runtime.sleeping = True
                            runtime.manager.device["sleep_behavior"] = "pause"
                        elif stop == "explicit_off":
                            runtime.manager.settings.update(control_mode="off", requested_mode="off")
                        else:
                            runtime._current_spec = lambda spec: False
                        await runtime.evaluate()
                        self.assert_reverse_target(runtime)
                        sent_at = runtime.call_times[-1]
                        await runtime.evaluate(29.999)
                        self.assertEqual(len(runtime.calls), 1)
                        # No reverse-target ACK is supplied. The timer still
                        # finishes this committed OFF without fabricating ACK.
                        await runtime.evaluate(0.001)
                        self.assert_off_request(runtime)
                        self.assertGreaterEqual(runtime.call_times[-1] - sent_at, 30)
                        self.assertFalse(runtime.record["native_setpoint_stop"]["target_confirmed"])
                        runtime.report(mode="off")
                        await runtime.evaluate(1)
                        self.assertNotIn(PRIMARY, runtime.record["power"])
                        self.assertIsNone(runtime.record["pending"])
                        self.assertNotIn("native_setpoint_stop", runtime.record)
                        self.assertEqual(runtime.record["off_at"][PRIMARY], runtime.now)

    async def test_minimum_on_precedes_preparation_and_maximum_on_prepares_early(self):
        for mode in ("heat", "cool"):
            with self.subTest(mode=mode, timing="minimum_on"):
                runtime = SequenceRuntime("pid", mode)
                runtime.running_extreme(age=100)
                runtime.measurement = 23.0
                await runtime.evaluate()
                self.assertEqual(runtime.calls, [])
                await runtime.evaluate(499.999)
                self.assertEqual(runtime.calls, [])
                await runtime.evaluate(0.001)
                self.assert_reverse_target(runtime)
                await runtime.evaluate(30)
                self.assert_off_request(runtime)
            with self.subTest(mode=mode, timing="maximum_on"):
                runtime = SequenceRuntime("automatic", mode)
                runtime.running_extreme(age=7169.0)
                await runtime.evaluate()
                self.assertEqual(runtime.calls, [])
                await runtime.evaluate(1)
                self.assert_reverse_target(runtime)
                await runtime.evaluate(30)
                self.assert_off_request(runtime)
                self.assertEqual(runtime.call_times[-1] - runtime.record["power"][PRIMARY]["since"], 7200)

    async def test_pwm_off_leg_uses_reverse_bound_and_complete_wait(self):
        for mode in ("heat", "cool"):
            with self.subTest(mode=mode):
                runtime = SequenceRuntime("pid", mode)
                runtime.running_extreme()
                cfg = runtime.manager.settings
                goal = runtime.manager.targets[mode]
                signature, _, _ = phase.phase_decision(
                    None, metric="temperature", target=goal, increasing=mode == "heat", profile="comfort",
                    mode=mode, preset="none", kp=cfg["kp"], ki=cfg["ki"], kd=cfg["kd"],
                    cycle_s=3600.0, min_on_s=600.0, min_off_s=600.0, measured=runtime.measurement,
                )
                memory = model.PIDMemory(measured=runtime.measurement, stamp=runtime.now, demand=24.0)
                runtime._memory[SPEC.identifier] = signature, memory, runtime.now - 1500
                await runtime.evaluate()
                self.assert_reverse_target(runtime)
                await runtime.evaluate(30)
                self.assert_off_request(runtime)

    async def test_equal_reverse_target_is_still_sent_and_ack_never_claims_off(self):
        for mode in ("heat", "cool"):
            for simultaneous_off in (False, True):
                with self.subTest(mode=mode, simultaneous_off=simultaneous_off):
                    runtime = SequenceRuntime("automatic", mode)
                    runtime.running_extreme()
                    runtime.report(temperature=runtime.original_target)
                    runtime.record["baseline"][PRIMARY] = production.snapshot(runtime.state)
                    runtime.open_window()
                    await runtime.evaluate()
                    self.assert_reverse_target(runtime)
                    runtime.report(mode="off" if simultaneous_off else mode,
                                   temperature=runtime.original_target)
                    await runtime.evaluate(10)
                    if simultaneous_off:
                        self.assertNotIn(PRIMARY, runtime.record["power"])
                        self.assertIsNone(runtime.record["pending"])
                        self.assertNotIn("native_setpoint_stop", runtime.record)
                        self.assertEqual(runtime.record["off_at"][PRIMARY], runtime.now)
                        self.assertEqual(len(runtime.calls), 1, "Native OFF needs no duplicate OFF service")
                    else:
                        self.assertIn(PRIMARY, runtime.record["power"])
                        self.assertIsNone(runtime.record["pending"])
                        await runtime.evaluate(20)
                        self.assert_off_request(runtime)

    async def test_wait_uses_successful_dispatch_time_not_request_time_or_ack_time(self):
        runtime = SequenceRuntime()
        runtime.running_extreme()
        runtime.open_window()
        runtime.service_delay = 4.0
        began = runtime.now
        await runtime.evaluate()
        self.assert_reverse_target(runtime)
        self.assertEqual(runtime.now, began + 4)
        runtime.service_delay = 0
        runtime.report(temperature=runtime.original_target)
        await runtime.evaluate(26)
        self.assertEqual(runtime.now, began + 30)
        self.assertEqual(len(runtime.calls), 1)
        await runtime.evaluate(4)
        self.assert_off_request(runtime)
        self.assertEqual(runtime.call_times[-1], began + 34)

    async def test_committed_stop_survives_renewed_demand_but_unsent_stop_can_cancel(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                runtime = SequenceRuntime()
                runtime.running_extreme()
                runtime.open_window()
                if not committed:
                    def withdraw(controller):
                        pending = controller.record.get("pending") or {}
                        if pending.get("stop_target") and pending.get("phase") == "intent":
                            controller.close_window()
                            controller.after_persist = None
                    runtime.after_persist = withdraw
                await runtime.evaluate()
                runtime.close_window()
                if committed:
                    self.assert_reverse_target(runtime)
                    await runtime.evaluate(30)
                    self.assert_off_request(runtime)
                    self.assertEqual([call["data"] for call in runtime.calls],
                                     [{"temperature": 5.0}, {"hvac_mode": "off"}])
                else:
                    self.assertIsNone(runtime.after_persist)
                    self.assertEqual(runtime.calls, [])
                    self.assertNotIn("native_setpoint_stop", runtime.record)
                    await runtime.evaluate(60)
                    self.assertEqual(runtime.calls, [])

    async def test_committed_stop_rechecks_identity_owner_defrost_and_manual_override(self):
        for blocker in ("identity", "foreign", "defrost", "manual"):
            with self.subTest(blocker=blocker):
                runtime = SequenceRuntime()
                runtime.running_extreme()
                runtime.open_window()
                await runtime.evaluate()
                self.assert_reverse_target(runtime)
                if blocker == "identity":
                    runtime.registered_device_id = "replacement_device"
                elif blocker == "foreign":
                    runtime.foreign_owner = "different_controller"
                elif blocker == "defrost":
                    runtime.state.attributes["hvac_action"] = "defrosting"
                else:
                    runtime.enable_config_writes()
                    runtime.state.context = N(user_id="explicit_ha_user", parent_id=None)
                    runtime.report(mode="cool", temperature=12.0)
                await runtime.evaluate(30)
                self.assertEqual(len(runtime.calls), 1)
                self.assertIn(PRIMARY, runtime.record["power"])
                if blocker == "manual":
                    self.assertEqual(runtime.record["paused"], "physical_manual_override")

    async def test_persisted_stop_resumes_its_original_deadline_without_repeating_target(self):
        for elapsed in (10.0, 40.0):
            with self.subTest(elapsed=elapsed):
                original = SequenceRuntime()
                original.running_extreme()
                original.open_window()
                await original.evaluate()
                self.assert_reverse_target(original)
                saved = deepcopy(original.persisted[-1])
                runtime = SequenceRuntime()
                runtime.record = saved
                runtime.records = {SPEC.identifier: runtime.record}
                runtime.manager.settings = deepcopy(original.manager.settings)
                runtime.state = deepcopy(original.state)
                runtime.now = original.now + elapsed
                runtime._native_ready_since[PRIMARY] = runtime.now - 30
                runtime._native_settled_for[(SPEC.identifier, PRIMARY)] = runtime.now - 30
                runtime.record["paused"] = "restart_reconciliation_required"
                runtime.record["automatic_continue_requested"] = {"method": "pid", "at": runtime.now}
                runtime.close_window()  # The already-dispatched stop remains committed.
                await runtime.evaluate()
                if elapsed < 30:
                    self.assertEqual(runtime.calls, [])
                    await runtime.evaluate(30 - elapsed)
                self.assert_off_request(runtime, count=1)
                self.assertEqual(runtime.call_times[-1], original.now + max(elapsed, 30))
                self.assertEqual(runtime.record["native_setpoint_stop"]["sent_at"], original.now)

    async def test_restart_after_off_dispatch_retries_off_with_original_attempt_history(self):
        original = SequenceRuntime()
        original.running_extreme()
        original.open_window()
        await original.evaluate()
        await original.evaluate(30)
        self.assert_off_request(original)
        when = original.record["pending"]["when"]
        runtime = self.rehydrate_stop(original, elapsed=40)
        await runtime.evaluate()
        self.assert_off_request(runtime, count=1)
        self.assertEqual(runtime.record["pending"]["attempts"], 2)
        self.assertEqual(runtime.record["pending"]["when"], when)
        self.assertEqual(runtime.service_journals[-1]["pending"]["attempts"], 2,
                         "Reserve the retry count durably before the physical call")
        self.assertEqual(runtime.service_journals[-1]["pending"]["phase"], "intent")
        runtime.report(mode="off")
        await runtime.evaluate()
        self.assertNotIn(PRIMARY, runtime.record["power"])
        self.assertNotIn("native_setpoint_stop", runtime.record)

    async def test_uncertain_off_intent_waits_once_then_retries_without_inventing_ack(self):
        original = SequenceRuntime()
        original.running_extreme()
        original.open_window()
        await original.evaluate()
        normal_service = original.service_call
        async def uncertain_off(domain, service, data, **kwargs):
            await normal_service(domain, service, data, **kwargs)
            if service == "set_hvac_mode" and data == {"hvac_mode": "off"}:
                raise TimeoutError("Simulated uncertain OFF completion")
        original.hass.services.async_call = uncertain_off
        await original.evaluate(30)
        self.assertEqual(original.record["pending"]["phase"], "intent")
        runtime = self.rehydrate_stop(original, elapsed=100)
        old_intent = deepcopy(runtime.record["pending"])
        await runtime.evaluate()
        self.assertEqual(runtime.calls, [])
        self.assertEqual(runtime.record["pending"], old_intent)
        await runtime.evaluate(29.999)
        self.assertEqual(runtime.calls, [])
        await runtime.evaluate(0.001)
        self.assert_off_request(runtime, count=1)
        self.assertEqual(runtime.record["pending"]["attempts"], 2)
        self.assertEqual(runtime.record["pending"]["when"], old_intent["when"])
        self.assertEqual(runtime.service_journals[-1]["pending"]["phase"], "intent")
        self.assertEqual(runtime.service_journals[-1]["pending"]["attempts"], 2)
        self.assertNotEqual(runtime.state.state, "off")

    async def test_committed_off_retries_keep_four_attempts_plus_two_real_reconnects(self):
        runtime = SequenceRuntime()
        runtime.running_extreme()
        runtime.open_window()
        await runtime.evaluate()
        await runtime.evaluate(30)
        when = runtime.record["pending"]["when"]
        for attempt in (2, 3, 4):
            await runtime.evaluate(30)
            self.assertEqual(runtime.record["pending"]["attempts"], attempt)
            self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
        for delta in (30, 60, 180):
            await runtime.evaluate(delta)
            self.assertEqual(len(runtime.calls), 5, "Preparation plus four OFF attempts")
            self.assertEqual(runtime.record["pending"]["attempts"], 4)
        for reconnect in (1, 2, 3):
            runtime.now += 1
            runtime.availability_event("unavailable")
            await runtime.evaluate()
            runtime.now += 5
            runtime.availability_event("heat")
            previous_calls = len(runtime.calls)
            await runtime.evaluate(29.999)
            self.assertEqual(len(runtime.calls), previous_calls)
            await runtime.evaluate(0.001)
            attempts = 4 + min(reconnect, 2)
            self.assertEqual(runtime.record["pending"]["attempts"], attempts)
            self.assertEqual(runtime.record["pending"]["when"], when)
            self.assertEqual(len(runtime.calls), 1 + attempts)
            for delta in (30, 120):
                await runtime.evaluate(delta)
                self.assertEqual(len(runtime.calls), 1 + attempts)
        self.assertEqual(sum(call["service"] == "set_temperature" for call in runtime.calls), 1)
        self.assertEqual(sum(call["service"] == "set_hvac_mode" for call in runtime.calls), 6)

    async def test_explicit_resume_rebases_owned_dwell_without_stranding_committed_stop(self):
        runtime = SequenceRuntime()
        runtime.running_extreme()
        runtime.open_window()
        await runtime.evaluate()
        await runtime.evaluate(30)
        runtime.now += 120
        error_type = base["base"]["HomeAssistantError"]
        with self.assertRaises(error_type):
            await runtime.async_resume(SPEC)
        runtime.now += 60
        await runtime.async_resume(SPEC)
        self.assertEqual(runtime.record["power"][PRIMARY]["since"], runtime.now)
        self.assertIn("native_setpoint_stop", runtime.record)
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 2)
        await runtime.evaluate(599.999)
        self.assertEqual(len(runtime.calls), 2)
        await runtime.evaluate(0.001)
        self.assert_off_request(runtime, count=3)

    async def test_explicit_resume_after_manual_mode_change_retires_old_stop_without_command(self):
        runtime = SequenceRuntime()
        runtime.running_extreme()
        runtime.enable_config_writes()
        runtime.open_window()
        await runtime.evaluate()
        self.assert_reverse_target(runtime)
        runtime.state.context = N(user_id="explicit_ha_user", parent_id=None)
        runtime.report(mode="cool", temperature=12.0)
        await runtime.evaluate(1)
        self.assertEqual(runtime.record["paused"], "physical_manual_override")
        self.assertEqual(runtime.manager.settings["control_mode"], "manual")
        runtime.now += 119
        with self.assertRaises(base["base"]["HomeAssistantError"]):
            await runtime.async_resume(SPEC)
        runtime.now += 60
        await runtime.async_resume(SPEC)
        self.assertNotIn("native_setpoint_stop", runtime.record)
        self.assertIsNone(runtime.record["pending"])
        self.assertIsNone(runtime.record["paused"])
        self.assertEqual(runtime.manager.settings["control_mode"], "pid")
        self.assertEqual(runtime.state.state, "cool")
        self.assertEqual(runtime.state.attributes["temperature"], 12.0)
        self.assertEqual(len(runtime.calls), 1, "Explicit verification itself cannot send a new actuator command")

    async def test_coalesced_off_on_during_target_persistence_cannot_skip_new_start_grace(self):
        for retry in (False, True):
            with self.subTest(retry=retry):
                runtime = SequenceRuntime()
                runtime.manager.settings["kp"] = 100.0
                runtime.running_extreme()
                runtime.report(temperature=runtime.original_target)
                runtime.record["baseline"][PRIMARY] = production.snapshot(runtime.state)
                before = production.snapshot(runtime.state)
                if retry:
                    await runtime.evaluate()
                    self.assertEqual(len(runtime.calls), 1)
                edge_at = []
                def coalesce(controller):
                    pending = controller.record.get("pending") or {}
                    phase_name = "retry_intent" if retry else "intent"
                    if pending.get("service") == "set_temperature" and pending.get("phase") == phase_name:
                        controller.after_persist = None
                        edge_at.append(controller.now)
                        controller.availability_event("off")
                        controller.availability_event("heat")
                runtime.after_persist = coalesce
                await runtime.evaluate(30 if retry else 0)
                self.assertIsNone(runtime.after_persist)
                self.assertEqual(production.snapshot(runtime.state), before,
                                 "The final snapshot alone cannot reveal this real OFF/ON transition")
                self.assertEqual(len(runtime.calls), 1 if retry else 0)
                self.assertIn(PRIMARY, getattr(runtime, "_native_on_epoch", {}))
                self.assertEqual(runtime._native_on_epoch[PRIMARY], edge_at[0])
                if retry:
                    self.assertEqual(runtime.record["pending"]["attempts"], 1)
                else:
                    await runtime.evaluate(29.999)
                    self.assertEqual(runtime.calls, [])
                    await runtime.evaluate(0.001)
                    self.assertEqual(len(runtime.calls), 1)
                    self.assertGreaterEqual(runtime.call_times[-1] - edge_at[0], 30)

    async def test_coalesced_off_on_during_stop_persistence_cannot_turn_new_episode_off(self):
        for final_leg in (False, True):
            with self.subTest(final_leg=final_leg):
                runtime = SequenceRuntime()
                runtime.running_extreme()
                runtime.open_window()
                if final_leg:
                    await runtime.evaluate()
                    self.assert_reverse_target(runtime)
                before = production.snapshot(runtime.state)
                def coalesce(controller):
                    pending = controller.record.get("pending") or {}
                    marker = "stop_finish" if final_leg else "stop_target"
                    if pending.get(marker) and pending.get("phase") == "intent":
                        controller.after_persist = None
                        controller.availability_event("off")
                        controller.availability_event("heat")
                runtime.after_persist = coalesce
                await runtime.evaluate(30 if final_leg else 0)
                self.assertIsNone(runtime.after_persist)
                self.assertEqual(production.snapshot(runtime.state), before)
                self.assertEqual(len(runtime.calls), 1 if final_leg else 0)
                self.assertFalse(any(call["data"] == {"hvac_mode": "off"} for call in runtime.calls))
                await runtime.evaluate(30)
                self.assertEqual(len(runtime.calls), 1 if final_leg else 0,
                                 "The new ON episode still requires its own minimum-ON dwell")

    async def test_invalidated_stop_survives_cold_rehydration_and_needs_explicit_reconciliation(self):
        original = SequenceRuntime()
        original.running_extreme()
        original.open_window()
        await original.evaluate()
        def coalesce(controller):
            pending = controller.record.get("pending") or {}
            if pending.get("stop_finish") and pending.get("phase") == "intent":
                controller.after_persist = None
                controller.availability_event("off")
                controller.availability_event("heat")
        original.after_persist = coalesce
        await original.evaluate(30)
        self.assertIsNone(original.after_persist)
        edge = original._native_on_epoch[PRIMARY]
        await original.evaluate()
        self.assertEqual(original.record["native_setpoint_stop"]["invalidated_on_epoch"], edge)
        self.assertEqual(original.record["power"][PRIMARY]["since"], edge)
        self.assertEqual(original.record["native_power_observations"][PRIMARY]["since"], edge)
        runtime = self.rehydrate_stop(original, elapsed=120)
        self.assertFalse(getattr(runtime, "_native_on_epoch", {}), "Only the durable journal survives")
        await runtime.evaluate()
        self.assertEqual(runtime.calls, [], "No stale OFF during the new minimum-ON interval")
        await runtime.evaluate(600)
        self.assertEqual(runtime.calls, [], "Elapsed dwell does not revive a stop from an earlier ON episode")
        self.assertEqual(runtime.record["native_setpoint_stop"]["invalidated_on_epoch"], edge)

    async def test_deadline_callback_only_schedules_and_busy_run_retains_the_wakeup(self):
        runtime = SequenceRuntime()
        runtime.manager.settings["kp"] = 100.0
        await runtime.evaluate()
        runtime.report(mode="heat")
        await runtime.evaluate()
        self.assertEqual(len(runtime.calls), 1)
        self.assertTrue(runtime.timer_loop.handles)
        runtime.now += 30
        runtime._tasks[SPEC.identifier] = asyncio.current_task()
        runtime.timer_loop.fire_due()
        self.assertEqual(len(runtime.calls), 1, "The timer cannot dispatch directly")
        self.assertIn(SPEC.identifier, runtime._setpoint_rerun)
        token = CURRENT_LOOP.set(runtime.timer_loop)
        try:
            await runtime._run(SPEC)
        finally:
            CURRENT_LOOP.reset(token)
        self.assertEqual(len(runtime.calls), 2)
        self.assertNotIn(SPEC.identifier, runtime._setpoint_rerun)
        self.assertGreater(runtime.scheduled_evaluations, 0)
        self.assertNotEqual(runtime.record.get("paused"), "controller_exception")


if __name__ == "__main__":
    unittest.main(verbosity=2)

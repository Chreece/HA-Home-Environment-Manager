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
sequence.asyncio = N(
    get_running_loop=lambda: CURRENT_LOOP.get() or asyncio.get_running_loop(),
    create_task=asyncio.create_task,
)


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
        self._native_on_epoch = {}
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


def seed_legacy_stop(runtime, *, phase="commanded", off_pending=False, age=900.0):
    """Persist the exact pre-b9 shape; no current runtime creates this record."""
    runtime.running_extreme(age)
    owned = runtime.record["power"][PRIMARY]
    at = runtime.now
    sequence_data = {
        "version": 1, "entity": PRIMARY, "source_device_id": SPEC.source_device_id,
        "area": SPEC.area_id, "mode": runtime.state.state,
        "temperature": runtime.original_target, "phase": "off_pending" if off_pending else "waiting",
        "requested_at": at, "owned": True, "owned_since": owned["since"],
        "sent_at": at, "off_not_before": at + 30.0,
    }
    data = {"hvac_mode": "off"} if off_pending else {"temperature": runtime.original_target}
    journal = {
        "entity": PRIMARY, "service": "set_hvac_mode" if off_pending else "set_temperature",
        "data": data, "expected": {"state": "off"} if off_pending else {"attributes": data},
        "power": off_pending, "output_on": not off_pending, "phase": phase,
        "when": at, "last_attempt_at": at, "attempts": 2,
        "min_on": owned["min_on"], "max_on": owned["max_on"],
        "stop_target": not off_pending, "stop_finish": off_pending,
        "stop_sequence_at": at, "retry_policy": "automatic_minute",
        "retry_context": {
            "settings": deepcopy(model.settings(runtime.manager, SPEC)), "profile": None,
            "automatic": False, "mode": "off", "shutdown": True,
            "policy_stop": None, "upstream_owned": None,
        },
    }
    runtime.record["native_setpoint_stop"] = sequence_data
    runtime.record["pending"] = journal
    return deepcopy(journal)


class SetpointSequenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_binary_start_target_is_immediate_after_native_on_ack(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode):
                    r = SequenceRuntime(method, mode)
                    r.manager.settings["kp"] = 100.0
                    r.manager.settings["timed_setpoint_sequence"] = True
                    await r.evaluate()
                    self.assertEqual(r.calls[-1]["data"], {"hvac_mode": mode})
                    self.assertFalse(r.record["power"])
                    await r.evaluate(5)
                    self.assertEqual(len(r.calls), 1)
                    r.report(mode=mode)
                    ack_at = r.now
                    await r.evaluate()
                    self.assertEqual(len(r.calls), 2)
                    self.assertEqual(r.calls[-1]["data"], {"temperature": r.requested_target})
                    self.assertEqual(r.call_times[-1], ack_at)
                    self.assertEqual(r.record["power"][PRIMARY]["since"], ack_at)
                    r.report(temperature=r.requested_target)
                    await r.evaluate()
                    self.assertIsNone(r.record["pending"])

    async def test_all_shutdown_entrypoints_use_guarded_direct_off(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                for stop in ("idle", "window", "sleep", "explicit_off", "retired"):
                    with self.subTest(method=method, mode=mode, stop=stop):
                        r = SequenceRuntime(method, mode)
                        r.running_extreme()
                        if stop == "idle":
                            r.measurement = 23.0 if mode == "heat" else 24.0
                        elif stop == "window":
                            r.open_window()
                        elif stop == "sleep":
                            r.sleeping = True
                            r.manager.device["sleep_behavior"] = "pause"
                        elif stop == "explicit_off":
                            r.manager.settings["control_mode"] = "off"
                        elif stop == "retired":
                            r._current_spec = lambda spec: False
                        await r.evaluate()
                        self.assertEqual(len(r.calls), 1, r.statuses)
                        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
                        self.assertTrue(r.record["pending"]["power"])
                        self.assertNotIn("native_setpoint_stop", r.record)
                        self.assertIn(PRIMARY, r.record["power"])
                        r.report(mode="off")
                        await r.evaluate()
                        self.assertNotIn(PRIMARY, r.record["power"])

    async def test_minimum_on_and_maximum_on_have_no_target_timing_offsets(self):
        r = SequenceRuntime("automatic")
        r.running_extreme(age=599.999)
        r.open_window()
        await r.evaluate()
        self.assertFalse(r.calls)
        self.assertEqual(r.statuses[-1][0], "minimum_on_hold")
        await r.evaluate(.001)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
        r = SequenceRuntime("automatic", "cool")
        r.running_extreme(age=7169)
        await r.evaluate()
        await r.evaluate(1)
        await r.evaluate(29.999)
        self.assertFalse(r.calls)
        await r.evaluate(.001)
        self.assertEqual(r.calls[-1]["data"], {"hvac_mode": "off"})
        self.assertEqual(r.now - r.record["power"][PRIMARY]["since"], 7200)

    async def test_soft_manual_range_and_humidity_targets_have_no_start_delay(self):
        for service, data in (("set_temperature", {"temperature": 22.}),
                              ("set_temperature", {"target_temp_low": 18., "target_temp_high": 25.}),
                              ("set_humidity", {"humidity": 45.})):
            with self.subTest(service=service, data=data):
                r = SequenceRuntime("manual")
                r.manager.power_grant = False
                r.state.attributes.update(supported_features=7, humidity=60.,
                                          target_temp_low=17., target_temp_high=26.)
                r.report(mode="heat")
                self.assertTrue(await r.command(service, data))
                self.assertEqual(r.call_times[-1], r.state.last_changed.timestamp())
                self.assertFalse(r.record["power"])

    async def test_direct_off_keeps_uncertain_service_and_minute_retry_history(self):
        r = SequenceRuntime("automatic")
        r.running_extreme()
        r.open_window()
        original = r.service_call
        async def timeout(*args, **kwargs):
            await original(*args, **kwargs)
            raise TimeoutError("native did not acknowledge")
        r.hass.services.async_call = timeout
        await r.evaluate()
        first = deepcopy(r.record["pending"])
        self.assertEqual(first["phase"], "commanded")
        self.assertEqual(first["service_error"], "native_command_failed_or_uncertain")
        self.assertFalse(r.record.get("paused"))
        await r.evaluate(59.999)
        self.assertEqual(len(r.calls), 1)
        await r.evaluate(.001)
        self.assertEqual(len(r.calls), 2)
        self.assertEqual(r.record["pending"]["attempts"], 2)
        self.assertEqual(r.record["pending"]["when"], first["when"])
        self.assertIn(PRIMARY, r.record["power"])

    async def test_unsent_off_rechecks_window_and_source_after_persistence(self):
        for change in ("window", "source"):
            with self.subTest(change=change):
                r = SequenceRuntime("automatic")
                r.running_extreme()
                r.open_window()
                def changed(controller):
                    if (controller.record.get("pending") or {}).get("phase") == "intent":
                        controller.after_persist = None
                        if change == "window":
                            controller.close_window()
                        else:
                            controller.registered_device_id = "replacement"
                r.after_persist = changed
                await r.evaluate()
                self.assertFalse(r.calls)
                self.assertIsNone(r.record.get("pending"))
                self.assertIn(PRIMARY, r.record["power"])

    async def test_new_on_epoch_during_stop_persistence_aborts_old_owned_off(self):
        r = SequenceRuntime("automatic")
        r.running_extreme()
        r.open_window()
        def changed(controller):
            if (controller.record.get("pending") or {}).get("phase") == "intent":
                controller.after_persist = None
                controller._native_on_epoch[PRIMARY] = controller.now
        r.after_persist = changed
        await r.evaluate()
        self.assertFalse(r.calls)
        self.assertIn(PRIMARY, r.record["power"])

    async def test_retry_deadline_only_requests_locked_evaluation(self):
        r = SequenceRuntime()
        r.running_extreme()
        r.open_window()
        await r.evaluate()
        self.assertEqual(len(r.calls), 1)
        r.now += 60
        r.timer_loop.fire_due()
        self.assertEqual(len(r.calls), 1, "Timer callback never dispatches")
        self.assertGreater(r.scheduled_evaluations, 0)
        sequence.cancel_wakeups(r)
        self.assertFalse(r._setpoint_wakeups)


if __name__ == "__main__":
    unittest.main(verbosity=2)

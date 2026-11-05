"""Live target crossings must override cached PID output and stale commands.

This executes the production capability model, PID calculation, tick, native
dispatch/ACK/retry and optional setpoint sequence. Only Home Assistant transport,
source identity, independent room measurements, storage and time are fixtures.
No physical valve position or acknowledgement is inferred from a service return.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta109_setpoint_sequence.py"))
SequenceRuntime, model, production, fixture, phase = (
    base[key] for key in ("SequenceRuntime", "model", "production", "fixture", "phase")
)
allocator = fixture["load_pure"]("pid_output_allocator", "pid_output_allocator.py")
for name in ("fan_speed_for_pid", "ordered_fan_stages", "percentage_output_requested"):
    setattr(production, name, getattr(allocator, name))
fixture["extract"](fixture["RUNTIME"], ("_status",), production.__dict__)
status_scope = {"equipment": model}
fixture["extract"](ROOT / "equipment_status.py", ("extra_state_attributes",), status_scope)


class CutoffRuntime(SequenceRuntime):
    """Use the same production runtime for real climate/humidifier/valve domains."""

    def __init__(self, kind="heat", *, method="pid", timed=False):
        mode = "auto" if kind == "humidify" else "dry" if kind == "dehumidify" else kind
        if kind == "valve":
            mode = "heat"
        super().__init__(method, mode)
        self.kind, self.mode = kind, mode
        domain = ("humidifier" if kind in ("humidify", "dehumidify")
                  else "number" if kind == "valve" else "climate")
        self.primary = f"{domain}.native_thermostat"
        self.spec = N(identifier="binary_controller", area_id="room",
                      source_device_id="thermostat", source_entities=(self.primary,))
        self.metric = "humidity" if kind in ("dry", "humidify", "dehumidify") else "temperature"
        self.increasing = kind in ("heat", "humidify", "valve")
        self.goal = 50. if self.metric == "humidity" else 26. if mode == "cool" else 21.
        self.measurement = self.goal + (-3. if self.increasing else 3.)
        self.manager.settings["timed_setpoint_sequence"] = timed
        self.state.domain = domain
        if domain == "humidifier":
            self.state.attributes = {
                "device_class": "humidifier" if self.increasing else "dehumidifier",
                "humidity": 50., "min_humidity": 20., "max_humidity": 80.,
                "supported_features": 0,
            }
        elif domain == "number":
            self.state.state = "0.0"
            self.state.attributes = {"unit_of_measurement": "%", "min": 0,
                                     "max": 100, "step": 1}
            self.manager.room["heat_actuator"] = self.primary
        elif kind == "dry":
            self.state.attributes = {
                "hvac_modes": ["off", "dry"], "humidity": 50.,
                "min_humidity": 20., "max_humidity": 80.,
                "supported_features": 4, "hvac_action": "idle",
            }
        self.hass.states.get = lambda entity: self.state if entity == self.primary else None
        self.record = {"sources": [self.primary], "source_device_id": self.spec.source_device_id,
                       "area": self.spec.area_id, "power": {}, "baseline": {},
                       "off_at": {}, "pending": None, "upstream": {}}
        self.records = {self.spec.identifier: self.record}
        self._native_ready_since = {self.primary: self.now - 30.}
        self._native_settled_for = {(self.spec.identifier, self.primary): self.now - 30.}
        self._native_session_observations = {}

    def measurements(self, spec, cap):
        return {"temperature": self.measurement if self.metric == "temperature" else 22.,
                "humidity": self.measurement if self.metric == "humidity" else 50.,
                "pm25": None, "co2": None}

    async def evaluate(self, advance=0.):
        self.now += advance
        token = base["CURRENT_LOOP"].set(self.timer_loop)
        try:
            self.timer_loop.fire_due()
            await self.tick(self.spec)
            while self.queued_tasks:
                tasks, self.queued_tasks = self.queued_tasks, []
                await asyncio.gather(*tasks)
        finally:
            base["CURRENT_LOOP"].reset(token)

    def own(self, *, age=900., extreme=True):
        self.state.state = ("50.0" if self.kind == "valve" else self.mode
                            if self.state.domain == "climate" else "on")
        self.state.last_changed = datetime.fromtimestamp(self.now - age, timezone.utc)
        if extreme and self.kind in ("heat", "cool"):
            self.state.attributes["temperature"] = 30. if self.increasing else 5.
        self.record["power"][self.primary] = {
            "since": self.now - age, "min_on": 600., "max_on": 7200.,
        }
        self.record["baseline"][self.primary] = production.snapshot(self.state)
        self.record["native_power_observations"] = {
            self.primary: {"state": "on", "since": self.now - age},
        }
        self._native_session_observations[(self.spec.identifier, self.primary)] = "on"
        self.record["capabilities"] = asdict(model.capabilities(self.manager, self.spec))

    def seed_residual(self, *, sample_age=1., integral=80., demand=90.):
        """A real previous PID sample, before the room reached its target."""
        cfg = self.manager.settings
        signature, _, _ = phase.phase_decision(
            None, metric=self.metric, target=self.goal, increasing=self.increasing,
            profile=model.profile_name(cfg, self.manager.plan), mode=self.mode,
            preset=cfg["preset"], kp=cfg["kp"], ki=cfg["ki"], kd=cfg["kd"],
            cycle_s=cfg["cycle_seconds"], min_on_s=600., min_off_s=600.,
            measured=self.goal + (-3. if self.increasing else 3.),
        )
        memory = model.PIDMemory(
            integral=integral, measured=self.goal + (-3. if self.increasing else 3.),
            stamp=self.now - sample_age, derivative=0., demand=demand,
        )
        self._memory[self.spec.identifier] = signature, memory, self.now - 100.

    async def dispatch(self, service, data, *, power=False, mode=None):
        expected = ({"state": mode} if power and self.state.domain == "climate"
                    else {"attributes": data})
        cap = model.capabilities(self.manager, self.spec)
        return await self._send(self.spec, cap, self.primary, service, data, expected,
                                power=power, mode=mode, automatic=True)


@contextmanager
def endpoint(kind="heat", **kwargs):
    runtime = CutoffRuntime(kind, **kwargs)
    with ExitStack() as stack:
        stack.enter_context(patch.object(model, "configured_sources", lambda *_: (runtime.primary,)))
        stack.enter_context(patch.object(production, "configured_sources", lambda *_: (runtime.primary,)))
        stack.enter_context(patch.object(production, "entity_area", lambda _, entity:
            runtime.spec.area_id if entity == runtime.primary else None))
        stack.enter_context(patch.object(fixture["registry"], "async_get", lambda hass:
            N(async_get=lambda entity: N(platform="native_fixture", device_id=runtime.registered_device_id)
              if entity == runtime.primary else None)))
        yield runtime


def calls(runtime):
    return [(c["service"], c["data"]) for c in runtime.calls]


def off(runtime):
    if runtime.state.domain == "climate":
        return "set_hvac_mode", {"hvac_mode": "off"}
    if runtime.state.domain == "number":
        return "set_value", {"value": 0.}
    return "turn_off", {}


class PIDTargetCutoffTests(unittest.IsolatedAsyncioTestCase):
    def assert_no_residual(self, runtime):
        saved = runtime._memory.get(runtime.spec.identifier)
        if saved is not None:
            self.assertEqual(saved[1].demand, 0., "Satisfied demand must not retain a cached ON pulse")
            self.assertEqual(saved[1].integral, 0., "Prior positive integral must not reopen output")

    async def test_satisfied_target_never_starts_output_from_cached_positive_pid(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify", "valve"):
            for overshoot in (0., .1, 1.1):
                with self.subTest(kind=kind, overshoot=overshoot), endpoint(kind) as r:
                    r.seed_residual()
                    r.measurement = r.goal + (overshoot if r.increasing else -overshoot)
                    await r.evaluate()
                    self.assertEqual(calls(r), [], r.statuses)
                    self.assert_no_residual(r)
                    self.assertFalse(r.record.get("pending"))
                    self.assertFalse(r.record.get("paused"))

    async def test_target_crossing_breaks_running_pwm_before_next_pid_sample(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify", "valve"):
            for overshoot in (0., .1, 1.1):
                with self.subTest(kind=kind, overshoot=overshoot), endpoint(kind) as r:
                    r.own()
                    r.seed_residual()
                    r.measurement = r.goal + (overshoot if r.increasing else -overshoot)
                    await r.evaluate()
                    self.assertEqual(calls(r), [off(r)], r.statuses)
                    self.assert_no_residual(r)
                    self.assertIn(r.primary, r.record["power"], "OFF dispatch is not physical OFF feedback")
                    self.assertEqual(r.record["pending"]["phase"], "commanded")
                    self.assertFalse(r.record.get("paused"))

    async def test_explicit_direction_does_not_depend_on_the_other_thermal_target(self):
        for kind, value, other_key, other_target in (
            ("heat", 22.1, "cool", 22.),
            ("heat", 35., "cool", 26.),
            ("cool", 24.9, "heat", 25.),
            ("cool", 15., "heat", 21.),
        ):
            with self.subTest(kind=kind, value=value), endpoint(kind) as r:
                r.manager.targets[other_key] = other_target
                r.own()
                r.seed_residual()
                r.measurement = value
                await r.evaluate()
                self.assertEqual(calls(r), [off(r)], r.statuses)
                self.assert_no_residual(r)

    async def test_cutoff_respects_native_minimum_on_but_drops_pid_demand_immediately(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.own(age=100.)
                r.seed_residual()
                r.measurement = r.goal
                await r.evaluate()
                self.assertEqual(calls(r), [])
                self.assert_no_residual(r)
                self.assertEqual(r.statuses[-1][0], "minimum_on_hold")
                await r.evaluate(499.999)
                self.assertEqual(calls(r), [])
                await r.evaluate(.001)
                self.assertEqual(calls(r), [off(r)], r.statuses)

    async def test_opted_in_stop_still_prepares_opposite_target_then_waits_30_seconds(self):
        for kind in ("heat", "cool"):
            with self.subTest(kind=kind), endpoint(kind, timed=True) as r:
                r.own()
                r.seed_residual()
                r.measurement = r.goal
                await r.evaluate()
                reverse = ("set_temperature", {"temperature": 5. if r.increasing else 30.})
                self.assertEqual(calls(r), [reverse], r.statuses)
                self.assert_no_residual(r)
                self.assertIn("native_setpoint_stop", r.record)
                await r.evaluate(29.999)
                self.assertEqual(calls(r), [reverse])
                await r.evaluate(.001)
                self.assertEqual(calls(r), [reverse, off(r)], r.statuses)
                self.assertEqual(r.call_times[-1] - r.call_times[0], 30.)

    async def test_lowered_heat_or_raised_cool_target_cancels_existing_cycle(self):
        for kind in ("heat", "cool"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.own()
                r.seed_residual()
                r.measurement = r.goal + (-.5 if r.increasing else .5)
                r.manager.targets[kind] = r.goal + (-1. if r.increasing else 1.)
                await r.evaluate()
                self.assertEqual(calls(r), [off(r)], r.statuses)
                self.assert_no_residual(r)

    async def test_soft_only_pid_removes_boost_without_acquiring_power_permission(self):
        for kind in ("heat", "cool"):
            for overshoot in (0., 1.1):
                with self.subTest(kind=kind, overshoot=overshoot), endpoint(kind) as r:
                    r.manager.power_grant = False
                    r.state.state = r.mode
                    # One previously applied PID trim step, so the ordinary
                    # native setpoint rate limit can remove it in this sample.
                    r.state.attributes["temperature"] = r.goal + (.5 if r.increasing else -.5)
                    r.state.last_changed = datetime.fromtimestamp(r.now - 900., timezone.utc)
                    r.record["baseline"][r.primary] = production.snapshot(r.state)
                    r.seed_residual()
                    r.measurement = r.goal + (overshoot if r.increasing else -overshoot)
                    await r.evaluate()
                    self.assertEqual(calls(r), [("set_temperature", {"temperature": r.goal})], r.statuses)
                    self.assertFalse(r.record["power"])
                    self.assertFalse(r.manager.power_grant)
                    self.assert_no_residual(r)

    async def test_soft_only_large_boost_is_reduced_in_existing_bounded_steps(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.manager.power_grant = False
                r.state.state = r.mode if r.state.domain == "climate" else "on"
                r.state.last_changed = datetime.fromtimestamp(r.now - 900., timezone.utc)
                key = "temperature" if r.metric == "temperature" else "humidity"
                step = .5 if r.metric == "temperature" else 5.
                sign = 1. if r.increasing else -1.
                r.state.attributes[key] = r.goal + 3 * step * sign
                r.record["baseline"][r.primary] = production.snapshot(r.state)
                r.measurement = r.goal
                r.seed_residual()
                expected = []
                for index in range(3):
                    await r.evaluate(0. if index == 0 else 300.)
                    value = r.goal + (2 - index) * step * sign
                    expected.append(("set_temperature" if key == "temperature" else "set_humidity",
                                     {key: value}))
                    self.assertEqual(calls(r), expected, r.statuses)
                    self.assertFalse(r.record["power"])
                    self.assert_no_residual(r)
                    r.state.attributes[key] = value  # Actual source feedback, never a service side effect.
                self.assertFalse(r.manager.power_grant)

    async def test_unboosted_correction_keeps_its_ack_and_bounded_retry_lifecycle(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.manager.power_grant = False
                r.state.state = r.mode if r.state.domain == "climate" else "on"
                r.state.last_changed = datetime.fromtimestamp(r.now - 900., timezone.utc)
                key = "temperature" if r.metric == "temperature" else "humidity"
                step = .5 if key == "temperature" else 5.
                r.state.attributes[key] = r.goal + (step if r.increasing else -step)
                r.record["baseline"][r.primary] = production.snapshot(r.state)
                r.measurement = r.goal
                r.seed_residual()
                await r.evaluate()
                original = deepcopy(r.record["pending"])
                command = (original["service"], original["data"])
                self.assertEqual(original["data"], {key: r.goal})
                for attempt in (2, 3, 4):
                    await r.evaluate(30.)
                    self.assertEqual(calls(r), [command] * attempt, r.statuses)
                    self.assertEqual(r.record["pending"]["attempts"], attempt)
                    self.assertNotIn("unconfirmed_native_target", r.record,
                                     "A reducing correction must not be retired as obsolete active output")
                    self.assertFalse(r.record["power"])
                    self.assertFalse(r.record.get("paused"))
                r.state.attributes[key] = r.goal
                await r.evaluate(1.)
                self.assertIsNone(r.record["pending"])
                self.assertEqual(len(r.calls), 4)
                self.assert_no_residual(r)

    async def cross_at_yield(self, runtime, stage, *, pending_phase="intent"):
        """Change only the independent room measurement while Store/lock yields."""
        intent = asyncio.Event()

        def after_save(controller):
            pending = controller.record.get("pending") or {}
            if pending.get("phase") == pending_phase:
                controller.after_persist = None
                if stage == "intent_save":
                    controller.measurement = controller.goal
                intent.set()

        runtime.after_persist = after_save
        if stage == "intent_save":
            await runtime.evaluate()
        else:
            await runtime._commands.acquire()
            task = asyncio.create_task(runtime.evaluate())
            try:
                await asyncio.wait_for(intent.wait(), timeout=2)
                runtime.measurement = runtime.goal
            finally:
                runtime._commands.release()
            await task
        self.assertTrue(intent.is_set(), "The intended persistence/dispatch boundary must be exercised")
        self.assertIsNone(runtime.after_persist)

    async def test_fresh_on_is_cancelled_when_target_crosses_during_dispatch_yields(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            for stage in ("intent_save", "semaphore"):
                with self.subTest(kind=kind, stage=stage), endpoint(kind) as r:
                    r.seed_residual()
                    await self.cross_at_yield(r, stage)
                    self.assertEqual(calls(r), [])
                    self.assertFalse(r.record.get("pending"), "A proven unsent ON must not become uncertain")
                    self.assertFalse(r.record["power"])
                    self.assertFalse(r.record.get("paused"))
                    await r.evaluate()
                    self.assertEqual(calls(r), [])
                    self.assert_no_residual(r)

    async def test_active_target_or_valve_raise_is_cancelled_at_each_dispatch_yield(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify", "valve"):
            for stage in ("intent_save", "semaphore"):
                with self.subTest(kind=kind, stage=stage), endpoint(kind) as r:
                    if r.metric == "humidity":
                        r.state.attributes["humidity"] = 35. if r.increasing else 65.
                    r.own(extreme=False)
                    r.seed_residual()
                    await self.cross_at_yield(r, stage)
                    self.assertEqual(calls(r), [])
                    self.assertFalse(r.record.get("pending"))
                    self.assertFalse(r.record.get("paused"))
                    await r.evaluate()
                    self.assertEqual(calls(r), [off(r)], r.statuses)
                    self.assert_no_residual(r)

    async def test_unacknowledged_active_target_does_not_block_satisfied_owned_shutdown(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                if r.metric == "humidity":
                    r.state.attributes["humidity"] = 35. if r.increasing else 65.
                r.own(extreme=False)
                r.seed_residual()
                await r.evaluate()
                self.assertEqual(len(r.calls), 1, r.statuses)
                initial = deepcopy(r.record["pending"])
                self.assertEqual(initial["attempts"], 1)
                self.assertFalse(initial["power"])
                r.measurement = r.goal
                await r.evaluate(1.)
                if len(r.calls) == 1:
                    await r.evaluate()
                self.assertEqual(calls(r), [(initial["service"], initial["data"]), off(r)], r.statuses)
                self.assertEqual(r.record["pending"]["expected"],
                                 {"state": "off"}, "A new OFF journal must be distinct from target ACK")
                ledger = r.record.get("unconfirmed_native_target")
                self.assertIsInstance(ledger, dict)
                for field in ("entity", "service", "data", "expected", "when", "attempts", "last_attempt_at"):
                    self.assertEqual(ledger[field], initial[field], field)
                self.assertIn(r.primary, r.record["power"])
                self.assertFalse(r.record.get("paused"))
                self.assert_no_residual(r)

    async def test_pending_on_is_not_reissued_after_target_reached_and_late_ack_is_respected(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.seed_residual()
                await r.evaluate()
                self.assertEqual(len(r.calls), 1, r.statuses)
                original = deepcopy(r.record["pending"])
                self.assertTrue(original["power"])
                r.measurement = r.goal
                await r.evaluate(30.)
                self.assertEqual(len(r.calls), 1, "Do not repeat an ON that is no longer needed")
                self.assertFalse(r.record["power"], "Absent physical ON feedback grants no ownership")
                self.assertIsNotNone(r.record.get("pending"), "Do not invent an ACK to clear the old ON")
                self.assertEqual(r.record["pending"]["attempts"], 1)
                self.assertEqual(r.manager.settings["control_mode"], "pid")
                self.assert_no_residual(r)
                self.assertIsInstance(r.record.get("automatic_continue_requested"), dict)
                await r.evaluate(1.)
                self.assertGreater(r.created_recovery_tasks, 0,
                                   "The real read-only automatic reconciliation must execute")
                self.assertEqual(len(r.calls), 1)
                # The already-sent command may still really complete. Observe
                # that ON, then enforce actual minimum-ON before normal OFF.
                r.report(mode=r.mode if r.state.domain == "climate" else "on")
                ack_at = r.now
                await r.evaluate()
                self.assertEqual(len(r.calls), 1)
                self.assertIn(r.primary, r.record["power"], r.statuses)
                self.assertEqual(r.record["power"][r.primary]["since"], ack_at)
                await r.evaluate(599.999)
                self.assertEqual(len(r.calls), 1)
                await r.evaluate(.001)
                self.assertEqual(calls(r)[-1], off(r), r.statuses)
                self.assertEqual(len(r.calls), 2, "A late ON must never be followed by an active max/min target")

    async def test_pending_on_without_ack_reconciles_stable_off_without_resending(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.seed_residual()
                await r.evaluate()
                self.assertEqual(len(r.calls), 1)
                requested_at = r.now
                r.measurement = r.goal
                await r.evaluate(30.)
                self.assertIsInstance(r.record.get("automatic_continue_requested"), dict)
                await r.evaluate(90.)
                self.assertIsNotNone(r.record.get("pending"),
                                     "One unchanged OFF observation is not an acknowledgement")
                await r.evaluate(60.)
                self.assertEqual(r.now - requested_at, 180.)
                self.assertGreaterEqual(r.created_recovery_tasks, 2)
                self.assertIsNone(r.record.get("pending"), r.statuses)
                self.assertIsNone(r.record.get("automatic_continue_requested"))
                self.assertEqual(r.record["last_resume_reconciliation"]["method"], "stable_native_state")
                self.assertFalse(r.record["power"])
                self.assertFalse(r.record.get("paused"))
                self.assertEqual(r.manager.settings["control_mode"], "pid")
                self.assertEqual(len(r.calls), 1, "Read-only verification sends neither another ON nor a fabricated OFF")

    async def test_returning_demand_continues_original_budget_before_minimum_on_finishes(self):
        for kind in ("heat", "cool"):
            for attempts in (1, 2, 3, 4):
                with self.subTest(kind=kind, attempts=attempts), endpoint(kind) as r:
                    r.own(age=100., extreme=False)
                    r.seed_residual()
                    await r.evaluate()
                    for _ in range(1, attempts):
                        await r.evaluate(30.)
                    original = deepcopy(r.record["pending"])
                    self.assertEqual(original["attempts"], attempts)
                    self.assertEqual(len(r.calls), attempts)
                    r.measurement = r.goal
                    await r.evaluate(1.)
                    self.assertEqual(len(r.calls), attempts, "Physical minimum ON remains in force")
                    self.assertIsNone(r.record.get("pending"))
                    self.assertEqual(r.record["unconfirmed_native_target"]["attempts"], attempts)
                    self.assert_no_residual(r)
                    r.measurement = r.goal + (-1. if r.increasing else 1.)
                    await r.evaluate(29.)
                    if attempts < 4:
                        self.assertEqual(len(r.calls), attempts + 1, r.statuses)
                        pending = r.record["pending"]
                        self.assertEqual(pending["attempts"], attempts + 1)
                        self.assertEqual(pending["when"], original["when"])
                        self.assertEqual(pending["data"], original["data"])
                        self.assertEqual(pending["expected"], original["expected"])
                        self.assertNotIn("unconfirmed_native_target", r.record)
                    else:
                        for _ in range(3):
                            await r.evaluate(30.)
                            self.assertEqual(len(r.calls), 4,
                                             "A target crossing cannot grant a fifth attempt without a real reconnect")
                        self.assertEqual(r.record["unconfirmed_native_target"]["attempts"], 4)
                    self.assertFalse(r.record.get("paused"))

    async def test_pending_fan_boost_cannot_hold_an_owned_heater_on_after_target_reached(self):
        with endpoint("heat") as r:
            r.state.attributes.update(supported_features=9,
                                      fan_modes=["low", "medium", "high"], fan_mode="low")
            r.own()
            r.seed_residual()
            await r.evaluate()
            self.assertEqual(calls(r), [("set_fan_mode", {"fan_mode": "high"})], r.statuses)
            original = deepcopy(r.record["pending"])
            r.measurement = r.goal
            await r.evaluate(1.)
            if len(r.calls) == 1:
                await r.evaluate()
            self.assertEqual(calls(r), [("set_fan_mode", {"fan_mode": "high"}), off(r)], r.statuses)
            ledger = r.record.get("unconfirmed_native_target")
            self.assertIsInstance(ledger, dict, "Keep unconfirmed adjustment evidence separate from OFF")
            for field in ("entity", "service", "data", "expected", "when", "attempts", "last_attempt_at"):
                self.assertEqual(ledger[field], original[field], field)
            self.assertFalse(r.record.get("paused"))
            self.assert_no_residual(r)

    async def test_late_or_partial_target_feedback_during_retirement_does_not_restart_dwell(self):
        for kind in ("heat", "cool"):
            for feedback in ("complete", "partial", "genuine_off_on"):
                with self.subTest(kind=kind, feedback=feedback), endpoint(kind) as r:
                    r.own(age=900., extreme=False)
                    r.seed_residual()
                    started = r.record["power"][r.primary]["since"]
                    await r.evaluate()
                    initial = deepcopy(r.record["pending"])
                    self.assertEqual(len(r.calls), 1)

                    def native_report_during_save(controller):
                        if (controller.record.get("unconfirmed_native_target")
                                and controller.record.get("pending") is None):
                            controller.after_persist = None
                            if feedback == "genuine_off_on":
                                controller.availability_event("off")
                                controller.availability_event(controller.mode)
                            value = (initial["data"]["temperature"] if feedback != "partial"
                                     else 20. if kind == "heat" else 27.)
                            controller.report(temperature=value)

                    r.after_persist = native_report_during_save
                    r.measurement = r.goal
                    await r.evaluate(1.)
                    self.assertIsNone(r.after_persist, "Native report must arrive during retirement persistence")
                    if feedback == "genuine_off_on":
                        self.assertEqual(len(r.calls), 1, "A genuinely new ON keeps its own minimum ON")
                        self.assertEqual(r._native_on_epoch[r.primary], r.now)
                        self.assertEqual(r.record["power"][r.primary]["since"], r.now)
                        await r.evaluate(599.999)
                        self.assertEqual(len(r.calls), 1)
                        await r.evaluate(.001)
                    else:
                        self.assertEqual(r.record["power"][r.primary]["since"], started,
                                         "A setpoint attribute report is not another physical ON episode")
                    self.assertEqual(calls(r), [(initial["service"], initial["data"]), off(r)], r.statuses)
                    self.assertFalse(r.record.get("paused"))
                    self.assert_no_residual(r)

    async def test_pending_percentage_raise_yields_to_zero_without_restarting_native_dwell(self):
        for feedback in (None, 55., 60.):
            with self.subTest(feedback=feedback), endpoint("valve") as r:
                r.own(age=900.)
                r.seed_residual()
                started = r.record["power"][r.primary]["since"]
                await r.evaluate()
                self.assertEqual(calls(r), [("set_value", {"value": 60.})], r.statuses)
                original = deepcopy(r.record["pending"])
                self.assertTrue(original["power"])
                self.assertEqual(r.state.state, "50.0", "Dispatch is not native feedback")

                def native_report_during_save(controller):
                    if (controller.record.get("unconfirmed_native_target")
                            and controller.record.get("pending") is None):
                        controller.after_persist = None
                        controller.report(mode=str(feedback))

                if feedback is not None:
                    r.after_persist = native_report_during_save
                r.measurement = r.goal
                await r.evaluate(1.)
                self.assertEqual(calls(r), [("set_value", {"value": 60.}), off(r)], r.statuses)
                self.assertIsNone(r.after_persist)
                self.assertEqual(r.record["power"][r.primary]["since"], started,
                                 "An amplitude change is not a new physical ON episode")
                self.assertEqual(r.record["pending"]["expected"], {"state": "0.0"})
                self.assertNotIn("automatic_continue_requested", r.record,
                                 "Known owned modulation does not need initial-ON reconciliation")
                if feedback == 60.:
                    self.assertNotIn("unconfirmed_native_target", r.record,
                                     "Matching late native feedback acknowledges the retired raise")
                else:
                    retained = r.record.get("unconfirmed_native_target")
                    self.assertIsInstance(retained, dict)
                    for field in ("entity", "service", "data", "expected", "when", "attempts", "last_attempt_at"):
                        self.assertEqual(retained[field], original[field], field)
                self.assertFalse(r.record.get("paused"))
                self.assert_no_residual(r)

                if feedback == 60.:
                    # A later observed zero really ends that power episode.
                    # A subsequent positive source value gets a fresh native
                    # dwell, without acquiring ownership of that external ON.
                    r.report(mode="0.0")
                    await r.evaluate(1.)
                    self.assertFalse(r.record["power"])
                    self.assertEqual(r.record["native_power_observations"][r.primary]["state"], "off")
                    r.now += 1.
                    r.report(mode="60.0")
                    await r.evaluate()
                    self.assertFalse(r.record["power"])
                    self.assertEqual(r.record["native_power_observations"][r.primary],
                                     {"state": "on", "since": r.now})
                    self.assertEqual(r.statuses[-1][0], "minimum_on_hold")
                    self.assertEqual(len(r.calls), 2)

    async def test_two_distinct_unconfirmed_targets_preserve_both_budgets_and_allow_off(self):
        with endpoint("heat") as r:
            r.manager.settings["kp"] = 100.
            r.own(age=900., extreme=False)
            r.seed_residual()
            await r.evaluate()
            for _ in range(3):
                await r.evaluate(30.)
            await r.evaluate(30.)
            self.assertEqual(r.record.get("paused"), "physical_acknowledgement_missing")
            interrupted = deepcopy(r.record["pending"])
            await r.evaluate()
            # Each retry must settle for 120 seconds from its own dispatch.
            # The old first-attempt age cannot start the two-check proof.
            await r.evaluate(interrupted["last_attempt_at"] + 120. - r.now - 1.)
            self.assertEqual(r.record["pending"], interrupted)
            self.assertNotIn("pending_resume_probe", r.record)
            self.assertEqual(len(r.calls), 4)
            await r.evaluate(1.)
            self.assertIn("pending_resume_probe", r.record)
            await r.evaluate(60.)
            self.assertIsNone(r.record.get("pending"))
            previous = deepcopy(r.record["unconfirmed_native_target"])
            self.assertEqual(previous["attempts"], 4)
            self.assertEqual(previous["data"], {"temperature": 30.})
            # Native capability metadata may change independently. The next
            # exact endpoint is a different target and retains its own journal.
            r.state.attributes["max_temp"] = 32.
            await r.evaluate()
            newest = deepcopy(r.record["pending"])
            self.assertEqual(newest["data"], {"temperature": 32.})
            self.assertEqual(newest["attempts"], 1)
            self.assertEqual(r.record["unconfirmed_native_target"], previous)
            r.measurement = r.goal
            await r.evaluate(1.)
            self.assertEqual(calls(r)[-1], off(r), r.statuses)
            self.assertEqual(len(r.calls), 6)
            self.assertEqual(r.record.get("previous_unconfirmed_native_target"), previous)
            retained = r.record.get("unconfirmed_native_target")
            self.assertIsInstance(retained, dict)
            for field in ("entity", "service", "data", "expected", "when", "attempts", "last_attempt_at"):
                self.assertEqual(retained[field], newest[field], field)
            self.assertEqual(r.record["pending"]["expected"], {"state": "off"})
            self.assertFalse(r.record.get("paused"))
            self.assert_no_residual(r)

    async def test_target_crossing_during_retry_reservation_does_not_consume_an_attempt(self):
        for kind in ("heat", "cool"):
            for stage in ("intent_save", "semaphore"):
                with self.subTest(kind=kind, stage=stage), endpoint(kind) as r:
                    r.own(extreme=False)
                    r.seed_residual()
                    await r.evaluate()
                    initial = deepcopy(r.record["pending"])
                    self.assertEqual(len(r.calls), 1)
                    r.now += 30.
                    await self.cross_at_yield(r, stage, pending_phase="retry_intent")
                    await r.evaluate()
                    self.assertEqual(calls(r), [(initial["service"], initial["data"]), off(r)], r.statuses)
                    ledger = r.record.get("unconfirmed_native_target")
                    self.assertIsInstance(ledger, dict)
                    self.assertEqual(ledger["attempts"], 1)
                    self.assertEqual(ledger["last_attempt_at"], initial["last_attempt_at"])
                    self.assertFalse(r.record.get("paused"))

    async def test_cutoff_keeps_defrost_foreign_owner_and_unavailable_protections(self):
        for hold in ("defrost", "foreign", "unavailable"):
            with self.subTest(hold=hold), endpoint("heat") as r:
                r.own()
                r.seed_residual()
                r.measurement = r.goal
                if hold == "defrost":
                    r.state.attributes["hvac_action"] = "defrosting"
                elif hold == "foreign":
                    r.foreign_owner = "other_owner"
                else:
                    r.state.state = "unavailable"
                await r.evaluate()
                self.assertEqual(calls(r), [], "Target cutoff does not remove physical safety/identity gates")
                self.assertIn(r.primary, r.record["power"])

    async def test_real_status_reports_zero_demand_and_control_reading_during_native_dwell(self):
        for kind in ("heat", "cool", "dry", "humidify", "dehumidify"):
            with self.subTest(kind=kind), endpoint(kind) as r:
                r.own(age=100.)
                r.seed_residual()
                r.measurement = r.goal
                await r.evaluate()
                self.assertEqual(calls(r), [])
                # _status normally schedules a presentation notification. The
                # sink is inactive here; the actual production state projection
                # and its controller-bound record are otherwise unchanged.
                sink = N(statuses={}, records={r.spec.identifier: r.record},
                         _fan_allocations={}, _pid_offline_previews={}, _active=False,
                         clock=r.clock)
                production._status(sink, r.spec, "minimum_on_hold",
                                   demand_percent=90., minimum_on_remaining_seconds=500.)
                shown = sink.statuses[r.spec.identifier]
                self.assertEqual(shown["status"], "minimum_on_hold")
                self.assertEqual(shown["demand_percent"], 0.)
                self.assertTrue(shown["pid_target_reached"])
                self.assertEqual(shown["pid_control_metric"], r.metric)
                self.assertEqual(shown["pid_control_target"], r.goal)
                self.assertEqual(shown["pid_control_measurement"], r.measurement)
                self.assertEqual(shown["minimum_on_remaining_seconds"], 500.)
                r.manager.equipment = sink
                sensor = N(_manager=r.manager, _spec=r.spec,
                           controller_settings=r.manager.settings)
                attributes = status_scope["extra_state_attributes"].fget(sensor)
                self.assertEqual(attributes["demand_percent"], 0.)
                self.assertIs(attributes.get("pid_target_reached"), True)
                self.assertEqual(attributes.get("pid_control_target"), r.goal)
                self.assertEqual(attributes.get("pid_control_measurement"), r.measurement)
                self.assertEqual(attributes["pid_control_metric"], r.metric)
                self.assertEqual(attributes["native_minimum_on_remaining_seconds"], 500.)


if __name__ == "__main__":
    unittest.main(verbosity=2)

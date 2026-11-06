"""Automatic native commands must use current directional room demand.

Reuse the production tick, dispatch/journal, native-target and power fixtures.
Only HA transport, qualified measurements, room targets, storage and time are
isolated. Storage and command-lock hooks change evidence at real async yields;
no actuator decision is replaced, and service success never fabricates an ACK.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta111_pid_target_cutoff.py"),
                     run_name="hem_automatic_target_fixture")
endpoint, model, production, calls, off = (
    base[key] for key in ("endpoint", "model", "production", "calls", "off")
)
KINDS = ("heat", "cool", "dry", "humidify", "dehumidify")


def target_key(runtime):
    return runtime.mode if runtime.metric == "temperature" else "humidity"


def band(runtime):
    return .3 if runtime.metric == "temperature" else 2.


def reduced_target(runtime):
    return {"heat": 16., "cool": 30., "humidify": 40.,
            "dehumidify": 60., "dry": 60.}[runtime.kind]


def on(runtime):
    if runtime.state.domain == "climate":
        return "set_hvac_mode", {"hvac_mode": runtime.mode}
    return "turn_on", {}


def running_target(runtime, *, at_goal=False):
    """Supply native feedback that either needs a target write or is settled."""
    attrs = runtime.state.attributes
    if runtime.metric == "temperature":
        attrs["temperature"] = (
            attrs["max_temp" if runtime.increasing else "min_temp"]
            if at_goal else runtime.goal
        )
    else:
        attrs["humidity"] = runtime.goal if at_goal else (
            runtime.goal - 15. if runtime.increasing else runtime.goal + 15.
        )
    runtime.own(extreme=False)


def after_cutoff_cleanup(runtime, change):
    """Resume a real tick with changed evidence before _send takes snapshots.

    A prior PID cutoff can survive a switch to Automatic. Removing this saved
    marker calls Store after tick has read its original target/measurement.
    The event models independently arriving presence or sensor evidence.
    """
    runtime.record["capabilities"] = asdict(model.capabilities(runtime.manager, runtime.spec))
    runtime.record["baseline"][runtime.primary] = production.snapshot(runtime.state)
    runtime.record["pid_target_cutoff"] = {
        "mode": runtime.mode, "metric": runtime.metric,
        "measured": runtime.goal, "target": runtime.goal,
    }
    changed = []

    def after_save(controller):
        if ("pid_target_cutoff" not in controller.record
                and not controller.record.get("pending")):
            controller.after_persist = None
            change(controller)
            changed.append(True)

    runtime.after_persist = after_save
    return changed


class AutomaticTargetTests(unittest.IsolatedAsyncioTestCase):
    def assert_no_command(self, runtime):
        self.assertEqual(calls(runtime), [], runtime.statuses)
        self.assertFalse(runtime.record.get("pending"))
        self.assertFalse(runtime.record.get("paused"))

    async def test_away_during_cutoff_cleanup_cannot_start_retained_native_target(self):
        for kind in KINDS:
            with self.subTest(kind=kind), endpoint(kind, method="automatic") as r:
                if kind == "heat":
                    # Reproducer: a retained high thermostat
                    # setting must not turn 18.6 C into heat for Away 16 C.
                    r.measurement = 18.6
                    r.state.attributes["temperature"] = 30.
                elif kind == "cool":
                    r.state.attributes["temperature"] = 5.

                def leave_home(controller):
                    controller.manager.plan["away"] = "away"
                    controller.manager.targets[target_key(controller)] = reduced_target(controller)

                changed = after_cutoff_cleanup(r, leave_home)
                await r.evaluate()
                self.assertEqual(changed, [True], "Exercise the pre-dispatch persistence yield")
                self.assertEqual(model.profile_name(r.manager.settings, r.manager.plan), "away")
                self.assert_no_command(r)
                self.assertEqual(r.state.state, "off")

    async def test_current_target_or_measurement_replaces_pre_save_demand(self):
        for kind in KINDS:
            for evidence in ("target", "measurement", "missing_measurement"):
                with self.subTest(kind=kind, evidence=evidence), endpoint(kind, method="automatic") as r:
                    r.manager.plan["away"] = "away"

                    def change(controller):
                        if evidence == "target":
                            controller.manager.targets[target_key(controller)] = reduced_target(controller)
                        elif evidence == "measurement":
                            controller.measurement = controller.goal + (
                                2 * band(controller) if controller.increasing else -2 * band(controller)
                            )
                        else:
                            controller.measurement = None

                    changed = after_cutoff_cleanup(r, change)
                    await r.evaluate()
                    self.assertEqual(changed, [True])
                    self.assert_no_command(r)

    async def change_target_at_dispatch_yield(self, runtime, stage):
        intent = asyncio.Event()

        def change():
            runtime.manager.targets[target_key(runtime)] = reduced_target(runtime)

        def after_save(controller):
            if (controller.record.get("pending") or {}).get("phase") == "intent":
                controller.after_persist = None
                if stage == "intent_save":
                    change()
                intent.set()

        runtime.after_persist = after_save
        if stage == "intent_save":
            await runtime.evaluate()
        else:
            await runtime._commands.acquire()
            task = asyncio.create_task(runtime.evaluate())
            try:
                await asyncio.wait_for(intent.wait(), timeout=2)
                change()
            finally:
                runtime._commands.release()
                await task
        self.assertTrue(intent.is_set(), "Reach the durable command or command-lock yield")
        self.assertIsNone(runtime.after_persist)

    async def test_on_and_native_boost_recheck_targets_at_each_dispatch_yield(self):
        for kind in KINDS:
            for active in (False, True):
                for stage in ("intent_save", "semaphore"):
                    with self.subTest(kind=kind, active=active, stage=stage), endpoint(kind, method="automatic") as r:
                        if active:
                            running_target(r)
                        await self.change_target_at_dispatch_yield(r, stage)
                        self.assert_no_command(r)

    async def test_native_extreme_checks_exact_direction_against_current_away_target(self):
        for kind, measurements in (("heat", (18.6, 40.)), ("cool", (29., 10.))):
            for measured in measurements:
                with self.subTest(kind=kind, measured=measured), endpoint(kind, method="automatic") as r:
                    running_target(r)
                    stale_targets = dict(r.manager.targets)
                    r.manager.settings["requested_mode"] = None
                    r.manager.plan["away"] = "away"
                    r.manager.targets[kind] = reduced_target(r)
                    r.measurement = measured
                    cap = model.capabilities(r.manager, r.spec)
                    await r._native_target(r.spec, cap, r.mode, stale_targets, None, True)
                    self.assert_no_command(r)
                    # The far-out measurements need the OTHER thermal
                    # direction; aggregate room demand cannot approve this one.
                    self.assertEqual(r.state.state, r.mode)

    async def test_opposite_native_direction_does_not_borrow_running_hysteresis(self):
        for kind in ("heat", "cool"):
            with self.subTest(kind=kind), endpoint(kind, method="automatic") as r:
                r.state.state = "cool" if kind == "heat" else "heat"
                r.record["baseline"][r.primary] = production.snapshot(r.state)
                r.record["capabilities"] = asdict(model.capabilities(r.manager, r.spec))
                r.measurement = r.goal - .1 if r.increasing else r.goal + .1
                # The incoming direction has not started. An old command
                # reaching _send cannot use the opposite direction's wider
                # continuation band to authorize a new thermal direction.
                await r.dispatch("set_hvac_mode", {"hvac_mode": kind}, power=True, mode=kind)
                self.assert_no_command(r)

    async def test_automatic_off_requires_start_hysteresis(self):
        for kind in KINDS:
            for offset, starts in ((.1, True), (-.1, False), (-.3, False)):
                with self.subTest(kind=kind, offset=offset), endpoint(kind, method="automatic") as r:
                    error = band(r) + offset
                    r.measurement = r.goal - error if r.increasing else r.goal + error
                    await r.evaluate()
                    self.assertEqual(calls(r), [on(r)] if starts else [], r.statuses)
                    self.assertFalse(r.record["power"], "A service return is not native ON feedback")

    async def test_running_automatic_keeps_hysteresis_and_stops_outside_it(self):
        for kind in KINDS:
            for error_offset, stops in ((.1, False), (-.1, True)):
                with self.subTest(kind=kind, error_offset=error_offset), endpoint(kind, method="automatic") as r:
                    running_target(r, at_goal=True)
                    error = -band(r) + error_offset
                    r.measurement = r.goal - error if r.increasing else r.goal + error
                    await r.evaluate()
                    self.assertEqual(calls(r), [off(r)] if stops else [], r.statuses)

    async def test_running_automatic_can_adjust_target_inside_hysteresis(self):
        for kind in KINDS:
            with self.subTest(kind=kind), endpoint(kind, method="automatic") as r:
                running_target(r)
                error = -band(r) / 2
                r.measurement = r.goal - error if r.increasing else r.goal + error
                await r.evaluate()
                if r.metric == "temperature":
                    key, service = "temperature", "set_temperature"
                    target = r.state.attributes["max_temp" if r.increasing else "min_temp"]
                else:
                    key, service = "humidity", "set_humidity"
                    target = r.goal - 10. if r.increasing else r.goal + 10.
                self.assertEqual(calls(r), [(service, {key: target})], r.statuses)

    async def test_soft_only_automatic_may_reduce_an_old_native_boost(self):
        for kind in KINDS:
            with self.subTest(kind=kind), endpoint(kind, method="automatic") as r:
                r.manager.power_grant = False
                key = "temperature" if r.metric == "temperature" else "humidity"
                service = "set_temperature" if r.metric == "temperature" else "set_humidity"
                step = .5 if r.metric == "temperature" else 5.
                sign = 1 if r.increasing else -1
                r.state.attributes[key] = r.goal + 3 * step * sign
                r.own(extreme=False)
                r.record["power"].clear()
                r.measurement = r.goal + 2 * band(r) * sign
                await r.evaluate()
                self.assertEqual(calls(r), [(service, {key: r.goal + 2 * step * sign})], r.statuses)
                self.assertFalse(r.record["power"])
                self.assertFalse(r.manager.power_grant)

    async def test_satisfied_automatic_off_preserves_minimum_on(self):
        for kind in KINDS:
            for age, stops in ((100., False), (900., True)):
                with self.subTest(kind=kind, age=age), endpoint(kind, method="automatic") as r:
                    r.own(age=age)
                    r.measurement = r.goal + (2 * band(r) if r.increasing else -2 * band(r))
                    await r.evaluate()
                    self.assertEqual(calls(r), [off(r)] if stops else [], r.statuses)
                    self.assertIn(r.primary, r.record["power"], "OFF still requires physical acknowledgement")

    async def test_manual_power_does_not_inherit_automatic_demand_gate(self):
        for kind in ("heat", "cool"):
            for reading in (None, 40. if kind == "heat" else 10.):
                with self.subTest(kind=kind, reading=reading), endpoint(kind, method="manual") as r:
                    r.manager.plan["away"] = "away"
                    r.manager.targets[kind] = reduced_target(r)
                    r.measurement = reading
                    await r.evaluate()
                    self.assertEqual(calls(r), [on(r)], r.statuses)


if __name__ == "__main__":
    unittest.main()

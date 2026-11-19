"""Interrupted physical evidence never becomes one continuous PID response.

Execute the production tick, observer, native event hook, command journal and
ACK reconciliation. HA transport/registry, clock and persistence are isolated;
an actual service return never substitutes for a reported native state.
"""
from __future__ import annotations

import ast
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import importlib
from pathlib import Path
import runpy
import sys
from types import MethodType, SimpleNamespace as N
import unittest
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[2]
learning = runpy.run_path(str(ROOT / ".github/tests/test_074_pid_learning_runtime.py"))
fixture, production, model, passive = (
    learning[key] for key in ("fixture", "production", "model", "passive")
)
load_pure = learning["load_pure"]
load_pure("pid_learning_store", "pid_learning_store.py")
restart = load_pure("pid_restart", "pid_restart.py")
PACKAGE = fixture["fixture"]["PACKAGE"]
sequence = importlib.import_module(PACKAGE + ".equipment_setpoint_sequence")
supply = importlib.import_module(PACKAGE + ".equipment_power_switch")
tree = ast.parse((ROOT / "equipment_runtime.py").read_text())
runtime_class = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "EquipmentRuntime")
METHODS = ("_interrupt_pid_learning", "_pid_learning_observed", "observe_native_availability")
for name in METHODS:
    node = next(node for node in runtime_class.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]),
                 f"production {name}", "exec"), production.__dict__)

# Use the real upstream pause/wait decision, with registry identity isolated at
# its boundary. Other upstream tests exercise command dispatch and power dwell.
supply_scope = dict(supply.__dict__)
supply_tree = ast.parse((ROOT / "equipment_power_switch.py").read_text())
supply_node = next(node for node in supply_tree.body
                   if isinstance(node, ast.AsyncFunctionDef) and node.name == "before_tick")
exec(compile(ast.Module(body=[supply_node], type_ignores=[]),
             "production upstream before_tick", "exec"), supply_scope)
supply_scope.update(_SWITCH_STATES=("off", "on"), UPSTREAM_ACK_SECONDS=30.)


@contextmanager
def endpoint():
    with fixture["endpoint"]("heat") as runtime:
        _, _, context = learning["attach"](runtime)
        for name in METHODS:
            setattr(runtime, name, MethodType(getattr(production, name), runtime))
        runtime._pid_learning_generation = {}
        runtime._pid_learning_edges = {}
        runtime._pid_learning_observed_edges = {}
        runtime._native_reconnect_epoch = {}
        with patch.object(model, "specs", lambda manager: [runtime.spec], create=True):
            yield runtime, context


def seed(runtime, context):
    observer = learning["seed_normal_response"](runtime, context)
    # Preserve a previously accepted response alongside this unfinished one.
    observer.cycles = [{"at": runtime.now - 20000., "gain": 4., "tau": 28.,
                        "dead": 10., "r2": .99}]
    runtime.record["pid_passive"] = deepcopy(observer.ledger())
    runtime._pid_learning_observed(runtime.spec)
    return observer


def native_event(runtime, *, state=None, **attributes):
    old = deepcopy(runtime.state)
    if state is not None:
        runtime.state.state = state
    runtime.state.attributes.update(attributes)
    runtime.observe_native_availability(runtime.primary, old, deepcopy(runtime.state))


class InterruptionTests(unittest.IsolatedAsyncioTestCase):
    def assert_interrupted(self, runtime, observer, saved):
        self.assertEqual(observer.on, [])
        self.assertEqual(observer.off, [])
        self.assertIsNone(observer.baseline)
        self.assertIsNone(observer.last_on)
        self.assertEqual(observer.cycles, saved["cycles"])
        self.assertEqual(runtime.record["pid_passive"]["context"], saved["context"])
        self.assertEqual(runtime.record["pid_passive"]["cycles"], saved["cycles"])
        self.assertGreater(runtime._pid_learning_generation[runtime.spec.identifier], 0)

    async def test_one_normal_off_event_completes_the_observed_response(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            native_event(runtime, state="off", hvac_action="off")
            self.assertTrue(observer.on, "A real final OFF is required evidence, not a discontinuity")
            runtime.measurement = runtime.goal
            await runtime.evaluate()
            self.assertEqual(len(observer.cycles), 2)
            self.assertEqual(runtime.record["pid_passive"]["summary"]["valid_cycles"], 2)
            self.assertEqual(runtime.calls, [])

    async def test_target_request_keeps_response_until_a_real_off_ack(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            runtime.measurement = runtime.goal
            await runtime.evaluate()
            self.assertEqual(len(observer.cycles), 1)
            self.assertTrue(observer.on)
            self.assertTrue(observer.last_on)
            self.assertIsNotNone(runtime.record["pending"])
            native_event(runtime, state="off", hvac_action="off")
            await runtime.evaluate(advance=1.)
            self.assertEqual(len(observer.cycles), 2)
            self.assertFalse(runtime.record["pending"])

    async def test_native_event_during_earlier_tick_await_cannot_certify_old_snapshot(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            saved = deepcopy(runtime.record["pid_passive"])
            runtime.measurement = runtime.goal
            observe_running = runtime._observe_native_running

            async def off_report_after_native_observation(spec, cap, captured_state):
                await observe_running(spec, cap, captured_state)
                self.assertIs(captured_state, runtime.state)
                old = runtime.state
                # HA replaces its State object when reporting an event. The
                # tick still holds the older object across this await boundary.
                runtime.state = deepcopy(old)
                runtime.state.state = "off"
                runtime.state.attributes["hvac_action"] = "off"
                runtime.observe_native_availability(runtime.primary, old, runtime.state)

            runtime._observe_native_running = off_report_after_native_observation
            await runtime.evaluate()
            self.assert_interrupted(runtime, observer, saved)
            self.assertEqual(runtime._pid_learning_edges[runtime.primary], 1)
            self.assertEqual(runtime._pid_learning_observed_edges[runtime.spec.identifier][runtime.primary], 0,
                             "An older snapshot must not consume the newer native OFF event")
            self.assertEqual(runtime.calls, [])

    async def test_hidden_off_on_same_timestamp_clears_only_partial_evidence(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            saved, writes = deepcopy(runtime.record["pid_passive"]), len(runtime.persisted)
            native_event(runtime, state="off", hvac_action="off")
            self.assertTrue(observer.on)
            native_event(runtime, state="heat", hvac_action="heating")
            self.assert_interrupted(runtime, observer, saved)
            first = runtime._pid_learning_generation[runtime.spec.identifier]
            native_event(runtime, state="off", hvac_action="off")
            self.assertGreater(runtime._pid_learning_generation[runtime.spec.identifier], first)
            self.assertEqual(len(runtime.persisted), writes, "Event counters must never write Store")
            self.assertEqual(runtime.calls, [])

    async def test_repeated_same_state_reports_do_not_interrupt_or_write(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            samples, writes = list(observer.on), len(runtime.persisted)
            for _ in range(3):
                native_event(runtime)
            self.assertEqual(observer.on, samples)
            self.assertEqual(runtime._pid_learning_generation, {})
            self.assertEqual(len(runtime.persisted), writes)

    async def test_hidden_availability_activity_mode_and_fan_roundtrips_interrupt(self):
        transitions = (
            ({"state": "unavailable"}, {"state": "heat"}),
            ({"hvac_action": "idle"}, {"hvac_action": "heating"}),
            ({"state": "cool", "hvac_action": "cooling"},
             {"state": "heat", "hvac_action": "heating"}),
            ({"fan_mode": "low"}, {"fan_mode": "high"}),
        )
        for changed, restored in transitions:
            with self.subTest(changed=changed), endpoint() as (runtime, context):
                runtime.own()
                runtime.state.attributes.update(hvac_action="heating", fan_mode="high")
                observer = seed(runtime, context)
                saved = deepcopy(runtime.record["pid_passive"])
                native_event(runtime, **changed)
                native_event(runtime, **restored)
                self.assert_interrupted(runtime, observer, saved)
                self.assertEqual(runtime.calls, [])

    async def test_normal_edges_are_consumed_by_each_certified_sample(self):
        with endpoint() as (runtime, context):
            observer = seed(runtime, context)
            observer.interrupt()
            old = deepcopy(runtime.state)
            runtime.state.state = "heat"
            runtime.state.attributes["hvac_action"] = "heating"
            runtime.observe_native_availability(runtime.primary, old, runtime.state)
            self.assertEqual(runtime._pid_learning_observed(runtime.spec), 0)
            native_event(runtime, state="off", hvac_action="off")
            self.assertEqual(runtime._pid_learning_generation, {})
            self.assertEqual(runtime._pid_learning_observed(runtime.spec), 0)

    async def test_normal_off_edge_allows_paired_native_control_attributes(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            samples = list(observer.on)
            native_event(runtime, state="off", hvac_action="off", temperature=21.,
                         target_temp_low=17., target_temp_high=25., humidity=45.,
                         preset_mode="eco", swing_mode="vertical",
                         swing_horizontal_mode="left", mode="eco")
            self.assertEqual(observer.on, samples)
            self.assertEqual(runtime._pid_learning_generation, {})
            self.assertEqual(runtime.calls, [])

    async def test_selected_supply_roundtrip_revokes_continuity(self):
        with endpoint() as (runtime, context):
            observer = seed(runtime, context)
            saved = deepcopy(runtime.record["pid_passive"])
            runtime.manager.settings["power_switch_entity"] = "switch.supply"
            on, off = N(state="on", attributes={}), N(state="off", attributes={})
            runtime.observe_native_availability("switch.supply", on, off)
            runtime.observe_native_availability("switch.supply", off, on)
            self.assert_interrupted(runtime, observer, saved)
            self.assertEqual(runtime.calls, [])

    async def test_short_unacknowledged_target_wait_cannot_bridge_the_response(self):
        with endpoint() as (runtime, context):
            runtime.own(extreme=False)
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            saved = deepcopy(runtime.record["pid_passive"])
            cap = model.capabilities(runtime.manager, runtime.spec)
            target = model.targets(runtime.manager, runtime.spec, cap,
                                   runtime.manager.settings, runtime.manager.plan)
            self.assertTrue(await runtime._native_target(runtime.spec, cap, "heat", target, None, True))
            journal = deepcopy(runtime.record["pending"])
            await runtime.evaluate(advance=1.)
            self.assert_interrupted(runtime, observer, saved)
            self.assertEqual(runtime.record["pending"]["expected"], journal["expected"])
            self.assertEqual(runtime.record["pending"]["attempts"], journal["attempts"])
            self.assertEqual(len(runtime.calls), 1, "Waiting must not resend a command or invent an ACK")

    async def test_real_upstream_pause_and_short_ack_wait_interrupt(self):
        for paused in (False, True):
            with self.subTest(paused=paused), endpoint() as (runtime, context):
                observer = seed(runtime, context)
                saved = deepcopy(runtime.record["pid_passive"])
                selected = "switch.supply"
                identity = {"entity": selected}
                runtime.manager.settings["power_switch_entity"] = selected
                relay = runtime.record["upstream"] = {"entity": selected, "identity": identity}
                if paused:
                    relay["paused"] = "upstream_switch_manual_override"
                else:
                    relay["pending"] = {"identity": identity, "desired": "on", "when": runtime.now}
                native_get = runtime.hass.states.get
                runtime.hass.states.get = lambda entity: (
                    N(state="off", attributes={}) if entity == selected else native_get(entity)
                )
                with patch.dict(supply_scope, permitted_supply=lambda *args: identity), \
                        patch.object(supply, "before_tick", supply_scope["before_tick"]):
                    await runtime.evaluate(advance=1.)
                self.assert_interrupted(runtime, observer, saved)
                self.assertEqual(runtime.calls, [])
                self.assertEqual(runtime.statuses[-1][0], "paused" if paused
                                 else "awaiting_physical_acknowledgement")

    async def test_early_controller_waits_drop_partial_but_keep_completed_ledger(self):
        cases = ("startup", "stop_sequence", "queued_supply", "restart_verification",
                 "automatic_recovery", "paused", "unavailable", "native_reconciliation")
        for case in cases:
            with self.subTest(case=case), endpoint() as (runtime, context):
                observer = seed(runtime, context)
                saved = deepcopy(runtime.record["pid_passive"])
                if case == "startup":
                    runtime.startup_ready = False
                elif case == "queued_supply":
                    runtime.record["queued_power_switch"] = {"entity": "switch.new"}
                    runtime._apply_queued_power_switch = AsyncMock(return_value=True)
                elif case == "restart_verification":
                    runtime.record["restart_power_verification"] = True
                    runtime._verify_restart_power = AsyncMock(return_value=False)
                elif case == "automatic_recovery":
                    runtime.record["automatic_continue_requested"] = {}
                    runtime._automatic_recovery_gate = lambda _: {"ready": False, "reason": "settling"}
                elif case == "paused":
                    runtime.record["paused"] = "physical_manual_override"
                elif case == "unavailable":
                    runtime.state.state = "unavailable"
                elif case == "native_reconciliation":
                    runtime._reconcile_native_after_supply_wake = AsyncMock(return_value=False)
                with patch.object(sequence, "progress_stop", AsyncMock(return_value=case == "stop_sequence")):
                    await runtime.evaluate()
                self.assert_interrupted(runtime, observer, saved)
                self.assertEqual(runtime.calls, [])

    async def test_max_on_and_permission_loss_shutdown_do_not_finish_a_model(self):
        for case in ("max_on", "permission"):
            with self.subTest(case=case), endpoint() as (runtime, context):
                runtime.own(age=8000. if case == "max_on" else 900.)
                runtime.state.attributes["hvac_action"] = "heating"
                observer = seed(runtime, context)
                saved = deepcopy(runtime.record["pid_passive"])
                if case == "permission":
                    runtime.manager.power_grant = False
                await runtime.evaluate()
                self.assert_interrupted(runtime, observer, saved)
                self.assertEqual(len(runtime.calls), 1)
                self.assertEqual(runtime.calls[0]["data"], {"hvac_mode": "off"})
                self.assertTrue(runtime.record["power"], "Dispatch is not physical OFF evidence")

    async def test_exception_and_cancellation_clear_partial_before_propagating(self):
        for error in (RuntimeError("read failure"), asyncio.CancelledError()):
            with self.subTest(error=type(error).__name__), endpoint() as (runtime, context):
                observer = seed(runtime, context)
                saved = deepcopy(runtime.record["pid_passive"])
                runtime._reconcile_native_after_supply_wake = AsyncMock(side_effect=error)
                with self.assertRaises(type(error)):
                    await runtime.evaluate()
                self.assert_interrupted(runtime, observer, saved)
                self.assertEqual(runtime.calls, [])

    async def test_exception_after_a_sample_still_revokes_its_partial_response(self):
        with endpoint() as (runtime, context):
            runtime.own()
            runtime.state.attributes["hvac_action"] = "heating"
            observer = seed(runtime, context)
            saved = deepcopy(runtime.record["pid_passive"])
            runtime._native_target = AsyncMock(side_effect=RuntimeError("late target read failure"))
            with self.assertRaises(RuntimeError):
                await runtime.evaluate()
            self.assertEqual(runtime._native_target.await_count, 1)
            self.assert_interrupted(runtime, observer, saved)
            self.assertEqual(runtime.calls, [])

    async def test_watchdog_hold_and_caught_failure_break_the_old_response(self):
        for failure in (False, True):
            with self.subTest(failure=failure), endpoint() as (runtime, context):
                runtime.state.state = "off"
                runtime.state.attributes["hvac_action"] = "off"
                runtime.measurement = runtime.goal
                observer = seed(runtime, context)
                saved = deepcopy(runtime.record["pid_passive"])
                runtime.record["thermal_off_watch"] = {"entity": runtime.primary}
                watchdog = AsyncMock(side_effect=RuntimeError("monitor failure")) if failure else AsyncMock(return_value=True)
                with patch.dict(sys.modules, {PACKAGE + ".off_state_runtime": N(watchdog_tick=watchdog)}):
                    await runtime.evaluate()
                self.assertEqual(watchdog.await_count, 1)
                self.assertEqual(observer.on, [], "A caught monitor failure must not retain the earlier ON samples")
                self.assertEqual(observer.cycles, saved["cycles"])
                self.assertGreater(runtime._pid_learning_generation[runtime.spec.identifier], 0)
                self.assertEqual(runtime.calls, [])

    async def test_logical_reset_also_revokes_a_queued_generation_without_storage(self):
        with endpoint() as (runtime, context):
            observer = seed(runtime, context)
            saved, writes = deepcopy(runtime.record["pid_passive"]), len(runtime.persisted)
            self.assertTrue(restart.reset_logical_cycle(runtime, runtime.spec, "active_control_changed"))
            self.assert_interrupted(runtime, observer, saved)
            first = runtime._pid_learning_generation[runtime.spec.identifier]
            self.assertFalse(restart.reset_logical_cycle(runtime, runtime.spec, "active_control_changed"))
            self.assertGreater(runtime._pid_learning_generation[runtime.spec.identifier], first)
            self.assertEqual(len(runtime.persisted), writes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

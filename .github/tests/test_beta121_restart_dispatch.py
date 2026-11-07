"""Restart presence cannot energize native output or its upstream supply.

Use production profile targets, PID checkpoints, tick, command journals,
retry/recovery and dispatch with the existing simulated HA transport. The
fixture provides fresh measurements and explicit presence evidence; the
separate presence/measurement suites verify how real HA states produce them.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import runpy
from types import MethodType, SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta111_pid_target_cutoff.py"))
fixture, model, production = (base[key] for key in ("fixture", "model", "production"))
fixture["load_pure"]("pid_restart", "pid_restart.py")
fixture["extract"](fixture["RUNTIME"], ("_resume_pid_checkpoint", "_checkpoint_pid"),
                   production.__dict__)
# Run the real profile and target resolver, including native/room limits.
target_scope = dict(model.__dict__)
fixture["extract"](ROOT / "climate_strategy.py", ("profile_humidity_target",),
                   target_scope, constants=("DEFAULT_PROFILE_TARGETS",))
fixture["extract"](ROOT / "equipment_model.py", ("targets",), target_scope)


@contextmanager
def endpoint(method="pid", *, away="unknown"):
    with base["endpoint"]("heat", method=method) as runtime:
        runtime.manager.plan.update(away=away, occupancy="unoccupied", sleeping=False)
        runtime.manager.room["profiles"] = {
            "home": {"heat_c": 21., "cool_c": 26., "humidity": 50.},
            "comfort": {"heat_c": 22., "cool_c": 25., "humidity": 50.},
            "away": {"heat_c": 10., "cool_c": 30., "humidity": 50.},
        }
        runtime.manager.settings["kp"] = 100.
        runtime.measurement = 19.
        with patch.object(model, "targets", target_scope["targets"]):
            yield runtime


def calls(runtime):
    return base["calls"](runtime)


class OnLock:
    def __init__(self, action):
        self.action = action

    async def __aenter__(self):
        self.action()

    async def __aexit__(self, *args):
        return False


class RestartDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_presence_waits_and_real_away_recovers_without_changing_mode(self):
        for method in ("automatic", "pid"):
            for measured, wanted in ((19., False), (9., True)):
                with self.subTest(method=method, measured=measured), endpoint(method) as r:
                    r.measurement = measured
                    await r.evaluate()
                    self.assertEqual(calls(r), [])
                    self.assertEqual(r.statuses[-1][0], "house_occupancy_unknown")
                    self.assertFalse(r.record.get("pending"))
                    self.assertFalse(r.record.get("paused"))
                    r.manager.plan["away"] = "away"
                    await r.evaluate(1)
                    self.assertEqual(calls(r), [("set_hvac_mode", {"hvac_mode": "heat"})]
                                     if wanted else [])
                    self.assertEqual(r.manager.settings["control_mode"], method)
                    self.assertFalse(r.record.get("paused"))

    async def test_positive_saved_pid_integral_cannot_start_above_current_away_target(self):
        with endpoint(away="home") as r:
            r._resume_pid_checkpoint = MethodType(production._resume_pid_checkpoint, r)
            r._checkpoint_pid = MethodType(production._checkpoint_pid, r)
            r.seed_residual(integral=80., demand=90.)
            signature, memory, anchor = r._memory[r.spec.identifier]
            await r._checkpoint_pid(r.spec, r.record, r.manager.settings, signature, memory, anchor)
            self.assertEqual(r.record["pid_checkpoint"]["integral"], 80.)
            r._memory.clear()  # A new runtime has only the persisted checkpoint.
            r.manager.plan["away"] = "away"
            await r.evaluate()
            self.assertEqual(calls(r), [])
            self.assertNotIn("pid_checkpoint", r.record)
            self.assertNotIn(r.spec.identifier, r._memory)
            self.assertEqual(r.record["pid_target_cutoff"]["target"], 10.)
            self.assertEqual(r.record["pid_target_cutoff"]["measured"], 19.)

    async def test_unknown_presence_at_each_native_dispatch_yield_cancels_unsent_on(self):
        for method in ("automatic", "pid"):
            for boundary in ("save", "lock"):
                with self.subTest(method=method, boundary=boundary), endpoint(method, away="home") as r:
                    def unknown():
                        r.manager.plan["away"] = "unknown"
                    if boundary == "save":
                        def after_save(current):
                            if current.record.get("pending"):
                                current.after_persist = None
                                unknown()
                        r.after_persist = after_save
                    else:
                        r._commands = OnLock(unknown)
                    await r.evaluate()
                    self.assertEqual(calls(r), [])
                    self.assertFalse(r.record.get("pending"))
                    self.assertFalse(r.record.get("paused"))
                    self.assertEqual(r.statuses[-1][0], "house_occupancy_unknown")

    async def test_manual_and_explicit_presets_remain_usable_with_unknown_presence(self):
        for method, preset in (("manual", "none"), ("automatic", "home"), ("pid", "home")):
            with self.subTest(method=method, preset=preset), endpoint(method) as r:
                r.manager.settings["preset"] = preset
                await r.evaluate()
                self.assertEqual(calls(r), [("set_hvac_mode", {"hvac_mode": "heat"})])
                self.assertFalse(r.record.get("paused"))

    async def test_unknown_presence_blocks_boost_but_allows_running_reduction_and_off(self):
        for method in ("automatic", "pid"):
            for operation in ("boost", "reduce", "off", "minimum_on"):
                with self.subTest(method=method, operation=operation), endpoint(method) as r:
                    r.own(age=100. if operation == "minimum_on" else 900.)
                    cap = model.capabilities(r.manager, r.spec)
                    if operation in ("off", "minimum_on"):
                        await r._power(r.spec, cap, "off", automatic=True, shutdown=True)
                        expected = [] if operation == "minimum_on" else [("set_hvac_mode", {"hvac_mode": "off"})]
                    else:
                        r.state.attributes["temperature"] = 20. if operation == "boost" else 30.
                        r.record["baseline"][r.primary] = production.snapshot(r.state)
                        data = {"temperature": 30. if operation == "boost" else 20.}
                        await r.dispatch("set_temperature", data, mode="heat")
                        expected = [] if operation == "boost" else [("set_temperature", data)]
                    self.assertEqual(calls(r), expected)
                    self.assertFalse(r.record.get("paused"))

    async def test_unknown_presence_never_treats_off_fan_percentage_as_a_reduction(self):
        safety = fixture["load_pure"]("equipment_pid_safety", "equipment_pid_safety.py")
        with endpoint() as r:
            r.state.domain, r.state.state = "fan", "off"
            r.state.attributes = {"percentage": 60.}
            cap = model.Capabilities(r.primary, "fan", ("off", "fan_only"), fan_entity=r.primary)
            for requested in (30., 80.):
                self.assertFalse(safety.command_allowed(
                    r, r.spec, cap, "set_percentage", {"percentage": requested},
                    mode="off", automatic=True,
                ))
            self.assertTrue(safety.command_allowed(
                r, r.spec, cap, "set_percentage", {"percentage": 0.},
                mode="off", automatic=True,
            ))

    async def test_unknown_presence_cannot_reduce_the_wrong_native_thermal_direction(self):
        with endpoint() as r:
            r.own()
            r.state.attributes["temperature"] = 20.
            r.record["baseline"][r.primary] = production.snapshot(r.state)
            await r.dispatch("set_temperature", {"temperature": 25.}, mode="cool")
            self.assertEqual(calls(r), [])

    async def test_pending_on_waits_for_presence_without_consuming_retry_budget(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method), endpoint(method, away="away") as r:
                r.measurement = 9.
                await r.evaluate()
                pending = r.record["pending"]
                original = deepcopy(pending)
                r.manager.plan["away"] = "unknown"
                await r.evaluate(30)
                self.assertEqual(len(calls(r)), 1)
                self.assertEqual(pending, original)
                self.assertFalse(r.record.get("paused"))
                self.assertEqual(r.statuses[-1][0], "house_occupancy_unknown")
                r.manager.plan["away"] = "away"
                await r.evaluate(30)
                self.assertEqual(len(calls(r)), 2)
                self.assertEqual(pending["attempts"], 2)

    async def test_presence_lost_during_retry_save_preserves_original_attempt(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method), endpoint(method, away="away") as r:
                r.measurement = 9.
                await r.evaluate()
                original = deepcopy(r.record["pending"])
                def after_save(current):
                    if current.record["pending"].get("phase") == "retry_intent":
                        current.after_persist = None
                        current.manager.plan["away"] = "unknown"
                r.after_persist = after_save
                await r.evaluate(60)
                self.assertIsNone(r.after_persist, "Exercise the durable retry reservation")
                self.assertEqual(r.manager.plan["away"], "unknown")
                self.assertEqual(len(calls(r)), 1)
                self.assertEqual(r.record["pending"], original)
                self.assertFalse(r.record.get("paused"))

    async def test_off_fan_percentage_retry_rechecks_presence_at_every_yield(self):
        for method in ("automatic", "pid"):
            for boundary in ("save", "lock"):
                with self.subTest(method=method, boundary=boundary), endpoint(method, away="home") as r:
                    r.primary = "fan.native_filter"
                    r.spec = N(identifier=r.spec.identifier, area_id=r.spec.area_id,
                               source_device_id=r.spec.source_device_id,
                               source_entities=(r.primary,))
                    r.record["sources"] = [r.primary]
                    r.state.domain, r.state.state = "fan", "off"
                    r.state.attributes = {"percentage": 60., "supported_features": 1}
                    r._native_settle_remaining = lambda spec: 0.
                    r.manager.settings["requested_mode"] = "fan_only"
                    r.manager.device.update(fan_purpose="filtration", sensor_verified=True)
                    r.manager.plan.update(air_evidence_at=r.now, air_actions={
                        "thresholds": {"pm25_short_term_action_ug_m3": 10.},
                    })
                    r.measurements = lambda *args: {
                        "temperature": 19., "humidity": 50., "co2": None, "pm25": 30.,
                    }
                    cap = model.capabilities(r.manager, r.spec)
                    await r._send(r.spec, cap, r.primary, "set_percentage", {"percentage": 30.},
                                  {"attributes": {"percentage": 30.}}, automatic=True)
                    self.assertEqual(calls(r), [("set_percentage", {"percentage": 30.})])
                    self.assertEqual(r.record["pending"]["retry_context"]["mode"], "off")
                    original = deepcopy(r.record["pending"])
                    def unknown():
                        r.manager.plan["away"] = "unknown"
                    if boundary == "save":
                        def after_save(current):
                            if current.record["pending"].get("phase") == "retry_intent":
                                current.after_persist = None
                                unknown()
                        r.after_persist = after_save
                    else:
                        r._commands = OnLock(unknown)
                    r.now += 60.
                    await r._retry_pending(r.spec, r.record["pending"], r.now)
                    self.assertEqual(r.manager.plan["away"], "unknown",
                                     "Exercise the requested retry boundary")
                    self.assertEqual(len(calls(r)), 1)
                    self.assertEqual(r.record["pending"], original)
                    self.assertFalse(r.record.get("paused"))

    async def test_pending_home_on_recovers_as_away_without_replaying_or_manual_pause(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method), endpoint(method, away="home") as r:
                await r.evaluate()
                original = deepcopy(r.record["pending"])
                r.manager.plan["away"] = "unknown"
                await r.evaluate(30)
                r.manager.plan["away"] = "away"
                await r.evaluate(30)
                self.assertEqual(len(calls(r)), 1)
                self.assertEqual(r.record["pending"], original)
                self.assertIn("automatic_continue_requested", r.record)
                self.assertFalse(r.record.get("paused"))
                # Observe actual native OFF through the existing read-only
                # two-observation recovery, without treating it as an ON ACK.
                await r.evaluate(60)
                await r.evaluate(60)
                await r.evaluate(1)
                self.assertEqual(len(calls(r)), 1)
                self.assertFalse(r.record.get("paused"))
                self.assertFalse(r.record.get("pending"))
                self.assertEqual(r.state.state, "off")

    async def test_pending_off_retries_when_profile_changes(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method), endpoint(method, away="home") as r:
                r.own()
                cap = model.capabilities(r.manager, r.spec)
                await r._power(r.spec, cap, "off", automatic=True, shutdown=True)
                r.manager.plan["away"] = "away"
                await r.evaluate(60)
                self.assertEqual(calls(r), [("set_hvac_mode", {"hvac_mode": "off"})] * 2)
                self.assertFalse(r.record.get("paused"))
                self.assertNotIn("automatic_continue_requested", r.record)

    async def test_supply_send_rechecks_unknown_presence_and_recovers_on_real_away_demand(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method), endpoint(method) as r:
                supply, identity = self.supply(r)
                self.assertFalse(await supply["_send"](r, r.spec, r.record, identity, "on"))
                self.assertEqual(calls(r), [])
                r.manager.plan["away"] = "away"
                self.assertFalse(await supply["_send"](r, r.spec, r.record, identity, "on"))
                self.assertEqual(calls(r), [])
                r.measurement = 9.
                self.assertTrue(await supply["_send"](r, r.spec, r.record, identity, "on"))
                self.assertEqual(calls(r), [("turn_on", {})])

    async def test_supply_does_not_use_explicit_preset_cleared_while_queued(self):
        with endpoint() as r:
            supply, identity = self.supply(r)
            r.manager.settings["preset"] = "home"
            def implicit_profile():
                r.manager.settings = {**r.manager.settings, "preset": "none"}
            r._commands = OnLock(implicit_profile)
            self.assertFalse(await supply["_send"](r, r.spec, r.record, identity, "on"))
            self.assertEqual(calls(r), [])
            self.assertFalse(r.record["upstream"].get("pending"))

    def supply(self, runtime):
        """Actual supply dispatch/demand; unrelated pairing/dwell are verified fixtures."""
        entity = "switch.heater_supply"
        identity = {"entity": entity, "area": runtime.spec.area_id, "device_id": "supply"}
        relay = N(domain="switch", state="off", attributes={})
        runtime.manager.settings["power_switch_entity"] = entity
        runtime.hass.states.get = lambda selected: relay if selected == entity else (
            runtime.state if selected == runtime.primary else None)
        scope = {
            "__package__": fixture["PACKAGE"], "model": model,
            "finite": model.finite, "Mapping": Mapping, "asyncio": asyncio,
            "_SWITCH_STATES": ("off", "on"),
            "verified_capabilities": lambda r, spec: model.capabilities(r.manager, spec),
            "device_supply_dwell": lambda *args: (600., 600.),
            "supply_minimum_off": lambda *args: True,
            "supply_minimum_on": lambda *args: True,
            "idle_cooldown_ready": lambda *args: True,
            "permitted_supply": lambda *args: identity,
        }
        fixture["extract"](ROOT / "equipment_power_switch.py", (
            "_send", "_dispatch_safe", "approved_demand", "output_required",
            "observed_output_off", "native_outputs_idle",
        ), scope, constants=("_IDLE_HVAC_ACTIONS",))
        return scope, identity


if __name__ == "__main__":
    unittest.main(verbosity=2)

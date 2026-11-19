"""Adaptive gains through the complete production settings writer and guards.

Uses the existing native runtime fixture: model/settings resolution, native
mode selection, async_update, persistence, both calibration guards and the
application/review methods are production code. Only HA transport/registry,
qualified sensor readings, time and storage are isolated. No device is used.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_061b7_runtime_modes.py"))
model, production, SPEC, PRIMARY = (
    fixture[key] for key in ("model", "production", "SPEC", "PRIMARY")
)
passive = importlib.import_module(fixture["PACKAGE"] + ".pid_passive")
review = importlib.import_module(fixture["PACKAGE"] + ".pid_review")
production.passive_identity = passive.identity
production.passive_bounded_gains = passive.bounded_gains
production.AUTO_INTERVAL_S = passive.AUTO_INTERVAL_S
METHODS = (
    "_pid_passive_apply", "_pid_passive_auto_authorized",
    "_pid_review_authorized", "async_review_pid",
    "_interrupt_pid_learning", "observe_native_availability",
)
fixture["base"]["extract"](
    ROOT / "custom_components/environment_manager/equipment_runtime.py",
    METHODS, production.__dict__,
)


def profile(*, scoped=True, inherited=False, method="adaptive_auto"):
    common = {"control_mode": "pid", "kp": 20., "ki": .2, "kd": 3.,
              "pid_calibration_method": method}
    if not scoped:
        return common
    return {
        **common,
        "mode_settings_version": 1,
        "mode_settings": {
            "heat": {"control_mode": "pid", "pid_calibration_method": method,
                     **({} if inherited else {"kp": 20., "ki": .2, "kd": 3.})},
            # Deliberately inherit the same flat gains in another mode;
            # tuning Heat must neither replace this profile nor its fallback.
            "cool": {"control_mode": "pid", "pid_calibration_method": "adaptive_auto"},
        },
    }


class AdaptiveRuntime(fixture["Runtime"]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.readings.update(temperature_entity="sensor.room", humidity_entity="sensor.humidity")

    def evidence(self):
        cfg, cap = self.cfg, self.cap
        direction = cfg["requested_mode"]
        metric = "humidity" if direction == "dry" else "temperature"
        targets = model.targets(self.manager, SPEC, cap, cfg, self.manager.plan)
        goal = targets["humidity" if metric == "humidity" else direction]
        context = passive.identity(
            SPEC.area_id, list(SPEC.source_entities), cap.primary,
            direction, metric, self.readings[metric + "_entity"],
            model.profile_name(cfg, self.manager.plan), round(float(goal), 2),
            self.state.attributes.get("fan_mode"), self.state.attributes.get("percentage"),
        )
        cycle_at = self.now - 120
        self.record["pid_passive"] = {
            "context": context,
            "cycles": [{"at": cycle_at - (4 - index) * 7200,
                        "gain": 4., "tau": 28., "dead": 10., "r2": .99}
                       for index in range(5)],
            "summary": {
                "confidence": "high", "status": "validated", "metric": metric,
                "last_cycle_at": cycle_at, "valid_cycles": 5,
                "suggested_gains": {"kp": 80., "ki": 1., "kd": 0.},
                "identified_model": {"process_gain": 4., "time_constant_minutes": 28.,
                                     "dead_time_minutes": 10.},
            },
        }
        return context, cycle_at, cfg.get("operating_mode")

    def next_cycle(self):
        saved = self.record["pid_passive"]
        cycle_at = self.now - 120
        saved["cycles"] = [*saved["cycles"][-5:], {**saved["cycles"][-1], "at": cycle_at}]
        saved["summary"].update(last_cycle_at=cycle_at, valid_cycles=len(saved["cycles"]))
        return saved["context"], cycle_at, self.cfg.get("operating_mode")

    async def apply(self, evidence):
        context, cycle_at, operating_mode = evidence
        await self._pid_passive_apply(SPEC, context, cycle_at, operating_mode=operating_mode)


for method in METHODS:
    setattr(AdaptiveRuntime, method, getattr(production, method))


class AdaptationScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_writer_scopes_explicit_and_inherited_gains(self):
        for inherited in (False, True):
            with self.subTest(inherited=inherited):
                runtime = AdaptiveRuntime(profile=profile(inherited=inherited))
                before = deepcopy(runtime.raw())
                await runtime.apply(runtime.evidence())
                self.assertEqual(runtime.cfg["kp"], 22.)
                self.assertEqual(runtime.cfg["ki"], .22)
                self.assertEqual(runtime.cfg["kd"], 3., "Passive PI must preserve manual D")
                self.assertEqual(runtime.raw()["kp"], before["kp"], "Flat fallback is unchanged")
                self.assertEqual(runtime.raw()["mode_settings"]["cool"], before["mode_settings"]["cool"])
                self.assertEqual(model.settings_for_mode(runtime.manager, SPEC, "cool")["kp"], 20.)
                saved = runtime.cfg["pid_last_calibration"]
                self.assertEqual(saved["operating_mode"], "heat")
                self.assertEqual(saved["previous_gains"], {"kp": 20., "ki": .2, "kd": 3.})
                self.assertEqual(saved["applied_gains"], {"kp": 22., "ki": .22, "kd": 3.})
                self.assertEqual(runtime.calls, [])

    async def test_legacy_flat_application_remains_flat_and_bound_to_heat(self):
        runtime = AdaptiveRuntime(profile=profile(scoped=False))
        evidence = runtime.evidence()
        self.assertIsNone(evidence[2])
        await runtime.apply(evidence)
        self.assertEqual(runtime.cfg["kp"], 22.)
        self.assertNotIn("mode_settings", runtime.raw())
        self.assertEqual(runtime.cfg["pid_last_calibration"]["operating_mode"], "heat")
        self.assertEqual(runtime.calls, [])

    async def test_saved_interval_and_two_new_cycles_survive_reload(self):
        runtime = AdaptiveRuntime(profile=profile(inherited=True))
        await runtime.apply(runtime.evidence())
        # Configuration and evidence are serialized and loaded into a new
        # runtime, not retained through an in-memory alias of the old one.
        restored = AdaptiveRuntime(profile=json.loads(json.dumps(runtime.raw())))
        restored.record["pid_passive"] = json.loads(json.dumps(runtime.record["pid_passive"]))
        restored.now = runtime.now + 7200
        await restored.apply(restored.next_cycle())
        self.assertEqual(restored.cfg["kp"], 22., "A fresh cycle does not waive 24 hours")
        restored.now = runtime.now + 86400
        saved = restored.record["pid_passive"]
        # One fresh cycle only: the elapsed day does not waive the second one.
        saved["cycles"][-1]["at"] = restored.now - 120
        saved["summary"]["last_cycle_at"] = restored.now - 120
        await restored.apply((saved["context"], restored.now - 120, "heat"))
        self.assertEqual(restored.cfg["kp"], 22.)
        restored.now += 300
        await restored.apply(restored.next_cycle())
        self.assertEqual(restored.cfg["kp"], 24.2)
        self.assertEqual(restored.cfg["pid_last_calibration"]["previous_gains"]["kp"], 22.)
        self.assertEqual(restored.calls, [])

    async def test_queued_heating_model_cannot_tune_newly_selected_cooling(self):
        runtime = AdaptiveRuntime(profile=profile())
        heating_evidence = runtime.evidence()
        # Real mode-selection path and real settings writer; no direct change
        # of cfg or mocked effective settings hides the race under test.
        await runtime.async_request_mode(SPEC, "cool")
        self.assertEqual(runtime.cfg["operating_mode"], "cool")
        before = deepcopy(runtime.raw())
        await runtime.apply(heating_evidence)
        self.assertEqual(runtime.raw(), before)
        self.assertEqual(runtime.calls, [])

    async def test_legacy_direction_change_rejects_old_model_by_live_context(self):
        runtime = AdaptiveRuntime(profile=profile(scoped=False))
        heating_evidence = runtime.evidence()
        await runtime.async_request_mode(SPEC, "cool")
        before = deepcopy(runtime.raw())
        await runtime.apply(heating_evidence)
        self.assertEqual(runtime.raw(), before)
        self.assertEqual(runtime.calls, [])

    async def test_scoped_auto_application_waits_for_physical_controller_lock(self):
        runtime = AdaptiveRuntime(profile=profile())
        evidence = runtime.evidence()
        async with runtime._lock(SPEC.identifier):
            task = asyncio.create_task(runtime.apply(evidence))
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertEqual(runtime.cfg["kp"], 20.)
        await asyncio.wait_for(task, 1)
        self.assertEqual(runtime.cfg["kp"], 22.)
        self.assertEqual(runtime.calls, [])

    async def test_sensor_change_while_settings_lock_yields_rejects_stale_model(self):
        runtime = AdaptiveRuntime(profile=profile())
        evidence = runtime.evidence()
        before = deepcopy(runtime.raw())
        settings_lock = runtime.manager._device_settings_write_lock = asyncio.Lock()
        async with settings_lock:
            task = asyncio.create_task(runtime.apply(evidence))
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            runtime.readings["temperature_entity"] = "sensor.replacement"
        await asyncio.wait_for(task, 1)
        self.assertEqual(runtime.raw(), before)
        self.assertEqual(runtime.calls, [])

    async def test_native_control_edit_revokes_waiting_automatic_gain_application(self):
        controls = (
            ("temperature", 19.), ("target_temp_low", 17.),
            ("target_temp_high", 25.), ("humidity", 45.),
            ("preset_mode", "eco"), ("swing_mode", "vertical"),
            ("swing_horizontal_mode", "left"), ("mode", "eco"),
        )
        for field, value in controls:
            with self.subTest(field=field):
                runtime = AdaptiveRuntime(profile=profile())
                context, cycle_at, mode = runtime.evidence()
                before = deepcopy(runtime.raw())
                continuity = {
                    "generation": getattr(runtime, "_pid_learning_generation", {}).get(SPEC.identifier, 0),
                    "tuning_settings": review.tuning_signature(runtime.cfg),
                }
                previous = {key: runtime.cfg[key] for key in ("kp", "ki", "kd")}
                async with runtime._lock(SPEC.identifier):
                    task = asyncio.create_task(runtime._pid_passive_apply(
                        SPEC, context, cycle_at, operating_mode=mode,
                        continuity=continuity, previous_gains=previous,
                    ))
                    await asyncio.sleep(0)
                    self.assertFalse(task.done())
                    old = deepcopy(runtime.state)
                    runtime.state.attributes[field] = value
                    runtime.state.context = N(id="native-user-edit", user_id="fixture-user", parent_id=None)
                    self.assertEqual(runtime.state.state, "off")
                    runtime.observe_native_availability(PRIMARY, old, runtime.state)
                    self.assertGreater(runtime._pid_learning_generation[SPEC.identifier],
                                       continuity["generation"])
                await asyncio.wait_for(task, 1)
                self.assertEqual(runtime.raw(), before,
                                 "A native edit must revoke queued proof before manual reconciliation runs")
                self.assertEqual(runtime.calls, [])

    async def test_explicit_approval_scoped_and_legacy_preserve_effective_evidence(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                runtime = AdaptiveRuntime(profile=profile(scoped=scoped, method="adaptive_suggest"))
                context, cycle_at, mode = runtime.evidence()
                saved = runtime.record["pid_passive"]
                pending = review.proposal_for(runtime.cfg, saved["summary"], context, runtime.now)
                pending["operating_mode"] = mode or "heat"
                runtime.record["pid_passive_review"] = pending
                accepted = await runtime.async_review_pid(SPEC, "approve", operating_mode=mode)
                self.assertTrue(accepted)
                self.assertEqual(runtime.cfg["kp"], 22.)
                calibration = runtime.cfg["pid_last_calibration"]
                self.assertEqual(calibration["applied_gains"], {"kp": 22., "ki": .22, "kd": 3.})
                self.assertEqual(calibration["operating_mode"], "heat")
                self.assertEqual(runtime.record["pid_passive_review"]["state"], "applied")
                self.assertFalse(any(call["domain"] in ("climate", "switch", "humidifier")
                                     for call in runtime.calls))

    async def test_suggest_mode_never_applies_automatically(self):
        runtime = AdaptiveRuntime(profile=profile(method="adaptive_suggest"))
        evidence = runtime.evidence()
        before = deepcopy(runtime.raw())
        await runtime.apply(evidence)
        self.assertEqual(runtime.raw(), before)
        self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

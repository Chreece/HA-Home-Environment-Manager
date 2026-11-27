"""Generic adaptive integration through production source, guard and write paths.

The existing native fixture supplies HA state/registry/services and Store
transport. Sources are already-qualified numeric measurements; their production
aggregation, provenance, observer, controller gates, scoped writer and receipts
run unchanged. Candidate-search mathematics has its own plant simulations;
authorization tests inject a completed validated assessment into the real
observer to exercise races and commit recovery without fabricating hardware.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_074b2_pid_review_lifecycle.py"))
model, production, SPEC, PRIMARY, PACKAGE = (
    fixture[key] for key in ("model", "production", "SPEC", "PRIMARY", "PACKAGE"))
engine = importlib.import_module(PACKAGE + ".pid_adaptive")
store = importlib.import_module(PACKAGE + ".pid_adaptive_store")
sources = importlib.import_module(PACKAGE + ".room_sources")
METHODS = (
    "_pid_adaptive_actuator", "_pid_adaptive_peer_active", "_pid_adaptive_sample",
    "_pid_adaptive_expected_pending", "_pid_adaptive_ack_event",
    "_pid_adaptive_live_sample", "_pid_adaptive_context", "_pid_adaptive_status",
    "_pid_adaptive_remember", "_pid_adaptive_observe_sample", "_pid_adaptive_authorized",
    "_pid_adaptive_review_authorized", "_pid_adaptive_apply", "_pid_review_maintenance",
    "async_review_pid", "_interrupt_pid_learning", "_pid_learning_observed",
)
fixture["fixture"]["fixture"]["base"]["extract"](
    ROOT / "custom_components/environment_manager/equipment_runtime.py",
    (*METHODS, "_reported_timestamp", "measurements"), production.__dict__)


def stamp(at):
    return datetime.fromtimestamp(at, timezone.utc)


class Runtime(fixture["LifecycleRuntime"]):
    def __init__(self, *, method="adaptive_auto"):
        super().__init__(method=method)
        self._pid_adaptive_observers, self._pid_adaptive_samples, self._pid_adaptive_tasks = {}, {}, {}
        self.state.last_reported = stamp(self.now)
        self.state.last_updated = stamp(self.now)
        for entity, value, metric in (("sensor.first", 18., "temperature"),
                                     ("sensor.second", 20., "temperature"),
                                     ("sensor.rh", 55., "humidity"),
                                     ("sensor.co2", 900., "co2"),
                                     ("sensor.pm", 30., "pm25")):
            self.extra_states[entity] = N(
                entity_id=entity, domain="sensor", state=str(value), metric=metric,
                attributes={}, last_reported=stamp(self.now), last_updated=stamp(self.now))
        self.manager.entry.options["room_sources"] = {SPEC.area_id: {
            "temperature": ["sensor.first", "sensor.second"],
            "humidity": ["sensor.rh"], "air_quality": ["sensor.co2", "sensor.pm"],
        }}
        self.manager.plan["air_actions"] = {"thresholds": {
            "co2_operational_ppm": 800., "pm25_short_term_action_ug_m3": 15.}}

    def _window_policy(self, *args, **kwargs):
        return dict(self.window)  # Qualified fixture contact/policy input.

    measurements = production.measurements

    def infer_direction(self, **settings):
        """An existing flat PID configuration delegates direction to HEM."""
        raw = self.raw()
        for key in ("requested_mode", "mode_settings_version", "mode_settings"):
            raw.pop(key, None)
        raw.update(settings)
        self.manager.entry.options[model.SETTINGS][SPEC.identifier] = raw
        return raw

    def sample(self, **kwargs):
        return self._pid_adaptive_live_sample(SPEC, **kwargs)

    def native_report(self, *, mode=None, action=None, target=None):
        if mode is not None:
            self.state.state = mode
        if action is None:
            self.state.attributes.pop("hvac_action", None)
        else:
            self.state.attributes["hvac_action"] = action
        if target is not None:
            self.state.attributes["temperature"] = target
        self.state.last_reported = stamp(self.now)
        self.state.last_updated = stamp(self.now)

    def evidence(self):
        sample = self.sample()
        assert sample is not None and sample["safe"] and sample["output_verified"], sample
        observer = engine.AdaptiveObserver(stepper=model.pid_step, transfer=model.pid_bumpless)
        for index in range(engine.ASSESS_EVERY):
            at = self.now - (engine.ASSESS_EVERY-1-index) * self.cfg["sample_seconds"]
            observer.observe({**sample, "observed_at": at, "reported_at": at, "output_at": at})
        current = {key: self.cfg[key] for key in ("kp", "ki", "kd")}
        candidate = {"validated": True, "evidence_id": "a" * 64,
                     "evidence_at": self.now, "context": sample["context"],
                     "previous_gains": current, "validated_windows": 2,
                     "predicted_improvement": .1,
                     "kp": current["kp"] * .95, "ki": current["ki"] * .95,
                     "kd": current["kd"]}
        observer._assessment = {
            "status": "candidate", "reason": "validated_improvement", "candidate": candidate,
            "performance": {"observed_seconds": 2400., "mean_error": 2.},
            "model": {"gain": 5., "tau_seconds": 600.},
        }
        self._pid_adaptive_observers[SPEC.identifier] = observer
        self._pid_adaptive_remember(self.record, sample["context"], observer.ledger())
        return observer

    def proof(self, approved_id=None):
        observer = self._pid_adaptive_observers.get(SPEC.identifier) or self.evidence()
        proof = store.make_proof(self.cfg, observer.snapshot(), observer.context, self.now,
                                 approved_id=approved_id)
        assert proof is not None, observer.snapshot()
        proof["generation"] = self._pid_learning_generation.get(SPEC.identifier, 0)
        return proof

    def changes(self, proof):
        return {**proof["apply"], "pid_last_calibration": store.calibration_receipt(proof, self.now)}

    def trim_control(self):
        """A real legacy soft setpoint grant, without compressor permission."""
        self.manager.entry.options[model.SETTINGS][SPEC.identifier].pop("_native_authorization", None)
        self.manager.device["method"] = "setpoint"
        self.state.attributes["target_temp_step"] = .25
        self.native_report(mode="heat", action="heating", target=21.75)
        self.seed_math()
        signature, _, anchor = self._memory[SPEC.identifier]
        self._memory[SPEC.identifier] = (
            signature, model.PIDMemory(10.3, 19., self.now-120, .1, 50.), anchor)


for method in METHODS:
    setattr(Runtime, method, getattr(production, method))


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        def qualified_numeric(hass, entity, area, group, age):
            state = hass.states.get(entity)
            if state is None or state.state in ("unknown", "unavailable"):
                return None
            if hass.fixture.now - state.last_reported.timestamp() > age * 60:
                return None
            return float(state.state)
        self.patches = [
            patch.object(sources, "numeric", qualified_numeric),
            patch.object(sys.modules[PACKAGE + ".discovery"], "supported_metric",
                         lambda hass, state, **kwargs: state.metric, create=True),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    async def test_exact_selected_mean_and_true_report_times_feed_observer(self):
        runtime = Runtime()
        sample = runtime.sample()
        self.assertEqual(sample["measured"], 19.)
        self.assertEqual(sample["feedback"]["contributor_ids"], ["sensor.first", "sensor.second"])
        self.assertEqual(sample["feedback"]["aggregation"], "mean")
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, sample)
        observer = runtime._pid_adaptive_observers[SPEC.identifier]
        self.assertEqual(len(observer.points), 1)
        runtime.now += 30
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, runtime.sample())
        self.assertEqual(len(observer.points), 1, "Polling one HA report is not new evidence")
        runtime.extra_states["sensor.second"].state = "22"
        runtime.extra_states["sensor.second"].last_reported = stamp(runtime.now)
        fresh = runtime.sample()
        self.assertEqual(fresh["measured"], 20.)
        self.assertEqual(fresh["reported_at"], runtime.now)
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, fresh)
        self.assertEqual(len(observer.points), 2)
        runtime.extra_states["sensor.second"].state = "unavailable"
        partial = runtime.sample()
        self.assertEqual(partial["measured"], 18.)
        self.assertEqual(partial["feedback"]["contributor_ids"], ["sensor.first"])
        self.assertNotEqual(partial["context"], fresh["context"])

    def test_humidifier_native_auto_binds_humidifying_activity_to_its_logical_mode(self):
        runtime = Runtime()
        runtime.infer_direction()
        runtime.state.state = "on"
        runtime.state.domain = "humidifier"
        runtime.state.attributes["action"] = "humidifying"
        cap = N(**{**asdict(runtime.cap), "domain": "humidifier", "modes": ("off", "auto"),
                   "humidifying": True})
        sample = runtime.sample(cap=cap)
        self.assertEqual((sample["native_mode"], sample["operating_mode"]), ("auto", "humidify"))
        self.assertEqual(sample["physical_activity"], "on")
        self.assertEqual(sample["observed_output"], 100.)
        runtime.state.attributes["action"] = "drying"
        self.assertFalse(runtime.sample(cap=cap)["output_verified"])

    async def test_reached_target_is_observed_without_waiting_for_a_long_on_cycle(self):
        runtime = Runtime()
        runtime.extra_states["sensor.first"].state = "21"
        runtime.extra_states["sensor.second"].state = "21"
        sample = runtime.sample()
        sample["requested_output"] = 0.
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, sample)
        observer = runtime._pid_adaptive_observers[SPEC.identifier]
        self.assertEqual(len(observer.points), 1)
        self.assertEqual(observer.points[-1]["value"], 21.)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_generic_metrics_direction_and_threshold_semantics(self):
        runtime = Runtime()
        for mode, metric, increasing, semantic in (
                ("heat", "temperature", True, "band"),
                ("cool", "temperature", False, "band"),
                ("dry", "humidity", False, "band"),
                ("fan_only", "co2", False, "upper_threshold")):
            with self.subTest(mode=mode):
                cfg = {**runtime.cfg, "requested_mode": mode, "operating_mode": mode}
                sample = runtime.sample(cfg=cfg)
                self.assertEqual((sample["metric"], sample["increasing"], sample["target_semantics"]),
                                 (metric, increasing, semantic))
        runtime.manager.device["fan_purpose"] = "filtration"
        sample = runtime.sample(cfg={**runtime.cfg, "requested_mode": "fan_only", "operating_mode": "fan_only"})
        self.assertEqual(sample["metric"], "pm25")

    async def test_native_command_feedback_needs_ownership_and_confirmed_target(self):
        runtime = Runtime()
        runtime.native_report(mode="off")
        before = runtime.sample()
        self.assertEqual(before["output_kind"], "acknowledged_native_command")
        self.assertTrue(before["output_verified"])
        runtime.native_report(mode="heat", target=runtime.state.attributes["max_temp"])
        self.assertFalse(runtime.sample()["output_verified"], "Foreign ON cannot be learnt as HEM output")
        runtime.record["power"][PRIMARY] = {"since": runtime.now-900, "min_on": 600., "max_on": 7200.}
        self.assertFalse(runtime.sample()["output_verified"], "An acknowledged mode and target do not prove activity")
        runtime.native_report(action="idle")
        self.assertEqual(runtime.sample()["observed_output"], 0.)
        runtime.native_report(action="heating")
        running = runtime.sample()
        self.assertTrue(running["output_verified"])
        self.assertEqual(running["observed_output"], 100.)
        self.assertEqual(running["physical_activity"], "on")
        self.assertEqual(before["context"], running["context"], "OFF/ON does not redefine the plant")
        runtime.state.attributes["temperature"] = 20.
        self.assertFalse(runtime.sample()["output_verified"])
        runtime.state.attributes["temperature"] = runtime.state.attributes["max_temp"]
        runtime.record["pending"] = {"phase": "commanded"}
        self.assertFalse(runtime.sample()["safe"])
        self.assertIn("pending_command", runtime.sample()["constraints"])

    async def test_external_heat_blocks_off_baseline_before_any_heater_warning(self):
        runtime = Runtime()
        runtime.native_report(mode="off")
        self.assertTrue(runtime.sample()["output_verified"])
        runtime.record["thermal_off_watch"] = {"external_heat_pending": True, "attempts": 0}
        self.assertFalse(runtime.sample()["output_verified"])
        runtime.record["thermal_off_watch"].pop("external_heat_pending")
        self.assertTrue(runtime.sample()["output_verified"])
        self.assertEqual(runtime.hardware_calls, [])

    def test_activity_requires_consistent_feedback_for_each_actuator(self):
        activity = importlib.import_module(PACKAGE + ".pid_diagnostics").calibration_activity
        for domain, state, mode, attrs, expected in (
                ("switch", "on", "heat", {}, None),
                ("humidifier", "on", "dry", {"action": "drying"}, "on"),
                ("humidifier", "on", "humidify", {"action": "drying"}, None),
                ("fan", "on", "fan_only", {"percentage": 100}, None),
                ("fan", "on", "fan_only", {"rpm": 705}, "on"),
                ("climate", "heat", "heat", {"actual_position": 30}, "on"),
                ("climate", "heat", "heat", {"actual_position": 0}, "off"),
                ("climate", "off", "heat", {"actual_position": 30, "hvac_action": "idle"}, None),
                ("climate", "heat", "heat", {"hvac_action": "heating", "restored": True}, None)):
            with self.subTest(domain=domain, mode=mode, attrs=attrs):
                self.assertEqual(activity(domain, N(state=state, attributes=attrs), mode), expected)

    async def test_completed_results_survive_pause_and_mode_round_trip_in_store(self):
        runtime = Runtime(method="adaptive_suggest")
        heat = runtime.sample()
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, heat)
        observer = runtime._pid_adaptive_observers[SPEC.identifier]
        completed = {"at": runtime.now, "status": "tracking_well"}
        observer.windows.append(completed)
        runtime._interrupt_pid_learning(SPEC, "controller_paused")
        self.assertEqual(list(observer.points), [])
        for mode in ("cool", "heat"):
            runtime.manager.entry.options[model.SETTINGS][SPEC.identifier]["requested_mode"] = mode
            runtime.now += 5
            sample = runtime.sample()
            self.assertEqual(json.loads(sample["context"])["operating_mode"], mode)
            await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, sample)
        persisted = runtime._store.payload["records"][SPEC.identifier]
        self.assertEqual(persisted["pid_adaptive"]["context"], heat["context"])
        self.assertEqual(persisted["pid_adaptive"]["ledger"]["windows"], [completed])

    async def test_reported_stale_restored_output_explains_live_hold(self):
        runtime = Runtime()
        runtime.state.last_reported = stamp(runtime.now - 2000)
        sample = runtime.sample()
        self.assertFalse(sample["output_verified"])
        self.assertIn("output_unverified", sample["constraints"])
        runtime.state.last_reported = stamp(runtime.now)
        runtime.state.attributes["restored"] = True
        self.assertIn("output_unverified", runtime.sample()["constraints"])

    async def test_status_and_review_availability_never_allocate_records(self):
        runtime = Runtime()
        runtime.records.clear()
        before = deepcopy(runtime.records)
        status = runtime._pid_adaptive_status(SPEC)
        self.assertFalse(status["context_verified"])
        self.assertEqual(status["feedback"]["value"], 19.)
        self.assertFalse(runtime._pid_adaptive_review_authorized(SPEC, "a"*32))
        self.assertEqual(runtime.records, before)

    async def test_actual_binary_writer_is_scoped_and_starts_verification(self):
        runtime = Runtime()
        before = deepcopy(runtime.raw())
        proof = runtime.proof()
        self.assertTrue(runtime._pid_adaptive_authorized(SPEC, runtime.changes(proof), proof))
        self.assertTrue(await runtime._pid_adaptive_apply(SPEC, proof))
        self.assertEqual(runtime.cfg["kp"], proof["apply"]["kp"])
        self.assertEqual(runtime.raw()["mode_settings"]["cool"], before["mode_settings"]["cool"])
        self.assertEqual(runtime.raw()["kp"], before["kp"])
        self.assertEqual(runtime.cfg["pid_last_calibration"]["method"], "performance_adaptive")
        self.assertEqual(runtime._pid_adaptive_observers[SPEC.identifier].trial["state"], "evaluating")
        self.assertEqual(runtime.hardware_calls, [])

    async def test_running_binary_pending_and_interruption_reject_the_same_proof(self):
        for change in ("running", "pending", "interrupted", "stale_input"):
            with self.subTest(change=change):
                runtime = Runtime()
                proof = runtime.proof()
                if change == "running":
                    runtime.native_report(mode="heat", target=runtime.state.attributes["max_temp"])
                    runtime.record["power"][PRIMARY] = {"since": runtime.now-900, "min_on": 600., "max_on": 7200.}
                elif change == "pending":
                    runtime.record["pending"] = {"phase": "commanded"}
                elif change == "interrupted":
                    runtime._interrupt_pid_learning(SPEC, "manual_override")
                else:
                    for entity in ("sensor.first", "sensor.second"):
                        runtime.extra_states[entity].last_reported = stamp(runtime.now-601)
                self.assertFalse(await runtime._pid_adaptive_apply(SPEC, proof))
                self.assertEqual(runtime.cfg["kp"], 20.)
                self.assertEqual(runtime.config_commits, [])

    async def test_source_context_is_rechecked_after_shared_options_lock(self):
        runtime = Runtime()
        proof = runtime.proof()
        lock = runtime.manager._device_settings_write_lock = asyncio.Lock()
        await lock.acquire()
        task = asyncio.create_task(runtime._pid_adaptive_apply(SPEC, proof))
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        runtime.manager.entry.options["room_sources"][SPEC.area_id]["temperature"] = ["sensor.first"]
        lock.release()
        self.assertFalse(await task)
        self.assertEqual(runtime.config_commits, [])

    async def test_suggest_approval_consumes_exact_evidence_and_receipt(self):
        runtime = Runtime(method="adaptive_suggest")
        observer = runtime.evidence()
        proposal = store.proposal_for(runtime.cfg, observer.snapshot(), observer.context, runtime.now)
        runtime.record["pid_passive_review"] = proposal
        await runtime._save()
        self.assertTrue(runtime._pid_adaptive_review_authorized(SPEC, proposal["id"]))
        self.assertFalse(runtime._pid_adaptive_review_authorized(SPEC, "b"*32))
        self.assertTrue(await runtime.async_review_pid(SPEC, "approve", token=proposal["id"]))
        await runtime.drain()
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "applied")
        self.assertEqual(runtime.cfg["pid_last_calibration"]["method"], "performance_approved")
        self.assertEqual(runtime.hardware_calls, [])

    async def test_inactive_manual_edit_persists_bank_only_invalidation(self):
        runtime = Runtime()
        heat = json.dumps({"version": 1, "operating_mode": "heat", "target": 21})
        cool = json.dumps({"version": 1, "operating_mode": "cool", "target": 26})
        for context in (cool, heat):
            runtime._pid_adaptive_remember(runtime.record, context, {
                "version": 1, "algorithm": store.ALGORITHM, "context": context,
                "raw_history_saved": False, "windows": [], "assessment": {},
            })
        await runtime._save()
        await runtime.async_update(SPEC, {"kp": 25.}, operating_mode="cool")
        persisted = runtime._store.payload["records"][SPEC.identifier]
        self.assertNotIn(cool, persisted["pid_adaptive_contexts"])
        self.assertIn(heat, persisted["pid_adaptive_contexts"])
        self.assertEqual(persisted["pid_adaptive"]["context"], heat)

    async def test_context_bank_is_bounded_and_never_restores_partial_history(self):
        runtime = Runtime()
        for index in range(15):
            runtime.now += 1
            context = json.dumps({"version": 1, "operating_mode": "heat", "target": index})
            runtime._pid_adaptive_remember(runtime.record, context, {
                "version": 1, "algorithm": store.ALGORITHM, "context": context,
                "raw_history_saved": False, "windows": [], "assessment": {},
            })
        self.assertEqual(len(runtime.record["pid_adaptive_contexts"]), 12)
        current = deepcopy(runtime.record["pid_adaptive"])
        runtime._pid_adaptive_remember(runtime.record, "bad json", {
            "version": 1, "algorithm": store.ALGORITHM, "context": "bad json", "raw_history_saved": False})
        self.assertEqual(runtime.record["pid_adaptive"], current)
        restored = engine.AdaptiveObserver(saved=current["ledger"], now=runtime.now,
                                           stepper=model.pid_step, transfer=model.pid_bumpless)
        self.assertEqual(len(restored.points), 0)
        self.assertFalse(restored.snapshot()["fresh_evidence"])

    async def test_quiet_hours_upgrade_restores_old_learning_without_reusing_it_for_opt_in(self):
        runtime = Runtime(method="adaptive_suggest")
        runtime.state.attributes.update(fan_modes=["low", "high"], fan_mode="high")
        runtime.state.attributes["supported_features"] |= model.FAN
        sample = runtime.sample()
        # A 0.7.5 journal could not include the new shared quiet-hours key.
        old_context = json.loads(sample["context"])
        old_context["policy"].pop("quiet_hours", None)
        old_context = json.dumps(old_context, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        window = {"evidence_id": "c" * 64, "at": runtime.now - 60,
                  "samples": 20, "observed_seconds": 2400.,
                  "performance": {"mean_error": .3},
                  "status": "stable", "reason": "stable_control"}
        runtime._pid_adaptive_remember(runtime.record, old_context, {
            "version": 1, "algorithm": store.ALGORITHM, "context": old_context,
            "raw_history_saved": False, "windows": [window], "assessment": {},
        })
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, sample)
        restored = runtime._pid_adaptive_observers[SPEC.identifier]
        self.assertEqual(restored.context, old_context)
        self.assertEqual(restored.windows, [window])
        self.assertLessEqual(len(restored.points), 1, "Upgrade must not invent raw observations")

        # A completed assessment recorded after the last periodic save must
        # survive a trip through a different context and an automatic pause.
        newer = {**window, "at": runtime.now}
        restored.windows.append(newer)
        runtime._interrupt_pid_learning(SPEC, "window_open_pause")
        await runtime.async_update(SPEC, {"quiet_hours": True})
        opted_in = runtime.sample()
        self.assertNotEqual(opted_in["context"], old_context)
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, opted_in)
        self.assertEqual(runtime._pid_adaptive_observers[SPEC.identifier].windows, [])
        await runtime.async_update(SPEC, {"quiet_hours": False})
        opted_out = runtime.sample()
        self.assertEqual(opted_out["context"], old_context)
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, opted_out)
        self.assertEqual(runtime._pid_adaptive_observers[SPEC.identifier].windows, [window, newer])
        self.assertEqual(runtime.hardware_calls, [])

    async def test_native_trim_uses_reported_target_without_clipping_foreign_targets(self):
        runtime = Runtime()
        runtime.trim_control()
        sample = runtime.sample()
        self.assertEqual(model.permission(runtime.manager, SPEC, runtime.cap), (True, False))
        self.assertEqual(sample["actuator_kind"], "setpoint_trim")
        self.assertEqual(sample["output_kind"], "acknowledged_target")
        self.assertAlmostEqual(sample["observed_output"], 50.)
        self.assertAlmostEqual(sample["max_output_change"], 100/3)
        self.assertEqual(sample["output_quantization"], "native_half_up")
        runtime.native_report(target=20.)
        self.assertFalse(runtime.sample()["output_verified"])
        self.assertIsNone(runtime.sample()["observed_output"], "A foreign below-goal target is not zero effort")
        runtime.native_report(target=25.)
        self.assertFalse(runtime.sample()["output_verified"])

    async def test_flat_inferred_direction_binds_auto_and_review_writes(self):
        for method in ("adaptive_auto", "adaptive_suggest"):
            with self.subTest(method=method):
                runtime = Runtime(method=method)
                raw = runtime.infer_direction()
                observer = runtime.evidence()
                status = observer.snapshot()
                if method == "adaptive_auto":
                    proof = runtime.proof()
                    self.assertEqual(proof["operating_mode"], "heat")
                    # The same device can now need cooling. The old heat proof
                    # must fail even though the configuration has not changed.
                    for entity in ("sensor.first", "sensor.second"):
                        runtime.extra_states[entity].state = "32"
                    self.assertFalse(await runtime._pid_adaptive_apply(SPEC, proof))
                    self.assertEqual(runtime.config_commits, [])
                    for entity in ("sensor.first", "sensor.second"):
                        runtime.extra_states[entity].state = "19"
                    self.assertTrue(await runtime._pid_adaptive_apply(SPEC, proof))
                else:
                    proposal = store.proposal_for(runtime.cfg, status, observer.context, runtime.now)
                    runtime.record["pid_passive_review"] = proposal
                    await runtime._pid_review_maintenance(SPEC)
                    self.assertTrue(runtime._pid_adaptive_review_authorized(SPEC, proposal["id"]))
                    self.assertTrue(await runtime.async_review_pid(
                        SPEC, "approve", token=proposal["id"], operating_mode="heat"))
                self.assertEqual(runtime.cfg["pid_last_calibration"]["operating_mode"], "heat")
                self.assertEqual(set(runtime.raw()["mode_settings"]), {"heat"})
                self.assertEqual(runtime.raw()["kp"], raw["kp"])
                self.assertEqual(model.settings_for_mode(runtime.manager, SPEC, "cool")["kp"], raw["kp"])
                self.assertIsNone(runtime.raw().get("requested_mode"))
                self.assertEqual(len(runtime.config_commits), 1)
                self.assertEqual(runtime.hardware_calls, [])

    async def test_continuous_actual_writer_preserves_memory_phase_and_dwell(self):
        runtime = Runtime()
        runtime.trim_control()
        before_signature, before_memory, before_anchor = runtime._memory[SPEC.identifier]
        runtime.record["pid_pwm_run"] = {"served_at": runtime.now-200, "marker": "keep"}
        physical = deepcopy({key: runtime.record.get(key) for key in ("power", "off_at", "pid_pwm_run")})
        proof = runtime.proof()
        self.assertTrue(await runtime._pid_adaptive_apply(SPEC, proof))
        signature, memory, anchor = runtime._memory[SPEC.identifier]
        self.assertEqual(signature[:6], before_signature[:6])
        self.assertEqual(signature[6:9], tuple(proof["apply"][key] for key in ("kp", "ki", "kd")))
        self.assertEqual(signature[9:], before_signature[9:])
        self.assertEqual(anchor, before_anchor)
        self.assertEqual((memory.measured, memory.stamp, memory.derivative, memory.demand),
                         (before_memory.measured, before_memory.stamp, before_memory.derivative, before_memory.demand))
        self.assertNotEqual(memory.integral, before_memory.integral)
        self.assertEqual({key: runtime.record.get(key) for key in physical}, physical)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_confirmed_regression_restores_only_the_receipted_trial(self):
        runtime = Runtime()
        first = runtime.proof()
        self.assertTrue(await runtime._pid_adaptive_apply(SPEC, first))
        observer = runtime._pid_adaptive_observers[SPEC.identifier]
        receipt = deepcopy(runtime.cfg["pid_last_calibration"])
        for _ in range(engine.ASSESS_EVERY):
            runtime.now += 300
            runtime.native_report(mode="off", action="off")
            for entity in ("sensor.first", "sensor.second"):
                runtime.extra_states[entity].last_reported = stamp(runtime.now)
            observer.observe(runtime.sample())
        observer.trial.update(state="rollback_recommended", reason="confirmed_regression",
            evidence_id="b"*64, evidence_at=runtime.now,
            previous_gains=deepcopy(first["apply"]), revert_gains=deepcopy(first["current"]),
            application=receipt)
        rollback = store.make_proof(runtime.cfg, observer.snapshot(), observer.context,
                                    runtime.now, rollback=True)
        self.assertIsNotNone(rollback)
        rollback["generation"] = runtime._pid_learning_generation.get(SPEC.identifier, 0)
        self.assertTrue(await runtime._pid_adaptive_apply(SPEC, rollback, rollback=True))
        self.assertEqual({key: runtime.cfg[key] for key in ("kp", "ki", "kd")}, first["current"])
        self.assertEqual(runtime.cfg["pid_last_calibration"]["method"], "performance_rollback")
        self.assertEqual(observer.trial["state"], "reverted")
        self.assertEqual(len(runtime.config_commits), 2)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_legacy_pending_proposal_expires_before_generic_observer_starts(self):
        runtime = Runtime(method="adaptive_suggest")
        runtime.record["pid_passive_review"] = {
            "id": "a"*32, "state": "pending", "created_at": runtime.now,
            "context": "legacy", "current": {"kp": 20., "ki": .2, "kd": 3.},
            "apply": {"kp": 21., "ki": .21, "kd": 3.},
        }
        await runtime._pid_review_maintenance(SPEC)
        await runtime.drain()
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "expired")
        self.assertEqual(runtime.record["pid_passive_review"]["reason"], "calibration_algorithm_updated")
        self.assertFalse(runtime._pid_adaptive_observers)
        self.assertFalse(await runtime.async_review_pid(SPEC, "approve", token="a"*32))
        self.assertEqual(runtime.config_commits, [])

    async def test_interruption_after_atomic_commit_recovers_trial_without_duplicate_write(self):
        runtime = Runtime()
        runtime.trim_control()
        proof = runtime.proof()
        original = runtime._checkpoint_pid
        async def interrupted_checkpoint(*args):
            await original(*args)
            raise asyncio.CancelledError("after exact config and bumpless-state commit")
        runtime._checkpoint_pid = interrupted_checkpoint
        with self.assertRaises(asyncio.CancelledError):
            await runtime._pid_adaptive_apply(SPEC, proof)
        self.assertEqual(len(runtime.config_commits), 1)
        self.assertEqual(runtime.cfg["pid_last_calibration"]["evidence_id"], proof["evidence_id"])
        self.assertIsNone(runtime._pid_adaptive_observers[SPEC.identifier].trial)
        runtime._checkpoint_pid = original
        await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, runtime.sample())
        await runtime.drain()
        self.assertEqual(len(runtime.config_commits), 1)
        observer = runtime._pid_adaptive_observers[SPEC.identifier]
        self.assertEqual(observer.trial["state"], "evaluating")
        self.assertEqual(observer.trial["application"]["evidence_id"], proof["evidence_id"])
        self.assertEqual(len(observer.points), 0, "Verification starts with a fresh response interval")

    async def test_executor_snapshot_is_discarded_after_native_or_source_change(self):
        for change in ("native", "source", "manual_gain"):
            with self.subTest(change=change):
                runtime = Runtime()
                await runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, runtime.sample())
                original = runtime._pid_adaptive_observers[SPEC.identifier]
                entered, release = asyncio.Event(), asyncio.Event()
                async def executor(function, sample):
                    self.assertIsNot(function.__self__, original)
                    entered.set()
                    await release.wait()
                    return function(sample)
                runtime.hass.async_add_executor_job = executor
                runtime.now += 300
                for entity in ("sensor.first", "sensor.second"):
                    runtime.extra_states[entity].last_reported = stamp(runtime.now)
                task = asyncio.create_task(runtime._pid_adaptive_observe_sample(SPEC, runtime.cfg, runtime.sample()))
                await entered.wait()
                if change == "native":
                    runtime._interrupt_pid_learning(SPEC, "native_command_acknowledged", preserve_adaptive=True)
                    original.observe_output(runtime.now, 100.)
                elif change == "source":
                    runtime.manager.entry.options["room_sources"][SPEC.area_id]["temperature"] = ["sensor.first"]
                else:
                    runtime.manager.entry.options[model.SETTINGS][SPEC.identifier]["mode_settings"]["heat"]["kp"] = 23.
                release.set()
                await task
                self.assertIs(runtime._pid_adaptive_observers[SPEC.identifier], original)
                self.assertEqual(len(original.points), 1)
                self.assertEqual(runtime.config_commits, [])
                if change == "native":
                    self.assertEqual(original.events[-1], (runtime.now, 1.))

    async def test_peer_heater_confounds_response_without_hiding_actual_measurement(self):
        runtime = Runtime()
        peer_entity = "climate.second_heater"
        peer = model.ManagedDevice("peer", SPEC.area_id, "Peer", "second-device", (peer_entity,))
        runtime.manager._device_hierarchy["controllers"][peer.identifier] = {"spec": peer}
        room = runtime.manager.entry.data["climate_rooms"][SPEC.area_id]
        room["selected_devices"].append(peer_entity)
        room["device_settings"][peer_entity] = {**runtime.manager.device}
        runtime.registry_rows[peer_entity] = N(entity_id=peer_entity, id="peer-registry", unique_id="peer-native",
                                             device_id="second-device", platform="native", area_id=SPEC.area_id)
        runtime.extra_states[peer_entity] = deepcopy(runtime.state)
        runtime.extra_states[peer_entity].state = "heat"
        runtime.extra_states[peer_entity].attributes["hvac_action"] = "heating"
        sample = runtime.sample()
        self.assertEqual(sample["measured"], 19.)
        self.assertTrue(sample["safe"])
        self.assertIn("other_controller_active", sample["constraints"])
        runtime.extra_states[peer_entity].state = "off"
        runtime.extra_states[peer_entity].attributes["hvac_action"] = "off"
        self.assertNotIn("other_controller_active", runtime.sample()["constraints"])

    async def test_allocator_metadata_matches_real_numeric_fan_and_stage_commands(self):
        runtime = Runtime()
        cap = runtime.cap
        fake = lambda **changes: N(**{**asdict(cap), **changes})
        state = deepcopy(runtime.state)
        state.state = "46.0"
        state.attributes.update(unit_of_measurement="%", min=0, max=100, step=2.)
        with patch.object(model, "permission", lambda *args: (True, True)):
            numeric = runtime._pid_adaptive_actuator(SPEC, runtime.cfg,
                fake(domain="number"), runtime.manager.plan, state, "heat", 21., 53.05)
            self.assertEqual(numeric["constrained_output"], 52.)
            self.assertEqual(numeric["max_output_change"], 10.)
            runtime.state.state = "on"
            runtime.state.attributes["percentage"] = 50.
            percent_cap = fake(domain="fan", fan_entity=PRIMARY, fan_percentage=True,
                               fan_modes=("25", "50", "75", "100"))
            percent = runtime._pid_adaptive_actuator(SPEC, runtime.cfg, percent_cap,
                runtime.manager.plan, runtime.state, "fan_only", 800., 64.)
            self.assertEqual(percent["constrained_output"], 75.)
            self.assertEqual(percent["output_stages"], [25., 50., 75., 100.])
            with patch.object(runtime, "_quiet_context", lambda *args: True):
                quiet = runtime._pid_adaptive_actuator(SPEC, {**runtime.cfg, "quiet_percentage": 60.}, percent_cap,
                    runtime.manager.plan, runtime.state, "fan_only", 800., 64.)
                self.assertEqual(quiet["constrained_output"], 50.)
                self.assertEqual(quiet["output_quantization"], "floor")
                runtime.state.attributes["fan_mode"] = "medium"
                stage = runtime._pid_adaptive_actuator(SPEC, {**runtime.cfg, "quiet_fan_mode": "medium"},
                    fake(domain="climate", fan_entity=PRIMARY, fan_percentage=False, fan_modes=("low", "medium", "high")),
                    runtime.manager.plan, runtime.state, "fan_only", 800., 100.)
                self.assertAlmostEqual(stage["max_percentage"], 200/3)
                self.assertAlmostEqual(stage["constrained_output"], 200/3)


if __name__ == "__main__":
    unittest.main()

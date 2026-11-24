"""Normal command acknowledgements preserve real adaptive observation history.

Use the production event hook, complete tick, command journal, acknowledgement
reconciliation, observer and write guard. Only HA transport, already-qualified
room inputs, time and Store transport come from the existing runtime fixture.
No learned response/model is seeded in the continuity tests.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import importlib
import math
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_074b4_pid_adaptive_runtime.py"))
SPEC, PRIMARY, model, production, stamp = (
    fixture[key] for key in ("SPEC", "PRIMARY", "model", "production", "stamp"))
transport = fixture["fixture"]["fixture"]["fixture"]["Runtime"]


class EventRuntime(fixture["Runtime"]):
    # Restore only the original simulated HA service transport; LifecycleRuntime
    # normally forbids hardware calls because its tests exercise gain writes.
    service_call = transport.service_call

    def feedback(self, value):
        for key in ("sensor.first", "sensor.second"):
            state = self.extra_states[key]
            state.state = str(value)
            state.last_reported = state.last_updated = stamp(self.now)

    def native_event(self, expected=None, *, entity=PRIMARY, mode=None, user_id=None, **attrs):
        current = self.state if entity == PRIMARY else self.extra_states[entity]
        old, new = deepcopy(current), deepcopy(current)
        expected = expected or {}
        if "state" in expected:
            new.state = expected["state"]
        if mode is not None:
            new.state = mode
        new.attributes.update(expected.get("attributes", {}))
        new.attributes.update(attrs)
        new.last_reported = new.last_updated = stamp(self.now)
        if old.state != new.state:
            new.last_changed = stamp(self.now)
        if user_id is not None:
            new.context = N(user_id=user_id, parent_id=None, id="physical-user-change")
        if entity == PRIMARY:
            self.state = new
        else:
            self.extra_states[entity] = new
        self.observe_native_availability(entity, old, new)

    async def acknowledge(self):
        """Report the actual requested native state, then run its real ACK path."""
        acknowledgements = 0
        while self.record.get("pending"):
            pending = deepcopy(self.record["pending"])
            assert pending["phase"] == "commanded", pending
            assert pending["attempts"] == 1, pending
            assert pending["entity"] in SPEC.source_entities, pending
            self.now += 1
            activity = {}
            if pending["entity"] == PRIMARY and "state" in pending["expected"]:
                mode = pending["expected"]["state"]
                activity["hvac_action"] = {"heat": "heating", "cool": "cooling", "off": "off"}.get(mode)
            self.native_event(pending["expected"], entity=pending["entity"], **activity)
            await self.evaluate()
            acknowledgements += 1
            assert acknowledgements <= 5, "An ordinary adjustment must finish its bounded command sequence"
        return acknowledgements

    def continuous(self):
        # A real native controller without an OFF capability grants setpoint
        # control, but no power permission. The production model resolves both.
        self.state.attributes["hvac_modes"] = ["heat", "cool"]
        self.state.state = "heat"
        self.state.attributes["hvac_action"] = "heating"
        self.state.attributes["temperature"] = 21.
        assert model.permission(self.manager, SPEC, self.cap) == (True, False)

    @property
    def observer(self):
        return self._pid_adaptive_observers.get(SPEC.identifier)

    async def until_adjustment(self):
        for index in range(20):
            self.now += 120
            self.feedback(20.2 + .6 * math.sin(index))
            self.state.last_reported = stamp(self.now)
            await self.evaluate()
            if self.record.get("pending"):
                return
        raise AssertionError("The real controller did not request the expected normal adjustment")


@contextmanager
def percentage_fan():
    """Real configured auxiliary fan capability with simulated HA registry rows."""
    entity = "fan.auxiliary"
    area = lambda hass, source: getattr(hass.registry.async_get(source), "area_id", None)
    with patch.object(SPEC, "source_entities", (PRIMARY, entity)), \
            patch.object(production, "entity_area", area):
        runtime = EventRuntime(method="adaptive_suggest")
        fan = N(entity_id=entity, state="on", domain="fan",
                attributes={"supported_features": 1, "percentage_step": 10, "percentage": 20, "rpm": 280},
                last_reported=stamp(runtime.now), last_updated=stamp(runtime.now),
                last_changed=stamp(runtime.now-900), context=N(user_id=None, parent_id=None))
        runtime.extra_states[entity] = fan
        runtime.registry_rows[entity] = N(
            entity_id=entity, id="fan-registry", unique_id="fan-native",
            device_id=SPEC.source_device_id, platform="native", area_id=SPEC.area_id)
        runtime.manager.entry.data["climate_rooms"][SPEC.area_id]["selected_devices"] = [PRIMARY, entity]
        raw = runtime.raw()
        raw["requested_mode"] = "fan_only"
        raw["mode_settings"]["fan_only"] = {
            "control_mode": "pid", "pid_calibration_method": "adaptive_suggest",
            "kp": .5, "ki": 0., "kd": 0.}
        activation = importlib.import_module(fixture["PACKAGE"] + ".device_activation")
        raw["_native_authorization"] = activation.authority_context(runtime.manager, SPEC)
        runtime.manager.entry.options[model.SETTINGS] = {SPEC.identifier: raw}
        runtime.state.attributes["fan_modes"] = []
        runtime.state.state = "fan_only"
        runtime.record["baseline"] = {
            PRIMARY: production.snapshot(runtime.state), entity: production.snapshot(fan)}
        for source in SPEC.source_entities:
            runtime.record["power"][source] = {"since": runtime.now-900, "min_on": 600., "max_on": 7200.}
            runtime._native_ready_since[source] = runtime.now-30
            runtime._native_settled_for[(SPEC.identifier, source)] = runtime.now-30
        runtime.manager.plan.setdefault("air_actions", {})["outdoor_air_verified"] = True
        assert runtime.cap.fan_entity == entity and runtime.cap.fan_percentage
        yield runtime, entity


class AdaptiveEventTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.input_transport = fixture["IntegrationTests"]()
        self.input_transport.setUp()

    def tearDown(self):
        self.input_transport.tearDown()

    async def test_repeated_native_trim_commands_keep_fresh_samples_and_output_edges(self):
        runtime = EventRuntime(method="adaptive_suggest")
        runtime.continuous()
        acknowledgements = 0
        for index in range(44):
            runtime.now += 120
            runtime.feedback(20.2 + .6 * math.sin(index))
            runtime.state.last_reported = stamp(runtime.now)
            await runtime.evaluate()
            if runtime.record.get("pending"):
                before = len(runtime.observer.points)
                # The first bounded ACK wait is part of an ordinary output
                # adjustment. It is not a fresh process measurement.
                runtime.now += 10
                await runtime.evaluate()
                self.assertEqual(len(runtime.observer.points), before,
                                 "An ordinary pending ACK must not erase qualified history")
                acknowledgements += await runtime.acknowledge()
        observer = runtime.observer
        self.assertGreaterEqual(acknowledgements, 4)
        self.assertGreaterEqual(len(observer.points), 32,
                                "Normal setpoint adjustments must permit model-sized observation windows")
        self.assertEqual(len({point["at"] for point in observer.points}), len(observer.points),
                         "Native ACKs do not fabricate temperature reports")
        self.assertGreaterEqual(len(observer.events), 4)
        self.assertGreaterEqual(len({output for _, output in observer.events if output is not None}), 2)
        self.assertFalse(runtime.record.get("paused"))

    async def test_heater_already_off_dispatches_recovery_and_ack_keeps_budget(self):
        runtime = EventRuntime(method="adaptive_suggest")
        runtime.state.attributes["hvac_modes"] = ["heat", "off"]
        runtime.native_report(mode="off", action="off")
        watchdog = importlib.import_module(fixture["PACKAGE"] + ".off_state_runtime")
        start = runtime.now
        temp = 21.
        # Replace only the room sensor transport, peer inventory and notices.
        # Tick, watchdog, the durable native dispatcher and ACK run together.
        with (patch.object(watchdog, "_independent_room_temperature",
                           side_effect=lambda *_: (temp, ("sensor.first", "sensor.second"))),
              patch.object(watchdog, "_competing_effect_clear", return_value=True),
              patch.object(watchdog, "_notify")):
            for elapsed, temp in ((0, 21.), (1800, 21.8), (2100, 22.1),
                                  (2400, 22.5), (2700, 23.)):
                runtime.now = start + elapsed
                runtime.feedback(temp)
                runtime.state.last_reported = stamp(runtime.now)
                await runtime.evaluate()
            self.assertTrue(runtime.record["pending"]["off_state_recovery"])
            self.assertEqual(runtime.calls[-1]["service"], "set_hvac_mode")
            self.assertEqual(runtime.calls[-1]["data"]["hvac_mode"], "off")
            await runtime.acknowledge()
            self.assertEqual(runtime.record["thermal_off_watch"]["off_since"], start)
            self.assertEqual(runtime.record["thermal_off_watch"]["attempts"], 1)

    async def test_outage_between_ticks_rebases_math_and_preserves_results(self):
        runtime = EventRuntime(method="adaptive_suggest")
        runtime.feedback(19.)
        await runtime.evaluate()
        await runtime.acknowledge()
        runtime.seed_math()
        before_anchor = runtime._memory[SPEC.identifier][2]
        # These durable results belong to the completed operating context.
        observed = runtime.observer
        result = {"at": runtime.now, "status": "tracking_well"}
        observed.windows.append(result)
        runtime._pid_adaptive_remember(runtime.record, observed.context, observed.ledger())
        bank = deepcopy(runtime.record["pid_adaptive_contexts"])
        runtime.now += 10
        state = runtime.state.state
        runtime.native_event(mode="unavailable")
        runtime.now += 1
        runtime.native_event(mode=state)
        assert SPEC.identifier in runtime._pid_availability_resets
        runtime.now += 300
        runtime.feedback(19.)
        await runtime.evaluate()
        self.assertNotIn(SPEC.identifier, runtime._pid_availability_resets)
        fresh = runtime._memory.get(SPEC.identifier)
        self.assertTrue(fresh is None or fresh[2] > before_anchor)
        self.assertEqual(runtime.record["pid_adaptive_contexts"][observed.context]["ledger"]["windows"],
                         bank[observed.context]["ledger"]["windows"])

    async def test_short_normal_binary_cycles_keep_observation_segments(self):
        runtime = EventRuntime(method="adaptive_suggest")
        runtime.feedback(19.)
        await runtime.evaluate()
        await runtime.acknowledge()
        acknowledged = 0
        for index in range(44):
            runtime.now += 120
            # Ordinary target completion/resting/renewed demand, not forced
            # relay probing. Native minimum ON/OFF holds remain unchanged.
            runtime.feedback(19.5 if index % 12 < 8 else 21.1)
            runtime.state.last_reported = stamp(runtime.now)
            await runtime.evaluate()
            acknowledged += await runtime.acknowledge()
        self.assertGreaterEqual(acknowledged, 4)
        self.assertGreaterEqual(len(runtime.observer.points), 32,
                                "Short ordinary ON/OFF cycles must not reset the generic observation window")
        outputs = {output for _, output in runtime.observer.events if output is not None}
        self.assertTrue({0., 1.}.issubset(outputs), outputs)
        self.assertFalse(runtime.record.get("paused"))

    async def test_normal_fan_percentage_acknowledgements_keep_actual_output_history(self):
        with percentage_fan() as (runtime, entity):
            acknowledgements = 0
            for index in range(44):
                runtime.now += 120
                runtime.feedback(20.)
                sensor = runtime.extra_states["sensor.co2"]
                sensor.state = str(900 + 70 * math.sin(index))
                sensor.last_reported = sensor.last_updated = stamp(runtime.now)
                runtime.extra_states[entity].last_reported = stamp(runtime.now)
                runtime.state.last_reported = stamp(runtime.now)
                runtime.manager.plan["air_evidence_at"] = runtime.now
                await runtime.evaluate()
                acknowledgements += await runtime.acknowledge()
            self.assertGreaterEqual(acknowledgements, 4)
            self.assertTrue(any(call["service"] == "set_percentage" for call in runtime.calls), runtime.calls)
            self.assertGreaterEqual(len(runtime.observer.points), 32)
            self.assertGreaterEqual(len(runtime.observer.events), 4)
            self.assertGreaterEqual(len({value for _, value in runtime.observer.events if value is not None}), 3)
            self.assertFalse(runtime.record.get("paused"))

    async def test_foreign_control_changes_and_hidden_availability_invalidate(self):
        for change in ("foreign_target", "foreign_percentage", "human_exact_ack", "offline_roundtrip"):
            with self.subTest(change=change):
                runtime = EventRuntime(method="adaptive_suggest")
                runtime.continuous()
                await runtime.until_adjustment()
                self.assertGreaterEqual(len(runtime.observer.points), 4)
                before = runtime._pid_learning_generation.get(SPEC.identifier, 0)
                if change == "foreign_target":
                    runtime.native_event(temperature=19.)
                elif change == "foreign_percentage":
                    runtime.native_event(runtime.record["pending"]["expected"], percentage=75)
                elif change == "human_exact_ack":
                    runtime.native_event(runtime.record["pending"]["expected"], user_id="real-user")
                else:
                    runtime.native_event(mode="unavailable")
                    runtime.native_event(mode="heat")
                self.assertEqual(len(runtime.observer.points), 0)
                self.assertEqual(len(runtime.observer.events), 0)
                self.assertGreater(runtime._pid_learning_generation[SPEC.identifier], before)

    async def test_unresolved_or_retry_ack_invalidates_but_does_not_forge_completion(self):
        for change in ("expired", "retried", "recovery"):
            with self.subTest(change=change):
                runtime = EventRuntime(method="adaptive_suggest")
                runtime.continuous()
                await runtime.until_adjustment()
                self.assertGreaterEqual(len(runtime.observer.points), 4)
                if change == "expired":
                    runtime.now += 121
                elif change == "retried":
                    runtime.record["pending"]["attempts"] = 2
                else:
                    runtime.record["pending"]["off_state_recovery"] = True
                await runtime.evaluate()
                self.assertEqual(len(runtime.observer.points), 0)
                self.assertFalse(runtime.observer.snapshot()["fresh_evidence"])
                self.assertNotIn(runtime.observer.snapshot()["status"], ("verified", "reverted"))

    async def test_native_foreign_event_revokes_queued_gain_proof(self):
        runtime = EventRuntime()
        proof = runtime.proof()  # Existing guard fixture supplies a completed numerical proposal.
        generation = proof["generation"]
        runtime.native_event(temperature=19.)
        self.assertGreater(runtime._pid_learning_generation[SPEC.identifier], generation)
        self.assertFalse(await runtime._pid_adaptive_apply(SPEC, proof))
        self.assertEqual(runtime.config_commits, [])
        self.assertEqual(runtime.calls, [])

    async def test_explicit_manual_binary_ack_discards_unfinished_response(self):
        for origin in ("ha_user", "physical_button"):
            with self.subTest(origin=origin):
                runtime = EventRuntime(method="adaptive_suggest")
                runtime.feedback(19.)
                await runtime.evaluate()
                await runtime.acknowledge()
                for _ in range(8):
                    runtime.now += 120
                    runtime.feedback(19.)
                    runtime.state.last_reported = stamp(runtime.now)
                    await runtime.evaluate()
                    await runtime.acknowledge()
                runtime.now += 120
                runtime.feedback(21.1)
                runtime.state.last_reported = stamp(runtime.now)
                await runtime.evaluate()
                pending = deepcopy(runtime.record["pending"])
                self.assertEqual(pending["expected"]["state"], "off")
                self.assertGreaterEqual(len(runtime.observer.points), 4)
                before = runtime._pid_learning_generation.get(SPEC.identifier, 0)
                kwargs = ({"user_id": "real-user"} if origin == "ha_user"
                          else {"operation_source": "physical_button"})
                runtime.now += 1
                runtime.native_event(pending["expected"], **kwargs)
                self.assertEqual(len(runtime.observer.points), 0,
                                 "An explicit human action is not an ordinary HEM ACK")
                self.assertEqual(len(runtime.observer.events), 0)
                self.assertGreater(runtime._pid_learning_generation[SPEC.identifier], before)

    async def test_simultaneous_foreign_mode_attribute_is_not_our_target_ack(self):
        runtime = EventRuntime(method="adaptive_suggest")
        runtime.continuous()
        await runtime.until_adjustment()
        self.assertGreaterEqual(len(runtime.observer.points), 4)
        reported = deepcopy(runtime.record["pending"]["expected"])
        reported.setdefault("attributes", {})["mode"] = "eco"
        runtime.native_event(reported)
        self.assertEqual(len(runtime.observer.points), 0)
        self.assertEqual(len(runtime.observer.events), 0)

    async def test_pending_command_cannot_bridge_readiness_or_window_hold(self):
        for hold in ("startup", "window"):
            with self.subTest(hold=hold):
                runtime = EventRuntime(method="adaptive_suggest")
                runtime.manager.entry.options[model.SETTINGS][SPEC.identifier]["pause_on_window_open"] = True
                runtime.continuous()
                await runtime.until_adjustment()
                self.assertGreaterEqual(len(runtime.observer.points), 4)
                if hold == "startup":
                    runtime.startup_ready = False
                else:
                    runtime.window.update(blocked=True, status="window_open")
                runtime.now += 10
                await runtime.evaluate()
                self.assertEqual(len(runtime.observer.points), 0,
                                 "Only an ordinary ACK wait may preserve response evidence")


if __name__ == "__main__":
    unittest.main(verbosity=2)

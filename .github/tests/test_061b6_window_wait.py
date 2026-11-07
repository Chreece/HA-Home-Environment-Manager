"""Per-device airing consent, independent clocks and real dispatch boundaries.

The production wait state machine, demand math, native gate and supply driver
run against the existing deterministic HA transport fixture. No live device
is controlled and no service return is substituted for native feedback.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(Path(__file__).with_name("test_061b5_window_wait.py")))
Manager, SPEC, Cap, wait, logic, model, power, const = (
    b[key] for key in ("Manager", "SPEC", "Cap", "wait", "logic", "model", "power", "const")
)


def accept(manager):
    manager._recalculate()
    rec = manager.plan.recommendations[0]
    manager.window_open_wait.begin_submission(rec)
    return rec, manager.window_open_wait.submitted(rec)


def second_device(manager, *, minutes=10, enabled=True):
    spec = N(identifier="second", area_id="room", source_entities=("climate.second",),
             source_device_id="physical-second", name="Second dehumidifier")
    cap = replace(Cap(), primary="climate.second")
    manager.specs = (*manager.specs, spec)
    manager.capabilities[spec.identifier] = cap
    manager.settings["equipment_controllers"][spec.identifier] = {
        **manager.cfg, "announce_before_start": enabled, "window_open_timeout_minutes": minutes,
    }
    manager.equipment.records[spec.identifier] = {
        "power": {}, "pending": None, "upstream": {}, "sources": [cap.primary],
        "area": "room", "source_device_id": spec.source_device_id,
    }
    manager.hass.areas[cap.primary] = "room"
    manager.set_state(cap.primary, "off", {"friendly_name": spec.name})
    return spec, cap


def held(manager, spec, cap):
    return wait.managed_start_hold(manager.equipment, spec, cap,
                                  model.settings(manager, spec), "dry")


class DeviceConsentTests(unittest.TestCase):
    def test_missing_disabled_or_invalid_opt_in_never_defers_native_start(self):
        for value in (None, False, 0, 1, "true", "false"):
            with self.subTest(value=value):
                m = Manager()
                m.cfg["announce_before_start"] = value
                m._recalculate()
                self.assertIsNone(m.gate())
                self.assertEqual(m.plan.recommendations[0].wait_devices, ())
                self.assertEqual(m.plan.recommendations[0].wait_seconds, 0)
        for minutes in (0, -1, 31, True, float("nan"), float("inf"), "bad"):
            m = Manager()
            m.cfg["window_open_timeout_minutes"] = minutes
            m._recalculate()
            self.assertIsNone(m.gate())
            self.assertFalse(m.window_open_wait.status("room")["active"])

    def test_native_consent_is_independent_from_old_global_wait_and_open_policy(self):
        m = Manager()
        m.settings[const.CONF_WINDOW_OPEN_TIMEOUT_MINUTES] = 0
        m.cfg.update(window_open_timeout_minutes=2, pause_on_window_open=False)
        m._recalculate()
        self.assertEqual(m.gate(), "window_request_pending")
        self.assertEqual(m.plan.recommendations[0].wait_devices[0]["timeout_seconds"], 120)
        m.cfg["announce_before_start"] = False
        self.assertIsNone(m.gate(), "Live disable must release before the next plan refresh")
        m._recalculate()
        self.assertEqual(m.window_open_wait.status("room")["status"], "window_wait_disabled")
        m.cfg["announce_before_start"] = True
        m._recalculate()
        self.assertIsNone(m.gate(), "Re-enabling must not renew a consumed demand")

    def test_two_devices_own_independent_deadlines_and_expiry_wakes_each_driver(self):
        m = Manager()
        m.cfg["window_open_timeout_minutes"] = 1
        other, cap = second_device(m, minutes=5)
        m.set_state("climate.dry", "off", {"friendly_name": "Bathroom Comfee"})
        m._recalculate()
        rec = m.plan.recommendations[0]
        self.assertEqual({d["friendly_name"] for d in rec.wait_devices},
                         {"Bathroom Comfee", "Second dehumidifier"})
        self.assertEqual({d["timeout_seconds"] for d in rec.wait_devices}, {60, 300})
        m.window_open_wait.begin_submission(rec)
        m.advance(12)
        self.assertTrue(m.window_open_wait.submitted(rec))
        start = m.now
        self.assertEqual(m.window_open_wait.status("room", "climate.dry")["expires_at"], start + 60)
        self.assertEqual(held(m, other, cap)["expires_at"], start + 300)
        refreshes = m.refreshes
        m.advance(60)
        self.assertGreater(m.refreshes, refreshes)
        self.assertIsNone(m.gate())
        self.assertEqual(held(m, other, cap)["remaining_seconds"], 240)
        self.assertEqual([d["entity_id"] for d in m.plan.recommendations[0].wait_devices], [cap.primary])
        self.assertEqual(m.window_open_wait.status("room", "climate.dry")["status"], "window_open_timeout")
        m.advance(240)
        self.assertIsNone(held(m, other, cap))
        self.assertEqual(m.plan.recommendations[0].wait_devices, ())
        self.assertFalse(m.window_open_wait.should_announce(m.plan.recommendations[0]))

    def test_a_later_device_gets_its_own_delivery_without_restarting_the_first(self):
        m = Manager()
        other, cap = second_device(m, minutes=2, enabled=False)
        first, accepted = accept(m)
        self.assertTrue(accepted)
        first_deadline = m.window_open_wait.status("room", "climate.dry")["expires_at"]
        m.advance(20)
        model.settings(m, other)["announce_before_start"] = True
        m._recalculate()
        second = m.plan.recommendations[0]
        self.assertEqual(m.window_open_wait.status("room")["status"], "window_request_pending")
        self.assertFalse(m.window_open_wait.submitted(first))
        self.assertEqual(held(m, other, cap)["status"], "window_request_pending")
        m.window_open_wait.begin_submission(second)
        m.advance(3)
        self.assertTrue(m.window_open_wait.submitted(second))
        self.assertEqual(m.window_open_wait.status("room", "climate.dry")["expires_at"], first_deadline)
        self.assertEqual(held(m, other, cap)["expires_at"], m.now + 120)

    def test_new_device_discovered_during_handoff_cannot_use_the_old_payload_ack(self):
        m = Manager()
        m._recalculate()
        old = m.plan.recommendations[0]
        m.window_open_wait.begin_submission(old)
        other, cap = second_device(m, minutes=2)
        m._recalculate()
        self.assertTrue(m.window_open_wait.submitted(old))
        self.assertEqual(m.gate(), "window_open_wait")
        self.assertEqual(held(m, other, cap)["status"], "window_request_pending")
        current = m.plan.recommendations[0]
        m.window_open_wait.begin_submission(current)
        self.assertTrue(m.window_open_wait.submitted(current))
        self.assertEqual(held(m, other, cap)["status"], "window_open_wait")

    def test_timeout_edits_never_extend_and_shorter_timeout_is_rechecked_at_dispatch(self):
        m = Manager()
        _, accepted = accept(m)
        self.assertTrue(accepted)
        deadline = m.window_open_wait.status("room", "climate.dry")["expires_at"]
        m.advance(61)
        m.cfg["window_open_timeout_minutes"] = 30
        m._recalculate()
        self.assertEqual(m.window_open_wait.status("room", "climate.dry")["expires_at"], deadline)
        self.assertEqual(m.plan.recommendations[0].wait_devices[0]["timeout_seconds"], 300)
        m.cfg["window_open_timeout_minutes"] = 1
        self.assertIsNone(m.gate())
        m._recalculate()
        self.assertEqual(m.plan.recommendations[0].wait_seconds, 0)
        m.cfg["window_open_timeout_minutes"] = 30
        m._recalculate()
        self.assertIsNone(m.gate())

    def test_advice_disappearance_and_missing_measurements_never_reset_same_demand(self):
        for missing in ("advice", "reading"):
            with self.subTest(missing=missing):
                m = Manager()
                original = m.original
                _, accepted = accept(m)
                self.assertTrue(accepted)
                if missing == "advice":
                    m.original = replace(original, recommendations=())
                else:
                    m.measurements["humidity"] = None
                m._recalculate()
                self.assertIsNone(m.gate())
                m.advance(3600)
                m._recalculate()
                m.original = original
                m.measurements["humidity"] = 68.
                m._recalculate()
                self.assertIsNone(m.gate())
                self.assertEqual(m.plan.recommendations[0].wait_devices, ())
                self.assertFalse(m.window_open_wait.should_announce(m.plan.recommendations[0]))

    def test_only_stable_fresh_resolved_device_demand_allows_a_new_episode(self):
        m = Manager()
        accept(m)
        m.advance(300)
        m.measurements["humidity"] = 59.
        m._recalculate()
        m.advance(30)
        m.measurements["humidity"] = 68.
        m._recalculate()
        self.assertIsNone(m.gate(), "A single low reading cannot restart the full wait")
        m.measurements["humidity"] = 59.
        m._recalculate()
        m.advance(wait.RESOLVED_SECONDS)
        m._recalculate()
        m.measurements["humidity"] = 68.
        m._recalculate()
        self.assertEqual(m.gate(), "window_request_pending")

    def test_matching_problem_only_and_unrelated_air_quality_reminders_survive(self):
        m = Manager()
        co2 = replace(m.original.recommendations[0], reasons=(logic.Reason("inside_co2"),))
        m.original = replace(m.original, recommendations=(co2,))
        m._recalculate()
        self.assertIsNone(m.gate(), "A dehumidifier cannot solve CO2")
        self.assertTrue(m.window_open_wait.should_announce(m.plan.recommendations[0]))
        mixed = replace(co2, reasons=(logic.Reason("inside_humidity"), logic.Reason("inside_co2")))
        m.original = replace(m.original, recommendations=(mixed,))
        accept(m)
        m.advance(300)
        self.assertIsNone(m.gate())
        self.assertTrue(m.window_open_wait.should_announce(m.plan.recommendations[0]))

    def test_filtration_wait_requires_matching_particles_and_never_extraction(self):
        activation = sys.modules[b["PKG"] + ".device_activation"]
        for purpose, reason, expected in (("filtration", "inside_pm25", True),
                                          ("filtration", "inside_co2", False),
                                          ("extraction", "inside_pm25", False)):
            with self.subTest(purpose=purpose, reason=reason):
                m = Manager()
                m.capabilities[SPEC.identifier] = Cap(domain="fan", modes=("off", "fan_only"))
                m.cfg.update(requested_mode="fan_only", fan_purpose=purpose)
                m.measurements.update(pm25=65., co2=1500.)
                m.original.environment["room"]["climate_plan"]["air_actions"] = {
                    "outdoor_air_verified": True,
                    "thresholds": {"pm25_short_term_action_ug_m3": 15., "co2_operational_ppm": 1000.},
                }
                rec = replace(m.original.recommendations[0], reasons=(logic.Reason(reason),))
                m.original = replace(m.original, recommendations=(rec,))
                with patch.object(activation, "effective_device", lambda *_args, **_kwargs:
                                  {"auto_control": True, "fan_purpose": purpose, "sensor_verified": True}):
                    m._recalculate()
                    self.assertEqual(bool(m.plan.recommendations[0].wait_devices), expected)
                    if expected:
                        self.assertEqual(m.plan.recommendations[0].wait_devices[0]["effect"], "filtration")
                        self.assertTrue(wait.managed_start_hold(m.equipment, SPEC,
                                                               m.capabilities[SPEC.identifier], m.cfg, "fan_only"))

    def test_real_fan_role_is_shared_by_settings_demand_and_wait_gate(self):
        # A room can measure both CO2 and particles. Its explicitly assigned
        # purifier must remain a purifier rather than falling back to an
        # ambiguous sensor-only inference. Exercise the production resolvers
        # through preparation and the native dispatch gate, not a role stub.
        activation = sys.modules[b["PKG"] + ".device_activation"]
        discovery = sys.modules[b["PKG"] + ".discovery"]

        def profile(manager, spec, entity=None):
            return model.room_config(manager, spec).get("device_settings", {}).get(entity, {})

        scope = {"__package__": b["PKG"], "authorized": lambda manager, spec: manager.authorized,
                 "settings": model.settings, "capabilities": model.capabilities,
                 "room_config": model.room_config, "device_config": profile}
        for path, function in (("device_activation.py", "effective_device"),
                               ("equipment_model.py", "window_alternative_supported")):
            node = next(node for node in ast.parse((ROOT / path).read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == function)
            exec(compile(ast.Module([node], []), path, "exec"), scope)
        cases = (
            ({"purifier_fan_entity": "climate.dry"}, "auto", None, "filtration"),
            ({"extraction_fan_entity": "climate.dry"}, "auto", None, "extraction"),
            ({"purifier_fan_entity": "fan.other"}, "auto", None, None),
            ({"extraction_fan_entity": "climate.dry"}, "filtration", None, "filtration"),
            ({"extraction_fan_entity": "climate.dry"}, "auto", "filtration", "filtration"),
        )
        with patch.object(activation, "effective_device", scope["effective_device"]), \
                patch.object(model, "device_config", profile, create=True), \
                patch.object(model, "window_alternative_supported", scope["window_alternative_supported"], create=True), \
                patch.object(discovery, "supported_metric", lambda _hass, state, **_kw:
                             state.attributes.get("metric"), create=True):
            for roles, controller_role, device_role, expected in cases:
                with self.subTest(roles=roles, controller_role=controller_role, device_role=device_role):
                    m = Manager()
                    cap = Cap(domain="fan", modes=("off", "fan_only"))
                    m.capabilities[SPEC.identifier] = cap
                    m.cfg.update(requested_mode="fan_only", fan_purpose=controller_role,
                                 sensor_verified=True, window_open_timeout_minutes=1)
                    m.settings["climate_rooms"]["room"].update(roles)
                    if device_role:
                        m.settings["climate_rooms"]["room"]["device_settings"] = {
                            cap.primary: {"fan_purpose": device_role}}
                    m.settings["room_sources"]["room"]["air_quality"] = ["sensor.co2", "sensor.pm25"]
                    m.set_state("sensor.co2", "1500", {"metric": "co2"})
                    m.set_state("sensor.pm25", "65", {"metric": "pm25"})
                    m.measurements.update(pm25=65., co2=1500.)
                    plan = m.original.environment["room"]["climate_plan"]
                    plan.update(air_evidence_at=m.now, air_actions={
                        "outdoor_air_verified": True,
                        "thresholds": {"pm25_short_term_action_ug_m3": 15., "co2_operational_ppm": 1000.},
                    })
                    rec = replace(m.original.recommendations[0], reasons=(logic.Reason("inside_pm25"),))
                    m.original = replace(m.original, recommendations=(rec,))
                    actual = activation.effective_device(m, SPEC, cap.primary, cap=cap)
                    self.assertEqual(actual.get("fan_purpose"), expected)
                    self.assertEqual(model.window_alternative_supported(m, SPEC, cap), expected == "filtration")
                    m._recalculate()
                    self.assertEqual(bool(m.plan.recommendations[0].wait_devices), expected == "filtration")
                    if expected == "filtration":
                        self.assertEqual(m.gate(mode="fan_only"), "window_request_pending")
                        rec = m.plan.recommendations[0]
                        m.window_open_wait.begin_submission(rec)
                        self.assertTrue(m.window_open_wait.submitted(rec))
                        m.advance(60)
                        self.assertIsNone(m.gate(mode="fan_only"))
                    else:
                        self.assertIsNone(wait.managed_start_hold(m.equipment, SPEC, cap, m.cfg, "fan_only"))

    def test_humidifier_requires_a_verified_moisture_gain_reason(self):
        m = Manager()
        m.capabilities[SPEC.identifier] = Cap(domain="humidifier", modes=("off", "auto"), humidifying=True)
        m.cfg.update(requested_mode="auto")
        m.measurements["humidity"] = 30.
        m._recalculate()
        self.assertEqual(m.plan.recommendations[0].wait_devices, ())
        rec = replace(m.original.recommendations[0], reasons=(logic.Reason("climate_window_humidify"),))
        m.original = replace(m.original, recommendations=(rec,))
        m._recalculate()
        self.assertEqual(m.plan.recommendations[0].wait_devices[0]["effect"], "humidify")

    def test_per_device_opt_in_enables_only_its_proved_alternative(self):
        m = Manager()
        option = {"status": "opportunity", "devices": ("climate.dry",), "effect": "dry"}
        self.assertTrue(m.window_open_wait.has_enabled_alternative("room", option))
        self.assertFalse(m.window_open_wait.has_enabled_alternative("other", option))
        self.assertFalse(m.window_open_wait.has_enabled_alternative("room", {**option, "devices": ("climate.other",)}))
        m.cfg["announce_before_start"] = False
        self.assertFalse(m.window_open_wait.has_enabled_alternative("room", option))


class ActualDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_dry_mode_is_sent_after_expiry_without_window_or_reminder(self):
        native = runpy.run_path(str(Path(__file__).with_name("test_beta111_pid_target_cutoff.py")))
        with native["endpoint"]("dry") as runtime, patch.dict(sys.modules, {
            native["production"].__package__ + ".window_open_wait": wait,
        }):
            cfg = runtime.manager.settings
            cfg.update(announce_before_start=True, window_open_timeout_minutes=1)
            runtime.manager.plan["sleeping"] = False
            runtime.state.entity_id = runtime.primary
            runtime.state.attributes["friendly_name"] = "Native Comfee"
            window = N(entity_id="binary_sensor.window", state="off",
                       attributes={"device_class": "window"})
            runtime.hass.states.get = lambda entity: (runtime.state if entity == runtime.primary
                                                      else window if entity == window.entity_id else None)
            runtime.hass.areas = {runtime.primary: "room", window.entity_id: "room"}
            cap = native["model"].capabilities(runtime.manager, runtime.spec)
            room = logic.Room("room", "Bathroom", (logic.Window(window.entity_id, "Window", False),), ())
            recommendation = logic.Recommendation("open", "room", "Bathroom", room.windows,
                                                  (logic.Reason("inside_humidity"),))
            plan = logic.Plan("open", True, (), (recommendation,), (), rooms=(room,),
                              environment={"room": {"room_presence": {"home": "home", "sleeping": False},
                                                     "climate_plan": runtime.manager.plan}})
            bridge = N(hass=runtime.hass, authorized=True, equipment=runtime,
                       specs=(runtime.spec,), capabilities={runtime.spec.identifier: cap},
                       targets=runtime.manager.targets, plan=plan,
                       settings={const.CONF_AUTO_TTS: True,
                                 "equipment_controllers": {runtime.spec.identifier: cfg},
                                 "room_sources": {"room": {"windows": [window.entity_id]}}})
            waiter = wait.WindowOpeningWait(bridge, clock=runtime.clock,
                schedule=lambda seconds, callback: runtime.timer_loop.call_later(seconds, callback).cancel)
            bridge._recalculate = lambda: setattr(bridge, "plan", waiter.prepare(plan))
            runtime.manager.window_open_wait = waiter
            bridge._recalculate()
            await runtime.evaluate()
            self.assertEqual(runtime.calls, [])
            rec = bridge.plan.recommendations[0]
            waiter.begin_submission(rec)
            self.assertTrue(waiter.submitted(rec))
            await runtime.evaluate(59)
            self.assertEqual(runtime.calls, [])
            await runtime.evaluate(1)
            self.assertEqual([(call["service"], call["data"]) for call in runtime.calls],
                             [("set_hvac_mode", {"hvac_mode": "dry"})])
            self.assertFalse(runtime.record["power"], "Submitting DRY does not prove the native device is running")
            self.assertEqual(runtime.record["pending"]["expected"], {"state": "dry"})
            self.assertFalse(waiter.should_announce(bridge.plan.recommendations[0]))
            self.assertIsNone(runtime.record.get("paused"))
            self.assertEqual(cfg["control_mode"], "pid")

    async def test_default_disabled_uses_real_supply_driver_without_request_delay(self):
        m = Manager()
        m.cfg.update(announce_before_start=False, power_switch_entity="switch.supply")
        identity = {"entity": "switch.supply", "area": "room", "registry_id": "id", "device_id": "plug"}
        record = m.equipment.records[SPEC.identifier]
        record["upstream"] = {"entity": "switch.supply", "identity": identity, "owned": False,
                              "off_at": m.now - 1800, "off_min_seconds": 600}
        m._recalculate()
        with patch.object(power, "permitted_supply", return_value=identity):
            await power.before_tick(m.equipment, SPEC)
        self.assertEqual([(domain, service) for domain, service, _, _ in m.calls], [("switch", "turn_on")])
        self.assertEqual(m.plan.recommendations[0].wait_devices, ())

    async def test_expired_dehumidifier_wait_starts_even_if_advice_and_other_device_wait_remain(self):
        m = Manager()
        m.cfg.update(window_open_timeout_minutes=1, power_switch_entity="switch.supply")
        other, cap = second_device(m, minutes=10)
        model.settings(m, other)["power_switch_entity"] = None
        identity = {"entity": "switch.supply", "area": "room", "registry_id": "id", "device_id": "plug"}
        record = m.equipment.records[SPEC.identifier]
        record["upstream"] = {"entity": "switch.supply", "identity": identity, "owned": False,
                              "off_at": m.now - 1800, "off_min_seconds": 600}
        _, accepted = accept(m)
        self.assertTrue(accepted)
        with patch.object(power, "permitted_supply", return_value=identity):
            await power.before_tick(m.equipment, SPEC)
            self.assertEqual(m.calls, [])
            m.advance(60)
            self.assertIsNone(m.gate())
            self.assertEqual(held(m, other, cap)["remaining_seconds"], 540)
            await power.before_tick(m.equipment, SPEC)
            self.assertEqual([(domain, service) for domain, service, _, _ in m.calls], [("switch", "turn_on")])
            self.assertFalse(record["upstream"]["owned"], "A service return must not fabricate the supply ACK")
            self.assertEqual(record["upstream"]["pending"]["phase"], "commanded")
        self.assertEqual([d["entity_id"] for d in m.plan.recommendations[0].wait_devices], [cap.primary])


if __name__ == "__main__":
    unittest.main()

"""Finite airing requests, accepted delivery and real native/supply boundaries.

Use production waiting logic, PID demand math, window policy and dispatch
guards with a deterministic HA fixture. No real HA services or devices.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_061b5_window_wait_fixture"
package = ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package


def stub(name, **items):
    result = ModuleType(PKG + "." + name)
    result.__dict__.update(items)
    sys.modules[result.__name__] = result
    return result


@dataclass
class Cap:
    primary: str = "climate.dry"
    domain: str = "climate"
    modes: tuple = ("off", "dry")
    humidifying: bool = False
    temperature: bool = False
    temperature_range: bool = False
    humidity: bool = True


SPEC = N(identifier="dryer", area_id="room", source_entities=("climate.dry",),
         source_device_id="physical-dryer")
model = stub("equipment_model", ManagedDevice=N, Capabilities=Cap,
    specs=lambda manager: manager.specs,
    settings=lambda manager, spec: manager.settings["equipment_controllers"][spec.identifier],
    room_config=lambda manager, spec: manager.settings.get("climate_rooms", {}).get(spec.area_id, {}),
    capabilities=lambda manager, spec: manager.capabilities.get(spec.identifier),
    permission=lambda manager, spec, cap: (manager.authorized, manager.authorized),
    targets=lambda manager, spec, cap, cfg, plan: dict(manager.targets),
    plan_for=lambda manager, spec: manager.plan.environment[spec.area_id]["climate_plan"],
    sources_available=lambda manager, spec: manager.hass.states.get(spec.source_entities[0]).state
        not in ("unknown", "unavailable"),
    timing=lambda *args, **kwargs: (600, 600, 7200),
    automatic_profile_reason=lambda *args: None,
    legacy_hold=lambda *args: None)
stub("discovery", entity_area=lambda hass, entity: hass.areas.get(entity),
     is_window=lambda hass, state: state.attributes.get("device_class") == "window",
     temperature_sensor_c=lambda hass, entity, age: 18.0)
stub("room_sources", selected=lambda settings, area, group:
     settings.get("room_sources", {}).get(area, {}).get(group))
stub("device_activation", authorized=lambda manager, spec: manager.authorized,
     effective_device=lambda *args, **kwargs: {"auto_control": True})
stub("occupancy_policy", live_device_permission=lambda hass, area, config, plan, device:
     ("eligible", "eligible") if plan.get("away") == "home" and plan.get("sleeping") is False
     else ("held", "room_unavailable"))
stub("climate_entry_ownership", foreign_owner_hold=lambda *args: None)
const = importlib.import_module(PKG + ".const")
logic = importlib.import_module(PKG + ".logic")
power = importlib.import_module(PKG + ".equipment_power_switch")
window_policy = importlib.import_module(PKG + ".equipment_window")
wait = importlib.import_module(PKG + ".window_open_wait")


def production_method(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    source = next(child for node in tree.body if isinstance(node, ast.ClassDef)
                  for child in node.body
                  if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and child.name == name)
    exec(compile(ast.Module(body=[source], type_ignores=[]), str(ROOT / path), "exec"), namespace)
    return namespace[name]


class Runtime:
    def __init__(self, manager):
        self.manager, self.hass = manager, manager.hass
        self.records = {SPEC.identifier: {"power": {}, "pending": None, "upstream": {},
            "sources": list(SPEC.source_entities), "area": "room", "source_device_id": "physical-dryer"}}
        self._active = self._ready = True
        self._started = manager.now - 1800
        self._memory = {SPEC.identifier: "old-integral"}
        self._pid_offline_previews = {}
        self._commands = asyncio.Semaphore(1)
        self.statuses = {}
        self._save_count = 0

    def clock(self):
        return self.manager.now

    def measurements(self, *args):
        return dict(self.manager.measurements)

    def _record(self, spec):
        return self.records[spec.identifier]

    def _current_spec(self, spec):
        return True

    def _window_policy(self, spec, cfg=None):
        return window_policy.evaluate(self, spec, cfg)

    def _status(self, spec, status, **details):
        self.statuses[spec.identifier] = {"status": status, **details}

    async def _save(self):
        self._save_count += 1


Runtime._gate = production_method("equipment_runtime.py", "_gate", {
    "__name__": PKG + ".runtime", "__package__": PKG, "model": model,
    "STARTUP_SECONDS": 300, "foreign_owner_hold": lambda *args: None,
    "snapshot": lambda state: None if state is None or state.state in ("unknown", "unavailable") else
        {"state": state.state, "attributes": dict(state.attributes)},
    "_physical_climate_conflict": lambda *args: None,
    "live_device_permission": sys.modules[PKG + ".occupancy_policy"].live_device_permission,
    "finite": importlib.import_module(PKG + ".pid_math").finite,
})


class Manager:
    def __init__(self):
        self.now = 1_799_000_000.0
        self.authorized = True
        self.settings = {
            const.CONF_AUTO_TTS: True, const.CONF_AUTO_NOTIFY: False,
            const.CONF_WINDOW_OPEN_TIMEOUT_MINUTES: 5,
            "room_sources": {"room": {"windows": ["binary_sensor.window"]}},
            "equipment_controllers": {SPEC.identifier: {
                "control_mode": "pid", "requested_mode": "dry", "pause_on_window_open": True,
                "announce_before_start": True, "window_open_timeout_minutes": 5,
                "power_switch_entity": None, "power_switch_cooldown_seconds": 600,
                "min_on_seconds": 600, "min_off_seconds": 600,
            }},
            "climate_rooms": {"room": {"enabled": True, "dry_climate_entity": "climate.dry"}},
        }
        self.specs = (SPEC,)
        self.capabilities = {SPEC.identifier: Cap()}
        self.targets = {"humidity": 60., "heat": 20., "cool": 26.}
        self.measurements = {"temperature": 22., "humidity": 68.}
        self.states = {}
        self.calls, self.timers = [], []
        self.refreshes = 0
        self.hass = N(states=N(get=lambda entity: self.states.get(entity)),
                      areas={"binary_sensor.window": "room", "climate.dry": "room",
                             "switch.supply": "room"}, data={const.DOMAIN: {"entry": self}})
        self.hass.services = N(has_service=lambda *args: True, async_call=self.service)
        self.entry = N(entry_id="entry")
        self.set_state("climate.dry", "off")
        self.set_state("switch.supply", "off")
        self.set_state("binary_sensor.window", "off", {"device_class": "window"})
        room = logic.Room("room", "Room", (logic.Window("binary_sensor.window", "Window", False),),
                          (logic.Reading("sensor.rh", "Humidity", "humidity", 68.),))
        self.original = logic.Plan("open", True, (), (logic.Recommendation(
            "open", "room", "Room", room.windows,
            (logic.Reason("inside_humidity", "Humidity", "68 %"),)),), (), rooms=(room,),
            environment={"room": {"room_presence": {"home": "home", "sleeping": False},
                "climate_plan": {"away": "home", "sleeping": False, "occupancy": "unoccupied",
                                 "window_safe": True, "window_contacts": ["binary_sensor.window"]}}})
        self.plan = self.original
        self.equipment = Runtime(self)
        self.window_open_wait = wait.WindowOpeningWait(self, clock=lambda: self.now, schedule=self.schedule)

    @property
    def cfg(self):
        return self.settings["equipment_controllers"][SPEC.identifier]

    def set_state(self, entity, value, attrs=None, age=1800):
        self.states[entity] = N(entity_id=entity, domain=entity.partition(".")[0], state=value,
            attributes=attrs or {}, last_changed=datetime.fromtimestamp(self.now - age, timezone.utc))

    async def service(self, domain, service, data, **kwargs):
        self.calls.append((domain, service, data, kwargs))

    def schedule(self, seconds, callback):
        timer = N(at=self.now + seconds, callback=callback, cancelled=False)
        self.timers.append(timer)
        return lambda: setattr(timer, "cancelled", True)

    def _recalculate(self):
        self.refreshes += 1
        self.plan = self.window_open_wait.prepare(self.original)

    def advance(self, seconds, *, fire=True):
        self.now += seconds
        if fire:
            for timer in tuple(self.timers):
                if not timer.cancelled and timer.at <= self.now:
                    timer.cancelled = True
                    timer.callback(None)

    def gate(self, *, mode="dry", automatic=True):
        return self.equipment._gate(SPEC, self.capabilities[SPEC.identifier], self.cfg,
                                   model.plan_for(self, SPEC), mode, automatic=automatic)


class WaitingTests(unittest.TestCase):
    def test_request_and_response_have_distinct_fixed_deadlines(self):
        m = Manager()
        self.assertIsNone(m.gate())
        m._recalculate()
        rec = m.plan.recommendations[0]
        m.window_open_wait.begin_submission(rec)
        self.assertEqual(rec.wait_seconds, 300)
        self.assertEqual(m.original.recommendations[0].wait_seconds, 0)
        self.assertEqual(m.gate(), "window_request_pending")
        self.assertEqual(m.window_open_wait.status("room")["remaining_seconds"], 130)
        m.advance(20)
        self.assertTrue(m.window_open_wait.submitted(rec))
        deadline = m.window_open_wait.status("room")["expires_at"]
        self.assertEqual(deadline, m.now + 300)
        self.assertEqual(m.gate(), "window_open_wait")
        m.advance(80)
        m._recalculate()
        self.assertFalse(m.window_open_wait.submitted(m.plan.recommendations[0]))
        self.assertEqual(m.window_open_wait.status("room")["expires_at"], deadline)
        self.assertEqual(m.plan.recommendations[0].wait_seconds, 220)
        m.advance(220)
        self.assertIsNone(m.gate())
        self.assertEqual(m.window_open_wait.status("room")["status"], "window_open_timeout")
        self.assertEqual(m.plan.recommendations[0].wait_seconds, 0)
        for _ in range(5):
            m.advance(3600)
            m._recalculate()
            self.assertIsNone(m.gate())
            self.assertFalse(m.window_open_wait.submitted(m.plan.recommendations[0]))

    def test_failed_or_late_submission_releases_and_cannot_rearm(self):
        for failure in ("failed", "expired"):
            with self.subTest(failure=failure):
                m = Manager()
                m._recalculate()
                rec = m.plan.recommendations[0]
                m.window_open_wait.begin_submission(rec)
                if failure == "failed":
                    m.window_open_wait.submission_failed(rec)
                else:
                    m.advance(131, fire=False)
                    self.assertIsNone(m.gate())  # Even a delayed HA timer cannot extend a hold.
                self.assertFalse(m.window_open_wait.submitted(rec))
                m._recalculate()
                self.assertIsNone(m.gate())
                self.assertEqual(m.plan.recommendations[0].wait_seconds, 0)

    def test_wrong_or_changed_request_cannot_acknowledge_current_request(self):
        m = Manager()
        m._recalculate()
        stale = m.plan.recommendations[0]
        m.window_open_wait.begin_submission(stale)
        rec = replace(stale, cautions=(logic.Reason("weather_cold", value="2 °C"),))
        m.original = replace(m.original, recommendations=(rec,))
        m._recalculate()
        self.assertFalse(m.window_open_wait.submitted(stale))
        self.assertFalse(m.window_open_wait.submitted(replace(rec, area_id="elsewhere")))
        m.window_open_wait.begin_submission(m.plan.recommendations[0])
        self.assertTrue(m.window_open_wait.submitted(m.plan.recommendations[0]))

    def test_old_delivery_and_cancelled_timer_cannot_change_a_later_episode(self):
        m = Manager()
        m._recalculate()
        old = m.plan.recommendations[0]
        m.window_open_wait.begin_submission(old)
        m.original = replace(m.original, recommendations=())
        m.measurements["humidity"] = 59.
        m._recalculate()
        m.advance(wait.RESOLVED_SECONDS)
        m._recalculate()
        m.original = replace(m.original, recommendations=(old,))
        m.measurements["humidity"] = 68.
        m._recalculate()
        current = m.plan.recommendations[0]
        m.window_open_wait.begin_submission(current)
        self.assertFalse(m.window_open_wait.submitted(old))
        m.window_open_wait.submission_failed(old)
        self.assertEqual(m.gate(), "window_request_pending")
        pending_callback = m.timers[-1].callback
        self.assertTrue(m.window_open_wait.submitted(current))
        deadline = m.window_open_wait.status("room")["expires_at"]
        pending_callback(None)  # Simulate a cancelled callback already queued by HA.
        self.assertEqual(m.window_open_wait.status("room")["expires_at"], deadline)
        self.assertEqual(m.gate(), "window_open_wait")

    def test_disabled_no_demand_manual_filter_and_running_do_not_wait(self):
        changes = (
            lambda m: m.cfg.update(window_open_timeout_minutes=0),
            lambda m: m.settings.update({const.CONF_AUTO_TTS: False}),
            lambda m: m.cfg.update(control_mode="manual"),
            lambda m: m.cfg.update(announce_before_start=False),
            lambda m: m.measurements.update(humidity=59.),
            lambda m: m.measurements.update(humidity=None),
            lambda m: m.set_state("climate.dry", "dry", {"hvac_action": "drying"}),
            lambda m: m.capabilities.update({SPEC.identifier: Cap(domain="fan", modes=("off", "fan_only"))}),
            lambda m: setattr(m, "authorized", False),
            lambda m: m.equipment.records[SPEC.identifier].update(pending={"phase": "commanded"}),
        )
        for change in changes:
            m = Manager()
            change(m)
            m._recalculate()
            self.assertEqual(m.plan.recommendations[0].wait_seconds, 0, change)
            self.assertFalse(m.window_open_wait.status("room").get("active"), change)

    def test_live_off_manual_and_running_bypass_wait_without_cancelling_episode(self):
        m = Manager()
        m._recalculate()
        self.assertIsNone(m.gate(mode="off"))
        self.assertIsNone(m.gate(automatic=False))
        m.set_state("climate.dry", "dry", {"hvac_action": "drying"})
        self.assertIsNone(m.gate())
        other = replace(m.capabilities[SPEC.identifier], primary="climate.other")
        m.set_state("climate.other", "off")
        self.assertIsNone(wait.managed_start_hold(m.equipment, SPEC, other, m.cfg, "dry"))
        m.set_state("climate.dry", "off")
        self.assertEqual(m.gate(), "window_request_pending")

    def test_live_contacts_no_false_open_and_consumed_episode_requires_resolution(self):
        m = Manager()
        m._recalculate()
        m.window_open_wait.begin_submission(m.plan.recommendations[0])
        m.window_open_wait.submitted(m.plan.recommendations[0])
        m.set_state("binary_sensor.window", "on", {"device_class": "window"})
        self.assertIsNone(wait.managed_start_hold(m.equipment, SPEC, Cap(), m.cfg, "dry"))
        self.assertEqual(m.gate(), "window_open_pause")
        m.original = replace(m.original, recommendations=())
        m._recalculate()
        self.assertEqual(m.window_open_wait.status("room")["status"], "window_opened")
        m.advance(1200)
        m.set_state("binary_sensor.window", "off", {"device_class": "window"}, age=0)
        source = Manager().original.recommendations[0]
        m.original = replace(m.original, recommendations=(source,))
        m._recalculate()
        self.assertEqual(m.plan.recommendations[0].wait_seconds, 0)
        self.assertEqual(m.gate(), "window_close_warmup")
        m.advance(60)
        self.assertIsNone(m.gate())
        m.original = replace(m.original, recommendations=())
        m.measurements["humidity"] = 59.
        m._recalculate()
        m.advance(wait.RESOLVED_SECONDS)
        m._recalculate()
        m.original = replace(m.original, recommendations=(source,))
        m.measurements["humidity"] = 68.
        m._recalculate()
        self.assertEqual(m.gate(), "window_request_pending")

    def test_restricted_presence_unknown_contact_and_changed_selection_release(self):
        for variant in ("away", "sleep", "unknown", "selection", "disabled"):
            m = Manager()
            m._recalculate()
            m.window_open_wait.begin_submission(m.plan.recommendations[0])
            m.window_open_wait.submitted(m.plan.recommendations[0])
            if variant == "away":
                m.original.environment["room"]["room_presence"]["home"] = "away"
            elif variant == "sleep":
                m.original.environment["room"]["room_presence"]["sleeping"] = True
            elif variant == "unknown":
                m.set_state("binary_sensor.window", "unavailable", {"device_class": "window"})
            elif variant == "selection":
                m.settings["room_sources"]["room"]["windows"] = []
            else:
                m.cfg["window_open_timeout_minutes"] = 0
            m._recalculate()
            self.assertFalse(m.window_open_wait.status("room")["active"], variant)
            self.assertIsNone(wait.managed_start_hold(m.equipment, SPEC, Cap(), m.cfg, "dry"), variant)

    def test_stopped_or_backward_clock_never_holds_and_all_timers_cancel(self):
        m = Manager()
        m._recalculate()
        m.advance(-1, fire=False)
        self.assertIsNone(wait.managed_start_hold(m.equipment, SPEC, Cap(), m.cfg, "dry"))
        m._recalculate()
        self.assertFalse(m.window_open_wait.status("room")["active"])
        m.window_open_wait.stop()
        self.assertTrue(all(timer.cancelled for timer in m.timers))

    def test_pending_demand_uses_measured_direction_and_exact_permission(self):
        m = Manager()
        plan = model.plan_for(m, SPEC)
        self.assertEqual(wait.pending_demands(m, "room", plan), ({
            "entity_id": "climate.dry", "effect": "dry", "temperature_c": 22.,
            "humidity_percent": 68., "target_humidity": 60.,
        },))
        m.measurements["humidity"] = None
        self.assertEqual(wait.pending_demands(m, "room", plan), ())
        m.measurements["humidity"] = 59.
        self.assertEqual(wait.pending_demands(m, "room", plan), ())
        m.measurements["humidity"] = 68.
        self.assertEqual(wait.pending_demands(m, "another-room", plan), ())
        m.authorized = False
        self.assertEqual(wait.pending_demands(m, "room", plan), ())

    def test_range_only_native_direction_follows_fresh_band_evidence(self):
        m = Manager()
        m.capabilities[SPEC.identifier] = Cap(modes=("off", "heat_cool"), temperature_range=True)
        m.cfg.update(control_mode="automatic", requested_mode=None)
        plan = model.plan_for(m, SPEC)
        for temperature, direction in ((18., "heat"), (29., "cool")):
            m.measurements["temperature"] = temperature
            rows = wait.pending_demands(m, "room", plan)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["effect"], direction)
            self.assertEqual(rows[0]["target_c"], m.targets[direction])
        for temperature in (20., 23., 26., None):
            m.measurements["temperature"] = temperature
            self.assertEqual(wait.pending_demands(m, "room", plan), ())


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_supply_waits_then_resumes_through_the_existing_minimum_off_guard(self):
        m = Manager()
        m.cfg["power_switch_entity"] = "switch.supply"
        identity = {"entity": "switch.supply", "area": "room", "registry_id": "id", "device_id": "plug"}
        record = m.equipment.records[SPEC.identifier]
        record["upstream"] = {"entity": "switch.supply", "identity": identity, "owned": False,
                              "off_at": m.now - 1800, "off_min_seconds": 600}
        m._recalculate()
        self.assertIsNone(power.approved_demand(m.equipment, SPEC, m.cfg, Cap()))
        self.assertFalse(power._dispatch_safe(m.equipment, SPEC, record, m.cfg, "switch.supply", "on"))
        with patch.object(power, "permitted_supply", return_value=identity):
            await power.before_tick(m.equipment, SPEC)
            self.assertEqual(m.equipment.statuses[SPEC.identifier]["status"], "window_request_pending")
            self.assertEqual(m.calls, [])
            self.assertNotIn(SPEC.identifier, m.equipment._memory)
            m.window_open_wait.begin_submission(m.plan.recommendations[0])
            m.window_open_wait.submitted(m.plan.recommendations[0])
            await power.before_tick(m.equipment, SPEC)
            self.assertEqual(m.equipment.statuses[SPEC.identifier]["status"], "window_open_wait")
            self.assertEqual(m.calls, [])
            m.advance(300)
            self.assertTrue(power.approved_demand(m.equipment, SPEC, m.cfg, Cap()))
            record["upstream"]["off_at"] = m.now - 599
            self.assertFalse(power._dispatch_safe(m.equipment, SPEC, record, m.cfg, "switch.supply", "on"))
            await power.before_tick(m.equipment, SPEC)
            self.assertEqual(m.equipment.statuses[SPEC.identifier]["status"], "minimum_off_hold")
            m.advance(1)
            self.assertTrue(power._dispatch_safe(m.equipment, SPEC, record, m.cfg, "switch.supply", "on"))
            await power.before_tick(m.equipment, SPEC)
            self.assertEqual(len(m.calls), 1)
            self.assertEqual(m.calls[0][:2], ("switch", "turn_on"))

    async def test_legacy_idle_setpoints_wait_while_running_and_filtration_bypass(self):
        m = Manager()
        # The real hierarchy still lists this physical device while its
        # owner is the existing legacy controller, not the managed runtime.
        m.cfg["control_mode"] = "existing"
        m.settings["climate_rooms"]["room"].update(allow_actuation=True, climate_entity="climate.dry")
        m.original.environment["room"]["climate_plan"].update(
            temperature_c=18., temperature_target_c=20., mode="heat")
        m.original = replace(m.original, recommendations=(replace(
            m.original.recommendations[0], reasons=(logic.Reason("climate_window_heat"),)),))
        m.set_state("climate.dry", "heat", {"hvac_action": "idle"})
        m._recalculate()
        self.assertEqual(wait.legacy_start_hold(m.hass, "entry", "room", "climate.dry", "thermal")["status"],
                         "window_request_pending")
        self.assertIsNone(wait.legacy_start_hold(m.hass, "entry", "room", "climate.dry", "filtration"))
        m.set_state("climate.dry", "heat", {"hvac_action": "heating"})
        self.assertIsNone(wait.legacy_start_hold(m.hass, "entry", "room", "climate.dry", "thermal"))


if __name__ == "__main__":
    unittest.main()

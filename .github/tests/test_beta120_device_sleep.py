"""Sleep/wake decisions across real managed settings, targets, and write guards.

The HA state machine, entity registry and service transport are test doubles.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import importlib.util
from pathlib import Path
import runpy
import sys
from types import MappingProxyType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / ".github/tests"
fixture = runpy.run_path(str(TESTS / "test_home_presence_authority.py"))
package = fixture["PACKAGE"]
policy = fixture["occupancy"]
quiet = fixture["runtime"]._quiet_context
wake = importlib.import_module(package + ".wake_alarm")
spec = importlib.util.spec_from_file_location(package + ".complete_model", ROOT / "equipment_model.py")
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)
writer = runpy.run_path(str(TESTS / "test_beta110_device_setting.py"))
# The older AST fixture supplies copy.deepcopy. Use the runtime's actual
# configuration-copy import when checking HA's read-only options below.
writer["ns"]["deepcopy"] = model.deepcopy
retries = runpy.run_path(str(TESTS / "test_beta88_power_startup_and_retries.py"))
native = runpy.run_path(str(TESTS / "test_onoff_native_extrema.py"))
status_tree = ast.parse((ROOT / "equipment_status.py").read_text())
status_method = next(n for cls in status_tree.body if isinstance(cls, ast.ClassDef)
                     and cls.name == "ControllerStatusSensor" for n in cls.body
                     if isinstance(n, ast.FunctionDef) and n.name == "extra_state_attributes")
status_method.decorator_list = []
status_scope = {"equipment": model, "__package__": package}
exec(compile(ast.Module(body=[ast.parse("from __future__ import annotations").body[0],
                             status_method], type_ignores=[]),
             str(ROOT / "equipment_status.py"), "exec"), status_scope)

FLAG = "sleep_when_everyone_asleep"
SLEEP = "input_text.sleeping_rooms"
PRESENCE = fixture["ROOMS"]


class DeviceSleep(unittest.TestCase):
    def setUp(self):
        h = self.hass = fixture["Hass"]()
        # test_beta110_device_setting installs a different HA fixture after
        # the policy importer. Use the room registry for the presence fixture.
        sys.modules["homeassistant.helpers.area_registry"].async_get = lambda hass: hass.areas
        self.now = fixture["NOW"].timestamp()
        self.shared = fixture["room_config"](sleep_rooms_entity=SLEEP)
        self.plan = {"status":"ready", "global_presence":self.shared,
                     "known_presence_areas":["living","bath"], "occupancy":"unoccupied",
                     "away":"home", "sleeping":False, "profile":"home"}
        self.manager = N(hass=h, settings={"climate_rooms":{"living":{"occupancy_sensors":[]}},
            model.SETTINGS:{"first":{"control_mode":"pid",FLAG:True},
                            "second":{"control_mode":"automatic"}}},
            plan=N(environment={"living":{"climate_plan":self.plan}}))
        self.a = model.ManagedDevice("first", "living","First","device1",("climate.first",))
        self.b = model.ManagedDevice("second","living","Second","device2",("climate.second",))
        h.put(PRESENCE, '["Bathroom"]')
        h.put(SLEEP, '["Bathroom"]')

    def facts(self, device):
        return model.plan_for(self.manager, device)

    def profile(self, device):
        return model.profile_name(model.settings(self.manager, device), self.facts(device))

    def status(self, device):
        self.manager.equipment = N(statuses={}, records={}, clock=lambda: self.now)
        view = N(_manager=self.manager, _spec=device,
                 controller_settings=model.settings(self.manager, device))
        with patch.object(model, "capabilities", return_value=None), \
                patch.object(model, "sources_available", return_value=False):
            return status_scope["extra_state_attributes"](view)

    def test_one_device_joins_household_sleep_without_marking_its_empty_room_occupied(self):
        self.assertEqual(self.profile(self.a), "sleep")
        self.assertEqual(self.profile(self.b), "home")
        facts = self.facts(self.a)
        self.assertEqual(facts["occupancy"], "unoccupied")
        self.assertFalse(self.plan["sleeping"])
        self.assertEqual(facts["sleep_schedule_evidence"], "all_occupied_rooms_sleeping")
        self.assertEqual(self.status(self.a)["effective_preset"], "sleep")
        self.assertEqual(self.status(self.b)["effective_preset"], "home")
        self.assertTrue(self.status(self.a)["sleep_when_everyone_asleep"])
        self.assertEqual(self.status(self.a)["sleep_evidence"], "all_occupied_rooms_sleeping")
        # Configured topology (no cached room plan) gives the same outcome.
        self.manager.plan.environment.clear()
        self.manager.settings.update(occupancy_global=self.shared, areas=["living","bath"])
        self.assertEqual(self.profile(self.a), "sleep")
        self.assertEqual(self.profile(self.b), "home")

    def test_native_only_plan_uses_explicit_room_selection_and_numeric_freshness(self):
        self.shared.pop("occupied_rooms_entity")
        self.manager.plan.environment.clear()
        count = "sensor.bath_people"
        self.manager.settings.update(occupancy_global=self.shared, areas=["living", "bath"])
        self.manager.settings["climate_rooms"]["bath"] = {
            "occupancy_sensors": [count], "occupancy_stale_minutes": 10,
        }
        self.hass.put(fixture["MOTION"], "on")  # Explicit [] in living ignores this.
        self.hass.put(count, "1", area="bath", age=15)
        self.assertEqual(self.profile(self.a), "sleep", "Automatic permits a sampled count within its 240-minute limit")
        self.manager.settings["climate_rooms"]["bath"]["occupancy_freshness_mode"] = "custom"
        self.assertNotEqual(self.profile(self.a), "sleep", "A stale Custom-limited count cannot prove everyone asleep")
        self.manager.settings["climate_rooms"]["bath"]["occupancy_stale_minutes"] = 20
        self.assertEqual(self.profile(self.a), "sleep")
        self.assertEqual(self.facts(self.a)["occupancy"], "unoccupied")
        self.assertNotIn("_room_occupancy_selections", self.shared)

    def test_targets_pause_quiet_and_presence_gate_agree(self):
        facts = self.facts(self.a)
        room = self.manager.settings["climate_rooms"]["living"]
        cfg = model.settings(self.manager, self.a)
        cap = model.Capabilities("climate.first","climate",("off","heat"),temperature=True)
        with patch.object(model, "device_limits", return_value={
                "temperature_min_limit":5,"temperature_max_limit":35,
                "humidity_min_limit":20,"humidity_max_limit":80}):
            target = model.targets(self.manager, self.a, cap, cfg, facts)
            self.assertEqual(target["heat"], model.DEFAULT_PROFILE_TARGETS["sleep"]["heat_c"])
        dev = {FLAG:True,"auto_control":True,"presence_requirement":"always","sleep_behavior":"pause"}
        self.assertEqual(policy.live_device_permission(self.hass,"living",room,facts,dev)[1],
                         "sleep_room_control_paused")
        self.assertEqual(policy.live_device_permission(self.hass,"living",room,facts,
                         {**dev, "sleep_behavior":"sleep_targets", "presence_requirement":"occupied"})[1],
                         "sleep_room_control_paused")
        self.assertEqual(policy.live_device_permission(self.hass,"living",room,facts,
                         {**dev,"auto_control":False})[0], "held")
        rt = N(manager=self.manager,hass=self.hass,clock=lambda:self.now)
        self.assertTrue(quiet(rt,self.a,{**cfg,"quiet_sleep":True},facts))
        # A new awake occupant invalidates cached household proof before a write.
        self.hass.put(PRESENCE, '["Living room","Bathroom"]')
        self.assertEqual(policy.live_device_permission(self.hass,"living",room,facts,dev)[0],
                         "eligible")
        self.assertFalse(quiet(rt,self.a,{**cfg,"quiet_sleep":True},facts))
        self.assertEqual(self.profile(self.a), "comfort")

    def test_verified_away_empty_house_and_manual_mode_precedence(self):
        self.hass.put(PRESENCE, '[]')
        self.assertNotEqual(self.profile(self.a), "sleep")
        self.shared["home_trackers"] = [fixture["PERSON"]]
        self.hass.put(fixture["PERSON"],"not_home")
        self.hass.put(PRESENCE,'["Bathroom"]')
        self.assertEqual(self.profile(self.a), "away")
        self.hass.put(fixture["PERSON"],"home")
        self.manager.settings[model.SETTINGS]["first"]["control_mode"] = "manual"
        self.assertEqual(self.profile(self.a), "manual")
        self.assertFalse(self.facts(self.a)["sleeping"])
        self.manager.settings[model.SETTINGS]["first"]["preset"] = "eco"
        self.assertEqual(self.profile(self.a), "eco")

    def test_alarm_cuts_inherited_sleep_for_targets_and_live_pause_checks(self):
        alarm,lead = "sensor.phone_alarm","input_number.wake_minutes"
        self.shared.update(wake_alarm_entity=alarm,wake_lead_minutes_entity=lead,_wake_entry_id="entry")
        self.hass.data = {wake._TRACKERS:{"entry":wake.WakeAlarm((alarm,lead),None)}}
        self.hass.put(alarm,datetime.fromtimestamp(self.now+3600,timezone.utc).isoformat(),
                      attributes={"device_class":"timestamp"})
        self.hass.put(lead,"30",attributes={"unit_of_measurement":"min"})
        dev = {FLAG:True,"auto_control":True,"presence_requirement":"always","sleep_behavior":"pause"}
        with patch("time.time",return_value=self.now+1799):
            cached = self.facts(self.a)
            self.assertTrue(cached["sleeping"])
            self.assertEqual(model.profile_name(model.settings(self.manager,self.a),cached),"sleep")
        with patch("time.time",return_value=self.now+1800):
            self.assertEqual(self.profile(self.a),"home")
            self.assertEqual(policy.live_device_permission(self.hass, "living", {}, cached, dev)[0],"eligible")
            self.assertEqual(self.status(self.a)["effective_preset"], "home")
            self.assertEqual(self.status(self.a)["sleep_evidence"], "wake_before_alarm")
            self.assertFalse(self.status(self.a)["sleeping"])
            self.assertEqual(self.status(self.b)["effective_preset"], "home")
        self.hass.put(alarm,datetime.fromtimestamp(self.now+90000,timezone.utc).isoformat(),
                      attributes={"device_class":"timestamp"})
        with patch("time.time",return_value=self.now+3601):
            self.assertEqual(self.profile(self.a),"home")


class PreferenceAndRetry(unittest.IsolatedAsyncioTestCase):
    async def test_alarm_during_pid_checkpoint_cannot_send_the_old_sleep_target(self):
        rt = native["NativeRuntime"]("pid", "heat")
        rt.manager.power_grant = False  # Setpoint-only authorization.
        rt.manager.settings["timed_setpoint_sequence"] = False
        rt.report(mode="heat", temperature=20.)
        rt.measurement = 15.
        rt.manager.targets["heat"] = 18.
        rt.manager.plan["sleeping"] = True

        async def wake_while_saving(*args):
            rt.manager.plan["sleeping"] = False
            rt.manager.targets["heat"] = 22.

        rt._checkpoint_pid = wake_while_saving
        await rt.tick(native["SPEC"])
        self.assertEqual(len(rt.calls), 1)
        self.assertEqual(rt.calls[0]["service"], "set_temperature")
        self.assertEqual(rt.calls[0]["data"], {"temperature": 20.5},
                         "Wake must raise toward the current goal, keeping the existing 0.5°C step")
        self.assertFalse(rt.record["pending"]["power"], "No new power authority")

    async def test_changed_sleep_profile_refreshes_only_its_device_when_demand_is_unchanged(self):
        rt = native["NativeRuntime"]("pid", "heat")
        rt.manager.settings["timed_setpoint_sequence"] = False
        rt.manager.plan.update(occupancy="unoccupied", sleeping=True,
                               sleep_schedule_evidence="all_occupied_rooms_sleeping")
        rt.measurement = 23.  # Both profiles are already satisfied.
        rt.manager.targets["heat"] = 18.
        rt._presentation_context = {}
        signals = []
        rt._presentation_updates = N(request=signals.append)
        await rt.tick(native["SPEC"])
        initial_status = deepcopy(rt.statuses[-1])
        signals.clear()
        await rt.tick(native["SPEC"])
        self.assertEqual(signals, [], "Unchanged policy must not cause extra updates")
        rt.manager.plan.update(sleeping=False, sleep_schedule_evidence="wake_before_alarm")
        await rt.tick(native["SPEC"])
        self.assertEqual(rt.statuses[-1], initial_status)
        self.assertEqual(signals, [native["SPEC"].identifier])
        self.assertEqual(rt._presentation_context[native["SPEC"].identifier][0], "home")
        self.assertEqual(rt.calls, [], "Refreshing a diagnostic is not a hardware command")

    async def test_option_survives_offline_pending_state_does_not_authorize_or_demote(self):
        case = writer["SettingTests"]()
        case.setUp()
        case.states.clear()
        switch = writer["platform"].EquipmentHouseholdSleepSwitch(case.manager, case.a)
        before = deepcopy(case.manager.entry.options)
        holds = deepcopy(case.holds)
        self.assertTrue(switch.available)
        self.assertFalse(switch.is_on)
        await switch.async_turn_on()
        self.assertTrue(switch.is_on)
        self.assertEqual(case.manager.entry.options[model.SETTINGS][case.a.identifier],
            {**before[model.SETTINGS][case.a.identifier], FLAG:True})
        self.assertEqual(case.holds, holds)
        self.assertEqual(case.manager.entry.options[model.SETTINGS][case.b.identifier],
                         before[model.SETTINGS][case.b.identifier])
        with self.assertRaises(ValueError):
            await case.manager.equipment.async_update(case.a,{FLAG:1})
        await switch.async_turn_off()
        self.assertFalse(switch.is_on)

    async def test_preference_preserves_frozen_options_and_concurrent_profile_edit(self):
        case = writer["SettingTests"]()
        case.setUp()
        m, rt = case.manager, case.manager.equipment
        m.entry.options[model.SETTINGS][case.a.identifier]["control_mode"] = "existing"
        case.states.clear()
        # HA exposes read-only entry.options; the save must make a mutable
        # isolated copy, and another controller's authorization must survive.
        m.entry.options = MappingProxyType(m.entry.options)
        peer_before = deepcopy(m.settings[model.SETTINGS][case.b.identifier])
        rt._record = lambda device: case.holds[device.identifier]
        device_lock = asyncio.Lock()
        rt._lock = lambda key: device_lock
        rt._status = lambda *args, **kw: None
        m._device_settings_write_lock = asyncio.Lock()
        switch = writer["platform"].EquipmentHouseholdSleepSwitch(m, case.a)
        async with m._device_settings_write_lock:
            enabling = asyncio.create_task(switch.async_turn_on())
            await asyncio.sleep(0)
            editing = asyncio.create_task(rt.async_update(case.a, {"power_switch_cooldown_seconds": 180}))
            await asyncio.sleep(0)
            self.assertTrue(device_lock.locked())
        await asyncio.gather(enabling, editing)
        cfg = model.settings(m, case.a)
        self.assertTrue(cfg[FLAG])
        self.assertEqual(cfg["power_switch_cooldown_seconds"], 180)
        self.assertEqual(cfg["control_mode"], "existing")
        self.assertEqual(m.settings[model.SETTINGS][case.b.identifier], peer_before)

    async def test_in_flight_sleep_command_is_verified_without_manual_pause_or_stale_replay(self):
        rt = retries["SimRuntime"]()
        pending = rt.pending()
        pending["retry_context"]["profile"] = "sleep"
        rt.now += 31
        original = deepcopy(pending)
        await rt._retry_pending(retries["SPEC"],pending,rt.now)
        self.assertEqual(pending,original)
        self.assertFalse(rt.record.get("paused"))
        self.assertEqual(rt.manager.settings["cfg"]["control_mode"],"pid")
        self.assertEqual(rt.record["automatic_continue_requested"]["method"],"pid")
        self.assertFalse(rt.calls)

    async def test_alarm_cancels_in_flight_sleep_pause_even_with_explicit_direction(self):
        rt = retries["SimRuntime"]("heat")
        pending = rt.pending()
        pending.update(data={"hvac_mode":"off"}, expected={"state":"off"})
        pending["retry_context"].update(mode="off", automatic=False, policy_stop="sleep")
        rt._stop_policy_verified = lambda *args: False
        rt.now += 31
        original = deepcopy(pending)
        await rt._retry_pending(retries["SPEC"], pending, rt.now)
        self.assertEqual(pending, original)
        self.assertFalse(rt.record.get("paused"))
        self.assertIn("automatic_continue_requested", rt.record)
        self.assertEqual(rt.manager.settings["cfg"]["requested_mode"], "heat")
        self.assertFalse(rt.calls)

    async def test_wake_boundary_during_retry_save_restores_original_attempt(self):
        rt = retries["SimRuntime"]()
        rt.measurements = lambda *args: {"temperature": 15., "humidity": 55.,
                                        "co2": None, "pm25": None}
        pending = rt.pending()
        pending["retry_context"]["profile"] = rt.manager.plan["profile"] = "sleep"
        rt.now += 31
        original = deepcopy(pending)
        save = rt._save

        async def wake_after_reservation():
            await save()
            if pending.get("phase") == "retry_intent":
                rt.manager.plan["profile"] = "home"

        rt._save = wake_after_reservation
        await rt._retry_pending(retries["SPEC"], pending, rt.now)
        self.assertEqual(pending, original)
        self.assertFalse(rt.calls)
        self.assertFalse(rt.record.get("paused"))
        await rt._retry_pending(retries["SPEC"], pending, rt.now)
        self.assertIn("automatic_continue_requested", rt.record)
        self.assertFalse(rt.calls)

    async def test_sleep_pause_reconciles_active_command_with_unchanged_explicit_preset(self):
        rt = retries["SimRuntime"]()
        rt.manager.plan.update(profile="eco", sleeping=True)
        rt.manager.settings["cfg"]["sleep_behavior"] = "pause"
        pending = rt.pending()
        pending["retry_context"]["profile"] = "eco"
        rt._gate = lambda *args, **kwargs: "sleep_room_control_paused"
        rt.now += 31
        original = deepcopy(pending)
        await rt._retry_pending(retries["SPEC"], pending, rt.now)
        self.assertEqual(pending, original)
        self.assertFalse(rt.calls)
        self.assertFalse(rt.record.get("paused"))
        self.assertIn("automatic_continue_requested", rt.record)


if __name__ == "__main__":
    unittest.main(verbosity=2)

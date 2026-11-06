"""General settings, offline device switches and delivery of the actual wake timer."""
import ast
import asyncio
from datetime import datetime, timezone
import importlib
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
general = runpy.run_path(str(ROOT / ".github/tests/test_beta79_general_form.py"))
native = runpy.run_path(str(ROOT / ".github/tests/test_bugfix_native_settings.py"))
ALARM, LEAD = "sensor.next_alarm", "input_number.minutes"
alarm_key, lead_key = "general_wake_alarm_entity", "general_wake_lead_minutes_entity"

class SetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_pair_is_optional_saved_and_clearable(self):
        ui = general["UI"]()
        show = general["real"]
        page = await show(ui)
        self.assertIn(alarm_key, page["data_schema"])
        self.assertIn(lead_key, page["data_schema"])
        for values in ({alarm_key: ALARM}, {lead_key: LEAD}):
            page = await show(ui, values)
            self.assertEqual(page["errors"][lead_key], "wake_sources_pair")
            self.assertEqual(ui.saved, 0)
        self.assertIn("saved", await show(ui, {alarm_key: ALARM, lead_key: LEAD}))
        self.assertIn("saved", await show(ui, {"general_source_stale_minutes": 90}))
        settings = ui._values["occupancy_global"]
        self.assertEqual((settings["wake_alarm_entity"], settings["wake_lead_minutes_entity"]), (ALARM, LEAD))
        self.assertIn("saved", await show(ui, {alarm_key: "none", lead_key: "none"}))
        self.assertIsNone(ui._values["occupancy_global"]["wake_alarm_entity"])
        self.assertIsNone(ui._values["occupancy_global"]["wake_lead_minutes_entity"])

    async def test_list_attributes_must_belong_to_the_selected_source(self):
        ui = general["UI"]()
        ui._room_attribute_options = lambda h, e: ([{"value":"__state__"}, {"value":"rooms"}]
            if e == "input_text.occupied_rooms" else [{"value":"__state__"}])
        show = general["real"]
        key = "general_occupied_rooms_attribute"
        failed = await show(ui, {key:"some_other_attribute"})
        self.assertEqual(failed["errors"][key], "general_invalid_attribute")
        self.assertIn("saved", await show(ui, {key:"rooms"}))
        self.assertEqual(ui._values["occupancy_global"]["occupied_rooms_attribute"], "rooms")
        self.assertIn("saved", await show(ui, {key:"__state__"}))
        self.assertEqual(ui._values["occupancy_global"]["occupied_rooms_attribute"], "")

    async def test_household_switch_present_and_writable_when_native_is_offline(self):
        f = native["Fixture"](online=False)
        await f.setup()
        switch = f.added["switch"][f"{f.spec.identifier}_sleep_when_everyone_asleep"]
        f.equipment._ready = True
        self.assertTrue(switch.available)
        self.assertFalse(switch.is_on)
        writes = []
        async def update(spec, settings):
            writes.append((spec, settings))
        f.equipment.async_update = update
        await switch.async_turn_on()
        await switch.async_turn_off()
        self.assertEqual(writes, [(f.spec, {"sleep_when_everyone_asleep": True}),
                                  (f.spec, {"sleep_when_everyone_asleep": False})])

class TimerTests(unittest.TestCase):
    def test_timer_reschedules_cancels_and_rechecks_only_current_deadline(self):
        package = ModuleType("beta120_timer"); package.__path__ = [str(ROOT)]
        sys.modules[package.__name__] = package
        klass = next(k for k in ast.parse((ROOT / "manager.py").read_text()).body
                     if isinstance(k, ast.ClassDef) and k.name == "AirQualityManager")
        node = next(n for n in klass.body if getattr(n,"name",None) == "_sync_wake_boundary")
        now = [datetime(2026,11,6,6,tzinfo=timezone.utc).timestamp()]
        states = {ALARM: N(state="2026-11-06T07:00:00+00:00",attributes={}),
                  LEAD: N(state="30",attributes={"unit_of_measurement":"min"})}
        cfg = {"wake_alarm_entity":ALARM, "wake_lead_minutes_entity":LEAD}
        timers, recalcs = [], []
        def later(hass, delay, cb):
            task = N(delay=delay, call=cb, cancelled=False)
            timers.append(task)
            return lambda:setattr(task, "cancelled", True)
        env = dict(__package__=package.__name__, time=lambda:now[0],
                   callback=lambda f:f, async_call_later=later)
        exec(compile(ast.Module([node],type_ignores=[]), "manager.py", "exec"),env)
        sync = env["_sync_wake_boundary"]
        owner = N(hass=N(states=states,config=N(time_zone="UTC")), _active=True,
                  _wake_boundary=None, _wake_boundary_unsub=None, _recalculate=lambda:recalcs.append(now[0]))
        sync(owner,cfg); sync(owner,cfg)
        self.assertEqual([t.delay for t in timers],[1800])
        states[LEAD].state = "45"
        sync(owner,cfg)
        self.assertTrue(timers[0].cancelled)
        self.assertEqual(timers[1].delay,900)
        timers[0].call(None)
        self.assertFalse(recalcs)
        now[0] += 900
        timers[1].call(None)
        self.assertEqual(recalcs, now)
        sync(owner,cfg)
        self.assertEqual(len(timers),2)
        states[ALARM].state = "2026-11-07T07:00:00+00:00"
        sync(owner,cfg)
        sync(owner,{})
        self.assertTrue(timers[-1].cancelled)
        timers[-1].call(None)
        self.assertEqual(recalcs, now)

if __name__ == "__main__":
    unittest.main()

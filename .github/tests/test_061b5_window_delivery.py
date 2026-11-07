"""Window requests use the actual manager scheduler and delivery transport.

No Home Assistant services are contacted: only the transport and clock are
replaced. Production message formatting, priorities and method bodies run.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import replace
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
fixture_module = runpy.run_path(str(Path(__file__).with_name(
    "test_061b5_announcement_delivery.py")))
fixture = fixture_module["fixture"]
logic, const, hub = (fixture_module[key] for key in ("logic","const","hub"))


class SubmissionProbe:
    def __init__(self):
        self.accepted = []
        self.failed = []
        self.started = []

    def begin_submission(self, recommendation):
        self.started.append(recommendation)

    def submitted(self, recommendation):
        self.accepted.append(recommendation)

    def submission_failed(self, recommendation):
        self.failed.append(recommendation)


class WindowDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_needed_open_uses_warning_and_forwards_ai_with_all_source_cautions(self):
        manager = fixture("el")
        manager.settings.update({const.CONF_HUB: True,"ai_rewrite": True})
        manager.hass.hub_installed = True
        manager.window_open_wait = SubmissionProbe()
        rec = replace(manager.plan.recommendations[0], wait_seconds=300,
                      cautions=(logic.Reason("weather_cold",value="3 °C"),
                                logic.Reason("weather_wind",value="38 km/h"),
                                logic.Reason("weather_condition",value="rainy"),
                                logic.Reason("outside_pm25","PM2.5","42 µg/m³")))
        manager.plan.recommendations = (rec,)
        outcome = await manager.async_announce(channels="auto")
        self.assertEqual(outcome,{"submitted":1,"errors":[]})
        payload = manager.hass.services.calls[0].data
        self.assertEqual(payload["level"],"warning")
        self.assertIs(payload["use_ai"],True)
        self.assertEqual(payload["ai_mode"],"rewrite")
        for value in ("3 °C","38 km/h","42 µg/m³","5"):
            self.assertIn(value,payload["text"])
        self.assertEqual(manager.window_open_wait.accepted,[rec])
        self.assertEqual(manager.window_open_wait.failed,[])
        self.assertEqual(manager.hass.rewrites,[])

    async def test_rejected_hub_releases_exact_request_without_local_duplicate(self):
        manager = fixture()
        manager.settings[const.CONF_HUB] = True
        manager.hass.hub_installed = True
        manager.hass.services.accepted = False
        manager.window_open_wait = SubmissionProbe()
        rec = replace(manager.plan.recommendations[0],wait_seconds=300)
        manager.plan.recommendations = (rec,)
        outcome = await manager.async_announce(channels="auto")
        self.assertEqual(outcome["submitted"],0)
        self.assertEqual(manager.window_open_wait.accepted,[])
        self.assertEqual(manager.window_open_wait.failed,[rec])
        self.assertEqual(len(manager.hass.services.calls),1)

    async def test_two_direct_channels_arm_one_room_request_once(self):
        manager = fixture()
        manager.window_open_wait = SubmissionProbe()
        rec = replace(manager.plan.recommendations[0],wait_seconds=300)
        manager.plan.recommendations = (rec,)
        result = await manager.async_announce(channels="both")
        self.assertEqual(result,{"submitted":2,"errors":[]})
        self.assertEqual(manager.window_open_wait.accepted,[rec])

    async def test_stuck_direct_tts_is_bounded_and_releases_failed_request(self):
        manager = fixture()
        manager.window_open_wait = SubmissionProbe()
        rec = replace(manager.plan.recommendations[0],wait_seconds=300)
        manager.plan.recommendations = (rec,)
        cancelled = []

        async def stuck(*args,**kwargs):
            try:
                await asyncio.Future()
            finally:
                cancelled.append(True)

        manager.hass.services.async_call = stuck
        real_wait_for = asyncio.wait_for
        budgets = []

        async def quick_deadline(awaitable,timeout):
            budgets.append(timeout)
            return await real_wait_for(awaitable,0.001)

        with patch.object(asyncio,"wait_for",quick_deadline):
            outcome = await manager.async_announce(channels="tts")
        self.assertEqual(budgets,[30])
        self.assertEqual(cancelled,[True])
        self.assertEqual(outcome["submitted"],0)
        self.assertEqual(manager.window_open_wait.failed,[rec])

    async def test_priority_preserves_optional_timing_reminders_and_channel_selection(self):
        manager = fixture()
        base = manager.plan.recommendations[0]
        reminder = replace(base,reasons=(logic.Reason("air_refresh_wake"),))
        for rec,expected in ((base,"warning"),(reminder,"info"),
                             (replace(reminder,cautions=(logic.Reason("weather_cold"),)),"warning")):
            payload = hub.make_hub_payload(rec,"title","message",speech=True,
                                           visual=False,language="de",use_ai=False,agent_id="default")
            self.assertEqual(payload["level"],expected)
            self.assertEqual(payload["text_tts"],"message")
            self.assertNotIn("text",payload)
            self.assertNotIn("text_notify",payload)


class ManagerSchedulerTests(unittest.TestCase):
    def make_manager(self,wait_seconds=0):
        methods = {"_recalculate","_plan_without_poll_clock","_queue_automatic",
                   "_cancel_pending","_cancel_repeat","_schedule_repeat",
                   "_automatic_channels_enabled","repeat_minutes"}
        tree = ast.parse((ROOT/"manager.py").read_text())
        manager_class = next(item for item in tree.body if isinstance(item,ast.ClassDef)
                             and item.name == "AirQualityManager")
        selected = [item for item in manager_class.body if isinstance(item,ast.FunctionDef)
                    and item.name in methods]
        compiled = ast.ClassDef(name="Scheduler",bases=[],keywords=[],body=selected,decorator_list=[])
        self.timers = []

        def timer(hass,delay,callback):
            entry = N(delay=delay,callback=callback,cancelled=False)
            self.timers.append(entry)
            return lambda: setattr(entry,"cancelled",True)

        scope = {**vars(const),"__name__":"window_scheduler","Plan":logic.Plan,
                 "callback":lambda fn:fn,"replace":replace,"Any":object,
                 "async_call_later":timer,"async_dispatcher_send":lambda *args:None,
                 "equipment_legacy_settings":lambda manager:({},{}),
                 "_LOGGER":fixture_module["logging"].getLogger("window_scheduler")}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[compiled],type_ignores=[])),
                     str(ROOT/"manager.py"),"exec"),scope)
        manager = scope["Scheduler"]()
        rec = replace(fixture().plan.recommendations[0],wait_seconds=wait_seconds)
        self.plan = logic.Plan("open",True,(),(rec,),(),environment={
            rec.area_id:{"window_open_wait":{"status":"window_request_pending"}}
        })
        manager.settings = {const.CONF_AUTO_TTS:True,const.CONF_REPEAT_MINUTES:0}
        manager.hass = N()
        manager.entry = N(entry_id="fixture")
        manager._source_refresh_handle = None
        manager._active = True
        manager._active_actions = {}
        manager._pending_unsubs = {}
        manager._repeat_unsubs = {}
        manager._sending_actions = {}
        manager.plan = logic.Plan("idle",True,(),(),())
        manager.window_open_wait = N(prepare=lambda plan:plan)
        manager._capture = lambda:self.plan
        for name in ("pid","native_climate","direct_climate","native_humidity",
                     "humidity_power","secondary_climate","running_fans","fan_power",
                     "native_air_mode","equipment","shading"):
            setattr(manager,name,N(schedule=lambda *args,**kwargs:None))
        manager.away_windows = N(observe=lambda **kwargs:None)
        return manager,rec

    def test_first_startup_notice_does_not_require_repeat_reminders(self):
        manager,_ = self.make_manager()
        manager._recalculate(initial=True)
        self.assertEqual([timer.delay for timer in self.timers],[const.ANNOUNCE_OPEN_STABLE_SECONDS])
        self.assertEqual(manager._repeat_unsubs,{})

    def test_pending_device_start_requests_immediately_and_does_not_duplicate(self):
        manager,_ = self.make_manager(300)
        manager._recalculate(initial=True)
        manager._recalculate()
        self.assertEqual([timer.delay for timer in self.timers],[0])

    def test_new_caution_is_announced_with_repeats_disabled(self):
        manager,rec = self.make_manager()
        manager._recalculate(initial=True)
        self.plan = replace(self.plan,recommendations=(
            replace(rec,cautions=(logic.Reason("weather_cold",value="3 °C"),)),))
        manager._recalculate()
        self.assertTrue(self.timers[0].cancelled)
        self.assertEqual(len(self.timers),2)

    def test_existing_air_need_can_gain_a_prestart_request(self):
        manager,rec = self.make_manager()
        manager._recalculate(initial=True)
        manager._cancel_pending()
        self.plan = replace(self.plan,recommendations=(replace(rec,wait_seconds=300),))
        manager._recalculate()
        self.assertEqual(self.timers[-1].delay,0)


if __name__ == "__main__":
    unittest.main()

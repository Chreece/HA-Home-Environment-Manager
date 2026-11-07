"""Removed timing flags cannot alter native command traces on the production runtime.

The Beta109 harness isolates HA transport, settings, persistence and time.
The actual decision, intent, dispatch, retry and observation paths run here.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / ".github/tests/test_beta109_setpoint_sequence.py"))
Runtime, SPEC, PRIMARY = (base[k] for k in ("SequenceRuntime", "SPEC", "PRIMARY"))
model, production, fixture = (base[k] for k in ("model", "production", "fixture"))
KEY = "timed_setpoint_sequence"
UNSET = object()


def choose(runtime, value):
    if value is UNSET:
        runtime.manager.settings.pop(KEY, None)
    else:
        runtime.manager.settings[KEY] = value


def calls(runtime):
    return [(c["service"], c["data"]) for c in runtime.calls]


OFF = ("set_hvac_mode", {"hvac_mode": "off"})


class OptInTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_true_false_and_invalid_saved_flags_use_the_same_trace(self):
        for value in (UNSET,True,False,None,1,"true"):
            for method in ("automatic","pid"):
                for mode in ("heat","cool"):
                    with self.subTest(value=str(value),method=method,mode=mode):
                        r=Runtime(method,mode)
                        choose(r,value)
                        r.manager.settings["kp"]=100.
                        await r.evaluate()
                        mode_on=("set_hvac_mode",{"hvac_mode":mode})
                        self.assertEqual(calls(r),[mode_on])
                        self.assertFalse(r.record["power"])
                        r.report(mode=mode)
                        ack_at=r.now
                        await r.evaluate()
                        target=("set_temperature",{"temperature":r.requested_target})
                        self.assertEqual(calls(r),[mode_on,target])
                        self.assertEqual(r.call_times[-1],ack_at)
                        r.report(temperature=r.requested_target)
                        r.open_window()
                        await r.evaluate(599.999)
                        self.assertEqual(calls(r),[mode_on,target])
                        await r.evaluate(.001)
                        self.assertEqual(calls(r),[mode_on,target,OFF])
                        self.assertNotIn("native_setpoint_stop",r.record)
                        self.assertIn(PRIMARY,r.record["power"])
                        deadlines=[h.deadline for h in r.timer_loop.handles if not h.cancelled() and not h.fired]
                        self.assertEqual(deadlines,[r.now+60])

    async def test_removed_flag_cannot_add_a_delay_to_soft_targets(self):
        for service,data in (("set_temperature",{"temperature":20.}),
                             ("set_temperature",{"target_temp_low":19.,"target_temp_high":25.}),
                             ("set_humidity",{"humidity":45.})):
            r=Runtime("manual")
            choose(r,True)
            r.manager.power_grant=False
            r.state.attributes.update(supported_features=7,humidity=60.,target_temp_low=18.,target_temp_high=26.)
            r.report(mode="heat")
            self.assertTrue(await r.command(service,data))
            self.assertEqual(calls(r),[(service,data)])
            self.assertEqual(r.call_times[-1],r.state.last_changed.timestamp())

    async def test_maximum_on_has_no_pre_stop_target_or_lead(self):
        for value in (UNSET,False,True):
            r=Runtime("automatic","cool")
            choose(r,value)
            r.running_extreme(age=7169)
            await r.evaluate()
            await r.evaluate(1)
            await r.evaluate(29.999)
            self.assertFalse(r.calls)
            await r.evaluate(.001)
            self.assertEqual(calls(r),[OFF])
            self.assertEqual(r.call_times[-1]-r.record["power"][PRIMARY]["since"],7200)

    async def test_raw_legacy_flag_change_during_off_reservation_cannot_create_reverse_write(self):
        for value in (True,False):
            for stage in ("intent_save","semaphore"):
                with self.subTest(value=value,stage=stage):
                    r=Runtime("automatic")
                    r.running_extreme()
                    r.open_window()
                    choose(r,value)
                    saved=asyncio.Event()
                    def at_intent(controller):
                        if (controller.record.get("pending") or {}).get("phase")=="intent":
                            controller.after_persist=None
                            saved.set()
                            if stage=="intent_save":choose(controller,not value)
                    r.after_persist=at_intent
                    if stage=="semaphore":
                        await r._commands.acquire()
                        task=asyncio.create_task(r.evaluate())
                        await saved.wait()
                        choose(r,not value)
                        r._commands.release()
                        await task
                    else:await r.evaluate()
                    self.assertEqual(calls(r),[OFF])
                    self.assertNotIn("native_setpoint_stop",r.record)

    async def test_saved_off_completion_has_no_delay_after_flag_cleanup(self):
        for value in (UNSET,False,True):
            r=Runtime("automatic")
            old=base["seed_legacy_stop"](r)
            choose(r,value)
            await r.evaluate()
            self.assertEqual(calls(r),[OFF])
            self.assertEqual(r.record["native_setpoint_stop"]["target_journal"],old)
            self.assertEqual(r.call_times[-1],old["last_attempt_at"])

    async def test_snapshot_with_missing_or_old_true_flag_keeps_the_same_retry_episode(self):
        for saved in (UNSET,True,False):
            r=Runtime("automatic")
            r.running_extreme()
            r.report(temperature=r.original_target)
            r.record["baseline"][PRIMARY]=production.snapshot(r.state)
            await r.evaluate()
            pending=r.record["pending"]
            when=pending["when"]
            if saved is UNSET:pending["retry_context"]["settings"].pop(KEY,None)
            else:pending["retry_context"]["settings"][KEY]=saved
            choose(r,UNSET)
            await r.evaluate(60)
            self.assertIs(r.record["pending"],pending)
            self.assertEqual(pending["attempts"],2)
            self.assertEqual(pending["when"],when)
            self.assertEqual(len(r.calls),2)
            self.assertEqual(r.calls[-1],r.calls[0])

    async def test_full_output_off_still_prevents_normal_target_with_old_true_flag(self):
        r=Runtime("automatic")
        choose(r,True)
        r.manager.settings["native_full_output"]=False
        await r.evaluate()
        r.report(mode="heat")
        await r.evaluate()
        self.assertEqual(calls(r),[("set_hvac_mode",{"hvac_mode":"heat"})])
        r.open_window()
        await r.evaluate(600)
        self.assertEqual(calls(r)[-1],OFF)
        self.assertFalse(any(c[0]=="set_temperature" for c in calls(r)))

    async def test_target_while_native_off_is_still_rejected(self):
        r=Runtime("manual")
        choose(r,True)
        self.assertFalse(await r.command("set_temperature",{"temperature":22.}))
        self.assertFalse(r.calls)

    async def test_existing_minute_retry_timer_cleanup_survives_feature_removal(self):
        r=Runtime("automatic")
        await r.evaluate()
        handles=list(r.timer_loop.handles)
        self.assertTrue(handles)
        base["sequence"].cancel_wakeups(r)
        self.assertTrue(all(h.cancelled() for h in handles))
        r.now += 120
        r.timer_loop.fire_due()
        self.assertEqual(len(r.calls),1)


if __name__=="__main__":
    unittest.main(verbosity=2)

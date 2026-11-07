"""Automatic dispatches retry once per minute without inventing manual input.

Uses production tick, command dispatch, ACK/retry and policy gates with the
existing isolated Home Assistant transport. No hardware service is performed.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / '.github/tests/test_beta108_retry_recovery.py'))
NativeRuntime, SPEC, PRIMARY, production = (
    fixture[name] for name in ('RecoveryRuntime', 'SPEC', 'PRIMARY', 'production')
)


class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def step(self, runtime, seconds=0):
        await runtime.evaluate(seconds)
        await asyncio.sleep(0)

    def runtime(self, method='pid'):
        runtime = NativeRuntime(method, 'heat')
        runtime.notices = []
        runtime.notification_tasks = []
        runtime.manager._tasks = set()
        runtime.manager.entry.options = {}
        production.model.SETTINGS = "equipment_device_settings"

        def update_entry(entry, *, options):
            entry.options = deepcopy(options)
            runtime.manager.settings.update(options[production.model.SETTINGS][SPEC.identifier])

        runtime.hass.config_entries = N(async_update_entry=update_entry)

        async def announce(spec, pending):
            runtime.notices.append((spec.identifier, deepcopy(pending)))

        def create(coroutine):
            task = runtime.create_task(coroutine)
            runtime.notification_tasks.append(task)
            return task

        runtime.manager.async_announce_device_nonresponse = announce
        runtime.hass.async_create_task = create
        return runtime

    async def test_minute_retries_continue_after_three_and_notify_once(self):
        for method in ('automatic', 'pid'):
            with self.subTest(method=method):
                runtime = self.runtime(method)
                await self.step(runtime)
                first = deepcopy(runtime.calls[0])
                for attempt in range(2, 7):
                    await self.step(runtime, 59)
                    self.assertEqual(len(runtime.calls), attempt - 1)
                    await self.step(runtime, 1)
                    self.assertEqual(len(runtime.calls), attempt)
                    self.assertEqual(runtime.calls[-1], first)
                    self.assertEqual(runtime.record['pending']['attempts'], attempt)
                    self.assertFalse(runtime.record.get('paused'))
                    self.assertEqual(runtime.manager.settings['control_mode'], method)
                    self.assertEqual(len(runtime.notices), int(attempt >= 4))
                self.assertEqual(runtime.notices[0][1]['nonresponse_attempts'], 3)
                self.assertFalse(runtime.record['power'], 'A service call is not native ON evidence')

    async def test_service_exceptions_remain_automatic_and_retry(self):
        runtime = self.runtime()
        original = runtime.service_call

        async def rejected(*args, **kwargs):
            await original(*args, **kwargs)
            raise TimeoutError('Device did not acknowledge transport')

        runtime.hass.services.async_call = rejected
        for attempt in range(1, 6):
            await self.step(runtime, 0 if attempt == 1 else 60)
            self.assertEqual(len(runtime.calls), attempt)
            self.assertEqual(runtime.record['pending']['attempts'], attempt)
            self.assertEqual(runtime.record['pending']['phase'], 'commanded')
            self.assertFalse(runtime.record.get('paused'))
        self.assertEqual(len(runtime.notices), 1)
        runtime.report(mode='heat')
        self.assertTrue(await runtime._reconcile(SPEC))
        self.assertIsNone(runtime.record['pending'])
        self.assertIn(PRIMARY, runtime.record['power'])

    async def test_unavailable_checks_do_not_count_and_recovery_respects_off_dwell(self):
        runtime = self.runtime()
        await self.step(runtime)
        await self.step(runtime, 60)
        runtime.report(mode='unavailable')
        await self.step(runtime, 60)
        await self.step(runtime, 60)
        self.assertEqual(len(runtime.calls), 2)
        self.assertEqual(runtime.record['pending']['attempts'], 2)
        runtime.report(mode='off')
        await self.step(runtime, 60)
        self.assertEqual(len(runtime.calls), 2)
        self.assertEqual(runtime.statuses[-1][0], 'minimum_off_hold')
        await self.step(runtime, 541)
        self.assertEqual(len(runtime.calls), 3)
        self.assertFalse(runtime.record.get('paused'))

    async def test_partial_or_stale_user_feedback_before_first_ack_is_not_manual(self):
        runtime = self.runtime()
        runtime.state.context = N(user_id='old-user', parent_id=None, id='old-context')
        await self.step(runtime)
        runtime.state.attributes['temperature'] = 9
        runtime.state.attributes['operation_source'] = 'physical_button'
        await self.step(runtime, 60)
        self.assertEqual(len(runtime.calls), 2)
        self.assertFalse(runtime.record.get('paused'))
        self.assertEqual(runtime.manager.settings['control_mode'], 'pid')
        runtime.report(mode='heat')
        self.assertTrue(await runtime._reconcile(SPEC))
        self.assertIn(PRIMARY, runtime.record['native_control_confirmed'])
        # Firmware reused the context of the old HA action; this is not a new user action.
        runtime.now += 1
        runtime.report(temperature=11)
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        self.assertTrue(await runtime._reconcile(SPEC))
        self.assertFalse(runtime.record.get('paused'))
        # A new direct human action after a verified HEM command remains authoritative.
        runtime.now += 1
        runtime.report(temperature=12)
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        runtime.state.context = N(user_id='user-now', parent_id=None, id='new-context')
        self.assertFalse(await runtime._reconcile(SPEC))
        self.assertEqual(runtime.record.get('paused'), 'physical_manual_override')

    async def test_manual_intervention_while_a_later_command_is_pending_stops_retries(self):
        runtime = self.runtime()
        runtime.own_running(age=700)
        await self.step(runtime)
        self.assertEqual(runtime.record['pending']['service'], 'set_temperature')
        runtime.now += 1
        runtime.report(temperature=18)
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        runtime.state.context = N(user_id='actual-user', parent_id=None, id='manual-change')
        await self.step(runtime, 60)
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.record.get('paused'), 'physical_manual_override')
        self.assertFalse(runtime.notices)

    async def test_legacy_ack_latch_migrates_without_resume_but_manual_and_identity_hold(self):
        for reason in ('physical_acknowledgement_missing', 'native_command_failed_or_uncertain'):
            with self.subTest(reason=reason):
                runtime = self.runtime()
                await self.step(runtime)
                pending = runtime.record['pending']
                pending.pop('retry_policy')
                pending['attempts'] = 4
                runtime.record['paused'] = reason
                runtime.record['automatic_continue_requested'] = {'method': 'pid', 'at': runtime.now}
                await self.step(runtime, 60)
                self.assertEqual(len(runtime.calls), 2)
                self.assertEqual(pending['attempts'], 5)
                self.assertFalse(runtime.record.get('paused'))
                self.assertNotIn('automatic_continue_requested', runtime.record)
        for blocker in ('manual', 'identity'):
            runtime = self.runtime()
            await self.step(runtime)
            if blocker == 'manual':
                runtime.record['paused'] = 'physical_manual_override'
            else:
                runtime._identity_ok = lambda spec: False
            await self.step(runtime, 60)
            self.assertEqual(len(runtime.calls), 1)

    async def test_window_presence_and_foreign_owner_block_retries_without_false_manual(self):
        for blocker in ('window', 'presence', 'owner'):
            with self.subTest(blocker=blocker):
                runtime = self.runtime()
                await self.step(runtime)
                if blocker == 'window':
                    runtime.window.update(blocked=True, status='window_open')
                elif blocker == 'presence':
                    runtime.sleeping = True
                    runtime.manager.device['sleep_behavior'] = 'pause'
                else:
                    runtime.foreign_owner = 'other_entry_owns_climate'
                await self.step(runtime, 60)
                self.assertEqual(len(runtime.calls), 1)
                self.assertNotEqual(runtime.record.get('paused'), 'physical_manual_override')
                runtime.window.update(blocked=False)
                runtime.sleeping = False
                runtime.foreign_owner = None
                await self.step(runtime, 60)
                if blocker == 'owner':
                    self.assertEqual(len(runtime.calls), 2)
                else:
                    self.assertEqual(len(runtime.calls), 1)
                    self.assertIsNotNone(runtime.record.get('automatic_continue_requested'))
                    await self.step(runtime, 60)
                    self.assertIsNone(runtime.record.get('pending'))
                    self.assertIsNone(runtime.record.get('automatic_continue_requested'))
                    await self.step(runtime, 599)
                    self.assertEqual(len(runtime.calls), 1, 'Verified OFF still requires the full OFF dwell')
                    await self.step(runtime, 1)
                    self.assertEqual(len(runtime.calls), 2)
                    self.assertFalse(runtime.record.get('paused'))

    async def test_obsolete_protective_off_recovers_after_policy_ends(self):
        for policy in ('window', 'sleep', 'idle'):
            with self.subTest(policy=policy):
                runtime = self.runtime()
                runtime.manager.settings['timed_setpoint_sequence'] = False
                runtime.own_running(age=700)
                if policy == 'window':
                    runtime.window.update(blocked=True, stop_requested=True)
                elif policy == 'sleep':
                    runtime.sleeping = True
                    runtime.manager.device['sleep_behavior'] = 'pause'
                else:
                    runtime.measurement = runtime.manager.targets['heat'] + 1
                await self.step(runtime)
                original = deepcopy(runtime.record['pending'])
                self.assertEqual(original['data'], {'hvac_mode': 'off'})
                runtime.window.update(blocked=False, stop_requested=False)
                runtime.sleeping = False
                runtime.measurement = runtime.manager.targets['heat'] - 1
                await self.step(runtime, 60)
                self.assertTrue(runtime.record['automatic_continue_requested']['obsolete_native_command'])
                await self.step(runtime, 60)
                self.assertEqual(runtime.record['pending'], original)
                await self.step(runtime, 60)
                self.assertIsNone(runtime.record['pending'])
                self.assertIsNone(runtime.record.get('automatic_continue_requested'))
                self.assertEqual(len(runtime.calls), 1, 'Read-only reconciliation must not replay obsolete OFF')
                await self.step(runtime)
                self.assertEqual(runtime.calls[-1]['service'], 'set_temperature')
                self.assertFalse(runtime.record.get('paused'))
                self.assertEqual(runtime.manager.settings['control_mode'], 'pid')

    async def test_wrong_reported_running_mode_verifies_then_off_before_requested_mode(self):
        runtime = self.runtime()
        runtime.manager.settings['timed_setpoint_sequence'] = False
        runtime.manager.settings['kp'] = 100.0
        await self.step(runtime)
        runtime.now += 1
        runtime.report(mode='cool')
        await self.step(runtime, 60)
        self.assertTrue(runtime.record['automatic_continue_requested']['obsolete_native_command'])
        await self.step(runtime, 60)
        await self.step(runtime, 60)
        self.assertIsNone(runtime.record['pending'])
        self.assertFalse(runtime.record.get('paused'))
        await self.step(runtime, 599)
        self.assertEqual(len(runtime.calls), 1, 'Observed running mode retains full minimum ON')
        await self.step(runtime, 1)
        self.assertEqual(runtime.calls[-1]['data'], {'hvac_mode': 'off'})
        self.assertEqual(len(runtime.calls), 2)
        runtime.report(mode='off')
        await self.step(runtime)
        await self.step(runtime, 599)
        self.assertEqual(len(runtime.calls), 2, 'Never reverse heat/cool without physical OFF and dwell')
        await self.step(runtime, 1)
        self.assertEqual(runtime.calls[-1]['data'], {'hvac_mode': 'heat'})
        self.assertFalse(runtime.record.get('paused'))

    async def test_matching_mode_ack_does_not_hide_new_human_temperature_change(self):
        runtime = self.runtime()
        await self.step(runtime)
        runtime.record['native_control_confirmed'] = {
            PRIMARY: {'at': runtime.now - 700, 'context_id': 'older-hem-ack'},
        }
        runtime.now += 1
        runtime.report(mode='heat', temperature=18)
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        runtime.state.context = N(user_id='human', parent_id=None, id='new-manual-temperature')
        await self.step(runtime)
        self.assertEqual(runtime.record['paused'], 'physical_manual_override')
        self.assertEqual(runtime.manager.settings['control_mode'], 'manual')
        self.assertEqual(runtime.record['manual_override_evidence']['kind'], 'ha_user')
        self.assertIn('temperature', runtime.record['manual_override_evidence']['changed_controls'])
        self.assertEqual(len(runtime.calls), 1)

    async def test_timed_stop_ignores_reused_human_context_but_honors_new_action(self):
        runtime = self.runtime()
        runtime.manager.settings['timed_setpoint_sequence'] = True
        runtime.own_running(age=700)
        runtime.state.attributes['fan_mode'] = 'low'
        runtime.state.context = N(user_id='earlier-user', parent_id=None, id='old-context')
        runtime.record['baseline'][PRIMARY] = production.snapshot(runtime.state)
        runtime.record['native_control_confirmed'] = {
            PRIMARY: {'at': runtime.now - 700, 'context_id': 'old-context'},
        }
        runtime.measurement = runtime.manager.targets['heat']
        await self.step(runtime)
        self.assertEqual(runtime.calls[-1]['service'], 'set_temperature')
        requested = runtime.calls[-1]['data']['temperature']
        runtime.now += 1
        runtime.report(temperature=requested)
        runtime.state.attributes['fan_mode'] = 'high'
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        await self.step(runtime)
        self.assertFalse(runtime.record.get('paused'), 'Reused HA context is not another human action')
        runtime.now += 1
        runtime.state.attributes['fan_mode'] = 'medium'
        runtime.state.last_updated = datetime.fromtimestamp(runtime.now, timezone.utc)
        runtime.state.context = N(user_id='new-user', parent_id=None, id='new-action')
        await self.step(runtime)
        self.assertEqual(runtime.record['paused'], 'physical_manual_override')
        self.assertEqual(runtime.manager.settings['control_mode'], 'manual')
        self.assertEqual(len(runtime.calls), 1)

    async def test_shutdown_nonresponse_notice_survives_a_changed_occupancy_profile(self):
        for timed in (False, True):
            with self.subTest(timed=timed):
                runtime = self.runtime()
                runtime.manager.settings['timed_setpoint_sequence'] = timed
                runtime.own_running(age=7200)
                await self.step(runtime)
                if timed:
                    self.assertEqual(runtime.calls[-1]['service'], 'set_temperature')
                    await self.step(runtime, 30)
                self.assertEqual(runtime.calls[-1]['data'], {'hvac_mode': 'off'})
                initial = runtime.record['pending']
                self.assertEqual(initial['retry_context']['automatic'], not timed)
                runtime.manager.plan.update(away=True, occupancy='unoccupied')
                for _ in range(3):
                    await self.step(runtime, 60)
                self.assertIs(runtime.record['pending'], initial)
                self.assertEqual(initial['attempts'], 4)
                self.assertEqual(len(runtime.notices), 1)
                self.assertEqual(runtime.notices[0][1]['nonresponse_attempts'], 3)
                self.assertFalse(runtime.record.get('paused'))

    async def test_notification_task_is_registered_for_unload_cancellation(self):
        runtime = self.runtime()
        await self.step(runtime)
        await self.step(runtime, 60)
        await self.step(runtime, 60)
        entered = asyncio.Event()

        async def blocked_notification(spec, pending):
            entered.set()
            await asyncio.Event().wait()

        runtime.manager.async_announce_device_nonresponse = blocked_notification
        runtime.now += 60
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.manager._tasks), 1)
        await entered.wait()
        task, = runtime.manager._tasks
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.assertFalse(runtime.manager._tasks)
        self.assertTrue(runtime.record['pending']['nonresponse_notified'])

    async def test_ack_before_notification_delivery_suppresses_notice(self):
        runtime = self.runtime()
        pending_callbacks = []
        release = asyncio.Event()

        def create_delayed(coroutine):
            async def delayed():
                await release.wait()
                await coroutine
            task = asyncio.create_task(delayed())
            pending_callbacks.append(task)
            return task

        runtime.hass.async_create_task = create_delayed
        await self.step(runtime)
        await self.step(runtime, 60)
        await self.step(runtime, 60)
        await self.step(runtime, 60)
        self.assertEqual(len(pending_callbacks), 1)
        runtime.report(mode='heat')
        release.set()
        await asyncio.gather(*pending_callbacks)
        self.assertFalse(runtime.notices)
        self.assertFalse(runtime.manager._tasks)


if __name__ == '__main__':
    unittest.main(verbosity=2)

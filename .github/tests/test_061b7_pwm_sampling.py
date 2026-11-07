"""Sampled PID pulses through real native dispatch, ACK, dwell and resets.

Clock, HA transport and qualified room inputs are isolated. Gains, cycle
selection, ownership, command journals and controller decisions are actual
production code. No physical equipment or running Home Assistant is used.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
f = runpy.run_path(str(ROOT / '.github/tests/test_061b7_runtime_modes.py'))
Runtime, SPEC, PRIMARY, production, model = (
    f[key] for key in ('Runtime', 'SPEC', 'PRIMARY', 'production', 'model'))
phase = importlib.import_module(f['PACKAGE'] + '.pid_phase')
f['base']['extract'](ROOT / 'equipment_runtime.py',
                     ('async_stop', '_verify_restart_power'), production.__dict__)


class SampledRuntime(Runtime):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scheduled = 0
        self._pid_pwm_wakeups = {}
        self._native_session_observations = {}
        self._presentation_updates.close = lambda: None

    def schedule(self):
        self.scheduled += 1  # Callback requests; tests explicitly run the locked work.

    _verify_restart_power = production._verify_restart_power


class Driver:
    def __init__(self, *, measured=20.4, off_age=1200, **profile):
        self.r = SampledRuntime(profile={
            'kp': 10., 'ki': 0., 'kd': 0., 'sample_seconds': 300.,
            'cycle_seconds': 600., '_native_timing_version': 1,
            'min_on_seconds': 120., 'min_off_seconds': 120.,
            'max_on_seconds': 7200., **profile,
        }, off_age=off_age)
        self.r.state.attributes['hvac_modes'] = ['off', 'heat']
        self.r.readings['temperature'] = measured
        self.origin = self.r.now
        self.seen = 0
        self.events = []
        self.settings = deepcopy(self.r.manager.settings)

    async def at(self, seconds, *, measured=None, acknowledge=True):
        r = self.r
        assert seconds >= r.now - self.origin
        r.now = self.origin + seconds
        if measured is not None:
            r.readings['temperature'] = measured
        for _ in range(8):
            await r.evaluate()
            calls = r.calls[self.seen:]
            self.seen = len(r.calls)
            if not calls:
                break
            for call in calls:
                self.events.append((seconds, call['service'], deepcopy(call['data'])))
                if acknowledge:
                    if call['service'] == 'set_hvac_mode':
                        r.report(mode=call['data']['hvac_mode'])
                    elif call['service'] == 'set_temperature':
                        r.report(temperature=call['data']['temperature'])
            if not acknowledge:
                break
        assert r.manager.settings == self.settings, 'Scheduling cannot retune saved preferences'

    @property
    def on(self):
        return [t for t, service, data in self.events
                if service == 'set_hvac_mode' and data.get('hvac_mode') == 'heat']

    @property
    def off(self):
        return [t for t, service, data in self.events
                if service == 'set_hvac_mode' and data.get('hvac_mode') == 'off']


class SampledPWMTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_late_poll_starts_only_after_real_off_dwell_and_ack(self):
        d = Driver(measured=20.75, off_age=0)
        await d.at(0)
        anchor = d.r._memory[SPEC.identifier][2]
        self.assertNotIn(SPEC.identifier, d.r._profile_wake)
        for at in (27, 57, 87, 117):
            await d.at(at, measured=20.4)
            self.assertEqual(d.on, [])
            self.assertEqual(d.r._memory[SPEC.identifier][2], anchor)
            self.assertEqual(d.r.record['off_at'][PRIMARY], d.origin)
            self.assertNotIn('pid_pwm_run', d.r.record)
        await d.at(147, acknowledge=False)
        self.assertEqual(d.on, [147], 'Old controller misses every usable start window')
        self.assertEqual(d.r._memory[SPEC.identifier][2], anchor, 'Service return is not native ACK')
        pending = deepcopy(d.r.record['pending'])
        await d.at(160, acknowledge=False)
        self.assertEqual(d.r.record['pending'], pending)
        self.assertNotIn('pid_pwm_run', d.r.record)
        d.r.now = d.origin + 170
        d.r.report(mode='heat')
        await d.at(170)
        self.assertEqual(d.r.record['power'][PRIMARY]['since'], d.origin + 170)
        self.assertEqual(d.r._memory[SPEC.identifier][2], d.origin + 170)
        self.assertEqual(d.r.record['pid_pwm_run']['confirmed_on_at'], d.origin + 170)
        await d.at(289)
        self.assertEqual(d.off, [])
        await d.at(290)
        self.assertEqual(d.off, [290], 'Full physical minimum starts at confirmed native ON')

    async def test_exact_minimum_pulse_survives_irregular_polling(self):
        d = Driver(measured=20.5)
        for at in (0, 120, 2399, 2401, 2459, 2520):
            await d.at(at)
        self.assertEqual(d.on, [0, 2401])
        self.assertEqual(d.off, [120])
        await d.at(2521)
        self.assertEqual(d.off, [120, 2521])
        await d.at(4802)
        self.assertEqual(d.on, [0, 2401, 4802])

    async def test_missed_whole_windows_coalesce_without_catchup_or_duplicate(self):
        d = Driver(measured=20.5)
        await d.at(0)
        await d.at(120)
        await d.at(10000)
        self.assertEqual(d.on, [0, 10000])
        self.assertEqual(d.r._memory[SPEC.identifier][2], d.origin + 10000)
        await d.at(10120)
        for at in (10240, 11000, 12399):
            await d.at(at)
            self.assertEqual(d.on, [0, 10000])
        await d.at(12400)
        self.assertEqual(d.on, [0, 10000, 12400])

    async def test_late_off_ack_preserves_complete_nominal_rest(self):
        for off_ack in (2350, 5000):
            with self.subTest(off_ack=off_ack):
                d = Driver()
                await d.at(0)
                await d.at(180, acknowledge=False)
                self.assertEqual(d.off, [180])
                d.r.now = d.origin + off_ack
                d.r.report(mode='off')
                await d.at(off_ack)
                self.assertEqual(d.r.record['off_at'][PRIMARY], d.origin + off_ack)
                # 6% of 2400s =144s ON, so a whole nominal OFF is2256s.
                for at in (off_ack + 120, off_ack + 2255):
                    await d.at(at)
                    self.assertEqual(d.on, [0])
                await d.at(off_ack + 2256)
                self.assertEqual(d.on, [0, off_ack + 2256])

    async def test_native_early_off_does_not_replay_current_cycle(self):
        d = Driver(measured=20.5)
        await d.at(0)
        d.r.now = d.origin + 60
        d.r.report(mode='off')  # Native self-stop without a human-origin event.
        await d.at(60)
        self.assertFalse(d.r.record.get('paused'))
        for at in (180, 2399):
            await d.at(at)
            self.assertEqual(d.on, [0])
        await d.at(2400)
        self.assertEqual(d.on, [0, 2400])

    async def test_late_running_pulse_cannot_wrap_through_missed_off_window(self):
        d = Driver(measured=20.001, kp=100., cycle_seconds=2400., min_off_seconds=1.)
        await d.at(0)
        await d.at(2397.5)
        self.assertEqual(d.off, [])
        await d.at(2401)
        self.assertEqual(d.off, [2401])
        await d.at(2403.3)
        self.assertEqual(d.on, [0])
        await d.at(2403.5)
        self.assertEqual(d.on, [0, 2403.5])

    async def test_target_reached_cancels_pending_logical_start(self):
        d = Driver(measured=20.5, off_age=0)
        await d.at(0)
        handle = d.r._pid_pwm_wakeups[SPEC.identifier][1]
        await d.at(119, measured=21.)
        self.assertTrue(handle.cancelled())
        self.assertNotIn(SPEC.identifier, d.r._pid_pwm_wakeups)
        for at in (120, 2401, 10000):
            await d.at(at)
        self.assertEqual(d.on, [])
        self.assertNotIn('pid_pwm_run', d.r.record)
        self.assertEqual(d.r.record['off_at'][PRIMARY], d.origin)

    async def test_pause_unavailable_and_changed_active_intent_cancel_only_math(self):
        for hold in ('pause', 'unavailable', 'window', 'settings'):
            with self.subTest(hold=hold):
                d = Driver(measured=20.5)
                await d.at(0)
                await d.at(120)
                r = d.r
                handle = r._pid_pwm_wakeups[SPEC.identifier][1]
                physical = {key: deepcopy(r.record.get(key))
                            for key in ('power', 'off_at', 'pending', 'native_control_confirmed')}
                if hold == 'pause':
                    await r._pause(SPEC, 'test_pause')
                elif hold == 'unavailable':
                    r.state.state = 'unavailable'
                    await r.evaluate()
                elif hold == 'window':
                    r.window.update(blocked=True, stop_requested=True, status='window_open')
                    await r.evaluate()
                else:
                    await r.async_update(SPEC, {'kp': 11.})
                self.assertTrue(handle.cancelled(), hold)
                self.assertNotIn(SPEC.identifier, r._pid_pwm_wakeups)
                self.assertNotIn('pid_pwm_run', r.record)
                self.assertEqual({key: r.record.get(key) for key in physical}, physical)

    async def test_restart_restores_pulse_marker_without_reanchoring(self):
        for running in (True, False):
            with self.subTest(running=running):
                d = Driver(measured=20.5)
                await d.at(0)
                if not running:
                    await d.at(120)
                r = d.r
                anchor, marker = r._memory[SPEC.identifier][2], deepcopy(r.record['pid_pwm_run'])
                r._cancel_pid_pwm_evaluation(SPEC)
                r._memory.clear()
                r._profile_wake.clear()
                await r.restart()
                await d.at(30 if running else 150)
                # First native report starts the real reconnect cooldown;
                # mathematical restore is evaluated after that stable dwell.
                await d.at(60 if running else 180)
                self.assertEqual(r.record['pid_checkpoint']['anchor'], anchor)
                if running:
                    await d.at(120)
                    self.assertEqual(d.off, [120])
                await d.at(300 if running else 420)
                self.assertEqual(r._memory[SPEC.identifier][2], anchor)
                for key in ('confirmed_on_at', 'served_at', 'anchor', 'signature'):
                    self.assertEqual(r.record['pid_pwm_run'][key], marker[key])
                self.assertEqual(d.on, [0])
                await d.at(2399)
                self.assertEqual(d.on, [0])
                await d.at(2400)
                self.assertEqual(d.on, [0, 2400])

    async def test_explicit_resume_clears_rest_but_preserves_physical_dwell(self):
        d = Driver(measured=20.5)
        await d.at(0)
        await d.at(120)
        r = d.r
        handle = r._pid_pwm_wakeups[SPEC.identifier][1]
        off_at = r.record['off_at'][PRIMARY]
        await r.async_resume(SPEC)
        self.assertTrue(handle.cancelled())
        self.assertNotIn('pid_pwm_run', r.record)
        self.assertEqual(r.record['off_at'][PRIMARY], off_at)
        await d.at(239)
        self.assertEqual(d.on, [0])
        await d.at(240)
        self.assertEqual(d.on, [0, 240])

    async def test_status_reports_evaluated_live_target_and_feedback(self):
        d = Driver()
        await d.at(0)
        await d.at(180)
        await d.at(200)
        self.assertEqual(d.r.status['status'], 'pid_output_inactive')
        self.assertEqual(d.r.status['pid_control_target'], 21.)
        self.assertEqual(d.r.status['pid_control_measurement'], 20.4)
        self.assertAlmostEqual(d.r.status['pid_pwm_next_window_seconds'], 2236.)
        await d.at(201, measured=21.)
        self.assertEqual(d.r.status['pid_control_measurement'], 21.)
        self.assertEqual(d.r.status['demand_percent'], 0.)

    async def test_zero_and_continuous_demand_do_not_create_modulo_timers(self):
        zero = Driver(measured=21.)
        for at in (0, 120, 2401):
            await zero.at(at)
        self.assertEqual(zero.on, [])
        self.assertFalse(getattr(zero.r, '_pid_pwm_wakeups', {}))
        full = Driver(measured=19.9, kp=100.)
        for at in (0, 2397, 2401, 7199):
            await full.at(at)
        self.assertEqual(full.on, [0])
        self.assertEqual(full.off, [])
        self.assertFalse(full.r._pid_pwm_wakeups)
        await full.at(7200)
        self.assertEqual(full.off, [7200])
        await full.at(7319)
        self.assertEqual(full.on, [0])
        await full.at(7320)
        self.assertEqual(full.on, [0, 7320])

    async def test_fractional_measurement_does_not_erase_exact_minimum_budget(self):
        d = Driver(measured=20.8, kp=100.)
        self.assertAlmostEqual((21. - 20.8) * 100, 20.)
        await d.at(0)
        self.assertEqual(d.on, [0])
        self.assertEqual(d.r._pid_pwm_wakeups[SPEC.identifier][0], d.origin + 120.)
        await d.at(120)
        self.assertEqual(d.off, [120])


class TimerTests(unittest.IsolatedAsyncioTestCase):
    async def test_separate_cancellable_timer_requests_serialized_rerun(self):
        r = Driver().r
        unrelated = N(cancel=lambda: self.fail('PWM timer cannot cancel native retry timer'))
        r._setpoint_wakeups = {SPEC.identifier: unrelated}
        r._schedule_pid_pwm_evaluation(SPEC, r.now + 20)
        first = r._pid_pwm_wakeups[SPEC.identifier][1]
        callback = first._callback
        r._schedule_pid_pwm_evaluation(SPEC, r.now + 30)
        self.assertTrue(first.cancelled())
        callback()
        self.assertEqual(r.scheduled, 0, 'Canceled stale callback cannot reschedule')
        self.assertIs(r._setpoint_wakeups[SPEC.identifier], unrelated)
        second = r._pid_pwm_wakeups[SPEC.identifier][1]
        r._tasks[SPEC.identifier] = N(done=lambda: False)
        second._callback()
        self.assertEqual(r.scheduled, 0)
        self.assertIn(SPEC.identifier, r._setpoint_rerun)
        r._tasks.clear()
        r._schedule_pid_pwm_evaluation(SPEC, r.now + 40)
        third = r._pid_pwm_wakeups[SPEC.identifier][1]
        third._callback()
        self.assertEqual(r.scheduled, 1)
        for deadline in (r.now, r.now - 1, None):
            r._schedule_pid_pwm_evaluation(SPEC, deadline)
            self.assertFalse(r._pid_pwm_wakeups, 'No past-due busy-loop timer')
        second.cancel()
        third.cancel()

    async def test_unload_cancels_pending_boundaries_and_late_callbacks(self):
        r = Driver().r
        r._schedule_pid_pwm_evaluation(SPEC, r.now + 20)
        handle = r._pid_pwm_wakeups[SPEC.identifier][1]
        callback = handle._callback
        await production.async_stop(r)
        self.assertTrue(handle.cancelled())
        self.assertFalse(r._pid_pwm_wakeups)
        callback()
        self.assertEqual(r.scheduled, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Quiet hours use HA local time and the existing guarded native fan adapters.

Transport, qualified sensor inputs and time are controlled by the established
runtime fixture. Tests exercise the production clock evaluator, shared settings
writer, mode resolution, quiet policy and native fan dispatch/acknowledgement.
No physical device or Home Assistant installation is contacted.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, time, timezone
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / '.github/tests/test_061b8_dehumidifier_fan.py'))
FanRuntime, model, production, PACKAGE = (
    fixture[key] for key in ('FanRuntime', 'model', 'production', 'PACKAGE'))
quiet = importlib.import_module(PACKAGE + '.quiet_hours')

# The real capability-gating functions with only HA entity-registry transport
# isolated. This avoids importing another platform fixture into this runtime.
source = ast.parse((ROOT / 'custom_components/environment_manager/equipment_feature_registration.py').read_text())
functions = [node for node in source.body if getattr(node, 'name', '') in (
    'quiet_keys', 'registered_control')]
namespace = dict(equipment=model, DOMAIN='environment_manager')
exec(compile(ast.fix_missing_locations(ast.Module([ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                         *functions], type_ignores=[])), 'equipment_feature_registration.py', 'exec'), namespace)
quiet_keys = namespace['quiet_keys']


def epoch(local, zone='Europe/Berlin', *, fold=0):
    return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zone), fold=fold).timestamp()


def schedule(runtime, *, start='22:00:00', end='08:00:00', enabled=True):
    runtime.hass.config.time_zone = 'Europe/Berlin'
    runtime.manager.entry.options.update(quiet_hours_enabled=enabled,
                                       quiet_hours_start=start, quiet_hours_end=end)
    raw = runtime.raw()
    raw['quiet_hours'] = True
    runtime.manager.entry.options[model.SETTINGS][runtime.spec.identifier] = raw


class ClockTests(unittest.TestCase):
    def check(self, when, expected, *, start='22:00:00', end='08:00:00', zone='Europe/Berlin', fold=0):
        config = dict(quiet_hours_enabled=True, quiet_hours_start=start, quiet_hours_end=end)
        self.assertIs(quiet.active(config, epoch(when, zone, fold=fold), zone), expected)

    def test_overnight_start_included_end_excluded(self):
        for when, expected in (
            ('2026-11-21T21:59:59', False), ('2026-11-21T22:00:00', True),
            ('2026-11-22T00:00:00', True), ('2026-11-22T07:59:59', True),
            ('2026-11-22T08:00:00', False), ('2026-11-22T21:59:59', False),
        ):
            self.check(when, expected)

    def test_daytime_and_second_precision(self):
        for when, expected in (
            ('2026-11-21T09:00:14', False), ('2026-11-21T09:00:15', True),
            ('2026-11-21T16:00:29', True), ('2026-11-21T16:00:30', False),
        ):
            self.check(when, expected, start='09:00:15', end='16:00:30')

    def test_configured_zone_controls_schedule_independent_of_host(self):
        stamp = datetime(2026, 11, 21, 21, 30, tzinfo=timezone.utc).timestamp()
        config = dict(quiet_hours_enabled=True)
        self.assertTrue(quiet.active(config, stamp, 'Europe/Berlin'))
        self.assertFalse(quiet.active(config, stamp, 'UTC'))
        self.assertFalse(quiet.active(config, stamp, 'America/New_York'))

    def test_dst_skipped_and_repeated_hours_follow_wall_clock(self):
        self.check('2026-03-29T01:59:59', False, start='02:15', end='03:30')
        self.check('2026-03-29T03:00:00', True, start='02:15', end='03:30')
        self.check('2026-03-29T03:30:00', False, start='02:15', end='03:30')
        for fold in (0, 1):
            self.check('2026-10-25T02:14:59', False, start='02:15', end='02:45', fold=fold)
            self.check('2026-10-25T02:15:00', True, start='02:15', end='02:45', fold=fold)
            self.check('2026-10-25T02:44:59', True, start='02:15', end='02:45', fold=fold)
            self.check('2026-10-25T02:45:00', False, start='02:15', end='02:45', fold=fold)

    def test_missing_invalid_disabled_and_equal_times_are_inert(self):
        stamp = epoch('2026-11-22T23:00:00')
        for flag in (None, False, 0, 1, 'true', [], {}):
            self.assertFalse(quiet.active({'quiet_hours_enabled': flag}, stamp, 'Europe/Berlin'))
        for value in ('24:00', '9:00', '22:00Z', '22:00+01:00', '22:00:00.1', '', None, True, '22:60:00',
                      '0١:00', '12:0٠', '12:00:0١'):
            self.assertIsNone(quiet.parse_clock(value))
            self.assertFalse(quiet.active(dict(quiet_hours_enabled=True, quiet_hours_start=value), stamp, 'UTC'))
        self.assertEqual(quiet.parse_clock('09:00'), time(9))
        self.assertEqual(quiet.parse_clock('09:00:01'), time(9, 0, 1))
        self.assertFalse(quiet.active(dict(quiet_hours_enabled=True, quiet_hours_start='22:00',
                                          quiet_hours_end='22:00:00'), stamp, 'UTC'))
        for value in (None, True, float('nan'), float('inf'), -1, 'bad'):
            self.assertFalse(quiet.active(dict(quiet_hours_enabled=True), value, 'UTC'))
        self.assertFalse(quiet.active(dict(quiet_hours_enabled=True), stamp, 'missing/timezone'))


class SharedPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_preference_is_strict_opt_in_and_is_not_a_mode_field(self):
        r = FanRuntime()
        self.assertFalse(r.cfg['quiet_hours'])
        self.assertNotIn('quiet_hours', model.MODE_FIELDS)
        for bad in (None, 1, 'true', [], {}):
            raw = r.raw()
            raw['quiet_hours'] = bad
            r.manager.entry.options[model.SETTINGS][r.spec.identifier] = raw
            self.assertFalse(r.cfg['quiet_hours'])
        before = deepcopy(r.record)
        await r.async_update(r.spec, {'quiet_hours': True})
        for mode in model.operating_modes(r.manager, r.spec):
            self.assertTrue(model.settings_for_mode(r.manager, r.spec, mode)['quiet_hours'])
            self.assertNotIn('quiet_hours', model.mode_descriptor(r.manager, r.spec, mode)['switch_fields'])
        self.assertNotIn('quiet_hours', r.raw()['mode_settings']['dry'])
        self.assertEqual(r.record, before)
        self.assertEqual(r.calls, [])
        for changes, scope in (({'quiet_hours': 1}, None), ({'quiet_hours': True, 'kp': 12}, None),
                               ({'quiet_hours': True}, 'dry')):
            with self.assertRaises(ValueError):
                await r.async_update(r.spec, changes, operating_mode=scope)

    async def test_upgrade_keeps_legacy_pid_cycle_but_real_quiet_opt_in_and_out_reset_math(self):
        r = FanRuntime()
        r.own_running(age=700)
        r.seed_math()
        # Simulate a 0.7.5b3 journal, which could never contain this new key.
        r.record['pid_control_intent'].pop('quiet_hours', None)
        checkpoint = deepcopy(r.record['pid_checkpoint'])
        memory = r._memory[r.spec.identifier]
        physical = deepcopy((r.record['power'], r.record['off_at']))
        await r._sync_pid_intent(r.spec, r.cfg)
        self.assertEqual(r.record['pid_checkpoint'], checkpoint)
        self.assertIs(r._memory[r.spec.identifier], memory)
        self.assertNotIn('pid_cycle_reset', r.record)
        self.assertNotIn('quiet_hours', r.record['pid_control_intent'])
        for enabled in (True, False):
            await r.async_update(r.spec, {'quiet_hours': enabled})
            await r._sync_pid_intent(r.spec, r.cfg)
            self.assertNotIn('pid_checkpoint', r.record)
            self.assertNotIn(r.spec.identifier, r._memory)
            self.assertEqual(r.record['pid_cycle_reset']['reason'], 'active_control_changed')
            self.assertEqual((r.record['power'], r.record['off_at']), physical)
            self.assertEqual(r.record['pid_control_intent'].get('quiet_hours', False), enabled)
            if enabled:
                r.seed_math()
        self.assertEqual(r.calls, [])

    async def test_capability_gating_adds_one_shared_flag_and_preserves_known_offline_control(self):
        r = FanRuntime()
        registry = N(async_get_entity_id=lambda *args: None)
        self.assertEqual(quiet_keys(r.manager, registry, r.spec, platform='switch').count('quiet_hours'), 1)
        r.state.attributes.pop('fan_modes')
        r.state.attributes['supported_features'] &= ~model.FAN
        self.assertNotIn('quiet_hours', quiet_keys(r.manager, registry, r.spec, platform='switch'))
        with self.assertRaisesRegex(ValueError, 'adjustable native fan'):
            await r.async_update(r.spec, {'quiet_hours': True})
        registry.async_get_entity_id = lambda platform, domain, key: (
            'switch.custom_quiet_hours' if key.endswith('_quiet_hours') else None)
        self.assertEqual(quiet_keys(r.manager, registry, r.spec, platform='switch'), ('quiet_hours',))
        raw = r.raw()
        raw['quiet_hours'] = True
        r.manager.entry.options[model.SETTINGS][r.spec.identifier] = raw
        await r.async_update(r.spec, {'quiet_hours': False})
        self.assertFalse(r.cfg['quiet_hours'])
        self.assertEqual(r.calls, [])

    async def test_unknown_presets_need_an_advertised_quiet_choice_and_can_be_disabled(self):
        r = FanRuntime(names=('normal', 'sleep'), quiet_fan_mode=None)
        with self.assertRaisesRegex(ValueError, 'advertised quiet fan mode'):
            await r.async_update(r.spec, {'quiet_hours': True})
        raw = r.raw()
        for mode in model.operating_modes(r.manager, r.spec):
            raw['mode_settings'].setdefault(mode, {})['quiet_fan_mode'] = 'sleep'
        r.manager.entry.options[model.SETTINGS][r.spec.identifier] = raw
        await r.async_update(r.spec, {'quiet_hours': True})
        self.assertTrue(r.cfg['quiet_hours'])
        # A manufacturer's later capability change must not trap the opt-out.
        r.state.attributes['fan_modes'] = ['normal', 'new-sleep']
        await r.async_update(r.spec, {'quiet_hours': False})
        self.assertFalse(r.cfg['quiet_hours'])

    async def test_quiet_hours_combine_with_sleep_and_occupancy_without_needing_presence(self):
        r = FanRuntime()
        schedule(r)
        r.now = epoch('2026-11-22T23:00:00')
        r.manager.plan.update(occupancy='unknown', sleeping=None)
        self.assertTrue(r._quiet_context(r.spec, r.cfg, r.manager.plan))
        r.now = epoch('2026-11-23T08:00:00')
        self.assertFalse(r._quiet_context(r.spec, r.cfg, r.manager.plan))
        for key in ('quiet_sleep', 'quiet_occupied'):
            raw = r.raw()
            raw['mode_settings']['dry'].update(quiet_sleep=False, quiet_occupied=False)
            raw['mode_settings']['dry'][key] = True
            r.manager.entry.options[model.SETTINGS][r.spec.identifier] = raw
            r.manager.plan.update(occupancy='occupied', sleeping=True)
            self.assertTrue(r._quiet_context(r.spec, r.cfg, r.manager.plan))
            r.manager.entry.options['quiet_hours_enabled'] = False
            self.assertTrue(r._quiet_context(r.spec, r.cfg, r.manager.plan))


class FanDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_upgrade_keeps_legacy_pending_power_retry_and_budget(self):
        r = FanRuntime()
        await r.evaluate()
        pending = r.record['pending']
        self.assertTrue(pending['power'])
        pending['retry_context']['settings'].pop('quiet_hours', None)
        original = deepcopy(pending)
        await r.evaluate(60)
        self.assertFalse(r.record.get('paused'))
        self.assertIsNotNone(r.record['pending'])
        retried = r.record['pending']
        self.assertEqual(retried['when'], original['when'])
        self.assertEqual(retried['data'], original['data'])
        self.assertEqual(retried['attempts'], original['attempts'] + 1)
        self.assertEqual([call['service'] for call in r.calls], ['set_hvac_mode', 'set_hvac_mode'])

    async def test_clock_tick_changes_and_restores_fan_with_unchanged_sensor_evidence(self):
        for method in ('automatic', 'pid'):
            with self.subTest(method=method):
                r = FanRuntime(method=method)
                schedule(r, start='23:59:50', end='00:00:10')
                r.now = epoch('2026-11-22T23:59:49')
                r.surface_reading(surface_rh=80)
                r.own_running(age=700)
                evidence = deepcopy({key: (state.state, state.last_reported)
                    for key, state in r.states.items() if key.startswith(('sensor.', 'weather.'))})
                physical = deepcopy((r.record['power'], r.record['off_at']))
                await r.evaluate()
                self.assertEqual(r.calls, [])
                memory = deepcopy(r._memory.get(r.spec.identifier))
                await r.evaluate(1)
                self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'Low'})
                r.feedback(fan='Low')
                await r.evaluate()
                await r.evaluate(20)
                self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'High'})
                self.assertEqual((r.record['power'], r.record['off_at']), physical)
                self.assertEqual([call['service'] for call in r.calls], ['set_fan_mode', 'set_fan_mode'])
                self.assertEqual({key: (state.state, state.last_reported)
                    for key, state in r.states.items() if key.startswith(('sensor.', 'weather.'))}, evidence)
                if method == 'pid':
                    self.assertEqual(r._memory[r.spec.identifier], memory)

    async def test_overnight_entry_and_exit_restore_normal_speed_without_touching_power(self):
        for method in ('automatic', 'pid'):
            with self.subTest(method=method):
                r = FanRuntime(method=method)
                schedule(r, start='23:59:50', end='00:00:10')
                r.now = epoch('2026-11-22T23:59:49')
                r.surface_reading(surface_rh=80)
                r.own_running(age=700)
                before = deepcopy((r.record['power'], r.record['off_at']))
                self.assertFalse(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True))
                r.now += 1
                self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True))
                self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'Low'})
                r.feedback(fan='Low')
                await r._reconcile(r.spec)
                r.now = epoch('2026-11-23T00:00:10')
                self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True))
                self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'High'})
                self.assertEqual((r.record['power'], r.record['off_at']), before)
                self.assertEqual([call['service'] for call in r.calls], ['set_fan_mode', 'set_fan_mode'])

    async def test_schedule_start_during_command_persistence_cannot_dispatch_old_high_speed(self):
        r = FanRuntime(method='automatic')
        schedule(r)
        r.now = epoch('2026-11-22T21:59:59')
        r.surface_reading(surface_rh=80)
        r.feedback(fan='Low')
        r.own_running(age=700)
        raw = r.raw()
        raw['mode_settings']['dry']['fan_mode'] = 'High'
        r.manager.entry.options[model.SETTINGS][r.spec.identifier] = raw
        save = r._save
        crossed = False
        async def saving():
            nonlocal crossed
            await save()
            if not crossed and r.record.get('pending'):
                crossed = True
                r.now += 1
        r._save = saving
        await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, None, True)
        self.assertTrue(crossed)
        self.assertTrue(r._quiet_context(r.spec, r.cfg, r.manager.plan))
        self.assertEqual(r.calls, [])

    async def test_opt_out_manual_and_off_device_preserve_existing_native_behavior(self):
        r = FanRuntime(method='automatic')
        schedule(r)
        r.now = epoch('2026-11-22T23:00:00')
        r.own_running(age=700)
        await r.async_update(r.spec, {'quiet_hours': False})
        self.assertFalse(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, None, True))
        await r.async_update(r.spec, {'quiet_hours': True})
        self.assertFalse(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, None, False))
        r.feedback(mode='off')
        self.assertFalse(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, None, True))
        self.assertEqual(r.calls, [])

    async def test_percentage_fan_keeps_quiet_ceiling_native_steps_and_device_minimum(self):
        r = FanRuntime(method='automatic')
        schedule(r)
        r.now = epoch('2026-11-22T23:00:00')
        r.own_running(age=700)
        fan = 'fan.native_speed'
        r.states[fan] = r.observation(fan, 'on', {'percentage': 80, 'supported_features': 1})
        cap = replace(r.cap, fan_entity=fan, fan_percentage=True, fan_modes=('20', '40', '60', '80', '100'))
        calls = []
        async def send(spec, native_cap, entity, service, data, expected, *, automatic):
            calls.append((entity, service, data))
            return True
        r._send = send  # Transport only: allocation and current quiet policy run unchanged.
        self.assertTrue(await r._fan(r.spec, cap, {**r.cfg, 'quiet_percentage': 30}, r.manager.plan, None, True))
        self.assertEqual(calls[-1], (fan, 'set_percentage', {'percentage': 20}))
        self.assertTrue(await r._fan(r.spec, cap, {**r.cfg, 'quiet_percentage': 1}, r.manager.plan, None, True))
        self.assertEqual(calls[-1], (fan, 'set_percentage', {'percentage': 20}))


if __name__ == '__main__':
    unittest.main()

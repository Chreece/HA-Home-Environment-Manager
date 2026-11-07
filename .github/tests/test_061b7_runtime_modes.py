"""Operating profiles and logical reset through actual native control paths.

Uses production model, scoped settings writer, tick, mode/target requests,
PID/retry/recovery, native ownership and dwell gates. Only HA transport,
qualified room inputs, scheduler and time are isolated; no device is operated.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import logging
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
f = runpy.run_path(str(ROOT / '.github/tests/test_061b1_operating_timing.py'))
model, production, base = f['model'], f['production'], f['base']
SPEC, PRIMARY, PACKAGE = f['SPEC'], f['PRIMARY'], f['PACKAGE']
METHODS = (
    'active_control_mode', '_refresh_operating_mode', '_reset_pid_cycle', '_sync_pid_intent',
    '_cancel_pid_pwm_evaluation', '_schedule_pid_pwm_evaluation', '_sampled_pid_pwm',
    '_resume_pid_checkpoint', '_checkpoint_pid', '_status', '_pause', '_identity_ok', '_current_spec',
    '_legacy_busy', 'async_request_mode', 'async_set_targets', 'async_set_fan',
    'async_resume', '_automatic_recovery_gate', '_schedule_automatic_reconciliation',
    '_apply_automatic_reconciliation', '_retry_after_verified_reconnect', '_observed_off_since',
    'observe_native_availability', '_native_settle_remaining', 'async_continue_automatic', 'resume_information',
    'async_apply_pid_calibration',
)
production.configured_sources = model.configured_sources
production._LOGGER = logging.getLogger(__name__)
production.tune_pid = importlib.import_module(PACKAGE + '.pid_calibration').tune
allocator = importlib.import_module(PACKAGE + '.pid_output_allocator')
for name in ('fan_speed_for_pid', 'ordered_fan_stages', 'percentage_output_requested'):
    setattr(production, name, getattr(allocator, name))
base['extract'](ROOT / 'equipment_runtime.py', (*METHODS, 'async_start'), production.__dict__)
restart = importlib.import_module(PACKAGE + '.pid_restart')
activation = importlib.import_module(PACKAGE + '.device_activation')


class Runtime(f['TimingRuntime']):
    def __init__(self, *, profile=None, **kwargs):
        super().__init__(profile=profile, **kwargs)
        self.registry_rows = {PRIMARY: N(entity_id=PRIMARY, id='native-registry', unique_id='native-unique',
            device_id=SPEC.source_device_id, platform='native', area_id=SPEC.area_id)}
        self.hass.registry = N(async_get=self.registry_rows.get, entities=self.registry_rows)
        sys.modules['homeassistant.helpers.entity_registry'].async_get = lambda hass: hass.registry
        self.hass.config = N(language='en', units=N(temperature_unit='°C'))
        self._presentation_updates = N(request=lambda key: None)
        self._tasks, self._pid_passive_tasks = {}, {}
        self._native_ready_since = {PRIMARY: self.now - 30}
        self._native_settled_for = {(SPEC.identifier, PRIMARY): self.now - 30}
        self._native_reconnect_epoch, self._native_on_epoch = {}, {}
        self.statuses, self.status_history = {}, []
        self.queued_tasks = []
        self.hass.async_create_task = self.create_task
        self.state.attributes.update(hvac_modes=['off', 'heat', 'cool', 'dry', 'fan_only', 'auto', 'heat_cool'])
        self.readings = {'temperature': 18.6, 'humidity': 55.8, 'co2': 500., 'pm25': 40.}
        raw = model.raw_settings(self.manager, SPEC)
        raw['_native_authorization'] = activation.authority_context(self.manager, SPEC)
        self.manager.entry.options[model.SETTINGS] = {SPEC.identifier: raw}

    def create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.queued_tasks.append(task)
        return task

    def schedule(self):
        pass  # Tests advance evaluations explicitly; controller logic is unchanged.

    def measurements(self, spec, cap):
        return dict(self.readings)

    async def evaluate(self, advance=0):
        self.now += advance
        await self.tick(SPEC)
        while self.queued_tasks:
            tasks, self.queued_tasks = self.queued_tasks, []
            await asyncio.gather(*tasks)

    async def restart(self):
        saved = deepcopy(self.records)

        class Store:
            def __init__(self, *args, **kwargs):
                pass

            async def async_load(self):
                return {'version': 1, 'records': deepcopy(saved)}

        storage = ModuleType('homeassistant.helpers.storage')
        storage.Store = Store
        with patch.dict(sys.modules, {storage.__name__: storage}):
            await production.async_start(self)
        # Production startup replaces the loaded record dictionary. Keep
        # this fixture's convenience alias bound to that restored record.
        self.record = self.records[SPEC.identifier]

    @property
    def status(self):
        return self.statuses.get(SPEC.identifier, {})

    def raw(self):
        return model.raw_settings(self.manager, SPEC)

    def seed_math(self):
        cfg = self.cfg
        mode = cfg.get('requested_mode') or 'heat'
        signature = ('temperature', 21., True, 'home', mode, 'none', cfg['kp'], cfg['ki'], cfg['kd'],
                     cfg['cycle_seconds'], 600., 600.)
        memory = model.PIDMemory(35., 18.6, self.now - 120, 1., 70.)
        self._memory[SPEC.identifier] = (signature, memory, self.now - 1400)
        self._profile_wake[SPEC.identifier] = {'mode': mode, 'profile': 'home', 'until': self.now + 5000}
        self._fan_allocations[SPEC.identifier] = {'old': True}
        self._pid_offline_previews[SPEC.identifier] = {'old': True}
        self.record['pid_checkpoint'] = restart.checkpoint(signature, memory, self.now - 1400,
            SPEC.source_entities, SPEC.source_device_id, cfg['sample_seconds'], self.now)
        self.record['pid_control_intent'] = restart.control_intent(cfg)


for method in METHODS:
    setattr(Runtime, method, getattr(production, method))


def scoped(**overrides):
    return {'mode_settings_version': 1, 'mode_settings': {
        'heat': {'control_mode': 'pid', 'kp': 12, 'ki': 0.2},
        'cool': {'control_mode': 'automatic', 'kp': 25, 'ki': 0.4},
        'dry': {'control_mode': 'pid', 'kp': 8, 'ki': 0.08},
        'fan_only': {'control_mode': 'pid', 'kp': 3, 'ki': 0.02},
        **overrides,
    }}


class RuntimeModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_inactive_parameters_do_not_reset_active_math_or_pending_command(self):
        r = Runtime(profile=scoped())
        r.own_running(age=700)
        await r.evaluate()
        self.assertEqual(r.record['pending']['service'], 'set_temperature')
        r.seed_math()
        physical = deepcopy(r.record)
        memory, wake = r._memory[SPEC.identifier], deepcopy(r._profile_wake)
        async with r._lock(SPEC.identifier):
            await asyncio.wait_for(r.async_update(SPEC, {'control_mode': 'pid', 'kp': 33,
                'profile_targets': {'home': {'cool': 28}, 'sleep': {'cool': 29}}}, operating_mode='cool'), .5)
        self.assertEqual(r.cfg['kp'], 12)
        self.assertEqual(model.settings_for_mode(r.manager, SPEC, 'cool')['kp'], 33)
        self.assertEqual(r.record, physical)
        self.assertIs(r._memory[SPEC.identifier], memory)
        self.assertEqual(r._profile_wake, wake)
        self.assertEqual(r.raw()['requested_mode'], 'heat')
        await r.evaluate(60)
        self.assertEqual(r.record['pending']['attempts'], 2)
        self.assertFalse(r.record.get('paused'))

    async def test_first_inactive_opt_in_preserves_legacy_active_retry_and_phase(self):
        r = Runtime(profile={'kp': 12})
        r.own_running(age=700)
        await r.evaluate()
        original = deepcopy(r.record['pending'])
        r.seed_math()
        anchor = r._memory[SPEC.identifier][2]
        await r.async_update(SPEC, {'kp': 33}, operating_mode='cool')
        self.assertEqual(r.record['pending'], original)
        await r.evaluate(60)
        self.assertFalse(r.record.get('paused'), r.status)
        self.assertEqual(r.record['pending']['attempts'], 2)
        self.assertEqual(r.record['pending']['when'], original['when'])
        self.assertEqual(r.record['pending']['retry_context']['settings']['operating_mode'], 'heat')
        self.assertEqual(r._memory[SPEC.identifier][2], anchor)

    async def test_facade_switch_consumes_requested_mode_method_and_targets(self):
        r = Runtime(profile=scoped())
        before = deepcopy(r.raw()['mode_settings']['heat'])
        await r.async_request_mode(SPEC, 'cool')
        self.assertEqual((r.cfg['operating_mode'], r.cfg['control_mode'], r.cfg['kp']), ('cool', 'automatic', 25))
        self.assertEqual(r.raw()['mode_settings']['heat'], before)
        room = deepcopy(r.manager.settings['climate_rooms'])
        await r.async_set_targets(SPEC, {'cool': 28}, mode='cool')
        self.assertEqual(r.cfg['control_mode'], 'automatic')
        self.assertEqual(r.cfg['profile_targets']['comfort'], {'cool': 28})
        self.assertEqual(r.manager.settings['climate_rooms'], room)
        self.assertEqual(r.raw()['mode_settings']['heat'], before)
        self.assertEqual(r.calls, [])
        r.readings['temperature'] = 30
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'cool'})

    async def test_mode_switch_verifies_old_target_then_observes_real_off_dwell(self):
        r = Runtime(profile=scoped())
        r.own_running(age=700)
        await r.evaluate()
        old = deepcopy(r.record['pending'])
        r.readings['temperature'] = 30
        await r.async_request_mode(SPEC, 'cool')
        self.assertEqual(r.record['pending'], old)
        await r.evaluate(120)
        self.assertEqual(len(r.calls), 1, 'Changing modes does not replay old Heat')
        await r.evaluate(60)
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'off'})
        self.assertFalse(any(c['data'].get('hvac_mode') == 'cool' for c in r.calls))
        r.report(mode='off')
        await r.evaluate()
        off_at = r.record['off_at'][PRIMARY]
        await r.evaluate(599)
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'off'})
        self.assertEqual(r.record['off_at'][PRIMARY], off_at)
        await r.evaluate(1)
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'cool'})
        self.assertEqual(r.record['pending']['retry_context']['settings']['control_mode'], 'automatic')

    async def test_physical_manual_change_pauses_only_active_method_and_resume_restores_it(self):
        r = Runtime(profile=scoped())
        await r.evaluate()
        r.report(mode='heat')
        await r.evaluate()
        self.assertIn(PRIMARY, r.record['native_control_confirmed'])
        other = deepcopy(r.raw()['mode_settings']['cool'])
        r.seed_math()
        r.now += 1
        r.report(temperature=19)
        r.state.last_updated = datetime.fromtimestamp(r.now, timezone.utc)
        r.state.context = N(user_id='actual-user', parent_id=None, id='new-native-button')
        await r.evaluate()
        self.assertEqual(r.record.get('paused'), 'physical_manual_override')
        self.assertEqual(r.raw()['mode_settings']['heat']['control_mode'], 'manual')
        self.assertEqual(r.raw()['mode_settings']['cool'], other)
        self.assertEqual(r.record['resume_operating_mode'], 'heat')
        self.assertFalse(r._memory)
        # Two stable user checks reconcile the old uncertain setpoint without
        # dispatch; the pending intent is never erased by the settings editor.
        calls = deepcopy(r.calls)
        r.now += 120
        with self.assertRaises(ValueError):
            await r.async_resume(SPEC)
        r.now += 60
        await r.async_resume(SPEC)
        self.assertEqual(r.calls, calls)
        self.assertEqual(r.raw()['mode_settings']['heat']['control_mode'], 'pid')
        self.assertEqual(r.raw()['mode_settings']['cool'], other)
        self.assertFalse(r.record.get('paused'))

    async def test_overlapping_inferred_targets_do_not_alternate_directions(self):
        profile = {**scoped(
            heat={'control_mode': 'pid', 'profile_targets': {'comfort': {'heat': 28}}},
            cool={'control_mode': 'automatic', 'profile_targets': {'comfort': {'cool': 24}}}),
            'requested_mode': None}
        r = Runtime(profile=profile)
        r.readings['temperature'] = 26
        await r.evaluate()
        self.assertEqual(r.calls, [])
        self.assertEqual(r.status.get('reason'), 'conflicting_heating_cooling_targets')
        await r.async_request_mode(SPEC, 'heat')
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'heat'})
        r.report(mode='heat')
        await r.evaluate()
        # Removing an explicit pin retains that directional profile while
        # the independent bands overlap, including on either side of them.
        await r.async_update(SPEC, {'requested_mode': None})
        for temperature in (29, 27, 23, 30):
            r.readings['temperature'] = temperature
            await r._refresh_operating_mode(SPEC)
            self.assertEqual(r.cfg['operating_mode'], 'heat')
        self.assertFalse(any(c['data'].get('hvac_mode') == 'cool' for c in r.calls))

    async def test_unselected_manual_profiles_cannot_fall_back_to_flat_pid(self):
        r = Runtime(profile={'requested_mode': None, 'control_mode': 'pid',
            'mode_settings_version': 1, 'mode_settings': {
                mode: {'control_mode': 'manual'}
                for mode in ('heat', 'cool', 'dry', 'fan_only', 'auto', 'heat_cool')
            }})
        await r.evaluate()
        self.assertEqual(r.calls, [])
        self.assertEqual(r.status.get('reason'), 'operating_mode_selection_required')
        await r.async_request_mode(SPEC, 'cool')
        self.assertEqual(r.cfg['control_mode'], 'manual')
        self.assertEqual(r.raw()['mode_settings']['heat']['control_mode'], 'manual')

    async def test_scoped_native_auto_inference_does_not_use_legacy_pid_method(self):
        for selected in ('auto', 'heat_cool'):
            for disabled in ('manual', 'off'):
                with self.subTest(selected=selected, disabled=disabled):
                    r = Runtime(profile={
                        'requested_mode': None, 'control_mode': 'pid',
                        'mode_settings_version': 1,
                        'mode_settings': {mode: {
                            'control_mode': 'automatic' if mode == selected else disabled,
                        } for mode in ('heat', 'cool', 'dry', 'fan_only', 'auto', 'heat_cool')},
                    })
                    await r.evaluate()
                    self.assertEqual(r.cfg['operating_mode'], selected)
                    self.assertEqual(r.cfg['control_mode'], 'automatic')
                    self.assertEqual(r.calls[-1]['data'], {'hvac_mode': selected})
                    self.assertFalse(any(call['data'].get('hvac_mode') in ('heat', 'cool', 'dry')
                                         for call in r.calls))

    async def test_missing_direction_feedback_cannot_fall_back_to_disabled_drying(self):
        r = Runtime(profile={
            'requested_mode': None, 'control_mode': 'pid',
            'mode_settings_version': 1,
            'mode_settings': {mode: {
                'control_mode': 'pid' if mode == 'heat' else 'manual',
            } for mode in ('heat', 'cool', 'dry', 'fan_only', 'auto', 'heat_cool')},
        })
        r.readings.update(temperature=None, humidity=90)
        await r.evaluate()
        self.assertEqual(r.calls, [])
        self.assertEqual(r.status.get('reason'), 'operating_mode_selection_required')
        r.readings['temperature'] = 18.6
        await r.evaluate(30)
        self.assertEqual(r.cfg['operating_mode'], 'heat')
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'heat'})

    async def test_inferred_native_range_preserves_owned_shutdown_and_off_dwell(self):
        r = Runtime(profile={
            'requested_mode': 'heat', 'control_mode': 'pid',
            'mode_settings_version': 1,
            'mode_settings': {mode: {
                'control_mode': 'automatic' if mode == 'heat_cool' else 'manual',
            } for mode in ('heat', 'cool', 'dry', 'fan_only', 'auto', 'heat_cool')},
        })
        r.own_running(age=100)
        ownership = deepcopy(r.record['power'])
        await r.async_update(SPEC, {'requested_mode': None})
        await r.evaluate()
        self.assertEqual(r.cfg['operating_mode'], 'heat_cool')
        self.assertEqual(r.status['status'], 'minimum_on_hold')
        self.assertEqual(r.calls, [])
        self.assertEqual(r.record['power'], ownership)
        await r.evaluate(500)
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'off'})
        self.assertEqual(r.record['power'], ownership, 'OFF submission is not a physical ACK')
        pending = deepcopy(r.record['pending'])
        await r.evaluate(1)
        self.assertEqual(r.record['pending'], pending)
        r.report(mode='off')
        await r.evaluate()
        off_at = r.record['off_at'][PRIMARY]
        self.assertFalse(r.record['power'])
        await r.evaluate(599)
        self.assertEqual(len(r.calls), 1)
        self.assertEqual(r.record['off_at'][PRIMARY], off_at)
        await r.evaluate(1)
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'heat_cool'})

    async def test_scoped_automatic_restart_reconciles_without_flat_opt_in(self):
        for legacy, selected in (('existing', 'pid'), ('manual', 'automatic')):
            for phase in ('intent', 'retry_intent'):
                with self.subTest(legacy=legacy, selected=selected, phase=phase):
                    r = Runtime(profile={**scoped(heat={'control_mode': selected}),
                                         'control_mode': legacy})
                    await r.evaluate()
                    r.record['pending']['phase'] = phase
                    pending = deepcopy(r.record['pending'])
                    calls = deepcopy(r.calls)
                    await r.restart()
                    self.assertEqual(r.record['pending'], pending)
                    self.assertEqual(r.record['paused'], 'restart_reconciliation_required')
                    self.assertEqual(r.cfg['control_mode'], selected)
                    await r.evaluate(30)
                    self.assertEqual(r.record['pending'], pending)
                    await r.evaluate(120)
                    self.assertEqual(r.record['pending'], pending)
                    await r.evaluate(60)
                    self.assertFalse(r.record.get('paused'))
                    self.assertFalse(r.record.get('pending'))
                    self.assertFalse(r.record.get('automatic_continue_requested'))
                    self.assertEqual(r.calls, calls, 'Restart reconciliation sends no native command')
                    self.assertFalse(r.record['power'], 'An unconfirmed intent never grants ON ownership')
                    self.assertEqual(r.cfg['control_mode'], selected)

    async def test_scoped_manual_restart_is_not_rearmed_by_flat_pid(self):
        for selected in ('manual', 'off'):
            with self.subTest(selected=selected):
                r = Runtime(profile=scoped())
                await r.evaluate()
                r.record['pending']['phase'] = 'intent'
                await r.async_update(SPEC, {'control_mode': selected}, operating_mode='heat')
                pending, calls = deepcopy(r.record['pending']), deepcopy(r.calls)
                await r.restart()
                for interval in (30, 120, 60):
                    await r.evaluate(interval)
                self.assertEqual(r.cfg['control_mode'], selected)
                self.assertEqual(r.record['pending'], pending)
                self.assertFalse(r.record.get('automatic_continue_requested'))
                self.assertEqual(r.calls, calls)

    async def test_humidity_extremum_requires_reported_range_and_matching_on_direction(self):
        for attributes in ({}, {'min_humidity': 20}, {'min_humidity': 70, 'max_humidity': 30},
                           {'min_humidity': float('nan'), 'max_humidity': 80}):
            with self.subTest(attributes=attributes):
                r = Runtime(profile={**scoped(), 'requested_mode': 'dry'})
                r.state.attributes.update(supported_features=model.HUMIDITY, humidity=60, **attributes)
                r.own_running(age=700)
                result = await r._native_target(SPEC, r.cap, 'dry', {'humidity': 50}, None, True)
                self.assertIsNone(result)
                self.assertEqual(r.calls, [])
                self.assertEqual(r.status['status'], 'physical_capabilities_unavailable')
        r = Runtime(profile={**scoped(), 'requested_mode': 'dry'})
        r.state.attributes.update(supported_features=model.HUMIDITY, humidity=60,
                                  min_humidity=20, max_humidity=80)
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'dry'})
        self.assertFalse(await r._native_target(SPEC, r.cap, 'dry', {'humidity': 50}, None, True))
        self.assertEqual(len(r.calls), 1, 'Mode service success never permits an RH write before ON ACK')
        r.report(mode='heat')
        self.assertFalse(await r._native_target(SPEC, r.cap, 'dry', {'humidity': 50}, None, True))
        self.assertEqual(len(r.calls), 1, 'Another reported ON direction does not authorize a drying target')

    async def test_explicit_off_preserves_methods_and_handles_unowned_running_output(self):
        for owned in (False, True):
            with self.subTest(owned=owned):
                r = Runtime(profile=scoped())
                if owned:
                    r.own_running(age=700)
                else:
                    r.report(mode='heat')
                    r.state.last_changed = datetime.fromtimestamp(r.now - 700, timezone.utc)
                saved = deepcopy(r.raw()['mode_settings'])
                await r.async_request_mode(SPEC, 'off')
                await r.evaluate()
                self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'off'})
                self.assertEqual(r.raw()['mode_settings'], saved)
                self.assertEqual(r.cfg['control_mode'], 'pid')
                self.assertEqual(bool(r.record['power']), owned, 'OFF dispatch does not acquire ON ownership')

    async def test_resume_and_real_policy_hold_remove_checkpoint_without_resetting_dwell(self):
        r = Runtime(profile=scoped())
        r.own_running(age=100)
        r.seed_math()
        physical = deepcopy(r.record['power'])
        await r.async_resume(SPEC)
        self.assertNotIn('pid_checkpoint', r.record)
        self.assertEqual(r.record['power'], physical)
        self.assertFalse(r._memory)
        self.assertIsNone(r._resume_pid_checkpoint(SPEC, r.record, r.cfg, 18.6, 21, True))
        r.seed_math()
        r.window.update(blocked=True, stop_requested=False, status='window_open')
        await r.evaluate()
        self.assertFalse(r._memory)
        self.assertFalse(r._profile_wake)
        self.assertNotIn('pid_checkpoint', r.record)
        self.assertEqual(r.record['power'], physical)
        saves = len(r.persisted)
        await r.evaluate(30)
        self.assertEqual(len(r.persisted), saves, 'An unchanged hold is not another reset/write')

    async def test_unavailable_feedback_resets_math_but_minimum_off_wait_does_not(self):
        r = Runtime(profile=scoped())
        r.seed_math()
        r.report(mode='unavailable')
        await r.evaluate()
        self.assertNotIn('pid_checkpoint', r.record)
        self.assertFalse(r._memory)
        self.assertEqual(r.status['status'], 'waiting_for_physical_device')
        r = Runtime(profile={**scoped(), 'kp': 100}, off_age=1)
        await r.evaluate()
        anchor = r._memory[SPEC.identifier][2]
        physical_off = deepcopy(r.record['off_at'])
        await r.evaluate(30)
        self.assertEqual(r._memory[SPEC.identifier][2], anchor)
        self.assertEqual(r.record['off_at'], physical_off)
        self.assertEqual(r.calls, [])
        self.assertEqual(r.status['status'], 'minimum_off_hold')

    async def test_source_change_resets_old_integral_but_same_value_save_keeps_phase(self):
        r = Runtime(profile=scoped(), off_age=1)
        r.readings.update(temperature_selected_entities=['sensor.old_room'],
                          temperature_source='room_selected_mean')
        await r.evaluate()
        r.seed_math()
        previous, memory, anchor = r._memory[SPEC.identifier]
        await r.async_update(SPEC, {'kp': 12}, operating_mode='heat')
        self.assertEqual(r._memory[SPEC.identifier], (previous, memory, anchor))
        self.assertIn('pid_checkpoint', r.record)
        off_at = deepcopy(r.record['off_at'])
        r.readings['temperature_selected_entities'] = ['sensor.new_room']
        await r.evaluate(30)
        current = r._memory[SPEC.identifier]
        self.assertNotEqual(current[2], anchor)
        self.assertEqual(current[1].integral, 0)
        self.assertEqual(r.record['pid_feedback_identity']['selected_entities'], ['sensor.new_room'])
        self.assertEqual(r.record['off_at'], off_at)
        self.assertEqual(r.calls, [])

    async def test_verified_old_target_cannot_trap_changed_active_parameters(self):
        r = Runtime(profile=scoped())
        r.own_running(age=700)
        await r.evaluate()
        for _ in range(3):
            await r.evaluate(60)
        self.assertIsNone(r.record['pending'])
        old = deepcopy(r.record['native_target_attempt_budget'])
        self.assertEqual(old['attempts'], 3)
        self.assertEqual(old['state'], 'unconfirmed')
        owned = deepcopy(r.record['power'])
        await r.async_update(SPEC, {'kp': 40}, operating_mode='heat')
        self.assertEqual(r.record['native_target_attempt_budget'], old)
        await r.evaluate(120)
        await r.evaluate(60)
        await r.evaluate()
        # A changed PID gain takes effect without reopening an exhausted
        # best-effort native target episode for the same physical endpoint.
        self.assertEqual(model.settings(r.manager, SPEC)['kp'], 40)
        self.assertAlmostEqual(r.status['demand_percent'], 96.)
        self.assertEqual(r.status['status'], 'controlling')
        self.assertIsNone(r.record['pending'])
        self.assertEqual(r.record['native_target_attempt_budget'], old)
        self.assertEqual(len(r.calls), 3)
        self.assertEqual(r.record['power'], owned)
        self.assertFalse(r.record.get('paused'))

    async def test_fan_only_pid_uses_air_quality_on_a_multimode_climate(self):
        r = Runtime(profile={**scoped(), 'requested_mode': 'fan_only'},
                    device={'fan_purpose': 'filtration', 'sensor_verified': True})
        r.state.attributes.update(supported_features=model.TEMP | model.FAN,
                                  fan_modes=['low', 'medium', 'high'], fan_mode='low')
        r.manager.plan.update(air_evidence_at=r.now, air_actions={'thresholds': {'pm25_short_term_action_ug_m3': 10}})
        r.readings.update(temperature=5, humidity=99, pm25=40)
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'], {'hvac_mode': 'fan_only'})
        r.report(mode='fan_only')
        await r.evaluate()
        self.assertEqual(r.calls[-1]['service'], 'set_fan_mode')
        self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'high'})
        self.assertFalse(any(c['service'] in ('set_temperature', 'set_humidity') for c in r.calls))
        self.assertEqual(r._memory[SPEC.identifier][0][0], 'pm25')

    async def test_offline_scoped_edit_needs_exact_cached_physical_identity(self):
        r = Runtime(profile=scoped())
        await r.evaluate()
        r.report(mode='unavailable')
        await r.async_update(SPEC, {'kp': 31}, operating_mode='cool')
        self.assertEqual(model.settings_for_mode(r.manager, SPEC, 'cool')['kp'], 31)
        r.registry_rows[PRIMARY].unique_id = 'replacement'
        with self.assertRaises(ValueError):
            await r.async_update(SPEC, {'kp': 32}, operating_mode='cool')
        self.assertEqual(r.raw()['mode_settings']['cool']['kp'], 31)

    async def test_calibration_consumes_and_saves_only_requested_mode_model(self):
        r = Runtime(profile=scoped())
        saved_heat = deepcopy(r.raw()['mode_settings']['heat'])
        await r.async_update(SPEC, {
            'pid_calibration_method': 'imc_lambda', 'pid_process_gain': 10,
            'pid_time_constant_minutes': 30, 'pid_dead_time_minutes': 5,
            'pid_lambda_minutes': 15,
        }, operating_mode='dry')
        await r.async_apply_pid_calibration(SPEC, operating_mode='dry')
        dry = r.raw()['mode_settings']['dry']
        self.assertEqual((dry['kp'], dry['ki'], dry['kd']), (15, .5, 0))
        self.assertEqual(dry['pid_last_calibration']['operating_mode'], 'dry')
        self.assertEqual(r.raw()['mode_settings']['heat'], saved_heat)
        self.assertEqual(r.cfg['operating_mode'], 'heat')
        self.assertEqual(r.calls, [])
        r.own_running(age=700)
        with self.assertRaises(ValueError):
            await r.async_apply_pid_calibration(SPEC, operating_mode='dry')

    async def test_withdrawn_explicit_mode_does_not_infer_another_direction(self):
        r = Runtime(profile={**scoped(), 'requested_mode': 'cool'})
        r.state.attributes['hvac_modes'] = ['off', 'heat', 'dry']
        await r.evaluate()
        self.assertEqual(r.calls, [])
        self.assertEqual(r.status['status'], 'native_power_mode_unsupported')


if __name__ == '__main__':
    unittest.main(verbosity=2)

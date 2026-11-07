"""Truthful readiness and low-duty evidence through actual controller paths.

Production startup, runtime, source selection, PID/PWM, command journals,
acknowledgements and status serialization run with isolated HA transport/time.
Synthetic gains produce 4.9% for 21°C/20.6°C; they are not a live-device claim.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import runpy
from types import MethodType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / '.github/tests/test_061b7_pwm_sampling.py'))
Driver, SPEC, PRIMARY, production, model = (
    fixture[key] for key in ('Driver', 'SPEC', 'PRIMARY', 'production', 'model'))
base = fixture['f']
base['base']['extract'](ROOT / 'equipment_runtime.py', ('_startup_readiness',),
                       production.__dict__, constants=(
                           'HA_READY_COOLDOWN_SECONDS', 'NATIVE_STARTUP_STABLE_SECONDS'))
status_scope = {'equipment': model, '__package__': base['PACKAGE']}
base['base']['extract'](ROOT / 'equipment_status.py', ('extra_state_attributes',), status_scope)
status_attributes = status_scope['extra_state_attributes'].fget


def live_startup(r):
    r._startup_readiness = MethodType(production._startup_readiness, r)
    r._ha_running_since = None
    r._startup_source_observed, r._startup_source_since = {}, {}
    r._startup_source_done = set()
    r._native_ready_since, r._native_settled_for = {}, {}
    r._started = r.now
    r.hass.state = N(value='RUNNING')


def attributes(r, spec=SPEC):
    return status_attributes(N(_manager=r.manager, _spec=spec, controller_settings=r.cfg))


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_off_climate_is_available_while_startup_checks_count_down(self):
        d = Driver(measured=20.6, kp=12.25)
        r = d.r
        live_startup(r)
        r.state.attributes.update(current_temperature=19.7, hvac_action='unknown')
        diagnostic = N(state='unknown', attributes={}, domain='sensor')
        native_get = r.hass.states.get
        r.hass.states.get = lambda entity: diagnostic if entity == 'sensor.native_hvac_action' else native_get(entity)
        # Even a legacy selection containing a diagnostic sensor cannot add
        # it to the source-bound actuator inventory or availability gate.
        r.manager.entry.data['climate_rooms'][SPEC.area_id]['selected_devices'].append('sensor.native_hvac_action')
        d.settings = deepcopy(r.manager.settings)
        self.assertNotIn('sensor.native_hvac_action', model.configured_sources(r.manager.settings, SPEC.area_id))
        expected = (
            (0, 'startup_warmup', 'home_assistant_ready_cooldown', 60),
            (59, 'startup_warmup', 'home_assistant_ready_cooldown', 1),
            (60, 'native_device_stabilizing', 'native_startup_stabilizing', 60),
            (119, 'native_device_stabilizing', 'native_startup_stabilizing', 1),
            (120, 'native_device_stabilizing', 'native_restore_settling', 30),
            (149, 'native_device_stabilizing', 'native_restore_settling', 1),
            (150, 'startup_warmup', 'startup_warmup', 150),
            (299, 'startup_warmup', 'startup_warmup', 1),
        )
        for at, code, reason, seconds in expected:
            await d.at(at)
            self.assertEqual((r.status['status'], r.status['reason']), (code, reason))
            info = attributes(r)
            self.assertEqual(info['readiness_remaining_seconds'], seconds)
            self.assertEqual(info['readiness_until'], d.origin + at + seconds)
            self.assertEqual(info['unavailable_source_entity_ids'], [])
            self.assertTrue(info['native_sources_available'])
            self.assertEqual(info['native_primary_state'], 'off')
            self.assertEqual(d.on, [])
        await d.at(300)
        self.assertEqual(d.on, [300], 'Unserved 4.9% demand starts after existing guards finish')
        self.assertAlmostEqual(r._memory[SPEC.identifier][1].demand, 4.9)

    async def test_passive_hvac_action_and_temperature_reports_do_not_restart_stability(self):
        d = Driver()
        r = d.r
        live_startup(r)
        await d.at(0)
        await d.at(60)
        for at in (80, 100, 119):
            r.state.attributes['current_temperature'] = 19.7 + at / 1000
            r.state.attributes['hvac_action'] = 'unknown' if at == 100 else 'idle'
            await d.at(at)
            self.assertEqual(r.status['readiness_until'], d.origin + 120)
        await d.at(120)
        self.assertIn((SPEC.identifier, PRIMARY), r._startup_source_done)
        self.assertEqual(r.status['reason'], 'native_restore_settling')

    async def test_true_missing_source_names_the_endpoint_without_inventing_a_deadline(self):
        for state in ('unavailable', 'unknown', None):
            with self.subTest(state=state):
                d = Driver()
                r = d.r
                r.record['capabilities'] = asdict(r.cap)
                live_startup(r)
                await d.at(0)
                if state is None:
                    r.hass.states.get = lambda entity: None
                else:
                    r.state.state = state
                await d.at(60)
                self.assertEqual(r.status['status'], 'waiting_for_physical_device')
                info = attributes(r)
                self.assertEqual(info['status_reason_code'], 'native_source_unavailable')
                self.assertEqual(info['readiness_source_entity_ids'], [PRIMARY])
                self.assertEqual(info['unavailable_source_entity_ids'], [PRIMARY])
                self.assertIsNone(info['readiness_until'])
                self.assertIsNone(info['readiness_remaining_seconds'])
                self.assertFalse(info['native_sources_available'])
                self.assertEqual(d.on, [])

    async def test_known_primary_does_not_hide_a_missing_selected_accessory(self):
        d = Driver()
        r = d.r
        live_startup(r)
        auxiliary = 'fan.native_accessory'
        spec = N(**{**vars(SPEC), 'source_entities': (PRIMARY, auxiliary)})
        r.manager.entry.data['climate_rooms'][SPEC.area_id]['selected_devices'].append(auxiliary)
        r.record['sources'] = list(spec.source_entities)
        native_get = r.hass.states.get
        fan = N(state='unavailable', attributes={}, domain='fan')
        r.hass.states.get = lambda entity: fan if entity == auxiliary else native_get(entity)
        await r.tick(spec)
        r.now += 60
        await r.tick(spec)
        self.assertEqual(r.status['status'], 'waiting_for_physical_device')
        info = attributes(r, spec)
        self.assertEqual(info['native_primary_entity_id'], PRIMARY)
        self.assertEqual(info['native_primary_state'], 'off')
        self.assertEqual(info['readiness_source_entity_ids'], [auxiliary])
        self.assertEqual(info['unavailable_source_entity_ids'], [auxiliary])
        self.assertEqual(r.calls, [])

    async def test_ha_still_starting_does_not_claim_native_connection_loss(self):
        d = Driver()
        r = d.r
        live_startup(r)
        r.hass.state = N(value='STARTING')
        await d.at(0)
        self.assertEqual(r.status['status'], 'startup_warmup')
        self.assertEqual(r.status['reason'], 'home_assistant_still_starting')
        self.assertIsNone(attributes(r)['readiness_until'])
        self.assertTrue(attributes(r)['native_sources_available'])
        self.assertEqual(d.on, [])


class LowDutyEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_4_9_percent_pulse_has_visible_bounded_rest_and_deadline(self):
        d = Driver(measured=20.6, kp=12.25)
        r = d.r
        r.state.attributes['current_temperature'] = 19.7
        await d.at(0)
        await d.at(147)
        self.assertEqual(d.on, [0])
        self.assertEqual(d.off, [147])
        await d.at(700)
        info = attributes(r)
        self.assertEqual(info['status_code'], 'pid_output_inactive')
        self.assertAlmostEqual(info['demand_percent'], 4.9)
        self.assertEqual(info['pid_control_target'], 21.)
        self.assertEqual(info['pid_control_measurement'], 20.6)
        self.assertEqual(info['pid_pwm_cycle_seconds'], 600.)
        self.assertEqual(info['pid_pwm_effective_cycle_seconds'], 3000.)
        self.assertEqual(info['pid_pwm_phase_seconds'], 700., 'Phase uses effective period, not 600s base')
        self.assertEqual(info['pid_pwm_wait_reason'], 'completed_pulse_rest')
        self.assertEqual(info['pid_pwm_last_confirmed_on_at'], d.origin)
        self.assertEqual(info['pid_pwm_last_confirmed_off_at'], d.origin + 147)
        self.assertAlmostEqual(info['pid_pwm_next_window_at'], d.origin + 3000)
        self.assertAlmostEqual(info['pid_pwm_next_window_seconds'], 2300)
        self.assertEqual(info['pid_control_parameters'], {
            'kp': 12.25, 'ki': 0., 'kd': 0., 'sample_seconds': 300., 'cycle_seconds': 600.})
        self.assertEqual(info['native_operating_limits'], {
            'min_on_seconds': 120., 'min_off_seconds': 120., 'max_on_seconds': 7200.})
        # Reading a later countdown does not evaluate PID or alter hardware.
        r.now += 9
        before = deepcopy((r.records, r.statuses, r.calls, r.persisted, r.manager.settings))
        self.assertAlmostEqual(attributes(r)['pid_pwm_next_window_seconds'], 2291)
        self.assertEqual((r.records, r.statuses, r.calls, r.persisted, r.manager.settings), before)
        await d.at(3000)
        self.assertEqual(d.on, [0, 3000])

    async def test_restart_of_unserved_4_9_percent_demand_retains_only_real_off_dwell(self):
        d = Driver(measured=20.6, kp=12.25, off_age=0,
                   min_on_seconds=600., min_off_seconds=600., cycle_seconds=3600.)
        r = d.r
        await d.at(0)
        self.assertEqual(d.on, [])
        self.assertNotIn('pid_pwm_run', r.record)
        r.now = d.origin + 100
        live_startup(r)
        r._memory.clear()
        await r.restart()
        for at in (100, 160, 220, 250, 400, 599):
            await d.at(at)
            self.assertEqual(d.on, [])
        self.assertEqual(r.record['off_at'][PRIMARY], d.origin)
        await d.at(600)
        self.assertEqual(d.on, [600])
        self.assertEqual(r.record['pid_pwm_run']['confirmed_on_at'], d.origin + 600)

    async def test_restart_after_completed_pulse_preserves_rest_and_current_target_cancels_it(self):
        d = Driver(measured=20.6, kp=12.25, cycle_seconds=3600.)
        r = d.r
        await d.at(0)
        await d.at(180)
        r.now = d.origin + 300
        live_startup(r)
        r._memory.clear()
        await r.restart()
        for at in (300, 360, 420, 450, 600):
            await d.at(at)
        self.assertEqual(d.on, [0])
        info = attributes(r)
        self.assertEqual(info['pid_restart_recovery'], 'integral_and_phase_restored')
        self.assertEqual(info['pid_pwm_wait_reason'], 'completed_pulse_rest')
        self.assertAlmostEqual(info['pid_pwm_next_window_at'], d.origin + 3603.6)
        await d.at(601, measured=21.)
        self.assertEqual(d.on, [0])
        self.assertEqual(attributes(r)['pid_pwm_state'], 'target_reached')
        self.assertIsNone(attributes(r)['pid_pwm_next_window_at'])
        self.assertNotIn('pid_pwm_run', r.record)


class StatusRobustnessTests(unittest.TestCase):
    def test_invalid_saved_native_timing_remains_readable_without_invented_limits(self):
        for invalid in ({'_native_timing_version': 2}, {'min_on_seconds': -1},
                        {'max_on_seconds': 120.}):
            with self.subTest(invalid=invalid):
                d = Driver(**invalid)
                r = d.r
                before = deepcopy((r.records, r.statuses, r.calls, r.manager.settings))
                info = attributes(r)
                self.assertIsNone(info['native_operating_limits'])
                self.assertEqual(info['native_primary_entity_id'], PRIMARY)
                self.assertEqual((r.records, r.statuses, r.calls, r.manager.settings), before)

    def test_foreign_cached_primary_cannot_escape_through_window_wait_lookup(self):
        d = Driver()
        r = d.r
        r.record['capabilities'] = {**asdict(r.cap), 'primary': 'climate.foreign_old_source'}
        r.hass.states.get = lambda entity: None
        looked_up = []
        r.manager.window_open_wait = N(status=lambda area, entity: looked_up.append((area, entity)))
        info = attributes(r)
        self.assertIsNone(info['native_primary_entity_id'])
        self.assertIsNone(info['native_primary_state'])
        self.assertEqual(info['source_entity_ids'], [PRIMARY])
        self.assertEqual(info['window_open_wait']['status'], 'window_wait_inactive')
        self.assertEqual(looked_up, [])
        self.assertEqual(r.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)

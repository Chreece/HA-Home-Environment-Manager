"""Optional native full-demand requests through actual dispatch/ACK/PID paths.

The fixture runs the production model, source selection, settings, command
journals, power guards and target logic. HA transport/time/room observations
are isolated; service completion never changes the physical feedback.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
f = runpy.run_path(str(ROOT / '.github/tests/test_061b7_runtime_mold.py'))
MoldRuntime, model, production, PACKAGE = (f[key] for key in ('MoldRuntime', 'model', 'production', 'PACKAGE'))
native_target = importlib.import_module(PACKAGE + '.equipment_native_target')
const = importlib.import_module(PACKAGE + '.const')
f['b']['base']['extract'](ROOT / 'equipment_runtime.py', ('_verify_restart_power',), production.__dict__)
MoldRuntime._verify_restart_power = production._verify_restart_power


def appliance(kind='dry', *, method='pid', minimum_on=120., minimum_off=120., **profile):
    r = MoldRuntime(method=method, kind='humidifier' if kind == 'humidify' else 'climate', minimum=30)
    raw = r.raw()
    native = 'auto' if kind == 'humidify' else kind
    goals = {'heat': 21., 'cool': 26., 'humidity': 50.}
    raw.update(control_mode=method, requested_mode=native, native_full_output=True,
               timed_setpoint_sequence=False, _native_timing_version=1,
               min_on_seconds=minimum_on, min_off_seconds=minimum_off,
               max_on_seconds=7200., mode_settings_version=1,
               mode_settings={kind: {'control_mode': method, 'kp': 10., 'ki': 0., 'kd': 0.,
                   'cycle_seconds': 3600., 'sample_seconds': 120.,
                   'profile_targets': {'home': goals, 'comfort': goals}}})
    raw.update(profile)
    r.manager.entry.options[model.SETTINGS] = {r.spec.identifier: raw}
    r.manager.entry.options[const.CONF_USE_MOLD] = False
    r.state.attributes.update(temperature=20., humidity=50., current_humidity=52.)
    r.sensor('sensor.room_temperature', 26.6 if kind == 'cool' else 20.4, 'temperature', '°C')
    r.sensor('sensor.room_humidity', 43. if kind == 'humidify' else 57.1, 'humidity', '%')
    r.target_service = 'set_temperature' if kind in ('heat', 'cool') else 'set_humidity'
    r.target_field = 'temperature' if kind in ('heat', 'cool') else 'humidity'
    r.target_value = (r.state.attributes['max_temp'] if kind == 'heat'
                      else r.state.attributes['min_temp'] if kind == 'cool'
                      else 80. if kind == 'humidify' else 30.)
    r.target_calls = lambda: [call for call in r.calls if call['service'] == r.target_service]
    r.native_mode = native if kind != 'humidify' else 'on'
    return r


async def start(r):
    await r.evaluate()
    assert r.record.get('pending') and r.record['pending']['power'] is True, r.status
    assert not r.target_calls(), 'No native target before ON acknowledgement'
    r.report(mode=r.native_mode)
    await r.evaluate()
    assert len(r.target_calls()) == 1, (r.calls, r.status)


async def exhaust(r):
    await start(r)
    await r.evaluate(60)
    await r.evaluate(60)
    assert len(r.target_calls()) == 3
    await r.evaluate(59.999)
    assert r.record['pending'] is not None
    await r.evaluate(.001)
    assert r.record['pending'] is None, r.status


class NativeTargetBudgetTests(unittest.IsolatedAsyncioTestCase):
    def close(self, r):
        r._cancel_pid_pwm_evaluation(r.spec)

    async def test_three_total_targets_then_nonblocking_actual_feedback_for_all_directions(self):
        for kind in ('heat', 'cool', 'dry', 'humidify'):
            with self.subTest(kind=kind):
                r=appliance(kind)
                actual=r.state.attributes[r.target_field]
                await exhaust(r)
                info=native_target.diagnostics(r,r.spec)
                self.assertEqual(info['attempts'],3)
                self.assertEqual(info['attempt_limit'],3)
                self.assertEqual(info['state'],'unconfirmed')
                self.assertTrue(info['exhausted'] and info['nonblocking'])
                self.assertIsNone(info['next_retry_at'])
                self.assertEqual(info['requested'],{r.target_field:r.target_value})
                self.assertEqual(info['reported'],{r.target_field:actual})
                self.assertEqual(r.state.attributes[r.target_field],actual)
                self.assertNotIn('paused',r.record)
                for _ in range(3):
                    await r.evaluate(60)
                self.assertEqual(len(r.target_calls()),3)
                self.close(r)

    async def test_short_pulse_releases_target_for_off_and_uses_only_remaining_attempts(self):
        r=appliance('dry',minimum_on=0.,minimum_off=0.)
        await start(r)
        r.sensor('sensor.room_humidity',49.,'humidity','%')
        await r.evaluate(10)
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'off'})
        self.assertTrue(r.record['pending']['power'])
        self.assertEqual(r.record[native_target.BUDGET]['attempts'],1)
        original=r.record[native_target.BUDGET]['journal']
        self.assertEqual(original['service'],'set_humidity')
        self.assertEqual(original['attempts'],1)
        r.report(mode='off')
        await r.evaluate()
        r.sensor('sensor.room_humidity',57.1,'humidity','%')
        await r.evaluate(10)
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'dry'})
        r.report(mode='dry')
        await r.evaluate()
        self.assertEqual(len(r.target_calls()),1,'Power cycle cannot reset feedback interval')
        await r.evaluate(40)
        self.assertEqual(len(r.target_calls()),2)
        self.assertEqual(r.record['pending']['attempts'],2)
        await r.evaluate(60)
        self.assertEqual(len(r.target_calls()),3)
        await r.evaluate(60)
        self.assertIsNone(r.record['pending'])
        self.assertEqual(r.record[native_target.BUDGET]['state'],'unconfirmed')
        self.close(r)

    async def test_exhausted_budget_survives_restart_and_next_power_cycle(self):
        r=appliance('dry')
        await exhaust(r)
        saved=deepcopy(r.record[native_target.BUDGET])
        r._memory.clear()
        await r.restart()
        for elapsed in (30,30,120):
            await r.evaluate(elapsed)
        self.assertEqual(r.record[native_target.BUDGET],saved)
        self.assertEqual(len(r.target_calls()),3)
        r.sensor('sensor.room_humidity',49.,'humidity','%')
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'off'})
        r.report(mode='off')
        await r.evaluate()
        r.sensor('sensor.room_humidity',57.1,'humidity','%')
        await r.evaluate(120)
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'dry'})
        r.report(mode='dry')
        await r.evaluate()
        self.assertEqual(len(r.target_calls()),3)
        self.close(r)

    async def test_unavailable_checks_do_not_spend_attempts_or_send_targets(self):
        r=appliance('dry')
        await start(r)
        budget=deepcopy(r.record[native_target.BUDGET])
        pending=deepcopy(r.record['pending'])
        r.state.state='unavailable'
        for elapsed in (60,60,60):
            await r.evaluate(elapsed)
        self.assertEqual(len(r.target_calls()),1)
        self.assertEqual(r.record[native_target.BUDGET],budget)
        self.assertEqual(r.record['pending'],pending)
        r.report(mode='dry')
        await r.evaluate()
        await r.evaluate(30)
        self.assertEqual(len(r.target_calls()),2)
        self.assertEqual(r.record['pending']['attempts'],2)
        self.close(r)

    async def test_real_late_ack_clears_notice_without_claiming_power_or_hiding_other_changes(self):
        r=appliance('dry')
        await exhaust(r)
        ownership=deepcopy(r.record['power'])
        r.state.attributes['humidity']=30.
        await r.evaluate()
        self.assertEqual(r.record[native_target.BUDGET]['state'],'confirmed')
        self.assertEqual(r.record['power'],ownership)
        self.assertFalse(native_target.diagnostics(r,r.spec)['exhausted'])
        self.assertEqual(len(r.target_calls()),3)
        self.close(r)

    async def test_changed_native_target_has_fresh_budget_and_stale_diagnostics_disappear(self):
        r=appliance('dry')
        await exhaust(r)
        old=deepcopy(r.record[native_target.BUDGET])
        r.state.attributes['min_humidity']=35.
        self.assertIsNone(native_target.diagnostics(r,r.spec))
        await r.evaluate()
        self.assertEqual(r.target_calls()[-1]['data'],{'humidity':35.})
        self.assertEqual(r.record['pending']['attempts'],1)
        self.assertEqual(r.record[native_target.BUDGET]['attempts'],1)
        self.assertEqual(r.record[native_target.PREVIOUS_BUDGET],old)
        self.close(r)

    async def test_old_more_than_three_dispatches_are_retained_without_new_retry(self):
        r=appliance('dry')
        await start(r)
        pending=r.record['pending']
        pending.pop(native_target.MARKER)
        pending.pop(native_target.FULL_MARKER)
        r.record.pop(native_target.BUDGET)
        pending['attempts']=7
        original=deepcopy(pending)
        await r.evaluate(59.999)
        self.assertIsNotNone(r.record['pending'])
        await r.evaluate(.001)
        self.assertIsNone(r.record['pending'])
        self.assertEqual(len(r.target_calls()),1)
        self.assertEqual(r.record[native_target.BUDGET]['attempts'],7)
        archived=r.record[native_target.BUDGET]['journal']
        for key,value in original.items():
            self.assertEqual(archived[key],value,key)
        self.close(r)

    async def test_native_power_pending_keeps_original_ack_retry_semantics(self):
        r=appliance('dry')
        await r.evaluate()
        for _ in range(4):
            await r.evaluate(60)
        self.assertTrue(r.record['pending']['power'])
        self.assertEqual(r.record['pending']['attempts'],5)
        self.assertEqual(len(r.calls),5)
        self.assertNotIn(native_target.BUDGET,r.record)
        self.assertFalse(r.record['power'],'Service returns cannot acknowledge ON')
        self.close(r)

    async def test_full_output_off_does_not_write_target_or_start_new_timed_transition(self):
        for kind in ('heat','cool','dry','humidify'):
            with self.subTest(kind=kind):
                r=appliance(kind,native_full_output=False,timed_setpoint_sequence=True)
                await r.evaluate()
                r.report(mode=r.native_mode)
                await r.evaluate()
                await r.evaluate(30)
                self.assertEqual(r.target_calls(),[])
                self.assertNotIn(native_target.BUDGET,r.record)
                self.assertNotIn('native_setpoint_stop',r.record)
                self.close(r)

    async def test_disable_retires_only_optional_target_and_preserves_its_history(self):
        r=appliance('dry')
        await start(r)
        pending=deepcopy(r.record['pending'])
        await r.async_update(r.spec,{'native_full_output':False})
        self.assertEqual(r.record['pending'],pending,'Preference write alone cannot acknowledge a command')
        await r.evaluate()
        self.assertIsNone(r.record['pending'])
        self.assertEqual(r.record[native_target.BUDGET]['journal'],pending)
        for _ in range(3):
            await r.evaluate(60)
        self.assertEqual(len(r.target_calls()),1)
        self.assertEqual(r.state.attributes['humidity'],50.)
        self.close(r)

    async def test_retry_rechecks_live_mode_features_and_bounds(self):
        cases=('off','other_mode','missing_feature','missing_bounds','changed_bounds')
        for change in cases:
            with self.subTest(change=change):
                r=appliance('dry')
                await start(r)
                if change=='off':
                    r.report(mode='off')
                elif change=='other_mode':
                    r.report(mode='heat')
                elif change=='missing_feature':
                    r.state.attributes['supported_features']=model.TEMP
                elif change=='missing_bounds':
                    r.state.attributes.pop('min_humidity')
                else:
                    r.state.attributes['min_humidity']=40.
                await r.evaluate(60)
                old_requests=[c for c in r.target_calls() if c['data']=={'humidity':30.}]
                self.assertEqual(len(old_requests),1,'Old full-demand request is no longer valid')
                self.close(r)

    async def test_automatic_does_not_borrow_an_exhausted_pid_budget(self):
        r=appliance('dry')
        await exhaust(r)
        old=deepcopy(r.record[native_target.BUDGET])
        await r.async_update(r.spec,{'control_mode':'automatic'},operating_mode='dry')
        await r.evaluate()
        for expected in (2,3,4,5):
            await r.evaluate(60)
            self.assertEqual(r.record['pending']['attempts'],expected)
            self.assertNotIn(native_target.MARKER,r.record['pending'])
        self.assertEqual(len(r.target_calls()),8)
        self.assertEqual(r.record[native_target.BUDGET],old)
        self.assertIsNone(native_target.diagnostics(r,r.spec))
        self.close(r)

    async def test_last_yield_capability_withdrawal_rolls_back_reserved_retry(self):
        r=appliance('dry')
        await start(r)
        original=deepcopy(r.record[native_target.BUDGET])
        save=r._save
        changed=False
        async def withdraw_after_reservation():
            nonlocal changed
            await save()
            pending=r.record.get('pending')
            if not changed and pending and pending.get('phase')=='retry_intent':
                changed=True
                r.state.attributes.pop('min_humidity')
        r._save=withdraw_after_reservation
        await r.evaluate(60)
        self.assertTrue(changed,'The actual durable retry boundary must be reached')
        self.assertEqual(len(r.target_calls()),1)
        self.assertEqual(r.record[native_target.BUDGET],original)
        self.close(r)

    async def test_same_entity_replacement_cannot_confirm_or_display_old_target(self):
        r=appliance('dry')
        await exhaust(r)
        budget=deepcopy(r.record[native_target.BUDGET])
        physical=deepcopy((r.record['power'],r.record['off_at']))
        r.registry_rows[r.primary].unique_id='replacement-native-identity'
        r.state.attributes['humidity']=30.
        self.assertIsNone(native_target.diagnostics(r,r.spec))
        await native_target.observe_feedback(r,r.spec)
        self.assertEqual(r.record[native_target.BUDGET],budget)
        self.assertEqual((r.record['power'],r.record['off_at']),physical)
        self.assertEqual(len(r.target_calls()),3)
        self.close(r)

    async def test_legacy_power_grant_without_registry_proof_skips_only_optional_target(self):
        r=appliance('dry')
        raw=r.raw()
        raw.pop('_native_authorization')
        r.manager.entry.options[model.SETTINGS][r.spec.identifier]=raw
        r.registry_rows[r.primary].id=None
        r.registry_rows[r.primary].unique_id=None
        self.assertTrue(model.permission(r.manager,r.spec,r.cap)[1])
        await r.evaluate()
        self.assertTrue(r.record['pending']['power'])
        r.report(mode='dry')
        await r.evaluate()
        self.assertEqual(r.target_calls(),[])
        self.assertNotIn(native_target.BUDGET,r.record)
        self.assertIsNone(r.record['pending'])
        self.assertEqual(r.status['status'],'controlling')
        r.sensor('sensor.room_humidity',49.,'humidity','%')
        await r.evaluate(120)
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'off'})
        self.close(r)

    async def test_late_target_ack_cannot_hide_a_simultaneous_real_manual_edit(self):
        r=appliance('dry')
        await exhaust(r)
        r.now+=1
        r.state.attributes.update(humidity=30.,fan_mode='High')
        r.state.last_updated=datetime.fromtimestamp(r.now,timezone.utc)
        r.state.context.user_id='physical-user'
        r.state.context.parent_id=None
        r.state.context.id='actual-user-change'
        await r.evaluate()
        self.assertEqual(r.record.get('paused'),'physical_manual_override')
        self.assertEqual(r.record[native_target.BUDGET]['state'],'unconfirmed')
        self.assertEqual(len(r.target_calls()),3)
        self.close(r)

    async def test_interrupted_retry_reservation_survives_restart_without_fresh_budget(self):
        r=appliance('heat')
        await start(r)
        save=r._save
        async def stop_after_durable_intent():
            await save()
            pending=r.record.get('pending')
            if pending and pending.get('phase')=='retry_intent':
                raise asyncio.CancelledError
        r._save=stop_after_durable_intent
        with self.assertRaises(asyncio.CancelledError):
            await r.evaluate(60)
        r._save=save
        self.assertEqual(len(r.target_calls()),1)
        self.assertEqual(r.record[native_target.BUDGET]['attempts'],2)
        self.assertEqual(r.record['pending']['phase'],'retry_intent')
        await r.restart()
        for elapsed in (30,60,60,60):
            await r.evaluate(elapsed)
        budget=r.record[native_target.BUDGET]
        self.assertEqual(budget['attempts'],2,'Uncertain dispatch reservation cannot become attempt one')
        self.assertEqual(budget['state'],'deferred')
        self.assertEqual(budget['reconciliation'],'stable_native_state')
        self.assertEqual(budget['journal']['phase'],'retry_intent')
        self.assertNotIn('unconfirmed_native_target',r.record,'No duplicate generic target blocker')
        self.assertEqual(len(r.target_calls()),1,'Read-only recovery does not fabricate or replay a call')
        self.close(r)

    async def test_full_output_disable_preserves_a_pre_upgrade_committed_off(self):
        r=appliance('heat',timed_setpoint_sequence=True)
        await r.evaluate()
        r.report(mode='heat')
        await r.evaluate()
        self.assertEqual(r.target_calls()[-1]['data'],{'temperature':35.})
        full_target=deepcopy(r.record['pending'])
        r.report(temperature=35.)
        await r.evaluate()
        r.now += 120
        owned=r.record['power'][r.cap.primary]
        # This exact old journal is a migration input, never a new b9 dispatch.
        committed={
            'version':1,'entity':r.cap.primary,'source_device_id':r.spec.source_device_id,
            'area':r.spec.area_id,'mode':'heat','temperature':5.,'phase':'waiting',
            'requested_at':r.now,'sent_at':r.now,'off_not_before':r.now+30.,
            'owned':True,'owned_since':owned['since'],
        }
        old=deepcopy(full_target)
        old.update(data={'temperature':5.},expected={'attributes':{'temperature':5.}},
                   stop_target=True,stop_finish=False,stop_sequence_at=r.now,
                   attempts=1,when=r.now,last_attempt_at=r.now)
        old.pop(native_target.MARKER,None)
        old.pop(native_target.FULL_MARKER,None)
        old['retry_context'].update(mode='off',automatic=False,shutdown=True,profile=None)
        r.record['pending']=old
        r.record['native_setpoint_stop']=committed
        await r.async_update(r.spec,{'native_full_output':False})
        self.assertEqual(r.record['native_setpoint_stop'],committed)
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'off'})
        self.assertTrue(r.record['pending']['power'])
        self.assertEqual(len(r.target_calls()),1,'No reverse-target or fresh full-output write')
        self.assertEqual(r.record['native_setpoint_stop']['target_journal'],old)
        r.report(mode='off')
        await r.evaluate()
        self.assertFalse(r.record['power'])
        self.close(r)


if __name__=='__main__':
    unittest.main(verbosity=2)

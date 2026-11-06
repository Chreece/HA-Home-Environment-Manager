"""Clock, HA-state adapter, active-episode and restart regressions."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('hem120wake', ROOT / 'wake_alarm.py')
wa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wa)
ALARM = 'sensor.next_alarm'
LEAD = 'input_number.wake_lead'
RING = datetime(2026, 1, 12, 6, tzinfo=timezone.utc).timestamp()
SETTINGS = {'wake_alarm_entity': ALARM, 'wake_lead_minutes_entity': LEAD,
            '_wake_entry_id': 'entry'}


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat()


def timestamp(value):
    return datetime.fromisoformat(value).timestamp()


class States(dict):
    def put(self, entity, value, **attrs):
        self[entity] = NS(entity_id=entity, state=value, attributes=attrs)

    def async_all(self, domain):
        return [s for e,s in self.items() if e.split('.')[0] == domain]


class Cases(unittest.TestCase):
    def setUp(self):
        self.states = States()
        self.hass = NS(config=NS(time_zone='Europe/Berlin'), states=self.states, data={})
        self.states.put(ALARM, iso(RING), device_class='timestamp')
        self.states.put(LEAD, '30', unit_of_measurement='min')
        self.tracker = wa.WakeAlarm()
        self.hass.data[wa._TRACKERS] = {'entry': self.tracker}

    def wake(self, when, raw=True, scope='room:bedroom', settings=None):
        return wa.wake_override(self.hass, SETTINGS if settings is None else settings,
                                scope, raw, now=when)

    def info(self, when=RING-3600, settings=None):
        return wa.alarm_evidence(self.hass, settings or SETTINGS, now=when)

    def test_exact_minutes_and_multiple_rooms(self):
        self.assertEqual(self.info(), dict(status='scheduled', alarm_at=RING,
                                         wake_at=RING-1800, lead_minutes=30))
        self.assertFalse(self.wake(RING-1800.01))
        self.assertTrue(self.wake(RING-1800))
        self.assertTrue(self.wake(RING-100, scope='household'))
        self.assertTrue(self.wake(RING-100, scope='room:guest'))
        self.assertFalse(self.wake(RING-10, False, scope='room:guest'))
        self.states.put(ALARM, iso(RING + 86400), device_class='timestamp')
        self.assertTrue(self.wake(RING+1))
        self.assertTrue(self.wake(RING+1, scope='household'))
        self.assertFalse(self.wake(RING+1, scope='room:guest'))
        self.assertFalse(self.wake(RING+5, False))
        self.assertFalse(self.wake(RING+10))

    def test_midnight_and_dst_elapsed_lead(self):
        self.states.put(ALARM, '00:10:00')
        info = self.info(timestamp('2026-01-11T23:30+01:00'))
        self.assertEqual(info['wake_at'], timestamp('2026-01-11T23:40+01:00'))
        self.states.put(ALARM, '03:05:00')
        info = self.info(timestamp('2026-03-29T00:10+01:00'))
        self.assertEqual(info['alarm_at'], timestamp('2026-03-29T03:05+02:00'))
        self.assertEqual(info['wake_at'], timestamp('2026-03-29T01:35+01:00'))
        self.states.put(ALARM, '02:30:00')
        # Spring gap is not silently shifted by one hour.
        self.assertEqual(self.info(timestamp('2026-03-29T00:10+01:00'))['alarm_at'],
                         timestamp('2026-03-30T02:30+02:00'))
        # Autumn duplicate local hour resolves to the first occurrence only.
        self.assertEqual(self.info(timestamp('2026-10-25T01:00+02:00'))['alarm_at'],
                         timestamp('2026-10-25T02:30+02:00'))
        self.assertEqual(self.info(timestamp('2026-10-25T02:31+02:00'))['alarm_at'],
                         timestamp('2026-10-26T02:30+01:00'))

    def test_timestamp_local_helper_and_fold(self):
        helper = 'input_datetime.wake_up'
        config = {**SETTINGS, 'wake_alarm_entity': helper}
        now = timestamp('2026-10-25T01:00+02:00')
        late = timestamp('2026-10-25T02:30+01:00')
        self.states.put(helper, '2026-10-25 02:30:00', has_date=True, has_time=True,
                        timestamp=late)
        self.assertEqual(self.info(now, config)['alarm_at'], late)
        self.states.put(helper, '2026-03-29 02:30:00', has_date=True, has_time=True)
        self.assertIsNone(self.info(now, config)['wake_at'])
        self.states.put(helper, '2026-03-29', has_date=True, has_time=False)
        self.assertIsNone(self.info(now, config)['wake_at'])
        self.states.put('time.weekday_alarm', '08:30:00')
        self.assertEqual(self.info(now, {**SETTINGS,'wake_alarm_entity':'time.weekday_alarm'})['alarm_at'],
                         timestamp('2026-10-25T08:30+01:00'))
        self.states.put(ALARM, '2026-10-25T01:30:00Z')
        self.assertEqual(self.info(now)['alarm_at'], late)

    def test_bad_data_never_triggers(self):
        for value, unit in ((-1,'min'), ('abc', 'min'), ('NaN','min'), ('inf','min'),
                            ('1e308','min'), (True, 'min'), ('10', 'h'), ('30', 'm'), ('10','s')):
            with self.subTest(value=value, unit=unit):
                self.states.put(LEAD, value, unit_of_measurement=unit)
                self.assertIsNone(self.info()['wake_at'])
                self.assertFalse(self.wake(RING-5))
        self.states.put(LEAD, '1.5')  # unitless numerical helper = minutes
        self.assertEqual(self.info()['wake_at'], RING-90)
        for value in ('unknown', 'unavailable', '', '2026-11-06', '25:62', '1800', '2026-99-20 10:00'):
            with self.subTest(value=value):
                self.states.put(ALARM, value)
                self.assertFalse(self.wake(RING-1))
        self.states.put(ALARM, iso(RING), restored=True)
        self.assertFalse(self.wake(RING-1))
        self.states.put(ALARM, iso(RING)); self.states.put(LEAD, '30', restored=True)
        self.assertFalse(self.wake(RING-1))
        self.states.pop(LEAD)
        self.assertFalse(self.wake(RING-1))
        self.assertFalse(self.wake(RING-1, settings={'wake_alarm_entity': ALARM}))

    def test_late_callback_zero_lead_and_rollover(self):
        self.states.put(LEAD, '0')
        self.assertFalse(self.wake(RING-30))
        self.states.put(ALARM, iso(RING + 86400))
        self.assertTrue(self.wake(RING + .25), 'observed ringing instant crossed')
        self.assertFalse(self.wake(RING + .25, scope='room:unobserved'))
        self.assertFalse(self.wake(RING+1, None), 'unknown sleep cannot provide new wake evidence')
        self.assertTrue(self.wake(RING+3))
        # An old dated timestamp on a cold start cannot signal a new wake.
        self.states.put(ALARM, iso(RING))
        self.assertFalse(self.wake(RING+1, scope='room:other'))

    def test_zero_lead_alarm_clearing_at_ring_keeps_witnessed_wake(self):
        self.states.put(LEAD, '0')
        for index, value in enumerate(('unknown', 'unavailable', '', None)):
            with self.subTest(value=value):
                scope = f'room:cleared{index}'
                self.states.put(ALARM, iso(RING))
                self.assertFalse(self.wake(RING-10, scope=scope))
                if value is None:
                    self.states.pop(ALARM)
                else:
                    self.states.put(ALARM, value)
                self.assertTrue(self.wake(RING+.25, scope=scope))
                self.assertFalse(self.wake(RING+.25, scope=scope+'-unobserved'))
                self.states.put(ALARM, iso(RING+86400))
                self.assertTrue(self.wake(RING+3, scope=scope))
                self.assertFalse(self.wake(RING+4, False, scope=scope))
                self.assertFalse(self.wake(RING+5, scope=scope))
        # Missing lead data does not turn an armed-but-not-triggered interval
        # into wake permission. A clear before ringing still cancels it.
        self.states.put(ALARM, iso(RING))
        self.assertFalse(self.wake(RING-10, scope='room:bad_lead'))
        self.states.put(LEAD, 'unavailable')
        self.states.put(ALARM, 'unknown')
        self.assertFalse(self.wake(RING+.25, scope='room:bad_lead'))

    def test_store_failure_does_not_abort_live_wake_decision(self):
        class BrokenStore:
            def async_delay_save(self, snapshot, seconds):
                raise OSError('simulated unavailable storage')

        self.tracker.store = BrokenStore()
        with self.assertLogs(wa.__name__, level='ERROR') as logs:
            self.assertTrue(self.wake(RING-10))
        self.assertTrue(any('Could not schedule wake alarm history save' in line
                            for line in logs.output))
        self.assertTrue(self.tracker.dirty)
        self.states.put(ALARM, iso(RING+86400))
        self.assertTrue(self.wake(RING+1))

    def test_disarm_and_unseen_intervals(self):
        self.states.put(LEAD, '0')
        self.assertFalse(self.wake(RING-5))
        self.assertFalse(self.wake(RING-4, False))
        self.assertFalse(self.wake(RING+1))
        self.assertFalse(self.wake(RING-5))
        self.states.put(ALARM, 'unavailable')
        self.assertFalse(self.wake(RING-1))
        self.states.put(ALARM, iso(RING+86400))
        self.assertFalse(self.wake(RING+.1))
        self.states.put(ALARM, iso(RING))
        self.assertFalse(self.wake(RING-300))
        self.states.put(ALARM, iso(RING+86400))
        self.assertFalse(self.wake(RING+14400), 'no fabricated ring after a long offline gap')

    def test_live_lead_and_source_changes(self):
        self.assertTrue(self.wake(RING-900))
        self.states.put(LEAD, '1', unit_of_measurement='min')
        self.assertFalse(self.wake(RING-899), 'edited lead leaves the upcoming wake window')
        self.assertTrue(self.wake(RING-60))
        self.states.put(ALARM, iso(RING+3600))
        self.assertFalse(self.wake(RING-59), 'rescheduling before ring re-evaluates the window')
        self.assertTrue(self.wake(RING+3600))
        changed = {**SETTINGS, 'wake_alarm_entity':'sensor.different'}
        self.assertFalse(self.wake(RING+3601, settings=changed), 'new source cannot reuse old episode')

    def test_picker(self):
        self.states.put('sensor.temp','21',unit_of_measurement='°C')
        self.states.put('input_datetime.date_only','2026-01-10',has_date=True,has_time=False)
        self.states.put('input_datetime.wake','unknown',has_time=True)
        self.states.put('sensor.offline_alarm','unavailable', device_class='timestamp')
        self.states.put('time.offline','unavailable')
        self.states.put('sensor.bad_lead', '30', unit_of_measurement='s')
        self.states.put('number.lead','unavailable')
        alarms, leads = wa.wake_source_options(self.hass, {'wake_alarm_entity':'sensor.removed'})
        self.assertEqual(alarms, sorted([ALARM,'input_datetime.wake','sensor.offline_alarm',
                                        'time.offline','sensor.removed']))
        self.assertEqual(leads, sorted([LEAD,'number.lead']))


class MemoryStore:
    by_key = {}
    def __init__(self, hass, version, key):
        self.key = key
    async def async_load(self):
        return deepcopy(self.by_key.get(self.key))
    def async_delay_save(self, snapshot, seconds):
        self.by_key[self.key] = deepcopy(snapshot())
    async def async_save(self, data):
        self.by_key[self.key] = deepcopy(data)


class EntryLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_entry_isolation_restart_and_source_bound_reset(self):
        module = ModuleType('homeassistant.helpers.storage'); module.Store = MemoryStore
        hass = NS(config=NS(time_zone='UTC'), states=States(), data={})
        hass.states.put(ALARM, iso(RING)); hass.states.put(LEAD, '15')
        MemoryStore.by_key.clear()
        with patch.dict(sys.modules, {'homeassistant.helpers.storage': module}), patch.object(wa, 'clock',return_value=RING):
            await wa.async_start_wake(hass,'entry',SETTINGS)
            await wa.async_start_wake(hass,'another',SETTINGS)
            self.assertTrue(wa.wake_override(hass,SETTINGS,'room:bedroom',True,now=RING-5))
            await wa.async_stop_wake(hass,'entry')
            hass.states.put(ALARM, iso(RING+86400))
            await wa.async_start_wake(hass,'entry',SETTINGS)
            self.assertTrue(wa.wake_override(hass,SETTINGS,'room:bedroom',True,now=RING+1))
            self.assertFalse(wa.wake_override(hass,{**SETTINGS,'_wake_entry_id':'another'},
                                               'room:bedroom',True,now=RING+1))
            self.assertFalse(wa.wake_override(hass,SETTINGS,'room:bedroom',False,now=RING+2))
            self.assertFalse(wa.wake_override(hass,SETTINGS,'room:bedroom',True,now=RING+3))
            await wa.async_stop_wake(hass,'entry')
            hass.states.put(ALARM, iso(RING))
            await wa.async_start_wake(hass,'entry',SETTINGS)
            self.assertTrue(wa.wake_override(hass,SETTINGS,'room:bedroom',True,now=RING))
            await wa.async_stop_wake(hass,'entry')
            await wa.async_start_wake(hass,'entry',{})
            await wa.async_stop_wake(hass,'entry')
            await wa.async_start_wake(hass,'entry',SETTINGS)
            self.assertFalse(wa.wake_override(hass,SETTINGS,'room:bedroom',True,now=RING+1))
            await wa.async_stop_wake(hass,'entry')
            await wa.async_stop_wake(hass,'another')
            self.assertNotIn(wa._TRACKERS, hass.data)


if __name__ == '__main__':
    unittest.main(verbosity=2)

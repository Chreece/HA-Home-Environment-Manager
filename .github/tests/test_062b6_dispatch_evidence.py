"""Real door observations through production native dispatch, never device I/O."""
from __future__ import annotations
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(ROOT / '.github/tests/test_onoff_native_extrema.py'))
model, Runtime, SPEC, PRIMARY = b['model'], b['NativeRuntime'], b['SPEC'], b['PRIMARY']
doors = b['load_pure']('room_doors', 'room_doors.py')
resume = b['load_pure']('equipment_resume', 'equipment_resume.py')
b['extract'](b['RUNTIME'], ('resume_information',), b['production'].__dict__)
Runtime.resume_information = b['production'].resume_information

class DispatchEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.offset, self.reads = 0.0, 0
        self.contact = N(entity_id='binary_sensor.test_door', state='off',
            attributes={'device_class':'door'}, last_changed=self.time-timedelta(hours=1),
            last_reported=self.time)
        self.available, self.area = True, 'room'
        self.config = {'door_sensors':[self.contact.entity_id]}
        self.hass = N(states=N(get=lambda entity: self.contact if self.available else None))
        self.saved_modules = {}
        for name, attrs in {
            'discovery': {'entity_area': lambda h,e:self.area,
                          '_device_class':lambda h,s:s.attributes.get('device_class')},
            'room_sources': {'native':lambda *args:True},
        }.items():
            full = b['PACKAGE']+'.'+name
            self.saved_modules[full] = sys.modules.get(full)
            module = ModuleType(full); module.__dict__.update(attrs); sys.modules[full]=module
        self.planner = patch.object(model, 'plan_for', self.plan)
        self.planner.start()

    def tearDown(self):
        self.planner.stop()
        for name, module in self.saved_modules.items():
            if module is None:sys.modules.pop(name, None)
            else:sys.modules[name]=module

    def plan(self, manager, spec):
        self.reads += 1
        door = doors.observe(self.hass, 'room', self.config,
            now=self.time+timedelta(seconds=self.offset, microseconds=self.reads),
            home='home', sleeping=False, occupancy='occupied', window_safe=True,
            temperature_c=20, humidity_rh=45)
        return {**deepcopy(manager.plan), 'door':door, 'door_eco_active':door['eco_active']}

    def runtime(self, method='automatic', mode='heat', mutation=None):
        r = Runtime(method,mode)
        self.refreshes=[]
        r._presentation_updates=N(request=self.refreshes.append)
        original=r._save
        self.intent_views=[]
        async def save():
            await original()
            if isinstance(r.record.get('pending'),dict) and r.record['pending'].get('phase')=='intent':
                self.intent_views.append(r.resume_information(SPEC))
                if mutation:mutation(r)
            await asyncio.sleep(0)  # Exercise a genuine async boundary.
        r._save=save
        return r

    async def test_unchanged_door_dispatches_under_real_advancing_observation_clock(self):
        for method in ('automatic','pid'):
            for mode in ('heat','cool'):
                for state in ('off','on'):
                    with self.subTest(method=method,mode=mode,state=state):
                        self.contact.state=state
                        r=self.runtime(method,mode)
                        await r.tick(SPEC)
                        self.assertEqual(len(r.calls),1)
                        self.assertEqual(r.calls[0]['data'],{'hvac_mode':mode})
                        self.assertEqual(r.record['pending']['phase'],'commanded')
                        self.assertEqual(self.contact.state,state)

    async def test_dry_only_dehumidifier_dispatches_with_selected_door(self):
        for method in ('automatic','pid'):
            r=self.runtime(method,'dry')
            r.state.attributes.update(hvac_modes=['off','dry'],supported_features=4,
                humidity=50,min_humidity=30,max_humidity=80)
            r.measurements=lambda *a:{'temperature':20.,'humidity':70.,'pm25':None,'co2':None}
            cap=model.capabilities(r.manager,SPEC)
            await r._power(SPEC,cap,'dry',automatic=True)
            self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'dry'})

    async def test_door_transition_still_aborts_and_clears_only_unsent_intent(self):
        r=self.runtime(mutation=lambda _:setattr(self.contact,'state','on'))
        await r.tick(SPEC)
        self.assertEqual(r.calls,[])
        self.assertIsNone(r.record['pending'])
        self.assertIn(SPEC.identifier,self.refreshes)
        self.assertEqual(r.statuses[-1][0],'authority_or_evidence_changed_before_dispatch')

    async def test_same_final_state_new_transition_epoch_still_aborts(self):
        r=self.runtime(mutation=lambda _:setattr(self.contact,'last_changed',self.contact.last_changed+timedelta(seconds=1)))
        await r.tick(SPEC)
        self.assertEqual(r.calls,[])
        self.assertIsNone(r.record['pending'])

    async def test_lost_moved_restored_or_reclassified_contact_still_aborts(self):
        changes=[lambda _:setattr(self,'available',False),lambda _:setattr(self,'area','other'),
                 lambda _:self.contact.attributes.update(restored=True),
                 lambda _:self.contact.attributes.update(device_class='window')]
        for change in changes:
            self.available=True;self.area='room';self.contact.attributes={'device_class':'door'}
            r=self.runtime(mutation=change)
            await r.tick(SPEC)
            self.assertEqual(r.calls,[])
            self.assertIsNone(r.record['pending'])

    async def test_contact_report_expiry_is_rechecked(self):
        self.config['door_settings']={self.contact.entity_id:{'report_timeout_minutes':1}}
        r=self.runtime(mutation=lambda _:setattr(self,'offset',61))
        await r.tick(SPEC)
        self.assertEqual(r.calls,[])

    async def test_closure_stability_boundary_is_rechecked(self):
        self.contact.last_changed=self.time-timedelta(seconds=119)
        r=self.runtime(mutation=lambda _:setattr(self,'offset',2))
        await r.tick(SPEC)
        self.assertEqual(r.calls,[])

    async def test_window_presence_sleep_and_profile_changes_still_abort(self):
        for key,value in (('window_safe',False),('away','away'),('sleeping',True),('occupancy','unoccupied')):
            with self.subTest(key=key):
                r=self.runtime(mutation=lambda r:r.manager.plan.update({key:value}))
                await r.tick(SPEC)
                self.assertEqual(r.calls,[])

    async def test_feedback_and_settings_changes_still_abort(self):
        for mutation in (lambda r:setattr(r,'measurement',20),
                         lambda r:r.manager.settings.update(preset='eco')):
            r=self.runtime(mutation=mutation)
            await r.tick(SPEC)
            self.assertEqual(r.calls,[])

    async def test_native_manual_change_still_aborts(self):
        r=self.runtime(mutation=lambda r:r.report(mode='cool'))
        await r.tick(SPEC)
        self.assertEqual(r.calls,[])

    async def test_abort_does_not_retain_transient_recovery_instructions(self):
        r=self.runtime(mutation=lambda _:setattr(self.contact,'state','on'))
        await r.tick(SPEC)
        self.assertTrue(self.intent_views)
        self.assertIsNone(r.resume_information(SPEC))
        self.assertIn(SPEC.identifier,self.refreshes)

    async def test_unconfirmed_intent_has_honest_message_without_altering_recovery(self):
        r=self.runtime()
        await r.tick(SPEC)
        view=self.intent_views[0]
        self.assertEqual(view['phase'],'intent')
        self.assertIs(view['dispatch_confirmed'],False)
        self.assertTrue(view['needs_physical_check'])
        self.assertIn('not confirmed',view['instructions'])
        self.assertEqual(r.record['pending']['phase'],'commanded')
        self.assertIn('confirmation',r.resume_information(SPEC)['instructions'].lower())
        for locale in ('en','el','de'):
            self.assertIn(PRIMARY,resume.unconfirmed_dispatch_message(view,language=locale))

if __name__=='__main__':
    unittest.main(verbosity=2)

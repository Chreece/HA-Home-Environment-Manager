"""Door evidence, graph and configuration invariants without physical I/O."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
base = runpy.run_path(str(ROOT / '.github/tests/test_062b1_room_doors.py'))
door, hass, now = base['door'], base['hass'], base['now']
load, AREAS, state = base['load'], base['AREAS'], base['state']
sources = base['sources']
context = load('door_context', base['ROOT'] / 'door_context.py')

class Evidence(unittest.TestCase):
    def setUp(self):
        AREAS.update({'binary_sensor.door_a':'area_a','binary_sensor.door_c':'area_a',
                      'binary_sensor.presence_a':'area_a'})
        hass.states['binary_sensor.door_a']=state('binary_sensor.door_a','off','door',age=600)
        hass.states['binary_sensor.door_c']=state('binary_sensor.door_c','off','door',age=600)
        hass.states['binary_sensor.presence_a']=state('binary_sensor.presence_a','off','occupancy',age=1200)
        self.cfg={'door_sensors':['binary_sensor.door_a'],'closed_door_eco':True}
        self.args=dict(occupancy='unoccupied',occupancy_evidence='all_selected_room_sensors_off',
                       occupancy_sources=['binary_sensor.presence_a'],home='home',sleeping=False,
                       temperature_c=20,humidity_rh=40,window_safe=True,now=now)
    def observe(self, cfg=None, **extra):
        return door.observe(hass,'area_a',cfg or self.cfg,**{**self.args,**extra})
    def test_closed_for_weeks_is_not_a_missing_heartbeat(self):
        hass.states['binary_sensor.door_a'].last_changed=now-timedelta(days=30)
        self.assertTrue(self.observe()['eco_active'])
        self.assertEqual(self.observe()['contacts'][0]['health'],'ok')
    def test_reporting_expiry_is_explicit_not_last_change(self):
        c=hass.states['binary_sensor.door_a'];c.last_changed=now-timedelta(days=4)
        c.last_reported=now-timedelta(seconds=5)
        cfg={**self.cfg,'door_settings':{'binary_sensor.door_a':{'report_timeout_minutes':5}}}
        self.assertTrue(self.observe(cfg)['eco_active'])
        c.last_reported=now-timedelta(minutes=6)
        self.assertFalse(self.observe(cfg)['eco_active'])
        self.assertEqual(self.observe(cfg)['contacts'][0]['health'],'report_expired')
    def test_missing_or_future_heartbeat_does_not_authorize_eco(self):
        cfg={**self.cfg,'door_settings':{'binary_sensor.door_a':{'report_timeout_minutes':5}}}
        self.assertEqual(self.observe(cfg)['contacts'][0]['health'],'report_time_unknown')
        hass.states['binary_sensor.door_a'].last_reported=now+timedelta(seconds=1)
        self.assertFalse(self.observe(cfg)['eco_active'])
    def test_local_vacancy_must_be_stable_at_live_gate(self):
        self.assertTrue(self.observe()['eco_active'])
        hass.states['binary_sensor.presence_a'].last_changed=now-timedelta(seconds=5)
        self.assertEqual(self.observe()['eco_reason'],'awaiting_stable_vacancy')
        self.assertFalse(self.observe(occupancy_sources=[])['eco_active'])
    def test_verified_room_list_authority_is_not_replaced(self):
        self.assertTrue(self.observe(occupancy_evidence='verified_room_list_unoccupied',
                                     occupancy_sources=[])['eco_active'])
        self.assertFalse(self.observe(occupancy='occupied')['eco_active'])
    def test_unknown_sleep_blocks_eco(self):
        self.assertEqual(self.observe(sleeping=None)['eco_reason'],'sleep_unknown')
    def test_mixed_contacts_report_open_without_claiming_complete(self):
        cfg={**self.cfg,'door_sensors':['binary_sensor.door_a','binary_sensor.door_c']}
        hass.states['binary_sensor.door_a'].state='on'
        hass.states['binary_sensor.door_c'].state='unavailable'
        report=self.observe(cfg)
        self.assertEqual(report['boundary'],'open')
        self.assertFalse(report['contacts_complete'])
        self.assertFalse(report['eco_active'])
    def test_moved_retyped_restored_invalid_time_are_unknown(self):
        c=hass.states['binary_sensor.door_a']
        AREAS[c.entity_id]='area_b'
        self.assertEqual(self.observe()['contacts'][0]['health'],'wrong_area')
        AREAS[c.entity_id]='area_a';c.attributes['device_class']='window'
        self.assertEqual(self.observe()['contacts'][0]['health'],'wrong_class')
        c.attributes['device_class']='door';c.attributes['restored']=True
        self.assertEqual(self.observe()['contacts'][0]['health'],'restored')
        c.attributes['restored']=False;c.last_changed=now+timedelta(seconds=1)
        self.assertEqual(self.observe()['contacts'][0]['health'],'invalid_timestamp')


def room(name,contacts=(),temp=20,rh=45,co2=600):
    return dict(name=name,contacts=list(contacts),boundary='closed',sleeping=False,
                measurements=dict(temperature_c=temp,humidity_rh=rh,co2_ppm=co2))
def edge(entity,target,kind='interior',state='open',health='ok'):
    return dict(entity_id=entity,target_area=target,kind=kind,state=state,health=health)

class Topology(unittest.TestCase):
    def test_explicit_graph_is_symmetric_and_cycles_are_bounded(self):
        reports={'a':room('A',[edge('ab','b')]),'b':room('B',[edge('bc','c')]),
                 'c':room('C',[edge('ca','a')])}
        links,connected=context.topology(reports)
        self.assertEqual(connected,{'a':['b','c'],'b':['a','c'],'c':['a','b']})
        self.assertEqual(links['b'][0]['owner_area'],'a')
    def test_closed_unknown_fire_exterior_and_invalid_never_give_transfer_path(self):
        for item in [edge('ab','b',state='closed'),edge('ab','b',health='unavailable'),
                     edge('ab','b',kind='fire'),edge('ab','b',kind='exterior'),
                     edge('ab','missing'),edge('ab','a')]:
            with self.subTest(item=item):
                _,connected=context.topology({'a':room('A',[item]),'b':room('B')})
                self.assertEqual(connected['a'],[])
    def test_humidity_comparison_uses_temperature_not_relative_rh_alone(self):
        reports={'a':room('Warm',[edge('ab','b')],temp=25,rh=60),
                 'b':room('Cool',temp=17,rh=45)}
        context.enrich(reports)
        notes=reports['a']['advisories']
        risk=next(n for n in notes if n['code']=='moisture_transfer_risk')
        self.assertGreater(risk['evidence']['projected_rh'],70)
        self.assertTrue(reports['a']['advisory_only'])
        reports['a']['measurements']['temperature_c']=None
        context.enrich(reports)
        self.assertNotIn('moisture_transfer_risk',[n['code'] for n in reports['a']['advisories']])
    def test_co2_requires_fresh_air_not_a_purifier_command(self):
        reports={'a':room('Bedroom',co2=1400)}
        context.enrich(reports)
        self.assertIn('fresh_air_needed',[n['code'] for n in reports['a']['advisories']])
        self.assertTrue(reports['a']['advisory_only'])
        self.assertNotIn('command',reports['a'])
    def test_possible_outdoor_route_needs_verified_path_and_outdoor_gate(self):
        reports={'a':room('A',[edge('ab','b')]),'b':room('B')}
        reports['b'].update(window_open=True,window_evidence_complete=True)
        context.enrich(reports,outside_safe=False)
        self.assertEqual(reports['a']['possible_outdoor_paths'],[])
        context.enrich(reports,outside_safe=True)
        self.assertEqual(reports['a']['possible_outdoor_paths'],['b'])
        reports['b']['window_evidence_complete']=False
        context.enrich(reports,outside_safe=True)
        self.assertEqual(reports['a']['possible_outdoor_paths'],[])
    def test_quiet_boundary_requires_verified_sleep_not_door_inference(self):
        reports={'a':room('A')}
        context.enrich(reports)
        self.assertFalse(reports['a']['quiet_boundary'])
        reports['a']['sleeping']=True;context.enrich(reports)
        self.assertTrue(reports['a']['quiet_boundary'])
        reports['a']['boundary']='unknown';context.enrich(reports)
        self.assertFalse(reports['a']['quiet_boundary'])
    def test_thermal_session_does_not_fill_gaps(self):
        monitor=context.DoorContextMonitor()
        monitor._session('a',('x',),'closed',1000)
        observed=monitor._session('a',('x',),'closed',1060)
        self.assertEqual(observed['closed_minutes'],1)
        observed=monitor._session('a',('x',),'closed',5000)
        self.assertEqual(observed['closed_minutes'],1)
        self.assertGreater(observed['unobserved_minutes'],60)
        observed=monitor._session('a',('other_source',),'closed',5060)
        self.assertEqual(observed['closed_minutes'],0)
    def test_transition_hints_ignore_restores_reconnects_and_identical_reports(self):
        monitor=context.DoorContextMonitor();monitor._members={'binary_sensor.door_a':'a'}
        closed=state('binary_sensor.door_a','off','door');opened=state('binary_sensor.door_a','on','door')
        monitor.state_changed(closed.entity_id,closed,closed,1000)
        monitor.state_changed(closed.entity_id,None,opened,1001)
        self.assertFalse(monitor._events)
        monitor.state_changed(closed.entity_id,closed,opened,1002)
        self.assertEqual(len(monitor._events[closed.entity_id]),1)
        opened.attributes['restored']=True
        monitor.state_changed(closed.entity_id,opened,closed,1003)
        self.assertEqual(len(monitor._events[closed.entity_id]),1)

class Settings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        area=ModuleType('homeassistant.helpers.area_registry')
        area.async_get=lambda h:N(async_get_area=lambda key:N(name={'area_a':'A','area_b':'B'}[key]) if key in ('area_a','area_b') else None)
        sys.modules[area.__name__]=area
        sys.modules['homeassistant.helpers'].area_registry=area
        hierarchy=ModuleType(base['PACKAGE']+'.device_hierarchy')
        hierarchy.configured_area_ids=lambda settings:settings.get('areas',[])
        sys.modules[hierarchy.__name__]=hierarchy
        errors=ModuleType('homeassistant.exceptions');errors.HomeAssistantError=ValueError
        sys.modules[errors.__name__]=errors
        cls.module=load('door_settings',base['ROOT']/'door_settings.py')
    def setUp(self):
        AREAS['binary_sensor.door_a']='area_a'
        hass.states['binary_sensor.door_a']=state('binary_sensor.door_a','off','door')
        entry=N(options={},data={'areas':['area_a','area_b'],'climate_rooms':{'area_a':{
            'door_sensors':['binary_sensor.door_a'],'device_settings':{'heater':{'control':'manual'}}}}})
        self.calls=[]
        def save(e,*,options):self.calls.append(deepcopy(options));e.options=options
        hass.config_entries=N(async_update_entry=save)
        class Manager:
            _active=False
            @property
            def settings(self):return {**self.entry.data,**self.entry.options}
        self.manager=Manager();self.manager.entry=entry;self.manager.hass=hass
    def write(self,key,value):return asyncio.run(self.module.async_update(self.manager,'area_a','binary_sensor.door_a',key,value))
    def test_exact_native_identity_and_target_area_validation(self):
        self.write('target_area','area_b')
        self.assertEqual(self.calls[-1]['climate_rooms']['area_a']['door_settings']['binary_sensor.door_a']['target_area'],'area_b')
        self.assertEqual(self.calls[-1]['climate_rooms']['area_a']['device_settings'],{'heater':{'control':'manual'}})
        for invalid in ('area_a','missing',True):
            with self.assertRaises(ValueError):self.write('target_area',invalid)
        AREAS['binary_sensor.door_a']='area_b'
        with self.assertRaises(ValueError):self.write('kind','interior')
    def test_exterior_does_not_retain_interior_connection(self):
        self.write('target_area','area_b');self.write('kind','exterior')
        self.assertIsNone(self.calls[-1]['climate_rooms']['area_a']['door_settings']['binary_sensor.door_a']['target_area'])
        with self.assertRaises(ValueError):self.write('target_area','area_b')
    def test_timeout_is_opt_in_bounded_and_noop_write_is_suppressed(self):
        for invalid in (True,float('nan'),-1,10081,'broken'):
            with self.assertRaises(ValueError):self.write('report_timeout_minutes',invalid)
        self.write('report_timeout_minutes',0);count=len(self.calls)
        self.write('report_timeout_minutes',0)
        self.assertEqual(count,len(self.calls))

class MonitorAdapter(unittest.TestCase):
    def setUp(self):
        Settings.setUpClass()
        AREAS.update({'binary_sensor.door_a':'area_a','binary_sensor.presence_a':'area_a'})
        hass.states['binary_sensor.door_a']=state('binary_sensor.door_a','on','door',age=600)
        hass.states['binary_sensor.presence_a']=state('binary_sensor.presence_a','off','occupancy',age=1200)
        sources.room_temperature_evidence=lambda h,c,area,**kw: (25 if area=='area_a' else 17,{})
        self.cfg={'areas':['area_a','area_b'],'climate_rooms':{
            'area_a':{'door_sensors':['binary_sensor.door_a'],
                      'door_settings':{'binary_sensor.door_a':{'target_area':'area_b'}}},
            'area_b':{}},'room_sources':{'area_a':{'temperature':['sensor.a']},
                                       'area_b':{'temperature':['sensor.b']}}}
        self.rooms=[N(area_id='area_a',name='A',readings=[
                N(metric='humidity',value=60,available=True),N(metric='co2',value=1400,available=True)],windows=[]),
            N(area_id='area_b',name='B',readings=[N(metric='humidity',value=40,available=True)],
              windows=[N(opened=True)])]
        self.env={a:{'climate_plan':{'sleeping':False}} for a in ('area_a','area_b')}
        self.presence={a:('unoccupied','verified_room_list_unoccupied',[]) for a in ('area_a','area_b')}
        self.monitor=context.DoorContextMonitor()
        class NoServices:
            def __getattr__(self,key):raise AssertionError('Passive door context attempted service access: '+key)
        hass.services=NoServices()
    def update(self,seconds=0,home='home'):
        return self.monitor.update(hass,self.cfg,self.env,self.rooms,self.presence,home,
                                   outside_safe=True,now=now.timestamp()+seconds)
    def test_actual_adapter_builds_context_without_changing_config_or_controllers(self):
        before=deepcopy(self.cfg)
        reports,tracked=self.update()
        self.assertEqual(self.cfg,before)
        self.assertEqual(tracked,{'binary_sensor.door_a'})
        self.assertEqual(reports['area_a']['connected_rooms'],['area_b'])
        self.assertEqual(reports['area_a']['possible_outdoor_paths'],['area_b'])
        self.assertIn('fresh_air_needed',[n['code'] for n in reports['area_a']['advisories']])
        self.assertIn('door_context',self.env['area_a'])
        self.assertEqual(self.env['area_a']['climate_plan'],{'sleeping':False})
    def test_contact_only_deadline_uses_existing_tick(self):
        hass.states['binary_sensor.door_a']=state('binary_sensor.door_a','off','door',age=30)
        reports,_=self.update()
        self.assertEqual(reports['area_a']['boundary'],'settling')
        self.assertFalse(self.monitor.should_refresh(now.timestamp()+89))
        self.assertTrue(self.monitor.should_refresh(now.timestamp()+90))
        reports,_=self.update(90)
        self.assertEqual(reports['area_a']['boundary'],'closed')
        self.assertFalse(self.monitor.should_refresh(now.timestamp()+91))
    def test_removing_doors_discards_context_history_and_event_membership(self):
        self.update();self.update(60)
        self.assertTrue(self.monitor._sessions)
        self.cfg['climate_rooms']['area_a']['door_sensors']=[]
        self.update(120)
        self.assertFalse(self.monitor._sessions)
        self.assertFalse(self.monitor._members)
        self.assertFalse(self.monitor._links)
        self.assertNotIn('door_context',self.env['area_a'])
    def test_measurement_source_change_does_not_mix_thermal_samples(self):
        reports,_=self.update()
        self.update(60)
        self.assertEqual(next(iter(self.monitor._links.values()))['open'].__len__(),2)
        self.cfg['room_sources']['area_a']['temperature']=['sensor.new_source']
        reports,_=self.update(120)
        self.assertEqual(len(self.monitor._links),1)
        self.assertEqual(len(next(iter(self.monitor._links.values()))['open']),1)
        self.assertEqual(reports['area_a']['session']['open_minutes'],0)
    def test_away_transition_is_a_hint_not_an_intrusion_or_occupancy_claim(self):
        self.update()
        old=state('binary_sensor.door_a','off','door')
        new=state('binary_sensor.door_a','on','door')
        self.monitor.state_changed(old.entity_id,old,new,now.timestamp()+1)
        reports,_=self.update(2,home='away')
        self.assertTrue(reports['area_a']['presence_recheck_hint'])
        self.assertEqual(reports['area_a']['occupancy'],'unoccupied')
        self.assertIn('door_activity_while_away',[n['code'] for n in reports['area_a']['advisories']])
        self.assertTrue(reports['area_a']['advisory_only'])

if __name__=='__main__':unittest.main(verbosity=2)

"""Door evidence, graph and configuration invariants without physical I/O."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from dataclasses import asdict, fields, FrozenInstanceError, replace
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
# Use the real production data model. A SimpleNamespace(available=True)
# previously hid the startup crash and the silently discarded measurements.
logic = load('logic', base['ROOT'] / 'logic.py')
Reading, Room, Window = logic.Reading, logic.Room, logic.Window


def production_block(filename, method, predicate):
    tree = ast.parse((base['ROOT'] / filename).read_text(encoding='utf-8'))
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == method]
    assert len(functions) == 1, (filename, method)
    chosen = [node for node in functions[0].body if predicate(node)]
    assert chosen, (filename, method, 'production block not found')
    return compile(ast.Module(body=chosen, type_ignores=[]), str(base['ROOT'] / filename), 'exec')


MANAGER_DOOR_BLOCK = production_block('manager.py', '_capture', lambda node:
    isinstance(node, ast.For) and isinstance(node.target, ast.Name)
    and node.target.id == 'monitored')
CLIMATE_CO2_BLOCK = production_block('climate_rooms.py', 'gather', lambda node:
    isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
    and target.id == 'co2_values' for target in node.targets))


class ReadingContract(unittest.TestCase):
    def test_real_model_has_computed_availability(self):
        for value in (0, 0.0, 45, 55.5, 1400.0):
            with self.subTest(value=value):
                self.assertIs(Reading('sensor.a', 'A', 'humidity', value).available, True)
        for value in (None, True, False, float('nan'), float('inf'), -float('inf'),
                      '55', 'unavailable', [], 10 ** 1000):
            with self.subTest(value=repr(value)[:40]):
                self.assertIs(Reading('sensor.a', 'A', 'humidity', value).available, False)

    def test_constructor_serialization_and_immutability_remain_compatible(self):
        item = Reading('sensor.a', 'A', 'humidity', 55.0)
        self.assertEqual([field.name for field in fields(item)],
                         ['entity_id', 'name', 'metric', 'value', 'details'])
        self.assertEqual(asdict(item), {'entity_id': 'sensor.a', 'name': 'A',
                         'metric': 'humidity', 'value': 55.0, 'details': None})
        self.assertFalse(replace(item, value=None).available)
        self.assertTrue(replace(item, value=0.0).available)
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            item.available = True

    def test_discovery_produces_available_only_for_accepted_sensor_evidence(self):
        # Execute the genuine sensor normalization/freshness functions. Only
        # HA's state store, clock and registry boundaries are test fixtures.
        names = {'_device_class', 'is_pressure_sensor', '_metric', '_numeric',
                 '_normalize', 'supported_metric', 'is_stale', 'reading'}
        tree = ast.parse((base['ROOT'] / 'discovery.py').read_text())
        nodes = [node for node in tree.body if
                 isinstance(node, ast.FunctionDef) and node.name in names or
                 isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                    and target.id in ('DEVICE_CLASS_METRICS', 'SUFFIX_METRICS')
                    for target in node.targets)]
        constants = sys.modules[base['PACKAGE'] + '.const']
        namespace = dict(__name__=base['PACKAGE'] + '.discovery',
                         __package__=base['PACKAGE'],
                         Reading=Reading, timedelta=timedelta,
                         dt_util=N(utcnow=lambda: now), er=base['registry'],
                         INDOOR_METRICS=constants.INDOOR_METRICS,
                         SUPPORTED_AIR_METRICS=constants.SUPPORTED_AIR_METRICS)
        future = ast.parse('from __future__ import annotations').body
        exec(compile(ast.Module(body=future + nodes, type_ignores=[]),
                     'discovery.py', 'exec'), namespace)
        cases = [
            ('45', 'humidity', '%', {}, 1, 45.0),
            ('1400', 'co2', 'ppm', {}, 1, 1400.0),
            ('0', 'pm25', 'µg/m³', {}, 1, 0.0),
            ('45', 'humidity', '%', {}, 6000, None),
            ('45', 'humidity', '%', {'restored': True}, 1, None),
            ('unavailable', 'humidity', '%', {}, 1, None),
            ('unknown', 'co2', 'ppm', {}, 1, None),
            ('nan', 'humidity', '%', {}, 1, None),
            ('inf', 'co2', 'ppm', {}, 1, None),
            ('101', 'humidity', '%', {}, 1, None),
            ('100', 'co2', 'ppm', {}, 1, None),
            ('1400', 'co2', 'wrong_unit', {}, 1, None),
        ]
        for value, metric, unit, extra, age, expected in cases:
            with self.subTest(value=value, metric=metric, extra=extra, age=age):
                native = N(entity_id='sensor.contract_' + metric, name='Measured',
                           domain='sensor', state=value,
                           attributes={'device_class': metric, 'unit_of_measurement': unit, **extra},
                           last_updated=now - timedelta(seconds=age))
                local_hass = N(states=N(get=lambda eid: native))
                result = namespace['reading'](local_hass, native.entity_id, 10, outdoor=False)
                self.assertIs(type(result), Reading)
                self.assertEqual(result.value, expected)
                self.assertIs(result.available, expected is not None)
        missing = namespace['reading'](N(states=N(get=lambda eid: None)), 'sensor.missing', 10,
                                       outdoor=False)
        self.assertIsNone(missing.value)
        self.assertFalse(missing.available)


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
        self.rooms=[Room(area_id='area_a',name='A',readings=(
                Reading('sensor.a_humidity','A humidity','humidity',60),
                Reading('sensor.a_co2','A CO2','co2',1400)),windows=()),
            Room(area_id='area_b',name='B',
                 readings=(Reading('sensor.b_humidity','B humidity','humidity',40),),
                 windows=(Window('binary_sensor.b_window','B window',True),))]
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
    def capture_doors(self):
        manager = N(hass=hass, _tracked=set())
        namespace = dict(self=manager, raw_rooms=self.rooms, config=self.cfg,
                         room_climate_configs=self.cfg['climate_rooms'],
                         room_temperature_evidence=sources.room_temperature_evidence,
                         observed_rooms=self.presence, home_status='home',
                         environment=self.env, observe_room_door=door.observe)
        # This is the exact _capture loop from the user's traceback, not a
        # reimplementation of its filtering/aggregation or a fake Reading.
        exec(MANAGER_DOOR_BLOCK, namespace)
        self.assertEqual(manager._tracked, {'binary_sensor.door_a'})
        return self.env['area_a']['door']

    def test_initial_manager_capture_with_real_readings(self):
        report = self.capture_doors()
        self.assertEqual(report['humidity_rh'], 60)
        self.assertEqual(report['co2_ppm'], 1400)
        self.assertFalse(report['eco_active'])  # Overview cannot authorize Eco.
        repeated = self.capture_doors()  # Contact age may advance between calls.
        for key in ('humidity_rh', 'co2_ppm', 'boundary', 'eco_active'):
            self.assertEqual(repeated[key], report[key])

    def test_manager_capture_rejects_unavailable_and_nonfinite_values(self):
        invalid = (None, float('nan'), float('inf'), True, '65')
        extra = tuple(Reading('sensor.bad_' + str(i), 'Bad', metric, value)
                      for metric in ('humidity', 'co2')
                      for i, value in enumerate(invalid))
        self.rooms[0] = replace(self.rooms[0], readings=self.rooms[0].readings + extra)
        self.assertEqual(self.capture_doors()['humidity_rh'], 60)
        self.assertEqual(self.capture_doors()['co2_ppm'], 1400)
        self.rooms[0] = replace(self.rooms[0], readings=extra)
        report = self.capture_doors()
        self.assertIsNone(report['humidity_rh'])
        self.assertIsNone(report['co2_ppm'])
        reports, _ = self.update()
        self.assertIsNone(reports['area_a']['measurements']['humidity_rh'])
        self.assertIsNone(reports['area_a']['measurements']['co2_ppm'])
        self.assertNotIn('fresh_air_needed', [n['code'] for n in reports['area_a']['advisories']])

    def test_climate_co2_aggregation_accepts_real_readings_not_mock_flags(self):
        finite = load('pid_math', base['ROOT'] / 'pid_math.py').finite
        namespace = {'room': self.rooms[0], 'finite': finite}
        exec(CLIMATE_CO2_BLOCK, namespace)
        self.assertEqual(namespace['co2_values'], [1400.0])
        namespace['room'] = replace(self.rooms[0], readings=(
            Reading('sensor.missing', 'Missing', 'co2', None),
            Reading('sensor.nan', 'Invalid', 'co2', float('nan'))))
        exec(CLIMATE_CO2_BLOCK, namespace)
        self.assertEqual(namespace['co2_values'], [])

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

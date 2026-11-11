"""Bounded door coordination and measured energy; no physical devices or HA I/O."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import importlib.util
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'custom_components/environment_manager'
PACKAGE = 'hem_b5_fixture'
pkg = ModuleType(PACKAGE); pkg.__path__ = [str(SOURCE)]; sys.modules[PACKAGE] = pkg


def load(name):
    spec = importlib.util.spec_from_file_location(PACKAGE+'.'+name, SOURCE/(name+'.py'))
    module = importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module);return module


def boundary(name, **attributes):
    module = ModuleType(PACKAGE+'.'+name);module.__dict__.update(attributes)
    sys.modules[module.__name__] = module;return module


coord = load('door_coordination');energy = load('door_energy')
doors = load('room_doors');load('building_physics')
NOW = 100000.0

def native(entity, value, *, at=NOW, changed=None, **attributes):
    return N(entity_id=entity, domain=entity.partition('.')[0], state=value, attributes=attributes,
             name=entity, last_updated=datetime.fromtimestamp(at,timezone.utc),
             last_reported=datetime.fromtimestamp(at,timezone.utc),
             last_changed=datetime.fromtimestamp(changed if changed is not None else at-600,timezone.utc))


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.budget=coord.StartBudget();self.now=NOW
        self.candidate={'kind':'shared','peer':'climate.peer','contact':'binary_sensor.door','minimum_progress':0.1}
    def decide(self, elapsed=0, value=20, candidate=True, signature='sources'):
        return self.budget.decide('a','physical-off',NOW+elapsed,
            self.candidate if candidate else None,value,signature,'room')
    def test_unimproved_wait_releases_at_60_seconds(self):
        self.assertIsNotNone(self.decide());self.assertIsNotNone(self.decide(59))
        self.assertIsNone(self.decide(60))
        self.assertIsNone(self.decide(61,value=21))
    def test_progress_never_extends_absolute_180_second_budget(self):
        self.assertIsNotNone(self.decide())
        self.assertIsNotNone(self.decide(60,value=20.2))
        self.assertIsNotNone(self.decide(120,value=20.4))
        self.assertIsNone(self.decide(180,value=20.6))
        self.assertIsNone(self.decide(900,value=21))
    def test_contact_flapping_or_lost_evidence_cannot_renew_wait(self):
        self.decide();self.assertIsNone(self.decide(10,candidate=False))
        self.assertIsNone(self.decide(20));self.assertIsNone(self.decide(200))
    def test_changed_sources_release_not_restart(self):
        self.decide();self.assertIsNone(self.decide(20,signature='new source'))
        self.assertIsNone(self.decide(30,signature='new source'))
    def test_peer_change_keeps_original_deadline(self):
        self.decide();self.candidate['peer']='climate.other'
        self.assertEqual(self.decide(20)['deadline'],NOW+180)
    def test_conflict_wait_is_bounded_without_progress_requirement(self):
        self.candidate['kind']='conflicts';self.decide()
        self.assertIsNotNone(self.decide(60));self.assertIsNone(self.decide(180))
    def test_clock_reversal_releases_optional_hold(self):
        self.decide();self.assertIsNone(self.decide(-1));self.assertIsNone(self.decide(1))
    def test_capacity_is_bounded_and_never_grants_more_delay_by_eviction(self):
        for index in range(coord.MAX_EPISODES+20):
            self.budget.decide(str(index),'off',NOW,self.candidate,20,'source','room')
        self.assertEqual(len(self.budget.records),coord.MAX_EPISODES)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.states={'climate.local':native('climate.local','off'),
                     'climate.peer':native('climate.peer','heat',hvac_action='heating'),
                     'binary_sensor.door':native('binary_sensor.door','on',device_class='door')}
        self.areas={entity:('b' if entity=='climate.peer' else 'a') for entity in self.states}
        self.states_store=N(get=self.states.get,async_all=lambda domain=None:[v for v in self.states.values()
                            if domain is None or v.domain==domain])
        self.hass=N(states=self.states_store)
        self.cfg={'control_mode':'automatic','preset':'none'}
        self.peer_cfg=dict(self.cfg)
        self.plan={'away':'home','sleeping':False,'arrival_preparing':False}
        self.settings={'climate_rooms':{'a':{'door_sensors':['binary_sensor.door'],
            'door_settings':{'binary_sensor.door':{'kind':'interior','target_area':'b','coordination':'shared'}}},'b':{}}}
        self.local=N(identifier='local',area_id='a',source_device_id='physical-a',source_entities=('climate.local',))
        self.peer=N(identifier='peer',area_id='b',source_device_id='physical-b',source_entities=('climate.peer',))
        self.cap=N(primary='climate.local',domain='climate',humidity=False)
        self.peer_cap=N(primary='climate.peer',domain='climate',humidity=False)
        self.values={'a':{'temperature':20.,'humidity':45.,'pm25':20},
                     'b':{'temperature':22.,'humidity':40.,'pm25':8}}
        self.targets={'heat':21.,'cool':25.,'humidity':50.}
        self.manager=N(hass=self.hass,settings=self.settings,entry=N(entry_id='entry'))
        self.now=NOW
        self.runtime=N(hass=self.hass,manager=self.manager,clock=lambda:self.now,records={'peer':{'power':{'climate.peer':{'since':NOW-1000}}}},
                       measurements=lambda spec,cap:dict(self.values[spec.area_id]))
        self.model=boundary('equipment_model',capabilities=lambda m,s:self.peer_cap,
            settings=lambda m,s:self.peer_cfg if s.identifier=='peer' else self.cfg,
            plan_for=lambda m,s:dict(self.plan),permission=lambda *args:(True,True),
            targets=lambda *args:dict(self.targets),humidity_demand=lambda *args:{})
        boundary('door_settings',inventory=lambda *args:iter([('a','binary_sensor.door')]),
                 target_areas=lambda *args:{'b':'Bedroom'})
        boundary('device_hierarchy',managed_devices=lambda *args:(self.local,self.peer))
        boundary('discovery',entity_area=lambda h,e:self.areas.get(e),
                 _device_class=lambda h,s:s.attributes.get('device_class',''))
        boundary('room_sources',native=lambda h,e:True,label=lambda h,e:e)
        boundary('door_context',_source_signature=lambda *args:('sensors',))
    def call(self,**kwargs):
        return coord.start_hold(self.runtime,self.local,self.cap,self.cfg,self.plan,'heat',**kwargs)
    def test_observe_is_noop_and_shared_requires_verified_active_peer(self):
        self.settings['climate_rooms']['a']['door_settings']['binary_sensor.door']['coordination']='observe'
        self.assertIsNone(self.call())
        self.assertFalse(hasattr(self.runtime,'_door_start_budget'))
        self.settings['climate_rooms']['a']['door_settings']['binary_sensor.door']['coordination']='shared'
        self.assertIsNotNone(self.call())
        self.states['climate.peer'].attributes['hvac_action']='idle'
        self.assertIsNone(self.call())
    def test_manual_pid_sleep_away_arrival_and_explicit_preset_bypass(self):
        for where,key,value in [(self.cfg,'control_mode','manual'),(self.cfg,'control_mode','pid'),
                (self.cfg,'preset','comfort'),(self.plan,'sleeping',True),(self.plan,'sleeping',None),
                (self.plan,'away','away'),(self.plan,'arrival_preparing',True)]:
            original=where.get(key);where[key]=value
            self.assertIsNone(self.call(),(key,value));where[key]=original
        self.assertIsNone(self.call(automatic=False));self.assertIsNone(self.call(power=False))
    def test_closed_moved_restored_fire_and_exterior_never_defer(self):
        for key,value in [('kind','fire'),('kind','exterior')]:
            item=self.settings['climate_rooms']['a']['door_settings']['binary_sensor.door']
            item[key]=value;self.assertIsNone(self.call());item[key]='interior'
        door=self.states['binary_sensor.door']
        for value in ('off','unknown','unavailable'):
            door.state=value;self.assertIsNone(self.call())
        door.state='on';door.attributes['restored']=True;self.assertIsNone(self.call())
        door.attributes['restored']=False;self.areas[door.entity_id]='b';self.assertIsNone(self.call())
    def test_fresh_open_contact_needs_stability(self):
        self.states['binary_sensor.door'].last_changed=datetime.fromtimestamp(NOW-5,timezone.utc)
        self.assertIsNone(self.call());self.now+=30;self.assertIsNotNone(self.call())
    def test_local_urgent_or_missing_measurements_bypass(self):
        for temp in (None,15.,17.,28.,30.,float('nan')):
            self.values['a']['temperature']=temp;self.assertIsNone(self.call(),temp)
    def test_loss_does_not_renew_even_after_reconnection_off_timestamp(self):
        self.assertIsNotNone(self.call());self.values['a']['temperature']=None
        self.assertIsNone(self.call());self.now+=10;self.values['a']['temperature']=20
        self.states['climate.local'].last_changed=datetime.fromtimestamp(self.now,timezone.utc)
        self.assertIsNone(self.call())
    def test_peer_override_paused_or_pending_cancels(self):
        self.assertIsNotNone(self.call());self.peer_cfg['control_mode']='manual'
        self.assertIsNone(self.call())
        for record in ({'paused':'manual'},{'pending':{'service':'turn_on'}}):
            self.runtime._door_start_budget=coord.StartBudget();self.peer_cfg['control_mode']='automatic'
            self.runtime.records['peer']=record;self.assertIsNone(self.call())
    def test_opposing_thermal_output_waits_but_same_mode_needs_gradient(self):
        self.states['climate.peer'].state='cool'
        self.states['climate.peer'].attributes['hvac_action']='cooling'
        self.assertEqual(self.call()['reason'],'door_conflicts_start_wait')
        self.runtime._door_start_budget=coord.StartBudget()
        self.states['climate.peer'].state='heat';self.states['climate.peer'].attributes['hvac_action']='heating';self.values['b']['temperature']=19
        self.assertIsNone(self.call())
    def test_humidity_coordination_uses_absolute_moisture_and_urgent_guard(self):
        self.cap.domain=self.peer_cap.domain='humidifier'
        self.cap.humidifying=self.peer_cap.humidifying=False
        self.cap.humidity=self.peer_cap.humidity=True
        self.states['climate.peer'].state='on'
        self.values['a'].update(temperature=22,humidity=55)
        self.values['b'].update(temperature=22,humidity=40)
        result=coord.start_hold(self.runtime,self.local,self.cap,self.cfg,self.plan,'dry')
        self.assertIsNotNone(result)
        self.values['a']['humidity']=70
        self.assertIsNone(coord.start_hold(self.runtime,self.local,self.cap,self.cfg,self.plan,'dry'))
    def test_mold_protection_bypasses_optional_delay(self):
        self.cap.humidity=True
        self.model.humidity_demand=lambda *a:{'mold_protection_required':True}
        self.assertIsNone(self.call())
    def test_generic_and_extraction_fans_never_delay_ventilation(self):
        self.cap.domain='fan';self.peer_cap.domain='fan';self.states['climate.peer'].state='on'
        for purpose in ('auto','extraction'):
            self.cfg['fan_purpose']=purpose
            self.assertIsNone(coord.start_hold(self.runtime,self.local,self.cap,self.cfg,self.plan,'fan_only'))
        self.cfg['fan_purpose']=self.peer_cfg['fan_purpose']='filtration'
        self.assertIsNotNone(coord.start_hold(self.runtime,self.local,self.cap,self.cfg,self.plan,'fan_only'))
    def test_unowned_peer_or_inconsistent_hvac_action_is_not_active_evidence(self):
        self.runtime.records.clear();self.assertIsNone(self.call())
        self.runtime.records['peer']={'power':{'climate.peer':{'since':NOW-1000}}}
        self.states['climate.peer'].state='cool'
        self.assertIsNone(self.call())
    def test_targets_and_config_are_never_mutated(self):
        old=deepcopy((self.settings,self.cfg,self.plan,self.targets));self.call()
        self.assertEqual(old,(self.settings,self.cfg,self.plan,self.targets))


class EnergyTests(unittest.TestCase):
    def setUp(self):
        self.monitor=energy.DoorEnergyMonitor()
    def observe(self,t,value,mode='closed',changed=1,**extra):
        reading={'at':t,'value':value,'unit':'kWh','reset':'','state_class':'total_increasing',**extra}
        return self.monitor.observe('door','meter',reading,mode,changed,t)
    def test_measured_consumption_coverage_and_mean_power(self):
        self.observe(1000,10);result=self.observe(1060,10.01)
        self.assertEqual(result['closed']['kwh'],.01)
        self.assertEqual(result['closed']['observed_minutes'],1)
        self.assertEqual(result['closed']['mean_power_w'],600)
        self.assertIsNone(result['savings_estimate']);self.assertFalse(result['comparison_ready'])
        self.assertEqual(self.observe(1060,10.01)['closed'],result['closed'])
    def test_reset_gap_clock_reverse_and_unit_change_are_excluded(self):
        for t,value,extra in [(1060,0,{}),(1500,10.1,{}),(900,10,{}),(1060,10.1,{'unit':'Wh'}),
                              (1060,10.1,{'reset':'new cycle'}),(1060,1000,{})]:
            self.monitor=energy.DoorEnergyMonitor();self.observe(1000,10)
            result=self.observe(t,value,**extra)
            self.assertEqual(result['closed']['kwh'],0)
            self.assertEqual(result['excluded_intervals'],1)
    def test_contact_chatter_and_missing_samples_do_not_fill_gaps(self):
        self.observe(1000,10)
        self.assertEqual(self.observe(1060,10.1,changed=1030)['excluded_intervals'],1)
        self.monitor.observe('door','meter',None,'closed',1030,1080)
        result=self.observe(1120,10.2,changed=1030)
        self.assertEqual(result['closed']['kwh'],0)
    def test_ready_needs_15_minutes_in_each_state(self):
        for i in range(17):result=self.observe(1000+60*i,10+.01*i)
        self.assertFalse(result['comparison_ready'])
        for i in range(17):result=self.observe(2020+60*i,10.2+.01*i,'open',2000)
        self.assertTrue(result['comparison_ready'])
    def test_changed_meter_resets_and_records_are_bounded(self):
        self.observe(1000,10);self.observe(1060,10.1)
        result=self.monitor.observe('door','new meter',None,'closed',1,1100)
        self.assertEqual(result['closed']['kwh'],0)
        for i in range(200):self.monitor.observe(str(i),'meter',None,'closed',1,1100)
        self.assertEqual(len(self.monitor.records),energy.MAX_CONTACTS)
    def test_meter_adapter_checks_area_units_and_restored_evidence(self):
        state=native('sensor.energy','1234',device_class='energy',state_class='total_increasing',unit_of_measurement='Wh')
        area=['a'];hass=N(states=N(get=lambda eid:state,async_all=lambda *args:[state]))
        boundary('discovery',entity_area=lambda h,e:area[0]);boundary('room_sources',native=lambda *args:True,label=lambda *args:'Energy')
        self.assertEqual(energy.sample(hass,'a','sensor.energy',NOW)['value'],1.234)
        area[0]='b';self.assertIsNone(energy.sample(hass,'a','sensor.energy',NOW));area[0]='a'
        state.attributes['restored']=True;self.assertIsNone(energy.sample(hass,'a','sensor.energy',NOW))
        state.attributes['restored']=False;state.attributes['unit_of_measurement']='W'
        self.assertIsNone(energy.sample(hass,'a','sensor.energy',NOW))
        state.attributes['unit_of_measurement']='kWh';state.last_reported=datetime.fromtimestamp(NOW-400,timezone.utc)
        self.assertIsNone(energy.sample(hass,'a','sensor.energy',NOW))


# Execute the actual production _send/_power/tick and rechecks from the existing
# deterministic runtime fixture. Only the coordinator response and HA transport
# boundary are controlled here; engine evidence is exercised separately above.
b=runpy.run_path(str(ROOT/'.github/tests/test_onoff_native_extrema.py'))
Runtime,SPEC,PRIMARY=b['NativeRuntime'],b['SPEC'],b['PRIMARY']
bridge=ModuleType(b['PACKAGE']+'.door_coordination')
sys.modules[bridge.__name__]=bridge
class DispatchTests(unittest.IsolatedAsyncioTestCase):
    def setup_runtime(self):
        r=Runtime('automatic','heat');r.manager.settings['climate_rooms']={'room':{
            'door_settings':{'binary_sensor.door':{'coordination':'shared'}}}}
        return r
    async def test_hold_prevents_any_journal_or_physical_command(self):
        r=self.setup_runtime();bridge.start_hold=lambda *a,**kw:{'reason':'door_shared_start_wait','remaining_seconds':60}
        await r.tick(SPEC)
        self.assertEqual(r.calls,[]);self.assertIsNone(r.record['pending'])
        self.assertEqual(r.statuses[-1][1]['reason'],'door_shared_start_wait')
    async def test_new_conflict_after_persistence_cancels_before_dispatch(self):
        r=self.setup_runtime();calls=[]
        def response(*args,**kwargs):
            calls.append(1)
            return None if len(calls)==1 else {'reason':'door_conflicts_start_wait'}
        bridge.start_hold=response
        await r.tick(SPEC)
        self.assertGreaterEqual(len(calls),2);self.assertEqual(r.calls,[])
        self.assertIsNone(r.record['pending'])
    async def test_released_hold_uses_unchanged_native_command(self):
        r=self.setup_runtime();bridge.start_hold=lambda *a,**kw:None
        await r.tick(SPEC)
        self.assertEqual(r.calls[-1],{'domain':'climate','service':'set_hvac_mode',
            'data':{'hvac_mode':'heat'},'target':{'entity_id':PRIMARY}})
    async def test_stop_does_not_consult_door_start_gate(self):
        r=self.setup_runtime();r.own_running(age=1200)
        bridge.start_hold=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('OFF must never wait for a door'))
        cap=b['model'].capabilities(r.manager,SPEC)
        await r._power(SPEC,cap,'off',automatic=False,shutdown=True)
        self.assertEqual(r.calls[-1]['data'],{'hvac_mode':'off'})


if __name__=='__main__':unittest.main(verbosity=2)

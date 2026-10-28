"""Actual-source AQI startup, late registration, overrides and bounded-load tests.

HA registries and entity interfaces are simulated; this is not a full HA or
physical-hardware certification. Any global registry scan or service call fails.
"""
from __future__ import annotations
import ast
import asyncio
import importlib
import json
import math
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace as N
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
pkg=ModuleType('hem67');pkg.__path__=[str(ROOT)];sys.modules['hem67']=pkg


def module(name, **values):
    obj=ModuleType(name);obj.__dict__.update(values);sys.modules[name]=obj
    return obj


class Registry:
    def __init__(self): self.items={};self.calls=0
    def async_get(self, key): self.calls+=1;return self.items.get(key)
    @property
    def entities(self): raise AssertionError('Unbounded registry enumeration')


class States:
    def __init__(self): self.items={}
    def get(self, key): return self.items.get(key)
    def async_all(self, *args): raise AssertionError('Global state scan')


registry=Registry();states=States();listeners=[];services=[]
def track(hass, ids, callback):
    item=(frozenset(ids),callback);listeners.append(item)
    return lambda:listeners.remove(item)

def event(entity):
    for ids, callback in tuple(listeners):
        if entity in ids: callback(N(data={'entity_id':entity}))

module('homeassistant',__path__=[])
module('homeassistant.core',callback=lambda f:f)
module('homeassistant.helpers',__path__=[])
module('homeassistant.helpers.entity_registry',async_get=lambda hass:registry)
module('homeassistant.helpers.event',async_track_state_change_event=track)
module('homeassistant.helpers.dispatcher',async_dispatcher_connect=lambda *args:lambda:None)
module('hem67.room_hubs',async_add_grouped_entities=lambda manager,add,items:add(list(items)))

def no_service(*args,**kwargs): raise AssertionError('AQI settings must not operate hardware')
hass=N(states=states,services=N(async_call=no_service),config=N(language='el'))
manager=N(hass=hass,settings={'outdoor_sensors':[]},_active=False)
source=importlib.import_module('hem67.aqi_sources')
science=importlib.import_module('hem67.environment_science')
logic=importlib.import_module('hem67.logic')
const=importlib.import_module('hem67.const')
dash=importlib.import_module('hem67.dashboard')


def extract(filename,names,env):
    tree=ast.parse((ROOT/filename).read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names),(filename,names)
    env.update(__name__='hem67.probe',__package__='hem67')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),env)
    return tuple(env[n] for n in names)


(global_aqi,)=extract('environment_extended.py',('global_aqi',),{'Any':Any,'aqi_category':science.aqi_category})
# Stored choice is authoritative, provider does not override the user's choice.
eid='sensor.heinrich_heine_strasse_air_quality_index'
registry.items[eid]=N(platform='waqi',original_device_class='aqi',device_class=None,name=None,original_name='Wesseling AQI')
manager.settings={'outdoor_sensors':[eid]}
assert states.get(eid) is None
assert source.configured_sources(hass,manager.settings)==(eid,)
assert source.resolve_scale(hass,{},eid)=={'scale':'us_epa','scale_source':'provider:waqi'}
assert source.source_name(hass,eid)=='Wesseling AQI'
reading=logic.Reading(eid,'Wesseling AQI','aqi',27)
actual=global_aqi(reading,{},hass=hass)
assert actual['status']=='ready' and actual['scale']=='us_epa' and actual['category']=='good'
assert actual['scale_source']=='provider:waqi'
assert not actual['operational_unsafe']
for selection in ('eea_category','custom','not_configured'):
    profile={'aqi_scales':{eid:{'scale':selection,'custom_limit':20}}}
    evidence=source.resolve_scale(hass,profile,eid)
    assert evidence['scale']==selection and evidence['scale_source']=='manual'
    classified=global_aqi(reading,profile,hass=hass)
    if selection=='custom': assert classified['operational_unsafe']
    if selection=='eea_category': assert classified['status']=='invalid'
    if selection=='not_configured': assert classified['status']=='configuration_required'
assert global_aqi(reading,{'aqi_scales':{eid:'us_epa'}})['status']=='ready'
for malicious in ('sensor.germany_aqi','sensor.us_epa_air_quality_index'):
    registry.items[malicious]=N(platform='template',original_device_class='aqi')
    states.items[malicious]=N(name='WAQI US EPA',state='27',attributes={'device_class':'aqi','provider':'waqi'})
    assert source.resolve_scale(hass,{},malicious)['scale']=='not_configured'
# A genuine WAQI concentration, not its AQ index, is never assigned an AQI scale.
registry.items['sensor.pm25']=N(platform='waqi',original_device_class='pm25')
assert source.resolve_scale(hass,{},'sensor.pm25')['scale']=='not_configured'
# Renamed source uses registry metadata, not an entity-ID suffix guess.
registry.items['sensor.renamed']=N(platform='waqi',original_device_class='aqi',original_name='Station')
assert source.configured_sources(hass,{'outdoor_sensors':['sensor.renamed']})==('sensor.renamed',)
assert source.configured_sources(hass,{'outdoor_sensors':[None,[],23,'light.bad',eid,eid]})==(eid,)
# Missing registry entry can still recreate an already configured source control.
assert source.configured_sources(hass,{'outdoor_sensors':['sensor.missing_aqi']})==('sensor.missing_aqi',)

# Exact old entity IDs/unique IDs remain stable. Pure configuration is available
# while native WAQI is absent; a numeric source being offline is not a UI lock.
class Base:
    hass=None
    @property
    def available(self): return True
    @property
    def name(self): return getattr(self,'_attr_name',None)
    @property
    def extra_state_attributes(self): return None
    @property
    def unique_id(self): return self._attr_unique_id
    def async_write_ha_state(self): self.writes=getattr(self,'writes',0)+1
    def async_on_remove(self,f): pass
    async def async_added_to_hass(self): pass

common={'SelectEntity':Base,'NumberEntity':Base,'NumberMode':N(BOX='box'),
        'EntityCategory':N(CONFIG='config'),'callback':lambda f:f,
        'DOMAIN':'environment_manager','SIGNAL_UPDATED':'hem_update'}
(Select,)=extract('select.py',('ConfigSelect',),dict(common))
(Number,)=extract('number.py',('ConfigNumber',),dict(common))
s=Select(manager,'entry',None,'aqi_scale',source.AQI_SCALES,setting_key='scale',entity_id=eid)
n=Number(manager,'entry',None,'aqi_limit','custom_limit',(0.,10000.,1.,None),entity_id=eid)
assert s.unique_id=='entry_home_aqi_scale_sensor_heinrich_heine_strasse_air_quality_index_scale'
assert n.unique_id=='entry_home_aqi_limit_sensor_heinrich_heine_strasse_air_quality_index_custom_limit'
assert s.available and n.available and s.current_option=='auto'
assert s.extra_state_attributes['scale']=='us_epa'
assert 'Κλίμακα AQI' in s.name and 'Wesseling' in s.name
assert 'Προσαρμοσμένο όριο AQI' in n.name
assert n.native_value==100
assert s._attr_translation_key=='home_aqi_scale'

# Late metadata is added exactly once. Unrelated state updates do not reach
# either new scoped listener, and repeated numeric AQI updates write no entities.
manager.settings={'outdoor_sensors':[eid,'sensor.late']}
added=[];unloads=[];entry=N(async_on_unload=unloads.append)
source.register_late_sources(manager,entry,added.extend,[s],lambda source_id:
    Select(manager,'entry',None,'aqi_scale',source.AQI_SCALES,setting_key='scale',entity_id=source_id))
source.register_late_sources(manager,entry,added.extend,[n],lambda source_id:
    Number(manager,'entry',None,'aqi_limit','custom_limit',(0.,10000.,1.,None),entity_id=source_id))
assert len(listeners)==2
for i in range(10000): event('sensor.unrelated_'+str(i))
assert not added
states.items['sensor.late']=N(state='unknown',name='Late AQI',attributes={'device_class':'aqi'})
registry.items['sensor.late']=N(platform='waqi',original_device_class='aqi')
event('sensor.late');assert len(added)==2
for i in range(100): event('sensor.late')
assert len(added)==2
s.hass=hass;n.hass=hass
states.items[eid]=N(state='27',name='Wesseling AQI',attributes={'device_class':'aqi'})
start=time.perf_counter()
for i in range(10000):
    states.items[eid].state=str(i%100)
    event(eid)
elapsed=time.perf_counter()-start
assert len(added)==2 and not getattr(s,'writes',0) and not getattr(n,'writes',0)
assert elapsed<3,elapsed
states.items[eid].name='Wesseling renamed'
event(eid)
assert s.writes==1 and n.writes==1
for unsubscribe in unloads: unsubscribe()
assert not listeners

# Real data logic: AQI no longer yields a scale blocker for actual WAQI.
normalized=logic.Reading(eid,'Wesseling AQI','aqi',27,{'aqi':actual})
weather=(logic.Weather('weather.home','partlycloudy',10.,60.,6.),)
plan=logic.evaluate((normalized,),weather,(),(),const.DEFAULT_THRESHOLDS)
assert not any(r.code=='aqi_scale_unconfigured' for r in plan.outside_reasons)
assert plan.outdoor_safe
result=dash.dashboard_snapshot(plan,const.DEFAULT_THRESHOLDS)
assert result['outdoor']['status']=='safe',result['outdoor']
# An unidentified provider remains explicitly unconfigured; no false green.
other=logic.Reading('sensor.us_epa_air_quality_index','Unknown','aqi',27)
no_scale=global_aqi(other,{},hass=hass)
other=logic.Reading(other.entity_id,other.name,'aqi',27,{'aqi':no_scale})
assert not logic.evaluate((other,),weather,(),(),const.DEFAULT_THRESHOLDS).outdoor_safe

# Actual options writer: overrides and auto survive updates while source absent.
class HAError(Exception): pass
from copy import deepcopy
writer_env={'Any':Any,'asyncio':asyncio,'deepcopy':deepcopy,'math':math,'HomeAssistantError':HAError,
            'AQI_SCALES':source.AQI_SCALES,'configured_aqi_entities':lambda manager:source.configured_sources(manager.hass,manager.settings)}
for name in dir(const):
    if name.isupper(): writer_env[name]=getattr(const,name)
(finite,update)=extract('device_controls.py',('_finite','update_device_setting'),writer_env)
writer_env['_finite']=finite
manager.entry=N(data={},options={})
def save_entry(entry,*,options): entry.options=options;manager.settings={**manager.settings,**options}
hass.config_entries=N(async_update_entry=save_entry)
async def writes():
    states.items.pop(eid,None)
    await update(manager,'aqi_scale','scale','custom',entity_id=eid)
    await update(manager,'aqi_limit','custom_limit',42,entity_id=eid)
    assert source.resolve_scale(hass,manager.settings['environment_global'],eid)['custom_limit']==42
    await update(manager,'aqi_scale','scale','not_configured',entity_id=eid)
    assert source.resolve_scale(hass,manager.settings['environment_global'],eid)['scale']=='not_configured'
    await update(manager,'aqi_scale','scale','auto',entity_id=eid)
    assert source.resolve_scale(hass,manager.settings['environment_global'],eid)['scale']=='us_epa'
asyncio.run(writes())

# Reachable options page and complete localized dropdown values.
options=(ROOT/'compact_options.py').read_text()
assert 'menu_options=["weather", "outdoor", "outside_aqi", "pollen"]' in options
assert 'aqis = list(configured_sources(self.hass, self._values))' in options
for path in (ROOT/'translations').glob('*.json'):
    data=json.loads(path.read_text())
    assert set(data['entity']['select']['home_aqi_scale']['state'])==set(source.AQI_SCALES)
print(f'PASS Beta67: offline/reordered AQI startup; exact preserved IDs; late registration once; WAQI provenance; overrides/unknown/custom; actual outdoor classification; 38 locales; 10k scoped updates in {elapsed:.3f}s; zero hardware commands')

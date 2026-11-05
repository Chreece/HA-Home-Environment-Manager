"""Beta65 unit/logic regressions with actual source and lightweight HA registries."""
import ast
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
from datetime import datetime, timezone, timedelta
from typing import Any
ROOT=Path(__file__).resolve().parents[2]
pkg=ModuleType('hem65test');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
logic=importlib.import_module('hem65test.logic');constants=importlib.import_module('hem65test.const')
dash=importlib.import_module('hem65test.dashboard')
W=logic.Warning;R=logic.Reading
outside=(R('sensor.pm','PM','pm25',4),)
weather=(logic.Weather('weather.home','partlycloudy',12.7,60,11),)
room=logic.Room('room','Room',(logic.Window('binary_sensor.window','Window',False),),(R('sensor.rh','RH','humidity',58.8),))
base=logic.evaluate(outside,weather,(),(room,),constants.DEFAULT_THRESHOLDS)
assert base.outdoor_safe
for label in ('unknown','unavailable','missing','null'):
 p=logic.evaluate(outside,weather,(W('sensor.alert',label,None),),(room,),constants.DEFAULT_THRESHOLDS)
 assert p.outdoor_safe and p.status==base.status and p.outside_reasons==base.outside_reasons
 d=dash.dashboard_snapshot(p,constants.DEFAULT_THRESHOLDS)
 assert d['outdoor']['status']=='safe' and not d['outdoor']['warnings']
 assert d['outdoor']['ignored_warning_entities']==['sensor.alert']
p=logic.evaluate(outside,weather,(W('sensor.alert','Alert',True),W('sensor.unknown','missing',None)),(room,),constants.DEFAULT_THRESHOLDS)
assert not p.outdoor_safe and any(r.code=='active_warning' for r in p.outside_reasons)
assert dash.dashboard_snapshot(p,constants.DEFAULT_THRESHOLDS)['outdoor']['status']=='unsafe'
for weather_case in ((),(logic.Weather('weather.home','rainy',12,60,11),),(logic.Weather('weather.home',None),)):
 assert not logic.evaluate(outside,weather_case,(W('sensor.alert','Alert',None),),(room,),constants.DEFAULT_THRESHOLDS).outdoor_safe

ha=ModuleType('homeassistant');ha.__path__=[]
core=ModuleType('homeassistant.core');core.HomeAssistant=object;core.State=object
helpers=ModuleType('homeassistant.helpers');helpers.__path__=[]
util=ModuleType('homeassistant.util');util.dt=N(utcnow=lambda:datetime.now(timezone.utc))
entities={};devices={}
registries={}
for name in ('area_registry','entity_registry','device_registry'):
 m=ModuleType('homeassistant.helpers.'+name)
 if name=='area_registry':reg=N(async_get_area=lambda a:N(name=a))
 else:
  values=entities if name=='entity_registry' else devices
  reg=N(async_get=values.get,entities=values)
 m.async_get=lambda h,reg=reg:reg;setattr(helpers,name,m);registries[m.__name__]=m
sys.modules.update({'homeassistant':ha,'homeassistant.core':core,'homeassistant.helpers':helpers,'homeassistant.util':util,**registries})
dis=importlib.import_module('hem65test.discovery')
now=datetime.now(timezone.utc)
def state(entity,value,unit='',kind=None,age=0):
 return N(entity_id=entity,name=entity,domain=entity.split('.')[0],state=str(value),attributes={'unit_of_measurement':unit,**({'device_class':kind} if kind else {})},last_updated=now-timedelta(minutes=age),last_reported=now-timedelta(minutes=age))
states={}
hass=N(states=N(get=states.get,async_all=lambda domain=None:[s for s in states.values() if domain is None or s.domain==domain]),config=N(time_zone='Europe/Berlin'))
for value,expected in [(123,123),(0,0),('unavailable',None),('unknown',None),(-1,None),('nan',None),(900000,None)]:
 s=state('sensor.light',value,'lx','illuminance');states[s.entity_id]=s
 assert dis.reading(hass,s.entity_id,90,outdoor=False).value==expected,(value,expected)
 assert dis.supported_metric(hass,s,outdoor=True) is None
for u in ('lx','lux',' LUX '):
 s=state('sensor.light',55,u,'illuminance');states[s.entity_id]=s
 assert dis.reading(hass,s.entity_id,90,outdoor=False).metric=='illuminance'
 assert dis.reading(hass,s.entity_id,90,outdoor=False).value==55
for u in ('%','W/m²','brightness'):
 s=state('sensor.light',55,u,'illuminance');states[s.entity_id]=s
 assert dis.supported_metric(hass,s,outdoor=False) is None
states['sensor.light']=state('sensor.light',99,'lx','illuminance',age=120)
assert dis.reading(hass,'sensor.light',90,outdoor=False).value is None
for v in ('unknown','unavailable',' Unavailable ','none','NULL',''):
 states['sensor.warning']=state('sensor.warning',v)
 assert dis.warning(hass,'sensor.warning',90).active is None
for v in ('red','severe','yellow','1'):
 states['sensor.warning']=state('sensor.warning',v)
 assert dis.warning(hass,'sensor.warning',90).active is True
for v in ('off','0','no warnings','clear'):
 states['sensor.warning']=state('sensor.warning',v)
 assert dis.warning(hass,'sensor.warning',90).active is False
# Real room inventory now preserves source identity, unit and zero lux.
for name,value in [('light_one',0),('light_two',300)]:
 eid='sensor.'+name;states[eid]=state(eid,value,'lx','illuminance')
 entities[eid]=N(entity_id=eid,area_id='room',device_id=None,platform='test',device_class=None,original_device_class=None)
selected={'room':{'air_quality':['sensor.light_one','sensor.light_two'],'humidity':[],'windows':[]}}
actual=dis.rooms(hass,['room'],90,source_selections=selected)[0]
assert [(r.entity_id,r.metric,r.value) for r in actual.readings]==[('sensor.light_one','illuminance',0),('sensor.light_two','illuminance',300)]
# A missing selected lux source retains the registry metric; it must not
# become a generic missing air-quality input.
saved_light=states.pop('sensor.light_one')
entities['sensor.light_one'].original_device_class='illuminance'
missing=dis.rooms(hass,['room'],90,source_selections=selected)[0]
assert missing.readings[0].metric=='illuminance' and missing.readings[0].value is None
states['sensor.light_one']=saved_light
# Lux cannot masquerade as AQ readiness and an unavailable optional lux does
# not invalidate a room with valid RH and a verified closed window.
illuminance=R('sensor.light','Light','illuminance',None)
r=logic.Room('room','Room',room.windows,room.readings+(illuminance,))
p=logic.evaluate(outside,weather,(),(r,),constants.DEFAULT_THRESHOLDS)
d=dash.dashboard_snapshot(p,constants.DEFAULT_THRESHOLDS)
assert d['rooms'][0]['status']=='safe',d['rooms'][0]
assert d['rooms'][0]['readings'][-1]['unit']=='lx'
r=logic.Room('room','Room',room.windows,(R('sensor.light','Light','illuminance',200),))
p=logic.evaluate(outside,weather,(),(r,),constants.DEFAULT_THRESHOLDS)
assert dash.dashboard_snapshot(p,constants.DEFAULT_THRESHOLDS)['rooms'][0]['status']=='unknown'
assert any(msg=='no_indoor_data' for _,msg in p.diagnostics)
# Existing real environmental aggregation/history and daylight path.
env=importlib.import_module('hem65test.environment')
history_mod=importlib.import_module('hem65test.environment_history')
history=history_mod.EnvironmentHistory()
r=logic.Room('room','Room',room.windows,room.readings+actual.readings)
report,changed=env.build_environment(hass,(r,),(r,),weather,outside,history=history,max_age_minutes=90,source_selections=selected,now=now.timestamp())
assert history.samples('room')[-1]['lux']==150,history.samples('room')
assert report['room']['sources']['optional_entity_sources']['illuminance_entities']['valid_count']==2
assert report['room']['international']['daylight']['status']!='not_configured'
print('PASS Beta65: warnings ignored without hazard bypass; lx/lux/zero/range/freshness; selected inventory; informational-only lux; history daylight input')

# Server-side friendly names and card translations share one locale source.
import json
names=importlib.import_module('hem65test.equipment_name_catalog')
for path in (ROOT/'translations').glob('*.json'):
 data=json.loads(path.read_text())
 for group in ('number','select','button'):
  for key,info in data['entity'][group].items():
   if key.startswith('equipment_pid_') and 'name' in info:
    name=names.localized_equipment_name(key.removeprefix('equipment_'),path.stem)
    assert name==info['name'].replace('{channel}','').strip(),(path.stem,key,name,info['name'])
print('PASS Beta65: localized server-side PID names agree with all 38 HA catalogs')

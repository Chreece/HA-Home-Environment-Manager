"""Exercise the actual shade configuration, lux evidence and native close path.

No Home Assistant services or physical devices are contacted.
"""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
from typing import Any

ROOT=Path(__file__).resolve().parents[2]


def extract(path, names, ns):
    tree=ast.parse((ROOT/path).read_text())
    chosen=[]
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names:
            chosen.append(n)
        if isinstance(n,ast.ClassDef):
            chosen.extend(m for m in n.body if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)) and m.name in names)
    assert {n.name for n in chosen}==set(names),(path,names)
    exec(compile(ast.Module(body=chosen,type_ignores=[]),path,'exec'),ns)
    return tuple(ns[n] for n in names)


NOW=datetime.now(timezone.utc)
TS=NOW.timestamp()
ROOM='schlafzimmer'
COVER='cover.rollo'
OTHER='cover.other'


def state(entity,value,attrs=None,ago=1):
    return NS(entity_id=entity,domain=entity.split('.')[0],state=str(value),name=entity,
              attributes=attrs or {},last_changed=NOW-timedelta(minutes=ago),
              last_updated=NOW-timedelta(minutes=ago))


class StateStore:
    def __init__(self,items):self.values=items;self.scan_calls=0
    def get(self,key):return self.values.get(key)
    def async_all(self,domain=None):
        self.scan_calls+=1
        return [v for v in self.values.values() if domain is None or v.domain==domain]


reg_items={
 'sensor.left':NS(entity_id='sensor.left',area_id=ROOM,platform='local',device_id='dev-light',name='Window',original_name='Window',device_class='illuminance',original_device_class=None,original_unit_of_measurement='lx'),
 'sensor.right':NS(entity_id='sensor.right',area_id=ROOM,platform='local',device_id='dev-light',name='Desk',original_name='Desk',device_class='illuminance',original_device_class=None,original_unit_of_measurement='lx'),
 'sensor.away':NS(entity_id='sensor.away',area_id='other',platform='local',device_id=None,name='Other',original_name='Other',device_class='illuminance',original_device_class=None,original_unit_of_measurement='lx'),
 'sensor.generated':NS(entity_id='sensor.generated',area_id=ROOM,platform='environment_manager',device_id=None,name='Fake',original_name='Fake',device_class='illuminance',original_device_class=None,original_unit_of_measurement='lx'),
 'sensor.invalid_unit':NS(entity_id='sensor.invalid_unit',area_id=ROOM,platform='local',device_id=None,name='Wrong units',original_name='Wrong units',device_class=None,original_device_class=None,original_unit_of_measurement='V'),
 'binary_sensor.window':NS(entity_id='binary_sensor.window',area_id=ROOM,platform='zigbee',device_id=None,name='Window',original_name='Window',device_class='window',original_device_class=None),
 'cover.rollo':NS(entity_id=COVER,area_id=ROOM,platform='cover',device_id='dev-cover',name='Rollo',original_name='Rollo',device_class='shade',original_device_class=None),
 'cover.other':NS(entity_id=OTHER,area_id=ROOM,platform='cover',device_id='dev-cover',name='Rollo2',original_name='Rollo2',device_class='shade',original_device_class=None),
}

reg=NS(entities=reg_items,async_get=reg_items.get)
devices={"dev-light":NS(name_by_user='Light Array',name='Light Array'),
         "dev-cover":NS(name_by_user='Cover Device',name='Cover Device')}
dreg=NS(async_get=devices.get)
HA=ModuleType('homeassistant');HA.__path__=[]
HELP=ModuleType('homeassistant.helpers');HELP.__path__=[]
ER=ModuleType('homeassistant.helpers.entity_registry');ER.async_get=lambda hass:reg
DR=ModuleType('homeassistant.helpers.device_registry');DR.async_get=lambda hass:dreg
HELP.entity_registry=ER;HELP.device_registry=DR
HA.helpers=HELP
sys.modules.update({'homeassistant':HA,'homeassistant.helpers':HELP,
                    'homeassistant.helpers.entity_registry':ER,
                    'homeassistant.helpers.device_registry':DR})


def entity_area(hass,entity):
    e=reg_items.get(entity)
    return getattr(e,'area_id',None)


def native(hass,entity):
    e=reg_items.get(entity)
    return e is None or e.platform!='environment_manager'


def selected(config,area,group):
    return tuple(config.get('room_sources',{}).get(area,{}).get(group,[]))


def is_window(hass,s):return s.domain=='binary_sensor' and s.attributes.get('device_class')=='window'


def reading(hass,entity,max_age_minutes,*,outdoor):
    s=hass.states.get(entity)
    if s is None:return NS(metric='illuminance',value=None)
    unit=s.attributes.get('unit_of_measurement')
    if unit not in ('lx','lux'):return NS(metric='unknown',value=None)
    if (NOW-s.last_updated).total_seconds()>max_age_minutes*60:
        return NS(metric='illuminance',value=None)
    try:v=float(s.state)
    except (TypeError,ValueError):v=None
    return NS(metric='illuminance',value=v if v is not None and 0<=v<=300000 else None)

PKG=ModuleType('lux_69');PKG.__path__=[]
DIS=ModuleType('lux_69.discovery');DIS.entity_area=entity_area;DIS.is_window=is_window;DIS.reading=reading
ROOMMOD=ModuleType('lux_69.room_sources');ROOMMOD.selected=selected;ROOMMOD.native=native
ROOMMOD.category=lambda hass,s:'shades' if s.domain=='cover' else None
ROOMMOD.room_temperature_evidence=lambda hass,settings,area,age_minutes:(29,{'source':'bedroom'})
ROOMMOD.choices=lambda hass,area:{'windows':[]}
WEATHER=ModuleType('lux_69.shade_weather');WEATHER.weather_evidence=lambda hass,settings:('weather_solar',{'weather_status':'weather_solar'})
WINDOW=ModuleType('lux_69.logic');WINDOW.Window=lambda eid,name,opened:NS(entity_id=eid,name=name,opened=opened)
sys.modules.update({m.__name__:m for m in (PKG,DIS,ROOMMOD,WEATHER,WINDOW)})

lux_globals={'__name__':'lux_69.shade_cooling','__package__':'lux_69','Any':Any,
             'selected':selected,'native':native,'category':ROOMMOD.category,'math':__import__('math'),
             'LUX_BOUNDS':(100.,100000.,100.,'lx',1000.),
             'LUX_ROOM_MEAN':'room_selected_mean',
             'SHADE_NUMBERS':{'close_above_c':(18.,36.,.5,'°C',25.),'min_sun_elevation':(3.,80.,1.,'°',10.)},
             'CONF_SHADE_ROOMS':'shade_rooms','CONF_SHADE_ANNOUNCE':'shade_announce',
             'COOLING_HYSTERESIS_C':1.0,'HOLD_SECONDS':7200,'STARTUP_SECONDS':60,
             'ACK_GRACE_SECONDS':300,'OPEN_STABLE_SECONDS':300,
             'OWNED_PHASES':frozenset(('closing_requested','owned_closed','opening_requested')),
             'room_temperature_evidence':ROOMMOD.room_temperature_evidence,
             'weather_evidence':WEATHER.weather_evidence,
             'HAZARDOUS':set(),'time':__import__('time'),
             'asyncio':asyncio,'datetime':datetime,'timezone':timezone,
}
sh_names=('config','cover_config','_numeric','_lux_candidate','selectable_lux_sensors',
          'lux_evidence','lux_signature','selectable_windows','evaluate_conditions',
          'eligible_shade','_open_supported','_solar_release_reason','_day',
          '_inputs','_tick')
# '_day' is a static method, and for all others actual production source is used.
results=extract('shade_cooling.py',sh_names,lux_globals)
for k,v in zip(sh_names,results):lux_globals[k]=v


def make_data(lux_value=1500,*,on=True,entity='sensor.left',threshold=1000,mean=False):
    shade={"enabled":True,"window_entity":"binary_sensor.window","announce":False,
           "close_above_c":25,"authorization_revision":3,
           "lux_enabled":on,"lux_entity":"room_selected_mean" if mean else entity,
           "min_lux":threshold}
    settings={'areas':[ROOM],"room_sources":{ROOM:{'shades':[COVER],
              'windows':['binary_sensor.window'],
              'air_quality':['sensor.left','sensor.right','sensor.away','sensor.generated']}},
              'shade_rooms':{ROOM:{'enabled':True,"covers":{COVER:shade,OTHER:{'enabled':False}}}},
              'weather_entities':['weather.home']}
    states={
      'sensor.left':state('sensor.left',lux_value,{'device_class':'illuminance','unit_of_measurement':'lx'}),
      'sensor.right':state('sensor.right',3000,{'device_class':'illuminance','unit_of_measurement':'lx'}),
      'sensor.away':state('sensor.away',9000,{'device_class':'illuminance','unit_of_measurement':'lx'}),
      'sensor.generated':state('sensor.generated',50000,{'device_class':'illuminance','unit_of_measurement':'lx'}),
      'sensor.invalid_unit':state('sensor.invalid_unit',90000,{'unit_of_measurement':'V'}),
      COVER:state(COVER,'open',{'supported_features':3,'device_class':'shade'}),
      OTHER:state(OTHER,'open',{'supported_features':3,'device_class':'shade'}),
      'binary_sensor.window':state('binary_sensor.window','off',{'device_class':'window'}),
      'sun.sun':state('sun.sun','above_horizon',{'elevation':40}),
      'weather.home':state('weather.home','sunny')}
    return settings,states


class Controller:
    def __init__(self,settings,states):
        self._records={};self._observed_cover_states={};self._ready=True
        self._active=True;self._started=TS-3600
        self.manager=NS(settings=settings,plan=NS(rooms=(NS(area_id=ROOM,
           windows=(NS(entity_id='binary_sensor.window',name='Window',opened=False),)),),
           climate_rooms=()))
        self._store=NS();self.manager.shading=self;self.manager._active=True
        self.statuses={};self.saved=[];self.hardware=[];self.hook=None;self.save_hook=None
        self.hass=NS(states=StateStore(states),services=NS())
        self.hass.services.has_service=lambda dom,service:dom=='cover' and service in ('close_cover','open_cover')
        async def send(domain,service,data,*,target,blocking):
            assert self._records[COVER]['phase'].endswith('requested'), 'must persist intent before motion'
            self.hardware.append((service,target['entity_id']))
            states[target['entity_id']].state='closed' if service=='close_cover' else 'open'
        self.hass.services.async_call=send
        self.clock=lambda:TS
    _inputs=lux_globals['_inputs'];_day=staticmethod(lux_globals['_day'])
    async def _before_move(self,area,action,entity,revision):
        if self.hook:self.hook()
        return True
    async def _save(self,entity,entry):
        if entry is None:self._records.pop(entity,None)
        else:self._records[entity]=deepcopy(entry)
        self.saved.append((entity,deepcopy(entry)))
        if self.save_hook:self.save_hook()
        return True
    def _status(self,area,status,**data):self.statuses[area]={'status':status,**data}


async def run_tick(controller):await lux_globals['_tick'](controller,ROOM)


async def shade_tests():
    for on,lux,expected in ((False,0,'closing_recommended'),
                            (True,0,'lux_below_threshold'),
                            (True,500,'lux_below_threshold'),
                            (True,1000,'closing_recommended'),
                            (True,2000,'closing_recommended'),
                            (True,'unavailable','lux_sensor_unavailable_or_stale')):
        settings,states=make_data(lux,on=on)
        c=Controller(settings,states)
        reason,info,*_=c._inputs(ROOM,settings,COVER)
        assert reason==expected,(on,lux,reason,expected,info)
        if on and isinstance(lux,(int,float)):
            assert info['illuminance']['value_lx']==float(lux)
        await run_tick(c)
        assert len(c.hardware)==int(expected=='closing_recommended'),(on,lux,c.hardware)
    # No auto-close even with 100,000 lx when sun/weather/window/temperature disagree.
    for bad,when in [('sun',lambda s:setattr(s['sun.sun'],'state','below_horizon')),
                     ('weather',lambda s:setattr(s['weather.home'],'state','rainy')),
                     ('window',lambda s:setattr(s['binary_sensor.window'],'state','on'))]:
        settings,states=make_data(2500)
        when(states);c=Controller(settings,states)
        if bad=='weather':WEATHER.weather_evidence=lambda h,s:('weather_no_solar_gain',{'weather_status':'weather_no_solar_gain'})
        lux_globals['weather_evidence']=WEATHER.weather_evidence
        if bad=='window':c.manager.plan.rooms=(NS(area_id=ROOM,windows=(NS(entity_id='binary_sensor.window',name='Window',opened=True),)),)
        await run_tick(c)
        assert not c.hardware,(bad,c.hardware)
        WEATHER.weather_evidence=lambda hass,settings:('weather_solar',{'weather_status':'weather_solar'})
        lux_globals['weather_evidence']=WEATHER.weather_evidence
    # Existing closed owned shades do NOT reopen when lux drops after closure.
    settings,states=make_data(2000);c=Controller(settings,states)
    await run_tick(c);assert c.hardware==[('close_cover',COVER)]
    await run_tick(c);assert c._records[COVER]['phase']=='owned_closed'
    states['sensor.left'].state='0'
    await run_tick(c);assert c.hardware==[('close_cover',COVER)],c.hardware
    states['sun.sun'].state='below_horizon'
    await run_tick(c);assert c.hardware[-1]==('open_cover',COVER),c.hardware
    # Independent cover evidence changes between announcement and action.
    settings,states=make_data(2300);c=Controller(settings,states)
    c.hook=lambda: setattr(states['sensor.left'],'state','0')
    await run_tick(c);assert c.hardware==[]
    # Changed policy during async persisted intent cannot authorize an old close.
    settings,states=make_data(3000);c=Controller(settings,states)
    def change_policy():settings['shade_rooms'][ROOM]['covers'][COVER]['min_lux']=5000
    c.save_hook=change_policy
    await run_tick(c);assert c.hardware==[]
    # Average selected room lux sources only, ignores unavailable; no cross-room or manager-generated sources.
    settings,states=make_data(1000,mean=True,threshold=1500)
    c=Controller(settings,states)
    evidence=lux_globals['lux_evidence'](c.hass,settings,ROOM,lux_globals['cover_config'](settings,ROOM,COVER))
    assert evidence['value_lx']==2000 and evidence['valid_count']==2,evidence
    states['sensor.left'].state='unavailable';states['sensor.right'].state='0'
    evidence=lux_globals['lux_evidence'](c.hass,settings,ROOM,lux_globals['cover_config'](settings,ROOM,COVER))
    assert evidence['value_lx']==0 and evidence['valid_count']==1,evidence
    states['sensor.right'].state='unavailable'
    evidence=lux_globals['lux_evidence'](c.hass,settings,ROOM,lux_globals['cover_config'](settings,ROOM,COVER))
    assert evidence['status']=='lux_sensor_unavailable_or_stale',evidence
    # Source moved to different area, or stale physical measurement: no close.
    settings,states=make_data(5000);c=Controller(settings,states)
    reg_items['sensor.left'].area_id='elsewhere'
    assert c._inputs(ROOM,settings,COVER)[0]=='lux_sensor_not_selected_or_ineligible'
    reg_items['sensor.left'].area_id=ROOM
    states['sensor.left'].last_updated=NOW-timedelta(minutes=15)
    assert c._inputs(ROOM,settings,COVER)[0]=='lux_sensor_unavailable_or_stale'
    # Source options are registered once per area, never rescanned on each UI property.
    states['sensor.left'].last_updated=NOW
    settings,states=make_data(2000);c=Controller(settings,states)
    valid=lux_globals['selectable_lux_sensors'](c.hass,ROOM)
    assert valid==('sensor.left','sensor.right'),valid
    assert c.hass.states.scan_calls==1


async def test_select_device_and_scan_budget():
    # Exercise the actual HA SelectEntity child: stable friendly names and
    # exactly one room inventory scan even with multiple cover devices.
    SELECT=ModuleType('lux_69.select')
    hierarchy=ModuleType('lux_69.device_hierarchy')
    hierarchy.controller_device_info=lambda manager,area,cover: {
        'identifiers':{('environment_manager',f'cover:{cover}')}
    }
    sys.modules[hierarchy.__name__]=hierarchy
    sys.modules['lux_69.shade_cooling']=NS(
        selectable_lux_sensors=lux_globals['selectable_lux_sensors'],
        LUX_ROOM_MEAN=lux_globals['LUX_ROOM_MEAN'],
        cover_config=lux_globals['cover_config'])
    scope={'__name__':SELECT.__name__,'__package__':'lux_69',
           'SelectEntity':object,'EntityCategory':NS(CONFIG='config'),
           'controller_device_info':hierarchy.controller_device_info,
           'update_device_setting':lambda *args,**kw:None,
           'SIGNAL_UPDATED':'update','callback':lambda fn:fn,
           'async_dispatcher_connect':lambda *args:None}
    klass=next(n for n in ast.parse((ROOT/'select.py').read_text()).body
               if isinstance(n,ast.ClassDef) and n.name=='ShadeIlluminanceSelect')
    exec(compile(ast.Module(body=[klass],type_ignores=[]),'select.py','exec'),scope)
    settings,states=make_data(1200)
    store=StateStore(states)
    manager=NS(hass=NS(states=store,config=NS(language='el')),
               settings=settings,entry=NS(entry_id='hem-entry'))
    selector=scope['ShadeIlluminanceSelect'](manager,'hem-entry',ROOM,COVER)
    another=scope['ShadeIlluminanceSelect'](manager,'hem-entry',ROOM,OTHER)
    assert store.scan_calls==1,store.scan_calls
    opts=selector.options
    assert any('Light Array - Window' in x and '[sensor.left]' in x for x in opts),opts
    assert any('Μέσος όρος' in x for x in opts),opts
    assert 'sensor.left' in selector.current_option
    states['sensor.left'].state='9000'
    assert selector.options==opts,'Lux changes must not rebuild selector labels'
    assert selector._attr_device_info!=another._attr_device_info
    assert selector._attr_unique_id!=another._attr_unique_id
    assert selector.extra_state_attributes['lux_entity']=='sensor.left'


async def test_configuration():
    # Execute real update_device_setting against a single config key,
    # asserting isolation, validation and no hardware command.
    import math
    dc={"__name__":"lux_69.device_controls","__package__":"lux_69",
        "Any":Any,"deepcopy":deepcopy,"asyncio":asyncio,"math":math,
        "CONF_AREAS":"areas","HomeAssistantError":ValueError,
        "_finite":lambda x,b: float(x) if type(x) in (int,float) and math.isfinite(x) and b[0]<=x<=b[1] else (_ for _ in ()).throw(ValueError('bad number'))}
    fn,=extract('device_controls.py',('update_device_setting',),dc)
    sys.modules['lux_69.shade_cooling']=NS(
        CONF_SHADE_ROOMS='shade_rooms',SHADE_NUMBERS=lux_globals['SHADE_NUMBERS'],
        LUX_BOUNDS=lux_globals['LUX_BOUNDS'],LUX_ROOM_MEAN=lux_globals['LUX_ROOM_MEAN'],
        eligible_shade=lux_globals['eligible_shade'],selectable_windows=lux_globals['selectable_windows'],
        selectable_lux_sensors=lux_globals['selectable_lux_sensors'])
    settings,states=make_data(3000,on=False)
    manager=NS(settings=settings,shading=NS(_records={}),entry=NS(options=deepcopy(settings)))
    def update(entry,*,options):entry.options=options;manager.settings=options
    hass=NS(states=StateStore(states),config_entries=NS(async_update_entry=update))
    manager.hass=hass;manager._active=False
    # Physical controller offline while editing lux settings is allowed.
    states[COVER].state='unavailable'
    await fn(manager,'shade_device','lux_entity','sensor.left',area=ROOM,entity_id=COVER)
    await fn(manager,'shade_device','min_lux',2400,area=ROOM,entity_id=COVER)
    await fn(manager,'shade_device','lux_enabled',True,area=ROOM,entity_id=COVER)
    current=manager.entry.options['shade_rooms'][ROOM]['covers'][COVER]
    assert current['lux_enabled'] and current['lux_entity']=='sensor.left' and current['min_lux']==2400
    assert manager.entry.options['shade_rooms'][ROOM]['covers'][OTHER]['enabled'] is False
    # Null and rejected edits never change the cover's current settings.
    for key,value in [('lux_enabled',1),('min_lux',0),('min_lux',200000),
                      ('lux_entity','sensor.away'),('lux_entity','sensor.generated'),
                      ('lux_entity','sensor.invalid_unit')]:
        try: await fn(manager,'shade_device',key,value,area=ROOM,entity_id=COVER)
        except ValueError:pass
        else:raise AssertionError(('unsafe setting accepted',key,value))
        assert manager.entry.options['shade_rooms'][ROOM]['covers'][COVER]==current
    await fn(manager,'shade_device','lux_enabled',False,area=ROOM,entity_id=COVER)
    await fn(manager,'shade_device','lux_entity',None,area=ROOM,entity_id=COVER)
    try: await fn(manager,'shade_device','lux_enabled',True,area=ROOM,entity_id=COVER)
    except ValueError:pass
    else:raise AssertionError('enabling with no sensor must be rejected')


async def main():
    await shade_tests()
    await test_select_device_and_scan_budget()
    await test_configuration()
    for path in (ROOT/'translations').glob('*.json'):
        entry=json.loads(path.read_text())['entity']
        assert all(k in entry[group] and entry[group][k]['name'] for group,k in (
            ('select','shade_lux_entity'),('switch','shade_lux_enabled'),('number','shade_min_lux'))),path
    print('PASS: optional per-cover lux; same-room identities; reading and selected mean; no stale/cross-room/invalid false-closures; close race revalidation; no light-driven reopen; offline edits; 38 locale names')

asyncio.run(main())

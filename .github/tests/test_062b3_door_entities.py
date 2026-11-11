"""Native door entities: real HA entity classes in CI, isolated metadata writes.

Run with --with-ha after installing the normal CI Home Assistant dependency.
Default mode supplies minimal entity boundaries for offline development.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]/'custom_components/environment_manager'
PKG='hem_door_entity_fixture'
package=ModuleType(PKG);package.__path__=[str(ROOT)];sys.modules[PKG]=package

def module(name,**values):
    item=ModuleType(name);item.__dict__.update(values);sys.modules[name]=item;return item

def load(name):
    spec=importlib.util.spec_from_file_location(PKG+'.'+name,ROOT/(name+'.py'))
    item=importlib.util.module_from_spec(spec);sys.modules[spec.name]=item;spec.loader.exec_module(item);return item

if '--with-ha' not in sys.argv:
    class Entity:
        def async_write_ha_state(self):pass
        async def async_added_to_hass(self):pass
    module('homeassistant');module('homeassistant.components');module('homeassistant.helpers')
    module('homeassistant.components.number',NumberEntity=type('NumberEntity',(Entity,),{}),NumberMode=N(BOX='box'))
    module('homeassistant.components.select',SelectEntity=type('SelectEntity',(Entity,),{}))
    module('homeassistant.components.sensor',SensorEntity=type('SensorEntity',(Entity,),{}),SensorDeviceClass=N(ENUM='enum'))
    module('homeassistant.core',callback=lambda fn:fn)
    module('homeassistant.helpers.dispatcher',async_dispatcher_connect=lambda *args:lambda:None)
    module('homeassistant.helpers.entity',EntityCategory=N(CONFIG='config',DIAGNOSTIC='diagnostic'))

saved={'kind':'interior','target_area':None,'report_timeout_minutes':0}
calls=[]
async def update(manager,area,entity,key,value):
    assert (area,entity)==('a','binary_sensor.door')
    calls.append((area,entity,key,value));saved[key]=value
module(PKG+'.door_settings',async_update=update,
       editable_contact=lambda *args:True,
       inventory=lambda *args:iter([('a','binary_sensor.door')]),
       target_areas=lambda *args:{'b':'Guest room','c':'Guest room'})
module(PKG+'.room_doors',contact_options=lambda *args:dict(saved))
load('const');entity=load('door_entities')
manager=N(entry=N(entry_id='entry'),settings={'climate_rooms':{'a':{}}},
          hass=N(config=N(language='en'),states=N(get=lambda eid:N(name='Hall contact'))),
          plan=N(environment={'a':{'door_context':{'boundary':'closed','contacts_complete':True,
              'contacts':[{'entity_id':'binary_sensor.door','health':'ok'}],
              'connected_rooms':['b'],'advisories':[{'code':'fresh_air_needed'}],
              'quiet_boundary':True,'presence_recheck_hint':False}}}))
selects=entity.select_entities(manager);numbers=entity.number_entities(manager);sensors=entity.sensor_entities(manager)
assert len(selects)==2 and len(numbers)==len(sensors)==1
all_entities=[*selects,*numbers,*sensors]
assert len({item._attr_unique_id for item in all_entities})==4
for item in all_entities:
    assert item._attr_device_info['identifiers']=={('environment_manager','entry_area_a')}
    # State publication is a boundary fixture; production entity properties,
    # class MRO, native schemas, choices and setter dispatch remain actual.
    item.async_write_ha_state=lambda:None
connection,kind=selects
assert connection.options==['Not connected','Guest room [b]','Guest room [c]']
assert connection.current_option=='Not connected'
assert connection.extra_state_attributes['door_setting_key']=='target_area'
assert connection.name=='Hall contact · Connects to room'
asyncio.run(connection.async_select_option('Guest room [b]'))
assert calls[-1][-2:]==('target_area','b')
assert connection.current_option=='Guest room [b]'
try:asyncio.run(connection.async_select_option('Guest room'))
except ValueError:pass
else:raise AssertionError('Ambiguous room title was accepted')
saved['target_area']='removed'
assert connection.current_option=='Unavailable room [removed]'
asyncio.run(connection.async_select_option('Not connected'))
assert saved['target_area'] is None
asyncio.run(kind.async_select_option('Fire/safety door'))
assert saved['kind']=='fire'
saved['kind']='exterior'
assert connection.options==['Not connected']
assert numbers[0].native_value==0
asyncio.run(numbers[0].async_set_native_value(30))
assert saved['report_timeout_minutes']==30
assert numbers[0].extra_state_attributes['door_source_entity']=='binary_sensor.door'
assert sensors[0].native_value=='closed'
assert sensors[0].extra_state_attributes['advisory_only'] is True
assert sensors[0].extra_state_attributes['advisory_codes']==['fresh_air_needed']
assert sensors[0].extra_state_attributes['connected_rooms']==['b']
for locale,label in [('el','Συνδέεται με χώρο'),('de','Verbunden mit Raum')]:
    manager.hass.config.language=locale
    assert connection.name.endswith(label)
    assert connection.extra_state_attributes['configuration_help']
manager.plan.environment.clear()
assert sensors[0].native_value=='unknown'
assert sensors[0].extra_state_attributes['contact_count']==0
print('PASS: native door select/number/enum entities, identities, exact setters and EN/EL/DE'+
      (' with actual Home Assistant base classes' if '--with-ha' in sys.argv else ' (offline boundaries)'))

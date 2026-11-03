"""Beta97: battery devices get NO HEM power switch selector.

Runs the real battery detector and the real select.async_setup_entry through
isolated HA registry/device fixtures. Does not send hardware commands or
alter existing physical power-switch configuration. Tests legacy selectors
with user-renamed HA entity IDs are retired using exact unique IDs.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
BATTERY=ROOT/'equipment_battery.py'
SELECT=ROOT/'select.py'

mod=ModuleType('beta97_power_select.equipment_battery')
sys.modules[mod.__name__]=mod
exec(compile(BATTERY.read_text(),str(BATTERY),'exec'),mod.__dict__)
detect=mod.battery_reporting_controllers

class State:
    def __init__(self,state='on',**attributes):
        self.state=state
        self.attributes=attributes

class Registry:
    def __init__(self,entities,old=None):
        self.entities={e.entity_id:e for e in entities}
        self.old=dict(old or {})
        self.removed=[]
    def async_get(self,entity):
        return self.entities.get(entity)
    def async_get_entity_id(self,domain,platform,uid):
        return self.old.get((domain,platform,uid))
    def async_remove(self,entity):
        self.removed.append(entity)
        for key,value in tuple(self.old.items()):
            if value==entity:self.old.pop(key)
        self.entities.pop(entity,None)

def entity(eid,device=None,cls=None,orig=None):
    return N(entity_id=eid,device_id=device,
             device_class=cls,original_device_class=orig)
def spec(identifier,device,sources):
    return N(identifier=identifier,source_device_id=device,
             source_entities=tuple(sources),area_id='livingroom')

# Two actual physical HA devices in the SAME ROOM. A battery sensor
# attached to device A must not hide device B's powered switch selector.
battery=spec('controller_battery','device-A',['climate.battery_native'])
mains=spec('controller_mains','device-B',['climate.mains_native'])
remote=spec('controller_other','device-C',['fan.room_extractor'])
states={
    'climate.battery_native':State('off'),
    'climate.mains_native':State('heat'),
    'fan.room_extractor':State('off'),
    'sensor.device_a_battery':State('68',device_class='battery',
                                   unit_of_measurement='%'),
    'sensor.device_b_power':State('92',device_class='power',
                                 unit_of_measurement='W'),
}
registry=Registry([
    entity('climate.battery_native','device-A'),
    entity('climate.mains_native','device-B'),
    entity('fan.room_extractor','device-C'),
    entity('sensor.device_a_battery','device-A',orig='battery'),
    entity('sensor.device_b_power','device-B',orig='power'),
])
hass=N(states=N(get=lambda eid:states.get(eid)))
assert detect(hass,[battery,mains,remote],registry)==frozenset({
    battery.identifier}), 'battery report cannot leak to same-room mains devices'

# Battery reported as a native attribute also qualifies even if the device
# has no separate HA battery entity at all.
attr=spec('controller_attr',None,['fan.battery_fan'])
states['fan.battery_fan']=State('on',battery_level=61)
assert detect(hass,[attr],registry)==frozenset({'controller_attr'})
states['fan.battery_fan']=State('on',battery_percentage=None)
assert detect(hass,[attr],registry)==frozenset()
states['fan.battery_fan']=State('on',battery_percentage=0)
assert detect(hass,[attr],registry)==frozenset({'controller_attr'})

# Registry-backed BATTERY class survives an unavailable battery sensor.
states['sensor.device_a_battery']=State('unavailable')
assert detect(hass,[battery,mains],registry)==frozenset({'controller_battery'})
# A battery class from an unrelated physical device is never sufficient.
registry.entities['sensor.device_a_battery'].device_id='device-C'
assert detect(hass,[battery,mains],registry)==frozenset()
registry.entities['sensor.device_a_battery'].device_id='device-A'

# Avoid a new registry sweep for each controller. The list of candidates is
# read once by setup and the existing runtime/dwell behavior is untouched.
class CountRegistry(Registry):
    def __init__(self,entities,old):
        super().__init__(entities,old)
        self.reads=0
        self.entities=self.Counted(self,self.entities)
    class Counted(dict):
        def __init__(self,owner,values):
            super().__init__(values)
            self.owner=owner
        def values(self):
            self.owner.reads+=1
            return super().values()

uids={
    ('select','environment_manager','controller_battery_power_switch_entity'):
       'select.user_renamed_battery_power_dropdown',
    ('select','environment_manager','controller_mains_power_switch_entity'):
       'select.my_mains_power_dropdown',
}
reg=CountRegistry(list(registry.entities.values()),uids)
all_specs=(battery,mains,remote)
assert detect(hass,all_specs,reg)==frozenset({battery.identifier})
assert reg.reads==1,reg.reads

# Simulate HA platform setup using actual select.py async_setup_entry code,
# not a restated implementation.
pkg=ModuleType('beta97_power_select')
pkg.__path__=[]
sys.modules[pkg.__name__]=pkg
equipment=ModuleType(pkg.__name__+'.equipment_model')
equipment.specs=lambda manager:all_specs
equipment.capabilities=lambda manager,spec:None
equipment.DEVICE_SELECTS={}
sys.modules[equipment.__name__]=equipment
features=ModuleType(pkg.__name__+'.equipment_feature_registration')
features.quiet_keys=lambda *a,**kw:()
features.pid_calibration_supported=lambda *a,**kw:False
features.registered_control=lambda *a,**kw:False
features.register_late_capabilities=lambda *a,**kw:None
sys.modules[features.__name__]=features
aqi=ModuleType(pkg.__name__+'.aqi_sources')
aqi.register_late_sources=lambda *a,**kw:None
sys.modules[aqi.__name__]=aqi
source=ModuleType(pkg.__name__+'.room_sources')
source.selected=lambda *a,**kw:()
sys.modules[source.__name__]=source
const=ModuleType(pkg.__name__+'.const')
const.CONF_AREAS='areas'
sys.modules[const.__name__]=const
ha_mod=ModuleType('homeassistant')
ha_mod.__path__=[]
helpers=ModuleType('homeassistant.helpers')
helpers.__path__=[]
er=ModuleType('homeassistant.helpers.entity_registry')
er.async_get=lambda h:reg
sys.modules.update({'homeassistant':ha_mod,'homeassistant.helpers':helpers,
                    'homeassistant.helpers.entity_registry':er})
helpers.entity_registry=er

registered=[]
def create(kind,*args):
    return N(kind=kind,args=args)
env={
    '__name__':pkg.__name__+'.select',
    '__package__':pkg.__name__,
    'DOMAIN':'environment_manager',
    'GLOBAL_POLICY_OPTIONS':{'home_policy':('auto',)},
    'configured_area_ids':lambda cfg:(),
    'configured_aqi_entities':lambda manager:(),
    'climate_settings':lambda *a,**kw:None,
    'pid_settings':lambda *a,**kw:None,
    'TTSLanguageSelect':lambda *args:create('language',*args),
    'ConfigSelect':lambda *args,**kw:create('config',*args),
    'EquipmentSelect':lambda *args:create('control',*args),
    'EquipmentPowerSwitchSelect':lambda *args:create('supply',*args),
    'AreaScienceSource':lambda *args:create('science',*args),
    'ShadeWindowSelect':lambda *args:create('shade',*args),
    'ShadeIlluminanceSelect':lambda *args:create('lux',*args),
    'async_add_grouped_entities':lambda manager,add,entities:
        registered.extend(entities),
}
tree=ast.parse(SELECT.read_text())
func=next(f for f in tree.body if isinstance(f,ast.AsyncFunctionDef)
          and f.name=='async_setup_entry')
exec(compile(ast.Module(body=[func],type_ignores=[]),
             str(SELECT),'exec'),env)
manager=N(settings={
    'equipment_controllers':{
        battery.identifier:{'power_switch_entity':'switch.saved_outlet'},
        mains.identifier:{'power_switch_entity':None},
    },
},entry=N(entry_id='hem-entry'))
entry=N(runtime_data=manager,entry_id='hem-entry')
asyncio.run(env['async_setup_entry'](hass,entry,lambda entities:None))
supply=[item for item in registered if item.kind=='supply']
assert len(supply)==2 and set(item.args[1].identifier for item in supply)=={
    mains.identifier,remote.identifier},supply
assert reg.removed==['select.user_renamed_battery_power_dropdown'],reg.removed
assert ('select','environment_manager','controller_mains_power_switch_entity') in reg.old
assert manager.settings['equipment_controllers'][battery.identifier][
    'power_switch_entity']=='switch.saved_outlet'
assert reg.reads==2,'one registry sweep in each explicit detection, no per-source scan'
print('BETA97_BATTERY_POWER_SELECT_GONE_AND_MAINS_AVAILABLE_LEGACY_RETIRE_ONLY=PASS')

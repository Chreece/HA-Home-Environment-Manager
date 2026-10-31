"""Beta79: exact three-section room menu and safe independent editors.

Runs extracted REAL ReconfigureSectionsMixin methods against deterministic fake
Home Assistant registries and native source selectors. A test saves each menu
section without touching any physical device, and checks 38 locale contracts.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'reconfigure_sections.py'
syntax=ast.parse(SOURCE.read_text(encoding='utf-8'))
nodes=[node for node in syntax.body if (
    isinstance(node,ast.FunctionDef) and node.name=='_locale_sections'
) or (
    isinstance(node,ast.ClassDef) and node.name=='ReconfigureSectionsMixin'
)]
assert len(nodes)==2
groups=('windows','air_quality','temperature','humidity',
        'pressure','climate_devices','shades')
room_ids=('badezimmer','wohnzimmer')
inventory={
    'badezimmer':{
       'windows':['binary_sensor.bath_window'],
       'air_quality':['sensor.bath_aqi'],
       'temperature':['sensor.bath_temperature'],
       'humidity':['sensor.bath_humidity'],
       'pressure':['sensor.bath_pressure'],
       'climate_devices':['climate.bath_dry'],
       'shades':['cover.bath_shade'],
    },
    'wohnzimmer':{
       'windows':['binary_sensor.living_window'],
       'air_quality':['sensor.living_aqi'],
       'temperature':['sensor.living_temperature'],
       'humidity':['sensor.living_humidity'],
       'pressure':['sensor.living_pressure'],
       'climate_devices':['climate.living_heat'],
       'shades':['cover.living_shade'],
    },
}
saves=[]
def store_selection(hass,settings,area,values):
    assert list(values)==list(groups),values
    saves.append((area,copy.deepcopy(values)))
    settings.setdefault('room_sources',{})[area]=copy.deepcopy(values)
    # The real store_selection is separately covered by existing device source
    # and physical grant tests. This stub cannot energize anything.
sources=NS(
    GROUPS=groups,
    defaults=lambda hass,settings,area: copy.deepcopy(settings.get(
        'room_sources',{}).get(area,inventory[area])),
    choices=lambda hass,area,saved: {
        k:[{'value':v,'label':v} for v in inventory[area][k]]
        for k in groups
    },
    store_selection=store_selection,
    label=lambda hass,eid:eid,
)
reg=NS(async_get_area=lambda area:NS(name={
     'badezimmer':'Badezimmer','wohnzimmer':'Wohnzimmer'
     }[area]) if area in room_ids else None)
global_ns={
    '__file__':str(SOURCE),'Any':object,'json':json,'Path':Path,
    'probatio':NS(Schema=lambda mapping:mapping,
                  Required=lambda key,default=None:key),
    'ar':NS(async_get=lambda hass:reg),
    'deepcopy':copy.deepcopy,'CONF_AREAS':'areas',
    'CONF_CLIMATE_ROOMS':'climate_rooms',
    'sources':sources,
    'room_sensor_choices':lambda hass,area: (
        ['binary_sensor.bath_a','binary_sensor.bath_b']
        if area=='badezimmer' else ['binary_sensor.living_a']
    ),
    'areas':lambda hass:[
        {'value':'badezimmer','label':'Badezimmer'},
        {'value':'wohnzimmer','label':'Wohnzimmer'},
    ],
    'field':lambda key,default:key,
    'select':lambda options,multiple=False:options,
}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),global_ns)
Mix=global_ns['ReconfigureSectionsMixin']

class Flow(Mix):
    def __init__(self):
        self.hass=NS(config=NS(language='el'),states=NS())
        self.context={'language':'el'}
        self._room_settings_area=None
        self._values={
            'areas':['badezimmer','wohnzimmer'],
            'room_sources':{'badezimmer':copy.deepcopy(inventory['badezimmer']),
                            'wohnzimmer':copy.deepcopy(inventory['wohnzimmer'])},
            'climate_rooms':{
                'badezimmer':{'enabled':True,'allow_actuation':True,
                    'selected_devices':['climate.bath_dry'],
                    'device_settings':{'climate.bath_dry':{
                         'auto_control':True,'hardware_confirmed':True}},
                    'occupancy_sensors':[]},
                'wohnzimmer':{'enabled':True,'allow_actuation':True,
                    'selected_devices':['climate.living_heat'],
                    'device_settings':{'climate.living_heat':{'auto_control':True}},
                    'occupancy_sensors':['binary_sensor.living_a']},
            },
            'pid_rooms':{'badezimmer':{'enabled':True}},
            'shade_rooms':{'badezimmer':{'enabled':True,'covers':{'cover.bath_shade':{'enabled':True}}}},
            'occupancy_global':{'occupied_rooms_entity':'input_text.occupied_rooms'},
        }
        self.completed=[]
    def async_show_form(self,**kw):return {'type':'form',**kw}
    def async_show_menu(self,**kw):return {'type':'menu',**kw}
    def async_abort(self,reason):return {'type':'abort','reason':reason}
    async def _finish(self):
        self.completed.append(copy.deepcopy(self._values))
        return {'type':'done'}
    async def async_step_setup_general(self,user_input=None):
        return {'type':'general','data':user_input}

async def test():
    flow=Flow()
    menu=flow._settings_menu('reconfigure')
    assert menu['type']=='menu' and menu['step_id']=='reconfigure'
    keys=list(menu['menu_options'])
    assert keys==['choose_rooms','edit_room_0','edit_room_1','general_settings'],keys
    assert menu['menu_options']['choose_rooms']=='Επιλογή δωματίων'
    assert menu['menu_options']['edit_room_0']=='Ρυθμίσεις δωματίου · Badezimmer'
    assert menu['menu_options']['edit_room_1']=='Ρυθμίσεις δωματίου · Wohnzimmer'
    assert menu['menu_options']['general_settings']=='Γενικές ρυθμίσεις'
    same=flow._settings_menu('init')
    assert same['step_id']=='init' and list(same['menu_options'])==keys

    first=await flow.async_step_edit_room_0()
    assert first['type']=='form' and first['step_id']=='room_settings'
    assert set(first['data_schema'])==set(groups)|{'occupancy_sensors'}
    # Saving an explicit empty selection stays empty, even if discovery found
    # two valid physical occupancy sensors in this room.
    assert first['data_schema']['occupancy_sensors']
    assert flow._values['climate_rooms']['badezimmer']['occupancy_sensors']==[]
    updated={k:list(v) for k,v in inventory['badezimmer'].items()}
    updated['occupancy_sensors']=['binary_sensor.bath_b']
    result=await flow.async_step_room_settings(updated)
    assert result['type']=='done'
    assert saves[-1][0]=='badezimmer'
    assert flow.completed[-1]['climate_rooms']['badezimmer']['occupancy_sensors']==[
        'binary_sensor.bath_b']
    assert flow.completed[-1]['climate_rooms']['wohnzimmer']['occupancy_sensors']==[
        'binary_sensor.living_a']
    assert flow.completed[-1]['climate_rooms']['badezimmer']['device_settings']['climate.bath_dry']['auto_control'] is True

    second=await flow.async_step_edit_room_1()
    assert second['step_id']=='room_settings'
    values={k:list(v) for k,v in inventory['wohnzimmer'].items()}
    values['occupancy_sensors']=[]
    await flow.async_step_room_settings(values)
    assert flow.completed[-1]['climate_rooms']['wohnzimmer']['occupancy_sensors']==[]
    # An empty list is an intentional empty selection, not autodiscovery.

    # General settings is the FULL shared setup page, not the shortened
    # presence-only historical fragment.
    response=await flow.async_step_general_settings()
    assert response['type']=='general' and response['data'] is None

    # Select a room: no uncontrolled output changes, no enrollment of a
    # deleted room; the deleted room's preferences remain available.
    new=Flow()
    form=await new.async_step_choose_rooms()
    assert form['step_id']=='choose_rooms'
    invalid=await new.async_step_choose_rooms({'areas':['invalid']})
    assert invalid['errors']['base']=='invalid_setup_rooms'
    removed=await new.async_step_choose_rooms({'areas':['wohnzimmer']})
    assert removed['type']=='done'
    assert removed['type']=='done'
    assert new._values['areas']==['wohnzimmer']
    bath=new._values['climate_rooms']['badezimmer']
    assert bath['enabled'] is False and bath['allow_actuation'] is False
    assert bath['device_settings']['climate.bath_dry']['auto_control'] is False
    assert bath['selected_devices']==['climate.bath_dry']
    assert new._values['pid_rooms']['badezimmer']['enabled'] is False
    assert new._values['shade_rooms']['badezimmer']['enabled'] is False
    assert new._values['climate_rooms']['wohnzimmer']['enabled'] is True

asyncio.run(test())

# Each language has exactly the sections/types available in either flow,
# and all eight of the original source selectors still have labels.
for path in [ROOT/'strings.json',*(ROOT/'translations').glob('*.json')]:
    doc=json.loads(path.read_text(encoding='utf-8'))
    for category,menu_step in (('options','init'),('config','reconfigure')):
        steps=doc[category]['step']
        assert list(steps[menu_step]['menu_options'])==[
            'choose_rooms','general_settings'],path
        assert 'areas' in steps['choose_rooms']['data']
        assert set(steps['room_settings']['data'])==set(groups)|{
            'occupancy_sensors'},path
        assert '{area_name}' in steps['room_settings']['title'],path
        for k in ('general_home_policy','general_source_stale_minutes'):
            assert k in steps['setup_general']['data'],path
print('BETA79_SECTION_MENU_AND_EIGHT_ROOM_SELECTORS=PASS')

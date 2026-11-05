"""Beta78 occupancy source precedence against the actual production functions.

No HA service calls or devices. Verifies true configured list authority,
explicitly empty lists, unavailable list fallback, local selection/defaults,
and conservative unverified readings. This regression directly executes AST
extracted functions from occupancy_policy.py, not a reimplementation.
"""
from __future__ import annotations

import ast
import json
import math
import re
import unicodedata
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'occupancy_policy.py').read_text(encoding='utf-8')
tree=ast.parse(source)
names={'_fresh','_room_key','_tokens','configured_rooms','_bool_presence',
       'room_sensor_choices','selected_room_sensors','room_presence'}
methods=[node for node in tree.body if isinstance(node,ast.FunctionDef)
         and node.name in names]
assert len(methods)==len(names), set(names)-{m.name for m in methods}

areas={'Wohnzimmer':'wohnzimmer','Badezimmer':'badezimmer',
       'Gästezimmer':'gastezimmer','Schlafzimmer':'schlafzimmer'}
now=datetime.now(timezone.utc)

class States:
    def __init__(self):
        self.data={}
    def get(self,e):return self.data.get(e)
    def async_all(self,domain=None):
        return [s for s in self.data.values() if domain is None or s.domain==domain]

class Hass:
    def __init__(self):
        self.states=States()
        self.areas={}
    def put(self,eid,value,*,area=None,klass=None,age=1, registry_class=None):
        domain=eid.split('.',1)[0]
        s=N(entity_id=eid,domain=domain,state=value,
            attributes=({'device_class':klass} if klass is not None else {}),
            registry_class=registry_class,
            last_reported=now-timedelta(minutes=age),
            last_updated=now-timedelta(minutes=age),
            last_changed=now-timedelta(minutes=age))
        self.states.data[eid]=s
        if area:self.areas[eid]=area
        return s

ns={'ast':ast,'json':json,'math':math,'re':re,
    'unicodedata':unicodedata,'Mapping':Mapping,
    'datetime':datetime,'timezone':timezone,
    'Any':object,
    'entity_area':lambda hass,eid:hass.areas.get(eid),
    '_device_class':lambda hass,s:s.attributes.get('device_class') or s.registry_class or '',
    '_area_aliases':lambda hass,known:{
        unicodedata.normalize('NFKC',n).strip().casefold():aid
        for n,aid in areas.items() if aid in known
    }}
exec(compile(ast.Module(body=methods,type_ignores=[]),
             'occupancy_policy.py','exec'),ns)
resolve=ns['room_presence']
h=Hass()
global_cfg={'occupied_rooms_entity':'input_text.occupied_rooms',
            'occupied_rooms_attribute':'__state__',
            'room_occupancy_sensors':[],
            'source_stale_minutes':240}
known=set(areas.values())
h.put('input_text.occupied_rooms','Wohnzimmer')
h.put('binary_sensor.bath_occupancy','on',area='badezimmer',klass='occupancy')
h.put('binary_sensor.bath_presence','off',area='badezimmer',klass='presence')
h.put('binary_sensor.living_presence','off',area='wohnzimmer',klass='occupancy')
h.put('binary_sensor.other_room','on',area='wohnzimmer',klass='occupancy')
h.put('binary_sensor.no_class','on',area='badezimmer')
h.put('binary_sensor.old_bath','on',area='badezimmer',klass='occupancy',age=400)
setting={'occupancy_sensors':['binary_sensor.bath_occupancy',
                             'binary_sensor.bath_presence'],
         'occupancy_stale_minutes':240}
def expect(room,setting,status,reason=None):
    actual=resolve(h,room,setting,global_cfg,known_areas=known)
    assert actual[0]==status, (status,actual)
    if reason is not None:assert actual[1]==reason,(reason,actual)
    return actual

# List is authoritative even with contradictory local ON sensors.
expect('wohnzimmer',{'occupancy_sensors':['binary_sensor.living_presence']},
       'occupied','verified_room_occupied')
expect('badezimmer',setting,'unoccupied','verified_room_list_unoccupied')
expect('gastezimmer',{},'unoccupied','verified_room_list_unoccupied')
# Explicit empty (both input_text representations) never initiates fallback.
for value in ('','[]','none'):
    h.put('input_text.occupied_rooms',value)
    expect('badezimmer',setting,'unoccupied','verified_room_list_unoccupied')
    expect('wohnzimmer',{},'unoccupied','verified_room_list_unoccupied')
# Unavailable list: only the room's *selected* positive sensor qualifies.
for value in ('unknown','unavailable'):
    h.put('input_text.occupied_rooms',value)
    expect('badezimmer',setting,'occupied','selected_room_sensor_on')
    expect('wohnzimmer',{'occupancy_sensors':['binary_sensor.living_presence']},
           'unoccupied','all_selected_room_sensors_off')
    expect('badezimmer',{'occupancy_sensors':['binary_sensor.bath_presence']},
           'unoccupied','all_selected_room_sensors_off')
    expect('badezimmer',{'occupancy_sensors':[]},'unknown','room_occupancy_source_unknown')
    expect('gastezimmer',{'occupancy_sensors':[]},'unknown','room_occupancy_source_unknown')
    # A positive sensor in a DIFFERENT area must never prove presence here.
    expect('badezimmer',{'occupancy_sensors':['binary_sensor.other_room']},'unknown')
    # Existing rooms without an explicit choice get suggested HA candidates.
    assert 'binary_sensor.bath_occupancy' in ns['room_sensor_choices'](h,'badezimmer')
    expect('badezimmer',{},'occupied','selected_room_sensor_on')
    # Unknown sensors do not prove absence; none available is UNKNOWN.
    expect('badezimmer',{'occupancy_sensors':['binary_sensor.old_bath']},'unknown')
# Stale list can similarly fall back, never be taken as a fresh room list.
h.put('input_text.occupied_rooms','Wohnzimmer',age=400)
expect('badezimmer',setting,'occupied','selected_room_sensor_on')
# Malformed list/unknown area is NOT permission to adopt local false-positive.
h.put('input_text.occupied_rooms','["Unknown room"]')
expect('badezimmer',setting,'unknown','unrecognized_room_in_occupancy_source')
h.put('input_text.occupied_rooms','[broken unparseable')
expect('badezimmer',setting,'unknown','invalid_rooms_format')
# The room's fallback choices are always included in the tracking set,
# even while the list is authoritative and they are not consulted.
h.put('input_text.occupied_rooms','Wohnzimmer')
actual=expect('badezimmer',setting,'unoccupied')
assert 'binary_sensor.bath_occupancy' in actual[2]
assert 'input_text.occupied_rooms' in actual[2]
# Device permissions must call the same room_presence function for live
# command-time checks; the room plan must skip fake vacancy dwell on a list.
device=(ROOT/'occupancy_policy.py').read_text(encoding='utf-8')
climate=(ROOT/'climate_rooms.py').read_text(encoding='utf-8')
assert 'room,_,_=room_presence(hass,area,room_config,global_settings' in device
assert 'occ_reason != "verified_room_list_unoccupied"' in climate
print('BETA78_ROOM_LIST_PRECEDENCE_AND_SELECTED_FALLBACK=PASS')

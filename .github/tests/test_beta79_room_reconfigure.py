"""Beta79 room-centric menu and source-editor regressions using production methods.

No real appliance calls. Actual ReconfigureRoomsMixin is AST-compiled intact
and given deterministic HA registries and a config entry. Covers per-room
direct navigation, all eight selectors, first-time defaults, explicit empty,
room isolation, no unnecessary permission changes, and room removals.
"""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
source=ast.parse((ROOT/"reconfigure_rooms.py").read_text(encoding="utf-8"))
nodes=[n for n in source.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))
       and n.name in ("ReconfigureRoomsMixin","_locale_menu")]
assert len(nodes)==2

group_names=("windows","air_quality","temperature","humidity",
             "pressure","climate_devices","shades")
rooms={"badezimmer":"Badezimmer","wohnzimmer":"Wohnzimmer",
       "schlafzimmer":"Schlafzimmer"}
actual={
 "binary_sensor.bath_presence":"badezimmer",
 "binary_sensor.bath_empty":"badezimmer",
 "binary_sensor.living_presence":"wohnzimmer",
 "sensor.bath_temp":"badezimmer",
 "sensor.bath_rh":"badezimmer",
 "climate.comfee":"badezimmer",
 "binary_sensor.window":"badezimmer",
}
candidate_defaults={
 "windows":["binary_sensor.window"],"air_quality":[],
 "temperature":["sensor.bath_temp"],"humidity":["sensor.bath_rh"],
 "pressure":[],"climate_devices":["climate.comfee"],"shades":[],
}
calls=[]
def saved_defaults(hass,opts,area):
    existing=opts.get("room_sources",{}).get(area)
    if isinstance(existing,dict):
        return {key:list(existing.get(key,[])) for key in group_names}
    return deepcopy(candidate_defaults if area=="badezimmer"
                    else {key:[] for key in group_names})
def choices(hass,area,previous):
    return {key:[{"value":eid,"label":eid} for eid in values]
            for key,values in previous.items()}
def store_selection(hass,opts,area,values):
    calls.append(("store_selection",area,deepcopy(values)))
    opts.setdefault("room_sources",{})[area]=deepcopy(values)
def restrict_rooms(opts,areas):
    calls.append(("restrict_rooms",list(areas)))
    opts["areas"]=list(areas)

module_source=N(GROUPS=group_names,CONF_ROOM_SOURCES="room_sources",
    defaults=saved_defaults,choices=choices,store_selection=store_selection,
    restrict_rooms=restrict_rooms,label=lambda h,e:e)
pack=ModuleType("beta79_fixture");pack.__path__=[]
presence=ModuleType("beta79_fixture.occupancy_policy")
presence.room_sensor_choices=lambda hass,area: [
 eid for eid,found in actual.items()
 if found==area and eid.startswith("binary_sensor.") and "presence" in eid
] + (["binary_sensor.bath_empty"] if area=="badezimmer" else [])
discovery=ModuleType("beta79_fixture.discovery")
discovery.entity_area=lambda hass,eid:actual.get(eid)
sys.modules.update({
 "beta79_fixture":pack,"beta79_fixture.occupancy_policy":presence,
 "beta79_fixture.discovery":discovery
})
def schema(fields):return fields
class Probatio:
    Schema=staticmethod(schema)
    @staticmethod
    def Required(key,default=None):return key
ns={
 "__name__":"beta79_fixture.reconfigure_rooms","__package__":"beta79_fixture",
 "__file__":str(ROOT/"reconfigure_rooms.py"),
 "json":__import__("json"),"Path":Path,
 "Any":object,"probatio":Probatio,"ar":N(async_get=lambda hass:N(
      async_get_area=lambda area:N(name=rooms[area]) if area in rooms else None)),
 "er":N(),"deepcopy":deepcopy,"sources":module_source,
 "field":lambda name,default:name,
 "select":lambda options,multiple=False:{"multiple":multiple,"options":options},
 "areas":lambda hass:[{"value":key,"label":name} for key,name in rooms.items()],
 "CONF_AREAS":"areas","CONF_CLIMATE_ROOMS":"climate_rooms",
}
exec(compile(ast.Module(body=nodes,type_ignores=[]),
             "reconfigure_rooms.py","exec"),ns)
Mixin=ns["ReconfigureRoomsMixin"]

class UI(Mixin):
    def __init__(self,with_sources=False):
        self._values={
            "areas":["badezimmer","wohnzimmer"],
            "climate_rooms":{
                "badezimmer":{"enabled":True,"device_settings":{
                    "climate.comfee":{"auto_control":True}
                }},
                "wohnzimmer":{"enabled":True},
            },
            **({"room_sources":{"badezimmer":deepcopy(candidate_defaults)}}
               if with_sources else {})
        }
        self._room_edit_area=None
        self.hass=N(config=N(language="el"),states=N(get=lambda e:N(state="on")))
        self.saves=0
        self.saved=[]
    def async_show_form(self,**kw):return {"type":"form",**kw}
    def async_show_menu(self,**kw):return {"type":"menu",**kw}
    def async_abort(self,reason):return {"type":"abort","reason":reason}
    async def _finish(self):
        self.saves+=1;self.saved.append(deepcopy(self._values))
        return {"type":"save","data":deepcopy(self._values)}
    async def async_step_setup_general(self,input=None):
        return {"type":"general","data":input}

async def run():
    f=UI()
    menu=f._room_edit_menu()
    assert list(menu)==[
        "choose_rooms","edit_room_badezimmer",
        "edit_room_wohnzimmer","general_settings"
    ],menu
    assert menu["edit_room_badezimmer"]=="Ρυθμίσεις · Badezimmer"
    assert menu["choose_rooms"]=="Επιλογή δωματίων"
    assert not hasattr(f,"async_step_edit_room_schlafzimmer")
    assert not hasattr(f,"async_step_edit_room_nonexistent")

    # HA's actual dispatcher does getattr(flow, "async_step_"+choice).
    page=await getattr(f,"async_step_edit_room_badezimmer")()
    assert page["type"]=="form" and page["step_id"]=="room_settings"
    assert set(page["data_schema"])==set(group_names)|{"occupancy_sensors"}
    assert f._room_edit_area=="badezimmer"
    # First visit must not mutate a configuration.
    assert f.saves==0 and "room_sources" not in f._values
    assert f._values["climate_rooms"]["badezimmer"]["device_settings"]["climate.comfee"]["auto_control"]
    full={group:list(values) for group,values in candidate_defaults.items()}
    full["occupancy_sensors"]=["binary_sensor.bath_presence","binary_sensor.bath_empty"]
    result=await f.async_step_room_settings(full)
    assert result["type"]=="save" and f.saves==1
    assert f.saved[0]["climate_rooms"]["badezimmer"]["occupancy_sensors"]==full["occupancy_sensors"]
    assert f.saved[0]["climate_rooms"]["badezimmer"]["device_settings"]["climate.comfee"]["auto_control"] is True
    assert f.saved[0]["climate_rooms"]["wohnzimmer"]=={"enabled":True}
    assert calls==[],calls  # initial existing choices did not revoke grants

    # Explicitly empty occupancy list always overrides auto-discovery.
    f2=UI(with_sources=True)
    f2._values["climate_rooms"]["badezimmer"]["occupancy_sensors"]=[]
    await getattr(f2,"async_step_edit_room_badezimmer")()
    assert set(f2._values["climate_rooms"]["badezimmer"]["occupancy_sensors"])==set()
    entered={group:list(values) for group,values in candidate_defaults.items()}
    entered["occupancy_sensors"]=[]
    saved=await f2.async_step_room_settings(entered)
    assert saved["data"]["climate_rooms"]["badezimmer"]["occupancy_sensors"]==[]
    assert calls==[],calls
    # An actual change revokes only through the existing source path.
    f3=UI(with_sources=True)
    await getattr(f3,"async_step_edit_room_badezimmer")()
    changed={group:list(values) for group,values in candidate_defaults.items()}
    changed["temperature"]=[]
    changed["occupancy_sensors"]=[]
    await f3.async_step_room_settings(changed)
    assert calls[-1][0:2]==("store_selection","badezimmer")
    assert f3._values["climate_rooms"]["wohnzimmer"]=={"enabled":True}

    # Choose rooms edits only once; initial render is read-only.
    f4=UI()
    choose=await f4.async_step_choose_rooms()
    assert choose["type"]=="form" and f4.saves==0
    outcome=await f4.async_step_choose_rooms({"areas":["badezimmer"]})
    assert outcome["type"]=="save"
    assert calls[-1]==("restrict_rooms",["badezimmer"])
    assert not hasattr(f4,"async_step_edit_room_wohnzimmer")
    # Explicitly rejected empty selection cannot wipe all rooms.
    f5=UI()
    rejected=await f5.async_step_choose_rooms({"areas":[]})
    assert rejected["type"]=="form" and rejected["errors"]
    assert f5.saves==0
    assert (await f5.async_step_general_settings({"hello":"world"}))=={
        "type":"general","data":{"hello":"world"}
    }
    print("BETA79_ROOM_MENU_AND_SOURCE_FORM=PASS")

asyncio.run(run())

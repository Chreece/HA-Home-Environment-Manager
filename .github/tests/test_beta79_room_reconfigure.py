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

# Use the production room-hub membership and removal rules. Menu access must
# match existing configured climate/PID hubs, and removing a monitored room
# must withdraw its grants just as the actual room-selection flow does.
hierarchy_source=ast.parse((ROOT/"device_hierarchy.py").read_text(encoding="utf-8"))
membership=next(n for n in hierarchy_source.body
                if isinstance(n,ast.FunctionDef) and n.name=="configured_area_ids")
native_domains=next(n for n in hierarchy_source.body if isinstance(n,ast.Assign)
                    and any(isinstance(target,ast.Name) and target.id=="NATIVE_DOMAINS"
                            for target in n.targets))
membership_ns={"Any":object,"CONF_AREAS":"areas",
               "CONF_CLIMATE_ROOMS":"climate_rooms","CONF_PID_ROOMS":"pid_rooms"}
exec(compile(ast.Module([native_domains,membership],type_ignores=[]),
             "device_hierarchy.py","exec"),membership_ns)
sources_source=ast.parse((ROOT/"room_sources.py").read_text(encoding="utf-8"))
restriction=next(n for n in sources_source.body
                if isinstance(n,ast.FunctionDef) and n.name=="restrict_rooms")
restriction_ns={}
exec(compile(ast.Module([restriction],type_ignores=[]),"room_sources.py","exec"),restriction_ns)

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
    restriction_ns["restrict_rooms"](opts,areas)

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
hierarchy=ModuleType("beta79_fixture.device_hierarchy")
hierarchy.configured_area_ids=membership_ns["configured_area_ids"]
sys.modules.update({
 "beta79_fixture":pack,"beta79_fixture.occupancy_policy":presence,
 "beta79_fixture.discovery":discovery,"beta79_fixture.device_hierarchy":hierarchy
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

class LegacyRoomSteps:
    async def async_step_setup_rooms(self, user_input=None):
        return {"original": "initial_rooms", "data": user_input}
    async def async_step_edit_room(self, user_input=None):
        return {"original": "initial_editor", "data": user_input}

class UI(Mixin, LegacyRoomSteps):
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
        self._menu_mode=True
        self.hass=N(config=N(language="el"),states=N(get=lambda e:N(state="on")),
                    async_add_executor_job=asyncio.to_thread)
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
    menu=await f._room_edit_menu()
    assert list(menu)==[
        "choose_rooms","edit_room_badezimmer",
        "edit_room_wohnzimmer","general_settings"
    ],menu
    assert menu["edit_room_badezimmer"]=="Ρυθμίσεις · Badezimmer"
    assert menu["choose_rooms"]=="Επιλογή δωματίων"
    assert menu["general_settings"]=="Γενικές ρυθμίσεις", menu
    # Exercise actual translation JSON from the release, not mocked locale.
    german = await f.hass.async_add_executor_job(ns["_locale_menu"], "de")
    assert german[1] == "Allgemeine Einstellungen", german
    assert not hasattr(f,"async_step_edit_room_schlafzimmer")
    assert not hasattr(f,"async_step_edit_room_nonexistent")

    # HA's actual dispatcher does getattr(flow, "async_step_"+choice).
    page=await getattr(f,"async_step_edit_room_badezimmer")()
    assert page["type"]=="form" and page["step_id"]=="edit_room"
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

    # The inherited legacy step IDs must dispatch to the current editor
    # without changing initial setup flows or safety grants.
    alias=UI()
    opened=await alias.async_step_setup_rooms()
    assert opened["step_id"]=="setup_rooms"
    alias._room_edit_area="badezimmer"
    rendered=await alias.async_step_edit_room()
    assert rendered["step_id"]=="edit_room"
    alias._menu_mode=False
    assert (await alias.async_step_setup_rooms())["original"]=="initial_rooms"
    assert (await alias.async_step_edit_room())["original"]=="initial_editor"

    # Choose rooms edits only once; initial render is read-only.
    f4=UI()
    choose=await f4.async_step_choose_rooms()
    assert choose["type"]=="form" and choose["step_id"]=="setup_rooms" and f4.saves==0
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

    # A dashboard room can be climate-only, with no CONF_AREAS membership.
    # The same exact room step must open without enrolling it in monitoring
    # or changing its existing actuation/PID permissions.
    rooms.update({"kueche":"Küche","lager":"Lager"})
    configured=UI()
    configured._values["areas"]=["badezimmer"]
    living_sources={key:[] for key in group_names}
    living_sources.update(temperature=["sensor.living_temp"],
                          climate_devices=["climate.radiator"])
    configured._values["room_sources"]={"wohnzimmer":deepcopy(living_sources)}
    configured._values["climate_rooms"]["wohnzimmer"]={
        "enabled":True,"allow_actuation":True,
        "selected_devices":["climate.radiator"],"occupancy_sensors":[],
        "device_settings":{"climate.radiator":{"auto_control":True,"method":"pid"}},
    }
    # Exact-device automatic control can make this room appear in planning
    # while its legacy room-level enabled flag is still false.
    configured._values["climate_rooms"]["kueche"]={
        "enabled":False,"selected_devices":["climate.kitchen"],
    }
    configured._values["climate_rooms"]["lager"]={"enabled":False}
    configured._values["pid_rooms"]={
        "schlafzimmer":{"enabled":True,"climate_entities":["climate.bedroom"]},
        "removed_area":{"enabled":True},
    }
    before=deepcopy(configured._values)
    room_menu=await configured._room_edit_menu()
    assert list(room_menu)==["choose_rooms","edit_room_badezimmer",
        "edit_room_wohnzimmer","edit_room_kueche","edit_room_schlafzimmer",
        "general_settings"],room_menu
    assert not hasattr(configured,"async_step_edit_room_lager")
    assert not hasattr(configured,"async_step_edit_room_removed_area")
    page=await getattr(configured,"async_step_edit_room_wohnzimmer")()
    assert page["type"]=="form" and page["step_id"]=="edit_room"
    assert page["description_placeholders"]=={"area_name":"Wohnzimmer"}
    assert configured._values==before and configured.saves==0
    original_calls=len(calls)
    result=await configured.async_step_room_settings({**living_sources,"occupancy_sensors":[]})
    assert result["type"]=="save" and result["data"]==before
    assert len(calls)==original_calls, calls
    assert result["data"]["areas"]==["badezimmer"]
    assert result["data"]["climate_rooms"]["wohnzimmer"]["allow_actuation"] is True
    assert result["data"]["pid_rooms"]==before["pid_rooms"]
    # A room removed after its menu was shown cannot be edited through a
    # retained step callback, even when its old source selections remain.
    stale_step=getattr(configured,"async_step_edit_room_wohnzimmer")
    configured._values["climate_rooms"]["wohnzimmer"].update(
        enabled=False,selected_devices=[])
    rejected=await stale_step()
    assert rejected=={"type":"abort","reason":"setup_area_removed"},rejected
    assert configured.saves==1
    print("BETA114_MONITORED_AND_CONFIGURED_ROOM_SETTINGS_NO_NEW_GRANTS=PASS")
    print("BETA79_ROOM_MENU_AND_SOURCE_FORM=PASS")

asyncio.run(run())

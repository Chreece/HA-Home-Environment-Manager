"""B13 backend: configured offline thermostat survives absent HA attributes.

No Home Assistant runtime or physical device is needed. The inventory derives
only from registered HEM source specs and persisted selection, and never
writes configuration or commands the physical Zigbee device.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace as N
import sys

ROOT=Path(__file__).resolve().parents[2]
PACKAGE="hem_b13_inventory_fixture"
pkg=ModuleType(PACKAGE)
pkg.__path__=[str(ROOT)]
sys.modules[PACKAGE]=pkg
const=ModuleType(PACKAGE+".const")
const.DOMAIN="environment_manager"
sys.modules[const.__name__]=const
sources=ModuleType(PACKAGE+".device_hierarchy")
sources.configured_sources=lambda settings,area:settings["allowed"][area]
sys.modules[sources.__name__]=sources
specA=N(identifier="entry_controller_trv",name="Καθιστικό θερμοστάτης",
        area_id="wohnzimmer",source_device_id="zha_trv",
        source_entities=("climate.wohnzimmer_trv",))
specB=N(identifier="entry_controller_purifier",name="Mi Air Purifier",
        area_id="wohnzimmer",source_device_id="mi_fan",
        source_entities=("fan.mi_purifier",))
specC=N(identifier="entry_controller_other",name="Not selected",
        area_id="kitchen",source_device_id="foreign",
        source_entities=("climate.foreign",))
equipment=ModuleType(PACKAGE+".equipment_model")
equipment.specs=lambda manager:(specA,specB,specC)
equipment.settings=lambda manager,spec:{
    "control_mode":"pid" if spec is specA else "automatic",
    "power_switch_entity":None,
}
equipment.operating_modes=lambda manager,spec:("heat",) if spec is specA else ("fan_only",)
sys.modules[equipment.__name__]=equipment
recordA=N(platform="environment_manager",config_entry_id="hem_entry",
          unique_id="entry_controller_trv_climate",disabled_by=None)
recordB=N(platform="environment_manager",config_entry_id="hem_entry",
          unique_id="entry_controller_purifier_climate",disabled_by=None)
registered={"climate.hem_trv":recordA,"climate.hem_purifier":recordB}
registry=N(
    async_get_entity_id=lambda domain,platform,uid:{
        "entry_controller_trv_climate":"climate.hem_trv",
        "entry_controller_purifier_climate":"climate.hem_purifier",
    }.get(uid),
    async_get=registered.get,
)
er=ModuleType("homeassistant.helpers.entity_registry")
er.async_get=lambda hass:registry
helpers=ModuleType("homeassistant.helpers")
helpers.__path__=[]
helpers.entity_registry=er
ha=ModuleType("homeassistant")
ha.__path__=[]
ha.helpers=helpers
sys.modules.update({
    "homeassistant":ha,"homeassistant.helpers":helpers,
    "homeassistant.helpers.entity_registry":er,
})
spec=importlib.util.spec_from_file_location(
    PACKAGE+".controller_inventory",ROOT/"controller_inventory.py")
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
class States:
    states={
        "climate.wohnzimmer_trv":N(state="unavailable",attributes={}),
        "fan.mi_purifier":N(state="off",attributes={"friendly_name":"Mi Air Purifier"}),
        "climate.hem_trv":N(state="unavailable",attributes={}),
    }
    def get(self,entity):
        return self.states.get(entity)
class Services:
    def __getattr__(self,name):
        raise AssertionError("Inventory may not call Home Assistant services")
manager=N(
    entry=N(entry_id="hem_entry"),settings={
        "allowed":{"wohnzimmer":["climate.wohnzimmer_trv","fan.mi_purifier"],
                   "kitchen":[]}},
    hass=N(states=States(),services=Services()),
    equipment=N(statuses={
        "entry_controller_trv":{"status":"waiting_for_physical_device",
                                "reason":"native_source_unavailable"}},
        records={"entry_controller_trv":{
            "capabilities":{"primary":"climate.wohnzimmer_trv"}}},
        active_control_mode=lambda spec:"heat" if spec is specA else "fan_only")
)
rows=module.controller_inventory(manager)
assert len(rows)==2,rows
trv=next(row for row in rows if row["name"]=="Καθιστικό θερμοστάτης")
assert trv["climate_entity_id"]=="climate.hem_trv",trv
assert trv["source_entity_ids"]==["climate.wohnzimmer_trv"]
assert trv["unavailable_source_entity_ids"]==["climate.wohnzimmer_trv"]
assert trv["supported_operating_modes"]==["heat"]
assert trv["selected_operating_mode"]=="heat"
assert trv["upstream_power_switch"] is None
assert trv["status_code"]=="waiting_for_physical_device"
assert next(row for row in rows if row["name"]=="Mi Air Purifier")[
    "unavailable_source_entity_ids"]==[]
assert all(row["area_id"]=="wohnzimmer" for row in rows)
assert all(row["source_device_id"]!="foreign" for row in rows)

# No frontend/HACS entity-registry dependency at all. Registered HEM IDs are
# resolved server side. Wrong owner may be named but never linked to another
# config entry's actual climate control.
registered["climate.hem_trv"]=N(
    platform="environment_manager",config_entry_id="different_entry",
    unique_id="entry_controller_trv_climate",disabled_by=None)
assert module.controller_inventory(manager)[0]["climate_entity_id"] is None
registered["climate.hem_trv"]=recordA
manager.hass.states.states["climate.wohnzimmer_trv"]=N(state="heat",attributes={})
restored=module.controller_inventory(manager)
assert restored[0]["unavailable_source_entity_ids"]==[]
assert restored[0]["climate_entity_id"]=="climate.hem_trv"
assert len(restored)==2
print("B13_CONFIGURED_TRV_OFFLINE_BACKEND_INVENTORY=PASS")

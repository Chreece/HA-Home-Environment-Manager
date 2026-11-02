"""Beta86: physical HA error entities, default-ON alerts, no synthetic sensor.

Exercise real detection and dispatch with two distinct HA physical devices,
exact registry identity, native state events, full announcement isolation and
the per-device preference writer. No physical device services or HA secrets.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
PKG="hem_beta86_native_fault_fixture"
package=ModuleType(PKG)
package.__path__=[str(ROOT)]
sys.modules[PKG]=package
const=ModuleType(PKG+".const")
const.DOMAIN="environment_manager"
const.CONF_HUB="use_announcement_hub"
const.CONF_NOTIFY_TARGETS="notify_entities"
const.CONF_TTS_ENGINE="tts_engine"
const.CONF_MEDIA_PLAYERS="media_players"
const.CONF_AUTO_TTS="automatic_tts"
sys.modules[const.__name__]=const
model=ModuleType(PKG+".equipment_model")
model.SETTINGS="equipment_controllers"
model.specs=lambda manager:manager.specs
model.settings=lambda manager,spec:{
    "announce_device_errors":manager.settings.get(model.SETTINGS,{})
    .get(spec.identifier,{}).get("announce_device_errors",True)
}
sys.modules[model.__name__]=model
cfg_mod=ModuleType(PKG+".config_data")
cfg_mod.mutable_copy=lambda value:deepcopy(value)
sys.modules[cfg_mod.__name__]=cfg_mod
hub=ModuleType(PKG+".hub_delivery")
hub.is_on=False
hub.events=[]
hub.hub_available=lambda hass:hub.is_on
async def submit(hass,payload):
    hub.events.append(payload)
    return True
hub.async_submit_hub=submit
sys.modules[hub.__name__]=hub

# Stub precisely the HA registry APIs this monitor reads. An unrelated device
# in the same room must not be accidentally attributed to another controller.
class Registry:
    def __init__(self):
        self.entities={}
    def async_get(self,entity):
        return self.entities.get(entity)
registry=Registry()
areas={"bath":N(name="Bathroom"),"kitchen":N(name="Kitchen")}
ER=ModuleType("homeassistant.helpers.entity_registry")
ER.async_get=lambda hass:registry
AR=ModuleType("homeassistant.helpers.area_registry")
AR.async_get=lambda hass:N(async_get_area=lambda area:areas.get(area))
ha=ModuleType("homeassistant")
ha.__path__=[]
helpers=ModuleType("homeassistant.helpers")
helpers.__path__=[]
helpers.entity_registry=ER
helpers.area_registry=AR
ha.helpers=helpers
sys.modules.update({
    "homeassistant":ha,
    "homeassistant.helpers":helpers,
    "homeassistant.helpers.entity_registry":ER,
    "homeassistant.helpers.area_registry":AR,
})
exc=ModuleType("homeassistant.exceptions")
class HomeAssistantError(Exception):
    pass
exc.HomeAssistantError=HomeAssistantError
sys.modules[exc.__name__]=exc

specA=N(identifier="managed_a",name="Bathroom Dehumidifier",
        area_id="bath",source_device_id="physical_a",
        source_entities=("climate.a",))
specB=N(identifier="managed_b",name="Kitchen Heater",
        area_id="kitchen",source_device_id="physical_b",
        source_entities=("climate.b",))
def reg(entity,device,*,platform="zha",original_name=None,
        area_id=None,disabled_by=None):
    registry.entities[entity]=N(
        entity_id=entity,device_id=device,platform=platform,
        original_name=original_name,area_id=area_id,disabled_by=disabled_by,
    )
def state(value,**attrs):
    return N(state=value,attributes=attrs)

reg("climate.a","physical_a")
reg("climate.b","physical_b")
reg("sensor.a_error_code","physical_a",original_name="Error Code")
reg("sensor.b_error_code","physical_b",original_name="Error Code")
reg("sensor.unrelated_error","physical_c",original_name="Error Code",
    area_id="bath")
reg("sensor.a_error_counter","physical_a",original_name="Error Counter")
reg("binary_sensor.a_problem","physical_a",original_name="Problem")
reg("sensor.disabled_fault","physical_a",original_name="Fault",disabled_by="user")
reg("sensor.other_area_error","physical_a",original_name="Error",area_id="kitchen")
states={
    "climate.a":state("off",error_code=0),
    "climate.b":state("heat",hvac_action="heating",error_code=0),
    "sensor.a_error_code":state("0",error_code=0,error_message="old fault from last week"),
    "sensor.b_error_code":state("0"),
    "sensor.unrelated_error":state("E9",error_message="Unrelated"),
    "sensor.a_error_counter":state("7"),
    "binary_sensor.a_problem":state("off",device_class="problem"),
    "sensor.disabled_fault":state("E10"),
    "sensor.other_area_error":state("E11"),
}
class Services:
    def __init__(self):
        self.calls=[]
        self.allowed={("notify","send_message"),
                      ("persistent_notification","create"),("tts","speak")}
    def has_service(self,domain,service):
        return (domain,service) in self.allowed
    async def async_call(self,domain,service,data,**kw):
        self.calls.append((domain,service,data,kw))
class Entry:
    entry_id="hem"
    data={}
    options={}
class Manager:
    def __init__(self):
        self.hass=N(states=N(get=states.get),services=Services(),
                    config=N(language="en"),config_entries=N())
        self.hass.async_create_task=lambda work:asyncio.create_task(work)
        self.entry=Entry()
        self.entry.options={}
        self.hass.config_entries.async_update_entry=self.update_entry
        self.specs=(specA,specB)
        self.updated=[]
        self.equipment=N(_presentation_updates=N(
            request=lambda identifier:self.updated.append(identifier)
        ))
        self._device_settings_write_lock=asyncio.Lock()
    @property
    def settings(self):
        return {**self.entry.data,**self.entry.options}
    def update_entry(self,entry,*,options):
        entry.options=deepcopy(options)
    def _targets_in_room(self,targets,area):
        return [t for t in targets if isinstance(t,str)]
manager=Manager()
module_spec=importlib.util.spec_from_file_location(PKG+".device_faults",ROOT/"device_faults.py")
module=importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name]=module
module_spec.loader.exec_module(module)
manager.faults=module.NativeDeviceFaultMonitor(manager)
F=module
assert not F._active("0") and not F._active("0000") and not F._active("0.00")
assert not F._active("No error") and not F._active("normal")
assert F._active("E37") and F._active(True)
assert not F.fault_entity_id(
    "sensor.a_error_counter",registry.async_get("sensor.a_error_counter"),
    states["sensor.a_error_counter"],
)
assert F.fault_entity_id(
    "binary_sensor.a_problem",registry.async_get("binary_sensor.a_problem"),
    states["binary_sensor.a_problem"],
)
assert F._read_native_error(
    "climate.a",state("off",error_code=0,error_description="old fault"),
    fault_entity=False,
) is None
problem=F._read_native_error(
    "binary_sensor.a_problem",
    state("on",device_class="problem",error_message="Compressor fault"),
    fault_entity=True,
)
assert problem["code"]=="problem"
assert problem["description"]=="Compressor fault"
assert model.settings(manager,specA)["announce_device_errors"] is True

name_spec=importlib.util.spec_from_file_location(
    PKG+".equipment_name_catalog",ROOT/"equipment_name_catalog.py"
)
name_catalog=importlib.util.module_from_spec(name_spec)
sys.modules[name_spec.name]=name_catalog
name_spec.loader.exec_module(name_catalog)
for catalog in [ROOT/"strings.json",*(ROOT/"translations").glob("*.json")]:
    label=json.loads(catalog.read_text())["entity"]["switch"][
        "equipment_announce_device_errors"
    ]["name"]
    language="en" if catalog.name=="strings.json" else catalog.stem
    assert name_catalog.localized_equipment_name(
        "announce_device_errors",language
    )==label.replace("{channel}","").strip(),catalog
assert len(list((ROOT/"translations").glob("*.json")))==38

async def drain():
    tasks=tuple(manager.faults._tasks)
    if tasks:
        await asyncio.gather(*tasks)

async def run():
    monitor=manager.faults
    monitor.start()
    assert monitor.details(specA)["status"]=="ok",monitor.details(specA)
    assert monitor.details(specB)["status"]=="ok",monitor.details(specB)
    assert "sensor.a_error_code" in monitor._by_entity
    assert "sensor.unrelated_error" not in monitor._by_entity
    assert "sensor.a_error_counter" not in monitor._by_entity
    assert "sensor.disabled_fault" not in monitor._by_entity
    assert "sensor.other_area_error" not in monitor._by_entity
    assert not manager.hass.services.calls,manager.hass.services.calls

    # Original HA error entity is authoritative: state + physical attributes.
    states["sensor.a_error_code"]=state(
        "E07",error_code="E07",error_message="Blocked filter",
        severity="warning",error_detail="Clean filter",
        error_info={"part":"filter","action":"clean"},
        device_class=None,
    )
    monitor.state_changed("sensor.a_error_code")
    await drain()
    info=monitor.details(specA)
    assert info["status"]=="warning" and info["code"]=="E07",info
    assert info["description"]=="Blocked filter" and info["active_count"]==1
    assert "part: filter" in info["info"]["error_info"]
    assert "action: clean" in info["info"]["error_info"]
    assert info["source_entity_id"]=="sensor.a_error_code"
    assert not monitor.details(specB)["faults"]
    assert len(manager.hass.services.calls)==1
    assert manager.hass.services.calls[0][0:2]==("persistent_notification","create")
    assert "Blocked filter" in manager.hass.services.calls[0][2]["message"]
    # No duplicate if HA repeatedly publishes same native fault.
    states["sensor.a_error_code"]=state(
        "E07",error_code="E07",error_message="Blocked filter",
        severity="warning",error_detail="Clean filter",last_seen=123,
    )
    monitor.state_changed("sensor.a_error_code")
    await drain()
    assert len(manager.hass.services.calls)==1

    states["sensor.a_error_code"]=state(
        "E07",error_code="E07",error_message="Blocked filter",severity="critical",
    )
    monitor.state_changed("sensor.a_error_code")
    await drain()
    assert len(manager.hass.services.calls)==2
    assert monitor.details(specA)["status"]=="critical"

    # An unavailable native fault sensor is not an all-clear. Keep the
    # last known fault for dashboard diagnostics; do not reannounce.
    states["sensor.a_error_code"]=state("unavailable")
    monitor.state_changed("sensor.a_error_code")
    await drain()
    assert monitor.details(specA)["status"]=="unavailable"
    assert monitor.details(specA)["last_known_fault"]["code"]=="E07"
    assert len(manager.hass.services.calls)==2
    # Only an explicitly clear manufacturer report resets deduplication.
    states["sensor.a_error_code"]=state("0",error_code=0)
    monitor.state_changed("sensor.a_error_code")
    await drain()
    assert monitor.details(specA)["status"]=="ok"
    assert len(manager.hass.services.calls)==2
    # Recurrence of same code/severity is a NEW event after confirmed recovery.
    states["sensor.a_error_code"]=state(
        "E07",error_code="E07",error_message="Blocked filter",severity="critical",
    )
    monitor.state_changed("sensor.a_error_code")
    await drain()
    assert len(manager.hass.services.calls)==3

    # Per-device switch writes only HA config data, even if physical
    # climate becomes unavailable; never changes native hardware.
    states["climate.a"]=state("unavailable")
    await monitor.async_set_announcements(specA,False)
    assert model.settings(manager,specA)["announce_device_errors"] is False
    states["sensor.a_error_code"]=state("E99",error_code="E99")
    monitor.state_changed("sensor.a_error_code")
    await drain()
    assert len(manager.hass.services.calls)==3
    assert monitor.details(specA)["code"]=="E99"
    await monitor.async_set_announcements(specA,True)
    assert model.settings(manager,specA)["announce_device_errors"] is True
    assert len(manager.hass.services.calls)==3
    states["climate.a"]=state("off",error_code=0)

    # Existing native error attributes work even without a separate
    # diagnostic fault sensor; no new HEM sensor is ever created.
    states["sensor.a_error_code"]=state("0",error_code=0)
    monitor.state_changed("sensor.a_error_code")
    states["climate.a"]=state("off",error_code=204,error_message="Water container full")
    manager.entry.options.update({
        "notify_entities":["notify.mobile_app_phone"],
    })
    monitor.state_changed("climate.a")
    await drain()
    assert len(manager.hass.services.calls)==4
    d=manager.hass.services.calls[-1]
    assert d[:2]==("notify","send_message"),d
    assert "Water container full" in d[2]["message"]
    assert d[3]["target"]["entity_id"]==["notify.mobile_app_phone"]
    assert monitor.details(specA)["source_entity_id"]=="climate.a"

    # With Hub selected, exactly one Hub handoff owns any retry/fallback;
    # no extra direct Home Assistant notification.
    hub.is_on=True
    manager.entry.options["use_announcement_hub"]=True
    states["climate.a"]=state("off",error_code=205,error_message="Motor overload")
    monitor.state_changed("climate.a")
    await drain()
    assert len(hub.events)==1
    assert len(manager.hass.services.calls)==4
    assert hub.events[0]["use_ai"] is False
    assert "Motor overload" in hub.events[0]["text"]

    # Turning alerts OFF on another managed device is isolated.
    await monitor.async_set_announcements(specB,False)
    assert model.settings(manager,specB)["announce_device_errors"] is False
    assert model.settings(manager,specA)["announce_device_errors"] is True
    await monitor.async_stop()
    assert not monitor.active
    assert "device_faults.py" not in (ROOT/"sensor.py").read_text()
    assert "AnnounceDeviceErrorsSensor" not in (ROOT/"sensor.py").read_text()
    print("BETA86_NATIVE_HA_FAULT_MONITOR_NO_DUPLICATE_SENSOR_DEFAULT_ON=PASS")

asyncio.run(run())
